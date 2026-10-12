Run from the setup root on Ubuntu:

```bash
bash build-image.sh
bash start-components.sh hdfs hive spark kafka jupyter
bash run-streaming-lab.sh
cat pyspark/streaming/results.json
```

Requires the base PostgreSQL, MySQL, ZooKeeper, Polaris and SeaweedFS deployments and the `training` Polaris catalog / `warehouse` bucket created by the base setup and `validations/verify.sh`.

This exercise uses Spark 3.5.9's native Structured Streaming Kafka source and Iceberg 1.10.0 sink. Each unique run creates three Kafka topics (three partitions, one replica) and three city-partitioned Iceberg tables:

| Spark catalog | Metadata service | Table files |
| --- | --- | --- |
| hive_hdfs | Hive Metastore | HDFS |
| hive_s3 | Hive Metastore | SeaweedFS S3, `s3a://warehouse/hive-iceberg/...` |
| polaris | Polaris REST | SeaweedFS S3, Polaris `training` warehouse |

The Hive S3 namespace stays on HDFS; each table explicitly selects its S3 location. Iceberg S3FileIO writes the table's metadata and data in S3. Hive Metastore uses matching Hadoop 3.3.6 / AWS SDK 1.12.367 S3A dependencies to validate that location. Spark retains its own Hadoop 3.3.4 dependencies; the two sets are deliberately separate.

The initial phase publishes IDs 1–3, streams them to Iceberg, streams Iceberg append snapshots into a Parquet readback sink, compares every field, and checks physical file sizes. The root script replaces the Jupyter pod and hence the driver process. Resume publishes IDs 4–6, resumes both checkpoints and verifies exactly six rows. Replay runs another driver with no new records and verifies six unchanged rows in both sinks. Checkpoints and results survive pod replacement. Each query has a 180-second timeout.

Kafka ingestion checkpoints are on HDFS for all three catalogs. Iceberg streaming read checkpoints use HDFS for the HDFS table and S3A for S3 tables: Iceberg's initial-offset file is written by the table's FileIO, so S3FileIO cannot use an HDFS checkpoint directory. Spark accesses those S3A checkpoints using its own matching Hadoop AWS dependencies and explicit endpoint / path-style / credential settings. Parquet readback output stays on HDFS in every case.

Run this before opening notebooks: replacing Jupyter interrupts active notebook kernels. The streaming tests use dedicated topics, tables and paths; existing person lesson data is retained. Test resources remain for inspection; repeated runs create additional small datasets. `state.json` refers to the latest run, so run only one validation at a time.

`availableNow` makes these small training tests finite. For ongoing ingestion use a processing-time trigger of at least one minute and plan snapshot expiration / file compaction. Iceberg streaming reads here process append snapshots; overwrite/delete snapshots and continuous processing are outside this exercise. Native HiveServer2 SQL reads of Iceberg are a separate integration and are not implied by Spark HiveCatalog access.

Reference: https://iceberg.apache.org/docs/1.10.0/spark-structured-streaming/

OpenLineage remains enabled. This exercise disables only its optional Iceberg scan/commit metrics injector with `spark.openlineage.vendors.iceberg.metricsReporterDisabled=true`, the documented workaround for injector problems. OpenLineage 1.53.0 otherwise reports a nonfatal `scala.None` / `CatalogPlugin` cast error on these streaming plans. Reference: https://openlineage.io/docs/integrations/spark/dataset_metrics/
