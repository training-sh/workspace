"""Build a dashboard for the lab's existing YARN JMX exporters."""
import json
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
prom = {'type': 'prometheus', 'uid': 'prometheus'}
loki = {'type': 'loki', 'uid': 'loki'}
source = 'https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-common/Metrics.html'
dashboard = {
    'uid': 'training-yarn', 'title': 'YARN - applications, containers, JVM and logs',
    'description': 'Existing YARN JMX exporters: ResourceManager, NodeManager and HistoryServer. Root QueueMetrics selected once; application logs collected by the existing NodeManager sidecar.',
    'schemaVersion': 39, 'version': 1, 'tags': ['training', 'yarn', 'hadoop', 'jvm'],
    'refresh': '15s', 'time': {'from': 'now-30m', 'to': 'now'},
    'links': [{'type': 'link', 'title': 'Hadoop metrics reference', 'targetBlank': True, 'url': source}],
    'templating': {'list': []}, 'panels': [],
}


def add(title, targets, kind='timeseries', unit='short', description=''):
    i = len(dashboard['panels'])
    pos = ({'x': (i % 4) * 6, 'y': (i // 4) * 4, 'w': 6, 'h': 4} if i < 12 else
           {'x': ((i - 12) % 2) * 12, 'y': 12 + ((i - 12) // 2) * 8, 'w': 12, 'h': 8})
    ds = loki if kind == 'logs' else prom
    p = {'id': i + 1, 'title': title, 'type': kind, 'description': description, 'gridPos': pos,
         'datasource': ds, 'targets': [{'refId': chr(65 + n), 'expr': expr, 'legendFormat': label, 'datasource': ds}
                                     for n, (label, expr) in enumerate(targets)],
         'fieldConfig': {'defaults': {'unit': unit, 'min': 0}, 'overrides': []}}
    if kind == 'stat':
        p['fieldConfig']['defaults']['color'] = {'mode': 'fixed', 'fixedColor': 'blue'}
        if 'scrape health' in title:
            p['fieldConfig']['defaults'].update(color={'mode': 'thresholds'}, thresholds={
                'mode': 'absolute', 'steps': [{'color': 'red', 'value': None}, {'color': 'green', 'value': 1}]})
        p['options'] = {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'colorMode': 'value', 'graphMode': 'none'}
    elif kind == 'logs':
        for target in p['targets']:
            target['maxLines'] = 200
        p['options'] = {'showTime': True, 'showLabels': True, 'wrapLogMessage': True, 'sortOrder': 'Descending', 'enableLogDetails': True}
    else:
        p['options'] = {'legend': {'displayMode': 'table', 'placement': 'bottom', 'calcs': ['lastNotNull']}, 'tooltip': {'mode': 'multi', 'sort': 'desc'}}
    dashboard['panels'].append(p)



def queue(suffix):
    return 'hadoop_resourcemanager_' + suffix + '{job="resourcemanager-jmx",name="QueueMetrics",q0="root",q1=""}'
def cluster(suffix):
    return 'hadoop_resourcemanager_' + suffix + '{job="resourcemanager-jmx",name="ClusterMetrics"}'
def node(suffix):
    return 'hadoop_nodemanager_' + suffix + '{job="nodemanager-jmx",name="NodeManagerMetrics"}'
def java(name, extra=''):
    return name + '{job=~"resourcemanager-jmx|nodemanager-jmx|historyserver-jmx"' + extra + '}'
for title, expr in [
 ('ResourceManager scrape health','up{job="resourcemanager-jmx"}'),
 ('NodeManager scrape health','up{job="nodemanager-jmx"}'),
 ('HistoryServer scrape health','up{job="historyserver-jmx"}'),
 ('Active NodeManagers',cluster('numactivenms')),
 ('Running applications',queue('appsrunning')),('Pending applications',queue('appspending')),
 ('Completed applications',queue('appscompleted')),('Failed applications',queue('appsfailed')),
 ('Killed applications',queue('appskilled')),('Allocated containers',queue('allocatedcontainers')),
 ('Lost NodeManagers',cluster('numlostnms')),('Unhealthy NodeManagers',cluster('numunhealthynms'))]:
    add(title,[(title,expr)],'stat')
add('Application states',[(x,queue('apps'+x)) for x in ('running','pending','completed','failed','killed')])
add('Application submissions per second',[('Submitted', 'rate('+queue('appssubmitted')+'[2m])')],unit='ops')
add('Scheduler memory',[(x,queue(x+'mb')+' * 1048576') for x in ('allocated','available')],unit='bytes',description='YARN scheduler capacity, not Kubernetes pod memory.')
add('Scheduler virtual cores',[(x,queue(x+'vcores')) for x in ('allocated','available')])
add('Scheduler containers',[('Allocated',queue('allocatedcontainers'))])
add('NodeManager container states',[(x,node('containers'+x)) for x in ('running','initing','completed','failed','killed')])
add('Containers launched per second',[('Launched','rate('+node('containerslaunched')+'[2m])')],unit='ops')
add('NodeManager virtual cores',[(x,node(x+'vcores')) for x in ('allocated','available')])
add('YARN JVM heap', [('{{job}} '+x,java('jvm_memory_'+x+'_bytes',',area="heap"')) for x in ('used','committed','max')],unit='bytes')
add('YARN JVM heap utilization',[('{{job}}','100 * '+java('jvm_memory_used_bytes',',area="heap"')+' / '+java('jvm_memory_max_bytes',',area="heap"'))],unit='percent')
add('YARN JVM non-heap memory',[('{{job}} '+x,java('jvm_memory_'+x+'_bytes',',area="nonheap"')) for x in ('used','committed')],unit='bytes')
add('YARN garbage collections per second',[('{{job}} {{gc}}','rate('+java('jvm_gc_collection_seconds_count')+'[2m])')],unit='ops')
add('YARN GC time per second',[('{{job}} {{gc}}','rate('+java('jvm_gc_collection_seconds_sum')+'[2m])')],unit='s')
add('YARN JVM threads',[('{{job}}',java('jvm_threads_current'))])
add('YARN pod CPU',[('{{pod}}','sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bigdata",pod=~"(resourcemanager|nodemanager|historyserver)-.*",container=~"resourcemanager|nodemanager|historyserver"}[2m]))')],unit='cores')
add('YARN pod memory',[('{{pod}}','sum by (pod) (container_memory_working_set_bytes{namespace="bigdata",pod=~"(resourcemanager|nodemanager|historyserver)-.*",container=~"resourcemanager|nodemanager|historyserver"})')],unit='bytes',description='NodeManager container includes its launched application JVMs.')
for title,component,container in [('ResourceManager logs','resourcemanager','resourcemanager'),('NodeManager logs','nodemanager','nodemanager'),('HistoryServer logs','historyserver','historyserver'),('YARN application logs','nodemanager','file-logs')]:
    add(title,[('Logs','{namespace="bigdata",component="'+component+'",container="'+container+'"}')],'logs')

cm = {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'grafana-dashboard-yarn', 'namespace': 'bigdata',
      'annotations': {'training.grafana/template': 'native-yarn-v1', 'training.grafana/source': source}},
      'data': {'yarn.json': json.dumps(dashboard, indent=2) + '\n'}}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(str, lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None))
path = root / 'monitoring/grafana-dashboard-yarn.yaml'
path.write_text('# Template: native-yarn-v1, matched to the installed YARN JMX endpoints.\n'
                '# Generated by validations/build-yarn-dashboard.py.\n' + yaml.dump(cm, Dumper=Dumper, sort_keys=False), encoding='utf-8')
print(path)
