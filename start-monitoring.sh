#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
kubectl apply -f platform/namespace.yaml
kubectl apply -f monitoring/
for app in loki alloy prometheus jaeger grafana; do
  checksum=$(sha256sum "monitoring/$app.yaml" | cut -d ' ' -f1)
  kubectl -n bigdata patch "statefulset/$app" --type=merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"training.config-sha\":\"$checksum\"}}}}}"
  kubectl -n bigdata rollout status "statefulset/$app" --timeout=600s
done
