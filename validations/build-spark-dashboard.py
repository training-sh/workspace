"""Build the native Spark standalone cluster dashboard ConfigMap (no downloads)."""
import json
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
prom = {'type': 'prometheus', 'uid': 'prometheus'}
loki = {'type': 'loki', 'uid': 'loki'}
dashboard = {
    'uid': 'training-spark', 'title': 'Spark - master, workers and logs',
    'description': 'Native Spark standalone master/worker overview: all four master gauges '
                   'and five worker gauges, capacity/utilization, pod resources, JVM heap/pools/buffers/GC, daemon/driver/executor logs. '
                   'Uses the existing PrometheusServlet and cAdvisor; no extra exporter. '
                   'Per-job SQL/stage/task profiling remains in the Spark application UI.',
    'schemaVersion': 39, 'version': 5, 'tags': ['training', 'spark', 'standalone', 'jvm'],
    'refresh': '15s', 'time': {'from': 'now-30m', 'to': 'now'},
    'links': [{'type': 'link', 'title': 'Spark metrics reference', 'targetBlank': True,
               'url': 'https://spark.apache.org/docs/3.5.7/monitoring.html#metrics'}],
    'templating': {'list': []}, 'panels': [],
}


def master(metric):
    return f'sum(metrics_master_{metric}_Number{{job="spark-master"}})'


def worker(metric):
    return f'sum(metrics_worker_{metric}_Number{{job="spark-worker"}})'


def add(title, targets, kind='timeseries', unit='short', description=''):
    index = len(dashboard['panels'])
    if index < 12:
        pos = {'x': (index % 4) * 6, 'y': (index // 4) * 4, 'w': 6, 'h': 4}
    else:
        pos = {'x': ((index - 12) % 2) * 12, 'y': 12 + ((index - 12) // 2) * 8, 'w': 12, 'h': 8}
    datasource = loki if kind == 'logs' else prom
    panel = {'id': index + 1, 'title': title, 'type': kind, 'description': description,
             'gridPos': pos, 'datasource': datasource,
             'targets': [{'refId': chr(65 + n), 'expr': expr, 'legendFormat': legend,
                          'datasource': datasource} for n, (legend, expr) in enumerate(targets)],
             'fieldConfig': {'defaults': {'unit': unit, 'min': 0}, 'overrides': []}}
    if kind == 'stat':
        panel['fieldConfig']['defaults']['color'] = {'mode': 'fixed', 'fixedColor': 'blue'}
        if 'scrape health' in title:
            panel['fieldConfig']['defaults']['color'] = {'mode': 'thresholds'}
            panel['fieldConfig']['defaults']['thresholds'] = {
                'mode': 'absolute', 'steps': [{'color': 'red', 'value': None}, {'color': 'green', 'value': 1}]}
        panel['options'] = {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False},
                            'colorMode': 'value', 'graphMode': 'none'}
    elif kind == 'logs':
        for target in panel['targets']:
            target['maxLines'] = 200
        panel['options'] = {'showTime': True, 'showLabels': True, 'wrapLogMessage': True,
                            'sortOrder': 'Descending', 'enableLogDetails': True}
    else:
        panel['options'] = {'legend': {'displayMode': 'table', 'placement': 'bottom', 'calcs': ['lastNotNull']},
                            'tooltip': {'mode': 'multi', 'sort': 'desc'}}
    dashboard['panels'].append(panel)


cores_used, cores_free = worker('coresUsed'), worker('coresFree')
mem_used, mem_free = worker('memUsed_MB'), worker('memFree_MB')
for title, expr, unit, description in [
    ('Master scrape health', 'min(up{job="spark-master"})', 'short', '1: reachable; 0: scrape failed. Missing data means no target.'),
    ('Worker scrape health', 'min(up{job="spark-worker"})', 'short', 'Minimum health across configured worker targets.'),
    ('Alive workers', master('aliveWorkers'), 'short', 'Workers reporting alive to the master.'),
    ('Registered workers', master('workers'), 'short', 'All workers registered with the master.'),
    ('Running applications', master('apps'), 'short', 'Applications registered with the standalone master.'),
    ('Waiting applications', master('waitingApps'), 'short', 'Applications waiting for resources.'),
    ('Running executors', worker('executors'), 'short', 'Executors allocated on the worker(s).'),
    ('Total worker cores', f'({cores_used}) + ({cores_free})', 'short', 'Configured Spark scheduling capacity; not host CPU count.'),
    ('Allocated worker cores', cores_used, 'short', 'Cores reserved by Spark executors; not measured CPU usage.'),
    ('Free worker cores', cores_free, 'short', 'Remaining Spark scheduling capacity.'),
    ('Total worker memory', f'(({mem_used}) + ({mem_free})) * 1048576', 'bytes', 'Configured Spark executor-memory scheduling capacity.'),
    ('Allocated worker memory', f'({mem_used}) * 1048576', 'bytes', 'Memory reserved by executors; not process working set.'),
]:
    add(title, [(title, expr)], 'stat', unit, description)
add('Applications over time', [('Running', master('apps')), ('Waiting', master('waitingApps'))])
add('Executors over time', [('Executors', worker('executors'))])
add('Worker cores: allocated and free', [('Allocated', cores_used), ('Free', cores_free)])
add('Worker memory: allocated and free', [('Allocated', f'({mem_used}) * 1048576'), ('Free', f'({mem_free}) * 1048576')], unit='bytes')
add('Master and worker CPU usage', [('{{pod}}', 'sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bigdata",pod=~"spark-(master|worker)-.*",container=~"spark-master|spark-worker"}[2m]))')], unit='cores')
add('Master and worker memory working set', [('{{pod}}', 'sum by (pod) (container_memory_working_set_bytes{namespace="bigdata",pod=~"spark-(master|worker)-.*",container=~"spark-master|spark-worker"})')], unit='bytes')
add('Worker core allocation', [('Allocated', f'100 * ({cores_used}) / clamp_min(({cores_used}) + ({cores_free}), 1)')], unit='percent')
add('Worker memory allocation', [('Allocated', f'100 * ({mem_used}) / clamp_min(({mem_used}) + ({mem_free}), 1)')], unit='percent')
jvm_jobs = 'job=~"spark-master|spark-worker"'
add('JVM heap: used, committed and maximum', [
    ('{{job}} used', f'metrics_jvm_heap_used_Value{{{jvm_jobs}}}'),
    ('{{job}} committed', f'metrics_jvm_heap_committed_Value{{{jvm_jobs}}}'),
    ('{{job}} maximum', f'metrics_jvm_heap_max_Value{{{jvm_jobs}}}'),
], unit='bytes')
add('JVM heap utilization', [('{{job}}', f'100 * metrics_jvm_heap_used_Value{{{jvm_jobs}}} / metrics_jvm_heap_max_Value{{{jvm_jobs}}}')], unit='percent')
add('JVM non-heap memory', [
    ('{{job}} used', f'metrics_jvm_non_heap_used_Value{{{jvm_jobs}}}'),
    ('{{job}} committed', f'metrics_jvm_non_heap_committed_Value{{{jvm_jobs}}}'),
], unit='bytes', description='Metaspace/code cache and other non-heap regions. Undefined JVM maximum values (-1) are not plotted.')
add('JVM memory pools', [('{{job}} {{pool}}',
    f'label_replace({{__name__=~"metrics_jvm_pools_.*_used_Value",{jvm_jobs}}}, "pool", "$1", "__name__", "metrics_jvm_pools_(.*)_used_Value")')], unit='bytes')
gc_count = f'{{__name__=~"metrics_jvm_.*_count_Value",__name__!~"metrics_jvm_(direct|mapped)_count_Value",{jvm_jobs}}}'
gc_time = f'{{__name__=~"metrics_jvm_.*_time_Value",{jvm_jobs}}}'
add('JVM garbage collections since start', [('{{job}}', f'sum by (job) ({gc_count})')], description='Cumulative count across garbage collectors. Resets when a daemon restarts; direct/mapped buffer counts are excluded.')
# rate drops __name__; preserve the collector as a label before applying rate
# so two collectors with otherwise identical labels do not collide.
gc_time_labeled = f'label_replace({gc_time}, "collector", "$1", "__name__", "metrics_jvm_(.+)_time_Value")'
gc_count_labeled = f'label_replace({gc_count}, "collector", "$1", "__name__", "metrics_jvm_(.+)_count_Value")'
add('JVM garbage collection time per second', [('{{job}}', f'sum by (job) (rate({gc_time_labeled}[2m:15s])) / 1000')], unit='s', description='Seconds spent in garbage collection per elapsed second, across collectors. Spark exports cumulative GC time in milliseconds.')
add('JVM garbage collections per second', [('{{job}}', f'sum by (job) (rate({gc_count_labeled}[2m:15s]))')], unit='ops')
add('JVM buffer memory', [
    ('{{job}} direct used', f'metrics_jvm_direct_used_Value{{{jvm_jobs}}}'),
    ('{{job}} direct capacity', f'metrics_jvm_direct_capacity_Value{{{jvm_jobs}}}'),
    ('{{job}} mapped used', f'metrics_jvm_mapped_used_Value{{{jvm_jobs}}}'),
], unit='bytes')
for title, selector in [
    ('Spark master logs', '{namespace="bigdata",component="spark-master",container="spark-master"}'),
    ('Spark worker logs', '{namespace="bigdata",component="spark-worker",container="spark-worker"}'),
    ('Spark driver logs', '{namespace="bigdata",component="jupyter",container="file-logs"}'),
    ('Spark executor logs', '{namespace="bigdata",component="spark-worker",container="file-logs"}'),
]:
    add(title, [(title, selector)], 'logs', description='Driver/executor file streams appear after an application emits logs. No logs in a quiet time window is normal.')

configmap = {'apiVersion': 'v1', 'kind': 'ConfigMap',
             'metadata': {'name': 'grafana-dashboard-spark', 'namespace': 'bigdata',
                          'annotations': {'training.grafana/template': 'native-spark-standalone-v2',
                                          'training.grafana/source': 'https://spark.apache.org/docs/3.5.7/monitoring.html#metrics'}},
             'data': {'spark.json': json.dumps(dashboard, indent=2) + '\n'}}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(str, lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None))
path = root / 'monitoring/grafana-dashboard-spark.yaml'
path.write_text('# Template: native-spark-standalone-v2 (Apache Spark native + JVM metrics).\n'
                '# Generated by validations/build-spark-dashboard.py.\n'
                + yaml.dump(configmap, Dumper=Dumper, sort_keys=False), encoding='utf-8')
print(path)
