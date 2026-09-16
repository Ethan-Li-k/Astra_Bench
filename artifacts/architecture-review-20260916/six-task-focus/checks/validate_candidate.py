"""Static admission only. Reuse actual current instruction-cap implementation."""
import ast,hashlib,importlib.util,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[1];snapshot=R/'snapshots';out=R/'checks'
caller=snapshot/'tools/learn_grasp_skill.py';tree=ast.parse(caller.read_text())
immutable=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='immutable' for t in n.targets))
module=ast.parse((snapshot/'rsi/codex_app_server.py').read_text())
network=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='NETWORK_CONTINUATION' for t in n.targets))
overhead=immutable+network
spec=importlib.util.spec_from_file_location('local_size_validation',snapshot/'rsi/skill_learning.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
common=(R/'candidate/loco-manip-direct/SKILL.md').read_text();assert common.startswith('---\nname: loco-manip-direct\n')
rows={}
for p in sorted((R/'candidate/deltas').glob('*.md')):
 text=common+'\n'+p.read_text();sizes=m.validate_policy_instructions(text,overhead)
 # Detail is independently included in this conservative check, even if read on demand.
 rows[p.stem]={'combined':sizes,'actor_markdown':m.skill_size(text),'sha256':hashlib.sha256(text.encode()).hexdigest(),'delta_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
reject=False
try:m.validate_policy_instructions(common+'\n'+('x'*6251),overhead)
except ValueError:reject=True
assert reject
# Candidate sources must not point to reviewer-only evidence or embed host audit payloads.
for p in (R/'candidate').rglob('*.md'):
 text=p.read_text();assert not any(token in text for token in ('host-audit/','success_review.json','failure_review.json','native-task-criteria.json','mjData','data.qpos','host_audit'))
receipt={'passed':True,'physics_or_model_started':False,'current_runtime_sha256':hashlib.sha256(overhead.encode()).hexdigest(),
 'runtime_size':m.skill_size(overhead),'network_continuation_reserved':network,'variants':rows,'oversize_rejected_without_truncation':reject,
 'instruction_cap_source_sha256':hashlib.sha256((snapshot/'rsi/skill_learning.py').read_bytes()).hexdigest(),
 'actor_markdown_scope':'common entrypoint plus exactly one entire task delta; actual fixed runtime plus recovery prompt',
 'not_counted_as_new_skill_sources':'reviewer-only receipts and static native criteria never enter actor package'}
(out/'length-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
(out/'runtime-instructions.txt').write_text(overhead)
print(json.dumps(receipt,indent=2))
