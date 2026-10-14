"""Execute the actual notebooks in fresh kernels, with errors disallowed.

Run this inside the course Kubernetes Python workbench, from the lesson folder:
    python assets/validate_notebooks.py --passes 2 --output /tmp/migration-validation
Connection settings come from the workbench environment. No SSH or host settings belong here.
"""
import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import nbformat
from nbclient import NotebookClient

LESSON = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--passes', type=int, default=2)
    parser.add_argument('--output', type=Path, default=Path('/tmp/migration-validation'))
    parser.add_argument('--only', help='Optional notebook filename prefix for diagnosis')
    args = parser.parse_args()
    if not Path('/var/run/secrets/kubernetes.io/serviceaccount').is_dir():
        raise RuntimeError('Run this validator inside the course Kubernetes workbench')
    if args.passes < 1:
        parser.error('--passes must be positive')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'started_utc': datetime.now(timezone.utc).isoformat(), 'execution': 'Fresh Python kernels in Kubernetes; Spark jobs use configured master',
              'kubernetes_serviceaccount_present': True,
              'connection_environment_present': {
                  key: bool(os.environ.get(key)) for key in [
                      'SPARK_MASTER_URL', 'SPARK_DRIVER_HOST', 'HDFS_URI',
                      'HIVE_METASTORE_URI', 'POLARIS_URI', 'POLARIS_WAREHOUSE',
                      'POLARIS_BASE_URL', 'POLARIS_CATALOG', 'S3_ENDPOINT',
                      'POLARIS_REALM', 'AWS_DEFAULT_REGION', 'AWS_REGION']},
              'sources': {p.name: digest(p) for p in sorted(LESSON.glob('*.ipynb'))},
              'validator_sha256': digest(Path(__file__)), 'runs': []}
    notebooks = sorted(LESSON.glob((args.only or '') + '*.ipynb'))
    if not notebooks:
        raise RuntimeError('No notebooks selected')
    for pass_no in range(1, args.passes + 1):
        for path in notebooks:
            run_id = f'p{pass_no}_' + uuid.uuid4().hex[:10]
            os.environ['LESSON_RUN_ID'] = run_id
            nb = nbformat.read(path, as_version=4)
            nbformat.validate(nb)
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    cell.outputs = []
                    cell.execution_count = None
            start_time = time.perf_counter()
            result = {'pass': pass_no, 'notebook': path.name, 'run_id': run_id}
            print(f'RUN pass={pass_no} {path.name} {run_id}', flush=True)
            try:
                client = NotebookClient(nb, timeout=900, kernel_name='python3', allow_errors=False,
                                        resources={'metadata': {'path': str(LESSON)}})
                client.execute()
                code_cells = [c for c in nb.cells if c.cell_type == 'code']
                assert all(c.execution_count is not None for c in code_cells), 'Unexecuted code cell'
                assert not any(o.output_type == 'error' for c in code_cells for o in c.outputs), 'Error output'
                output = '\n'.join(o.get('text', '') for c in code_cells for o in c.outputs)
                assert 'ALL CORE CHECKS PASSED' in output, 'Missing completion marker'
                distributed = 'PASS: Distributed Spark executor verified' in output
                if os.environ.get('SPARK_MASTER_URL', '').startswith('spark://'):
                    assert distributed, 'Distributed executor check missing'
                result.update(status='PASS', code_cells=len(code_cells), checks=output.count('PASS:'), distributed_executor_verified=distributed)
            except Exception as error:
                result.update(status='FAIL', error=str(error))
                raise
            finally:
                result['seconds'] = round(time.perf_counter() - start_time, 2)
                report['runs'].append(result)
                nbformat.write(nb, args.output / f'pass{pass_no}_{path.name}')
                (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
                print(f"{result['status']} {path.name} {result['seconds']}s", flush=True)
    print(f"COMPLETE: {len(report['runs'])} notebook executions passed", flush=True)


if __name__ == '__main__':
    main()
