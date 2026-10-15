# Grafana dashboards

On **aadhi**, open http://100.116.85.84:3001 while connected to Tailscale.
Login: **team / team1234**. This address belongs to aadhi, not the other machines.

| Grafana folder / dashboard | Dashboard YAML | Template/source |
|---|---|---|
| Training / Training workload performance | `monitoring/grafana.yaml` | Workspace CPU/memory and JVM overview |
| Training / Training centralized logs | `monitoring/grafana.yaml` | Workspace Loki logs |
| Tools / [Kafka](http://100.116.85.84:3001/d/training-kafka) | `monitoring/grafana-dashboard-kafka.yaml` | [7589 revision 5](https://grafana.com/grafana/dashboards/7589-kafka-exporter-overview/), adapted for Grafana 13 with JVM/resource metrics and logs |
| Tools / [Spark](http://100.116.85.84:3001/d/training-spark) | `monitoring/grafana-dashboard-spark.yaml` | `native-spark-standalone-v2`, built for the installed Spark [master/worker and JVM metrics](https://spark.apache.org/docs/3.5.7/monitoring.html#metrics) |
| Tools / [Trino](http://100.116.85.84:3001/d/training-trino) | `monitoring/grafana-dashboard-trino.yaml` | `native-trino-476-v1`, matched to Trino 476's native [OpenMetrics endpoint](https://trino.io/docs/current/admin/openmetrics.html) |
| Tools / [HDFS](http://100.116.85.84:3001/d/training-hdfs) | `monitoring/grafana-dashboard-hdfs.yaml` | `native-hdfs-v1`, matched to NameNode/DataNode `/prom` metrics and the [Hadoop metrics reference](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-common/Metrics.html) |

| Tools / [YARN](http://100.116.85.84:3001/d/training-yarn) | `monitoring/grafana-dashboard-yarn.yaml` | `native-yarn-v1`, matched to existing ResourceManager/NodeManager/HistoryServer JMX metrics |

## Update and start

Run in the workspace on each already configured machine, with Minikube running:

```bash
git pull                          # after these changes are committed and published
kubectl config use-context bigdata
bash stop-components.sh yarn       # 8 GiB profile: finish YARN jobs first
bash start-monitoring.sh           # applies dashboard ConfigMaps, scraping and Grafana
bash start-components.sh hdfs spark kafka trino
bash monitoring-access.sh          # keep running for this machine's local browser
```

For a local browser on that machine, open http://127.0.0.1:3001.
Monitoring starts first so it collects startup logs. Existing workloads/data are retained;
configuration changes can restart affected pods. Apply the JVM update between exercises:
`start-components.sh spark` restarts the master/worker once when telemetry changes, interrupting active Spark jobs.
Rerunning it with unchanged configuration keeps the existing Spark pods running.
No image rebuild or manual dashboard import.
`git pull` alone updates files; the commands above apply them to Kubernetes.

## What to look at

- **Kafka:** broker/exporter health, topics, message rates, partitions, consumer lag, JVM, CPU/memory and logs. `monitoring/kafka-exporter.yaml` supplies topic/group metrics. Consumer panels need a group with committed offsets. The validation topic/group is `grafana-dashboard-check`.
- **Spark:** 32 panels covering master/worker health, alive/registered workers, running/waiting applications, executors, allocated/free cores and memory, utilization, pod CPU/memory, JVM heap/non-heap, memory pools, buffers, garbage collection, and master/worker/driver/executor logs. Idle application/executor counts of zero are normal. Driver/executor logs appear after running a Spark workload; widen the time range if needed.
- JVM collection is enabled in `monitoring/telemetry-config.yaml` with `*.source.jvm.class=org.apache.spark.metrics.source.JvmSource`. The existing startup helper copies this shared configuration into Spark; Prometheus scrapes both daemons through the existing targets. The JVM panels show the master and worker JVMs, including while idle; driver/executor JVM scraping is a separate application instrumentation step.
- **Trino:** 30 panels for node/scrape health, query totals/states/rates, failures, drivers/tasks, memory reservations, pod CPU/memory, input throughput, query duration, garbage collection, server logs and query-ID timelines. Uses the existing single-node Trino (coordinator also executes tasks); no exporter or image rebuild. The native `/metrics` scrape uses username `team`, configured in `monitoring/prometheus.yaml`.
- Trino duration percentiles need at least one completed query, and timelines appear after queries run. Query totals/percentiles are since server startup, while rate panels show recent activity. Query timelines are not a full SQL audit archive.
- Trino's **Finished queries total** includes success, failure and cancellation. Validation deliberately creates failed/cancelled queries, so nonzero failure totals after testing are expected.
- On the 8 GiB profile, run compute lessons in groups: YARN plus Spark/Kafka/Trino can exhaust cluster memory. Finish any YARN jobs before pausing it with `bash stop-components.sh yarn`; resume with `bash start-components.sh yarn` for its lesson. HDFS can stay running.
- **HDFS:** 30 panels for NameNode/DataNode health, live/dead nodes, namespace/file/block counts, missing/corrupt/under-replicated blocks, storage, I/O and RPC rates/latency, pending replication/deletion, JVM heap/non-heap/GC, pod CPU/memory and both daemon logs. Uses existing native metrics and Alloy; no additional exporter. Zero corruption/missing blocks is healthy. Storage capacity/non-HDFS usage reflects the shared filesystem, not an isolated PVC quota.

Generate a small Trino example (result: 25):

```bash
kubectl -n bigdata exec trino-0 -- trino --server http://localhost:8080 --user team --execute 'SELECT count(*) FROM tpch.tiny.nation'
```
- Spark uses the existing standalone cluster inside Kubernetes and native metric endpoints; no new Spark installation/exporter. Per-job SQL, stage, task and shuffle profiling remains in the Spark application UI; it is not supplied by the master/worker endpoints.

Dashboards provision automatically from ConfigMaps mounted by `monitoring/grafana.yaml`;
folder definitions are in `monitoring/grafana-dashboard-providers.yaml`.
Select **Last 30 minutes** and refresh after starting a workload.

## Verification

Kafka: 14 panels tested in browser and via Grafana; 120 messages produced/consumed,
consumer lag verified at 0 → 120 → 0, and fresh broker logs verified in Loki.
Spark: all 32 panels tested through Grafana and in a browser; distributed RDD/SQL
results checked, workload metrics returned to idle, and fresh driver/executor logs found.
Grafana has a 768 MiB memory limit and a 512 MiB Go memory target; Spark log panels show up to 200 lines per query.

HDFS: 54 functional checks and all 30 browser panels passed. A temporary 1 MiB file
was written/read with matching SHA-256, I/O counters and fresh logs verified, then deleted.
YARN: 32 panels cover application states, scheduler memory/vcores/containers, NodeManager
container states, all three daemon JVMs, CPU/memory and four log panels including application logs.
Root QueueMetrics is selected once to avoid double counting parent/child queues.
Counters reset when daemons restart. Idle counts of zero are normal; application logs need a job.
HistoryServer JVM/health/logs are included; per-job task details remain in its native web UI.
A real Pi MapReduce job succeeded (3.148),
with active/idle metrics, completion counters, HistoryServer job and Loki application logs verified.

For the YARN lesson on the 8 GiB profile, finish Trino queries and use this order:

```bash
bash stop-components.sh trino
bash start-monitoring.sh
bash start-components.sh yarn       # starts HDFS first
bash monitoring-access.sh
```

Small YARN example (reduced memory for this lab):

```bash
kubectl -n bigdata exec resourcemanager-0 -- bash -ec 'hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar pi -Dmapreduce.map.memory.mb=256 -Dmapreduce.map.java.opts=-Xmx128m -Dmapreduce.reduce.memory.mb=256 -Dmapreduce.reduce.java.opts=-Xmx128m -Dyarn.app.mapreduce.am.resource.mb=256 -Dyarn.app.mapreduce.am.command-opts=-Xmx128m 1 1000'
```

On aadhi, YARN is now running and Trino is paused as agreed. To return to Trino after
finishing YARN jobs: `bash stop-components.sh yarn && bash start-components.sh trino`.
Do not run large Spark/Kafka workloads alongside YARN on the 8 GiB profile.

Dashboard YAML already contains the complete JSON; startup does not run Python builders or test scripts.
The five `validations/build-*-dashboard.py` files are maintenance sources for regenerating
the templates. Generated test evidence and local test utilities are excluded from Git.
