#!/usr/bin/env python3
"""Read-only candidate preflight + UNSIGNED draft. Never enrolls or attests reset."""
import argparse
import json
import re
import ikea_gate as g


def prepare(name):
    g.need(re.fullmatch(r'episode-\d{4,}', name), 'exact episode-NNNN required')
    ep=g.CAMPAIGN/name
    review=g.read(ep/'success_review.json')
    result=g.read(ep/'result.json')
    scene=g.read(ep/'video/scene_setup.json')
    manifest=g.read(ep/'video/render_manifest.json')
    g.need(review['audited_task_success'] is True and review['actor_access'] is False,
           'existing host success review required')
    g.need(result['success'] is True and result['native_outcome']=='success'
           and result['stop_reason']=='native_success' and result['error'] is None
           and result['skill_updated'] is True, 'completed host success required')
    reset=scene['reset_provenance']
    g.need(reset==review['reset'] and reset['seed']==int(name.split('-')[-1]), 'host reset binding mismatch')
    binding=g.frame_binding()
    revision=g.audit_frame_revision(scene,manifest['runtime_source_sha256'],binding)
    g.need(review['physics_revision']==scene['frame_collision_override']
           and review['unmodified_native_benchmark'] is False, 'host physics review mismatch')
    count=result['codex_turns']
    g.need(type(count) is int and 0<count<=1000, 'invalid turn count')
    names=set((*g.REQUIRED, 'success_review.json', 'account_route_verified.json',
               *(f'turn_{i:03d}.json' for i in range(1,count+1)), *review['evidence_sha256']))
    hashes={n:g.digest(g.inside(ep,n)) for n in sorted(names)}
    for n,h in review['evidence_sha256'].items():g.need(hashes[n]==h,'changed host-reviewed evidence: '+n)
    for i in range(1,count+1):
        turn=g.read(ep/f'turn_{i:03d}.json')
        g.need(turn['status']=='completed' and turn.get('error') is None,'incomplete reasoning turn')
    g.need(result['starting_skill_sha256']==hashes['SKILL.md'],'starting skill mismatch')
    stats=g.audit_trace(ep/'video/robot_trace.jsonl',manifest['initial_render_state'],result['sim_s'])
    g.need(stats==review['recording_audit'] and stats['commands']==result['actions'],'host trace review mismatch')
    video=g.video_probe(ep/'video/episode.mp4');expected=(stats['ticks']+1)//2
    g.need(int(video['nb_frames'])==expected and video['r_frame_rate']=='25/1'
           and abs(float(video['duration'])-expected/25)<.041,'incomplete original video')
    for n,h in hashes.items():g.need(g.digest(g.inside(ep,n))==h,'evidence changed during preflight')
    draft={'schema':2,'data_kind':'unpopulated_template','host_reviewer_thread':g.THREAD,
           'contract':g.CONTRACT,'mode':'formal_direct_simulation','episode':str(ep),
           'reset':reset,'provenance_review':{**dict.fromkeys(g.COMMON_PROVENANCE,False),
                    'original_physics':False,'reviewed_physics_revision':False},
           'physics_revision':binding,'runtime_source_sha256':manifest['runtime_source_sha256'],
           'host_evidence':[{'path':str((ep/n).relative_to(g.ROOT)),'sha256':hashes[n]}
                            for n in ['success_review.json','video/scene_setup.json']],
           'evidence_sha256':hashes}
    folder=g.OUT/'frame-override-validation'
    path=folder/(name+'.UNSIGNED.json')
    if path.exists():g.need(g.read(path)==draft,'existing draft differs; preserve it and use a reviewed new version')
    else:g.atomic_json(path,draft)
    outcome={'episode':name,'source_host_review_sha256':hashes['success_review.json'],
        'candidate_evidence_verified':True,'host_receipt_issued_by_maintainer':False,
        'enrolled':False,'success_credit_added':0,'unsigned_draft':str(path),
        'recording_audit':stats,'video':video,'physics_revision':revision,
        'reset_id_from_existing_scene':reset['reset_id'],'launch_from_existing_scene':reset['launch'],
        'limitation':'Only original supervisor can attest provenance and enroll. This preflight never signs a host receipt.',
        'model_calls':0,'simulations':0,'api_or_accounting_read':False}
    g.atomic_json(folder/(name+'.preflight.json'),outcome)
    return outcome


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--episode',required=True)
    print(json.dumps(prepare(p.parse_args().episode),ensure_ascii=False,indent=2))
