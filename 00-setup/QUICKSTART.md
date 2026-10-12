# Demonstration setup by command

Use this alternative when you want the demonstration ready without walking through each notebook. It deploys the same manifests in order and waits for readiness. It does not execute exercises, create their `test_*` data, or run pause/resume tests. YARN/Hive and later Airflow/Trino/lineage lessons stay separate.

For a picture of what this command creates, read [Our cluster architecture](00-cluster-architecture.ipynb) first.

## 1. Prepare Ubuntu once

Use Ubuntu x86_64 with at least four CPUs, enough memory for the 8 GiB Minikube profile plus Ubuntu (16 GiB host recommended), and at least 50 GiB free for image/deployment work. Internet access is required for cluster and application downloads.

Complete [00-ubuntu-workspace.ipynb](00-ubuntu-workspace.ipynb) once if Docker, Minikube or kubectl is missing. That notebook installs tools and grants ordinary-account Docker access. Reconnect after changing Docker group membership. Run the following commands without sudo.

Clone the supplied repository into `~/workspace`. If already cloned, use that checkout:

```bash
REPOSITORY_URL='https://github.com/training-sh/workspace.git'
git clone "$REPOSITORY_URL" "$HOME/workspace"
cd "$HOME/workspace"
```

The checkout root must contain `setup-demo.sh` and `versions.env`. For a different folder, `cd` into its root instead. The deployment command saves that actual folder as `WORKSPACE_HOME` in `.bashrc`.

## 2. Check readiness without starting anything

On the prepared demonstration machine, the shared image already exists:

```bash
bash setup-demo.sh --check
```

Expect `Prerequisites ready`. If a tool or Docker permission is missing, the command explains what to fix. A Git clone does not contain the built Docker image.

## 3. Start the demonstration

With the existing image:

```bash
bash setup-demo.sh
```

On a new machine without that image, allow the first build explicitly:

```bash
bash setup-demo.sh --build-image
```

The build option still reuses an image if present. Building/downloading on a new machine can take much longer; there is no fixed completion time. The script shows six stages and ends with `READY`. A failure stops the script and identifies the stage; fix the error and run the same command again. It preserves existing PVC data and does not delete a cluster or image. This command selects the `bigdata` kubectl context. Re-running reconciles the demonstration services and may restart Pods when configuration changes.

| Stage | Starts |
|---|---|
| 1 | Minikube node, DNS, storage and namespace |
| 2 | metrics-server and Headlamp |
| 3 | Loki, Alloy, Prometheus, Jaeger and Grafana |
| 4 | SeaweedFS S3, PostgreSQL, Polaris, MySQL |
| 5 | Import shared image into the node's containerd store |
| 6 | Jupyter, HDFS NameNode/DataNode, Spark master/worker, ZooKeeper/Kafka |

## 4. Open browser pages

Run each block in a separate terminal and keep it open. Open links in the Ubuntu desktop browser, including through Guacamole. Ctrl+C ends forwarding.

Monitoring:

```bash
cd "${WORKSPACE_HOME:-$HOME/workspace}"
bash monitoring-access.sh
```

[Grafana](http://127.0.0.1:3001), [Prometheus](http://127.0.0.1:9090), [Jaeger](http://127.0.0.1:16686). Grafana example login: `team / team1234`.

Jupyter:

```bash
kubectl --context=bigdata -n bigdata port-forward --address=127.0.0.1 service/jupyter 8889:8888
```

[JupyterLab](http://127.0.0.1:8889), example token `team1234`. Open exercises under `/workspace/notebooks`.

Headlamp:

```bash
kubectl --context=bigdata -n headlamp port-forward --address=127.0.0.1 service/headlamp 4466:80
```

In another terminal, generate a login token, then paste it into [Headlamp](http://127.0.0.1:4466). Do not save the token in Git:

```bash
kubectl --context=bigdata -n headlamp create token workspace-ui --duration=8h
```

The [README UI table](../README.md#local-browser-uis) lists SeaweedFS, HDFS, Spark and other pages. NameNode uses local port `19870` and YARN uses `18088` to avoid existing host applications. A port-forward reports an error if a local port is occupied; close an earlier forward or choose another local port.

## 5. Stop and resume

Close browser-forward terminals with Ctrl+C. Stop the course cluster without deleting its data:

```bash
minikube -p bigdata stop
```

For the next demonstration, run `bash setup-demo.sh` from the same checkout. The existing image and volumes are reused. For individual daily start/stop, logs and interactive container access, use the [README commands](../README.md#start-daily).

## If setup stops

```bash
minikube -p bigdata status
kubectl --context=bigdata -n bigdata get pods,pvc
kubectl --context=bigdata -n bigdata get events --sort-by=.metadata.creationTimestamp
```

For a failing Pod, use its actual name from `get pods` with `kubectl --context=bigdata -n bigdata describe pod POD_NAME`. Check Docker access, disk space, available memory, download connectivity and the reported stage before retrying. Keep the step-by-step notebooks for the explanation and component-specific tests.
