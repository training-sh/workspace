# Hive lesson module

Command-by-command setup: [Hive](../00-setup/11-hive.ipynb).

From `workspace/`, build/load the [common image](../SHARED_IMAGE.md) and start the existing MySQL infrastructure, then:

```bash
bash start-components.sh yarn hive
```

Hive 4.0.0 uses two separate pods from the same image: a metastore and HiveServer2. The root script creates a dedicated `hive_metastore` database in MySQL and grants the existing `team` / `team1234` account access. The `hive-schema` Job initializes an empty schema and checks its version; it does not import the host's old Hive metadata.

In JupyterLab Terminal:

```bash
beeline -u jdbc:hive2://hiveserver2:10000/default -n team
```

Then run SQL:

```sql
SHOW DATABASES;
CREATE DATABASE IF NOT EXISTS course;
CREATE TABLE IF NOT EXISTS course.numbers (id INT);
INSERT INTO course.numbers VALUES (1), (2);
SELECT count(*) FROM course.numbers;
```

The initial execution engine is MapReduce on YARN, with managed data on HDFS. HiveServer2 uses the training `NONE` authentication mode and does not impersonate another OS user. The metastore uses database credentials; Beeline's `team` name is not a Kubernetes or MySQL login handshake.

Pause with `bash stop-components.sh hive`; keep HDFS/YARN running if another lesson still needs them. MySQL metadata and HDFS table data survive pod replacement through their PVCs. Retain the completed schema Job; do not delete metadata or rerun initialization against an existing schema to resolve unrelated errors.

For diagnosis, this Hive distribution also writes its detailed application log inside the pod:

```bash
kubectl -n bigdata logs hiveserver2-0
kubectl -n bigdata exec hiveserver2-0 -- tail -100 /tmp/team/hive.log
kubectl -n bigdata exec hive-metastore-0 -- tail -100 /tmp/team/hive.log
```

The logs under `/tmp` are diagnostic files and are replaced with the pod. Jaeger does not collect these ordinary logs.
