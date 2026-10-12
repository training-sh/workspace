#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
bash start-components.sh hdfs hive spark jupyter
kubectl -n bigdata exec postgres-0 -- sh -ec 'export PGPASSWORD="$POSTGRES_PASSWORD"; if ! psql -h postgres -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datname='\''training_person'\''" | grep -qx training_person; then createdb -h postgres -U "$POSTGRES_USER" training_person; fi'
bash start-components.sh trino
for app in mysql postgres seaweedfs; do kubectl -n bigdata rollout status "statefulset/$app" --timeout=300s; done
kubectl -n bigdata rollout status deployment/polaris --timeout=300s
kubectl -n bigdata exec jupyter-0 -c jupyter -- python /workspace/pyspark/federation/federation_lab.py
