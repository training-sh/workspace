# Deployment validation

Validated on 10 October 2026 using an Ubuntu AMD64 VM. The generic account procedure is in UBUNTU_SETUP.md and README.md. These results describe one working training installation, not validation of every Ubuntu host or cloud platform.

## Tested environment

| Component | Tested value |
|---|---|
| Host | Ubuntu 24.04.5 LTS, AMD64, four CPUs, approximately 16 GB RAM |
| Docker Engine | Existing installation, 29.1.3; ordinary-user Docker group access |
| Minikube | v1.39.0; profile `bigdata`; Docker driver |
| Kubernetes / kubectl | v1.35.0 / v1.35.0 |
| Workload runtime | containerd 2.3.4 inside the Minikube node |
| Allocation | Four CPUs, 8192 MiB memory |
| Namespace | `bigdata` |
| PostgreSQL | 16.15; digest pinned in postgresql.yaml |
| SeaweedFS | 4.47; digest pinned in seaweedfs.yaml |
| Polaris server / admin tool | 1.7.0 / 1.7.0 |
| Adminer | Deployed using the fixed digest in adminer.yaml |

Resolved Polaris image identities from the running/completed pods:

```text
apache/polaris@sha256:3495f67f38cca33892a045f7dd3f46eb52387f0fd52d4145538a772fd8aedad7
apache/polaris-admin-tool@sha256:3d8a24cea57aef3b71a0d7b09e5d2278d01e7e1b30071bf6648f2a6953322cca
```

Polaris manifests retain the requested `1.7.0` tags; the digests above record what was actually tested. Editing a completed Job's image creates an immutable-template conflict, so any future change to its image must be handled as an explicit bootstrap maintenance operation.

## Results

| Check | Result |
|---|---|
| User-local tool installation and checksum verification | Passed; neither tool installation required sudo |
| Ready Kubernetes node and containerd runtime | Passed |
| Owner administrative access | `kubectl auth can-i '*' '*' --all-namespaces` returned `yes` without sudo |
| Manifest API validation | All seven manifest files passed server-side dry-run |
| Shell syntax | Startup and verification scripts checked with Bash |
| PostgreSQL Service DNS and authenticated SQL | Passed; database `polaris`, user `team` |
| Persistent volume provisioning | PostgreSQL 5 GiB and SeaweedFS 10 GiB claims Bound |
| SeaweedFS authentication | Signed object upload/download passed; incorrect secret returned HTTP 403 |
| Polaris bootstrap | Job completed successfully; completed Job retained |
| Polaris readiness and OAuth | Passed |
| Catalog configuration | `training` created with internal SeaweedFS S3 endpoints and matched storage prefix |
| Polaris-to-SeaweedFS integration | Created namespace `training_check` and table `storage_check`; read its metadata file directly through signed S3 and matched the table UUID |
| Storage pod replacement | Passed read-only checks; no catalog, namespace, table or S3 object recreated |
| Minikube stop/start | Passed read-only checks after DNS/application recovery |
| Repeat root startup | `WITH_ADMINER=true bash start.sh` succeeded with existing resources and completed bootstrap Job |
| Adminer | Deployment Ready; HTTP startup/readiness probes passed |

The same table UUID persisted across storage pod replacement and cluster stop/start:

```text
77637f64-8f1f-4c5b-a432-69d0f2d68547
```

## Corrections discovered during deployment

Polaris's requested insecure-storage setting must use its exact quoted feature name. Enabling it explicitly in 1.7.0 also requires the documented education-only production-readiness override. Both settings are now explicit JVM properties.

The catalog's allowed prefix must agree with the default storage base for this lab. Both now use `s3://warehouse/iceberg`, and actual namespace/table creation verified that choice.

Cluster resume starts workloads together while DNS recovers. Polaris initially failed when resolving PostgreSQL too early. A server initContainer now waits for an authenticated SQL connection before launching the server. Verification waits for application readiness and reports port-forward diagnostics on failure.

## Existing host applications

The older Docker data-platform training stack and Compose PostgreSQL/SeaweedFS/Polaris/Adminer containers were stopped to free memory. Their containers and volumes were preserved. Unrelated Odoo applications and their databases continued running. The exact list of stopped container names was saved privately on the host in `~/workspace-operations/stopped-containers.txt`.

If restoring that old stack later, first stop Minikube and terminate course port-forwards, then review the saved names before starting them:

```bash
minikube stop -p bigdata
cat "$HOME/workspace-operations/stopped-containers.txt"
while IFS= read -r container; do docker start "$container"; done \
  < "$HOME/workspace-operations/stopped-containers.txt"
```

This is operational recovery for the validation host, not a required account setup step.

## Limits

Fresh Docker package installation was documented but not repeated on a host that already had working Docker. The initial applications and selected AMD64 image references were tested; ARM64, multi-node and cloud deployment were not tested. Full backup/restore rehearsal, browser login to Adminer/SeaweedFS admin, and compute-engine queries remain later exercises. The empty Iceberg table verifies metadata integration; Spark, Trino, Hadoop, Hive and Airflow remain deferred. Kafka and MySQL were added in the subsequent stage below.

Services remain ClusterIP. Port-forwards are started by the account's terminal commands; no public endpoint or persistent background forwarding service was installed. Minikube storage provides local lab persistence, not high availability. Course credentials are intentionally the public samples supplied for this education setup.

## MySQL and Kafka stage

Added and tested on the same Ubuntu training VM on 10 October 2026. Scope was MySQL and Kafka only; no Hadoop, Hive, Spark, Trino or Airflow modules were deployed and no Polaris credentials were changed.

| Component | Deployed configuration |
|---|---|
| MySQL | 8.4.11, one StatefulSet, 5 GiB PVC; `training` database; `team` / `team1234`; local root account password `root1234` |
| ZooKeeper | 3.9.3, one standalone StatefulSet, 1 GiB PVC |
| Kafka | 3.9.1 in ZooKeeper mode; one broker baseline; 5 GiB PVC per broker |
| Client bootstrap | `kafka.bigdata.svc.cluster.local:9092` |
| Images | All three pinned to inspected existing-image digests in their manifests |

Verified:

- MySQL authenticated `team` SQL, table creation, row insertion/readback and root login. Incorrect application-user and root passwords are rejected.
- Kafka topic creation, acknowledged production and consumption from an independent temporary client pod using Service discovery and broker-advertised DNS.
- Scaling to two brokers: created a three-partition topic with replication factor 2; both broker IDs appeared in every partition's ISR; production and consumption succeeded. The temporary replication topic was deleted and the cluster returned to one broker.
- MySQL, ZooKeeper and Kafka pods were replaced. Read-only verification recovered the existing SQL row and Kafka message without recreating either. ZooKeeper topic ID remained `ou9f-HA0SjWFiOc0ls3bUQ`.
- Re-running `start-data.sh` succeeded with the existing data. All three new YAML files passed server-side dry-run; the root startup and verification scripts passed Bash syntax checks.
- Existing PostgreSQL, SeaweedFS, Polaris and Adminer pods remained ready.

One additional `data-kafka-1` PVC remains from the scaling test, following StatefulSet's data-retention behaviour. No second broker is running; the retained claim can be reused when scaling up. Old Docker Kafka, ZooKeeper and MySQL volumes were neither imported nor deleted.

The simultaneous replacement test briefly caused Kafka to retry registration while an earlier ZooKeeper session expired (`NodeExists`); it recovered automatically and the persistence checks passed. Wait for readiness rather than assuming all services recover at exactly the same moment.

A ZooKeeper ensemble, automatic replica reassignment, workload queries from Spark/Trino, MySQL backup/restore and another whole-profile stop/start with the new modules remain outside this stage. External listeners were added in the following stage. The tested two-broker configuration is on one Minikube node and is not host-level high availability.

## Kafka internal/external listener stage

Tested on 10 October 2026. INTERNAL remains port 9092 with Kubernetes broker DNS; EXTERNAL binds 9093 and advertises loopback ports 19092 plus broker ordinal. Root `kafka-access.sh` maintains one forward per broker. Host-network Kafka CLI containers ran outside Kubernetes to exercise the host endpoint.

- Single-broker metadata advertised only `127.0.0.1:19092`; host production and internal consumption passed.
- Replaced kafka-0 with forwarding active. The helper recovered, and the external consumer read the persisted record. Brief client connection warnings occurred while forwarding reconnected; no record was lost.
- Scaled to two brokers. External discovery reported both `127.0.0.1:19092` and `127.0.0.1:19093`, without cluster DNS. Production bootstrapped through broker 1's forwarded port and consumption through broker 0's forwarded port passed.
- Three partitions with replication factor 2 had both broker IDs in ISR and leaders on both brokers, demonstrating reachable advertised endpoints beyond bootstrap.
- Independent in-cluster client and MySQL read-only regression verification passed. Temporary listener-test topics were deleted, forwards stopped and the broker count restored to one. Existing training-check topic ID and message remained intact.

SSH-tunnel commands are documented but laptop end-to-end client execution was not tested. Direct LAN/public endpoints and Jupyter remain outside this stage. The extra broker PVC remains available for future scaling exercises.

## Monitoring and tracing stage

Deployed on 10 October 2026: Prometheus 3.13.4, Grafana 13.2.0 and Jaeger 2.22.0, fixed by their observed image digests in the manifests. Each has one StatefulSet replica in the existing cluster and its own PVC. No additional cluster or replicated monitoring backend was created.

Verified all four scrape targets healthy: Prometheus, Grafana, Jaeger and Kubernetes cAdvisor. Prometheus returned Kafka pod CPU counters and memory working-set data. Grafana authenticated team/team1234, its Prometheus datasource health check passed, and its provisioned performance dashboard was accessible through the API. A real OTLP/HTTP span was sent and retrieved through Jaeger's trace API.

Replaced all three monitoring pods. The original trace `eb7f9be5ddce4b3a9b81c1590f0126a7` remained queryable without reingestion; Prometheus returned historical Kafka memory data from before replacement. Dashboard and datasource checks passed again. All application pods remained Ready afterwards.

The tested Jaeger release does not implement the legacy service-list endpoint used by Grafana's built-in Jaeger datasource health check. That datasource was removed; Jaeger's native UI supplies trace search. Ordinary application logs are not ingested by Jaeger. Application instrumentation, specialized Kafka/database exporters, Ubuntu host-wide metrics, Loki and Jupyter remain future work.

Post-deployment snapshot: Minikube Docker container used 2.698 GiB of its 8 GiB limit; whole VM used 8.3 GiB with 7.3 GiB available. These are instantaneous measurements including all existing workloads, not steady-state or peak guarantees. Monitoring requests total 640 MiB and limits total 2304 MiB; PVC requests total 12 GiB.

## Shared image, workbench and selectable compute stage

Tested on 10 October 2026 on the same Ubuntu AMD64 profile. Reference: Local-Setup.md; implementation and commands: SHARED_IMAGE.md. Built `dataeng-training:1.0.0` with Hadoop 3.3.6, Hive 4.0.0, Spark 3.5.9, Kafka 3.9.1, Trino 476, JupyterLab 4.4.9 and Airflow 3.3.1. Trino uses its Java 24 runtime; the Hadoop/Hive/Spark/Kafka roles use Java 11. Both Python environments passed pip check; inventories and connector hashes are recorded under image/.

Observed final Docker image ID: `7eba295d97953f87b1606307b1bf92e265d54f324fe2560f52de46988eedd67e`. The running Jupyter, Airflow and Kafka pods all reported the same CRI image ID: `sha256:2f69a3e55b5b5329c9c63b8fb397aab09aac7d50c935bf2658ee616e1255dc5f`. Docker reported about 9.6 GB disk usage and 3.81 GB content size. This is a local built artifact; no registry publication was performed.

Executed checks:

- Authenticated Jupyter API, terminal creation/deletion and actual execution of notebooks/00-workbench.ipynb using its Python/PySpark kernel.
- Spark Kafka batch production/consumption, Delta 3.3.2 write/read and Iceberg 1.10.0 table creation/insert/read. Local Delta/Iceberg paths used explicit file URIs. These checks passed again on the final image.
- Airflow team/team1234 authentication, host-shared DAG parsing, scheduler/LocalExecutor execution and successful Hadoop/Kafka CLI task. Airflow uses its dedicated PostgreSQL database. Successful runs included `verify-1791624234` and, after workspace recovery and Airflow replacement, `verify-1791624517`.
- Host-to-pod and pod-to-host file writes as UID/GID 1000, file retention after Jupyter replacement, and recovery after stopping/replacing the mount and workbench processes. The share runs over loopback-only SSH forwarding, without a host firewall exception.
- HDFS upload/read and recovery of `/user/team/common-image-check.txt` after NameNode/DataNode replacement, without reformatting. YARN node registration and a complete MapReduce Pi job passed (`job_1791623478549_0001`).
- Distributed Spark DataFrame and Python execution on YARN. Standalone Spark master/worker execution also passed, including a repeat on the final image.
- Hive schema initialization and version check against MySQL as team; HiveServer2 database/table creation, insert and MapReduce count returned 2. Both Hive pods were replaced; the retained table still returned 2 without recreating metadata or data.
- Trino TPCH count returned 25. Its readiness check waits until server initialization finishes; query execution passed again on the final image.
- Kafka moved to the shared image while retaining its ConfigMap, dual listeners and PVCs. Independent in-cluster consumption recovered the original training-check topic ID and message. External/internal exchange, forwarding recovery after broker replacement and two-broker replication/ISR checks passed. The broker count was restored to one. Final-image broker replacement and read-only MySQL/Kafka verification passed again.
- Bash syntax checks and Kubernetes server-side dry-run passed for all new workload manifests. Workstation SSH tunnels reached Jupyter's authenticated API and Airflow's authenticated API, healthy scheduler endpoint and HTTP 200 UI. Existing host Jupyter remained on 8888; the Kubernetes workbench uses host port 8889, with Airflow on 8087.

Implementation corrections found during validation: Trino's relocated Java path, writable Airflow password initialization, Kafka's JVM log directory, automatic Service environment-variable collisions with Spark, Spark's pod bind address, YARN's explicit teaching queue, the history service bind address and CLI loading of the generated Hadoop configuration. These fixes are included in the source and final image/manifests.

The initial Minikube image-loader attempt exhausted host memory and restarted several existing services. It was stopped; the final build script saves an archive and streams it into containerd instead. Imports then completed with stable memory, and subsequent application/data checks passed. Prepare the large artifact before class; do not use the earlier memory-buffered loader for this image.

Final state: Jupyter and Airflow run alongside the existing databases, one Kafka broker/ZooKeeper, Polaris, SeaweedFS and monitoring. HDFS, YARN, Hive, Trino and standalone Spark remain deployed with replicas zero; their PVCs are retained for later lessons. Host installations and their data were not migrated or removed. Localhost workbench forwards were left running; the temporary workstation test tunnel was closed.

Final snapshot after the checks: Minikube used 3.953 GiB of its 8 GiB limit; the whole VM used about 9.3 GiB with 6.3 GiB available, and the root filesystem had 69 GiB free. These are instantaneous measurements, not peak guarantees. Starting every optional lesson module together is not the validated 8 GiB operating mode.

Not tested in this stage: ARM builds, cloud deployment/registry delivery, multi-node HDFS/YARN, native Spark-on-Kubernetes RBAC/submission, Spark history-service configuration, split/distributed Airflow execution, Trino Hive/Polaris catalogs, Spark S3/Polaris integration from the new workbench, and a whole-profile stop/start after adding these modules. The existing Polaris principal credentials remain unchanged. Common software availability does not automatically configure these later integrations.

## Shared Python environment revision ? 10 October 2026

Rebuilt and deployed `dataeng-training:1.0.0`, Docker image ID `9c305c85db33`; running Jupyter, Airflow and Kafka pods use image ID `sha256:f14430591deb5a14a29af7aba1bc8a1f2794039feec61217177c44958d6e7e66`. This revision supersedes the previous separate Python environments and image-size measurements.

All common-image roles now use Python 3.11.17 and `/opt/venv`. PySpark 3.5.9 imports from `/opt/spark/python/pyspark`, with no pip-installed PySpark distribution. Spark's generated driver/executor configuration selects `/opt/venv/bin/python`; the shared site-packages path also works in Airflow when PYTHONPATH is unset. Package inventory is `image/shared-installed.lock`. Connector JARs are copied directly into Spark, removing the redundant temporary COPY layer.

Passed: `pip check`, notebook authentication/terminal/kernel execution, Spark Kafka batch write/read, Delta and Iceberg checks, and Airflow DAG parsing/scheduling/task execution (run `verify-1791629769`). Separate standalone Spark driver/executor jobs passed Java and Python execution and verified the exact same `sys.version` and `/opt/venv` on executor and driver. Optional Spark pods were returned to replicas zero after verification. Other previously paused compute roles were not restarted for this revision.

Docker reports compressed content 3.41 GB and disk usage 8.69 GB, compared with 3.81 GB and 9.6 GB previously. The two component-specific Java runtimes remain: Java 11 for Hadoop/Spark and Java 24 for Trino 476.

## Person data and OpenLineage ? 10 October 2026

Built and deployed `dataeng-training:1.1.0` (Docker image `003680758d65`, running containerd image `sha256:fad5b667878a262088de8ba2c9a7e418d4d3711f355fb3af3009b5c10ba3dec8`). The image adds checksum-pinned OpenLineage Spark 1.53.0 / Scala 2.12 while retaining the single Python 3.11.17 `/opt/venv` and Spark's bundled PySpark. All nine active common-image roles report that same image ID. Compressed image content is 3.45 GB, Docker disk usage 8.77 GB.

`bash run-person-lab.sh` starts and leaves HDFS, Hive, Spark master/worker and lineage running alongside the existing Polaris, SeaweedFS, databases and other services. All active workload pods were Ready. YARN and Trino remain paused. At the final idle check, the Minikube container used 6.025 GiB of its 8 GiB limit; this is a snapshot, not a peak guarantee. The single-node CPU requests are fully allocated, so schema checks on reruns execute inside the existing metastore instead of launching an extra Job.

The final person run passed 16 checks, saved in `python/person/results.json`: three exact matching rows in CSV/JSON/ORC/Parquet on HDFS, a Hive managed table and four external tables with verified types, Spark metastore reads of that managed source, Polaris Iceberg Parquet and ORC copies, both JDBC write/read branches, independent S3 metadata/data-object verification, and the actual Hive/HDFS-to-S3 plus MySQL/PostgreSQL lineage edges. Native MySQL/PostgreSQL clients independently confirmed three rows in their final tables. Original Hive/HDFS source data is retained.

Marquez 0.50.0 API and web viewer use digest-pinned images with one replica each, PostgreSQL database `marquez`, no OpenSearch, and Recreate deployment strategy for this small node. UI HTTP 200 and its API proxy were verified. Lineage jobs survived collector replacement. Root `lineage-access.sh` exposes localhost 3000/5000, actively checks HTTP health and reconnects; automatic forwarding recovery was tested. SSH access from another machine is documented in `lineage/README.md`.

Corrections included Hive 4's non-ACID table translation (explicit `EXTERNAL=FALSE` on the dedicated sample), avoiding repeated schema Jobs at full scheduler capacity, disabling optional Polaris REST metrics reports for this lesson, and distinct JDBC table names to preserve both database graph branches. OpenLineage emitted nonfatal diagnostics for some auxiliary SQL/metadata plans; the required source-to-Iceberg and both database edges were verified. Native Hive SQL is not separately instrumented; this module captures Spark operations and their Hive/HDFS inputs.

Existing workbench regression checks also passed on the final image: authenticated notebook/terminal/kernel execution, Kafka batch write/read, Delta/Iceberg, `pip check`, and Airflow scheduler/LocalExecutor DAG run `verify-1791631929`. Untested: ARM/cloud deployment, large datasets, simultaneous account workloads and additional native Hive lineage integration. Existing Polaris bootstrap client credentials remain as recorded in the Secret; JDBC exercise credentials are team/team1234.

## Kafka / Iceberg Structured Streaming ? 10 October 2026

Built and imported `dataeng-training:1.1.1`, Docker image `ca0a03e9c7b18c1e058210aec1834da13578b450388911d714494efcaf1bd8a8`. All nine active shared-image pods are Ready and report containerd image `sha256:71656f416c92178176fedd899c4454d3d0ca540cb3223c8fb1c26377647f913f`. Compressed image content is 3.73 GB, Docker disk usage 9.36 GB. The single Python 3.11.17 `/opt/venv` and bundled Spark 3.5.9 PySpark remain. YARN and Trino remain paused.

`bash run-streaming-lab.sh` passed nine checks on the final configuration, run `1791634462978704736`, saved in `pyspark/streaming/results.json`. The matrix is Spark HiveCatalog + HDFS, Spark HiveCatalog + SeaweedFS S3, and Polaris REST catalog + SeaweedFS S3. Each uses a dedicated three-partition / one-replica Kafka topic and an Iceberg v2 table partitioned by city. Native Structured Streaming ingests JSON records into Iceberg; a second native streaming query reads Iceberg append snapshots into a Parquet readback sink.

Initial ingestion verifies IDs 1?3, every field and physical data files. The script replaces Jupyter through a StatefulSet rollout and waits for readiness, then a new Spark driver publishes IDs 4?6 and resumes both sinks from persistent checkpoints. All tables and readback sinks contain exactly six matching rows. Another independent driver runs with no new input and verifies six unchanged rows, with no missing or duplicate records. Hive Metastore's persisted metadata locations are checked independently through MySQL; S3 metadata JSON and actual HDFS/S3 data objects are checked. The final streaming log contains zero ERROR entries.

Fixed the issues exposed by these tests: Hive's missing S3 filesystem support (checksum-pinned Hadoop AWS 3.3.6 / AWS SDK 1.12.367 confined to Hive's libraries, and S3A endpoint/path-style settings), and incompatible HDFS checkpoints for S3FileIO streaming reads. Kafka ingestion checkpoints stay on HDFS; Iceberg read checkpoints match the table FileIO, HDFS or S3A. Spark uses its separate Hadoop 3.3.4 dependencies for S3A checkpoints. OpenLineage's optional Iceberg metrics injector is disabled only in this exercise using its documented `spark.openlineage.vendors.iceberg.metricsReporterDisabled=true` workaround; lineage collection remains enabled.

The existing person exercise was rerun on 1.1.1 and passed all 16 checks: Hive managed/external format tables, Spark reads, Polaris Iceberg ORC/Parquet, JDBC write/read to both databases, direct S3 metadata/data validation and Marquez dataset edges. Original course data is retained. Streaming test topics/tables/checkpoints remain available for inspection; repeated runs create new dedicated datasets.

Scope: single-node Minikube, one Kafka broker, one Spark worker, small finite micro-batches with `availableNow`. This verifies Spark HiveCatalog access to Hive Metastore, not native HiveServer2 SQL execution against Iceberg. High-volume ingestion, broker/executor failure during an in-flight commit, Kafka retention loss, Iceberg overwrite/delete streaming snapshots, multi-account concurrency and cloud deployments are not validated by this exercise.

Final workbench regression also passed on 1.1.1: `pip check`, shared Python / bundled PySpark checks, authenticated Jupyter terminal and actual notebook kernel execution, Kafka batch write/read, Delta 3.3.2 and Iceberg 1.10.0, and Airflow team login / scheduler / LocalExecutor Hadoop-Kafka DAG run `verify-1791634841`. Marquez API independently listed eight jobs for `kafka_iceberg_streaming_validation` after the metrics-injector workaround; this confirms events arrived, without claiming full streaming graph completeness.

## Local log and metric telemetry ? 10 October 2026

Deployed checksum/digest-pinned Loki 3.7.0 and Alloy 1.20.1 as single-instance StatefulSets with persistent volumes (5 GiB and 1 GiB), plus the existing Grafana/Prometheus/Jaeger. Loki uses local filesystem/TSDB storage with 72-hour compactor retention. No hosted log destination is configured; Loki analytics and Alloy usage reporting are disabled. Memory limits are 512 MiB for Loki and 256 MiB for Alloy, with small Loki caches. CPU reservations for Jupyter, Airflow and Prometheus are 50m each, preserving their CPU limits, to fit the new collectors on the four-core node.

Alloy discovers bigdata pods and reads their container logs through namespace-scoped Kubernetes API RBAC. Five small file-log sidecars reuse `dataeng-training:1.1.1` and its single Python environment: Hive Metastore / HiveServer2 logs, standalone Spark executor stdout/stderr, Spark JVM driver logs in Jupyter, and Airflow task/DAG-processor log files. ConfigMaps enable native HDFS /prom and Spark master/worker PrometheusServlet metrics; Prometheus also scrapes Loki/Alloy. File-log forwarding dynamically discovers new executor/task logs. Grafana has a healthy Loki datasource and `Training centralized logs` dashboard; its actual datasource proxy query was tested.

`bash validations/verify-telemetry.sh` passed 16 checks, marker `telemetry-1791641374`, saved in `workspace/telemetry/results.json`. Verified actual distributed Spark driver/executor log markers, Hive/Airflow file markers, HDFS/Prometheus container markers, searchable logs from other running components, six actual native metric jobs, healthy scrape targets, Grafana provisioning/querying and preserved Hive lesson tables. The same checks passed after replacing both Loki and Alloy, demonstrating stored-log persistence and collection recovery. Independently confirmed the real successful Airflow DAG task logs for `verify-1791641846` were searchable through the file-log forwarder.

Streaming regression with telemetry active passed all nine cases, run `1791641504208182906`: HiveCatalog/HDFS, HiveCatalog/S3 and Polaris/S3, initial ingestion, Jupyter pod replacement / checkpoint recovery, and no-new-data replay. Workbench regression passed shared Python / bundled PySpark, pip consistency, notebook authentication/terminal/kernel, Kafka batch, Delta/Iceberg and the Airflow DAG. Existing monitoring verification passed native workload metrics and Jaeger OTLP trace ingestion/query, trace ID `23576b1baaff4b67b716579bbfe8918b`.

During HDFS restart, a Kubernetes pod-IP reverse-DNS check prevented DataNode registration. The training bootstrap disables `dfs.namenode.datanode.registration.ip-hostname-check` while retaining the DataNode Service hostname. HDFS subsequently left safe mode normally, with one registered DataNode and zero under-replicated blocks. Safe mode was not forcibly disabled and course data was retained.

All active workload pods are Ready and remain running. Final cluster snapshot: 6.621 GiB / 8 GiB (82.77%), with about 3.7 GiB available on the VM; this is not a measured peak guarantee. YARN and Trino remain paused. Grafana local forwarding on 3001 returned HTTP 200; Marquez retains 3000. Root start/verify/access/pause commands and generic account SSH tunnels are documented in `monitoring/TELEMETRY.md`.

Scope remains a single-node training deployment: no host-outside-Kubernetes log collector, high-availability ingestion, exhaustive log-loss testing, arbitrary notebook-output capture or automatic application tracing. Source-file storage and collector downtime can lose uncollected logs; centralized Loki retention does not impose a strict disk-size quota. Additional workloads can be discovered automatically, but their file logs/native application metrics need explicit configuration.

## Trino and Spark federation validation - 2026-10-10

Trino 476 now runs with MySQL, PostgreSQL, Hive, HMS Iceberg (HDFS and SeaweedFS S3) and Polaris REST/S3 catalogs. These use the existing shared image 1.1.1; no image rebuild was needed. Database connectors use team/team1234. Existing Polaris principal credentials are unchanged.

Full matrix passed twice: initial run `1791645837880340959`, then the documented root command `bash run-federation-lab.sh`, run `1791646291316865333` with Airflow, lineage and telemetry running. All 92 checks passed: six Trino seed write/reads, 30 directed Trino create/append/read transfers, six Spark reads/appends to Trino tables, six Spark seed write/reads, 30 directed Spark create/append/read transfers independently read by Trino, six Trino reads/appends to Spark tables, two six-store federated joins and six physical Iceberg data-location checks. Exact rows and duplicates were compared, not merely row counts.

`bash run-federation-formats.sh` also passed its fixture/person regression and all 15 format checks, run `1791646789576470053`. Trino writes and Spark appends CSV, JSON, ORC and Parquet on HDFS; Trino, native HiveServer2 and Spark native file readers confirm exact contents. The seven earlier Hive/Polaris lesson tables remain readable through Trino. Hive JSON required changing the dedicated lesson SerDe to `org.apache.hive.hcatalog.data.JsonSerDe`, persisted in the person lab code. CSV Hive columns are VARCHAR; the assertion converts IDs to integers. Spark JSON is read through its native file reader rather than Hive SerDe deserialization.

The notebook's five-store SQL example executed against the actual run tables and returned all four expected rows. Trino CLI SHOW CATALOGS and a real Ubuntu-host HTTP query through localhost:8089 both passed. Client nextUri values retained the host-forwarded endpoint. Root `trino-access.sh` remains running; a pre-existing service on 8088 was retained.

HDFS access initially failed because Trino proxy impersonation was not configured on NameNode. The catalog now uses the shared team identity without impersonation. Trino reserves 50m CPU and the idle Adminer UI 10m; their limits remain unchanged. ConfigMap manifest hashing restarts Trino when its catalog templates change.

The expanded Minikube Docker container was resized in place from 8 to 10 GiB; versions.env and saved profile configuration reflect 10240 MiB. No cluster deletion, PVC removal or data reset occurred. The latest health snapshot has 23 active pods Ready and 7.57GiB / 10GiB used, with YARN still paused and Trino running. About 8.4 GiB was observed during the full simultaneous workload; this is an observed snapshot, not a guaranteed peak. Prometheus had ten targets UP; Airflow, Marquez and Grafana health endpoints returned HTTP 200; Loki contained Trino pod logs. No new container restarts were observed in the final snapshot.

Evidence: pyspark/federation/results.json, formats-results.json, access-results.json and health-results.json. The person regression evidence is python/person/results.json. These checks cover small batch datasets, shared create/append/read, federation and storage placement. They do not assert atomic cross-store transactions, arbitrary data-type mappings, concurrent writers or production load. Existing optional OpenLineage plan-extraction warnings remain; this test does not certify every federation job's lineage graph.
