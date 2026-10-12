"""Check real collected logs and metrics for a running notebook component."""
import argparse
import json
import subprocess
import time
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--components', required=True, help='Comma-separated app labels')
parser.add_argument('--jobs', default='', help='Comma-separated native metric job names')
parser.add_argument('--marker', default='')
parser.add_argument('--file-logs', action='store_true')
parser.add_argument('--namespace', default='bigdata')
args = parser.parse_args()


def get(url, parameters=None):
    if parameters:
        url += '?' + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def query(expression):
    return get('http://127.0.0.1:19090/api/v1/query', {'query': expression})['data']['result']


processes = []
try:
    for service, mapping in [('prometheus', '19090:9090'), ('loki', '13100:3100')]:
        processes.append(subprocess.Popen(
            ['kubectl', '--context=bigdata', '-n', 'bigdata', 'port-forward',
             '--address=127.0.0.1', 'service/' + service, mapping],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for attempt in range(60):
        try:
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Validation port is occupied or forwarding failed.')
            query('up')
            get('http://127.0.0.1:13100/loki/api/v1/labels')
            break
        except (OSError, ValueError):
            time.sleep(1)
    else:
        raise RuntimeError('Monitoring APIs did not become reachable.')
    for component in args.components.split(','):
        selector = '{namespace=' + json.dumps(args.namespace) + ',component=' + json.dumps(component) + '}'
        if args.file_logs:
            selector = selector[:-1] + ',container="file-logs"}'
        if args.marker:
            selector += ' |= ' + json.dumps(args.marker)
        memory = ('sum(container_memory_working_set_bytes{namespace="' + args.namespace + '",'
                  'pod=~"' + component + '-.*",container!="",container!="POD"})')
        cpu = ('count(container_cpu_usage_seconds_total{namespace="' + args.namespace + '",'
               'pod=~"' + component + '-.*",container!="",container!="POD"})')
        for attempt in range(90):
            logs = get('http://127.0.0.1:13100/loki/api/v1/query_range', {
                'query': selector, 'start': str(time.time_ns() - 24 * 3600 * 10**9), 'limit': 50,
            })['data']['result']
            memory_samples, cpu_samples = query(memory), query(cpu)
            if (logs and memory_samples and float(memory_samples[0]['value'][1]) > 0
                    and cpu_samples and float(cpu_samples[0]['value'][1]) > 0):
                break
            time.sleep(2)
        else:
            raise AssertionError('Missing logs or CPU/memory metrics: ' + component)
        print('PASS: ' + component + ' collected logs and actual CPU/memory samples.', flush=True)
    for job in filter(None, args.jobs.split(',')):
        for attempt in range(90):
            health = query('min(up{job="' + job + '"})')
            samples = query('count({job="' + job + '",__name__!~"up|scrape_.*"})')
            if (health and float(health[0]['value'][1]) == 1 and samples
                    and float(samples[0]['value'][1]) > 0):
                break
            time.sleep(2)
        else:
            raise AssertionError('Native metric scrape failed: ' + job)
        print('PASS: ' + job + ' healthy scrape and native metric samples.', flush=True)
finally:
    for process in processes:
        process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
