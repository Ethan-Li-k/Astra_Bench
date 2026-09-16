"""Real rejected public row + explicitly synthetic later failures, no physics."""
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('baseline_memory',ROOT/'baseline/rsi/skill_learning.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
row=json.loads((ROOT/'evidence/public-experience-0001.json').read_text())
review=json.loads((ROOT/'evidence/host-only/success_review.json').read_text())
assert row['native_outcome']=='success' and review['audited_task_success'] is False
with tempfile.TemporaryDirectory(dir=ROOT/'tests') as temp:
    root=Path(temp);skill=root/'SKILL.md';skill.write_text('---\nname: loco-manip-direct\ndescription: test\n---\n')
    memory=module.SkillMemory(root/'memory',skill)
    rows=[row]+[dict(row,version=i,episode_id=f'synthetic-later-{i}',native_outcome='in_progress',
                     lesson='Synthetic later incomplete record for selection boundary only.') for i in range(2,7)]
    memory.journal.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    selected=[r['version'] for r in memory.read()['experiences']]
    assert selected==[1,4,5,6],selected
    result={'bug_reproduced':True,'real_source_episode':'boxplace-campaign/episode-0001',
            'native_outcome':'success','canonical_task_audit':False,
            'fixture_note':'Five later rows are synthetic, not new physical attempts.',
            'unbiased_recent_versions':[3,4,5,6],'actual_baseline_versions':selected,
            'effect':'Audit-rejected version1 displaces newer version3 as the pinned native success.'}
    (ROOT/'evidence/reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
