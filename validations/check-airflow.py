"""Exercise the scheduler and task execution via Airflow 3's authenticated API."""
import time,requests
base='http://airflow:8080'
r=requests.post(base+'/auth/token',json={'username':'team','password':'team1234'},timeout=15);r.raise_for_status()
headers={'Authorization':'Bearer '+r.json()['access_token']}
dag='training_smoke'
for attempt in range(90):
    r=requests.get(base+'/api/v2/dags/'+dag,headers=headers,timeout=15)
    if r.status_code==200:break
    time.sleep(2)
else:raise RuntimeError('DAG not parsed: '+r.text)
requests.patch(base+'/api/v2/dags/'+dag,headers=headers,json={'is_paused':False},timeout=15).raise_for_status()
run_id='verify-'+str(int(time.time()))
r=requests.post(base+'/api/v2/dags/'+dag+'/dagRuns',headers=headers,json={'dag_run_id':run_id,'logical_date':None},timeout=15);r.raise_for_status()
for attempt in range(120):
    r=requests.get(base+'/api/v2/dags/'+dag+'/dagRuns/'+run_id,headers=headers,timeout=15);r.raise_for_status()
    state=r.json()['state']
    if state in ('success','failed'):break
    time.sleep(2)
assert state=='success',r.text
print('PASS: Airflow team authentication, DAG parsing, scheduler and shared-image Hadoop/Kafka task. Run '+run_id)
