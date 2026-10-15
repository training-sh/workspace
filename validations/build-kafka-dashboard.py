"""Adapt Grafana template 7589 into a separate provisioned lab ConfigMap."""
import hashlib
import json
from pathlib import Path
import urllib.request
import yaml

root = Path(__file__).resolve().parents[1]
url = 'https://grafana.com/api/dashboards/7589/revisions/5/download'
raw = urllib.request.urlopen(url, timeout=30).read()
source = json.loads(raw)
prom = {'type': 'prometheus', 'uid': 'prometheus'}
loki = {'type': 'loki', 'uid': 'loki'}
dashboard = {
    'uid': 'training-kafka', 'title': 'Kafka - topics, consumers and logs',
    'description': 'Adapted from Grafana.com Kafka Exporter Overview 7589 revision 5. '
                   'Modern panels, fixed lab datasource UIDs, scoped exporter queries, '
                   'topic/group filters, broker health, resource metrics and Loki logs.',
    'schemaVersion': 39, 'version': 1, 'tags': ['training', 'kafka', 'template-7589'],
    'refresh': '15s', 'time': {'from': 'now-30m', 'to': 'now'},
    'links': [{'title': 'Source template 7589', 'type': 'link', 'targetBlank': True,
               'url': 'https://grafana.com/grafana/dashboards/7589-kafka-exporter-overview/'}],
    'templating': {'list': []}, 'panels': [],
}
for name, label, metric, field in [
    ('topic', 'Topic', 'kafka_topic_partitions{job="kafka-exporter",topic!="__consumer_offsets"}', 'topic'),
    ('group', 'Consumer group', 'kafka_consumergroup_lag{job="kafka-exporter"}', 'consumergroup'),
]:
    dashboard['templating']['list'].append({
        'name': name, 'label': label, 'type': 'query', 'datasource': prom,
        'query': {'query': f'label_values({metric}, {field})', 'refId': 'VariableQuery'},
        'definition': f'label_values({metric}, {field})', 'refresh': 1,
        'multi': True, 'includeAll': True, 'allValue': '.*', 'sort': 1,
        'current': {'text': 'All', 'value': '$__all'}, 'options': [],
    })


def add(title, expr, kind='timeseries', unit='short', description='', legend='{{topic}} {{consumergroup}}', height=8):
    index = len(dashboard['panels'])
    ds = loki if kind == 'logs' else prom
    panel = {'id': index + 1, 'title': title, 'type': kind, 'description': description,
             'gridPos': {'x': (index % 2) * 12, 'y': (index // 2) * 8, 'w': 12, 'h': height},
             'datasource': ds, 'targets': [{'refId': 'A', 'expr': expr, 'datasource': ds,
                                           'legendFormat': legend}],
             'fieldConfig': {'defaults': {'unit': unit, 'min': 0}, 'overrides': []}}
    if kind == 'stat':
        panel['options'] = {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False},
                            'colorMode': 'value', 'graphMode': 'none'}
    elif kind == 'logs':
        panel['options'] = {'showTime': True, 'showLabels': True, 'wrapLogMessage': True,
                            'sortOrder': 'Descending', 'enableLogDetails': True}
    else:
        panel['options'] = {'legend': {'displayMode': 'table', 'placement': 'bottom', 'calcs': ['lastNotNull']},
                            'tooltip': {'mode': 'multi', 'sort': 'desc'}}
    dashboard['panels'].append(panel)


add('Kafka broker scrape health', 'up{job="kafka-jmx"}', 'stat', description='1 means the Kafka JVM metrics endpoint is reachable; 0 means its scrape failed.')
add('Kafka exporter scrape health', 'up{job="kafka-exporter"}', 'stat')
add('Brokers discovered', 'kafka_brokers{job="kafka-exporter"}', 'stat')
add('Under-replicated partitions', 'sum(kafka_topic_partition_under_replicated_partition{job="kafka-exporter",topic=~"${topic:regex}"})', 'stat', description='Zero is healthy for the selected topics.')

# Keep the five source template panels, replacing obsolete Graph with Time series.
selector = 'job="kafka-exporter",topic=~"${topic:regex}"'
queries = [
    f'sum by (topic) (rate(kafka_topic_partition_current_offset{{{selector}}}[2m]))',
    f'sum by (consumergroup, topic) (kafka_consumergroup_lag{{{selector},consumergroup=~"${{group:regex}}"}})',
    f'sum by (topic) (clamp_min(delta(kafka_topic_partition_current_offset{{{selector}}}[5m]), 0) / 5)',
    f'sum by (consumergroup, topic) (clamp_min(delta(kafka_consumergroup_current_offset{{{selector},consumergroup=~"${{group:regex}}"}}[5m]), 0) / 5)',
    f'sum by (topic) (kafka_topic_partitions{{{selector}}})',
]
for original, query in zip(source['panels'], queries):
    title = original['title'].strip().replace('  ', ' ')
    add(title, query, unit='ops' if 'second' in title else 'short',
        description='Adapted from template 7589 revision 5. Consumer panels require a group with committed offsets; rate panels need at least two scrapes.')
add('Kafka JVM heap used', 'sum(jvm_memory_used_bytes{job="kafka-jmx",area="heap"})', unit='bytes', legend='Kafka heap')
add('Kafka pod CPU', 'sum(rate(container_cpu_usage_seconds_total{namespace="bigdata",pod="kafka-0",container="kafka"}[2m]))', unit='cores', legend='Kafka CPU')
add('Kafka pod memory', 'sum(container_memory_working_set_bytes{namespace="bigdata",pod="kafka-0",container="kafka"})', unit='bytes', legend='Kafka memory')
add('Kafka broker logs', '{namespace="bigdata",component="kafka",container="kafka"}', 'logs')
add('ZooKeeper logs', '{namespace="bigdata",component="zookeeper"}', 'logs')

payload = json.dumps(dashboard, indent=2) + '\n'
configmap = {'apiVersion': 'v1', 'kind': 'ConfigMap',
             'metadata': {'name': 'grafana-dashboard-kafka', 'namespace': 'bigdata',
                          'annotations': {'training.grafana/template': '7589 revision 5',
                                          'training.grafana/source-sha256': hashlib.sha256(raw).hexdigest()}},
             'data': {'kafka.json': payload}}


class Dumper(yaml.SafeDumper):
    pass


def string(dumper, value):
    return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None)


Dumper.add_representer(str, string)
output = root / 'monitoring/grafana-dashboard-kafka.yaml'
output.write_text('# Template: Kafka Exporter Overview, Grafana.com 7589 revision 5.\n'
                  '# Adapted for this lab; generated by validations/build-kafka-dashboard.py.\n'
                  + yaml.dump(configmap, Dumper=Dumper, sort_keys=False), encoding='utf-8')
print(output)
