#!/usr/bin/env python3
"""Download published course files while keeping user_notebooks/ local."""
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def git(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def main():
    if not shutil.which('git'):
        raise RuntimeError('Git is not installed. Complete the initial workspace setup first.')
    if Path(git('rev-parse', '--show-toplevel')).resolve() != ROOT:
        raise RuntimeError('This script must be inside the course repository root.')
    personal = ROOT / 'user_notebooks'
    personal.mkdir(exist_ok=True)
    # Also protect the folder when updating an older checkout's .gitignore.
    exclude = ROOT / git('rev-parse', '--git-path', 'info/exclude')
    existing = exclude.read_text(encoding='utf-8') if exclude.exists() else ''
    if '/user_notebooks/' not in existing.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open('a', encoding='utf-8') as stream:
            stream.write('\n/user_notebooks/\n')
    if git('ls-files', '--', 'user_notebooks'):
        raise RuntimeError('user_notebooks contains tracked files. Move personal work to a safe location before updating.')
    print('Downloading course updates...', flush=True)
    git('fetch', 'origin', 'main')
    target = git('rev-parse', 'refs/remotes/origin/main^{commit}')
    if git('ls-tree', '-r', '--name-only', target, '--', 'user_notebooks'):
        raise RuntimeError('The published version contains user_notebooks. Update stopped to protect personal files.')
    name = 'before-update-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    git('branch', 'backup/' + name)
    # --include-untracked respects the personal-folder rule in info/exclude.
    git('stash', 'push', '--include-untracked', '-m', name)
    git('reset', '--hard', target)
    personal.mkdir(exist_ok=True)
    print('Course files updated. Local edits to course files were replaced.')
    print(f'Keep your own notebooks in: {personal}')
    print('Personal notebooks were preserved. Reopen course notebooks to load the new versions.')
    print('Running cluster services were not changed.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as exc:
        print(f'Update stopped: {exc}', file=sys.stderr)
        sys.exit(1)
