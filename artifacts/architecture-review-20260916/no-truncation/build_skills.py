import ast,json,hashlib,re
from pathlib import Path
B=Path(__file__).resolve().parent
common='''Use gpt-6-astra/xhigh. Read workspace task, current tool contract and selected public experience. Before acting state 当前问题 / 总目标 / 不可重犯的错误, selected experience IDs/versions, prerequisites, counterexamples and conditions to recheck. Route control contract, locomotion, interaction mechanism, then task instance; explicitly decline transfer without compatibility evidence.

Use only public RGB/calibration, named robot measurements, own command receipts and authorized public sources. Never inspect host evaluator/object/contact truth. Preserve human-feedback tier. Four points are left/right wrist_yaw_link and ankle_roll_link: absolute metre positions, unit wxyz quaternions, named active sets; grippers 0=open, 1=closed. Wrists are not TCPs. Follow current observation limits and start/next_call; never reset an initialized episode. Geometry tools do not execute. Fresh request IDs, observations and ACKs precede each changed action. Target arrival, closure and image overlap do not prove manipulation.

Await complete inference and tool responses. A natural model turn end is not task completion. Only the owner may continue a confirmed closed turn in the same live thread/reset; reconcile receipts and observe first, never replay uncertain actions. EOF, unknown RPC outcome and host restart require owner diagnosis. Do not retry quota, authorization or safety stops. Respect physical and authorized-call boundaries. finish_attempt records a changed hypothesis, not early termination. Keep concise NOTES with phase, last confirmed action, uncertainty and next observation.

Update local skill only after real new evidence, reproducible failure, contract change or explicit correction. Preserve source/version, failures and feedback tier. Candidate, locally validated and shared validated are distinct; shared publisher alone promotes, pins at episode start and never hot-edits a running episode. Audit labels affect retrieval eligibility only: rejected, unknown, incomplete or incompatible native success is not a successful template. Hidden audit payload never becomes visual evidence.
'''
tasks={
'simple':('SIMPLE condition-based continuation','''Goal and completion_contract come from this task workspace. Use S-TABLE-retrieve only for retrieve/check/correct; no historical world coordinates. S-DOOR-unload is a candidate only for compatible fixed-frame push-open: check whole-hand clearance, panel/frame motion, support and posture after unloading. It does not establish a gait, latch operation or original IKEA success. S-BOX-lift supports testing grasp with a fresh lift/hold observation, not assuming carry/release. S-APPLE-closure is a counterexample: visible enclosure precedes closure; reobserve before lifting. Faucet rotation and box placement remain unvalidated: separate mechanism motion from camera motion, and acquisition/lift from release/container support. Budget-ended episodes are incomplete, not new manipulation successes. Recheck camera convention and controller/hand geometry after interface changes; no numerical trajectory replay.'''),
'ground':('Floor cube to original table','''Goal: approach the floor cube, grasp, carry airborne to the original table, release, withdraw and stay standing. Current approved batch allows at most 120 API calls and 180 physical seconds; authorization is episode-specific, never renewed by this skill. Host has initialized physics: follow next_call, not another loco_start. Preserve human planning feedback: approach reachable stable stance before bending; it is not a demonstrated gait. G-APPROACH-001 supplies experimental foot-relocation observations only. G-DESCENT-007 warns against unchanged long-reach bilateral descent after tilt. Recompute from current heading/robot geometry and views. Empty-hand walking does not validate carrying; lifting does not validate stable transport or release. Recheck load, support, enclosure, carry clearance and table placement at each phase. Episode002 interruption provides no validated grasp/carry lesson; do not replay its uncertain final action/request.'''),
'ikea':('IKEA door mechanism identification','''Door task only: use the owner-declared scene, controller and completion contract; do not assume a latch, free hinge or SIMPLE geometry. No IKEA actor success currently supports a motion template. Import S-DOOR-unload only as a hypothesis about reach/support after visually establishing compatible push-open mechanics. Reconfirm hinge side, permitted direction, handle/clearance and actual panel response; a handle-looking shape is not proof of a latch. Without a compatible declared mechanism explicitly decline door-policy transfer. Preserve source-scene versus engineered-variant qualification in task identity. Apple, refrigerator and combined-task goals require their own task contracts; this door candidate supplies no recipe for them. Owner must resolve the actual tool/runtime contract and authorize execution before this prepared skill is eligible.''')}

def literal(path,name):
 tree=ast.parse(path.read_text())
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets):return ast.literal_eval(n.value)
 raise ValueError(name)
runtime=literal(B/'snapshots/tools/learn_grasp_skill.py','immutable')
api=literal(B/'snapshots/api-ground-to-table/actor-adapter/actor.py','INSTRUCTIONS')
(B/'runtime/simple.txt').write_text(runtime)
(B/'runtime/ground.txt').write_text('\n'+api)
# IKEA has no running actor/selected production runtime. This basis is conditional only.
(B/'runtime/ikea-proposed.txt').write_text(runtime)
rows=[]
for key,(title,task) in tasks.items():
 d=B/'skills'/key;d.mkdir(parents=True,exist_ok=True)
 s=f'---\nname: continuity-{key}\ndescription: Apply public conditional experience and preserve execution continuity for {title.lower()}.\n---\n\n# {title}\n\nVersion NT-20260916-v1; unmerged candidate.\n\n'+common+'\n'+task+'\n'
 (d/'SKILL.md').write_text(s)
 rt=api if key=='ground' else runtime
 combined=s+ ('\n' if key=='ground' else '')+rt
 size=dict(words=len(combined.split()),characters=len(combined),non_whitespace_characters=len(re.sub(r'\s','',combined)))
 passed=size['words']<=831 and size['characters']<=6250 and size['non_whitespace_characters']<=5357
 assert passed,(key,size)
 rows.append(dict(task=key,skill_sha256=hashlib.sha256(s.encode()).hexdigest(),runtime_sha256=hashlib.sha256((('\n' if key=='ground' else '')+rt).encode()).hexdigest(),combined=size,passed=passed,runtime_basis='actual snapshotted caller' if key!='ikea' else 'conditional LearningHost proposal; actual IKEA runtime not selected; MUST recheck before launch'))
(B/'evidence/length-validation.json').write_text(json.dumps(rows,indent=2))
