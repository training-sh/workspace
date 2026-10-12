#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
marker="telemetry-$(date +%s)"
kubectl -n bigdata exec airflow-0 -c airflow -- sh -c 'mkdir -p /opt/airflow/logs; printf "%s-airflow\n" "$1" >> /opt/airflow/logs/telemetry-probe.log' -- "$marker"
kubectl -n bigdata exec hiveserver2-0 -c hiveserver2 -- sh -c 'printf "%s-hive\n" "$1" >> /tmp/team/hive.log' -- "$marker"
kubectl -n bigdata exec namenode-0 -- sh -c 'printf "%s-hdfs\n" "$1" > /proc/1/fd/1' -- "$marker"
kubectl -n bigdata exec prometheus-0 -- sh -c 'printf "%s-prometheus\n" "$1" > /proc/1/fd/1' -- "$marker"
kubectl -n bigdata exec -i jupyter-0 -c jupyter -- env TELEMETRY_MARKER="$marker" python - < validations/spark_probe.py
kubectl -n bigdata exec -i jupyter-0 -c jupyter -- env TELEMETRY_MARKER="$marker" python - < validations/check-telemetry.py
# Confirm stored logs survive replacement of both the store and collector.
kubectl -n bigdata rollout restart statefulset/loki
kubectl -n bigdata rollout status statefulset/loki --timeout=300s
kubectl -n bigdata rollout restart statefulset/alloy
kubectl -n bigdata rollout status statefulset/alloy --timeout=300s
kubectl -n bigdata exec -i jupyter-0 -c jupyter -- env TELEMETRY_MARKER="$marker" python - < validations/check-telemetry.py
