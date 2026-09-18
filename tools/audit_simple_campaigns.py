"""Incremental status ledger; zero-action records and diagnostics earn no credit."""
import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

# Keep the long-standing direct script invocation usable without PYTHONPATH.
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def termination_class(result):
    if result is None:return 'running'
    if result.get('error'):return 'infrastructure_interruption'
    if result.get('goal_scope')=='curriculum_stage':
        return 'curriculum_success' if result.get('curriculum_success') else 'curriculum_learning_stop'
    if result.get('success') and result.get('native_outcome')=='success':return 'native_success'
    if result.get('backend_stop_reason'):return 'runtime_safety_stop'
    reason=result.get('stop_reason')
    if reason in ('progress_stall','progress_order_violation','progress_actor_stall'):
        return 'progress_supervised_learning_stop'
    if reason=='policy_declared_stall':return 'policy_early_stop'
    if reason=='episode_step_budget':return 'budget_truncation'
    if reason=='policy_safety_stop':return 'policy_safety_stop_requires_review'
    if result.get('native_outcome')=='failure':return 'native_failure_unspecified'
    return 'unfinished_terminal_record'


def turn_completeness(episode, result):
    """Validate host terminal receipts; never expose them as actor observations."""
    paths = {p.name: p for p in episode.glob('turn_*.json') if p.is_file()}
    contract = (result or {}).get('turn_record_contract')
    try:
        records = {name: json.loads(p.read_text()) for name, p in paths.items()}
        if any(not isinstance(row, dict) for row in records.values()):
            raise ValueError('non-object terminal')
        numbered = (result or {}).get('codex_turns')
        if contract is None:
            if any('_rsi_terminal' in row for row in records.values()):
                raise ValueError('new receipts without result contract')
            # Old no-recovery receipts retain their previous interpretation. Where
            # the historical count exists, do not accept a known numbering gap.
            if type(numbered) is int and numbered > 0:
                if set(records) != {f'turn_{i:03d}.json' for i in range(1, numbered+1)}:
                    raise ValueError('legacy numbering gap')
                last = records[f'turn_{numbered:03d}.json']
            else:
                last = records[sorted(records)[-1]] if records else {}
            return bool(last.get('status') == 'completed'), 'legacy_no_identity_proof'
        if contract == 'api-terminal-sequence-v1':
            if (records or type(numbered) is not int or numbered != 0
                    or result.get('codex_thread_id') is not None
                    or result.get('codex_turn_ids') != []):
                raise ValueError('API-first cannot invent Codex terminal identities')
            from rsi.actor_terminal_audit import complete_api_chain
            complete_api_chain(result,None)
            return True, 'complete_api_terminal_sequence'
        if contract != 'codex-terminal-sequence-v1':
            raise ValueError('unsupported terminal contract')
        identities = result.get('codex_turn_ids')
        thread = result.get('codex_thread_id')
        if (type(numbered) is not int or numbered < 1 or not isinstance(identities, list)
                or len(identities) != numbered or not isinstance(thread, str) or not thread
                or any(not isinstance(i, str) or not i for i in identities)
                or len(set(identities)) != numbered):
            raise ValueError('invalid ACK identity sequence')
        if set(records) != {f'turn_{i:03d}.json' for i in range(1, numbered+1)}:
            raise ValueError('missing or extra terminal number')
        if result.get('api_continuation') and records[f'turn_{numbered:03d}.json'].get('status')!='failed':
            raise ValueError('API handoff requires a preserved failed Codex terminal')
        recovered_reset = None
        for i, identity in enumerate(identities, 1):
            row = records[f'turn_{i:03d}.json']
            meta = row.get('_rsi_terminal')
            if (not isinstance(meta, dict) or meta.get('contract') != contract
                    or type(meta.get('sequence')) is not int or meta['sequence'] != i
                    or meta.get('thread_id') != thread or row.get('id') != identity):
                raise ValueError('terminal identity/order mismatch')
            reset_id = meta.get('reset_id')
            if recovered_reset is not None and reset_id != recovered_reset:
                raise ValueError('reset changed after recovered failure')
            if row.get('status') == 'completed':
                if row.get('error') or meta.get('recovery_reason') is not None:
                    raise ValueError('completed terminal has error/recovery label')
            elif (i == numbered and result.get('api_continuation')):
                from rsi.actor_terminal_audit import complete_api_chain
                complete_api_chain(result,row)
            elif (row.get('status') == 'failed' and i < numbered and row.get('error')
                    and meta.get('recovery_reason') == 'no_new_physical_progress'):
                from rsi.actor_terminal_audit import diagnostic_resume
                diagnostic_resume(episode,i,row); recovered_reset=reset_id
            elif (row.get('status') == 'failed' and i < numbered and row.get('error')
                    and meta.get('recovery_reason') == 'confirmed_closed_network_turn'
                    and isinstance(reset_id, str) and reset_id):
                recovered_reset = reset_id
            else:
                raise ValueError('unrecovered or incomplete terminal')
        return True, 'complete_terminal_sequence'
    except (OSError, ValueError, TypeError, KeyError) as error:
        return False, 'invalid_terminal_sequence: '+str(error)


def episode_status(episode):
    result_path=episode/'result.json'
    result=json.loads(result_path.read_text()) if result_path.is_file() else None
    interruption_path=episode/'infrastructure_review.json'
    interruption=json.loads(interruption_path.read_text()) if interruption_path.exists() else {}
    interrupted=bool(result is None and interruption.get('termination_class')=='infrastructure_interruption')
    history_path=episode/'rollout/history.jsonl'
    history=[json.loads(s) for s in history_path.read_text().splitlines()] if history_path.exists() else []
    actions=sum(r.get('tool')=='scalebfm_act' for r in history)
    if result is not None: actions=result.get('actions',actions)
    full_turn, turn_integrity = turn_completeness(episode, result)
    revision=bool(result and result.get('skill_updated'))
    host_success=bool(result and result.get('success') and result.get('native_outcome')=='success'
                        and actions>0 and full_turn and revision and not result.get('error'))
    curriculum_only=(result or {}).get('goal_scope')=='curriculum_stage'
    curriculum_success=bool(result and result.get('curriculum_success') and actions>0 and full_turn and revision and not result.get('error'))
    host_success=host_success and not curriculum_only
    review_path=episode/'success_review.json'
    review=json.loads(review_path.read_text()) if review_path.exists() else {}
    exposure_path=episode/'human_feedback_review.json'
    exposure=json.loads(exposure_path.read_text()) if exposure_path.exists() else {}
    scene_path=episode/'video/scene_setup.json'
    scene=json.loads(scene_path.read_text()) if scene_path.exists() else {}
    old_boot=scene.get('reset_provenance',{}).get('launch',{}).get('boot_id')
    boot_path=Path('/proc/sys/kernel/random/boot_id')
    rebooted=bool(result is None and old_boot and boot_path.exists()
                  and old_boot != boot_path.read_text().strip())
    interrupted=interrupted or rebooted
    contract=((result or {}).get('completion_contract') or scene.get('completion_contract') or {}).get('id',
        'door-push-contact30deg-dwell1s-standing' if episode.parent.name=='door-campaign'
        else 'native_simple_criterion')
    return {'episode_id':episode.name,'state':'interrupted' if interrupted else 'finished' if result is not None else 'running',
        'physical_attempt':actions>0,'actions':actions,'full_turn_completed':full_turn,
        'turn_record_integrity':turn_integrity,
        'skill_updated':revision,'host_success_complete':host_success,
        'completion_contract':contract,
        'goal_scope':(result or {}).get('goal_scope','full_task'),
        'curriculum_level':(result or {}).get('curriculum_level'),
        'curriculum_host_success':curriculum_success,
        'task_audit_status':('passed' if review.get('audited_task_success') is True
            else 'rejected' if review.get('audited_task_success') is False else 'unknown'),
        'audited_task_success':host_success and review.get('audited_task_success') is True,
        'native_outcome':result.get('native_outcome') if result else (history[-1].get('native_outcome') if history else 'not_started'),
        'error':result.get('error') if result else (
            interruption.get('reason') or 'Recorded reset belongs to a previous host boot'
            if interrupted else None),
        'termination_class':('infrastructure_interruption' if interrupted else 'native_success_rejected_by_task_audit'
            if host_success and review.get('audited_task_success') is False
            else 'verified_variant_success' if host_success and contract!='native_simple_criterion'
            else termination_class(result)),
        'human_feedback_used':bool((result and result.get('human_feedback_used',False))
                                   or exposure.get('human_feedback_used',False)),
        'frame_collision_revision':scene.get('frame_collision_override',{}).get('id','original'),
        'reset_id':scene.get('reset_provenance',{}).get('reset_id'),
        'reset_recorded_utc':scene.get('reset_provenance',{}).get('recorded_utc'),
        'sim_s':result.get('sim_s') if result else None,
        'video':str(episode/'video/episode.mp4'),'video_exists':(episode/'video/episode.mp4').is_file(),
        'result_path':str(result_path) if result else None,
        'failure_review_exists':(episode/'failure_review.json').is_file() or (episode/'infrastructure_review.json').is_file()}


def memory_success_review(campaign, completion_contract):
    """Host-only live projection; the supervisor's success_review.json is authoritative.

    Re-read on each memory request, including reviews published after skill_update.
    No copied audit ledger, actor file access, or historical experience rewrite.
    """
    campaign = Path(campaign)
    def lookup(episode_id):
        if (not isinstance(episode_id, str) or not episode_id.startswith('episode-')
                or not episode_id.removeprefix('episode-').isdigit()):
            return {}
        try:
            status = episode_status(campaign / episode_id)
        except (FileNotFoundError, json.JSONDecodeError):
            # A supervisor may still be publishing its review; do not pin on a
            # partial/missing read and do not cache a previous approval.
            return {}
        return {'task_audit_status': status['task_audit_status'],
                'completion_contract_matches': (isinstance(completion_contract, str)
                    and bool(completion_contract) and status['completion_contract'] == completion_contract),
                'audited_task_success': status['audited_task_success']}
    return lookup


def focused_cohorts(root, campaigns):
    """Keep historical successes separate from newly started focus evaluations."""
    path=root/'six-task-focus/supervisor-ack.json'
    if not path.exists():return None
    focus=json.loads(path.read_text())
    protocol_path=root/'six-task-focus/five-stable-ack.json'
    protocol=json.loads(protocol_path.read_text()) if protocol_path.exists() else None
    boundary=datetime.datetime.fromisoformat(focus['effective_utc'])
    inflight={(x['campaign'],x['episode']) for x in focus['inflight']}
    mapping=focus.get('campaign_families',{})
    families={name:[] for name in focus['scope']}
    for campaign in campaigns:
        name=Path(campaign['campaign']).name
        if name not in mapping:continue
        row={'campaign':name,'cohorts':{}}
        for e in campaign['episodes']:
            recorded=e.get('reset_recorded_utc')
            try:
                started=datetime.datetime.fromisoformat(recorded) if recorded else None
                cohort=('post_focus' if started and started>=boundary else
                        'transition_inflight' if (name,e['episode_id']) in inflight else
                        'historical' if started else 'unknown_reset_time')
            except (ValueError,TypeError):cohort='unknown_reset_time'
            bucket=row['cohorts'].setdefault(cohort,{'physical_attempts':0,'audited_successes':0,'episodes':[]})
            bucket['physical_attempts']+=int(e['physical_attempt'])
            bucket['audited_successes']+=int(e['audited_task_success'])
            bucket['episodes'].append(e['episode_id'])
        families[mapping[name]].append(row)
    return {'source':focus['source'],'effective_utc':focus['effective_utc'],
            'families':families,'exact_entries':focus.get('mapping',{}),'protocol':protocol,
            'protocol_progress':frozen_protocol_progress(root,focus),
            'grasp_entry':focus.get('grasp_entry_status','control adaptation pending'),
            'outside_focus':'Historical records retained; no new trials authorized in this phase.',
            'scores':'Each campaign/variant and start cohort stays separate; historical success is not a new evaluation.'}


def frozen_protocol_progress(root, focus):
    """Only registered, bound host audits contribute to the frozen protocol."""
    from rsi.frozen_skill import stability_count
    result={}
    for campaign, family in focus.get('campaign_families',{}).items():
        candidates=[]
        for path in sorted((root/campaign/'fixed-candidates').glob('*/manifest.json')):
            directory=path.parent
            if (directory/'superseded-before-launch.json').exists():continue
            manifest=json.loads(path.read_text())
            registrations=[json.loads(p.read_text()) for p in sorted((directory/'registrations').glob('*.json'))]
            outcomes={p.stem:json.loads(p.read_text()) for p in (directory/'outcomes').glob('*.json')}
            stable=[outcomes[r['registration_id']]['audit'] for r in registrations
                    if r['phase']=='stability' and r['registration_id'] in outcomes]
            evaluation=[outcomes[r['registration_id']]['audit'] for r in registrations
                        if r['phase']=='evaluation' and r['registration_id'] in outcomes]
            count=stability_count(manifest['task_id'],manifest['candidate_sha256'],stable)
            unresolved=[r['episode'] for r in registrations if r['registration_id'] not in outcomes]
            admission_path=directory/'admission-audit.json'
            admission=json.loads(admission_path.read_text()) if admission_path.exists() else {}
            candidates.append({'candidate_sha256':manifest['candidate_sha256'],
                'path':str(directory),'phase':'evaluation' if any(r['phase']=='evaluation' for r in registrations) else 'stability',
                'admission_audit':admission,
                **count,'pending_registered_episodes':unresolved,
                'evaluation_successes':sum(r['audited_task_success'] for r in evaluation),
                'evaluation_completed':len(evaluation),'evaluation_planned':10,
                'eligible_for_evaluation':count['eligible_for_evaluation'] and not unresolved and admission.get('stability_credit_allowed',True)})
        result[family]={'task_id':focus.get('mapping',{}).get(family),
                        'candidates':candidates,'current':candidates[-1] if candidates else None}
    return result


def write_progress(root, report):
    """Refresh the existing stable supervisor entry from the same audited ledger."""
    focus=report.get('current_focus')
    goal=('当前仅原README六项精确入口：XMovePickTeleop、BendPickMP、HandoverTeleop、LocomotionPickBetweenTablesTeleop、TabletopGraspMP、XMoveBendPickTeleop。MP已真实接入，连续控制可靠性待修复；IKEA/地面搬运暂停。旧91库存保留但不扩张。'
          if focus else '目标：推门10次独立审计成功；全部可用操作任务各至少1次。已完成桌面抓块10次不重做。')
    lines=['# SIMPLE 进展', '', '更新时间：'+report['updated_utc'],goal,
        '后端：MuJoCo，推理期间物理暂停，非 RTC；推门是明确门框碰撞修复的 push-open 变体。', '']
    if focus:
        if focus.get('protocol'):
            lines += ['最新验收：每项固定完整候选连续5次独立审计成功，再冻结同一策略做L0/L1/L2各10回合，共180回合。等级、目标布局、实际Isaac输入及原生预算对齐前不计榜单；未运行不显示0%。旧在途不倒签稳定性，历史累计不等于固定候选五连胜。',
                      '全目标：完整、对齐并独立审计的180回合至少155次成功，严格超过Ψ0基准154/180；五稳只是准入，不是总目标完成。各候选不得择优拼接。唯一goal_guard验收入口由原接续负责人维护。',
                      '冻结状态：'+focus['protocol']['freeze_loading_status']]
            for family,row in focus.get('protocol_progress',{}).items():
                current=row['current']
                if current:
                    eval_text=(f"{current['evaluation_successes']}/{current['evaluation_completed']}已完成"
                               if current['evaluation_completed'] else '未运行')
                    lines.append(f"{family} 固定候选 {current['candidate_sha256'][:12]}：阶段{current['phase']}；连续成功{current['consecutive_successes']}/5；旧候选评测{eval_text}（历史登记10，不能代替最新三级协议）；登记未入冻结计分{len(current['pending_registered_episodes'])}回合。")
                    if current['admission_audit'].get('stability_credit_allowed') is False:
                        lines.append('  本候选准入审计否决（保留原审计原文）：'+current['admission_audit']['reason']+'；该候选稳定性不给分，回合实际状态见下方账本。')
                else:lines.append(f'{family}：适配/学习，尚未登记固定候选成功（0/5）；冻结评测未启动。')
        lines += ['六类生效：'+focus['effective_utc']+'。以下总审计数含历史；新测评、切换时在途和历史基线分别计数，变体不合并。']
        for family,entries in focus['families'].items():
            for entry in entries:
                counts=entry['cohorts']
                line='；'.join(f"{label} {counts.get(key,{}).get('audited_successes',0)}成功/{counts.get(key,{}).get('physical_attempts',0)}尝试"
                              for key,label in [('historical','历史'),('transition_inflight','切换在途'),('post_focus','生效后新回合')])
                lines.append(f"{family} / {entry['campaign']}：{line}。")
            if not entries:lines.append(f"{family}：精确入口控制适配/验收准备中，未登记新回合成功。")
        lines.append('')
    for campaign in report['campaigns']:
        if not campaign['episodes']: continue
        latest=campaign['episodes'][-1]; folder=Path(campaign['campaign']); ep=folder/latest['episode_id']
        trace=ep/'video/robot_trace.jsonl'
        stamp=(datetime.datetime.fromtimestamp(trace.stat().st_mtime, datetime.timezone.utc).isoformat()
               if trace.exists() else '尚无物理日志')
        phase=latest['state']
        if phase=='running':
            requests=sorted((ep/'agent/rpc_calls').glob('*_request.json'))
            phase='等待模型/工具；物理暂停'
            if requests:
                request=json.loads(requests[-1].read_text())
                reply=requests[-1].with_name(requests[-1].name.replace('_request','_result'))
                if not reply.exists() and request.get('tool') in ('scalebfm_act','loco_start'):
                    phase='物理执行/初始化中（本次快照）'
        lines.append(f"- {folder.name}：审计成功 {campaign['audited_task_successes']}/{campaign['required_successes']}；"
                     f"{latest['episode_id']}，{phase}，{latest['actions']}动作；终态分类 {latest['termination_class']}。最近物理日志 {stamp}。")
        if campaign['human_assisted_audited_successes'] or latest['human_feedback_used']:
            lines.append(f"  成绩分层：自主 {campaign['autonomous_audited_successes']}；语义反馈辅助 {campaign['human_assisted_audited_successes']}。")
        budget=ep/'policy_instruction_budget.json'
        if budget.exists():
            b=json.loads(budget.read_text());s=b['combined_size']
            lines.append(f"  已加载入口：{s['words']} words / {s['characters']} chars / {s['non_whitespace']}非空白；组合SHA {b['combined_sha256']}。")
        complete=next((e for e in reversed(campaign['episodes']) if e['state']=='finished' and e['video_exists']),None)
        if complete:lines.append('  最近完整录像：'+complete['video']+'（历史物理录像，非直播）。')
    lines += ['', '重启恢复：door15旧boot中断，61动作、无完整turn/result/skill_update；MP4缺moov保留，不冒称可播放。证据 recovery-20260916/door15-interruption.json。',
        '框架：ARCH长度与MEMORY-PRIORITY、相机render-frustum-v1已在门16和水龙头8完成真实调用链及受限skill_update验证，证据instruction-cap-integration/status.json。NT逐turn记录/审计兼容候选已发布，63项针对检查通过，门19完整单turn及修订真实验证；尚未发生真实网络恢复。证据nt-audit-integration-20260916/status.json；共同变更不能作单因收益归因。',
        '下一步：完整等待各活动回合，逐轮审查；后续仅按最新授权六类安排，不扩张旧库存，不重复凑推门数。推门历史10次门槛凭door-campaign/ten-success-milestone.json核验。苹果H001004先张手包络后闭合。权限修复首次生效门18/垃圾桶1/办公椅1，实际workspaceWrite/on-request+auto_review已随真实动作核验；旧在途不热改，证据recovery-20260916/permission-physical-route-verification.json。',
        '失败分层：预算截断、系统中断、提前终止均不凑三次自主物理失败求助。入口/标定/检索并变不能作单变量因果结论。',
        '来源：各任务memory/versions、公开rollout、独立host审计；中央统一发布skill，实际加载版本和回执分开核验。91入口库存保留但本阶段只调度六项，预检和未尝试不计成功。',
        '范围：本主管仅SIMPLE；IKEA/地面搬运按用户暂停，由原owner保留收尾证据。视频页 http://127.0.0.1:8765/ 读取既有证据。', '']
    stability = root/'robot-stability-integration-20260916/status.json'
    if stability.exists():
        state = json.loads(stability.read_text())
        lines += ['机器人本体观测：ROBOT-STABILITY-OBS-V1 状态 '+state['status']+
                  '；首次新回合 '+state['first_physical_boundary']+
                  '。仅新增命名骨盆测量/动作内采样摘要，未改控制或安全阈值；单因任务收益未隔离验证。证据 '+str(stability)+ '。', '']
    (root/'PROGRESS.md').write_text('\n'.join(lines))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('artifacts/R019'))
    args=p.parse_args(); campaigns=[]
    mapping={'door-campaign':'SIMPLE asset003 push-open variant',
             'bendpickmp-campaign':'simple/G1WholebodyBendPickMP-v0',
             'tabletopgraspmp-campaign':'simple/G1WholebodyTabletopGraspMP-v0',
             'handover-campaign':'simple/G1WholebodyHandoverTeleop-v0',
             'mobiletables-campaign':'simple/G1WholebodyLocomotionPickBetweenTablesTeleop-v0',
             'mobilecheezit-campaign':'simple/G1WholebodyMobilePickAndPlaceCheezitTeleop-v0',
             'closedoor-campaign':'simple/G1WholebodyCloseDoorTeleop-v0',
             'apple-campaign':'simple/G1WholebodyPickAndPlaceAppleTeleop-v0',
             'faucet-campaign':'simple/G1WholebodyOpenFaucetTeleop-v0',
             'boxplace-campaign':'simple/G1WholebodyBendPickAndPlaceTeleop-v0',
             'bendpick-campaign':'simple/G1WholebodyBendPickTeleop-v0',
             'bendpicksim-campaign':'simple/G1WholebodyBendPickSimToRealTeleop-v0',
             'oven-campaign':'simple/G1WholebodyOpenOvenTeleop-v0',
             'trashcan-campaign':'simple/G1WholebodyOpenTrashCanTeleop-v0',
             'chair-campaign':'simple/G1WholebodyPushOfficeChairTeleop-v0',
             'xmovebendpick-campaign':'simple/G1WholebodyXMoveBendPickTeleop-v0',
             'xmovepick-campaign':'simple/G1WholebodyXMovePickTeleop-v0',
             'xmovepicksim-campaign':'simple/G1WholebodyXMovePickSimToRealTeleop-v0'}
    for folder in sorted(args.root.glob('*-campaign')):
        episodes=[episode_status(e) for e in sorted(folder.glob('episode-*')) if e.is_dir()]
        campaigns.append({'campaign':str(folder),'task':mapping.get(folder.name,'unmapped'),
            'required_successes':10 if folder.name=='door-campaign' else 1,
            'physical_attempts':sum(e['physical_attempt'] for e in episodes),
            'finished_physical_attempts':sum(e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'interrupted_physical_attempts':sum(e['physical_attempt'] and e['state']=='interrupted' for e in episodes),
            'zero_action_finished_records':sum(not e['physical_attempt'] and e['state']=='finished' for e in episodes),
            'complete_host_successes':sum(e['host_success_complete'] for e in episodes),
            'complete_native_evaluator_successes':sum(e['host_success_complete'] and
                e['completion_contract']=='native_simple_criterion' for e in episodes),
            'audited_task_successes':sum(e['audited_task_success'] for e in episodes),'episodes':episodes})
        campaigns[-1]['termination_counts']=dict(Counter(e['termination_class'] for e in episodes))
        campaigns[-1]['autonomous_audited_successes']=sum(
            e['audited_task_success'] and not e['human_feedback_used'] for e in episodes)
        campaigns[-1]['human_assisted_audited_successes']=sum(
            e['audited_task_success'] and e['human_feedback_used'] for e in episodes)
        campaigns[-1]['audited_successes_by_contract']=dict(Counter(
            e['completion_contract'] for e in episodes if e['audited_task_success']))
    report={'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'all_goals_complete':False,'unresolved_scope':'All 91 registered entries remain in task-inventory and task-compatibility reports; unaudited or unattempted tasks are not treated as complete.',
        'diagnostics_and_replays_counted':False,'campaigns':campaigns}
    report['current_focus']=focused_cohorts(args.root,campaigns)
    if report['current_focus']:
        report['unresolved_scope']='Exact six README benchmark entries only. MP adapter has executed real actor actions; reliable multi-step control and loaded travel remain unresolved. Handover3 passed complete learning audit; fixed-candidate stability and aligned formal evaluation remain pending. Related variants are transfer evidence only. Old91-entry inventory retained, expansion paused by user.'
    (args.root/'campaign_audit.json').write_text(json.dumps(report,indent=2))
    inventory_path=args.root/'task-evaluation-status.json'
    if inventory_path.exists():
        inventory=json.loads(inventory_path.read_text())
        by_task={c['task']:c for c in campaigns}
        for entry in inventory['entries']:
            campaign=by_task.get(entry['env_id'])
            if campaign is None or not campaign['episodes']:continue
            count=campaign['audited_task_successes']
            active=any(e['state']=='running' for e in campaign['episodes'])
            entry.update(audited_task_successes=count,
                evaluation_status='verified' if count else 'in_progress' if active else 'attempted_unverified',
                reason='Current host-audited campaign ledger; raw outcome alone earns no task credit.',
                campaign_evidence=campaign['campaign'])
        door=by_task.get('SIMPLE asset003 push-open variant')
        if door:
            variant=inventory['separate_user_variant']
            variant['audited_successes']=door['audited_task_successes']
            variant.pop('audited_task_successes',None)  # One canonical count field.
        inventory['updated_utc']=report['updated_utc']
        inventory['status_counts']=dict(Counter(e['evaluation_status'] for e in inventory['entries']))
        inventory_path.write_text(json.dumps(inventory,indent=2)+'\n')
    write_progress(args.root, report)
    for c in campaigns:print(json.dumps({k:v for k,v in c.items() if k!='episodes'}))


if __name__=='__main__':main()
