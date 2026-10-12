"""Run inside Jupyter after the root verification script emits markers."""
import os,json,time
from pathlib import Path
import requests
marker=os.environ['TELEMETRY_MARKER']
checks=[]
def passed(message):
 checks.append(message);print('PASS: '+message,flush=True)
def logs(query):
 response=requests.get('http://loki:3100/loki/api/v1/query_range',params={'query':query,'start':str(time.time_ns()-3600*10**9),'end':str(time.time_ns()),'limit':200},timeout=20);response.raise_for_status()
 return response.json()['data']['result']
expected={'airflow':marker+'-airflow','hiveserver2':marker+'-hive','namenode':marker+'-hdfs','prometheus':marker+'-prometheus','jupyter':marker+'-driver','spark-worker':marker+'-executor'}
for attempt in range(40):
 missing=[component for component,text in expected.items() if not logs('{namespace="bigdata",component="'+component+'"} |= "'+text+'"')]
 if not missing:break
 time.sleep(3)
else:raise AssertionError('Missing collected log markers: '+str(missing))
for component in expected:passed('Actual '+component+' log collected in Loki')
for component in ('kafka','datanode','hive-metastore','spark-master','airflow','postgres','mysql','polaris','seaweedfs','grafana','alloy','loki'):
 assert logs('{namespace="bigdata",component="'+component+'"}'),component
passed('All other running service components have searchable logs')
for attempt in range(30):
 targets=requests.get('http://prometheus:9090/api/v1/targets',timeout=20).json()['data']['activeTargets']
 required={'prometheus','grafana','jaeger','kubernetes-cadvisor','loki','alloy','hdfs-namenode','hdfs-datanode','spark-master','spark-worker'}
 active=[t for t in targets if t['labels']['job'] in required]
 if {t['labels']['job'] for t in active}==required and all(t['health']=='up' for t in active):break
 time.sleep(3)
else:raise AssertionError([(t['labels'],t['health'],t.get('lastError')) for t in targets])
for job in ('hdfs-namenode','hdfs-datanode','spark-master','spark-worker','loki','alloy'):
 query='count({job="'+job+'",__name__!~"up|scrape_.*"})'
 result=requests.get('http://prometheus:9090/api/v1/query',params={'query':query},timeout=20).json()['data']['result']
 assert result and float(result[0]['value'][1])>0,job
 passed('Prometheus receives actual '+job+' metrics')
grafana=requests.Session();grafana.auth=('team','team1234')
response=grafana.get('http://grafana:3000/api/datasources/uid/loki/health',timeout=20);response.raise_for_status();assert response.json()['status']=='OK'
response=grafana.get('http://grafana:3000/api/dashboards/uid/training-logs',timeout=20);response.raise_for_status();assert response.json()['dashboard']['title']=='Training centralized logs'
passed('Grafana Loki datasource healthy and centralized dashboard provisioned')
response=grafana.get('http://grafana:3000/api/datasources/proxy/uid/loki/loki/api/v1/query_range',params={'query':'{component="namenode"} |= "'+marker+'-hdfs"','start':str(time.time_ns()-3600*10**9),'end':str(time.time_ns())},timeout=20);response.raise_for_status();assert response.json()['data']['result']
passed('Grafana actually queries collected logs through its Loki datasource')
from pyhive import hive
connection=hive.Connection(host='hiveserver2',port=10000,username='team',auth='NONE');cursor=connection.cursor();cursor.execute('SET hive.fetch.task.conversion=more')
cursor.execute('SHOW DATABASES');databases=[row[0] for row in cursor.fetchall()]
if 'course_person' in databases:
 cursor.execute('SHOW TABLES IN course_person');tables=[row[0] for row in cursor.fetchall()]
 for table in ('person','person_csv','person_json','person_orc','person_parquet'):
  if table in tables:
   cursor.execute('SELECT * FROM course_person.'+table)
   assert len(cursor.fetchall())==3,table
 passed('Existing Hive person lesson tables remain readable')
else:
 cursor.execute('SELECT 1');assert cursor.fetchall()==[(1,)]
 passed('Hive SQL connection and constant query work; person lesson not installed')
cursor.close();connection.close()
results = Path('/workspace/validations/results/results.json')
results.parent.mkdir(parents=True, exist_ok=True)
results.write_text(json.dumps({'marker':marker,'checks':checks},indent=2))
