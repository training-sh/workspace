#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
for app in alloy loki prometheus grafana jaeger; do
 kubectl -n bigdata scale "statefulset/$app" --replicas=0
done
# PVCs and configuration are retained. Close monitoring-access.sh with Ctrl+C.
