import os,json
from pathlib import Path
from pyspark.sql import SparkSession
marker=os.environ['TELEMETRY_MARKER']
spark=(SparkSession.builder.appName('telemetry_probe').master('spark://spark-master:7077').config('spark.driver.host','jupyter.bigdata.svc.cluster.local').config('spark.driver.bindAddress','0.0.0.0').config('spark.driver.port','7078').config('spark.blockManager.port','7079').config('spark.cores.max','1').config('spark.executor.cores','1').config('spark.executor.memory','512m').getOrCreate())
try:
 spark._jvm.org.apache.logging.log4j.LogManager.getLogger('training.telemetry').warn(marker+'-driver')
 def probe(value):
  print(marker+'-executor',flush=True)
  return value*2
 assert spark.sparkContext.parallelize([21],1).map(probe).collect()==[42]
 print('PASS: Spark driver and real distributed executor emitted '+marker,flush=True)
finally:spark.stop()
