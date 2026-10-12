#!/usr/bin/env bash
set -euo pipefail
source /opt/training/env.sh
mkdir -p /tmp/hadoop-logs /tmp/hive-logs /tmp/hive-local
python3 /opt/training/render.py
role=${1:-jupyter}; shift || true
# Enable the agent only in daemon launch environments, not kubectl exec clients.
if [[ "${TRAINING_JMX_METRICS:-false}" == true ]]; then
  export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -javaagent:/opt/training/metrics/jmx_prometheus_javaagent-1.0.1.jar=9404:/etc/training-telemetry/jmx-exporter.yaml"
fi
case "$role" in
  jupyter) : "${JUPYTER_TOKEN:?Set JUPYTER_TOKEN}"; exec jupyter lab --config=/opt/training/jupyter_config.py "$@" ;;
  airflow|airflow-api|airflow-scheduler|airflow-dag-processor|airflow-triggerer)
    unset PYTHONPATH
    case "$role" in
      airflow) exec airflow standalone "$@" ;;
      airflow-api) exec airflow api-server "$@" ;;
      airflow-scheduler) exec airflow scheduler "$@" ;;
      airflow-dag-processor) exec airflow dag-processor "$@" ;;
      airflow-triggerer) exec airflow triggerer "$@" ;;
    esac ;;
  namenode)
    mkdir -p /data/namenode
    if [[ ! -f /data/namenode/current/VERSION ]]; then
      [[ -z "$(ls -A /data/namenode)" ]] || { echo 'Refusing to format a nonempty NameNode directory'; exit 1; }
      hdfs namenode -format -nonInteractive
    fi
    exec hdfs namenode "$@" ;;
  datanode) mkdir -p /data/datanode; exec hdfs datanode "$@" ;;
  resourcemanager) exec yarn resourcemanager "$@" ;;
  nodemanager) mkdir -p /data/yarn/local /data/yarn/log; exec yarn nodemanager "$@" ;;
  historyserver) exec mapred historyserver "$@" ;;
  hive-metastore) exec hive --service metastore "$@" ;;
  hiveserver2) exec hiveserver2 "$@" ;;
  hive-schema) exec schematool -dbType mysql "$@" ;;
  spark-master) exec /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master --host "${POD_IP:-$(hostname -i)}" --port 7077 --webui-port 8080 "$@" ;;
  spark-worker) mkdir -p "$SPARK_WORKER_DIR"; exec /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker --cores 1 --memory 1g spark://spark-master:7077 "$@" ;;
  spark-history) exec /opt/spark/bin/spark-class org.apache.spark.deploy.history.HistoryServer "$@" ;;
  driver|executor) exec /opt/training/spark-k8s-entrypoint.sh "$role" "$@" ;;
  kafka) exec bash /etc/kafka-training/start.sh "$@" ;;
  trino) export JAVA_HOME=/opt/java/trino; export PATH=$JAVA_HOME/bin:$PATH; exec /opt/trino/bin/launcher --etc-dir=/opt/training/conf/trino run "$@" ;;
  shell) exec /bin/bash "$@" ;;
  exec) exec "$@" ;;
  *) echo "Unknown component: $role" >&2; exit 2 ;;
esac
