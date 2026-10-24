"""Read-only production evidence for the learning-system assessment.

Does not generate content, query learner records, dump credentials or mutate DBs.
Only whitelisted aggregate/configuration metadata is emitted to check notices.
"""
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

APP = Path('/opt/cortex/backend')
ENTRYPOINTS = ('run_daily_pulse.py', 'generate_lesson_content.py', 'generate_quizzes.py', 'generate_flashcards.py')


def run(arguments, **kwargs):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=kwargs.pop('timeout', 15), **kwargs)


def main():
    assert os.geteuid() == 0 and socket.gethostname() == 'ubuntu-4gb-fsn1-1'
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'hostname': socket.gethostname()}
    with sqlite3.connect((APP / 'ai_academy.db').as_uri() + '?mode=ro', uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        names = ('courses', 'modules', 'lessons', 'quizzes', 'flashcard_decks', 'daily_pulses', 'tracks')
        report['content_counts'] = {name: db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0] for name in names if name in tables}
        if 'daily_pulses' in tables:
            report['pulse_statuses'] = db.execute('SELECT status,COUNT(*),MIN(pulse_date),MAX(pulse_date) FROM daily_pulses GROUP BY status').fetchall()
            report['pulse_recent_dates'] = db.execute('SELECT pulse_date,COUNT(*) FROM daily_pulses GROUP BY pulse_date ORDER BY pulse_date DESC LIMIT 14').fetchall()
            report['pulse_duplicate_groups'] = db.execute('SELECT COUNT(*) FROM (SELECT pulse_date,track_id FROM daily_pulses GROUP BY pulse_date,track_id HAVING COUNT(*)>1)').fetchone()[0]
        report['lesson_columns'] = [r[1] for r in db.execute('PRAGMA table_info(lessons)')]
        report['lesson_creation_range'] = db.execute('SELECT MIN(created_at),MAX(created_at) FROM lessons').fetchone()
        corpus = db.execute('SELECT id,slug,title,content_markdown,content_blocks FROM lessons ORDER BY id').fetchall()
        report['lesson_content_sha256'] = hashlib.sha256(json.dumps(corpus, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

    schedules = []
    def scan_cron(text, source):
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            matches = [entry for entry in ENTRYPOINTS if entry in stripped]
            if matches:
                fields = stripped.split()
                schedules.append({'source': source, 'schedule': fields[0] if fields[0].startswith('@') else ' '.join(fields[:5]), 'entrypoints': matches})
    root_cron = run(['crontab', '-l'])
    scan_cron(root_cron.stdout, 'root crontab')
    for path in [Path('/etc/crontab'), *Path('/etc/cron.d').glob('*')]:
        if path.is_file():
            scan_cron(path.read_text(errors='replace'), str(path))
    # Other installed user crontabs, if any; serialize only matching schedules.
    spool = Path('/var/spool/cron/crontabs')
    if spool.is_dir():
        for path in spool.iterdir():
            if path.is_file() and path.name != 'root':
                scan_cron(path.read_text(errors='replace'), 'user crontab ' + path.name)
    report['matching_cron_schedules'] = schedules
    timers = run(['systemctl', 'list-units', '--all', '--type=timer', '--no-legend', '--no-pager'])
    matched_timers = []
    for line in timers.stdout.splitlines():
        fields = line.lstrip('● ').split()
        if not fields:
            continue
        timer = fields[0]
        if not timer.endswith('.timer'):
            continue
        unit = timer[:-6] + '.service'
        start = run(['systemctl', 'show', unit, '--property=ExecStart', '--value']).stdout
        matches = [entry for entry in ENTRYPOINTS if entry in start]
        if matches or re.search('cortex|pulse|academy', timer, re.I):
            matched_timers.append({'timer': timer, 'entrypoints': matches})
    report['matching_systemd_timers'] = matched_timers

    backend_environment = os.environ.copy()
    pm2_home = Path('/root/.pm2')
    if (pm2_home / 'pm2.pid').is_file() and (pm2_home / 'rpc.sock').exists():
        result = run(['pm2', 'jlist'], env={**os.environ, 'PM2_HOME': str(pm2_home)})
        for process in json.loads(result.stdout):
            if process.get('name') == 'cortex-backend':
                metadata = process.get('pm2_env', {})
                for key in ('PATH', 'HOME', 'CLAUDE_CONFIG_DIR', 'ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN'):
                    value = metadata.get(key, metadata.get('env', {}).get(key))
                    if isinstance(value, str):
                        backend_environment[key] = value
                pid = process.get('pid')
                if pid and Path('/proc', str(pid)).exists():
                    report['backend_process_uid'] = Path('/proc', str(pid)).stat().st_uid
                report['backend_auth_binding_presence'] = {key: bool(backend_environment.get(key)) for key in ('CLAUDE_CONFIG_DIR', 'ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN')}
    python = next((str(p) for p in (APP / '.venv/bin/python', APP / 'venv/bin/python') if p.is_file()), None)
    if python:
        settings_code = 'import json; from app.core.config import get_settings; s=get_settings(); print(json.dumps({"claude_bin":s.claude_bin,"claude_model":s.claude_model,"feeds":s.daily_pulse_rss_feeds}))'
        settings = run([python, '-c', settings_code], cwd=str(APP), env=backend_environment)
        if settings.returncode == 0:
            configuration = json.loads(settings.stdout)
            report['configured_generation_model'] = configuration['claude_model']
            binary = shutil.which(configuration['claude_bin'], path=backend_environment.get('PATH'))
            report['claude_binary_available'] = bool(binary)
            if binary:
                auth = run([binary, 'auth', 'status'], cwd=str(APP), env=backend_environment)
                try:
                    status = json.loads(auth.stdout)
                    report['claude_auth'] = {key: status.get(key) for key in ('loggedIn', 'authMethod', 'apiProvider')}
                except json.JSONDecodeError:
                    report['claude_auth'] = {'status': 'unrecognized status output', 'exit_code': auth.returncode}
            # Same client defaults and status handling as the actual RSS ingest.
            feed_code = '''import json,httpx,feedparser
from urllib.parse import urlsplit
from app.core.config import get_settings
results=[]
with httpx.Client(timeout=10.0,headers={"User-Agent":"AIAcademyDailyPulse/1.0"}) as client:
 for url in get_settings().daily_pulse_rss_feeds:
  item={"host":urlsplit(url).hostname}
  try:
   response=client.get(url)
   item["http_status"]=response.status_code
   item["rss_entries"]=len(feedparser.parse(response.content).entries) if response.status_code==200 else 0
  except httpx.HTTPError as error:
   item["error_type"]=type(error).__name__
  results.append(item)
print(json.dumps(results))'''
            feeds = run([python, '-c', feed_code], cwd=str(APP), env=backend_environment, timeout=30)
            if feeds.returncode == 0:
                report['live_feed_checks'] = json.loads(feeds.stdout)
            else:
                report['live_feed_checks'] = {'status': 'feed probe unavailable', 'exit_code': feeds.returncode}
        else:
            report['configuration_probe'] = {'status': 'unavailable', 'exit_code': settings.returncode}
    else:
        report['configuration_probe'] = {'status': 'no expected backend virtualenv found'}
    encoded = json.dumps(report, sort_keys=True)
    print('::notice title=Cortex learning assessment::' + encoded.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A'))


if __name__ == '__main__':
    main()
