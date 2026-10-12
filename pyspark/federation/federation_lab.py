"""Full directed transfer matrix, two engines, exact rows and shared-table writes."""
import json
import sys
import time
from pathlib import Path

import trino

sys.path.insert(0, '/workspace/pyspark/streaming')
from streaming_lab import session

ROOT = Path('/workspace/pyspark/federation')
ROWS = [(1, 'Person1', 'Chennai'), (2, 'Person2', 'Bengaluru'), (3, 'Person3', 'Hyderabad')]
STORES = {
    'mysql': ('mysql.training', None),
    'postgresql': ('postgresql.public', None),
    'hive': ('hive.federation_hive', 'spark_catalog.federation_hive'),
    'ice_hdfs': ('iceberg_hive.federation_ice_hdfs', 'hive_hdfs.federation_ice_hdfs'),
    'ice_s3': ('iceberg_hive.federation_ice_s3', 'hive_s3.federation_ice_s3'),
    'polaris': ('polaris.federation_polaris', 'polaris.federation_polaris'),
}
JDBC = {
    'mysql': ('jdbc:mysql://mysql:3306/training', 'com.mysql.cj.jdbc.Driver'),
    'postgresql': ('jdbc:postgresql://postgres:5432/training_person', 'org.postgresql.Driver'),
}


def run():
    state = {'run_id': str(time.time_ns()), 'status': 'running', 'checks': [], 'sql': []}
    rid = 'r' + state['run_id']
    conn = trino.dbapi.connect(host='trino', port=8080, user='team', request_timeout=120)
    spark = None

    def save():
        (ROOT / 'results.json').write_text(json.dumps(state, indent=2))

    def passed(message):
        state['checks'].append(message)
        save()
        print('PASS: ' + message, flush=True)

    def sql(statement):
        state['sql'].append(statement)
        cursor = conn.cursor()
        cursor.execute(statement)
        result = cursor.fetchall()
        cursor.close()
        return result

    def name(engine, suffix='seed'):
        return rid + '_' + engine + '_' + suffix

    def tq(store, table):
        return STORES[store][0] + '.' + table

    def sq(store, table):
        return STORES[store][1] + '.' + table

    def check(actual, expected=ROWS):
        assert sorted(tuple(row) for row in actual) == sorted(expected), (actual, expected)

    def properties(store, table):
        if store == 'hive':
            return " WITH (format='PARQUET', external_location='hdfs://namenode:9000/user/team/federation/" + rid + '/' + table + "')"
        if store == 'ice_s3':
            return " WITH (format='PARQUET', location='s3a://warehouse/federation/" + rid + '/' + table + "')"
        if store in ('ice_hdfs', 'polaris'):
            return " WITH (format='PARQUET', format_version=2)"
        return ''

    def jdbc_options(store, table):
        url, driver = JDBC[store]
        return dict(url=url, table=('public.' if store == 'postgresql' else '') + table,
                    properties={'user': 'team', 'password': 'team1234', 'driver': driver})

    def read(store, table):
        if store in JDBC:
            return spark.read.jdbc(**jdbc_options(store, table))
        spark.catalog.refreshTable(sq(store, table))
        return spark.table(sq(store, table)).select('id', 'name', 'city')

    def write(store, table, frame, create=False):
        if store in JDBC:
            frame.coalesce(1).write.jdbc(mode='error' if create else 'append', **jdbc_options(store, table))
        elif store == 'hive':
            if create:
                spark.sql('CREATE TABLE ' + sq(store, table) + " (id INT, name STRING, city STRING) STORED AS PARQUET LOCATION 'hdfs://namenode:9000/user/team/federation/" + rid + '/' + table + "'")
            frame.select('id', 'name', 'city').coalesce(1).write.mode('append').insertInto(sq(store, table))
        else:
            if create:
                location = " LOCATION 's3a://warehouse/federation/" + rid + '/' + table + "'" if store == 'ice_s3' else ''
                spark.sql('CREATE TABLE ' + sq(store, table) + ' (id INT, name STRING, city STRING) USING iceberg' + location + " TBLPROPERTIES ('format-version'='2', 'engine.hive.enabled'='false')")
            frame.select('id', 'name', 'city').coalesce(1).writeTo(sq(store, table)).append()

    try:
        sql("CREATE SCHEMA IF NOT EXISTS hive.federation_hive WITH (location='hdfs://namenode:9000/user/team/federation/hive')")
        for schema in ('federation_ice_hdfs', 'federation_ice_s3'):
            sql("CREATE SCHEMA IF NOT EXISTS iceberg_hive." + schema + " WITH (location='hdfs://namenode:9000/user/team/federation/" + schema + "')")
        sql('CREATE SCHEMA IF NOT EXISTS polaris.federation_polaris')
        values = "SELECT CAST(id AS INTEGER) id, CAST(name AS VARCHAR) name, CAST(city AS VARCHAR) city FROM (VALUES (1,'Person1','Chennai'),(2,'Person2','Bengaluru'),(3,'Person3','Hyderabad')) AS p(id,name,city)"
        for store in STORES:
            table = name('trino')
            sql('CREATE TABLE ' + tq(store, table) + properties(store, table) + ' AS ' + values)
            check(sql('SELECT id,name,city FROM ' + tq(store, table)))
            passed('Trino ' + store + ': CTAS write/read, exact 3 rows')
        # Every store is both a source and a destination, with an additional INSERT.
        for source in STORES:
            for dest in STORES:
                if source == dest:
                    continue
                table = name('trino', 'from_' + source)
                source_table = tq(source, name('trino'))
                sql('CREATE TABLE ' + tq(dest, table) + properties(dest, table) + ' AS SELECT id,name,city FROM ' + source_table)
                sql('INSERT INTO ' + tq(dest, table) + ' SELECT id,name,city FROM ' + source_table)
                check(sql('SELECT id,name,city FROM ' + tq(dest, table)), ROWS * 2)
                passed('Trino transfer ' + source + ' -> ' + dest + ': CTAS + INSERT/read, exact 6 rows')

        spark = session()
        frame = spark.createDataFrame(ROWS, 'id INT, name STRING, city STRING')
        fourth = [(4, 'Engine', 'Shared')]
        extra = spark.createDataFrame(fourth, frame.schema)
        for store in STORES:
            check(read(store, name('trino')).collect())
            write(store, name('trino'), extra)
            check(sql('SELECT id,name,city FROM ' + tq(store, name('trino'))), ROWS + fourth)
            passed('Shared ' + store + ': Spark reads Trino table, appends; Trino sees exact 4 rows')
            write(store, name('spark'), frame, create=True)
            check(read(store, name('spark')).collect())
            passed('Spark ' + store + ': create/write/read, exact 3 rows')
        for source in STORES:
            for dest in STORES:
                if source == dest:
                    continue
                table = name('spark', 'from_' + source)
                source_frame = read(source, name('spark'))
                write(dest, table, source_frame, create=True)
                write(dest, table, source_frame)
                check(read(dest, table).collect(), ROWS * 2)
                check(sql('SELECT id,name,city FROM ' + tq(dest, table)), ROWS * 2)
                passed('Spark transfer ' + source + ' -> ' + dest + ': create + append/read; Trino confirms exact 6 rows')
        for store in STORES:
            check(sql('SELECT id,name,city FROM ' + tq(store, name('spark'))))
            sql("INSERT INTO " + tq(store, name('spark')) + " VALUES (4,'Engine','Shared')")
            check(read(store, name('spark')).collect(), ROWS + fourth)
            passed('Shared ' + store + ': Trino reads Spark table, appends; Spark sees exact 4 rows')
        for engine in ('trino', 'spark'):
            if engine == 'trino':
                refs = [tq(store, name('trino')) for store in STORES]
                result = sql('SELECT a.id,a.name,a.city FROM ' + refs[0] + ' a ' + ' '.join('JOIN ' + ref + ' ' + alias + ' ON a.id=' + alias + '.id AND a.name=' + alias + '.name AND a.city=' + alias + '.city' for ref, alias in zip(refs[1:], 'bcdef')))
            else:
                for store in STORES:
                    read(store, name('spark')).createOrReplaceTempView('fed_' + store)
                result = spark.sql('SELECT a.id,a.name,a.city FROM fed_mysql a ' + ' '.join('JOIN fed_' + store + ' ' + alias + ' ON a.id=' + alias + '.id AND a.name=' + alias + '.name AND a.city=' + alias + '.city' for store, alias in zip(list(STORES)[1:], 'bcdef'))).collect()
            check(result, ROWS + fourth)
            passed(engine.title() + ': single federated join across all SIX stores, exact 4 rows')
        # Assert that HMS Iceberg really uses HDFS or S3 and Polaris really uses S3.
        for store in ('ice_hdfs', 'ice_s3', 'polaris'):
            for engine in ('trino', 'spark'):
                paths = [row[0] for row in sql('SELECT file_path FROM ' + STORES[store][0] + '."' + name(engine) + '$files"')]
                assert paths and all(path.startswith('hdfs://') if store == 'ice_hdfs' else path.startswith(('s3://', 's3a://')) for path in paths), paths
                passed(engine.title() + ' ' + store + ': physical data-file locations match the required storage')
        state['status'] = 'passed'
    except Exception as exc:
        state['status'] = 'failed'
        state['error'] = str(exc)
        raise
    finally:
        save()
        if spark:
            spark.stop()
        conn.close()
    print('ALL ' + str(len(state['checks'])) + ' CHECKS PASSED; run=' + state['run_id'], flush=True)


if __name__ == '__main__':
    run()
