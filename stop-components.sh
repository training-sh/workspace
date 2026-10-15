#!/usr/bin/env bash
set -euo pipefail
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
for component in "$@"; do
  case "$component" in
    lineage) kubectl -n bigdata scale deployment/marquez deployment/marquez-web --replicas=0; continue ;;
    jupyter|airflow|trino) apps="$component" ;;
    hdfs) apps='namenode datanode' ;;
    yarn) apps='resourcemanager nodemanager historyserver' ;;
    hive) apps='hiveserver2 hive-metastore' ;;
    spark) apps='spark-worker spark-master' ;;
    kafka)
      if kubectl -n bigdata get deployment/kafka-exporter >/dev/null 2>&1; then
        kubectl -n bigdata scale deployment/kafka-exporter --replicas=0
      fi
      apps='kafka zookeeper' ;;
    *) echo 'Choose: jupyter airflow hdfs yarn hive trino spark kafka lineage'; exit 2 ;;
  esac
  for app in $apps; do
    if kubectl -n bigdata get "statefulset/$app" >/dev/null 2>&1; then
      kubectl -n bigdata scale "statefulset/$app" --replicas=0
      kubectl -n bigdata wait --for=delete pod -l "app=$app" --timeout=180s
    fi
  done
done
# Keep PVCs and the host workspace. Resume using start-components.sh.
