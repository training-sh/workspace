"""Repeatable, small person exercise. Run via root run-person-lab.sh or notebook."""
import json
import os
import time
from pathlib import Path
import boto3
import requests
from pyhive import hive
from pyspark.sql import SparkSession

ROWS = [(1, 'Person1', 28, 'Chennai'), (2, 'Person2', 35, 'Bengaluru'), (3, 'Person3', 31, 'Hyderabad')]
SCHEMA = 'id INT, name STRING, age INT, city STRING'
HDFS = 'hdfs://namenode:9000/user/team/person_lab'
POLARIS = 'http://polaris:8181/api/catalog'
S3 = 'http://seaweedfs:8333'
MASTER = os.environ.get('PERSON_SPARK_MASTER', 'spark://spark-master:7077')


def run():
    builder = (SparkSession.builder.appName('person_hive_to_polaris_jdbc').master(MASTER)
        .config('spark.driver.host', 'jupyter.bigdata.svc.cluster.local')
        .config('spark.driver.bindAddress', '0.0.0.0')
        .config('spark.driver.port', '7078').config('spark.blockManager.port', '7079')
        .config('spark.executor.instances', '1').config('spark.executor.cores', '1')
        .config('spark.cores.max', '1').config('spark.executor.memory', '512m')
        .config('spark.hadoop.hive.metastore.uris', 'thrift://hive-metastore:9083')
        .config('spark.sql.extensions', 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions')
        .config('spark.sql.catalog.polaris', 'org.apache.iceberg.spark.SparkCatalog')
        .config('spark.sql.catalog.polaris.type', 'rest')
        .config('spark.sql.catalog.polaris.rest-metrics-reporting-enabled', 'false')
        .config('spark.redaction.regex', '(?i)secret|password|token|access[.]key|credential')
        .config('spark.sql.catalog.polaris.uri', POLARIS)
        .config('spark.sql.catalog.polaris.warehouse', 'training')
        .config('spark.sql.catalog.polaris.oauth2-server-uri', POLARIS + '/v1/oauth/tokens')
        .config('spark.sql.catalog.polaris.credential', os.environ['POLARIS_CLIENT_ID'] + ':' + os.environ['POLARIS_CLIENT_SECRET'])
        .config('spark.sql.catalog.polaris.scope', 'PRINCIPAL_ROLE:ALL')
        .config('spark.sql.catalog.polaris.header.Polaris-Realm', 'POLARIS')
        .config('spark.sql.catalog.polaris.io-impl', 'org.apache.iceberg.aws.s3.S3FileIO')
        .config('spark.sql.catalog.polaris.s3.endpoint', S3)
        .config('spark.sql.catalog.polaris.s3.path-style-access', 'true')
        .config('spark.sql.catalog.polaris.s3.access-key-id', os.environ['AWS_ACCESS_KEY_ID'])
        .config('spark.sql.catalog.polaris.s3.secret-access-key', os.environ['AWS_SECRET_ACCESS_KEY'])
        .config('spark.sql.catalog.polaris.client.region', 'us-east-1')
        .enableHiveSupport())
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    checks = []
    def passed(message):
        checks.append(message)
        print('PASS: ' + message, flush=True)
    try:
        person = spark.createDataFrame(ROWS, SCHEMA)
        # Formats are data encodings. Iceberg is a table format with catalog metadata.
        for fmt in ('csv', 'json', 'orc', 'parquet'):
            path = HDFS + '/external/' + fmt
            person.coalesce(1).write.mode('overwrite').format(fmt).save(path)
            actual = spark.read.schema(SCHEMA).format(fmt).load(path)
            assert sorted(tuple(row) for row in actual.collect()) == ROWS, fmt
            passed('HDFS ' + fmt + ' write/read: 3 matching people')

        # Hive owns the managed table; external tables point to the format directories.
        connection = hive.Connection(host='hiveserver2', port=10000, username='team', auth='NONE')
        cursor = connection.cursor()
        cursor.execute('SET hive.fetch.task.conversion=more')
        cursor.execute('CREATE DATABASE IF NOT EXISTS course_person')
        cursor.execute("CREATE TABLE IF NOT EXISTS course_person.person (id INT, name STRING, age INT, city STRING) ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE TBLPROPERTIES ('transactional'='false')")
        # Hive 4 can translate a non-ACID CREATE into an external table.
        # Explicitly establish managed ownership for this dedicated sample.
        cursor.execute("ALTER TABLE course_person.person SET TBLPROPERTIES ('EXTERNAL'='FALSE')")
        person.coalesce(1).write.mode('overwrite').csv(HDFS + '/staging')
        cursor.execute("LOAD DATA INPATH '/user/team/person_lab/staging' OVERWRITE INTO TABLE course_person.person")
        declarations = {
            'csv': "ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE",
            'json': "ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe' STORED AS TEXTFILE",
            'orc': 'STORED AS ORC',
            'parquet': 'STORED AS PARQUET',
        }
        for fmt, declaration in declarations.items():
            cursor.execute(f"CREATE EXTERNAL TABLE IF NOT EXISTS course_person.person_{fmt} (id INT, name STRING, age INT, city STRING) {declaration} LOCATION '/user/team/person_lab/external/{fmt}'")
            if fmt == 'json':
                cursor.execute("ALTER TABLE course_person.person_json SET SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'")
        for table in ('person', 'person_csv', 'person_json', 'person_orc', 'person_parquet'):
            cursor.execute('SELECT * FROM course_person.' + table)
            assert sorted(tuple(row) for row in cursor.fetchall()) == ROWS, table
            cursor.execute('DESCRIBE FORMATTED course_person.' + table)
            details = {str(row[0]).strip().rstrip(':'): str(row[1]).strip() for row in cursor.fetchall() if row[0]}
            expected_type = 'MANAGED_TABLE' if table == 'person' else 'EXTERNAL_TABLE'
            assert details.get('Table Type') == expected_type, details
            passed('Hive ' + table + ': ' + expected_type + ', 3 matching people')
        cursor.close()
        connection.close()

        source = spark.table('spark_catalog.course_person.person')
        assert sorted(tuple(row) for row in source.collect()) == ROWS
        passed('Spark reads the actual Hive managed table through its metastore')
        spark.sql('CREATE NAMESPACE IF NOT EXISTS polaris.course_person')
        for fmt in ('parquet', 'orc'):
            table = 'polaris.course_person.person_' + fmt
            spark.sql(f"CREATE TABLE IF NOT EXISTS {table} (id INT, name STRING, age INT, city STRING) USING iceberg TBLPROPERTIES ('write.format.default'='{fmt}')")
            source.writeTo(table).overwritePartitions()
            assert sorted(tuple(row) for row in spark.table(table).collect()) == ROWS
            formats = {row.file_format for row in spark.sql(f'SELECT DISTINCT file_format FROM {table}.files').collect()}
            assert formats == {fmt.upper()}, formats
            passed('Hive -> Polaris Iceberg / SeaweedFS S3: ' + fmt + ', 3 matching people')

        # These dedicated exercise tables are replaced on every run.
        databases = {
            'mysql': ('jdbc:mysql://mysql:3306/training?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC', 'com.mysql.cj.jdbc.Driver'),
            'postgresql': ('jdbc:postgresql://postgres:5432/training_person', 'org.postgresql.Driver'),
        }
        lake = spark.table('polaris.course_person.person_parquet')
        for name, (url, driver) in databases.items():
            properties = {'user': 'team', 'password': 'team1234', 'driver': driver}
            # Distinct names keep MySQL and PostgreSQL write jobs separate in lineage.
            target = 'person_from_iceberg_' + name
            lake.write.mode('overwrite').jdbc(url, target, properties=properties)
            result = spark.read.jdbc(url, target, properties=properties)
            assert sorted(tuple(row) for row in result.collect()) == ROWS
            passed('Spark JDBC write/read ' + name + ': 3 matching people')

        # Verify real object data and catalog metadata, independently of Spark's cache.
        response = requests.post(POLARIS + '/v1/oauth/tokens', headers={'Polaris-Realm': 'POLARIS'}, data={
            'grant_type': 'client_credentials', 'client_id': os.environ['POLARIS_CLIENT_ID'],
            'client_secret': os.environ['POLARIS_CLIENT_SECRET'], 'scope': 'PRINCIPAL_ROLE:ALL'}, timeout=30)
        response.raise_for_status()
        headers = {'Polaris-Realm': 'POLARIS', 'Authorization': 'Bearer ' + response.json()['access_token']}
        s3 = boto3.client('s3', endpoint_url=S3, region_name='us-east-1', config=boto3.session.Config(s3={'addressing_style': 'path'}))
        for fmt in ('parquet', 'orc'):
            response = requests.get(POLARIS + '/v1/training/namespaces/course_person/tables/person_' + fmt, headers=headers, timeout=30)
            response.raise_for_status()
            table = response.json()
            metadata = table['metadata-location']
            assert metadata.startswith('s3://warehouse/iceberg/')
            stored = json.loads(s3.get_object(Bucket='warehouse', Key=metadata.removeprefix('s3://warehouse/'))['Body'].read())
            assert stored['table-uuid'] == table['metadata']['table-uuid']
            files = spark.sql(f'SELECT file_path FROM polaris.course_person.person_{fmt}.files').collect()
            assert files
            for row in files:
                assert row.file_path.startswith('s3://warehouse/')
                assert s3.head_object(Bucket='warehouse', Key=row.file_path.removeprefix('s3://warehouse/'))['ContentLength'] > 0
        passed('Polaris metadata UUIDs and actual Iceberg data objects verified directly in S3')
    finally:
        spark.stop()

    # Check that the collector received genuine Spark events with dataset edges.
    for attempt in range(60):
        response = requests.get('http://marquez:5000/api/v1/namespaces/training/jobs?limit=100', timeout=30)
        response.raise_for_status()
        jobs = [job for job in response.json()['jobs'] if 'person_hive_to_polaris_jdbc' in job['name']]
        migration = [job for job in jobs if any('/user/hive/warehouse/course_person.db/person' == item['name'] for item in job.get('inputs', [])) and any(item['namespace'] == 's3://warehouse' for item in job.get('outputs', []))]
        jdbc_present = all(any(any('person_from_iceberg_' + database in item['name'] for item in job.get('outputs', [])) for job in jobs) for database in ('mysql', 'postgresql'))
        if len(migration) >= 2 and jdbc_present:
            break
        time.sleep(2)
    else:
        raise AssertionError('Missing Spark input/output lineage in Marquez')
    migration = [job for job in jobs if any('/user/hive/warehouse/course_person.db/person' == item['name'] for item in job.get('inputs', [])) and any(item['namespace'] == 's3://warehouse' for item in job.get('outputs', []))]
    assert len(migration) >= 2, migration
    for database in ('mysql', 'postgresql'):
        assert any(any('person_from_iceberg_' + database in item['name'] for item in job.get('outputs', [])) for job in jobs), database
    passed('Marquez received Hive/HDFS -> S3 Iceberg and separate MySQL/PostgreSQL dataset edges')
    report = {'checks': checks, 'people': [list(row) for row in ROWS], 'lineage_jobs': [job['name'] for job in jobs]}
    Path('/workspace/python/person/results.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    run()
