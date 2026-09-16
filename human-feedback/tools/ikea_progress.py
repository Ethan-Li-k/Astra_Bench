"""Public IKEA projection. Reuses existing containment, signatures and media handler."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from api_progress import APIProgress, ROOT, number, signature

IKEA = ROOT / 'ikea'
PHASES = {
    'source_physics_confirmed_scene_alignment': '源资产物理核对完成；派生场景对齐准备',
    'door_physics_validation': '派生门编译成功；物理校验待完成',
    'asset_inventory': '资产与可动部件核对',
    'scene_build': '派生场景构建',
    'door_reset_validation': '闭门重置校验',
    'door_contact_diagnostic': '门接触诊断',
    'policy_preparation': '策略回合准备',
    'policy_learning': '真实策略尝试',
    'bedroom_door': '卧室门探索',
    'apple': '苹果抓取探索',
    'fridge': '冰箱开启探索',
    'placement': '放入冰箱探索',
}
STATES = {
    'engineering': '工程准备', 'continue': '工程等待继续',
    'inference_waiting': '等待完整推理', 'inference_waiting_no_deadline': '等待完整推理',
    'action_executing': '动作执行', 'system_interrupted': '系统中断',
    'blocked': '等待条件满足', 'ended': '回合已结束', 'complete': '工程记录已结束',
}
TERMINALS = {
    'host_audited_success': '来源报告审计成功',
    'physical_failure': '真实物理失败',
    'budget_limited_incomplete': '预算截断 · 未完成（不是物理失败）',
    'safety_stop': '安全停止',
    'agent_stopped_incomplete': '主动提前结束 · 未完成',
    'infrastructure_error': '系统 / 基础设施中断',
    'host_restart_infrastructure_interruption': '主机重启 · 系统中断',
}
CATEGORIES = {'diagnostic': '诊断', 'learning': '学习',
              'audited_success': '审计成功', 'human_assisted': '人工辅助'}
TASKS = {'bedroom_door': '卧室门', 'apple': '苹果', 'fridge': '冰箱', 'placement': '放入'}
VARIANTS = {'fbx-derived-no-latch-v1': 'FBX-derived no-latch v1',
            'fbx-door-west-no-latch-v1': 'FBX-derived no-latch v1'}
ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}')


def timestamp(value):
    if type(value) in (int, float):
        return number(value)
    if not isinstance(value, str) or len(value) > 48:
        return None
    try:
        d = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return number(d.timestamp()) if d.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def count(value):
    return value if type(value) is int and value >= 0 else None


def boot_info():
    try:
        boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        btime = next(x.split()[1] for x in Path('/proc/stat').read_text().splitlines() if x.startswith('btime '))
        return boot_id, float(btime)
    except (OSError, StopIteration, ValueError):
        return None, None


def last_known_runtime(data, boot_started_at):
    """Annotate old API payload without changing its source/evidence or terminal classification."""
    d = dict(data)
    previous = number(d.get('updated_at_unix'))
    interrupted = bool(boot_started_at and previous is not None and previous < boot_started_at and not d.get('terminal_kind'))
    d['runtime_confirmed'] = False
    d['host_restart_after_update'] = interrupted
    d['state_label'] = ('主机重启前最后已知：' if interrupted else '最近记录（非实时进程确认）：') + d.get('state_label', '未知')
    d['runtime_notice'] = ('本机重启已中断旧进程；尚无该回合恢复后的公开进展。' if interrupted
                           else '仅显示来源最近记录；页面获取和心跳不证明任务正在运行。')
    return d


class IKEAProgress(APIProgress):
    def __init__(self, root=IKEA, boot=None):
        super().__init__(root)
        self.boot_id, self.boot_started_at = boot if boot is not None else boot_info()

    def read(self, path):
        data, ref = super().read(path)
        ref['source'] = 'ikea/' + str(path.relative_to(self.root))
        return data, ref

    def optional(self, relative, sources):
        try:
            d, ref = self.read(self.root / relative)
            if isinstance(d, dict):
                sources.append(ref)
                return d
        except (OSError, ValueError, TypeError):
            pass
        return {}

    def _snapshot(self):
        sources = []
        public = self.optional('web-progress.json', sources)
        legacy = self.optional('state.json', sources)
        heartbeat = self.optional('heartbeat.json', sources)
        incident = self.optional('recovery-20260916/incident.json', sources)
        ack = self.optional('recovery-ack.json', sources)
        if not ack:
            ack = self.optional('recovery-20260916/recovery-ack.json', sources)
        fresh_schema = public.get('schema_version', public.get('schema')) == 1
        source = public if fresh_schema else legacy
        updated = timestamp(source.get('updated_at', source.get('last_actual_progress_at')))
        progress = timestamp(source.get('last_progress_at', source.get('last_actual_progress_at'))) if fresh_schema else timestamp(source.get('updated_at'))
        phase = source.get('phase')
        phase = phase if isinstance(phase, str) and phase in PHASES else 'unknown'
        state = source.get('state')
        if state is None and source.get('execution_kind') == 'engineering':
            state = 'engineering'
        state = state if isinstance(state, str) and state in STATES else 'unknown'
        interrupted = bool(self.boot_started_at and updated is not None and updated < self.boot_started_at)
        live = source.get('live_evidence')
        live = live if isinstance(live, dict) else {}
        live_at = timestamp(live.get('observed_at'))
        live_valid = bool(self.boot_id and live.get('boot_id') == self.boot_id and live_at is not None
                          and self.boot_started_at <= live_at <= time.time() + 5 and live.get('state') == state)
        label = STATES.get(state, '状态未知')
        if interrupted:
            label = '系统中断：主机重启；旧状态为“' + label + '”，等待新的状态证据'
        else:
            label = ('本次启动后最近确认：' if live_valid else '最近记录（运行未实时确认）：') + label
        backend = source.get('backend')
        if backend == 'MuJoCo FBX-derived no-latch variant v1':
            backend, variant = 'MuJoCo', 'FBX-derived no-latch v1'
        else:
            backend = backend if backend in ('MuJoCo', 'Isaac') else '未知'
            variant = VARIANTS.get(source.get('variant'), '未知 / 未提供') if isinstance(source.get('variant'), str) else '未知 / 未提供'
        terminal = source.get('terminal_kind')
        terminal = terminal if isinstance(terminal, str) and terminal in TERMINALS else None
        tasks = source.get('tasks') if isinstance(source.get('tasks'), dict) else {}
        chain = []
        for key, title in TASKS.items():
            item = tasks.get(key) if isinstance(tasks.get(key), dict) else {}
            # No implicit success promotion from phase, counts or an engineer's "complete".
            chain.append(dict(id=key, title=title, verification='未验证',
                physical_attempts=count(item.get('physical_attempts')),
                audited_successes=count(item.get('audited_successes'))))
        videos, media_note = self.manifest_videos(sources)
        return dict(schema_version=1, source_schema='web-progress-v1' if fresh_schema else 'legacy-state',
            backend=backend, variant=variant, phase=phase, phase_label=PHASES.get(phase, '工程阶段未知'),
            state=state, state_label=label, runtime_evidence_confirmed=live_valid and not interrupted,
            terminal_kind=terminal, terminal_label=TERMINALS.get(terminal, '尚无真实终态 / 未验证'),
            physical_attempts=count(source.get('physical_attempts', source.get('attempts'))),
            audited_successes=count(source.get('audited_successes')),
            actions=count(source.get('actions')), simulated_seconds=number(source.get('simulated_seconds', source.get('sim_s'))),
            diagnostic_runs=count(source.get('diagnostic_runs')), diagnostic_simulated_seconds=number(source.get('diagnostic_sim_s')),
            needs_human=source.get('needs_human', source.get('human_help_needed')) if type(source.get('needs_human', source.get('human_help_needed'))) is bool else None,
            original_usd_joints='未知 / 未验证', tasks=chain,
            last_progress_at_unix=progress, progress_time_basis='explicit_last_progress' if fresh_schema else 'legacy_engineering_record',
            source_updated_at_unix=updated, heartbeat_at_unix=timestamp(heartbeat.get('at')),
            fetched_at_unix=time.time(), live_evidence_at_unix=live_at if live_valid else None,
            host_restart_observed=incident.get('classification') == 'host_restart_infrastructure_interruption',
            interrupted_by_restart=interrupted, boot_started_at_unix=self.boot_started_at,
            recovery_ack_at_unix=timestamp(ack.get('at', ack.get('updated_at', ack.get('acknowledged_at')))),
            videos=videos, media_note=media_note, sources=sources)

    def manifest_videos(self, sources):
        manifest = self.optional('video-manifest.json', sources)
        entries = manifest.get('videos') if manifest.get('schema_version', manifest.get('schema')) == 1 else []
        entries = entries if isinstance(entries, list) else []
        videos, allowed, seen = [], set(), set()
        for entry in entries[:100]:
            try:
                # One reviewed existing recorder: validate_door.py calls record_tick on each
                # physics tick, closes EpisodeVideo, then publishes this exact manifest row.
                legacy_recording = False
                if isinstance(entry, dict) and manifest.get('schema') == 1 and entry.get('episode') in ('door-v1-001','door-v3-contact-001') and entry.get('kind') == 'diagnostic':
                    raw_path = Path(entry.get('path', ''))
                    rel = str(raw_path.relative_to(self.root)) if raw_path.is_absolute() else str(raw_path)
                    if rel == 'diagnostics/'+entry['episode']+'/video/episode.mp4':
                        path = self.safe(self.root / rel)
                        legacy_recording = True
                        entry = dict(entry, id=entry['episode'], path=rel, completed=entry.get('complete'), continuous=True,
                                     category='diagnostic', completed_at=path.stat().st_mtime)
                if not isinstance(entry, dict) or entry.get('completed') is not True or entry.get('continuous') is not True:
                    continue
                ident = entry.get('id');category = entry.get('category');relative = entry.get('path')
                if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in seen:
                    continue
                seen.add(ident)
                if not isinstance(category, str) or category not in CATEGORIES:
                    continue
                if category == 'audited_success' and entry.get('audited_success') is not True:
                    continue
                if not isinstance(relative, str) or not re.fullmatch(r'(?:videos|diagnostics|campaign|runs)/[A-Za-z0-9_./-]+\.mp4', relative):
                    continue
                if any(part.startswith('.') for part in relative.split('/')) or '//' in relative:
                    continue
                expected = entry.get('sha256')
                if not legacy_recording and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
                    continue
                complete_at = timestamp(entry.get('completed_at'))
                if complete_at is None or complete_at > time.time() + 5:
                    continue
                path = self.safe(self.root / relative)
                route = '/videos/ikea-' + ident + '.mp4';before = signature(path)
                entry_hash = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
                cached = self.media.get(route)
                if cached and cached['signature'] == before and cached['entry_hash'] == entry_hash:
                    video = cached['public']
                else:
                    self.media.pop(route, None)
                    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'format=duration:stream=width,height,avg_frame_rate', '-of', 'json', str(path)],
                        capture_output=True, check=True, timeout=8)
                    meta = json.loads(result.stdout);stream = meta['streams'][0]
                    duration = number(float(meta['format']['duration']))
                    if not duration or not stream['width'] or not stream['height']:
                        continue
                    h = hashlib.sha256()
                    with path.open('rb') as f:
                        for block in iter(lambda: f.read(1024 * 1024), b''):
                            h.update(block)
                    if (expected is not None and h.hexdigest() != expected) or signature(path) != before:
                        continue
                    expected = h.hexdigest()
                    video = dict(id='ikea-' + ident, url=route, title='IKEA · ' + CATEGORIES[category] + ' · ' + ident,
                        kind='ikea_' + category, category=category, category_label=CATEGORIES[category],
                        source_kind=entry.get('kind') if entry.get('kind') in ('diagnostic', 'learning', 'policy', 'policy_incomplete', 'human_assisted', 'audited_success') else None,
                        source_title=entry.get('title', '')[:300] if isinstance(entry.get('title', ''), str) else '',
                        source='ikea/' + relative, sha256=expected, size_bytes=before[2],
                        duration_s=duration, width=stream['width'], height=stream['height'], fps=stream['avg_frame_rate'],
                        completed_at_unix=complete_at, result_note=CATEGORIES[category] + '记录；仅凭录像不推断任务链成功。',
                        view='已封口连续录像；相机类型未提供，不能当作策略原始视野。',
                        timing='物理录像时长不等于推理墙钟时间。',
                        provenance_basis='完成标记、ffprobe、SHA256 与读取前后稳定签名均通过。')
                    self.media[route] = dict(path=path, signature=before, entry_hash=entry_hash, public=video)
                allowed.add(route);videos.append(video)
            except (OSError, ValueError, TypeError, KeyError, IndexError, subprocess.SubprocessError):
                continue
        self.media = {k: v for k, v in self.media.items() if k in allowed}
        return videos, '已完成连续录像如下' if videos else '首个连续视频尚未完成'

    def video(self, route):
        with self.lock:
            self.manifest_videos([])
            item = self.media.get(route)
            if item is None:
                return None
            path = self.safe(item['path'])
            if signature(path) != item['signature']:
                self.media.pop(route, None)
                raise ValueError('video evidence changed')
            return path, path.stat()
