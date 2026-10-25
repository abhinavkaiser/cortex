"""Run the existing public Daily Pulse job without exposing its raw logs."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
from datetime import datetime,timezone

if os.geteuid()!=0 or socket.gethostname()!='ubuntu-4gb-fsn1-1':raise RuntimeError('Wrong deployment identity')
app=Path('/opt/cortex/backend')
python=next(p for p in [app/'.venv/bin/python',app/'venv/bin/python'] if p.exists())
result=subprocess.run(['runuser','-u','cortexapp','--',str(python),'scripts/run_daily_pulse.py'],cwd=app,capture_output=True,text=True,timeout=900)
with sqlite3.connect('file:/opt/cortex/backend/ai_academy.db?mode=ro',uri=True) as db:
    rows=db.execute('select t.slug,p.pulse_date,p.status,p.eval_score from daily_pulses p join tracks t on t.id=p.track_id where p.id in (select max(id) from daily_pulses group by track_id)').fetchall()
today=datetime.now(timezone.utc).date().isoformat()
report=dict(exit=result.returncode,pulses=[dict(track=slug,date=date,status=status,quality_score=score) for slug,date,status,score in rows],all_current_published=bool(rows) and all(date==today and status.lower()=='published' for _,date,status,_ in rows))
print('::notice title=Public daily content refresh::'+json.dumps(report))
raise SystemExit(0 if result.returncode==0 and report['all_current_published'] else 1)
