#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(kubectl config current-context)" == bigdata ]] || { echo 'Select context bigdata first'; exit 1; }
[[ $# -gt 0 ]] || set -- jupyter airflow
wait_app() {
  case "$1" in
    namenode|datanode|hive-metastore|hiveserver2|spark-master|spark-worker|jupyter|resourcemanager|nodemanager|historyserver|kafka)
      checksum=$(sha256sum monitoring/telemetry-config.yaml | cut -d ' ' -f1)
      kubectl -n bigdata patch "statefulset/$1" --type=merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"training.telemetry-sha\":\"$checksum\"}}}}}" ;;
  esac
  kubectl -n bigdata rollout status "statefulset/$1" --timeout=900s
}
hdfs_cmd() { kubectl -n bigdata exec namenode-0 -- bash -ec 'source /opt/training/env.sh; exec hdfs "$@"' -- "$@"; }
start_hdfs() {
  kubectl apply -f hadoop/hdfs.yaml
  wait_app namenode; wait_app datanode
  hdfs_cmd dfsadmin -safemode wait
  hdfs_cmd dfs -mkdir -p /user/team /tmp/hive /user/hive/warehouse /user/hive/external /spark-history
  hdfs_cmd dfs -chmod 1777 /tmp /tmp/hive
}
kubectl apply -f monitoring/telemetry-config.yaml
for component in "$@"; do
  case "$component" in
    headlamp)
      minikube -p bigdata addons enable headlamp
      kubectl apply -f platform/headlamp-access.yaml
      kubectl -n headlamp rollout status deployment/headlamp --timeout=300s ;;
    polaris-console)
      minikube -p bigdata image ls | grep -q 'polaris-console:db1f8ea' || bash polaris/console/build-console.sh
      kubectl apply -f polaris/console.yaml
      kubectl -n bigdata rollout status deployment/polaris-console --timeout=300s ;;
    jupyter)
      if ! minikube -p bigdata ssh -- 'test -f /course-workspace/.training-workspace' < /dev/null >/dev/null 2>&1; then
        mkdir -p .state
        if [[ -f .state/workspace-mount.pid ]]; then
          previous_pid=$(cat .state/workspace-mount.pid)
          if [[ "$previous_pid" =~ ^[0-9]+$ ]] && [[ "$(readlink "/proc/$previous_pid/cwd" 2>/dev/null || true)" == "$PWD" ]] && [[ "$(ps -p "$previous_pid" -o args=)" == 'bash workspace-mount.sh' ]]; then
            kill "$previous_pid" 2>/dev/null || true
            sleep 2
          fi
        fi
        nohup bash workspace-mount.sh > .state/workspace-mount.log 2>&1 < /dev/null & echo "$!" > .state/workspace-mount.pid
        mounted=false
        for attempt in $(seq 1 60); do
          if minikube -p bigdata ssh -- 'test -f /course-workspace/.training-workspace' < /dev/null >/dev/null 2>&1; then mounted=true; break; fi
          sleep 1
        done
        [[ "$mounted" == true ]] || { cat .state/workspace-mount.log; exit 1; }
        # Existing pods may be bound to an empty or expired mount. Reattach them.
        kubectl -n bigdata delete pod jupyter-0 airflow-0 --ignore-not-found --wait=true
      fi
      kubectl apply -f jupyter/jupyter.yaml; wait_app jupyter ;;
    airflow)
      # Airflow and the workbench share host-owned DAGs/notebooks.
      bash ./start-components.sh jupyter
      # Dedicated metadata database; retain the existing Polaris database.
      kubectl -n bigdata exec postgres-0 -- sh -ec 'export PGPASSWORD="$POSTGRES_PASSWORD"; if ! psql -h postgres -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datname='\''airflow_metadata'\''" | grep -qx airflow_metadata; then createdb -h postgres -U "$POSTGRES_USER" airflow_metadata; fi'
      kubectl apply -f airflow/airflow.yaml; wait_app airflow ;;
    hdfs) start_hdfs ;;
    yarn) start_hdfs; kubectl apply -f hadoop/yarn.yaml; for app in resourcemanager nodemanager historyserver; do wait_app "$app"; done ;;
    hive)
      start_hdfs
      kubectl -n bigdata exec mysql-0 -- sh -ec 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=TCP -h127.0.0.1 -uroot -e "CREATE DATABASE IF NOT EXISTS hive_metastore; GRANT ALL ON hive_metastore.* TO '\''team'\''@'\''%'\'';"'
      # A running metastore can validate its schema in place. This avoids needing
      # extra scheduler capacity for a new schema Job on every lesson rerun.
      if [[ "$(kubectl -n bigdata get pod hive-metastore-0 -o 'jsonpath={.status.containerStatuses[0].ready}' 2>/dev/null || true)" == true ]]; then
        kubectl -n bigdata exec hive-metastore-0 -- schematool -dbType mysql -info
      else
        # Job templates are immutable; replace only a completed earlier job.
        if kubectl -n bigdata get job hive-schema >/dev/null 2>&1; then
          kubectl -n bigdata wait --for=condition=complete job/hive-schema --timeout=900s
          kubectl -n bigdata delete job hive-schema
        fi
        kubectl apply -f hive/schema.yaml
        kubectl -n bigdata wait --for=condition=complete job/hive-schema --timeout=900s
      fi
      kubectl apply -f hive/hive.yaml
      wait_app hive-metastore; wait_app hiveserver2 ;;
    trino)
      kubectl apply -f trino/trino.yaml
      catalog_hash=$(sha256sum trino/trino.yaml | cut -d' ' -f1)
      kubectl -n bigdata patch statefulset trino --type=merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"training.catalog-sha\":\"$catalog_hash\"}}}}}"
      wait_app trino ;;
    spark) kubectl apply -f spark/spark.yaml; wait_app spark-master; wait_app spark-worker ;;
    lineage)
      kubectl -n bigdata exec postgres-0 -- sh -ec 'export PGPASSWORD="$POSTGRES_PASSWORD"; if ! psql -h postgres -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datname='\''marquez'\''" | grep -qx marquez; then createdb -h postgres -U "$POSTGRES_USER" marquez; fi'
      kubectl apply -f lineage/marquez.yaml
      kubectl -n bigdata rollout status deployment/marquez --timeout=900s
      kubectl -n bigdata rollout status deployment/marquez-web --timeout=900s ;;
    kafka) kubectl apply -f kafka/zookeeper.yaml; wait_app zookeeper; kubectl apply -f kafka/kafka.yaml; wait_app kafka
      kubectl apply -f monitoring/kafka-exporter.yaml
      kubectl -n bigdata rollout status deployment/kafka-exporter --timeout=300s ;;
    *) echo "Choose: jupyter airflow hdfs yarn hive trino spark kafka lineage headlamp polaris-console"; exit 2 ;;
  esac
done
kubectl -n bigdata get pods
