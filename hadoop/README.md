# HDFS and YARN lesson modules

Command-by-command setup: [HDFS](../00-setup/09-hdfs.ipynb), [YARN](../00-setup/10-yarn.ipynb).

Run from `workspace/` after building/loading the [common course image](../SHARED_IMAGE.md):

```bash
bash start-components.sh hdfs
# Adds ResourceManager, NodeManager and MapReduce history service:
bash start-components.sh yarn
```

`hdfs.yaml` starts one NameNode and one DataNode, each with a 5 GiB PVC. `yarn.yaml` starts one of each YARN role. Every daemon uses the same image, runs in the foreground and selects its role through `args`; no host Hadoop scripts or SSH between pods are required.

In JupyterLab Terminal:

```bash
hdfs dfsadmin -report
hdfs dfs -ls /
printf 'hello hdfs\n' | hdfs dfs -put -f - /user/team/hello.txt
hdfs dfs -cat /user/team/hello.txt
yarn node -list
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar pi 1 10
```

For a host command, explicitly load the image's environment:

```bash
kubectl -n bigdata exec jupyter-0 -- bash -ec 'source /opt/training/env.sh; hdfs dfs -ls /'
```

Use `bash -ec 'source /opt/training/env.sh; ...'` when writing a noninteractive script, since login shells do not necessarily source `.bashrc`.

NameNode formatting occurs only when its data directory is empty. Existing nonempty storage without a valid VERSION file is refused; do not reformat to troubleshoot. The root startup script creates the training directories after safe mode clears. New Kubernetes data is separate from the old host HDFS installation.

The NodeManager advertises 2 GiB and two vcores, while its 3 GiB pod limit includes its own JVM. A default CapacityScheduler queue permits one small Spark AM/executor pair. See SHARED_IMAGE.md for the notebook's YARN driver addresses and memory settings. This is one DataNode/NodeManager initially; scaling requires per-node identity and storage configuration, not just increasing replicas.

Pause in dependency order:

```bash
bash stop-components.sh hive yarn hdfs  # Only include already-deployed modules.
```

Use separate host terminals for the web UIs:

```bash
kubectl -n bigdata port-forward --address=127.0.0.1 service/namenode 9870:9870
kubectl -n bigdata port-forward --address=127.0.0.1 service/resourcemanager 8088:8088
kubectl -n bigdata port-forward --address=127.0.0.1 service/historyserver 19888:19888
```

Laptop browsers need matching SSH forwards. These browser forwards do not make HDFS data transfer or YARN callback protocols available to host clients; use the in-cluster Jupyter workbench for those exercises.
