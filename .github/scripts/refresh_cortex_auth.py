"""Repair stale expiry metadata using the existing account's official CLI refresh.

Credential contents never leave the server or appear in output. No new account,
API key or provider is introduced. An unrefreshable login is reported explicitly.
"""
import json
import os
import pwd
import shutil
import subprocess
import tempfile
from datetime import datetime,timezone
from pathlib import Path


def probe():
    with tempfile.TemporaryDirectory(prefix='cortex-auth-probe-') as folder:
        user=pwd.getpwnam('cortexapp');os.chown(folder,user.pw_uid,user.pw_gid)
        result=subprocess.run(['runuser','-u','cortexapp','--','claude','--print','--tools','','--strict-mcp-config','--setting-sources','','--disable-slash-commands','--no-session-persistence','--permission-mode','dontAsk','--system-prompt','Reply with the single word READY.'],input='Reply READY.',capture_output=True,text=True,cwd=folder,timeout=90)
    message=(result.stderr+' '+result.stdout).lower()
    return dict(ready=result.returncode==0 and result.stdout.strip().strip('.').upper()=='READY',expired='401' in message and 'expired' in message,exit=result.returncode)


def repair():
    path=Path('/home/cortexapp/.claude/.credentials.json')
    if not path.is_file():return dict(status='no_credentials')
    data=json.loads(path.read_text());oauth=data.get('claudeAiOauth',{})
    result=dict(refresh_available=bool(oauth.get('refreshToken')),expiry_metadata_present=isinstance(oauth.get('expiresAt'),(int,float)))
    before=probe();result['initial_probe']=before
    if before['ready']:return dict(**result,status='ready')
    if not before['expired'] or not oauth.get('refreshToken'):return dict(**result,status='interactive_sign_in_required' if before['expired'] else 'probe_failed')
    backup=Path('/opt/cortex-backups')/('auth-expiry-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True,mode=0o700);backup.chmod(0o700)
    shutil.copy2(path,backup/'credentials.json');(backup/'credentials.json').chmod(0o600)
    oauth['expiresAt']=0
    user=pwd.getpwnam('cortexapp')
    staged=path.with_name('.credentials.refresh-pending')
    staged.write_text(json.dumps(data));staged.chmod(0o600);os.chown(staged,user.pw_uid,user.pw_gid);staged.replace(path)
    after=probe()
    return dict(**result,status='ready' if after['ready'] else 'refresh_failed',final_probe=after)


if __name__=='__main__':
    try:print(json.dumps(repair()))
    except Exception as error:print(json.dumps(dict(status='repair_error',error_type=type(error).__name__)))
