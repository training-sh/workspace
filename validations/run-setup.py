"""Extract the actual Bash examples for repeatable setup validation on Ubuntu."""
import argparse
import json
import re
import shlex
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--emit', type=Path, required=True)
parser.add_argument('--from-notebook', default='00')
parser.add_argument('--to-notebook', default='07')
parser.add_argument('--skip-notebooks', default='', help='Comma-separated two-digit notebook numbers')
parser.add_argument('--phases', default='main,pause,resume,persistence,ui-setup,ui-check,stage-pause,log-persistence,image-import')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
phases = set(args.phases.split(','))
skipped = set(args.skip_notebooks.split(','))
assert 'destructive-reset' not in phases, 'Destructive reset is never included.'
lines = ['#!/usr/bin/env bash', 'set -euo pipefail']
count = 0
for path in sorted((root / '00-setup').glob('*.ipynb')):
    if path.name[:2] in skipped or not args.from_notebook <= path.name[:2] <= args.to_notebook:
        continue
    notebook = json.loads(path.read_text(encoding='utf-8'))
    for cell in notebook['cells']:
        if cell.get('metadata', {}).get('setup_phase') not in phases:
            continue
        source = ''.join(cell['source'])
        for block in re.findall(r'```bash\n(.*?)\n```', source, re.S):
            title = source.splitlines()[0].removeprefix('## ')
            label = shlex.quote(path.name + ': ' + title)
            lines.append("printf '\nSTEP %s\n' " + label)
            lines.append(block)
            count += 1
lines.append("printf '\nPASS: all selected notebook commands completed.\n'")
args.emit.parent.mkdir(parents=True, exist_ok=True)
args.emit.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
print(f'Emitted {count} Bash blocks to {args.emit}')
