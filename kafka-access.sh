#!/usr/bin/env bash
# Run on the client machine with kubectl access to the training cluster.
# One supervised forward per broker; Ctrl+C closes all forwards.
set -euo pipefail
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
workers=()
cleanup() { for worker in "${workers[@]}"; do kill "$worker" 2>/dev/null || true; done; wait || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
forward_broker() {
  local ordinal=$1 child=''
  trap '[[ -z "$child" ]] || kill "$child" 2>/dev/null; exit 0' TERM INT
  while true; do
    kubectl -n bigdata port-forward --address=127.0.0.1 "pod/kafka-$ordinal" "$((19092 + ordinal)):9093" &
    child=$!
    wait "$child" || true
    child=''
    sleep 3 & child=$!; wait "$child" || true; child=''
  done
}
replicas=$(kubectl -n bigdata get statefulset kafka -o jsonpath='{.spec.replicas}')
[[ "$replicas" -gt 0 ]] || { echo 'Kafka has no brokers'; exit 1; }
# Fail early if a local port is already occupied; never reuse an unknown process.
for ((ordinal=0; ordinal<replicas; ordinal++)); do
  if (echo > "/dev/tcp/127.0.0.1/$((19092 + ordinal))") 2>/dev/null; then
    echo "Port $((19092 + ordinal)) is already in use. Close the previous forward or client service." >&2
    exit 1
  fi
done
for ((ordinal=0; ordinal<replicas; ordinal++)); do
  forward_broker "$ordinal" & workers+=("$!")
done
echo 'Kafka external bootstrap: 127.0.0.1:19092. Keep this terminal open.'
echo 'After changing broker count, restart this script to forward every broker.'
wait
