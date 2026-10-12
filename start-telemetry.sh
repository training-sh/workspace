#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
# Existing namespace/base services and shared image are prerequisites.
kubectl apply -f monitoring/telemetry-config.yaml
kubectl apply -f monitoring/prometheus.yaml
kubectl apply -f airflow/airflow.yaml
kubectl -n bigdata rollout status statefulset/airflow --timeout=600s
bash start-components.sh hdfs hive spark jupyter
bash start-monitoring.sh
