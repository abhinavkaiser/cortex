#!/usr/bin/env python3
"""Backed-up, scoped Cortex release. Never seeds or replaces learner data."""
import argparse
import json
import os
import pwd
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

APP = Path('/opt/cortex')
CHECKOUT = Path(__file__).resolve().parents[2]
PM2_ENV = {**os.environ, 'PM2_HOME': '/root/.pm2'}


def run(*args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(Path(args[0]).name + ' failed with exit ' + str(result.returncode))
    return result.stdout.strip()


def git(*args):
    try:
        return run('git', '-c', 'safe.directory=/opt/cortex', '-C', str(APP), *args)
    except RuntimeError as error:
        raise RuntimeError('Production git ' + args[0] + ' failed') from error


def notice(title, data):
    encoded = json.dumps(data, sort_keys=True)
    print('::notice title=' + title + '::' + encoded.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D'), flush=True)


def preflight():
    if os.geteuid() != 0 or socket.gethostname() != 'ubuntu-4gb-fsn1-1':
        raise RuntimeError('Wrong deployment identity')
    python = next((p for p in [APP / 'backend/.venv/bin/python', APP / 'backend/venv/bin/python'] if p.is_file()), None)
    if python is None or not Path('/root/.pm2/rpc.sock').exists():
        raise RuntimeError('Expected Python environment and running PM2 daemon required')
    report = dict(python=str(python), node=run('node', '--version'), npm=run('npm', '--version'),
                  revision=git('rev-parse', 'HEAD'), tracked_changes=git('status', '--porcelain', '--untracked-files=no').splitlines(),
                  free_bytes=shutil.disk_usage(APP).free, backend_owner_uid=(APP / 'backend').stat().st_uid,
                  frontend_owner_uid=(APP / 'frontend').stat().st_uid,
                  frontend_node_modules=(APP / 'frontend/node_modules').is_dir())
    notice('Learning release preflight', report)
    return python, report


def backup_database(destination):
    with sqlite3.connect('file:/opt/cortex/backend/ai_academy.db?mode=ro', uri=True, timeout=30) as source:
        with sqlite3.connect(destination) as target:
            source.backup(target)
            if target.execute('pragma integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Backup integrity check failed')
    destination.chmod(0o600)


def restore_content(backup, published):
    """Restore only changed teaching records; preserve attempts and all learner data."""
    with sqlite3.connect(backup) as old, sqlite3.connect(APP / 'backend/ai_academy.db') as current:
        for slug, new_record in published.items():
            live = current.execute('select title,content_markdown,content_blocks,estimated_minutes from lessons where slug=?', (slug,)).fetchone()
            if live != new_record:
                continue  # Never overwrite edits made after publication.
            previous = old.execute('select title,content_markdown,content_blocks,estimated_minutes from lessons where slug=?', (slug,)).fetchone()
            if previous:
                current.execute('update lessons set title=?,content_markdown=?,content_blocks=?,estimated_minutes=? where slug=?', (*previous, slug))
                lesson_id = current.execute('select id from lessons where slug=?', (slug,)).fetchone()[0]
                # Before this first release, there were no learning-unit records.
                # Keeping attempts is intentional; a redeploy can reuse their version.
                has_units = old.execute("select 1 from sqlite_master where name='learning_units'").fetchone()
                previous_unit = old.execute('select * from learning_units where lesson_id=?', (lesson_id,)).fetchone() if has_units else None
                if previous_unit:
                    columns = [column[1] for column in old.execute('pragma table_info(learning_units)')]
                    assignments = ','.join(column + '=?' for column in columns if column != 'id')
                    values = [previous_unit[i] for i, column in enumerate(columns) if column != 'id']
                    current.execute('update learning_units set ' + assignments + ' where lesson_id=?', (*values, lesson_id))
                else:
                    current.execute('delete from learning_units where lesson_id=?', (lesson_id,))
        # Restore revised quizzes and decks without deleting any attempts.
        for quiz_id, original_json in current.execute('select quiz_id,original from learning_quiz_publications').fetchall():
            original = json.loads(original_json)
            prior = old.execute('select title,passing_score,questions,randomize_questions,max_attempts from quizzes where id=?', (quiz_id,)).fetchone()
            if prior:
                current.execute('update quizzes set title=?,passing_score=?,questions=?,randomize_questions=?,max_attempts=? where id=?', (*prior, quiz_id))
                had_publications = old.execute("select 1 from sqlite_master where name='learning_quiz_publications'").fetchone()
                previous_publication = old.execute('select version,original from learning_quiz_publications where quiz_id=?', (quiz_id,)).fetchone() if had_publications else None
                if previous_publication:
                    current.execute('update learning_quiz_publications set version=?,original=? where quiz_id=?', (*previous_publication, quiz_id))
                else:
                    current.execute('delete from learning_quiz_publications where quiz_id=?', (quiz_id,))
                module_id = current.execute('select module_id from quizzes where id=?', (quiz_id,)).fetchone()[0]
                deck = old.execute('select title,cards from flashcard_decks where module_id=?', (module_id,)).fetchone()
                if deck:
                    current.execute('update flashcard_decks set title=?,cards=? where module_id=?', (*deck, module_id))
        existed = old.execute("select 1 from courses where slug='ai-technical-bridge'").fetchone()
        if not existed:
            current.execute("update courses set is_published=0 where slug='ai-technical-bridge'")


def deploy(python, report):
    if report['tracked_changes'] or report['free_bytes'] < 2_000_000_000:
        raise RuntimeError('A clean checkout and at least 2 GB free are required')
    user = pwd.getpwnam('cortexapp')
    if report['backend_owner_uid'] != user.pw_uid or report['frontend_owner_uid'] != user.pw_uid:
        raise RuntimeError('Unexpected application owner')
    # No dependency change is part of this release. Do not mutate live node_modules.
    for name in ['package.json', 'package-lock.json']:
        if (APP / 'frontend' / name).read_bytes() != (CHECKOUT / 'frontend' / name).read_bytes():
            raise RuntimeError('Dependency changes require a separate deployment procedure')
    revision = run('git', '-C', str(CHECKOUT), 'rev-parse', 'HEAD')
    fetch_options = ['--unshallow'] if git('rev-parse', '--is-shallow-repository') == 'true' else []
    git('fetch', *fetch_options, str(CHECKOUT), revision)
    git('merge-base', '--is-ancestor', report['revision'], revision)
    backup_dir = Path('/opt/cortex-backups') / ('learning-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + revision[:10])
    backup_dir.mkdir(parents=True, mode=0o700)
    backup_dir.chmod(0o700)
    backup = backup_dir / 'ai_academy.db'
    backup_database(backup)
    (backup_dir / 'release.json').write_text(json.dumps(dict(previous_revision=report['revision'], revision=revision)))
    notice('Learning release stage', dict(stage='backup verified', backup=str(backup)))
    validation = backup_dir / 'publication-test.db'
    shutil.copy2(backup, validation)
    validation_env = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(validation)}
    run(str(python), 'scripts/publish_learning_path.py', '--apply', cwd=CHECKOUT / 'backend', env=validation_env)
    # Exercise additive schemas and API contracts with an isolated in-memory DB.
    run(str(python), '-m', 'pytest', 'tests/test_learning.py', '-q', cwd=CHECKOUT / 'backend', env={**os.environ, 'DATABASE_URL': 'sqlite://'})
    published = {}
    with sqlite3.connect(backup) as old, sqlite3.connect(validation) as candidate:
        for slug, title, markdown, blocks, minutes in candidate.execute('select slug,title,content_markdown,content_blocks,estimated_minutes from lessons'):
            before = old.execute('select title,content_markdown,content_blocks,estimated_minutes from lessons where slug=?', (slug,)).fetchone()
            if before != (title, markdown, blocks, minutes):
                published[slug] = (title, markdown, blocks, minutes)
    validation.unlink()
    notice('Learning release stage', dict(stage='production-copy publication and API tests passed'))
    build_dir = Path(tempfile.mkdtemp(prefix='cortex-learning-build-', dir='/opt'))
    frontend_build = build_dir / 'frontend'
    staged_next = APP / 'frontend' / ('.next-release-' + revision[:10])
    previous_next = backup_dir / 'next'
    switched = False
    try:
        shutil.copytree(CHECKOUT / 'frontend', frontend_build, ignore=shutil.ignore_patterns('node_modules', '.next', '.env*', '*.tsbuildinfo'))
        for path in [build_dir, *build_dir.rglob('*')]:
            if not path.is_symlink():
                os.chown(path, user.pw_uid, user.pw_gid)
        build_env = {'PATH': os.environ['PATH'], 'NEXT_PUBLIC_API_URL': 'https://cortex.xiox.in', 'NEXT_TELEMETRY_DISABLED': '1', 'CI': 'true'}
        run('runuser', '-u', 'cortexapp', '--', 'npm', 'ci', '--no-audit', '--no-fund', cwd=frontend_build, env=build_env)
        run('runuser', '-u', 'cortexapp', '--', 'npm', 'run', 'build', cwd=frontend_build, env=build_env)
        shutil.copytree(frontend_build / '.next', staged_next)
        # Preserve old hashed assets for browsers that loaded the previous page.
        if (APP / 'frontend/.next/static').is_dir():
            shutil.copytree(APP / 'frontend/.next/static', staged_next / 'static', dirs_exist_ok=True)
        for path in [staged_next, *staged_next.rglob('*')]:
            if not path.is_symlink():
                os.chown(path, user.pw_uid, user.pw_gid)
        notice('Learning release stage', dict(stage='production frontend build ready'))
        run('pm2', 'stop', 'cortex-backend', env=PM2_ENV)
        switched = True
        git('checkout', '--detach', revision)
        run('runuser', '-u', 'cortexapp', '--', str(python), 'scripts/publish_learning_path.py', '--apply', cwd=APP / 'backend',
            env={**os.environ, 'DATABASE_URL': 'sqlite:////opt/cortex/backend/ai_academy.db'})
        run('pm2', 'stop', 'cortex-frontend', env=PM2_ENV)
        if (APP / 'frontend/.next').exists():
            (APP / 'frontend/.next').rename(previous_next)
        staged_next.rename(APP / 'frontend/.next')
        run('pm2', 'restart', 'cortex-backend', env=PM2_ENV)
        run('pm2', 'restart', 'cortex-frontend', env=PM2_ENV)
        healthy = False
        for _ in range(20):
            try:
                with urllib.request.urlopen('https://cortex.xiox.in/health', timeout=5) as response:
                    backend_ok = json.load(response) == {'status': 'ok'}
                with urllib.request.urlopen('https://cortex.xiox.in/dashboard/learn', timeout=5) as response:
                    frontend_ok = response.status == 200 and 'Build skills by doing' in response.read().decode()
                if backend_ok and frontend_ok:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(2)
        if not healthy:
            raise RuntimeError('Release health checks did not pass')
        service = '[Unit]\nDescription=Cortex lesson source refresh\nAfter=network-online.target\n\n[Service]\nType=oneshot\nUser=cortexapp\nWorkingDirectory=/opt/cortex/backend\nExecStart=' + str(python) + ' scripts/refresh_curriculum_updates.py\nTimeoutStartSec=120\n'
        timer = '[Unit]\nDescription=Daily Cortex lesson source refresh\n\n[Timer]\nOnCalendar=*-*-* 06:15:00 UTC\nRandomizedDelaySec=300\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n'
        Path('/etc/systemd/system/cortex-curriculum-refresh.service').write_text(service)
        Path('/etc/systemd/system/cortex-curriculum-refresh.timer').write_text(timer)
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', 'cortex-curriculum-refresh.timer')
        run('systemctl', 'start', '--no-block', 'cortex-curriculum-refresh.service')
        notice('Learning release deployed', dict(revision=revision, backup=str(backup), lesson_records_changed=len(published),
                                                health='ok', source_timer='cortex-curriculum-refresh.timer'))
    except Exception:
        if switched:
            run('pm2', 'stop', 'cortex-backend', env=PM2_ENV)
            run('pm2', 'stop', 'cortex-frontend', env=PM2_ENV)
            restore_content(backup, published)
            git('checkout', '--detach', report['revision'])
            if previous_next.exists():
                failed = backup_dir / 'failed-next'
                if (APP / 'frontend/.next').exists():
                    (APP / 'frontend/.next').rename(failed)
                previous_next.rename(APP / 'frontend/.next')
            run('pm2', 'restart', 'cortex-backend', env=PM2_ENV)
            run('pm2', 'restart', 'cortex-frontend', env=PM2_ENV)
            notice('Learning release rollback', dict(revision=report['revision'], learner_data='preserved'))
        raise
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)
        if staged_next.exists():
            shutil.rmtree(staged_next)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true')
    parser.add_argument('--calibrate', action='store_true')
    args = parser.parse_args()
    python, report = preflight()
    if args.calibrate:
        calibration = subprocess.run(['runuser', '-u', 'cortexapp', '--', str(python), 'scripts/validate_education_models.py'], cwd=CHECKOUT / 'backend', capture_output=True, text=True)
        try: result = json.loads(calibration.stdout)
        except ValueError: result = dict(passed=False, error='Calibration process failed before reporting')
        notice('Education grader calibration', result)
        if calibration.returncode: raise RuntimeError('Education model calibration did not pass')
    elif args.deploy:
        try:
            deploy(python, report)
        except Exception as error:
            notice('Learning release failure', dict(error=str(error), kind=type(error).__name__))
            raise
    else:
        # Use the official CLI refresh path before testing live model controls.
        notice('Education authentication repair',json.loads(run('python3',str(CHECKOUT / '.github/scripts/refresh_cortex_auth.py'))))
        auth_reports=[]
        for flags in [[], ['--setting-sources','']]:
            auth=subprocess.run(['runuser','-u','cortexapp','--','claude',*flags,'auth','status','--json'],capture_output=True,text=True)
            try:
                state=json.loads(auth.stdout)
                auth_reports.append(dict(settings_disabled=bool(flags),logged_in=state.get('loggedIn'),method=state.get('authMethod'),key_source=state.get('apiKeySource')))
            except ValueError:auth_reports.append(dict(settings_disabled=bool(flags),exit=auth.returncode))
        notice('Education authentication metadata', auth_reports)
        env_code='import os,json;print(json.dumps({"home":os.environ.get("HOME"),"configured":{k:bool(os.environ.get(k)) for k in ["ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_BASE_URL","CLAUDE_CONFIG_DIR","CLAUDE_CODE_OAUTH_TOKEN"]}}))'
        notice('Education caller configuration',json.loads(run('runuser','-u','cortexapp','--','python3','-c',env_code)))
        auth_paths=[]
        for path in [Path('/home/cortexapp'),Path('/home/cortexapp/.claude'),Path('/home/cortexapp/.claude/.credentials.json'),Path('/home/cortexapp/.claude.json')]:
            if path.exists():auth_paths.append(dict(path=str(path),uid=path.stat().st_uid,mode=oct(path.stat().st_mode&0o777)))
        notice('Education authentication file metadata',auth_paths)

        help_text = run('runuser', '-u', 'cortexapp', '--', 'claude', '--help')
        notice('Education model controls', {flag: flag in help_text for flag in ['--tools', '--strict-mcp-config', '--setting-sources', '--no-session-persistence', '--disable-slash-commands', '--permission-mode']})
        references = []
        for url in json.loads((CHECKOUT / 'backend/content/source_checks.json').read_text()):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'CortexContentReview/1.0'})
                with urllib.request.urlopen(request, timeout=25) as response:
                    references.append(dict(url=url, status=response.status))
            except Exception as error:
                references.append(dict(url=url, error=type(error).__name__))
        notice('Curriculum references', references)
