# Logs and metrics

Follow [monitoring notebook](../00-setup/02-monitoring.ipynb) before the compute notebooks. The Ubuntu desktop inside Guacamole uses the local browser URLs; no laptop tunnel is needed.

| Source | Logs in Loki | Metrics in Prometheus |
|---|---|---|
| bigdata workloads | Container stdout/stderr through Alloy | cAdvisor CPU/memory |
| Headlamp | Container logs, standard app-label fallback | cAdvisor CPU/memory; metrics-server also supplies UI live usage |
| HDFS | Daemon logs | Native NameNode/DataNode /prom endpoints |
| YARN | Daemon logs and NodeManager application stdout/stderr/syslog | ResourceManager, NodeManager and HistoryServer JVM/JMX |
| Hive | Container logs and /tmp/team/hive.log | Metastore and HiveServer2 JVM/JMX |
| Spark | Daemon logs, Jupyter driver Log4j file, worker executor files | Native master/worker Prometheus endpoints |
| Kafka | Broker container logs | JVM/JMX on port 9404 |
| ZooKeeper | Container logs | Native/JVM Prometheus provider on port 7000 plus cAdvisor CPU/memory |

The pinned shared image dataeng-training:1.2.0 includes Prometheus JMX agent 1.0.1. Only daemon entrypoints enable it; in-pod command-line clients do not inherit its listener and can run normally. Kafka/YARN/Hive metric Services are internal ClusterIP.

Ordinary Python prints from a kubectl exec driver are not container-main logs. The Spark notebook emits a driver Log4j marker and an executor stdout marker and verifies both file-log streams. Arbitrary host files and services outside these namespaces need a separate collector. Traces require explicit instrumentation; installing Jaeger does not instrument applications.

For logs use Grafana Explore with Loki and `{namespace="bigdata"}` or `{namespace="headlamp"}`. For one daemon use `{component="namenode"}`. The performance dashboard includes bigdata/Headlamp pod CPU/memory and JVM heap. Down targets are expected for paused or not-yet-deployed lessons.

Each setup notebook invokes [check-observability.py](../validations/check-observability.py). Its file-log and marker options check real application records rather than only startup logs. Stop/resume tests retain monitoring PVCs. Loki retains logs for 72 hours and Prometheus retains metrics for seven days with its configured size target; neither is a production high-availability archive.
