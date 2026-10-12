"""Native Hive + Trino + Spark interoperability for external file encodings."""
import json
import sys
import time
from pathlib import Path
import trino
from pyhive import hive
sys.path.insert(0, '/workspace/pyspark/streaming')
from streaming_lab import session


def run():
    rows = [(1, 'Person1', 'Chennai'), (2, 'Person2', 'Bengaluru'), (3, 'Person3', 'Hyderabad')]
    rid = str(time.time_ns())
    result = {'run_id': rid, 'status': 'running', 'checks': []}
    spark = session()
    tc = trino.dbapi.connect(host='trino', port=8080, user='team').cursor()
    hc = hive.Connection(host='hiveserver2', port=10000, username='team', auth='NONE').cursor()
    hc.execute('SET hive.fetch.task.conversion=more')
    def check(actual, expected):
        assert sorted((int(r[0]), r[1], r[2]) for r in actual) == sorted(expected), actual
    def passed(message):
        result['checks'].append(message)
        print('PASS: ' + message, flush=True)
    try:
        frame = spark.createDataFrame(rows, 'id INT, name STRING, city STRING')
        for fmt in ('csv', 'json', 'orc', 'parquet'):
            table = 'federation_hive.fmt_' + fmt + '_' + rid
            path = 'hdfs://namenode:9000/user/team/federation/formats/' + rid + '/' + fmt
            columns = 'id VARCHAR,name VARCHAR,city VARCHAR' if fmt == 'csv' else 'id INTEGER,name VARCHAR,city VARCHAR'
            tc.execute('CREATE TABLE hive.' + table + ' (' + columns + ") WITH (format='" + fmt.upper() + "',external_location='" + path + "')")
            tc.fetchall()
            tc.execute('INSERT INTO hive.' + table + (" VALUES ('1','Person1','Chennai'),('2','Person2','Bengaluru'),('3','Person3','Hyderabad')" if fmt == 'csv' else " VALUES (1,'Person1','Chennai'),(2,'Person2','Bengaluru'),(3,'Person3','Hyderabad')"))
            tc.fetchall()
            tc.execute('SELECT id,name,city FROM hive.' + table)
            check(tc.fetchall(), rows)
            check(spark.read.schema(frame.schema).format(fmt).load(path).collect(), rows)
            hc.execute('SELECT id,name,city FROM ' + table)
            check(hc.fetchall(), rows)
            passed(fmt.upper() + ': Trino write; Trino, native Hive and Spark read exact 3 rows')
            frame.coalesce(1).write.mode('append').format(fmt).save(path)
            check(spark.read.schema(frame.schema).format(fmt).load(path).collect(), rows * 2)
            tc.execute('SELECT id,name,city FROM hive.' + table)
            check(tc.fetchall(), rows * 2)
            hc.execute('SELECT id,name,city FROM ' + table)
            check(hc.fetchall(), rows * 2)
            passed(fmt.upper() + ': Spark append; Spark, Trino and native Hive read exact 6 rows')
        # Existing lesson tables now use the common JSON SerDe.
        people = [(1,'Person1',28,'Chennai'),(2,'Person2',35,'Bengaluru'),(3,'Person3',31,'Hyderabad')]
        for table in ('hive.course_person.person', 'hive.course_person.person_csv', 'hive.course_person.person_json', 'hive.course_person.person_orc', 'hive.course_person.person_parquet', 'polaris.course_person.person_parquet', 'polaris.course_person.person_orc'):
            tc.execute('SELECT id,name,age,city FROM ' + table)
            assert sorted(tuple(r) for r in tc.fetchall()) == people
            passed('Trino reads earlier lesson ' + table + ': exact 3 people')
        result['status'] = 'passed'
    except Exception as exc:
        result['status'] = 'failed'
        result['error'] = str(exc)
        raise
    finally:
        Path('/workspace/pyspark/federation/formats-results.json').write_text(json.dumps(result,indent=2))
        tc.close()
        hc.close()
        spark.stop()
    print('ALL ' + str(len(result['checks'])) + ' FORMAT CHECKS PASSED', flush=True)


if __name__ == '__main__':
    run()
