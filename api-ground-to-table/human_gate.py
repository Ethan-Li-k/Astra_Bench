"""Escalation gate over evidence-verified host records, not an evidence verifier.

The case owner must validate paths/hashes and mechanism/control compatibility.
Synthetic tests and fixed-action reproductions never become physical evidence.
"""
def assess(records,mechanism,control_signature,self_review_completed):
    episodes,resets,accepted=set(),set(),[]
    for r in records:
        if (r.get('mechanism')!=mechanism or r.get('control_signature')!=control_signature
            or r.get('new_physics') is not True or r.get('exploration') is not True
            or r.get('complete') is not True or r.get('success') is not False
            or r.get('terminal_kind') not in ('physical_failure','safety_stop')
            or r.get('actions',0)<=0 or not r.get('video') or not r.get('evidence')
            or not r.get('tested_change') or not r.get('episode') or not r.get('reset')):
            continue
        if r['episode'] in episodes or r['reset'] in resets:continue
        episodes.add(r['episode']);resets.add(r['reset']);accepted.append(r)
    allowed=len(accepted)>=3 and self_review_completed is True
    return {'can_ask_human':allowed,'minimum_failures':3,
        'comparable_independent_failure_count':len(accepted),
        'self_review_completed':self_review_completed is True,
        'episodes':[r['episode'] for r in accepted],
        'reason':'eligible_not_mandatory' if allowed else 'continue_agent_owned_trials_or_evidence_review'}
