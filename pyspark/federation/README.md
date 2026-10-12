# Trino and Spark federation lab

For remote SSH examples, set `LAB_SSH_USER` and `LAB_SSH_HOST` in your workstation shell to your Ubuntu login and host address.

Run from the `workspace/` root on Ubuntu after the initial deployment and shared-image build:

```bash
bash run-federation-lab.sh
cat pyspark/federation/results.json
```

The expanded stack uses a 16 GB host, four CPUs and a 10 GB Minikube limit. `versions.env` sets the limit for new installations. For an existing Docker-driver profile, increase the running container limit without deleting the cluster or its data:

```bash
docker update --memory 10g --memory-swap 10g bigdata
minikube config set memory 10240
```

For subsequent starts of an existing profile, explicitly pass `--memory=10240` to `minikube start -p bigdata`; the global default alone does not resize an existing running container. The Docker update above applies immediately. Keep YARN paused during this standalone Spark lesson.

| Store | Trino catalog/schema | Spark access | Storage |
|---|---|---|---|
| MySQL | `mysql.training` | JDBC, MySQL driver | MySQL PVC |
| PostgreSQL | `postgresql.public` | JDBC, PostgreSQL driver | PostgreSQL PVC; database `training_person` |
| Hive tables | `hive.federation_hive` | `spark_catalog.federation_hive` | HDFS, external non-ACID Parquet |
| Iceberg/Hive/Hadoop | `iceberg_hive.federation_ice_hdfs` | `hive_hdfs.federation_ice_hdfs` | HDFS |
| Iceberg/Hive/S3 | `iceberg_hive.federation_ice_s3` | `hive_s3.federation_ice_s3` | SeaweedFS S3 |
| Iceberg/Polaris/S3 | `polaris.federation_polaris` | `polaris.federation_polaris` | SeaweedFS S3 |

`iceberg_hive` is one Trino Iceberg connector backed by Hive Metastore. It supports both storage types; separate schemas keep their table locations clear. `hive` reads ordinary Hive tables and redirects Iceberg tables to `iceberg_hive`.

The lab creates unique tables per run, preserving previous exercises. Each engine writes and reads each store, then performs **all 30 directed transfers** between the six stores. Every transfer includes creation and append, checking all six rows including duplicates. Trino independently reads every table transferred by Spark. Each engine reads and appends to the other engine's seed tables; the writer's result is independently checked by the other engine. Finally, each engine performs a single join across all six stores and checks the Iceberg physical data-file locations.

Results include exact assertions, the run identifier and every Trino SQL statement. A failure writes `status: failed` with the error and stops the command. Do not interpret an old results file as evidence of the current run. The notebook `03-trino-spark-federation.ipynb` runs the same code in the shared workbench. Avoid running concurrent Spark drivers from this notebook and the shell: they share driver ports and the single worker.

Trino uses its MySQL/PostgreSQL connectors, which internally use JDBC. Spark uses its JDBC DataFrame reader/writer. Both use `team/team1234` for these databases. Trino catalogs read the existing Kubernetes `lab-credentials` Secret for S3 and Polaris credentials; this lab does not change the Polaris principal.

Trino catalog templates and startup code are in `trino/trino.yaml`. Run `bash start-components.sh trino` after editing catalogs; the root helper hashes the manifest to restart Trino when its configuration changes. No shared-image rebuild is required.

This checks tiny educational datasets, create/append/read and federation. It does not certify arbitrary types, transactions across databases, concurrent writers, UPDATE/DELETE for non-ACID Hive, failure recovery of distributed writes or production throughput. Cross-store writes are independent commits; they are not a single atomic transaction. Spark JDBC reads and writes are batch operations.

To query Trino from the Ubuntu host:

```bash
bash trino-access.sh
# In another terminal, use the CLI already available in the common image:
kubectl -n bigdata exec -it trino-0 -- trino --server http://trino:8080 --user team
```

For a remote laptop, forward host port 8089 using `ssh -L 8089:127.0.0.1:8089 "${LAB_SSH_USER:?Set LAB_SSH_USER}@${LAB_SSH_HOST:?Set LAB_SSH_HOST}"`. A host Python Trino client then connects to `localhost:8089` as `team`. SQL uses Kubernetes DNS internally; the laptop needs only the Trino endpoint, not direct access to every datastore.

For the separate CSV/JSON/ORC/Parquet compatibility lesson, run:

```bash
bash run-federation-formats.sh
cat pyspark/federation/formats-results.json
```

This prepares the existing person lesson and checks Trino writes, Spark reads/appends and native Hive reads for external format tables. CSV columns are VARCHAR in the Hive table; tests convert IDs back to integers. Spark reads JSON/CSV with its native file readers rather than requiring a Hive SerDe on the Spark classpath. The JSON Hive table uses the HCatalog SerDe shared by Hive and Trino.
