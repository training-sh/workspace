"""Run inside the workbench pod; exercises actual installed connectors."""
import os,subprocess,tempfile,time,sys
import importlib.metadata
import pyspark
from pathlib import Path
import requests
from nbclient import NotebookClient
import nbformat
from pyspark.sql import SparkSession
assert sys.prefix == '/opt/venv', sys.prefix
assert pyspark.__version__ == '3.5.9'
assert pyspark.__file__.startswith('/opt/spark/python/'), pyspark.__file__
try:
    importlib.metadata.distribution('pyspark')
except importlib.metadata.PackageNotFoundError:
    pass
else:
    raise AssertionError('PySpark must not be installed with pip')
subprocess.run(['python', '-m', 'pip', 'check'], check=True)
print('PASS: shared Python environment, bundled PySpark and consistent dependencies.')
token=os.environ['JUPYTER_TOKEN']
base='http://127.0.0.1:8888'
headers={'Authorization':'token '+token}
r=requests.get(base+'/api',headers=headers,timeout=15);r.raise_for_status()
r=requests.post(base+'/api/terminals',headers=headers,json={},timeout=15);r.raise_for_status()
terminal=r.json()['name']
requests.delete(base+'/api/terminals/'+terminal,headers=headers,timeout=15).raise_for_status()
book=nbformat.read('/workspace/notebooks/00-workbench.ipynb',as_version=4)
NotebookClient(book,timeout=180,kernel_name='pyspark').execute()
print('PASS: Jupyter authentication, terminal creation and real notebook kernel execution.')
topic='workbench-check-'+str(int(time.time()))
bootstrap=os.environ['KAFKA_BOOTSTRAP_SERVERS']
subprocess.run(['kafka-topics.sh','--bootstrap-server',bootstrap,'--create','--topic',topic,'--partitions','1','--replication-factor','1'],check=True)
warehouse=Path(tempfile.mkdtemp(prefix='training-iceberg-',dir='/tmp'))
spark=(SparkSession.builder.appName('shared-image-connectors').master('local[2]')
       .config('spark.databricks.delta.snapshotPartitions','2')
       .config('spark.sql.extensions','io.delta.sql.DeltaSparkSessionExtension,org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions')
       .config('spark.sql.catalog.spark_catalog','org.apache.spark.sql.delta.catalog.DeltaCatalog')
       .config('spark.sql.catalog.lab','org.apache.iceberg.spark.SparkCatalog')
       .config('spark.sql.catalog.lab.type','hadoop')
       .config('spark.sql.catalog.lab.warehouse',warehouse.as_uri()).getOrCreate())
try:
    spark.createDataFrame([('shared-image-kafka',)],['value']).write.format('kafka').option('kafka.bootstrap.servers',bootstrap).option('topic',topic).save()
    records=(spark.read.format('kafka').option('kafka.bootstrap.servers',bootstrap).option('subscribe',topic).option('startingOffsets','earliest').option('endingOffsets','latest').load())
    assert records.selectExpr('CAST(value AS STRING) AS value').first()['value']=='shared-image-kafka'
    delta=(warehouse/'delta').as_uri()
    spark.range(5).write.format('delta').save(delta)
    assert spark.read.format('delta').load(delta).count()==5
    spark.sql('CREATE NAMESPACE lab.checks')
    spark.sql('CREATE TABLE lab.checks.numbers (id BIGINT) USING iceberg')
    spark.sql('INSERT INTO lab.checks.numbers VALUES (1),(2)')
    assert spark.table('lab.checks.numbers').count()==2
    print('PASS: Spark 3.5.9 Kafka batch write/read, Delta 3.3.2 and Iceberg 1.10.0.')
finally:
    spark.stop()
    subprocess.run(['kafka-topics.sh','--bootstrap-server',bootstrap,'--delete','--topic',topic],check=True)
