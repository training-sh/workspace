# Connections and storage configuration

Every notebook reads environment overrides, then falls back to the course Kubernetes Service names.
It prints the selected endpoints, catalog name and warehouse directories before Spark starts. Credentials stay hidden.
The notebooks do not load Kubernetes manifests. The existing workbench startup script applies the workbench manifest.
No manifest changes or rollout are required for this lesson.

## Filesystems and warehouses

`spark.hadoop.fs.defaultFS` selects HDFS for paths without a URI scheme.
`spark.sql.warehouse.dir` supplies the default Spark managed-table location.
The lesson creates its Hive database with an explicit location under the current execution root.
HDFS client hostname access is enabled so the DataNode address advertised to the driver and executors is used.

| Catalog | Configuration | Registration | Data and Iceberg metadata files |
|---|---|---|---|
| `spark_catalog` | `SparkSessionCatalog`, type `hive` | Hive metastore; legacy tables and in-place migration | HDFS |
| `lake` | `SparkCatalog`, type `hadoop` | HadoopCatalog on HDFS | HDFS |
| `iceberg` | `SparkCatalog`, type `hive` | Hive metastore; named Iceberg catalog | HDFS |
| `polaris` | `SparkCatalog`, type `rest` | Polaris REST catalog | S3-compatible storage |

The two metastore-backed catalog configurations use the same metastore URI deliberately.
A namespace already registered in Hive keeps its database location; a catalog warehouse option does not relocate it.
The named HiveCatalog customer example therefore supplies an explicit table `LOCATION`.
Two catalog aliases pointing to the same Hive metastore do not create separate metastore services or independent table ownership.

## Ordinary S3 files and Iceberg S3 files

The S3A configuration is needed for `spark.read.parquet('s3a://...')` and ordinary DataFrame object-store writes.
It sets the endpoint, path-style access, HTTP/HTTPS behavior, Hadoop filesystem implementation,
static credential provider and credentials. These settings are explicit in the notebooks, even when core-site.xml
already supplies similar values in the course image.

Polaris Iceberg tables use `org.apache.iceberg.aws.s3.S3FileIO` with its own endpoint, region, path-style access
and credential properties. Configuring S3A alone does not configure S3FileIO, and the reverse is also true.
Notebook 01 verifies the S3A client with an ordinary Parquet write/read, separately from its Polaris Iceberg migrations.
The runtime, AWS bundle and Hadoop AWS libraries must match the installed Spark and Hadoop versions; the lesson uses the existing image.

## Polaris client and server settings

`spark.sql.catalog.polaris.uri` is the REST catalog API endpoint and ends in `/api/catalog`.
The OAuth endpoint is that URI followed by `/v1/oauth/tokens`.
The client also sets its credential, scope, realm header and S3FileIO configuration.

`spark.sql.catalog.polaris.warehouse` selects the **Polaris catalog name**, such as `training`.
It is not the S3 warehouse directory. The server-side catalog determines `default-base-location` and allowed storage locations.
The existing setup provisions the bucket and Polaris catalog; creating a Spark namespace does not provision either one.

The server catalog storage configuration also supplies the internal object-store endpoint, region, path-style access
and `stsUnavailable` for this static-credential lab. Notebook client properties do not replace that server configuration.
Bucket/catalog creation, Polaris bootstrap and server feature settings remain in the existing setup lessons.
The migration notebooks do not repeat those administrative operations or print bearer tokens.

## Configuration comparison

The supplied reference configuration used localhost endpoints for a driver running alongside locally exposed services.
Inside Kubernetes, the defaults use Service DNS names and the internal service ports.
This lesson keeps the reference's explicit HDFS warehouse and S3A settings, adds the required driver callback configuration,
and distinguishes HadoopCatalog from HiveCatalog and Polaris REST registration.
The Iceberg SQL extension is configured once. Table properties such as format version, compression and copy-on-write mode
are table behavior choices, rather than connection requirements; specify them in the relevant DDL when needed.

References: [Iceberg Spark configuration](https://iceberg.apache.org/docs/1.10.0/spark-configuration/),
[Hadoop S3A](https://hadoop.apache.org/docs/r3.3.4/hadoop-aws/tools/hadoop-aws/index.html),
[Kubernetes Service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/).
