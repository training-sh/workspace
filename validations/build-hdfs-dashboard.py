"""Build a dashboard for the lab's native Hadoop NameNode/DataNode metrics."""
import json
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
prom = {'type': 'prometheus', 'uid': 'prometheus'}
loki = {'type': 'loki', 'uid': 'loki'}
source = 'https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-common/Metrics.html'
dashboard = {
    'uid': 'training-hdfs', 'title': 'HDFS - storage, operations, JVM and logs',
    'description': 'Native /prom metrics for the installed NameNode and DataNode: '
                   'capacity, node/block health, namespace, I/O, RPC, JVM, pod resources and Loki logs. '
                   'No extra exporter. Filesystem capacity includes storage shared with other lab services.',
    'schemaVersion': 39, 'version': 1, 'tags': ['training', 'hdfs', 'hadoop', 'jvm'],
    'refresh': '15s', 'time': {'from': 'now-30m', 'to': 'now'},
    'links': [{'type': 'link', 'title': 'Hadoop metrics reference', 'targetBlank': True, 'url': source}],
    'templating': {'list': []}, 'panels': [],
}


def nn(name):
    return name + '{job="hdfs-namenode"}'


def dn(name):
    return name + '{job="hdfs-datanode"}'


def jvm(name):
    return name + '{job=~"hdfs-namenode|hdfs-datanode"}'


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


for title, expr, unit in [
    ('NameNode scrape health', 'up{job="hdfs-namenode"}', 'short'),
    ('DataNode scrape health', 'up{job="hdfs-datanode"}', 'short'),
    ('Live DataNodes', nn('fs_namesystem_num_live_data_nodes'), 'short'),
    ('Dead DataNodes', nn('fs_namesystem_num_dead_data_nodes'), 'short'),
    ('Files and directories', nn('fs_namesystem_files_total'), 'short'),
    ('Blocks', nn('fs_namesystem_blocks_total'), 'short'),
    ('Missing blocks', nn('fs_namesystem_missing_blocks'), 'short'),
    ('Corrupt blocks', nn('fs_namesystem_corrupt_blocks'), 'short'),
    ('Under-replicated blocks', nn('fs_namesystem_under_replicated_blocks'), 'short'),
    ('HDFS storage used', nn('fs_namesystem_capacity_used'), 'bytes'),
    ('Storage remaining', nn('fs_namesystem_capacity_remaining'), 'bytes'),
    ('Storage total capacity', nn('fs_namesystem_capacity_total'), 'bytes'),
]:
    add(title, [(title, expr)], 'stat', unit)
add('Storage breakdown', [(label, nn('fs_namesystem_capacity_' + suffix)) for label, suffix in [('HDFS used', 'used'), ('Non-HDFS used', 'used_non_dfs'), ('Remaining', 'remaining')]], unit='bytes', description='Non-HDFS usage includes other files/services on the shared filesystem.')
add('Storage utilization', [('HDFS', f'100 * {nn("fs_namesystem_capacity_used")} / {nn("fs_namesystem_capacity_total")}'),
                            ('HDFS + non-HDFS', f'100 * ({nn("fs_namesystem_capacity_used")} + {nn("fs_namesystem_capacity_used_non_dfs")}) / {nn("fs_namesystem_capacity_total")}')], unit='percent')
add('Namespace objects', [('Files/directories', nn('fs_namesystem_files_total')), ('Blocks', nn('fs_namesystem_blocks_total'))])
add('File operations per second', [(label, f'rate({nn("namenode_files_" + suffix)}[2m])') for label, suffix in [('Created', 'created'), ('Deleted', 'deleted'), ('Renamed', 'renamed')]], unit='ops')
add('DataNode throughput', [(label, f'rate({dn("datanode_bytes_" + suffix)}[2m])') for label, suffix in [('Read', 'read'), ('Written', 'written')]], unit='Bps')
add('DataNode block operations', [(label, f'rate({dn("datanode_blocks_" + suffix)}[2m])') for label, suffix in [('Read', 'read'), ('Written', 'written'), ('Removed', 'removed')]], unit='ops')
add('NameNode RPC calls per second', [('RPC calls', f'rate({nn("rpc_rpc_processing_time_num_ops")}[2m])')], unit='ops')
add('NameNode RPC latency', [('Queue {{port}}', nn('rpc_rpc_queue_time_avg_time')), ('Processing {{port}}', nn('rpc_rpc_processing_time_avg_time'))], unit='ms', description='Native average RPC timings, not a latency percentile.')
add('Pending block work', [(label, nn('fs_namesystem_' + suffix)) for label, suffix in [('Replication', 'pending_replication_blocks'), ('Reconstruction', 'pending_reconstruction_blocks'), ('Deletion', 'pending_deletion_blocks')]])
add('HDFS JVM heap', [('{{job}} ' + suffix, jvm('jvm_metrics_mem_heap_' + suffix + '_m') + ' * 1048576') for suffix in ('used', 'committed', 'max')], unit='bytes')
add('HDFS JVM heap utilization', [('{{job}}', f'100 * {jvm("jvm_metrics_mem_heap_used_m")} / {jvm("jvm_metrics_mem_heap_max_m")}')], unit='percent')
add('HDFS JVM non-heap memory', [('{{job}} ' + suffix, jvm('jvm_metrics_mem_non_heap_' + suffix + '_m') + ' * 1048576') for suffix in ('used', 'committed')], unit='bytes')
add('HDFS garbage collections per second', [('{{job}}', f'rate({jvm("jvm_metrics_gc_count")}[2m])')], unit='ops')
add('HDFS GC time per second', [('{{job}}', f'rate({jvm("jvm_metrics_gc_time_millis")}[2m]) / 1000')], unit='s')
add('NameNode and DataNode CPU', [('{{pod}}', 'sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bigdata",pod=~"(namenode|datanode)-.*",container=~"namenode|datanode"}[2m]))')], unit='cores')
add('NameNode and DataNode memory', [('{{pod}}', 'sum by (pod) (container_memory_working_set_bytes{namespace="bigdata",pod=~"(namenode|datanode)-.*",container=~"namenode|datanode"})')], unit='bytes')
for component in ('namenode', 'datanode'):
    add('NameNode logs' if component == 'namenode' else 'DataNode logs', [('Logs', '{namespace="bigdata",component="' + component + '",container="' + component + '"}')], 'logs')

cm = {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'grafana-dashboard-hdfs', 'namespace': 'bigdata',
      'annotations': {'training.grafana/template': 'native-hdfs-v1', 'training.grafana/source': source}},
      'data': {'hdfs.json': json.dumps(dashboard, indent=2) + '\n'}}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(str, lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:str', value, style='|' if '\n' in value else None))
path = root / 'monitoring/grafana-dashboard-hdfs.yaml'
path.write_text('# Template: native-hdfs-v1, matched to the installed Hadoop /prom endpoints.\n'
                '# Generated by validations/build-hdfs-dashboard.py.\n' + yaml.dump(cm, Dumper=Dumper, sort_keys=False), encoding='utf-8')
print(path)
