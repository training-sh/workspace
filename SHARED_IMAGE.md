# Shared image and selectable Kubernetes components

Reference: [Local-Setup.md](Local-Setup.md). This document records the container adaptation; the reference's host-install instructions are not container startup commands.

## Contract

Build one image, `dataeng-training:1.2.0`, and reuse it for the account workbench and compute/streaming services. Select the process using the Kubernetes container `args`. Installing software in the image does not start it or reserve its server RAM.

```yaml
containers:
  - name: jupyter
    image: dataeng-training:1.2.0
    args: [jupyter]
# A different pod uses the same image and args: [namenode], [trino], etc.
```

Every pod has separate configuration, resources and storage. Database, Polaris, SeaweedFS and monitoring images remain their purpose-built upstream images. The common artifact is the course's Hadoop/Hive/Spark/Kafka/Trino/Jupyter/Airflow software environment.

| Software | Version / runtime |
|---|---|
| Hadoop / HDFS / YARN / MapReduce | 3.3.6, Java 11 |
| Hive / Beeline / schema tools | 4.0.0, Java 11 |
| Spark / PySpark | 3.5.9, Scala 2.12, Java 11 |
| Kafka broker and CLI | 3.9.1, Java 11 |
| Iceberg | 1.10.0, Spark 3.5 / Scala 2.12 runtime and AWS bundle |
| Delta Lake | 3.3.2 |
| OpenLineage Spark | 1.53.0, Scala 2.12 JAR; Marquez 0.50.0 is a separate module |
| Spark Kafka / Avro | 3.5.9; Kafka client 3.4.1 matches the reference connector set |
| Spark Hadoop S3A | hadoop-aws 3.3.4 / AWS SDK bundle 1.12.262, matching Spark's bundled Hadoop |
| JDBC | MySQL 8.4.0; PostgreSQL 42.7.8 |
| JupyterLab | 4.4.9, shared Python 3.11 environment |
| Airflow | 3.3.1, shared Python 3.11 environment; installed with official constraints before notebook dependencies |
| Trino server and CLI | 476, its upstream Java 24 runtime |

The actual published Trino 476 artifact is used with its supported Java runtime; Java 11 cannot run that server. Airflow, notebooks and Spark share Python 3.11.17 and one `/opt/venv`; PySpark comes from Spark's bundled files. Kafka's Spark token-provider JAR is included even for plaintext lessons because the Spark connector can load its classes; it is not treated as a SASL-only optional dependency.

Large distributions come from digest-pinned official images. Connector downloads use TLS verification and upstream checksums, with an artifacts.lock recording SHA-256 values. No `curl -k`, host `/opt` copying, user-specific home paths or cluster credentials are needed to build. The initial validation target is Ubuntu/Linux AMD64; other architectures must be built and verified separately.

## Build once, start selected modules from the root

Prerequisites: [Ubuntu setup](UBUNTU_SETUP.md), running bigdata profile/context, Docker access without sudo and Python 3. The image is large because it includes every requested distribution; prepare/download it before class and allow ample disk space for Docker layers and Minikube's separate image store.

```bash
kubectl config use-context bigdata
bash build-image.sh
# Initial infrastructure from the existing course modules:
bash start.sh
# Workbench and Airflow:
bash start-components.sh jupyter airflow
bash validations/verify-components.sh
```

`build-image.sh` builds with Docker on the host, saves an archive under `.state/`, and streams it into the Docker driver's bigdata node using `ctr --namespace k8s.io images import`. This avoids buffering the entire large image in Minikube's loader. The archive is removed after successful import. Allow at least 50 GiB of free disk before building. Pods use IfNotPresent; they do not expect a private registry to exist. Repeat import for every additional Minikube node. For a cloud/shared cluster, push the same built artifact to your registry and change manifests to that registry reference or digest. Do not rebuild the artifact differently on each account's machine when distributing a validated class image.

Additional lesson choices:

```bash
bash start-components.sh hdfs
bash start-components.sh yarn
bash start-components.sh yarn hive
bash start-components.sh trino
bash start-components.sh spark
bash start-components.sh kafka
```

Do not start every optional module simultaneously on the initial 8 GiB Minikube allocation. Choose the lesson's components and pause others with the root stop script:

```bash
bash stop-components.sh airflow trino spark hive yarn hdfs
# Resume an existing module and its retained storage:
bash start-components.sh airflow
```

The stop script scales selected workloads to zero and retains PVCs and the notebook workspace. Stop only modules you actually deployed. Start order is explicit: infrastructure first; workbench/Airflow; HDFS before YARN; initialize the Hive schema before its servers; Trino and standalone Spark as selected lessons. Airflow startup ensures the workbench/mount is available too. Startup does not run host start-dfs/start-yarn scripts or create inter-container SSH keys.

Module commands and exercises: [Hadoop/HDFS/YARN](hadoop/README.md), [Hive](hive/README.md), [Spark](spark/README.md), [Trino](trino/README.md), [Kafka](kafka/README.md).

## Startup roles

| args[0] | Process selected |
|---|---|
| jupyter | JupyterLab with Python/PySpark kernel and terminal |
| airflow | One training standalone instance: API, scheduler, DAG processor and triggerer, using PostgreSQL and LocalExecutor |
| airflow-api / airflow-scheduler / airflow-dag-processor / airflow-triggerer | Individual Airflow components for a later split deployment |
| namenode / datanode | Individual HDFS daemons; one of each initially |
| resourcemanager / nodemanager / historyserver | Individual YARN / MapReduce daemons |
| hive-metastore / hiveserver2 / hive-schema | Hive servers or schema tool |
| spark-master / spark-worker / spark-history | Standalone Spark roles |
| driver / executor | Delegate to upstream Spark's Kubernetes entrypoint for future native Kubernetes submissions |
| kafka | ZooKeeper-mode broker using the existing dual-listener ConfigMap |
| trino | Coordinator with included worker, TPCH catalog and Java 24 |
| shell / exec | Interactive shell or an explicit command for exercises |

ZooKeeper remains its existing single-instance service; Kafka retains the previously tested internal/external listener rules and persistent volumes. Adding more brokers does not require another image. HDFS/YARN scaling needs per-node advertised addresses and capacity changes; the initial DataNode configuration is intentionally one node. Do not scale it blindly as a multi-node template.

## Notebook and DAG ownership

`~/workspace` is owned by your ordinary Ubuntu login account. Minikube's 9p mount exposes it at `/course-workspace` on the node. The root mount script carries 9p over the node's existing SSH connection, with loopback-only port 39090 on each side; no host firewall exception is needed. Jupyter sees it at `/workspace`; Airflow sees the same directory at `/workspace` and its `airflow/dags/` subdirectory at `/opt/airflow/dags`.

The mount presents UID/GID 1000; containers run as the image's team user with those IDs. The host Linux account can have a different name. This image user is unrelated to Kubernetes ServiceAccounts/RBAC or database accounts. Routine notebook, terminal and DAG editing requires no sudo, chmod 777 or user-specific /home path.

`start-components.sh` starts a background mount if needed and records its log/PID under ignored `.state/`. The mount must remain active while the pods use the share. To run/diagnose it interactively:

```bash
bash workspace-mount.sh
# In another terminal:
cat .state/workspace-mount.log
minikube -p bigdata ssh -- ls /course-workspace
```

The mount supervisor closes both its SSH tunnel and file server when either exits. If startup must restore the share, it replaces existing Jupyter/Airflow pods so they attach to the restored mount. To deliberately restart the workspace mount, pause those two modules first, stop the recorded mount PID, then run `bash start-components.sh jupyter airflow` again.

The files remain on the Ubuntu host after pods are replaced or the profile is deleted. Keep them in your course Git repository or back them up normally. Use one editor for a given file at a time to avoid conflicting saves. A Windows/laptop copy is not automatically synchronized with the VM's folder; use Jupyter download/upload, Git or your file-transfer workflow.

Image builds and component restarts do not rewrite `workspace/`. When updating the course source, retain accounts' edited notebooks/DAGs instead of copying fresh templates over them; commit or back up those edits first.

Cloud Kubernetes needs a PVC/shared storage or Git-based workflow instead of this Minikube-specific hostPath mount; the image and process-selection contract remain the same. The 9p share is for notebooks, DAGs and small teaching files, not production datasets or databases.

## Access and commands

Run `bash workbench-access.sh` from the root and leave it open. It forwards both UIs and retries after pod replacement. Equivalent manual commands are:

```bash
# Separate terminals, leave running:
kubectl -n bigdata port-forward --address=127.0.0.1 service/jupyter 8889:8888
kubectl -n bigdata port-forward --address=127.0.0.1 service/airflow 8087:8080
```

Host port 8889 allows an existing host Jupyter on 8888 to coexist with this workbench. If needed, choose free local ports with `JUPYTER_PORT=8890 AIRFLOW_PORT=8089 bash workbench-access.sh` and use those same ports in your SSH tunnel.

Jupyter: http://127.0.0.1:8889, token `team1234`. Airflow: http://127.0.0.1:8087, team/team1234. If using a remote VM, forward laptop ports 8889 and 8087 through SSH using the same pattern as the other module instructions.

With both `kubectl port-forward` commands running on the Ubuntu VM, run this in a laptop terminal:

```bash
ssh -N -L 8889:127.0.0.1:8889 -L 8087:127.0.0.1:8087 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"
```

Replace the generic account/host and add your SSH key option when needed. Open the same localhost browser URLs on the laptop. The loopback-only forwards avoid exposing the training credentials directly to the network.

In the JupyterLab terminal:

```bash
kafka-topics.sh --bootstrap-server kafka:9092 --list
hdfs dfs -ls /
yarn node -list
beeline -u jdbc:hive2://hiveserver2:10000/default -n team
trino --server http://trino:8080 --user team --execute 'SELECT 1'
spark-submit --version
```

Only commands for started services can connect. CLI binaries are always present. Jupyter runs inside the cluster, so it uses internal Service/broker addresses, including Kafka port 9092; no external listener tunnel is needed for notebook clients.

`notebooks/00-workbench.ipynb` demonstrates terminal-style commands and local PySpark. Its same kernel supports later lessons; you do not need a different notebook environment for every service. `airflow/dags/training_smoke.py` demonstrates an Airflow task running installed Hadoop/Kafka tools.

## Spark execution modes

Default local[2] is for small first lessons. Standalone Spark starts only through the spark component choice. For a YARN notebook session, start yarn, stop the prior Spark session, then select its master and reachable driver addresses explicitly:

```python
from pyspark.sql import SparkSession
spark = (SparkSession.builder.appName("yarn-notebook")
    .master("yarn")
    .config("spark.driver.host", "jupyter.bigdata.svc.cluster.local")
    .config("spark.driver.bindAddress", "0.0.0.0")
    .config("spark.driver.port", "7078")
    .config("spark.blockManager.port", "7079")
    .config("spark.executor.instances", "1")
    .config("spark.executor.cores", "1")
    .config("spark.executor.memory", "512m")
    .config("spark.executor.memoryOverhead", "384m")
    .config("spark.yarn.am.memory", "512m")
    .config("spark.yarn.am.memoryOverhead", "384m")
    .getOrCreate())
```

YARN launches application processes inside the NodeManager pod; it does not create Kubernetes executor pods. The NodeManager's 3 GiB limit includes its JVM and the 2 GiB advertised application capacity. Native Spark-on-Kubernetes uses its Kubernetes scheduler, driver/executor roles and separate RBAC; that is a later configuration lesson. Merely installing Spark or its executor entrypoint does not configure native Kubernetes submission.

Trino initially exposes a TPCH catalog for server validation. Hive/Polaris/S3 catalogs and distributed worker scaling are configured in their own lessons; installed connectors do not automatically create catalogs. Iceberg and Delta extensions are selected explicitly per Spark session to avoid forcing every exercise onto a single catalog.

Airflow has a dedicated airflow_metadata database in the existing PostgreSQL server, separate from Polaris. Hive has hive_metastore in MySQL, initialized only when empty. Neither uses or imports the old host Hive metadata. Training defaults and credentials are documented examples, not production authentication.

See [validations/VALIDATION.md](validations/VALIDATION.md) for executed checks and remaining limits. Upstream references: [Spark 3.5.9](https://spark.apache.org/docs/3.5.9/), [Trino 476 runtime requirements](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/installation/deployment.md), [Airflow quick start](https://airflow.apache.org/docs/apache-airflow/3.3.1/start.html), [Minikube mount](https://minikube.sigs.k8s.io/docs/commands/mount/).

All roles use `/opt/venv` and the same Python 3.11 interpreter. PySpark is imported from `/opt/spark/python` through a site-packages `.pth` file; it is never installed with pip. Drivers and executors use `/opt/venv/bin/python`. Airflow and notebook packages share one dependency set, checked with `pip check`. Connector JARs are copied directly into Spark to avoid a redundant temporary image layer.

The validated Python patch version is 3.11.17 from the digest-pinned base image; `image/shared-installed.lock` records the combined package inventory. Latest measured compressed image content is 3.73 GB (Docker disk usage 9.36 GB). Hive S3A uses Hadoop 3.3.6 / AWS SDK 1.12.367 in Hive only; Spark retains its own matching Hadoop 3.3.4 dependencies. See validations/VALIDATION.md for the checks performed on this revision.

Person data exercises and lineage: see [python/person/README.md](python/person/README.md) and [lineage/README.md](lineage/README.md). Run `bash run-person-lab.sh` from this root to start the required modules and verify Hive formats, Spark, Polaris/S3 Iceberg, both JDBC databases and Marquez lineage.
