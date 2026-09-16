"""Public-source mechanism selection only; never reads host audit."""
import hashlib
import json
from pathlib import Path
ROOT=Path('/home/galbot/lizekai/RSI');OUT=Path(__file__).resolve().parent
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
frozen=ROOT/'codex-account-2/workspace/ground-to-table/provenance/episodes/episode-0007'
setting=json.loads((frozen/'setting_manifest.json').read_text())
ep=ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0002'
selected=[
 dict(id='ground002-approach-counterexample-v1',status='unvalidated_candidate',source=[ref(ep/'rollout/public_decision_0049.json'),ref(ep/'rollout/public_decision_0051.json'),ref(ep/'rollout/public_decision_0053.json')],
      mechanism='unloaded foot movement and approach',use='Use current measured heading and RGB. Elevated ankle references alone did not establish unloading; simultaneous turning/advancing constraints were absorbed into posture in the later twisted stance. Avoid repeating that condition unchanged.',
      prerequisites='Original G1/DEX3/model38000/WristPI contract. Empty hands and current stable posture must be rechecked.',
      different_test='On the fresh reset test observable clearance and advancement before accumulating heading correction with forward motion. Choose concrete targets from the new observation.',
      not_for='Not a validated gait; cannot infer loaded carrying, grasp or table placement.'),
 dict(id='simple-door0011-unload-reposition-v11',status='mechanism_hypothesis_only',source=[ref(ROOT/'artifacts/R019/door-campaign/memory/experience.jsonl')],
      mechanism='free arm reach versus stance progression',use='Public door0011 lesson reports a stalled extended push, followed by unloading/retracting the open hand, changing stance and reacquiring working height. Reconsider support/posture when wrist reach stalls.',
      prerequisites='Only the support/arm-load hypothesis is transferable. Source SimpleLiveSim/corrected door asset differs from this original-table backend; exact controller/contract identity is not established.',
      different_test='Check low free-arm posture and measured support response in this scene; no door coordinates, hand targets or success label transferred.',
      not_for='No import of door geometry, contact truth, whole gait recipe, loaded locomotion or door success count.'),
 dict(id='ground001-original-table-v1',status='unvalidated_candidate',source=[ref(ROOT/'api-ground-to-table/actor-adapter/campaign/episode-0001/rollout/history.jsonl')],
      mechanism='coordinated empty-hand locomotion',use='First batch ended at six requests/three actions with task incomplete. Larger coordinated arcs had measurable foot relocation but arm motion, posture and amplitude were confounded.',
      prerequisites='Same original-table runtime; freshly measure start pose.',different_test='Validate actual foot clearance, placement and body advance separately.',not_for='No proof of pickup or loaded walking.')]
v=dict(schema=1,run_id='api-ground-003',episode='episode-0003',stage='approach',backend='MuJoCo',
    human_feedback_used=True,human_demonstration_used=False,
    control=dict(setting=setting['setting'],model_sha256=setting['model_sha256'],wrist_pi=setting['wrist_pi'],
      original_table_offset_m=0,setting_manifest=ref(frozen/'setting_manifest.json'),
      continuous_contract_sha256=hashlib.sha256(json.dumps(setting['continuous_chunk_contract'],sort_keys=True).encode()).hexdigest(),
      four_point_implementation=ref(frozen/'rsi/four_point.py'),policy_harness=ref(frozen/'rsi/policy_harness.py')),
    selected=selected,rejected=[dict(id='simple-boxplace-native-success-0001-0002',reason='Public lessons explicitly lack verified acquisition/lift/retained transport/release. Never use these native success labels as a complete placement skill.',source=ref(ROOT/'artifacts/R019/boxplace-campaign/memory/experience.jsonl'))],
    no_truncation_handoff=ref(ROOT/'artifacts/architecture-review-20260916/HANDOFF-API.md'),
    notes='Public mechanism summaries only; old timestamps/paths are historical. No replay, success promotion or hidden audit data. Original task and live controller contract prevail.')
(OUT/'public-transfer.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'selected':[x['id'] for x in selected],'rejected':[x['id'] for x in v['rejected']],'hash':ref(OUT/'public-transfer.json')['sha256']}))
