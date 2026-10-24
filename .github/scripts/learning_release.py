#!/usr/bin/env python3
"""Production preflight and narrowly scoped release of the learning changes."""
import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

APP = Path('/opt/cortex')


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, **kwargs).strip()


def notice(title, data):
    encoded = json.dumps(data, sort_keys=True)
    print('::notice title=' + title + '::' + encoded.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D'), flush=True)


def preflight():
    if os.geteuid() != 0 or socket.gethostname() != 'ubuntu-4gb-fsn1-1':
        raise RuntimeError('Wrong deployment identity')
    python = next((p for p in [APP / 'backend/.venv/bin/python', APP / 'backend/venv/bin/python'] if p.is_file()), None)
    if python is None:
        raise RuntimeError('Production Python environment not found')
    status = run('git', '-c', 'safe.directory=/opt/cortex', '-C', str(APP), 'status', '--porcelain', '--untracked-files=no')
    # File names only; never file contents or environment values.
    report = dict(python=str(python), node=run('node', '--version'), npm=run('npm', '--version'),
                  revision=run('git', '-c', 'safe.directory=/opt/cortex', '-C', str(APP), 'rev-parse', 'HEAD'),
                  tracked_changes=status.splitlines(), free_bytes=shutil.disk_usage(APP).free,
                  backend_owner_uid=(APP / 'backend').stat().st_uid,
                  frontend_owner_uid=(APP / 'frontend').stat().st_uid,
                  frontend_node_modules=(APP / 'frontend/node_modules').is_dir())
    notice('Learning release preflight', report)
    return python


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    args = parser.parse_args()
    preflight()
    if args.deploy:
        raise SystemExit('Deployment procedure not yet prepared')
    # These fixed public documentation requests do not touch application data.
    import re
    sources = json.loads(Path('backend/content/source_checks.json').read_text())
    for url in sources:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CortexContentReview/1.0'})
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read(150000).decode('utf-8', errors='replace')
                title = re.search(r'<title[^>]*>(.*?)</title>', body, re.S | re.I)
                notice('Curriculum reference', dict(url=url, status=response.status, title=re.sub('<[^>]*>', '', title.group(1))[:200] if title else 'Feed or document'))
        except Exception as error:
            notice('Curriculum reference', dict(url=url, error=type(error).__name__))
