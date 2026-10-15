"""Generate the standalone dashboard for Trino 476 native OpenMetrics and Loki."""
import json
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
prom = {'type': 'prometheus', 'uid': 'prometheus'}
loki = {'type': 'loki', 'uid': 'loki'}
dashboard = {
    'uid': 'training-trino', 'title': 'Trino - queries, resources and logs',
    'description': 'Native OpenMetrics dashboard for the lab Trino 476 single node '
                   '(coordinator also executes worker tasks). Query states, totals/rates, '
                   'failures, drivers/tasks, memory reservations, CPU, durations, GC and Loki logs. '
                   'Query totals are since server start; zero activity while idle is normal.',
    'schemaVersion': 39, 'version': 2, 'tags': ['training', 'trino', 'openmetrics'],
    'refresh': '15s', 'time': {'from': 'now-30m', 'to': 'now'},
    'links': [{'type': 'link', 'title': 'Trino metrics reference', 'targetBlank': True,
               'url': 'https://trino.io/docs/current/admin/openmetrics.html'}],
    'templating': {'list': []}, 'panels': [],
}


def metric(name):
    return name + '{job="trino"}'


def query(name):
    return metric('trino_execution_name_QueryManager_' + name)


def memory(name):
    return metric('trino_memory_name_ClusterMemoryManager_' + name)


def nodes(name):
    return metric('trino_metadata_name_DiscoveryNodeManager_' + name)


def add(title, targets, kind='timeseries', unit='short', description=''):
    index = len(dashboard['panels'])
    pos = ({'x': (index % 4) * 6, 'y': (index // 4) * 4, 'w': 6, 'h': 4}
           if index < 12 else {'x': ((index - 12) % 2) * 12, 'y': 12 + ((index - 12) // 2) * 8, 'w': 12, 'h': 8})
    ds = loki if kind == 'logs' else prom
    panel = {'id': index + 1, 'title': title, 'type': kind, 'description': description,
             'gridPos': pos, 'datasource': ds,
             'targets': [{'refId': chr(65 + i), 'expr': expr, 'legendFormat': name, 'datasource': ds}
                         for i, (name, expr) in enumerate(targets)],
             'fieldConfig': {'defaults': {'unit': unit, 'min': 0}, 'overrides': []}}
    if kind == 'stat':
        panel['fieldConfig']['defaults']['color'] = {'mode': 'fixed', 'fixedColor': 'blue'}
        if title == 'Trino scrape health':
            panel['fieldConfig']['defaults'].update(color={'mode': 'thresholds'}, thresholds={
                'mode': 'absolute', 'steps': [{'color': 'red', 'value': None}, {'color': 'green', 'value': 1}]})
        panel['options'] = {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'colorMode': 'value', 'graphMode': 'none'}
    elif kind == 'logs':
        for target in panel['targets']:
            target['maxLines'] = 200
        panel['options'] = {'showTime': True, 'showLabels': True, 'wrapLogMessage': True,
                            'sortOrder': 'Descending', 'enableLogDetails': True}
    else:
        panel['options'] = {'legend': {'displayMode': 'table', 'placement': 'bottom', 'calcs': ['lastNotNull']},
                            'tooltip': {'mode': 'multi', 'sort': 'desc'}}
    dashboard['panels'].append(panel)


for title, expr, unit in [
    ('Trino scrape health', 'up{job="trino"}', 'short'),
    ('Active nodes', nodes('ActiveNodeCount'), 'short'),
    ('Inactive nodes', nodes('InactiveNodeCount'), 'short'),
    ('Submitted queries total', query('SubmittedQueries'), 'short'),
    ('Finished queries total', query('CompletedQueries'), 'short'),
    ('Failed queries total', query('FailedQueries'), 'short'),
    ('Running queries', query('RunningQueries'), 'short'),
    ('Queued queries', query('QueuedQueries'), 'short'),
    ('Running drivers', query('RunningDrivers'), 'short'),
    ('Blocked drivers', query('BlockedDrivers'), 'short'),
    ('Query memory reserved', memory('ClusterTotalMemoryReservation'), 'bytes'),
    ('Query memory capacity', memory('ClusterMemoryBytes'), 'bytes'),
]:
    add(title, [(title, expr)], 'stat', unit, description='Includes successful, failed and cancelled queries.' if title == 'Finished queries total' else '')
add('Query states', [(name, query(name + 'Queries')) for name in ('Running', 'Queued', 'Finishing', 'FullyBlocked')])
add('Query rates', [(label, f'rate({query(name + "Queries")}[2m])') for label, name in [('Submitted', 'Submitted'), ('Finished (all outcomes)', 'Completed'), ('Failed', 'Failed')]], unit='ops')
add('Query failures by category', [(name, query(name + 'Failures')) for name in ('UserError', 'Internal', 'External', 'InsufficientResources')])
add('Execution drivers', [(name, query(name + 'Drivers')) for name in ('Running', 'Queued', 'Blocked', 'Completed')])
add('Query memory reservations', [('Total reserved', memory('ClusterTotalMemoryReservation')), ('User reserved', memory('ClusterUserMemoryReservation')), ('Capacity', memory('ClusterMemoryBytes'))], unit='bytes')
add('Query memory utilization', [('Reserved', f'100 * {memory("ClusterTotalMemoryReservation")} / clamp_min({memory("ClusterMemoryBytes")}, 1)')], unit='percent')
add('Trino pod CPU', [('CPU', 'sum(rate(container_cpu_usage_seconds_total{namespace="bigdata",pod="trino-0",container="trino"}[2m]))')], unit='cores')
add('Trino pod memory working set', [('Memory', 'sum(container_memory_working_set_bytes{namespace="bigdata",pod="trino-0",container="trino"})')], unit='bytes')
add('Consumed input bytes per second', [('Input', f'rate({query("ConsumedInputBytes")}[2m])')], unit='Bps')
add('Consumed input rows per second', [('Rows', f'rate({query("ConsumedInputRows")}[2m])')], unit='ops')
add('Node health over time', [('Active', nodes('ActiveNodeCount')), ('Inactive', nodes('InactiveNodeCount'))])
add('Garbage collections per second', [(name, 'rate(' + metric('io_airlift_stats_name_GcMonitor_' + name + 'Gc_AllTime_count') + '[2m])') for name in ('Minor', 'Major')], unit='ops')
add('Garbage collections since start', [(name, metric('io_airlift_stats_name_GcMonitor_' + name + 'Gc_AllTime_count')) for name in ('Minor', 'Major')])
add('Task creation and failure rates', [(name, 'rate(' + metric('trino_execution_name_SqlTaskManager_' + name + 'Tasks') + '[2m])') for name in ('Created', 'Failed')], unit='ops')
add('Query execution duration', [(label, 'trino_execution_name_QueryManager_ExecutionTime_AllTime{job="trino",quantile="' + q + '"}') for label, q in [('Median', '0.5'), ('95th percentile', '0.95')]], unit='ms', description='All-time completed-query distribution. Empty/NaN until at least one query executes; not a recent-window percentile.')
add('Query CPU seconds per second', [('CPU', f'rate({query("ConsumedCpuTimeSecs")}[2m])')], unit='s')
add('Trino server logs', [('Logs', '{namespace="bigdata",component="trino",container="trino"}')], 'logs')
add('Trino query timelines', [('Queries', '{namespace="bigdata",component="trino",container="trino"} |= "TIMELINE:"')], 'logs', description='Query-completion records include query IDs and timings. Appears after queries run; this is not a SQL audit archive.')

configmap = {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {
    'name': 'grafana-dashboard-trino', 'namespace': 'bigdata', 'annotations': {
        'training.grafana/template': 'native-trino-476-v1',
        'training.grafana/source': 'https://trino.io/docs/current/admin/openmetrics.html'}},
    'data': {'trino.json': json.dumps(dashboard, indent=2) + '\n'}}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(str, lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None))
path = root / 'monitoring/grafana-dashboard-trino.yaml'
path.write_text('# Template: native-trino-476-v1, matched to the installed OpenMetrics endpoint.\n'
                '# Generated by validations/build-trino-dashboard.py.\n'
                + yaml.dump(configmap, Dumper=Dumper, sort_keys=False), encoding='utf-8')
print(path)
