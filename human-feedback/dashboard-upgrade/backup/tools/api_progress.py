"""Read-only public projection. No actor imports, arbitrary paths or audit reads."""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'api-ground-to-table/actor-adapter'
EPISODE = re.compile(r'episode-[0-9]{4,8}')
RUN = re.compile(r'api-ground-[0-9]{3,8}')
KINDS = {
    'host_audited_success': '结果报告审计成功（本页未独立复审）',
    'physical_failure': '真实物理失败',
    'safety_stop': '安全停止',
    'budget_limited_incomplete': '预算截断 · 未完成（不是物理失败）',
    'agent_stopped_incomplete': '主动提前结束 · 未完成',
    'adapter_stopped_incomplete': '适配器停止 · 未完成',
    'infrastructure_error': '后台 / 基础设施错误',
}
STATES = {
    'inference_waiting_no_deadline': '正在推理 · 无推理截止时间',
    'action_executing': '动作执行中',
    'ended': '回合终止',
    'error': '后台错误',
    'infrastructure_error': '后台 / 基础设施错误',
}


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def identifier(value, pattern):
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def signature(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


class APIProgress:
    def __init__(self, root=ADAPTER):
        self.root = Path(root)
        self.lock = threading.RLock()
        self.media = {}

    def safe(self, path):
        # Reject symlinks at every component, even if they currently point inside.
        rel = path.relative_to(self.root)
        current = self.root
        if current.is_symlink():
            raise ValueError('symlink source')
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('symlink source')
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError('source outside adapter')
        return path

    def read(self, path):
        self.safe(path)
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('public source too large')
        raw = path.read_bytes()
        return json.loads(raw), {
            'source': 'api-ground-to-table/actor-adapter/' + str(path.relative_to(self.root)),
            'sha256': hashlib.sha256(raw).hexdigest(),
        }

    def sealed_video(self, episode, result_hash):
        """Only called after result exists (writer emits it after host.close)."""
        path = self.safe(self.root / 'campaign' / episode / 'video/episode.mp4')
        route = '/videos/api-ground-' + episode + '.mp4'
        before = signature(path)
        old = self.media.get(route)
        if old and old['signature'] == before and old['result_hash'] == result_hash:
            return old['public']
        self.media.pop(route, None)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'format=duration:stream=width,height,avg_frame_rate',
            '-of', 'json', str(path)], capture_output=True, check=True, timeout=8)
        info = json.loads(probe.stdout)
        stream = info['streams'][0]
        duration = number(float(info['format']['duration']))
        if not duration or not stream['width'] or not stream['height']:
            raise ValueError('incomplete video')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                h.update(block)
        if signature(path) != before:
            raise ValueError('video still changing')
        public = dict(id='api-ground-' + episode, url=route,
            title='API 地面块上桌 · ' + episode, kind='completed_api_recording',
            source='api-ground-to-table/actor-adapter/campaign/' + episode + '/video/episode.mp4',
            sha256=h.hexdigest(), size_bytes=before[2], duration_s=duration,
            width=stream['width'], height=stream['height'], fps=stream['avg_frame_rate'],
            view='MuJoCo 连续物理录像；包含外部诊断视角，不等于策略原始视野。',
            timing='推理期间物理暂停；录像长度不是推理墙钟时间，不声称实时闭环。',
            provenance_basis='result 已存在；固定路径录像经 ffprobe、读取前后文件签名和 SHA256 核验。')
        self.media[route] = dict(path=path, signature=before, result_hash=result_hash, public=public)
        return public

    def video(self, route):
        with self.lock:
            item = self.media.get(route)
            if not item:
                return None
            path = self.safe(item['path'])
            result, ref = self.read(path.parent.parent / 'result.json')
            if ref['sha256'] != item['result_hash'] or signature(path) != item['signature']:
                self.media.pop(route, None)
                raise ValueError('video evidence changed')
            return path, path.stat()

    def snapshot(self):
        with self.lock:
            return self._snapshot()

    def _snapshot(self):
        current = {}
        sources = []
        source_error = None
        try:
            current, ref = self.read(self.root / 'auxiliary-progress.json')
            if not isinstance(current, dict):
                raise ValueError('invalid progress')
            sources.append(ref)
        except (OSError, ValueError, TypeError):
            current = {}
            source_error = '公开进度暂不可读；保留未知状态，不推断机器人故障。'
        episode = identifier(current.get('episode'), EPISODE)
        rows, videos, permitted = [], [], set()
        directories = sorted((self.root / 'campaign').glob('episode-*'))
        for folder in directories:
            name = identifier(folder.name, EPISODE)
            if not name:
                continue
            row = dict(episode=name, run_id=None, terminal_kind=None,
                terminal_label='尚无终态结果', api_calls_completed=None, actions=None,
                physical_s=None, backend='未知', video_status='result 未完成 / 录像未封口，暂不发布')
            if name == episode:
                try:
                    provenance, ref = self.read(folder / 'provenance.json')
                    if provenance.get('backend') in ('MuJoCo', 'Isaac'):
                        row['backend'] = provenance['backend']
                        sources.append(ref)
                except (OSError, ValueError, TypeError, AttributeError):
                    pass
            try:
                result, ref = self.read(folder / 'result.json')
                if not isinstance(result, dict) or result.get('episode_id', name) != name:
                    raise ValueError('invalid result')
                row['source'] = ref
                row['run_id'] = identifier(result.get('run_id'), RUN)
                kind = result.get('episode_terminal_kind', result.get('terminal_kind'))
                row['terminal_kind'] = kind if kind in KINDS else 'unknown'
                row['terminal_label'] = KINDS.get(kind, '终态分类未知')
                row['api_calls_completed'] = number(result.get('api_calls'))
                row['actions'] = number(result.get('actions'))
                row['physical_s'] = number(result.get('physical_s'))
                row['backend'] = result.get('backend') if result.get('backend') in ('MuJoCo', 'Isaac') else '未知'
                row['video_status'] = 'result 已有；录像尚未通过封口 / 可读核验，暂不发布'
                video = dict(self.sealed_video(name, ref['sha256']))
                video['result_note'] = row['terminal_label'] + '；抓取 / 搬运 / 放置：未验证。'
                row['video_status'] = '完成录像已核验'
                row['video_url'] = video['url']
                videos.append(video)
                permitted.add(video['url'])
            except (OSError, ValueError, TypeError, KeyError, IndexError, subprocess.SubprocessError):
                pass  # Never expose raw exceptions, file contents or host paths.
            rows.append(row)
        self.media = {k: v for k, v in self.media.items() if k in permitted}
        selected = next((row for row in rows if row['episode'] == episode), None)
        terminal = selected and selected['terminal_kind'] is not None
        state = 'ended' if terminal else current.get('state')
        state = state if state in STATES else 'unknown'
        updated = number(current.get('updated_at_unix'))
        if terminal:
            updated = max(updated or 0, (self.root / 'campaign' / episode / 'result.json').stat().st_mtime)
        history = None
        if episode:
            try:
                entries, ref = self.read(self.root / 'campaign' / episode / 'public_history_index.json')
                if isinstance(entries, list):
                    history = dict(ref, entries=len(entries))
            except (OSError, ValueError, TypeError):
                pass
        return dict(run_id=(selected['run_id'] if terminal else identifier(current.get('run_id'), RUN)),
            episode=episode, state=state, state_label=STATES.get(state, '状态未知'),
            task_stage='未提供可核验的任务子阶段',
            verification={'grasp': '未验证', 'carry': '未验证', 'placement': '未验证'},
            api_calls_completed=(selected['api_calls_completed'] if terminal else number(current.get('api_calls_completed', current.get('api_calls')))),
            actions=(selected['actions'] if terminal else number(current.get('actions'))),
            physical_s=(selected['physical_s'] if terminal else number(current.get('physical_s'))),
            updated_at_unix=updated, observed_at_unix=time.time(),
            age_s=max(0, time.time() - updated) if updated is not None else None,
            physics_paused=None if terminal else (current.get('physics_paused') if type(current.get('physics_paused')) is bool else None),
            terminal_kind=selected['terminal_kind'] if terminal else None,
            terminal_label=selected['terminal_label'] if terminal else '尚无当前回合 result；终态未验证',
            backend=selected['backend'] if selected else '未知',
            source_error=source_error, sources=sources, public_history=history,
            episodes=rows, videos=videos,
            notice='每 10 秒读取公开文件；未更新只显示时长，不对推理设超时或重发。后台聊天通知未启用。')
