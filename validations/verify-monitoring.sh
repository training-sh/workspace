#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
pids=()
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
for mapping in prometheus:19090:9090 grafana:13000:3000 jaeger:16687:16686 jaeger:14318:4318; do
  IFS=: read -r service local_port remote_port <<< "$mapping"
  if (echo > "/dev/tcp/127.0.0.1/$local_port") 2>/dev/null; then echo "Verification port $local_port is occupied"; exit 1; fi
  kubectl -n bigdata port-forward --address=127.0.0.1 "service/$service" "$local_port:$remote_port" >/dev/null 2>&1 & pids+=("$!")
done
for port in 19090 13000 16687 14318; do
  for attempt in $(seq 1 30); do
    if (echo > "/dev/tcp/127.0.0.1/$port") 2>/dev/null; then break; fi
    sleep 1
  done
done
python3 validations/check-monitoring.py
