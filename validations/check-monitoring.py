"""Standard-library checks through the temporary forwards in verify-monitoring.sh."""
import base64, json, os, time, urllib.request, urllib.error, urllib.parse, uuid
def request(port,path,body=None,auth=False):
    headers={}
    if body is not None: headers['Content-Type']='application/json'
    if auth: headers['Authorization']='Basic '+base64.b64encode(b'team:team1234').decode()
    req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=15) as response: return json.load(response)
assert request(13000,'/api/health')['database']=='ok'
for uid in ('prometheus',):
    result=request(13000,f'/api/datasources/uid/{uid}/health',auth=True)
    assert result['status']=='OK',result
assert request(13000,'/api/dashboards/uid/training-performance',auth=True)['dashboard']['title']=='Training workload performance'
required_jobs={'prometheus','grafana','jaeger','kubernetes-cadvisor','loki','alloy'}
for attempt in range(30):
    targets=request(19090,'/api/v1/targets')['data']['activeTargets']
    active=[t for t in targets if t['labels']['job'] in required_jobs]
    if {t['labels']['job'] for t in active}==required_jobs and all(t['health']=='up' for t in active): break
    time.sleep(3)
else: raise AssertionError([(t['labels']['job'],t['health'],t.get('lastError')) for t in active])
for metric in ('container_memory_working_set_bytes','container_cpu_usage_seconds_total'):
    query=urllib.parse.quote(metric+'{namespace="bigdata",container!="",container!="POD"}')
    result=request(19090,'/api/v1/query?query='+query)['data']['result']
    assert result,metric
    assert any(r['metric'].get('pod')==os.environ.get('VERIFY_EXPECT_POD','prometheus-0') for r in result),metric
print('PASS: healthy scrape targets, workload CPU/memory, Grafana datasources and dashboard.')
trace_id=os.environ.get('VERIFY_TRACE_ID') or uuid.uuid4().hex
if not os.environ.get('VERIFY_TRACE_ID'):
    now=time.time_ns()
    body={'resourceSpans':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'training-observability-check'}}]},'scopeSpans':[{'scope':{'name':'training-check'},'spans':[{'traceId':trace_id,'spanId':uuid.uuid4().hex[:16],'name':'verify-persistent-trace','kind':1,'startTimeUnixNano':str(now-10000000),'endTimeUnixNano':str(now),'status':{'code':1}}]}]}]}
    request(14318,'/v1/traces',body)
for attempt in range(30):
    try:
        result=request(16687,'/api/traces/'+trace_id)
    except urllib.error.HTTPError as error:
        if error.code != 404: raise
        result={'data':[]}
    if result.get('data'): break
    time.sleep(1)
else: raise AssertionError(result)
assert result['data'][0]['spans'][0]['operationName']=='verify-persistent-trace',result
print('PASS: trace ingestion/query; trace ID '+trace_id)
