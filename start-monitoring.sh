#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl apply -f platform/namespace.yaml
# Kubernetes log streaming needs one watcher per active container stream.
minikube -p bigdata ssh -- 'current=$(sysctl -n fs.inotify.max_user_instances); if [ "$current" -lt 1024 ]; then sudo sysctl -w fs.inotify.max_user_instances=1024; fi' < /dev/null
for manifest in monitoring/*.yaml; do kubectl apply -f "$manifest"; done
for app in loki alloy prometheus jaeger grafana; do
  if [[ "$app" == grafana ]]; then
    checksum=$(cat monitoring/grafana.yaml monitoring/grafana-dashboard-*.yaml | sha256sum | cut -d ' ' -f1)
  else
    checksum=$(sha256sum "monitoring/$app.yaml" | cut -d ' ' -f1)
  fi
  kubectl -n bigdata patch "statefulset/$app" --type=merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"training.config-sha\":\"$checksum\"}}}}}"
  kubectl -n bigdata rollout status "statefulset/$app" --timeout=600s
done
