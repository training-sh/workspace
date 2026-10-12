# Spark lesson module

Command-by-command setup: [Spark](../00-setup/12-spark.ipynb).

All commands start from `workspace/`. Spark 3.5.9 is installed in the common image, including PySpark, Kafka/Avro, Iceberg and Delta connectors. Jupyter's Python/PySpark kernel uses that installation. See [shared-image instructions](../SHARED_IMAGE.md) for the build, credentials and workspace ownership.

Local execution needs only Jupyter:

```bash
bash start-components.sh jupyter
```

For standalone execution, start one master and one worker:

```bash
bash start-components.sh spark
```

Use this in a notebook after stopping any previous Spark session:

```python
from pyspark.sql import SparkSession
spark = (SparkSession.builder.appName("standalone-lesson")
    .master("spark://spark-master:7077")
    .config("spark.driver.host", "jupyter.bigdata.svc.cluster.local")
    .config("spark.driver.bindAddress", "0.0.0.0")
    .config("spark.driver.port", "7078")
    .config("spark.blockManager.port", "7079")
    .config("spark.cores.max", "1")
    .config("spark.executor.memory", "512m")
    .getOrCreate())
spark.range(100).repartition(2).count()
spark.sparkContext.parallelize(range(5), 2).map(lambda x: x + 1).sum()
spark.stop()
```

The master binds its pod IP; clients use its stable Service. `enableServiceLinks: false` prevents Kubernetes' automatic `SPARK_MASTER_PORT`/`SPARK_WORKER_PORT` environment variables from conflicting with Spark's numeric settings.

Pause this lesson with `bash stop-components.sh spark`. The worker's local scratch directory is disposable; lesson files remain in the shared workspace. For YARN execution, use the separate [Hadoop module](../hadoop/README.md) and the YARN example in SHARED_IMAGE.md. Native Kubernetes driver/executor submission requires its own RBAC and configuration in a later lesson.

For local Delta/Iceberg files, use explicit `file:///tmp/...` URIs. The configured default filesystem points to HDFS, which must be started before using HDFS paths. Local `/tmp` data is disposable; persist course data to HDFS or the object-storage catalog configured for its lesson.
