#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
child=''
cleanup() { [[ -z "$child" ]] || kill "$child" 2>/dev/null || true; }
trap 'exit 0' INT TERM
trap cleanup EXIT
echo 'Trino: http://localhost:8089 (user team); keep this terminal open'
while true; do
  kubectl -n bigdata port-forward --address=127.0.0.1 svc/trino 8089:8080 &
  child=$!
  wait "$child" || true
  child=''
  sleep 2
done
