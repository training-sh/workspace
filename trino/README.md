# Trino lesson module

Run from `workspace/` after building/loading the [common image](../SHARED_IMAGE.md):

```bash
bash start-components.sh trino
```

One pod runs Trino 476 as coordinator and worker, with its Java 24 runtime. Readiness waits until initialization completes. Its catalogs are TPCH, MySQL, PostgreSQL, Hive, Iceberg through Hive Metastore (HDFS and S3), and Iceberg through Polaris (SeaweedFS S3). Catalog templates are in the ConfigMap inside `trino.yaml`; credentials come from the shared lab Secret.

In JupyterLab Terminal:

```bash
trino --server http://trino:8080 --user team --execute 'SELECT count(*) FROM tpch.tiny.nation'
# Expected: 25
trino --server http://trino:8080 --user team
```

For a browser on the Ubuntu host, leave this running in a separate host terminal:

```bash
bash trino-access.sh
```

Open http://127.0.0.1:8089 and use `team`. Laptop access requires an SSH tunnel for local port 8089. Initial Trino authentication is the training user name only; no password authentication is configured. The data-directory PVC survives pod replacement. Pause with `bash stop-components.sh trino`.

Run `bash run-federation-lab.sh` from the root for the complete Trino/Spark write/read and cross-catalog matrix. Run `bash run-federation-formats.sh` for file-format interoperability. See [the federation lab](../pyspark/federation/README.md) for catalogs, exact coverage, notebook and results. The expanded stack uses a 10 GiB Minikube limit; YARN stays paused during this standalone Spark lesson.
