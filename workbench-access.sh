#!/usr/bin/env bash
set -euo pipefail
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
workers=()
jupyter_port=${JUPYTER_PORT:-8889}
airflow_port=${AIRFLOW_PORT:-8087}
cleanup() { for worker in "${workers[@]}"; do kill "$worker" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
forward() {
  local service=$1 local_port=$2 remote_port=$3 child=''
  trap '[[ -z "$child" ]] || kill "$child" 2>/dev/null; exit 0' TERM INT
  while true; do
    kubectl -n bigdata port-forward --address=127.0.0.1 "service/$service" "$local_port:$remote_port" & child=$!
    wait "$child" || true; child=''
    sleep 3 & child=$!; wait "$child" || true; child=''
  done
}
for port in "$jupyter_port" "$airflow_port"; do
  if (echo > "/dev/tcp/127.0.0.1/$port") 2>/dev/null; then echo "Port $port is occupied; close the previous forward first."; exit 1; fi
done
kubectl -n bigdata wait --for=condition=Ready pod -l app=jupyter --timeout=120s
kubectl -n bigdata wait --for=condition=Ready pod -l app=airflow --timeout=120s
forward jupyter "$jupyter_port" 8888 & workers+=("$!")
forward airflow "$airflow_port" 8080 & workers+=("$!")
echo "Jupyter http://127.0.0.1:$jupyter_port (token team1234); Airflow http://127.0.0.1:$airflow_port (team/team1234)"
echo 'Keep this terminal open. Ctrl+C closes both forwards.'
wait
