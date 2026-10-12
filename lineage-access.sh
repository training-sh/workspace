#!/usr/bin/env bash
set -euo pipefail
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
children=()
cleanup() { for pid in "${children[@]}"; do kill "$pid" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
forward() {
  local service=$1 mapping=$2 health=$3 child='' failures=0 local_port=${2%%:*}
  trap '[[ -z "$child" ]] || kill "$child" 2>/dev/null; exit 0' INT TERM
  while true; do
    kubectl -n bigdata port-forward --address=127.0.0.1 "service/$service" "$mapping" & child=$!
    failures=0
    while kill -0 "$child" 2>/dev/null; do
      sleep 3
      if curl --max-time 3 -fsS "http://127.0.0.1:$local_port$health" >/dev/null 2>&1; then
        failures=0
      else
        failures=$((failures + 1))
        if [[ "$failures" -ge 3 ]]; then
          echo "Reconnecting $service forward"
          kill "$child" 2>/dev/null || true
          break
        fi
      fi
    done
    wait "$child" || true; child=''
    sleep 3
  done
}
for port in 3000 5000; do
  if (echo > "/dev/tcp/127.0.0.1/$port") 2>/dev/null; then echo "Port $port is occupied."; exit 1; fi
done
kubectl -n bigdata rollout status deployment/marquez --timeout=300s
kubectl -n bigdata rollout status deployment/marquez-web --timeout=300s
forward marquez-web 3000:3000 / & children+=("$!")
forward marquez 5000:5000 /api/v1/namespaces & children+=("$!")
echo 'Marquez viewer: http://127.0.0.1:3000 — select namespace training'
echo 'Marquez API: http://127.0.0.1:5000 — Ctrl+C closes both forwards.'
wait
