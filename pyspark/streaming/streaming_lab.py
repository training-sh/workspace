"""Kafka -> native Iceberg streaming, durable restart, and Iceberg streaming reads."""
import json, os, sys, time
from pathlib import Path
import boto3
import mysql.connector
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
POLARIS='http://polaris:8181/api/catalog'
S3='http://seaweedfs:8333'
MASTER='spark://spark-master:7077'
STATE=Path('/workspace/pyspark/streaming/state.json')
BOOTSTRAP='kafka:9092'
SCHEMA='id INT, name STRING, city STRING'

def session():
    builder = (SparkSession.builder.appName('kafka_iceberg_streaming_validation').master(MASTER)
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
        .config('spark.openlineage.vendors.iceberg.metricsReporterDisabled', 'true')
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
    for catalog in ('hive_hdfs', 'hive_s3'):
        prefix='spark.sql.catalog.'+catalog+'.'
        builder=builder.config('spark.sql.catalog.'+catalog,'org.apache.iceberg.spark.SparkCatalog').config(prefix+'type','hive').config(prefix+'uri','thrift://hive-metastore:9083').config(prefix+'warehouse','hdfs://namenode:9000/user/team/streaming/'+catalog).config(prefix+'engine.hive.enabled','false')
        if catalog == 'hive_s3':
            for k,v in {'io-impl':'org.apache.iceberg.aws.s3.S3FileIO','s3.endpoint':S3,'s3.path-style-access':'true','s3.access-key-id':os.environ['AWS_ACCESS_KEY_ID'],'s3.secret-access-key':os.environ['AWS_SECRET_ACCESS_KEY'],'client.region':'us-east-1'}.items():
                builder=builder.config(prefix+k,v)
    for k,v in {'endpoint':S3,'path.style.access':'true','connection.ssl.enabled':'false','access.key':os.environ['AWS_ACCESS_KEY_ID'],'secret.key':os.environ['AWS_SECRET_ACCESS_KEY'],'aws.credentials.provider':'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider'}.items():
        builder=builder.config('spark.hadoop.fs.s3a.'+k,v)
    spark=builder.getOrCreate()
    spark.sparkContext.setLogLevel('ERROR')
    return spark

def wait(query):
    if not query.awaitTermination(180):
        query.stop()
        raise TimeoutError('Streaming query exceeded 180 seconds')
    if query.exception(): raise query.exception()

def produce(topic, ids):
    producer=Producer({'bootstrap.servers':BOOTSTRAP,'enable.idempotence':True})
    errors=[]
    def delivered(error,message):
        if error: errors.append(str(error))
    for i in ids:
        producer.produce(topic,key=str(i),value=json.dumps({'id':i,'name':'Person'+str(i),'city':'Chennai' if i%2 else 'Bengaluru'}),partition=i%3,on_delivery=delivered)
    assert producer.flush(30)==0 and not errors, errors

def assert_rows(frame, count):
    rows=sorted((r.id,r.name,r.city) for r in frame.collect())
    expected=[(i,'Person'+str(i),'Chennai' if i%2 else 'Bengaluru') for i in range(1,count+1)]
    assert rows==expected, (rows,expected)

def run(phase):
    if phase=='initial':
        state={'run_id':str(time.time_ns()),'checks':[]}
        STATE.write_text(json.dumps(state,indent=2))
    else: state=json.loads(STATE.read_text())
    spark=session()
    try:
        for catalog in ('hive_hdfs','hive_s3','polaris'):
            namespace='stream_'+catalog
            table=catalog+'.'+namespace+'.person_'+state['run_id']
            topic='stream-'+catalog+'-'+state['run_id']
            root='hdfs://namenode:9000/user/team/streaming/checkpoints/'+state['run_id']+'/'+catalog
            read_checkpoint=root+'/iceberg' if catalog=='hive_hdfs' else 's3a://warehouse/'+('iceberg' if catalog=='polaris' else 'hive-iceberg')+'/streaming-checkpoints/'+state['run_id']+'/'+catalog+'/read'
            if phase=='initial':
                admin=AdminClient({'bootstrap.servers':BOOTSTRAP})
                for future in admin.create_topics([NewTopic(topic,3,1)]).values(): future.result(30)
                spark.sql('CREATE NAMESPACE IF NOT EXISTS '+catalog+'.'+namespace)
                location=" LOCATION 's3a://warehouse/hive-iceberg/"+state['run_id']+"/person'" if catalog=='hive_s3' else ''
                spark.sql('CREATE TABLE '+table+' ('+SCHEMA+') USING iceberg PARTITIONED BY (city)'+location+" TBLPROPERTIES ('format-version'='2')")
            count=3 if phase=='initial' else 6
            if phase!='replay': produce(topic,range(1,4) if phase=='initial' else range(4,7))
            source=(spark.readStream.format('kafka').option('kafka.bootstrap.servers',BOOTSTRAP).option('subscribe',topic).option('startingOffsets','earliest').option('failOnDataLoss','true').load().select(from_json(col('value').cast('string'),SCHEMA).alias('person')).select('person.*'))
            wait(source.writeStream.format('iceberg').outputMode('append').option('fanout-enabled','true').option('checkpointLocation',root+'/kafka').trigger(availableNow=True).toTable(table))
            assert_rows(spark.table(table),count)
            wait(spark.readStream.format('iceberg').load(table).writeStream.format('parquet').option('path',root+'/readback').option('checkpointLocation',read_checkpoint).trigger(availableNow=True).start())
            assert_rows(spark.read.parquet(root+'/readback'),count)
            files=spark.sql('SELECT file_path FROM '+table+'.files').collect()
            assert files
            s3=boto3.client('s3',endpoint_url=S3,aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],region_name='us-east-1')
            for file in files:
                if catalog=='hive_hdfs':
                    path=spark._jvm.org.apache.hadoop.fs.Path(file.file_path)
                    assert path.getFileSystem(spark._jsc.hadoopConfiguration()).getFileStatus(path).getLen()>0
                else:
                    bucket,key=file.file_path.split('://',1)[1].split('/',1)
                    assert s3.head_object(Bucket=bucket,Key=key)['ContentLength']>0
            if catalog.startswith('hive_'):
                connection=mysql.connector.connect(host='mysql',user='team',password='team1234',database='hive_metastore')
                cursor=connection.cursor()
                cursor.execute("SELECT p.PARAM_VALUE FROM TABLE_PARAMS p JOIN TBLS t ON t.TBL_ID=p.TBL_ID JOIN DBS d ON d.DB_ID=t.DB_ID WHERE d.NAME=%s AND t.TBL_NAME=%s AND p.PARAM_KEY='metadata_location'",(namespace,'person_'+state['run_id']))
                metadata=cursor.fetchone()[0]
                cursor.close(); connection.close()
                if catalog=='hive_s3':
                    bucket,key=metadata.split('://',1)[1].split('/',1)
                    document=json.loads(s3.get_object(Bucket=bucket,Key=key)['Body'].read())
                    assert document['current-snapshot-id']>0
                else:
                    path=spark._jvm.org.apache.hadoop.fs.Path(metadata)
                    assert path.getFileSystem(spark._jsc.hadoopConfiguration()).exists(path)
            path=spark._jvm.org.apache.hadoop.fs.Path(root+'/kafka/commits/0')
            assert path.getFileSystem(spark._jsc.hadoopConfiguration()).exists(path)
            message=f'{phase}: {catalog}: Kafka 3 partitions -> partitioned Iceberg -> streaming Parquet readback; {count} exact rows, durable checkpoints, physical files verified'
            state['checks'].append(message)
            STATE.write_text(json.dumps(state,indent=2))
            print('PASS: '+message,flush=True)
    finally: spark.stop()
    if phase=='replay':
        Path('/workspace/pyspark/streaming/results.json').write_text(json.dumps(state,indent=2))

if __name__=='__main__': run(sys.argv[1] if len(sys.argv)>1 else 'initial')
