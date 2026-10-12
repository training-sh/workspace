"""Render internal Service addresses; writable per-pod config, never host /opt."""
import os,pathlib,socket,shutil,xml.etree.ElementTree as ET
root=pathlib.Path('/opt/training/conf')
def xml(folder,name,props):
    target=root/folder; target.mkdir(parents=True,exist_ok=True)
    tree=ET.Element('configuration')
    for key,value in props.items():
        p=ET.SubElement(tree,'property'); ET.SubElement(p,'name').text=key; ET.SubElement(p,'value').text=str(value)
    ET.indent(tree)
    (target/name).write_text(ET.tostring(tree,encoding='unicode'))
nn=os.environ.get('HDFS_URI','hdfs://namenode:9000')
xml('hadoop','core-site.xml',{'fs.defaultFS':nn,'hadoop.tmp.dir':'/tmp/hadoop-team','fs.s3a.impl':'org.apache.hadoop.fs.s3a.S3AFileSystem','fs.s3a.endpoint':'http://seaweedfs:8333','fs.s3a.path.style.access':'true','fs.s3a.connection.ssl.enabled':'false','fs.s3a.aws.credentials.provider':'org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider','fs.s3a.access.key':os.environ.get('AWS_ACCESS_KEY_ID','team'),'fs.s3a.secret.key':os.environ.get('AWS_SECRET_ACCESS_KEY','team1234')})
xml('hadoop','hdfs-site.xml',{'dfs.replication':1,'dfs.namenode.name.dir':'file:///data/namenode','dfs.datanode.data.dir':'file:///data/datanode','dfs.permissions.enabled':'true','dfs.namenode.rpc-bind-host':'0.0.0.0','dfs.namenode.http-address':'0.0.0.0:9870','dfs.datanode.hostname':os.environ.get('DATANODE_HOST',socket.getfqdn()),'dfs.client.use.datanode.hostname':'true','dfs.datanode.use.datanode.hostname':'true'})
xml('hadoop','yarn-site.xml',{'yarn.resourcemanager.hostname':'resourcemanager','yarn.resourcemanager.bind-host':'0.0.0.0','yarn.nodemanager.hostname':os.environ.get('POD_IP',socket.getfqdn()),'yarn.nodemanager.aux-services':'mapreduce_shuffle','yarn.nodemanager.resource.memory-mb':2048,'yarn.nodemanager.resource.cpu-vcores':2,'yarn.scheduler.minimum-allocation-mb':256,'yarn.scheduler.maximum-allocation-mb':2048,'yarn.scheduler.minimum-allocation-vcores':1,'yarn.nodemanager.local-dirs':'/data/yarn/local','yarn.nodemanager.log-dirs':'/data/yarn/log','yarn.nodemanager.vmem-check-enabled':'false','yarn.nodemanager.env-whitelist':'JAVA_HOME,HADOOP_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,HADOOP_YARN_HOME,HADOOP_MAPRED_HOME,PATH,PYSPARK_PYTHON,PYTHONPATH','yarn.log-aggregation-enable':'false'})
xml('hadoop','mapred-site.xml',{'mapreduce.framework.name':'yarn','mapreduce.application.classpath':'/opt/hadoop/share/hadoop/mapreduce/*:/opt/hadoop/share/hadoop/mapreduce/lib/*','mapreduce.map.memory.mb':512,'mapreduce.map.java.opts':'-Xmx384m','mapreduce.reduce.memory.mb':512,'mapreduce.reduce.java.opts':'-Xmx384m','yarn.app.mapreduce.am.resource.mb':512,'yarn.app.mapreduce.am.command-opts':'-Xmx384m','mapreduce.jobhistory.address':'historyserver:10020','mapreduce.jobhistory.webapp.address':'historyserver:19888'})
xml('hadoop','capacity-scheduler.xml',{'yarn.scheduler.capacity.root.queues':'default','yarn.scheduler.capacity.root.default.capacity':100,'yarn.scheduler.capacity.root.default.maximum-capacity':100,'yarn.scheduler.capacity.root.default.state':'RUNNING','yarn.scheduler.capacity.root.default.acl_submit_applications':'*','yarn.scheduler.capacity.root.default.acl_administer_queue':'*','yarn.scheduler.capacity.maximum-am-resource-percent':0.5})
# The advertised history address is a Service; bind the daemon on the pod.
tree=ET.parse(root/'hadoop'/'mapred-site.xml'); prop=ET.SubElement(tree.getroot(),'property'); ET.SubElement(prop,'name').text='mapreduce.jobhistory.bind-host'; ET.SubElement(prop,'value').text='0.0.0.0'; ET.indent(tree); tree.write(root/'hadoop'/'mapred-site.xml',encoding='unicode')
for name in ('log4j.properties', 'log4j2.properties'):
    source=pathlib.Path('/opt/hadoop/etc/hadoop')/name
    if source.exists(): shutil.copyfile(source,root/'hadoop'/name)
props={'hive.metastore.uris':'thrift://hive-metastore:9083','hive.metastore.warehouse.dir':'/user/hive/warehouse','hive.exec.scratchdir':'/tmp/hive','hive.exec.local.scratchdir':'/tmp/hive-local','hive.execution.engine':'mr','hive.fetch.task.conversion':'none','hive.server2.thrift.bind.host':'0.0.0.0','hive.server2.enable.doAs':'false','hive.server2.authentication':'NONE','hive.metastore.schema.verification':'true','datanucleus.schema.autoCreateAll':'false','javax.jdo.option.ConnectionURL':'jdbc:mysql://mysql:3306/hive_metastore?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC','javax.jdo.option.ConnectionDriverName':'com.mysql.cj.jdbc.Driver','javax.jdo.option.ConnectionUserName':'team','javax.jdo.option.ConnectionPassword':os.environ.get('HIVE_DB_PASSWORD','team1234')}
xml('hive','hive-site.xml',props)
spark=root/'spark'; spark.mkdir(exist_ok=True)
# Do not force Hive or Polaris onto every Spark session. Lessons select catalogs.
(spark/'spark-defaults.conf').write_text('spark.master local[2]\nspark.driver.memory 512m\nspark.executor.memory 512m\nspark.sql.shuffle.partitions 2\nspark.pyspark.python /opt/venv/bin/python\nspark.executorEnv.PYSPARK_PYTHON /opt/venv/bin/python\n')
# OpenLineage is built into the image; no Maven downloads in account jobs.
with (spark/'spark-defaults.conf').open('a') as settings:
    settings.write('spark.extraListeners io.openlineage.spark.agent.OpenLineageSparkListener\nspark.openlineage.transport.type http\nspark.openlineage.transport.url '+os.environ.get('OPENLINEAGE_URL','http://marquez:5000')+'\nspark.openlineage.transport.endpoint /api/v1/lineage\nspark.openlineage.namespace training\n')
trino=root/'trino'; trino.mkdir(exist_ok=True); (trino/'catalog').mkdir(exist_ok=True)
(trino/'node.properties').write_text(f'node.environment=training\nnode.id={socket.gethostname()}\nnode.data-dir=/data/trino\n')
(trino/'jvm.config').write_text('-server\n-Xmx768M\n-XX:+UseG1GC\n-XX:G1HeapRegionSize=32M\n-XX:+ExitOnOutOfMemoryError\n')
(trino/'config.properties').write_text('coordinator=true\nnode-scheduler.include-coordinator=true\nhttp-server.http.port=8080\ndiscovery.uri=http://trino:8080\nquery.max-memory=256MB\nquery.max-memory-per-node=256MB\nmemory.heap-headroom-per-node=256MB\n')
(trino/'catalog'/'tpch.properties').write_text('connector.name=tpch\n')
