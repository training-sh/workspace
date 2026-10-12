#!/usr/bin/env bash
set -euo pipefail
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
workers=()
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
for mapping in grafana:3001:3000 prometheus:9090:9090 jaeger:16686:16686 jaeger:4318:4318; do
  IFS=: read -r service local_port remote_port <<< "$mapping"
  if (echo > "/dev/tcp/127.0.0.1/$local_port") 2>/dev/null; then echo "Port $local_port is occupied; close the previous forward/service first."; exit 1; fi
done
for mapping in grafana:3001:3000 prometheus:9090:9090 jaeger:16686:16686 jaeger:4318:4318; do
  IFS=: read -r service local_port remote_port <<< "$mapping"
  forward "$service" "$local_port" "$remote_port" & workers+=("$!")
done
echo 'Grafana http://127.0.0.1:3001 (team/team1234); Prometheus :9090; Jaeger :16686; OTLP HTTP :4318'
echo 'Keep this terminal open. Ctrl+C closes all forwards.'
wait
