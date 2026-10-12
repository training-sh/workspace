# Person data exercise

Complete the base README startup and `bash validations/verify.sh` first; those prepare the warehouse bucket and Polaris training catalog. From the `workspace/` root after building/importing `dataeng-training:1.2.0`:

```bash
bash build-image.sh
bash run-person-lab.sh
bash lineage-access.sh
```

Keep the final terminal open for the lineage viewer. Jupyter's existing access command is `bash workbench-access.sh`; open `01-person-data-lab.ipynb` to repeat the exercise. The notebook calls the same readable Python file as the root command. Close earlier Spark sessions before running it.

The three sample people travel through this sequence:

1. Spark master/worker writes and reads CSV, JSON, ORC and Parquet under HDFS `/user/team/person_lab/external/`.
2. Hive loads a separate staging copy into managed table `course_person.person` and registers four external tables pointing at the format directories. HiveServer2 reads all five and verifies their contents and table types. Small `SELECT *` queries use Hive fetch tasks; this exercise does not require starting YARN.
3. Spark reads the actual Hive managed table via `hive-metastore:9083` and copies its rows into Polaris catalog `training`, namespace `course_person`, tables `person_parquet` and `person_orc`.
4. Those are Iceberg tables containing Parquet or ORC data files in `s3://warehouse/iceberg/`, served by SeaweedFS. The exercise checks Iceberg's files metadata, Polaris's metadata UUIDs and actual S3 objects independently.
5. Spark JDBC writes the Iceberg rows to MySQL database `training` and PostgreSQL database `training_person`, tables `person_from_iceberg_mysql` and `person_from_iceberg_postgresql` respectively, then reads and compares them.
6. OpenLineage emits real Spark events; the exercise verifies jobs with input/output dataset edges in Marquez and saves `person/results.json` into the host-shared workspace.

CSV/JSON/ORC/Parquet are file formats. Iceberg is a table format; Polaris is its catalog and SeaweedFS is the S3 storage. A plain CSV or JSON directory is not automatically a Polaris table. This exercise copies data and retains the original Hive/HDFS data; it does not drop or relocate source tables.

Reruns overwrite only these dedicated sample paths/tables. All example JDBC connections use `team/team1234`. Polaris credentials and S3 credentials come from the workbench pod's Kubernetes Secret references. Existing Polaris bootstrap client credentials remain as configured in `platform/lab-secret.yaml`.

For plain SQL in Jupyter's terminal:

```bash
beeline -u jdbc:hive2://hiveserver2:10000/default -n team \
  -e 'SET hive.fetch.task.conversion=more; SELECT * FROM course_person.person_parquet;'
hdfs dfs -ls /user/team/person_lab/external
```

After the exercise, Hive, HDFS, Spark master/worker, Polaris, SeaweedFS and Marquez stay running for lessons. Pause selected compute services with `bash stop-components.sh hive spark hdfs`; PVC data stays available.

Hive 4 may translate a nontransactional CREATE into an external table. The exercise explicitly sets `EXTERNAL=FALSE` on its dedicated managed sample and verifies the resulting table type. Optional Iceberg REST metrics reporting is disabled for this lesson; OpenLineage events still go to Marquez and platform metrics remain in Prometheus.

The JSON external table uses `org.apache.hive.hcatalog.data.JsonSerDe`, which both Hive 4 and Trino 476 understand. Rerunning the lesson also updates the SerDe of its existing dedicated JSON table without rewriting the data.
