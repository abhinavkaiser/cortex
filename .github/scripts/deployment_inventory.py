#!/usr/bin/env python3
"""Report non-secret deployment metadata from the registered server runner."""
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.request
from pathlib import Path


def command(*arguments):
    return subprocess.check_output(arguments, text=True, stderr=subprocess.DEVNULL).strip()


def inventory():
    if os.geteuid() != 0 or socket.gethostname() != 'ubuntu-4gb-fsn1-1':
        raise SystemExit('The deployment runner must execute as root on the confirmed Hetzner server')
    application = Path('/opt/cortex')
    if not (application / 'backend/ai_academy.db').is_file():
        raise SystemExit('Expected production application/database not found')
    units = command('systemctl', 'list-unit-files', '--type=service', '--no-legend', '--no-pager')
    services = []
    for line in units.splitlines():
        unit = line.split()[0]
        if unit.startswith('actions.runner.') or not re.search(r'cortex|uvicorn|nextjs|pm2|nginx', unit):
            continue
        properties = command('systemctl', 'show', unit, '--property=Id,User,WorkingDirectory,FragmentPath,ActiveState')
        metadata = dict(line.split('=', 1) for line in properties.splitlines() if '=' in line)
        start = command('systemctl', 'show', unit, '--property=ExecStart', '--value')
        # Report executable paths only: never disclose command arguments or env.
        metadata['ExecutablePaths'] = re.findall(r'(?:^|[ {;])path=([^ ;}]+)', start)
        services.append(metadata)
    revision = command('git', '-c', 'safe.directory=/opt/cortex', '-C', str(application), 'rev-parse', 'HEAD')
    dirty = bool(command('git', '-c', 'safe.directory=/opt/cortex', '-C', str(application), 'status', '--porcelain', '--untracked-files=no'))
    with urllib.request.urlopen('https://cortex.xiox.in/health', timeout=20) as response:
        health = json.load(response)
    if health != {'status': 'ok'}:
        raise SystemExit('Production health check failed')
    return {
        'hostname': socket.gethostname(),
        'uid': os.geteuid(),
        'application': str(application),
        'revision': revision,
        'tracked_changes_present': dirty,
        'services': services,
        'runtime_paths': {name: shutil.which(name) for name in ('python3', 'node', 'npm')},
        'database': '/opt/cortex/backend/ai_academy.db',
        'health': health,
    }


if __name__ == '__main__':
    result = inventory()
    encoded = json.dumps(result, sort_keys=True)
    print(encoded)
    # Annotations can be read through the existing GitHub integration even when
    # its separate log-download destination is not enabled in network settings.
    escaped = encoded.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Cortex deployment inventory::' + escaped)
    print('Read-only root access verified. No application code, data or services changed.')
