"""Incremental status ledger; zero-action records and diagnostics earn no credit."""
import argparse
import datetime
import json
from collections import Counter
from pathlib import Path


def termination_class(result):
    if result is None:return 'running'
    if result.get('error'):return 'infrastructure_interruption'
    if result.get('success') and result.get('native_outcome')=='success':return 'native_success'
    if result.get('backend_stop_reason'):return 'runtime_safety_stop'
    reason=result.get('stop_reason')
    if reason=='policy_declared_stall':return 'policy_early_stop'
    if reason=='episode_step_budget':return 'budget_truncation'
    if reason=='policy_safety_stop':return 'policy_safety_stop_requires_review'
    if result.get('native_outcome')=='failure':return 'native_failure_unspecified'
    return 'unfinished_terminal_record'


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
    turns=[json.loads(p.read_text()) for p in sorted(episode.glob('turn_*.json')) if p.is_file()]
    full_turn=bool(turns and turns[-1].get('status')=='completed')
    revision=bool(result and result.get('skill_updated'))
    host_success=bool(result and result.get('success') and result.get('native_outcome')=='success'
                        and actions>0 and full_turn and revision and not result.get('error'))
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
        'skill_updated':revision,'host_success_complete':host_success,
        'completion_contract':contract,
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


def write_progress(root, report):
    """Refresh the existing stable supervisor entry from the same audited ledger."""
    lines=['# SIMPLE 进展', '', '更新时间：'+report['updated_utc'],
        '目标：推门10次独立审计成功；全部可用操作任务各至少1次。已完成桌面抓块10次不重做。',
        '后端：MuJoCo，推理期间物理暂停，非 RTC；推门是明确门框碰撞修复的 push-open 变体。', '']
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
        budget=ep/'policy_instruction_budget.json'
        if budget.exists():
            b=json.loads(budget.read_text());s=b['combined_size']
            lines.append(f"  已加载入口：{s['words']} words / {s['characters']} chars / {s['non_whitespace']}非空白；组合SHA {b['combined_sha256']}。")
        complete=next((e for e in reversed(campaign['episodes']) if e['state']=='finished' and e['video_exists']),None)
        if complete:lines.append('  最近完整录像：'+complete['video']+'（历史物理录像，非直播）。')
    lines += ['', '重启恢复：door15旧boot中断，61动作、无完整turn/result/skill_update；MP4缺moov保留，不冒称可播放。证据 recovery-20260916/door15-interruption.json。',
        '框架：ARCH长度与MEMORY-PRIORITY、相机render-frustum-v1已在门16和水龙头8完成真实调用链及受限skill_update验证，证据instruction-cap-integration/status.json；不能据此作单因收益归因。NT仅采用无期限turn/start ACK及不确定提交锁；自动网络续接与审计衔接待验证。',
        '下一步：完整等待各活动回合，逐轮审查；门以10次为目标。苹果H001004先张手包络后闭合；最低次数已验收任务保留经验，空位推进其它可用入口。权限修复首次生效门18/垃圾桶1/办公椅1，实际workspaceWrite/on-request+auto_review已随真实动作核验；旧在途不热改，证据recovery-20260916/permission-physical-route-verification.json。',
        '失败分层：预算截断、系统中断、提前终止均不凑三次自主物理失败求助。入口/标定/检索并变不能作单变量因果结论。',
        '来源：各任务memory/versions、公开rollout、独立host审计；共享core未晋升。91入口库存保留，预检和未尝试不计成功。',
        '范围：本主管仅SIMPLE；IKEA/API搬运归各自owner。视频页 http://127.0.0.1:8765/ 读取既有证据。', '']
    (root/'PROGRESS.md').write_text('\n'.join(lines))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('artifacts/R019'))
    args=p.parse_args(); campaigns=[]
    mapping={'door-campaign':'SIMPLE asset003 push-open variant',
             'apple-campaign':'simple/G1WholebodyPickAndPlaceAppleTeleop-v0',
             'faucet-campaign':'simple/G1WholebodyOpenFaucetTeleop-v0',
             'boxplace-campaign':'simple/G1WholebodyBendPickAndPlaceTeleop-v0',
             'bendpick-campaign':'simple/G1WholebodyBendPickTeleop-v0',
             'oven-campaign':'simple/G1WholebodyOpenOvenTeleop-v0',
             'trashcan-campaign':'simple/G1WholebodyOpenTrashCanTeleop-v0',
             'chair-campaign':'simple/G1WholebodyPushOfficeChairTeleop-v0'}
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
