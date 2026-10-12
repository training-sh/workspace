#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
bash start-components.sh lineage hdfs hive spark jupyter
kubectl -n bigdata rollout status deployment/polaris --timeout=300s
kubectl -n bigdata rollout status statefulset/seaweedfs --timeout=300s
kubectl -n bigdata exec postgres-0 -- sh -ec 'export PGPASSWORD="$POSTGRES_PASSWORD"; if ! psql -h postgres -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datname='\''training_person'\''" | grep -qx training_person; then createdb -h postgres -U "$POSTGRES_USER" training_person; fi'
kubectl -n bigdata exec jupyter-0 -- python /workspace/python/person/person_lab.py
