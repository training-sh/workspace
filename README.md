# Big data workspace

Repository: [training-sh/workspace](https://github.com/training-sh/workspace).

Place this directory at `~/workspace` or another directory you own. `WORKSPACE_HOME` defaults to `$HOME/workspace`; notebook 00 saves your chosen path and `~/.local/bin` in `.bashrc`. One-time Docker installation and group access are handled there; routine Docker, Minikube and kubectl commands run without sudo. Run shell commands on Ubuntu, using the same ordinary login account for Docker, Minikube and kubectl.

Begin with the illustrated [Kubernetes introduction notebook](00-kubernetes-introduction/00-kubernetes-introduction.ipynb): Docker/Compose comparisons, architecture, Pods, networking, storage, Minikube and cloud options.

Read the notebooks in `00-setup/` and paste their Bash blocks into a terminal in order:

First read [Our cluster architecture](00-setup/00-cluster-architecture.ipynb) for an illustrated view of this repository's components, data paths, monitoring and storage. It is an overview, not another deployment step.

1. [Ubuntu and workspace](00-setup/00-ubuntu-workspace.ipynb)
2. [Minikube cluster](00-setup/01-minikube-cluster.ipynb)
3. [Monitoring](00-setup/02-monitoring.ipynb)
4. [S3 / SeaweedFS](00-setup/03-s3-seaweedfs.ipynb)
5. [PostgreSQL](00-setup/04-postgresql.ipynb)
6. [Polaris catalog](00-setup/05-polaris-catalog.ipynb)
7. [MySQL](00-setup/06-mysql.ipynb)
8. [Grouped start/stop and persistence](00-setup/07-start-stop-group.ipynb)
9. [Shared image and Python workbench](00-setup/08-shared-image-workbench.ipynb)
10. [HDFS](00-setup/09-hdfs.ipynb)
11. [YARN](00-setup/10-yarn.ipynb)
12. [Hive](00-setup/11-hive.ipynb)
13. [Spark](00-setup/12-spark.ipynb)
14. [Kafka](00-setup/13-kafka.ipynb)


For an initial replay that defers YARN and Hive, complete notebooks 00-09, then 12-13. Notebook 08 reuses the existing validated image and imports it into the new node. Optional UI forwards run in a second terminal; continue setup in your original terminal. Skip the optional destructive-reset block when moving to the next notebook.

Notebook 01 also enables Headlamp and metrics-server. In the Guacamole Ubuntu browser, use the URL printed by `minikube -p bigdata service headlamp -n headlamp --url`; generate the viewer login token using the command in that notebook. No laptop tunnel is needed on the same Ubuntu host.

Monitoring starts first and captures the first service startup logs. The storage sequence deploys S3, PostgreSQL, Polaris and MySQL one at a time. It creates `test-bucket/test-object.txt`, `test_catalog.test_namespace.test_table` (Iceberg metadata), and PostgreSQL/MySQL `test_database.test_table` rows. The later exercise catalog `training` also points to `s3://warehouse/iceberg`.

After completing the individual steps, run `bash cluster.sh start all`, `bash cluster.sh stop all` or `bash cluster.sh status`. Groups always use dependency order; stopping retains PVCs. `all` covers only these four initial services. For compute groups use `bash start-components.sh hdfs hive spark jupyter kafka` and `bash stop-components.sh spark hive kafka jupyter`. Run the YARN lesson separately on the 8 GiB profile and pause it afterward; its application containers reserve substantial memory. Airflow and Trino tutorials follow later.

## First time after cloning

For command-based demonstration setup, use the [quick-start guide](00-setup/QUICKSTART.md). After Ubuntu preparation (notebook 00), run `bash setup-demo.sh --check`, then `bash setup-demo.sh` from the checkout root. This reuses the existing image and deploys the current walkthrough without exercise tests. On a new host without the image, use `bash setup-demo.sh --build-image`; an existing image is still preserved. The notebook walkthrough below remains the detailed alternative.

Use the repository URL supplied for this workspace. The repository root must contain `00-setup/`, `versions.env` and the scripts below:

```bash
REPOSITORY_URL='https://github.com/training-sh/workspace.git'
git clone "$REPOSITORY_URL" "$HOME/workspace"
cd "$HOME/workspace"
```

For another checkout location, clone into that directory and set `WORKSPACE_HOME` to its absolute path in notebook 00. That notebook persists the choice in `.bashrc`; all later sessions use it. The Git repository contains source files, not the built Docker image or Kubernetes volumes. On a new machine, notebook 08 builds the image if absent; on the prepared machine it reuses the existing `dataeng-training:1.2.0` image. A new Minikube node still needs the image imported into its containerd store.

There are **six stages**, using **12 setup notebooks** for the current walkthrough (00-09, then 12-13). The minimal monitored data cluster needs only the first **seven notebooks, 00-06**. These are notebook counts, not individual shell-command counts; execute each notebook's numbered sections in order.

| Stage | Notebooks | Result |
|---|---|---|
| 1. Prepare Ubuntu | [00](00-setup/00-ubuntu-workspace.ipynb) | Install tools, configure Docker group access and save workspace path. Complete the logout/login when required; verify ordinary Docker access before proceeding. |
| 2. Create cluster | [01](00-setup/01-minikube-cluster.ipynb) | Docker-driver Minikube, containerd, namespace, storage, metrics-server and Headlamp |
| 3. Start monitoring first | [02](00-setup/02-monitoring.ipynb) | Loki, Alloy, Prometheus, Grafana and Jaeger collect subsequent startup logs and metrics |
| 4. Add data services in order | [03](00-setup/03-s3-seaweedfs.ipynb), [04](00-setup/04-postgresql.ipynb), [05](00-setup/05-polaris-catalog.ipynb), [06](00-setup/06-mysql.ipynb), [07](00-setup/07-start-stop-group.ipynb) | S3, PostgreSQL, Polaris, MySQL, basic tests and lifecycle/persistence checks |
| 5. Import image and add workbench/HDFS | [08](00-setup/08-shared-image-workbench.ipynb), [09](00-setup/09-hdfs.ipynb) | Reuse/build and import image; mount source into Jupyter; NameNode and DataNode |
| 6. Add Spark and Kafka | [12](00-setup/12-spark.ipynb), [13](00-setup/13-kafka.ipynb) | Spark master/worker, then ZooKeeper and Kafka |

Leave [10 YARN](00-setup/10-yarn.ipynb) and [11 Hive](00-setup/11-hive.ipynb) for separate sessions. Their longer tests are deferred. Airflow, Trino and lineage have manifests but their lesson walkthroughs are not part of this validated initial sequence. Skip optional destructive resets between notebooks. First-time initialization and sample tests belong in the notebooks; daily startup does not repeat them.

## Start daily

After first-time setup, open a terminal on the Ubuntu host:

```bash
export WORKSPACE_HOME="${WORKSPACE_HOME:-$HOME/workspace}"
export PATH="$HOME/.local/bin:$PATH"
cd "$WORKSPACE_HOME"
source versions.env
minikube start --profile=bigdata --driver=docker --container-runtime=containerd \
  --kubernetes-version="$LAB_K8S_VERSION" --cpus="$LAB_CPUS" --memory="$LAB_MEMORY_MB"
kubectl config use-context bigdata
kubectl config set-context bigdata --namespace=bigdata
bash start-monitoring.sh
```

Starting a stopped profile resumes its existing workloads. The following commands also restore services that you previously scaled to zero. Start initial services one at a time:

```bash
bash cluster.sh start s3
bash cluster.sh start postgres
bash cluster.sh start polaris
bash cluster.sh start mysql
```

Then start the current compute session one at a time:

```bash
bash start-components.sh jupyter
bash start-components.sh hdfs
bash start-components.sh spark
bash start-components.sh kafka
```

Or start the **whole current walkthrough group** after the cluster is running:

```bash
bash start-monitoring.sh
bash cluster.sh start all
bash start-components.sh jupyter hdfs spark kafka
```

`cluster.sh ... all` means the four initial data services only. It does not include monitoring or compute. The compute script processes arguments sequentially and waits for readiness; Polaris includes S3/PostgreSQL dependencies and Kafka starts ZooKeeper first. No command here starts every manifest in the repository. On the configured 8 GiB profile, use YARN/Hive as a separate session rather than activating every application:

```bash
bash stop-components.sh spark kafka
bash start-components.sh yarn
# In a separate Hive session, with MySQL running:
# bash stop-components.sh yarn
# bash start-components.sh hive
```

Start only services whose setup notebook has already been completed. Browser forwarding processes must be started again after a host/profile restart. Check the result:

```bash
minikube -p bigdata status
bash cluster.sh status
kubectl -n bigdata get pods,services,pvc
kubectl -n bigdata top pods
```

## Stop services

Stop individual compute groups before their storage dependencies:

```bash
bash stop-components.sh spark
bash stop-components.sh kafka
bash stop-components.sh jupyter
# If started for this session:
# bash stop-components.sh hive yarn
bash stop-components.sh hdfs
bash cluster.sh stop polaris
bash cluster.sh stop mysql
bash cluster.sh stop postgres
bash cluster.sh stop s3
```

To pause all configured application workloads while keeping the node and PVCs, including any optional applications you started:

```bash
kubectl --context=bigdata -n bigdata scale deployment,statefulset --all --replicas=0
kubectl --context=bigdata -n bigdata get pods
```

Use this after setup jobs have finished; scaling does not cancel an active Job. Application Pods terminate asynchronously; completed setup Job Pods may remain listed. Daily start commands restore only the current walkthrough group. To **stop the entire course cluster**, including monitoring and Headlamp, close access/forward terminals with Ctrl+C, then:

```bash
minikube -p bigdata stop
```

This retains the profile, imported images and persistent volumes. `minikube -p bigdata delete` is a destructive reset: it removes node storage and PVC data. The host-built Docker image remains separate. Do not delete the profile during normal daily shutdown.

## Local browser UIs

Open these links in the **Ubuntu desktop browser**, including a desktop accessed through Guacamole. `127.0.0.1` refers to the browser's machine. Each service must be running and its forward active. GitHub Markdown does not reliably force a new tab; use Ctrl+click or the browser's Open link in new tab action.

The internal machine name below is Kubernetes Service DNS, not a hardcoded host. Names shown use namespace `bigdata`, except Headlamp. StatefulSet Pod names are stable; `*` indicates the generated Deployment suffix. Container names are listed after `/`.

| Service / page | Internal machine name | Pod / container | Local HTTP URL | Forward target and ports |
|---|---|---|---|---|
| Headlamp | `headlamp.headlamp.svc.cluster.local` | `headlamp-*` / discover below | [Headlamp](http://127.0.0.1:4466) | Namespace `headlamp`: `service/headlamp 4466:80` |
| SeaweedFS admin | `seaweedfs.bigdata.svc.cluster.local` | `seaweedfs-0 / seaweedfs` | [Admin](http://127.0.0.1:23646) | `service/seaweedfs 23646:23646` |
| SeaweedFS master | `seaweedfs.bigdata.svc.cluster.local` | `seaweedfs-0 / seaweedfs` | [Master](http://127.0.0.1:9333) | `service/seaweedfs 9333:9333` |
| SeaweedFS filer | `seaweedfs.bigdata.svc.cluster.local` | `seaweedfs-0 / seaweedfs` | [Filer](http://127.0.0.1:18888) | `service/seaweedfs 18888:8888` |
| SeaweedFS volume | `seaweedfs.bigdata.svc.cluster.local` | `seaweedfs-0 / seaweedfs` | [Volume](http://127.0.0.1:9340) | `service/seaweedfs 9340:9340` |
| HDFS NameNode | `namenode.bigdata.svc.cluster.local` | `namenode-0 / namenode` | [NameNode](http://127.0.0.1:19870) | `service/namenode 19870:9870` |
| HDFS DataNode | `datanode.bigdata.svc.cluster.local` | `datanode-0 / datanode` | [DataNode](http://127.0.0.1:9864) | `service/datanode 9864:9864` |
| YARN ResourceManager | `resourcemanager.bigdata.svc.cluster.local` | `resourcemanager-0 / resourcemanager` | [ResourceManager](http://127.0.0.1:18088) | `service/resourcemanager 18088:8088` |
| YARN NodeManager | `nodemanager.bigdata.svc.cluster.local` | `nodemanager-0 / nodemanager` | [NodeManager](http://127.0.0.1:8042) | `service/nodemanager 8042:8042` |
| MapReduce history | `historyserver.bigdata.svc.cluster.local` | `historyserver-0 / historyserver` | [History](http://127.0.0.1:19888) | `service/historyserver 19888:19888` |
| HiveServer2 status | `hiveserver2.bigdata.svc.cluster.local` | `hiveserver2-0 / hiveserver2` | [HiveServer2](http://127.0.0.1:10002) | `service/hiveserver2 10002:10002` |
| Spark master | `spark-master.bigdata.svc.cluster.local` | `spark-master-0 / spark-master` | [Master](http://127.0.0.1:8080) | `service/spark-master 8080:8080` |
| Spark worker | `spark-worker.bigdata.svc.cluster.local` | `spark-worker-0 / spark-worker` | [Worker](http://127.0.0.1:8081) | `service/spark-worker 8081:8081` |
| Spark application in Jupyter | `jupyter.bigdata.svc.cluster.local` | `jupyter-0 / jupyter` | [Active application](http://127.0.0.1:4040) | `service/jupyter 4040:4040`; only while its Spark context runs |
| JupyterLab | `jupyter.bigdata.svc.cluster.local` | `jupyter-0 / jupyter` | [JupyterLab](http://127.0.0.1:8889) | `service/jupyter 8889:8888` |
| Grafana | `grafana.bigdata.svc.cluster.local` | `grafana-0 / grafana` | [Grafana](http://127.0.0.1:3001) | `service/grafana 3001:3000` |
| Prometheus | `prometheus.bigdata.svc.cluster.local` | `prometheus-0 / prometheus` | [Prometheus](http://127.0.0.1:9090) | `service/prometheus 9090:9090` |
| Jaeger | `jaeger.bigdata.svc.cluster.local` | `jaeger-0 / jaeger` | [Jaeger](http://127.0.0.1:16686) | `service/jaeger 16686:16686` |
| Alloy diagnostics | `alloy.bigdata.svc.cluster.local` | `alloy-0 / alloy` | [Alloy](http://127.0.0.1:12345) | `service/alloy 12345:12345` |
| Adminer, optional SQL browser | `adminer.bigdata.svc.cluster.local` | `adminer-* / adminer` | [Adminer](http://127.0.0.1:8086) | `service/adminer 8086:8080`; optional deployment below |
| Airflow, later lesson | `airflow.bigdata.svc.cluster.local` | `airflow-0 / airflow` | [Airflow](http://127.0.0.1:8087) | `service/airflow 8087:8080` |
| Trino, later lesson | `trino.bigdata.svc.cluster.local` | `trino-0 / trino` | [Trino](http://127.0.0.1:8089) | `service/trino 8089:8080` |
| Marquez lineage, later lesson | `marquez-web.bigdata.svc.cluster.local` | `marquez-web-* / marquez-web` | [Lineage](http://127.0.0.1:3000) | `service/marquez-web 3000:3000` |

For any row, run `kubectl --context=bigdata -n bigdata port-forward --address=127.0.0.1` followed by its target and ports. Keep the terminal open; Ctrl+C closes the forward. For example, one terminal can expose all SeaweedFS pages:

```bash
kubectl --context=bigdata -n bigdata port-forward --address=127.0.0.1 \
  service/seaweedfs 23646:23646 9333:9333 18888:8888 9340:9340
```

In other terminals:

```bash
kubectl --context=bigdata -n bigdata port-forward --address=127.0.0.1 service/namenode 19870:9870
```

```bash
kubectl --context=bigdata -n headlamp port-forward --address=127.0.0.1 service/headlamp 4466:80
```

Or expose the three monitoring UIs together using the existing helper:

```bash
cd "${WORKSPACE_HOME:-$HOME/workspace}"
bash monitoring-access.sh
```

Do not run two forwards for the same local port. Some links inside Hadoop/Spark pages point to cluster-only addresses; use the direct local links in the table to open other components. The table adds forwarding instructions for all manifest HTTP pages; these additional pages have not all been tested interactively in a browser.

Headlamp uses the viewer token command in notebook 01. Jupyter uses token `team1234`; Grafana and Airflow use the example login `team / team1234`. SeaweedFS admin credentials are the example S3 values in `platform/lab-secret.yaml`. For optional Adminer:

```bash
kubectl --context=bigdata apply -f postgresql/adminer.yaml
kubectl --context=bigdata -n bigdata rollout status deployment/adminer --timeout=600s
kubectl --context=bigdata -n bigdata port-forward --address=127.0.0.1 service/adminer 8086:8080
```

Choose PostgreSQL/server `postgres` or MySQL/server `mysql` in Adminer and use the database credentials from the lab Secret. PostgreSQL/MySQL have no bundled native web UI. Kafka/ZooKeeper and Hive metastore also have no web UI in these manifests. Polaris exposes REST at `http://127.0.0.1:18181` and readiness at [Polaris health](http://127.0.0.1:18182/q/health/ready), not a catalog browser; use notebook 05's forward. S3 at `http://127.0.0.1:19001` is an authenticated API, not a browser UI. Loki is queried through Grafana, not through a standalone web UI.

## Check logs

Use the application container name explicitly when a Pod also contains a `file-logs` sidecar:

```bash
kubectl --context=bigdata -n bigdata logs seaweedfs-0 -c seaweedfs --tail=100
kubectl --context=bigdata -n bigdata logs spark-worker-0 -c spark-worker --tail=100 -f
kubectl --context=bigdata -n bigdata logs deployment/polaris -c polaris --since=10m
# Previous container instance, only when that container has restarted:
kubectl --context=bigdata -n bigdata logs spark-worker-0 -c spark-worker --previous
kubectl --context=bigdata -n bigdata describe pod spark-worker-0
kubectl --context=bigdata -n bigdata get events --sort-by=.metadata.creationTimestamp
```

Ctrl+C ends log following. For collected logs, open Grafana, choose Explore, select Loki and query `{namespace="bigdata"}`. Narrow with `{namespace="bigdata", pod="namenode-0"}`. Grafana retains collected logs according to Loki's configured storage/retention even after an application Pod disappears; deleting the profile destroys its local storage. Forward/mount helper logs, when run in the background as shown in notebooks, are under `.state/`; these are local runtime files and are not committed. See the official [kubectl logs reference](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/).

## Enter a running container for hands-on work

Kubernetes provides [`kubectl exec`](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_exec/), the equivalent operation to `docker exec` for a running Pod container. You enter a running container, not an image. Our host Docker runs the Minikube node; application containers run under containerd inside that node, so use kubectl for them.

```bash
kubectl --context=bigdata -n bigdata get pods
kubectl --context=bigdata -n bigdata get pod jupyter-0 \
  -o jsonpath='{.spec.containers[*].name}{"\n"}'
kubectl --context=bigdata -n bigdata exec -it jupyter-0 -c jupyter -- bash
```

Inside the workbench, the checkout is mounted at `/workspace`:

```bash
cd /workspace
python --version
ls notebooks python pyspark sql/trino airflow/dags
exit
```

Other examples, run from the host terminal:

```bash
kubectl --context=bigdata -n bigdata exec -it namenode-0 -c namenode -- bash
kubectl --context=bigdata -n bigdata exec -it spark-master-0 -c spark-master -- bash
kubectl --context=bigdata -n bigdata exec -it mysql-0 -c mysql -- sh
# Run one command without an interactive shell:
kubectl --context=bigdata -n bigdata exec jupyter-0 -c jupyter -- python --version
# Discover the actual generated Headlamp Pod and container names:
kubectl --context=bigdata -n headlamp get pods \
  -o custom-columns='POD:.metadata.name,CONTAINERS:.spec.containers[*].name'
```

For an image-only shell without starting Kubernetes, create a temporary host container from the retained image:

```bash
docker run --rm -it --entrypoint bash \
  --mount "type=bind,src=${WORKSPACE_HOME:-$HOME/workspace},dst=/workspace" \
  --workdir /workspace dataeng-training:1.2.0
```

That temporary container does not automatically join Kubernetes networking or provide cluster Service DNS. Host-bound workspace changes persist; changes to its container filesystem disappear when it exits. Use Jupyter for cluster-connected Python/PySpark exercises. Avoid installing packages manually into running Pods; durable software changes belong in the image build.

## Project layout

| Directory | Contents |
|---|---|
| `00-setup/` | Shell-by-shell setup notebooks |
| `notebooks/` | Python/PySpark `.ipynb` exercises |
| `python/` | Python modules and packages |
| `pyspark/` | Spark batch and streaming jobs |
| `sql/trino/` | Trino SQL files |
| `airflow/dags/` | Airflow DAG source |
| `platform/`, `seaweedfs/`, `postgresql/`, `polaris/`, `mysql/` | Initial Kubernetes manifests |
| `validations/` | Validation commands and records |
| `.state/` | Ignored downloads, forwarding logs and runtime files |

The entire project will mount into later Jupyter/Airflow containers at `/workspace`; Airflow additionally mounts `airflow/dags/` at `/opt/airflow/dags`. Container software stays in the shared image, not in a host-specific installation. Python host virtual environments, when needed, belong in `.venv/` and stay out of Git.

## Initial storage

| Service | Workload | PVC | Mount | Size |
|---|---|---|---|---|
| S3 | StatefulSet `seaweedfs` | `seaweedfs-data` | `/data` | 10 GiB |
| PostgreSQL | StatefulSet `postgres` | `postgres-data` | `/var/lib/postgresql/data` | 5 GiB |
| Polaris | Deployment `polaris` | Uses PostgreSQL and S3 | No separate data mount | ? |
| MySQL | StatefulSet `mysql` | `mysql-data` | `/var/lib/mysql` | 5 GiB |

`kubectl get pvc,pv` shows the generated PV names. With the Minikube Docker driver, Docker volume `bigdata` contains node storage, including these local PVCs. Deleting the profile destroys that storage. Namespace and context are also `bigdata`.

The committed credentials are public local-lab examples. Change initialization credentials before creating fresh volumes when using your own values; changing a Secret does not reset an existing database password.

[Validation commands](validations/README.md) and [reviewed replay and clean handoff record](validations/EXTENDED_SETUP.md) document the checks. [Shared image](SHARED_IMAGE.md) and existing component folders describe later sessions.

Monitoring is started before compute. Alloy forwards bigdata/Headlamp container logs and configured file logs to Loki; Prometheus stores container CPU/memory, native HDFS/Spark metrics, and YARN/Hive/Kafka JVM metrics. Grafana provisions performance and log dashboards. Each component notebook checks actual collected samples. [Extended setup execution](validations/EXTENDED_SETUP.md) records results and scope.
