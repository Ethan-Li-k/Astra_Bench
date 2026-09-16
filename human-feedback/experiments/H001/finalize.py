"""Finalize the authorized three-trial handoff; no model or physics calls."""
from pathlib import Path
import datetime
import hashlib
import json

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
BASE=ROOT/'human-feedback/reproductions/H001'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2))

def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    baseline=json.loads((BASE/'BASELINE_FROZEN.json').read_text())
    mismatches=[x['path'] for x in baseline['files'] if sha(BASE/x['path'])!=x['sha256']]
    dump(OUT/'baseline_verification_final.json',{'checked_utc':now,'files_checked':len(baseline['files']),
        'mismatches':mismatches,'baseline_manifest_sha256':sha(BASE/'BASELINE_FROZEN.json')})
    assert not mismatches
    rows=[];caps=[];runtime_hashes=[]
    for n in range(1,4):
        d=OUT/f'trial-{n:03d}';a=OUT/f'host_audit/trial-{n:03d}'
        r=json.loads((d/'result.json').read_text());v=json.loads((a/'version.json').read_text())
        e=json.loads((a/'assessment.json').read_text());i=json.loads((a/'actor_input_audit.json').read_text())
        actor=json.loads((d/'public/actor_report.json').read_text())
        history=[json.loads(s) for s in (d/'public/history.jsonl').read_text().splitlines()]
        assert r['error'] is None and r['new_physical_actions']>0 and e['same_recorded_prefix']
        assert not i['forbidden_public_key_violations']
        assert not e['retained_grasp_host_criterion'] and not actor['visible_retained_lift'], 'Success needs independent reset verification; do not finalize unsolved.'
        assert (OUT/f'logs/assess-{n}.exit').read_text().strip()=='0'
        assert (OUT/f'logs/trial-{n}.exit').read_text().strip()=='0'
        for path in r['videos'].values():assert Path(path).is_file()
        closure_actions=sum(any(x['arguments']['response']['trajectory'][0]['grippers'][s]>0 for s in ('left','right')) for x in history)
        policy=actor['candidate_rule']+'\nApplicable: '+actor['applicable_when']+'\nNot applicable: '+actor['not_applicable_when']
        caps.append({'trial':n,'main_words':i['actor_skill_words'],'main_characters':i['actor_skill_characters'],
            'candidate_with_conditions_words':len(policy.split()),'candidate_with_conditions_characters':len(policy),
            'main_sha256':i['actor_skill_sha256']})
        assert len(policy.split())<=831 and len(policy)<=6250
        runtime_hashes.append(v['frozen_runtime_sha256'])
        classification=('executed_closure_lift_not_retained_then_actor_stop' if closure_actions else
            'enclosure_acquisition_unresolved_physical_budget_grasp_untested')
        row={'trial':n,'independent_native_reset':True,'fixed_prefix_actions':59,
            'new_actions':r['new_physical_actions'],'new_physics_s':round(r['final_sim_s']-r['prefix_end_sim_s'],5),
            'total_physics_s_after_settle':round(r['final_sim_s']-5.005,5),
            'budget_overshoot_after_atomic_action_s':round(max(0,r['final_sim_s']-5.005-240),5),
            'feedback_versions':r['feedback_versions_used'],'classification':classification,
            'native_outcome':r['native_outcome_host_only'],'stop_reason':r['stop_reason'],
            'actions_with_nonzero_closure':closure_actions,'grasp_was_tested':bool(closure_actions),
            'retained_grasp_success':False,'original_placement_success':False,
            'primary_test':json.loads((d/'public/test_declaration.json').read_text())['one_main_change'],
            'observed_result':actor['observed_result'],'actor_next_hypothesis':actor['next_test'],
            'videos':r['videos'],'candidate':str(OUT/f'candidates/trial-{n:03d}.json'),
            'public_report':str(d/'public/actor_report.json'),'host_assessment':str(a/'assessment.json'),
            'actor_input_audit':str(a/'actor_input_audit.json'),'version_and_initial_state_root':str(a),
            'prefix_exact':e['same_recorded_prefix'],'maximum_apple_lift_host_m':e['maximum_apple_lift_m'],
            'model_wait_wall_s':i['policy_wait_sum_wall_s'],'model_thread':r['thread_id']}
        rows.append(row)
    assert all(x==runtime_hashes[0] for x in runtime_hashes)
    dump(OUT/'short_rule_length_checks.json',caps)
    comparison={'completed_utc':now,'case':'H001','backend':'SIMPLE / MuJoCo','non_RTC':True,
        'trial_class':'fixed_original_prefix_human_feedback_assisted_diagnostic',
        'fully_autonomous_from_reset_trials':0,'human_feedback_used':True,'human_demonstration_used':False,
        'independent_reset_correction_trials':3,'new_physical_actions':sum(x['new_actions'] for x in rows),
        'new_physics_s':sum(x['new_physics_s'] for x in rows),'retained_grasp_successes':0,
        'original_task_successes':0,'formal_campaign_credit':0,
        'actual_closure_lift_trials':1,'pregrasp_budget_end_trials':2,
        'physical_controller_source_identical_across_trials':True,'rows':rows,
        'feedback_comparability_limit':'Trial1 uses001–003; trials2/3 use001–004. Shared physics and reset, differing feedback/closure gate. Three correction trials do not establish three identical physical grasp failures.',
        'verified_limited_improvement':{'kind':'earlier public visibility of near-side thumb at an observation boundary',
            'trial2':{'new_action':14,'new_physics_s':21.06,'observation':str(OUT/'trial-002/public/rollout/episode/observations/0073')},
            'trial3':{'new_action':5,'new_physics_s':8.04,'observation':str(OUT/'trial-003/public/rollout/episode/observations/0064')},
            'review':'Actor records plus root inspection of original RGB; qualitative visibility, not a contact or success detector.',
            'limits':'One sequence per policy/order; visibility later lost during alignment. No grasp-success improvement or transfer demonstrated.'},
        'repeated_observations':['Lowering/2D overlap did not establish retained grasp in trial1.',
            'Trials2/3 alternate visibility acquisition and depth/height correction; later corrections lose key finger visibility.',
            'Translation tracking can be millimetric while attitude remains outside arrival tolerance.',
            'Visible thumb is insufficient to establish opposing-side enclosure.'],
        'unresolved_questions':['Which available public evidence can jointly establish depth and side-height enclosure under actual, drifting hand pose?',
            'Can the same controller maintain a suitable approach while preserving useful camera visibility?',
            'Only34.36s of the original240s budget remain after the fixed prefix; no longer correction budget or autonomous-from-reset comparison was run.',
            'No004-compliant closure/lift occurred; contact-surface and retention behavior after a genuinely established envelope remain untested.'],
        'shared_skill_published':False,'publisher':'SIMPLE supervisor only','paid_api_calls':0,
        'model':'gpt-6-astra','effort':'xhigh','launcher':str(ROOT/'codex-account-2/run.sh')}
    dump(OUT/'COMPARISON.json',comparison)
    notice={'recipient':'main_thread_read_only_reviewer','status':'ready_for_review_no_more_correction_runs',
        'notice_utc':now,'summary':'3 independent reset correction diagnostics,55 new actions,0 retained grasps. One closure/lift failure under003; two open-hand enclosure acquisition budget ends under004.',
        'bounded_authorized_work_finished':True,'grasp_objective_achieved':False,
        'human_question_sent':False,'human_help_eligibility':'Main thread must decide. Numeric count3 is met, but cannot claim3 comparable004 grasp failures; actual closure/lift tested only once.',
        'requested_main_thread_decision':'Review whether further autonomous diagnostic testing is warranted before considering representative human analysis. No automatic fourth correction trial.',
        'report':str(OUT/'REPORT.md'),'comparison':str(OUT/'COMPARISON.json'),
        'videos':[x['videos'] for x in rows],'candidate_proposals':[x['candidate'] for x in rows],
        'global_skill_modified':False}
    dump(OUT/'MAIN_THREAD_NOTICE.json',notice)
    state=json.loads((OUT/'status.json').read_text())
    state.update(phase='complete_bounded_diagnostics_unsolved_main_review',updated_utc=now,
        attempts_started=3,attempts_completed=3,new_actions_total=55,
        retained_grasp_successes=0,original_task_successes=0,
        actual_closure_lift_trials=1,pregrasp_budget_end_trials=2,
        human_help_requested=False,main_thread_notice=str(OUT/'MAIN_THREAD_NOTICE.json'),
        more_correction_runs_authorized_in_this_branch=False,
        report=str(OUT/'REPORT.md'),comparison=str(OUT/'COMPARISON.json'),
        baseline_files_verified_final=len(baseline['files']),baseline_mismatches=[],
        all_recorded_prefixes_exact=True,all_public_input_audits_passed=True,
        feedback_versions_by_trial={str(r['trial']):r['feedback_versions'] for r in rows},
        videos_by_trial={str(r['trial']):r['videos'] for r in rows},
        short_rule_length_checks=str(OUT/'short_rule_length_checks.json'),
        shared_skill_published=False,success_verification_required=False,
        success_verification_reason='No observed retained-grasp success to replicate.',
        automatic_retry=False,actor_running=False,physics_running=False)
    dump(OUT/'status.json',state)
    print(json.dumps({'independent_resets':3,'new_actions':55,'new_physics_s':comparison['new_physics_s'],
        'successes':0,'baseline_files_verified':len(baseline['files']),'short_caps':caps},ensure_ascii=False))

if __name__=='__main__':main()
