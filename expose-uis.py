#!/usr/bin/env python3
"""Expose deployed workshop UIs on the Kubernetes host; Ctrl+C closes forwards."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

# name, namespace, Service, Service port, host port, browser path
PORTALS = [
    ('headlamp', 'headlamp', 'headlamp', 80, 14466, '/'),
    ('polaris-console', 'bigdata', 'polaris-console', 8080, 18180, '/'),
    ('seaweed-admin', 'bigdata', 'seaweedfs', 23646, 19002, '/'),
    ('seaweed-master', 'bigdata', 'seaweedfs', 9333, 19333, '/'),
    ('seaweed-filer', 'bigdata', 'seaweedfs', 8888, 18889, '/'),
    ('seaweed-volume', 'bigdata', 'seaweedfs', 9340, 19340, '/'),
    ('namenode', 'bigdata', 'namenode', 9870, 19870, '/'),
    ('datanode', 'bigdata', 'datanode', 9864, 19864, '/'),
    ('yarn', 'bigdata', 'resourcemanager', 8088, 18088, '/'),
    ('yarn-node', 'bigdata', 'nodemanager', 8042, 18042, '/'),
    ('mapreduce-history', 'bigdata', 'historyserver', 19888, 19888, '/'),
    ('hive-status', 'bigdata', 'hiveserver2', 10002, 10002, '/'),
    ('spark-master', 'bigdata', 'spark-master', 8080, 18080, '/'),
    ('spark-worker', 'bigdata', 'spark-worker', 8081, 18081, '/'),
    ('spark-app', 'bigdata', 'jupyter', 4040, 14040, '/'),
    ('jupyter', 'bigdata', 'jupyter', 8888, 18888, '/'),
    ('airflow', 'bigdata', 'airflow', 8080, 28080, '/'),
    ('grafana', 'bigdata', 'grafana', 3000, 13000, '/'),
    ('prometheus', 'bigdata', 'prometheus', 9090, 19090, '/'),
    ('jaeger', 'bigdata', 'jaeger', 16686, 16686, '/'),
    ('alloy', 'bigdata', 'alloy', 12345, 12345, '/'),
    ('adminer', 'bigdata', 'adminer', 8080, 18086, '/'),
    ('trino', 'bigdata', 'trino', 8080, 18089, '/'),
    ('lineage', 'bigdata', 'marquez-web', 3000, 13001, '/'),
]


def error_hint(exc):
    """Keep terminal status short; kubectl may emit several lines of diagnostics."""
    if isinstance(exc, subprocess.TimeoutExpired):
        return 'Kubernetes request timed out; check cluster connectivity and context'
    return next((line.strip() for line in str(exc).splitlines() if line.strip()),
                type(exc).__name__)[:300]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     epilog='Use --components to list all supported component names without Kubernetes.')
    parser.add_argument('--context', default='bigdata', help='Kubernetes context (default: bigdata)')
    parser.add_argument('--bind', default='127.0.0.1', help='Host IPv4 address to listen on')
    parser.add_argument('--only', nargs='+', choices=[p[0] for p in PORTALS], help='Forward only these components')
    parser.add_argument('--components', action='store_true', help='List supported component names and ports, then exit')
    parser.add_argument('--list', action='store_true', help='Inspect without starting forwards')
    parser.add_argument('--seconds', type=int, help='Stop automatically after this many seconds')
    args = parser.parse_args()
    if args.components:
        for name, ns, service, remote, local, path in PORTALS:
            print(f'{name:20} localhost:{local} -> {ns}/{service}:{remote}')
        return 0
    if args.seconds is not None and args.seconds <= 0:
        parser.error('--seconds must be positive')
    if not shutil.which('kubectl'):
        parser.error('kubectl must be installed and available on PATH')
    try:
        socket.inet_aton(args.bind)
    except OSError:
        parser.error('--bind must be an IPv4 address')
    base = ['kubectl', '--context', args.context]

    def get(kind, ns):
        result = subprocess.run(base + ['-n', ns, 'get', kind, '-o', 'json'],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)['items']

    selected = [p for p in PORTALS if not args.only or p[0] in args.only]
    # Namespace-scoped reads also work with accounts that cannot list cluster-wide.
    inventory = {}
    inventory_errors = {}
    for ns in sorted({p[1] for p in selected}):
        try:
            inventory[ns] = ({s['metadata']['name']: s for s in get('services', ns)},
                             get('endpointslices.discovery.k8s.io', ns))
        except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            inventory_errors[ns] = error_hint(exc)
    logdir = Path(__file__).resolve().parent / '.state' / 'ui-port-forwards'
    if not args.list:
        logdir = logdir / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        logdir.mkdir(parents=True, exist_ok=True)
    forwards = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    browser_host = '127.0.0.1' if args.bind == '0.0.0.0' else args.bind
    print(f'Context: {args.context}; bind: {args.bind}', flush=True)
    if args.bind == '0.0.0.0':
        print('Listening on all host IPv4 interfaces; use the host address from another machine.')
    try:
        for name, ns, service, remote, local, path in selected:
            if ns in inventory_errors:
                print(f'{name:20} INSPECTION FAILED: {inventory_errors[ns]}', flush=True)
                continue
            services, slices = inventory[ns]
            svc = services.get(service)
            if not svc:
                print(f'{name:20} NOT DEPLOYED: service {ns}/{service} is missing', flush=True)
                continue
            if remote not in [p['port'] for p in svc['spec'].get('ports', [])]:
                print(f'{name:20} SERVICE PORT {remote} MISSING', flush=True)
                continue
            ready = any((s['metadata'].get('labels') or {}).get('kubernetes.io/service-name') == service
                        and any((e.get('conditions') or {}).get('ready') is not False
                                and e.get('addresses') for e in (s.get('endpoints') or []))
                        for s in slices)
            url = f'http://{browser_host}:{local}{path}'
            if not ready:
                print(f'{name:20} NO READY PODS: check kubectl -n {ns} get pods (context {args.context})', flush=True)
                continue
            if args.list:
                print(f'{name:20} READY {url} -> {ns}/{service}:{remote} '
                      f'(Service type: {svc["spec"]["type"]}; forward not started)', flush=True)
                continue
            try:
                with socket.socket() as sock:
                    # A prior run can leave closed connections in TIME_WAIT.
                    if sys.platform != 'win32':
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind((args.bind, local))
            except OSError as exc:
                print(f'{name:20} PORT {local} UNAVAILABLE: {exc}', flush=True)
                continue
            logfile = logdir / f'{name}.log'
            command = base + ['-n', ns, 'port-forward', '--address', args.bind,
                              f'service/{service}', f'{local}:{remote}']
            item = {'name': name, 'url': url, 'port': local, 'command': command,
                    'logfile': logfile, 'process': None, 'retry': 0, 'announced': False}
            forwards.append(item)

        if args.list:
            return 1 if inventory_errors else 0
        if not forwards:
            print('No forwards could be started.')
            return 1
        print(f'Logs: {logdir}\nCtrl+C closes only the forwards started by this script.', flush=True)
        print('Spark application UI needs an active Spark context; Seaweed volume / may return HTTP 400.', flush=True)
        deadline = time.monotonic() + args.seconds if args.seconds is not None else float('inf')
        while not stopping and time.monotonic() < deadline:
            for item in forwards:
                proc = item['process']
                if proc is not None and proc.poll() is not None:
                    detail = error_hint(item['logfile'].read_text(errors='replace'))
                    print(f'{item["name"]:20} FORWARD STOPPED: {detail}; retrying in 5s (see log)', flush=True)
                    item.update(process=None, retry=time.monotonic() + 5, announced=False)
                if item['process'] is None and time.monotonic() >= item['retry']:
                    try:
                        with item['logfile'].open('wb') as log:
                            item['process'] = subprocess.Popen(item['command'], stdout=log, stderr=log,
                                                               stdin=subprocess.DEVNULL)
                    except OSError as exc:
                        print(f'{item["name"]:20} FORWARD FAILED: {error_hint(exc)}; retrying in 5s', flush=True)
                        item.update(process=None, retry=time.monotonic() + 5)
                # The kubectl readiness message proves this process owns the listener.
                if item['process'] is not None and not item['announced']:
                    content = item['logfile'].read_text(errors='replace')
                    if 'Forwarding from' in content and item['process'].poll() is None:
                        print(f'{item["name"]:20} FORWARDED {item["url"]}', flush=True)
                        item['announced'] = True
            time.sleep(0.5)
        return 0
    finally:
        for item in forwards:
            proc = item['process']
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for item in forwards:
            proc = item['process']
            if proc is not None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        if forwards:
            print('UI forwards stopped.', flush=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        print(f'UI forwarding failed: {error_hint(exc)}', file=sys.stderr)
        sys.exit(1)
