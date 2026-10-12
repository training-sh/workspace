#!/usr/bin/env bash
# Deploy the current demonstration; exercises remain in the notebooks.
set -euo pipefail
case "${1:-}" in
  --help|-h) echo 'Usage: bash setup-demo.sh [--check | --build-image]'; echo 'Complete Ubuntu preparation (notebook 00) first. Existing images are reused.'; exit 0 ;;
  ''|--check|--build-image) ;;
  *) echo 'Usage: bash setup-demo.sh [--check | --build-image]' >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo 'Pass only one option.' >&2; exit 2; }
option=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")"
export WORKSPACE_HOME="$PWD"
export PATH="$HOME/.local/bin:$PATH"
source versions.env
step='prerequisite checks'
trap 'printf "\nSetup stopped during: %s (line %s). Fix the reported error and run the same command again.\n" "$step" "$LINENO" >&2' ERR
[[ $EUID -ne 0 ]] || { echo 'Run as your ordinary Ubuntu login account, without sudo.' >&2; exit 1; }
[[ "$(uname -m)" == x86_64 ]] || { echo 'This demonstration requires Ubuntu x86_64.' >&2; exit 1; }
for tool in docker minikube kubectl python3 sha256sum; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. Complete 00-setup/00-ubuntu-workspace.ipynb first." >&2; exit 1; }
done
docker info >/dev/null || { echo 'Docker must work without sudo. Complete notebook 00 and reconnect after the group change.' >&2; exit 1; }
if ! docker image inspect "$TRAINING_IMAGE" >/dev/null 2>&1; then
  [[ "$option" == --build-image ]] || { echo "Image $TRAINING_IMAGE is missing. Run: bash setup-demo.sh --build-image (first build can take considerable time)." >&2; exit 1; }
fi
[[ "$option" != --check ]] || { echo "Prerequisites ready. Workspace: $WORKSPACE_HOME. No cluster or files changed."; exit 0; }
mkdir -p .state airflow/dags
step='save workspace path'
python3 - <<'PY'
import os, shlex
from pathlib import Path
p = Path.home() / '.bashrc'
text = p.read_text() if p.exists() else ''
kept, inside = [], False
for line in text.splitlines():
    if line == '# BEGIN BIGDATA WORKSPACE':
        inside = True
    elif line == '# END BIGDATA WORKSPACE':
        inside = False
    elif not inside and line != 'export WORKSPACE_HOME="$HOME/workspace"':
        kept.append(line)
block = '\n# BEGIN BIGDATA WORKSPACE\nexport WORKSPACE_HOME=' + shlex.quote(os.environ['WORKSPACE_HOME'])
block += '\nexport PATH="$HOME/.local/bin:$PATH"\n# END BIGDATA WORKSPACE\n'
p.write_text('\n'.join(kept).rstrip() + '\n' + block)
PY
step='shared image'
if docker image inspect "$TRAINING_IMAGE" >/dev/null 2>&1; then
  printf 'Reusing %s; no rebuild.\n' "$TRAINING_IMAGE"
else
  python3 image/fetch.py
  docker build -t "$TRAINING_IMAGE" image/
fi
step='Minikube and system services'
printf '\n1/6 Start Minikube\n'
minikube start --profile=bigdata --driver=docker --container-runtime=containerd \
  --kubernetes-version="$LAB_K8S_VERSION" --cpus="$LAB_CPUS" --memory="$LAB_MEMORY_MB"
kubectl config use-context bigdata
kubectl wait --for=condition=Ready node --all --timeout=180s
kubectl -n kube-system rollout status deployment/coredns --timeout=180s
kubectl -n kube-system wait --for=condition=Ready pod/storage-provisioner --timeout=180s
kubectl apply -f platform/namespace.yaml
kubectl config set-context bigdata --namespace=bigdata
kubectl apply -f platform/lab-secret.yaml
step='metrics-server and Headlamp'
printf '\n2/6 Enable cluster UI and metrics\n'
minikube -p bigdata addons enable metrics-server
kubectl -n kube-system rollout status deployment/metrics-server --timeout=300s
minikube -p bigdata addons enable headlamp
kubectl -n headlamp rollout status deployment/headlamp --timeout=300s
kubectl apply -f platform/headlamp-access.yaml
step='monitoring'
printf '\n3/6 Start monitoring before data services\n'
bash start-monitoring.sh
step='S3, PostgreSQL, Polaris and MySQL'
printf '\n4/6 Start data services in dependency order\n'
bash cluster.sh start all
step='import shared image'
printf '\n5/6 Import host image into node containerd\n'
docker save "$TRAINING_IMAGE" | docker exec -i bigdata ctr --namespace k8s.io images import -
step='Jupyter, HDFS, Spark and Kafka'
printf '\n6/6 Start compute services sequentially\n'
bash start-components.sh jupyter hdfs spark kafka
kubectl -n bigdata get pods,services,pvc
printf '\nREADY: demonstration deployed. YARN/Hive and later lessons are not started.\n'
printf 'Exercise sample data is created by the notebooks, not this deployment command.\n'
printf 'Browser access: follow 00-setup/QUICKSTART.md or the README UI table.\n'
printf 'Stop the whole cluster, retaining data: minikube -p bigdata stop\n'
