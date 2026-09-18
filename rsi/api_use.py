"""User-controlled stop checked before creating any new project API request."""
import json
from pathlib import Path

STOP_FILE=Path('/home/galbot/lizekai/RSI/ref/tasks/api-disabled.json')

class APIDisabledByUser(RuntimeError):
    pass

def require_api_enabled(path=STOP_FILE):
    if path.exists() and json.loads(path.read_text()).get('disabled') is True:
        raise APIDisabledByUser('API disabled by explicit user instruction; no automatic resume')
