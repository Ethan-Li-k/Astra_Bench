"""Offline per-process reset/inference checks for the existing Sonic task set."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in json.loads(args.inventory.read_text())['entries']:
        if not task['native_sonic']: continue
        output = args.output/task['kwargs']['task']
        if task.get('initialization_evidence'):
            result_path = Path(task['initialization_evidence'])
        else:
            result_path = output/'result.json'
            if not result_path.exists():
                with (args.output/(task['kwargs']['task']+'.log')).open('a') as log:
                    code = subprocess.call([sys.executable, 'tools/simple_scalebfm_audit.py',
                        '--output',str(output),'--env-id',task['id'],
                        '--data-root','data/simple/runtime'], stdout=log, stderr=log)
                if not result_path.exists():
                    rows.append({'env_id':task['id'],'status':'initialization_process_error','exit_code':code})
                    continue
        result = json.loads(result_path.read_text())
        row = {k:result[k] for k in ('env_id','status','error_type','error') if k in result}
        row['evidence'] = str(result_path.resolve()); rows.append(row)
        (args.output/'summary.json').write_text(json.dumps({'scope':'Reset/inference availability only; no task-success credit','results':rows},indent=2))
        print(json.dumps(row), flush=True)


if __name__ == '__main__': main()
