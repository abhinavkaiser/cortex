"""Install the pinned app-only Codex CLI; inspect login without exposing tokens."""
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess

VERSION='0.164.0'
PREFIX=Path('/opt/cortex-codex')
if os.geteuid()!=0 or socket.gethostname()!='ubuntu-4gb-fsn1-1':
    raise RuntimeError('Wrong deployment identity')
user=pwd.getpwnam('cortexapp')
PREFIX.mkdir(mode=0o755,exist_ok=True)
os.chown(PREFIX,user.pw_uid,user.pw_gid)
binary=PREFIX/'node_modules/.bin/codex'
installed=subprocess.run([str(binary),'--version'],capture_output=True,text=True) if binary.exists() else None
if not installed or installed.returncode or installed.stdout.strip()!='codex-cli '+VERSION:
    result=subprocess.run(['runuser','-u','cortexapp','--','npm','install','--prefix',str(PREFIX),'--no-audit','--no-fund','@openai/codex@'+VERSION],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('App-only Codex installation failed')
help_result=subprocess.run([str(binary),'exec','--help'],capture_output=True,text=True,check=True)
required=['--ignore-user-config','--ignore-rules','--ephemeral','--json','--sandbox']
if not all(flag in help_result.stdout for flag in required):raise RuntimeError('Required Codex isolation controls missing')
auth=subprocess.run(['runuser','-u','cortexapp','--',str(binary),'login','status'],capture_output=True,text=True)
ready=auth.returncode==0 and 'chatgpt' in (auth.stdout+auth.stderr).lower()
print('::notice title=Codex subscription runtime::'+json.dumps(dict(version=VERSION,binary=str(binary),subscription_login=ready,status='ready_for_calibration' if ready else 'subscription_sign_in_required')))
