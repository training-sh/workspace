# Iceberg migration and maintenance

Run the notebooks in numerical order. Each notebook stages its own typed data in HDFS and can also run independently.
Use a fresh Python kernel and run all cells from top to bottom. Close other Spark sessions before starting the next notebook.
Each notebook contains its own Spark connection and catalog configuration. There is no lesson-specific import or setup function.
SQL operations have separate cells, with short comments and visible assertions beside the checks.

| Notebook | Work |
|---|---|
| 01 | Hive managed/external sources, partitioned/unpartitioned layouts, migration design and first rewrite |
| 02 | File reuse with shallow import and in-place migration |
| 03 | Snapshot migration, reconciliation and type normalization |
| 04 | Phased backfill, coexistence, cutover and rollback |
| 05 | Late data, corrections, deduplication and replay |
| 06 | Hidden day partitions, customer buckets and partition evolution |
| 07 | Branches, tags, compaction, retention and cleanup |

## Before opening a notebook

Use the course Python workbench inside Kubernetes. It needs Spark 3.5 with a compatible Iceberg runtime and AWS bundle,
HDFS, a Hive metastore, a Polaris catalog and S3-compatible storage. This lesson uses non-transactional Hive Parquet tables.
Migration procedures run through the Iceberg Spark SQL extensions. HiveServer2 and YARN execution are not needed for these Spark SQL operations.

Connection settings use `os.environ.get(name, default)` directly in every notebook.
The defaults are the Kubernetes **Service DNS names**, with no fixed IP addresses or VM hostnames.
The notebook prints all resolved non-secret addresses before creating Spark. Environment variables take precedence.

No new cluster configuration is required for an existing installation. Keep the original workbench deployment.
Its existing `lab-credentials` Secret references already provide the catalog and storage credentials.
`start-components.sh` applies `jupyter/jupyter.yaml` when starting the workbench; the lesson does not apply manifests.
Exports in an unrelated host terminal are not automatically passed into an already running Jupyter Pod or kernel.

| Setting | Environment override | Kubernetes default |
|---|---|---|
| Spark master | `SPARK_MASTER_URL` | `spark://spark-master:7077` |
| Notebook driver | `SPARK_DRIVER_HOST` | `jupyter` |
| HDFS filesystem | `HDFS_URI` | `hdfs://namenode:9000` |
| Hive metastore | `HIVE_METASTORE_URI` | `thrift://hive-metastore:9083` |
| Polaris REST catalog | `POLARIS_URI` | `http://polaris:8181/api/catalog` |
| Polaris catalog name | `POLARIS_WAREHOUSE`, then `POLARIS_CATALOG` | `training` |
| S3 endpoint | `S3_ENDPOINT` | `http://seaweedfs:8333` |
| Region | `AWS_DEFAULT_REGION`, then `AWS_REGION` | `us-east-1` |
| Polaris realm | `POLARIS_REALM` | `POLARIS` |

`POLARIS_BASE_URL` is also accepted: when `POLARIS_URI` is absent, the notebook appends `/api/catalog` to that base URL.
The catalog credential can come from `POLARIS_CREDENTIAL` or the existing `POLARIS_CLIENT_ID` and `POLARIS_CLIENT_SECRET` pair.
Storage credentials use the existing `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. Credentials are never printed.

Short Service names work when the driver, workers and data services share a namespace.
For another namespace, override the address with its fully qualified Service DNS name.
Use `localhost` only when that service runs in the same Pod; it does not refer to the host or another Pod.

The account needs namespace/table creation permissions, access under `/workshop/11-iceberg-migration/`,
and access to the selected Polaris warehouse. The setup lesson creates catalog `training` and bucket `warehouse`.
For a different existing catalog, set the catalog-name override; Spark does not provision a Polaris catalog or bucket.

The [configuration notes](CONFIGURATION.md) explain HDFS defaults, the four catalog roles, raw S3A access,
Iceberg S3FileIO, and the server-side settings that remain part of the existing Polaris deployment.

## How the notebook reaches Spark

The connection appears directly in every notebook:

```python
master_url = os.environ.get('SPARK_MASTER_URL', 'spark://spark-master:7077')

builder = (
    SparkSession.builder
    .appName('iceberg-migration')
    .master(master_url)
)
```

The following cells add the driver networking and catalog configuration before calling `getOrCreate()`.
The notebook kernel runs the driver. The standalone master allocates executors on workers, and those executors
connect back to `SPARK_DRIVER_HOST` on the configured driver and block-manager ports. The driver displays
`spark.sparkContext.master`, then runs a task that verifies a separate executor was used. The notebooks require
the standalone master explicitly; they do not silently fall back to local execution.

Running these notebook cells does not require a separate `spark-submit` command. For a Python job file, the equivalent
submission pattern is `spark-submit --master "$SPARK_MASTER_URL" --deploy-mode client your_job.py`, with the same
catalog settings and reachable driver configuration. Standalone Spark does not support cluster deploy mode for Python jobs.
See [Spark standalone application submission](https://spark.apache.org/docs/3.5.9/spark-standalone.html#launching-spark-applications).

## Data and ownership

DataFrames use names such as `staged_orders_df` and `staged_invoices_df`. Source paths follow:

```text
/workshop/11-iceberg-migration/<notebook-number>/<execution-id>/<dataset>/<layout>
```

Each run prints its namespace and source root. A new execution ID prevents cross-run contamination and avoids replacing
another exercise's data. Inspect the completed tables before removing anything. The notebooks retain their tables and
source files for review; they do not recursively delete the lesson root. Use a fresh execution ID for a full rerun.

The four catalogs have distinct roles: `spark_catalog` connects Hive tables and in-place migration to the metastore;
`lake` uses a HadoopCatalog on HDFS; `iceberg` uses the Hive metastore with HDFS files; `polaris` holds Iceberg tables rewritten to the object-store warehouse.
File-reuse migration does not move HDFS data into S3. A backup table registration and a test snapshot can share source files;
they are not independent backups. Housekeeping exercises use independently owned data.

## Diagrams and validation

Every notebook embeds a PNG from `assets/`. Editable SVGs and the renderer live beside the PNGs.
To regenerate them, install Playwright and Chromium, then run `python assets/render_diagrams.py`.

Run the actual notebooks twice in the Kubernetes workbench:

```bash
python assets/validate_notebooks.py --passes 2 --output /tmp/migration-validation
```

The validator starts a fresh kernel for each notebook, rejects all cell errors, checks completion and saves executed copies
plus a JSON record. Source hashes tie results to the files tested. Diagnostic runs with `--only` do not replace two complete
successful passes of the final material. Exercises ask for additional changes; the supplied core cells are what the validator executes.

See the [validation record](VALIDATION.md) for the execution results and source hashes of this edition.

## References

- [Iceberg Spark procedures](https://iceberg.apache.org/docs/1.10.0/spark-procedures/)
- [Hidden partitioning](https://iceberg.apache.org/docs/1.10.0/partitioning/)
- [Partition evolution](https://iceberg.apache.org/docs/1.10.0/evolution/)
- [Branches and tags](https://iceberg.apache.org/docs/1.10.0/branching/)
- [Table maintenance](https://iceberg.apache.org/docs/1.10.0/maintenance/)
