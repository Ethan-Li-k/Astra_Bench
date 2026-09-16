"""Offline next-boundary guard: exercise the actual updater in an isolated copy."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime-apple-v1'))
from rsi.skill_learning import SkillMemory,validate_policy_instructions


def validate(markdown,runtime,output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'engineering-evidence'):
        raise ValueError('Synthetic preflight evidence must remain in IKEA engineering-evidence')
    output.mkdir(parents=True,exist_ok=False)
    skill=output/'candidate.md';skill.write_text(markdown)
    evidence=output/'synthetic-public-evidence.json'
    evidence.write_text('{"synthetic":true,"physical_actions":0,"success_credit":0}\n')
    memory=SkillMemory(output/'synthetic-memory',skill)
    memory.runtime_instructions=runtime
    result=dict(synthetic=True,actor_calls=0,physical_actions=0,success_credit=0,
        skill_sha256=hashlib.sha256(markdown.encode()).hexdigest(),
        updater_sha256=hashlib.sha256((ROOT/'runtime-apple-v1/rsi/skill_learning.py').read_bytes()).hexdigest())
    try:
        result['length']=validate_policy_instructions(markdown,runtime)
        updated=memory.update(markdown,'Synthetic interface preflight only; no physical experience.',
            [str(evidence)],output,'synthetic-preflight','not_started',change_summary='No live skill change')
        result.update(accepted=True,synthetic_version=updated['version'])
    except ValueError as exc:
        result.update(accepted=False,error=str(exc))
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('skill',type=Path);p.add_argument('runtime',type=Path)
    p.add_argument('output',type=Path);a=p.parse_args()
    result=validate(a.skill.read_text(),a.runtime.read_text(),a.output)
    print(json.dumps(result));sys.exit(0 if result['accepted'] else 1)
