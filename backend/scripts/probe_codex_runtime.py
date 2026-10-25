"""Fixed-prompt runtime diagnostic. Never prints credentials or raw provider output."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services import claude_client
from app.services.education_grading import MODELS
cache=Path.home()/'.codex/models_cache.json'
if cache.exists():
    data=json.loads(cache.read_text())
    metadata=dict(available_models=[{key:item[key] for key in ['slug','display_name','supported_in_api','default_reasoning_level'] if key in item} for item in data.get('models',[])])
else:metadata=dict(available_models=[])
actual=claude_client.subprocess.run
reports=[]
SIGNALS=['unknown option','unrecognized','unknown field','unknown feature','not supported','not available','model_not_found','invalid model','not a valid','error loading config','failed to load','failed to read','read-only','permission denied','no such file','401','403','429','usage limit','rate limit','refresh token','not logged in','unsupported value','invalid value','unexpected argument','requires','invalid configuration','invalid type','failed to spawn','not found','unauthorized','authentication','server error']
def probe_run(*args,**kwargs):
    result=actual(*args,**kwargs)
    combined=(result.stderr+' '+result.stdout).lower()
    events=[]
    for line in result.stdout.splitlines():
        try:
            data=json.loads(line)
            events.append(dict(type=data.get('type'),item_type=data.get('item',{}).get('type')))
        except ValueError:pass
    reports.append(dict(exit=result.returncode,signals=[key for key in SIGNALS if key in combined],events=events))
    return result
claude_client.subprocess.run=probe_run
for model in MODELS:
    try:
        value=claude_client._spawn_claude('Reply with the single word READY.',model,timeout=60)
        reports[-1].update(model=model,ready=value.strip().strip('.').upper()=='READY')
    except Exception as error:
        if not reports or 'model' in reports[-1]:reports.append({})
        reports[-1].update(model=model,error_type=type(error).__name__,ready=False)
print(json.dumps(dict(**metadata,probes=reports)))
