#!/usr/bin/env python3
"""Loopback-only read-only video/progress UI; exact media whitelist + Range."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from store import ROOT, Store, verify, now, digest
from api_progress import APIProgress
from dashboard import Dashboard
from feedback_board import FeedbackBoard

MEDIA = {
    '/videos/simple-door-0008.mp4': ROOT.parent / 'artifacts/R019/door-campaign/episode-0008/video/episode.mp4',
    '/videos/h001-closure-lift.mp4': ROOT / 'reproductions/H001/evidence/closure-lift-head-left.mp4',
    '/videos/f001-baseline.mp4': ROOT.parent / 'api-ground-to-table/reproductions/F001-baseline-001/video/episode.mp4',
}


def byte_range(value, size):
    if value is None:
        return 0, size - 1, 200
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
    if not match or not any(match.groups()):
        raise ValueError('invalid single byte range')
    left, right = match.groups()
    if not left:
        if int(right) <= 0:
            raise ValueError('invalid suffix range')
        start, end = max(0, size - int(right)), size - 1
    else:
        start, end = int(left), min(int(right), size - 1) if right else size - 1
    if start >= size or start > end:
        raise ValueError('range not satisfiable')
    return start, end, 206


def progress():
    data = json.loads((ROOT / 'ui/video-index.json').read_text())
    # Select public status only. Never return raw status, host paths or audit data.
    path = ROOT / 'reproductions/H001/status.json'
    state = json.loads(path.read_text())
    reproduced = state.get('failure_reproduced') is True
    data['h001_progress'] = {'failure_reproduced': reproduced,
        'source': 'human-feedback/reproductions/H001/status.json',
        'source_sha256': digest(path.read_bytes()), 'source_updated_utc': state.get('updated_utc'),
        'correction_success_claimed': False,
        'summary': ('H001：旧动作基线已在新动力学运行中复现失败；完成65个原动作。'
                    '复现不代表修正成功，根因尚未确认；四条原话已记录，目前不追加提问。'
                    if reproduced else 'H001：当前状态未确认基线失败已复现；四条原话已记录，目前不追加提问。')}
    fourth = ROOT / 'H001-user-feedback-004.json'
    if fourth.exists():
        d = json.loads(fourth.read_text())
        data['feedback']['H001']['replies'].append({'question_id':'side_grasp_gate_correction_004', 'verbatim':d.get('verbatim', d.get('user_original_words', '第四条侧抓反馈已保存')), 'source':'human-feedback/H001-user-feedback-004.json', 'sha256':digest(fourth.read_bytes())})
    data['human_help']['open'] = False
    return data


def make_server(port, dashboard=None, feedback_root=None, fixture=False, delivery=None):
    api = APIProgress()
    board = dashboard or Dashboard(api=api)
    feedback = FeedbackBoard(board, feedback_root, fixture, delivery)
    csrf = secrets.token_urlsafe(32)
    store = Store()
    verify()
    media_stat = {}
    catalog = json.loads((ROOT / 'ui/video-index.json').read_text())
    for item in catalog['videos']:
        path = MEDIA[item['url']]
        if digest(path.read_bytes()) != item['sha256']:
            raise ValueError('video source hash changed')
        media_stat[item['url']] = path.stat()
    routes = {'/': ROOT / 'ui/index.html', '/app.js': ROOT / 'ui/app.js',
              '/style.css': ROOT / 'ui/style.css', '/video-index.json': ROOT / 'ui/video-index.json'}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, data, mime='application/json; charset=utf-8'):
            raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; media-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            if self.command != 'HEAD': self.wfile.write(raw)

        def video(self, route, dynamic=None):
            path, original = dynamic if dynamic else (MEDIA[route], media_stat[route])
            stat = path.stat()
            if (stat.st_ino, stat.st_size, stat.st_mtime_ns) != (original.st_ino, original.st_size, original.st_mtime_ns):
                raise ValueError('video changed since verified startup')
            try:
                start, end, status = byte_range(self.headers.get('Range'), stat.st_size)
            except ValueError:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{stat.st_size}')
                self.send_header('Content-Length', '0'); self.end_headers(); return
            self.send_response(status)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status == 206: self.send_header('Content-Range', f'bytes {start}-{end}/{stat.st_size}')
            self.end_headers()
            if self.command == 'HEAD': return
            with path.open('rb') as stream:
                stream.seek(start); remaining = end - start + 1
                while remaining:
                    block = stream.read(min(65536, remaining))
                    if not block: break
                    self.wfile.write(block); remaining -= len(block)

        def do_HEAD(self):
            self.do_GET()

        def local(self):
            expected = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != expected:
                raise ValueError('loopback Host required')
            if self.headers.get('Origin') not in [None, 'http://' + expected]:
                raise ValueError('cross-origin request refused')

        def do_GET(self):
            try:
                self.local()
                path = urlsplit(self.path).path
                if path == '/api/health':
                    self.reply(200, {'service': 'rsi-H001-human-feedback', 'pid': os.getpid(), 'evidence_valid': bool(verify()), 'mode': 'four_task_feedback', 'human_help_open': bool(feedback.cases()['cases']), 'fixture': fixture})
                elif path == '/api/dashboard':
                    snapshot = board.snapshot()
                    feedback.publish_packages(snapshot['tasks'])
                    self.reply(200, dict(snapshot, help=feedback.cases(), answers=feedback.receipts(), csrf=csrf, fixture=fixture))
                elif path == '/api/feedback':
                    self.reply(200, {'answers': feedback.receipts(), 'fixture': fixture})
                elif path.startswith('/media/'):
                    board.snapshot()
                    item = board.media_file(path)
                    if not item: self.reply(404, {'error': 'not in public media whitelist'})
                    elif item[0].suffix == '.mp4': self.video(path, item)
                    else: self.reply(200, item[0].read_bytes(), 'image/png')
                elif path == '/api/case':
                    self.reply(410, {'error': 'Questionnaire closed; use the read-only video homepage', 'human_help_open': False})
                elif path == '/api/progress':
                    self.reply(200, progress())
                elif path == '/api/ground-progress':
                    self.reply(200, api.snapshot())
                elif path in MEDIA:
                    self.video(path)
                elif path.startswith('/videos/api-ground-'):
                    # Dynamic routes only become eligible via verified public results.
                    api.snapshot()
                    dynamic = api.video(path)
                    if dynamic:
                        self.video(path, dynamic)
                    else:
                        self.reply(404, {'error': 'not in completed media whitelist'})
                elif path.startswith('/api/annotation/'):
                    self.reply(200, store.read(path.removeprefix('/api/annotation/')))
                elif path in routes:
                    p = routes[path]
                    mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
                            '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.json': 'application/json'}[p.suffix]
                    self.reply(200, p.read_bytes(), mime)
                else:
                    self.reply(404, {'error': 'not in resource whitelist'})
            except (BrokenPipeError, ConnectionResetError):
                pass  # Browsers cancel Range streams when seeking or switching videos.
            except (ValueError, OSError, KeyError):
                self.reply(409, {'error': 'request or source evidence rejected'})

        def do_POST(self):
            try:
                self.local()
                if urlsplit(self.path).path != '/api/feedback':
                    self.reply(410, {'error': 'Legacy questionnaire is closed; use scoped task feedback'}); return
                expected = f'http://127.0.0.1:{self.server.server_port}'
                if self.headers.get('Origin') != expected or self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin'):
                    self.reply(403, {'error': '同源提交 required'}); return
                if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), csrf):
                    self.reply(403, {'error': '页面校验失效，请刷新后重试'}); return
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    self.reply(415, {'error': 'JSON required'}); return
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536 or self.headers.get('Transfer-Encoding'):
                    self.reply(413, {'error': '提交大小无效'}); return
                payload = json.loads(self.rfile.read(size))
                self.reply(200, feedback.submit(payload))
            except (ValueError, OSError, KeyError, TypeError):
                self.reply(409, {'error': '提交未被接受：检查任务、证据版本和回答内容；同一提交编号不可改写。'})

        def log_message(self, fmt, *args):
            # Log routes/status only; submitted answers and CSRF token never logged.
            print(now(), fmt % args, flush=True)

    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    httpd.daemon_threads = True
    return httpd


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--fixture-root', type=Path)
    args = parser.parse_args()
    if args.fixture_root:
        fixture_root = args.fixture_root.resolve()
        allowed = (ROOT/'dashboard-upgrade').resolve()
        if not fixture_root.is_relative_to(allowed) or not fixture_root.name.startswith('fixture-'):
            raise SystemExit('Fixture root must be isolated beneath dashboard-upgrade/fixture-*')
        server = make_server(args.port, feedback_root=fixture_root/'feedback', fixture=True)
    else:
        server = make_server(args.port)
    status = {'pid': os.getpid(), 'url': f'http://127.0.0.1:{server.server_port}/',
              'started_at': now(), 'bind': '127.0.0.1', 'session': 'rsi-human-feedback-h001'}
    status_path = args.fixture_root/'server-status.json' if args.fixture_root else ROOT/'reviews/server-status.json'
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status), flush=True)
    server.serve_forever()
