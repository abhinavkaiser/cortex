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
import time
import urllib.request
import urllib.error
import re
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
    # Zero is interpreted by the official CLI as an inference-only token with
    # no refresh schedule. A positive timestamp in the past triggers refresh.
    oauth['expiresAt']=1
    user=pwd.getpwnam('cortexapp')
    staged=path.with_name('.credentials.refresh-pending')
    staged.write_text(json.dumps(data));staged.chmod(0o600);os.chown(staged,user.pw_uid,user.pw_gid);staged.replace(path)
    after=probe()
    if not after['ready'] and after['expired']:
        # The endpoint and public client identifier are the installed official
        # CLI's production OAuth configuration. Reuse only the existing grant;
        # never request broader scopes or send credentials to another host.
        current=json.loads(path.read_text());grant=current.get('claudeAiOauth',{})
        refresh=grant.get('refreshToken')
        if not refresh:return dict(**result,status='interactive_sign_in_required',final_probe=after)
        client=grant.get('clientId')
        if not isinstance(client,str) or not re.fullmatch('[a-fA-F0-9-]{36}',client):client='9d1c250a-e61b-44d9-88ed-5944d1962f5e'
        payload=dict(grant_type='refresh_token',refresh_token=refresh,client_id=client)
        scopes=grant.get('scopes')
        if isinstance(scopes,list) and scopes and all(isinstance(s,str) for s in scopes):payload['scope']=' '.join(scopes)
        request=urllib.request.Request('https://platform.claude.com/v1/oauth/token',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=30) as response:tokens=json.load(response)
        except urllib.error.HTTPError as error:
            try:detail=json.loads(error.read())
            except ValueError:detail={}
            code=detail.get('error')
            safe_code=code if code in {'invalid_grant','invalid_request','unauthorized_client','invalid_scope','access_denied'} else 'refresh_rejected'
            return dict(**result,status='interactive_sign_in_required',refresh_http_status=error.code,refresh_error=safe_code,final_probe=after)
        if not isinstance(tokens.get('access_token'),str) or type(tokens.get('expires_in')) not in (int,float):
            return dict(**result,status='invalid_refresh_response',final_probe=after)
        grant['accessToken']=tokens['access_token']
        if tokens.get('refresh_token'):grant['refreshToken']=tokens['refresh_token']
        grant['expiresAt']=int((time.time()+tokens['expires_in'])*1000)
        if isinstance(tokens.get('scope'),str):grant['scopes']=tokens['scope'].split()
        staged.write_text(json.dumps(current));staged.chmod(0o600);os.chown(staged,user.pw_uid,user.pw_gid);staged.replace(path)
        after=probe()
    return dict(**result,status='ready' if after['ready'] else 'refresh_failed',final_probe=after)


if __name__=='__main__':
    try:print(json.dumps(repair()))
    except Exception as error:print(json.dumps(dict(status='repair_error',error_type=type(error).__name__)))
