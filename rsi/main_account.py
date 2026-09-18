"""Explicit primary ChatGPT route; no API, auxiliary or rate-limit probes."""
import hashlib
import json
from pathlib import Path

from rsi.stdio_transport import StdioAppServer

ROOT = Path('/home/galbot/lizekai/RSI')
MAIN_ONLY_POLICY = 'authorized-main-chatgpt-only-v1'
LAUNCHER = ROOT/'main-account/run.sh'
MAIN_AUTH = Path('/home/galbot/.codex/auth.json')


def require_main_source():
    policy = json.loads((ROOT/'ref/tasks/account-policy.json').read_text())
    if (policy.get('main_account_allowed') is not True
            or policy.get('auxiliary_accounts_allowed') is not False
            or policy.get('model') != 'gpt-6-astra' or policy.get('effort') != 'xhigh'):
        raise ValueError('Current persisted account policy is not main-only')
    link = ROOT/'main-account/home/auth.json'
    if not link.is_symlink() or link.resolve() != MAIN_AUTH or not link.is_file():
        raise ValueError('Existing main-account authentication link required')
    return str(MAIN_AUTH)


def verify_account(transport, output):
    source = require_main_source()
    account = transport.request('account/read', {'refreshToken': False}, None).get('account')
    if not account or account.get('type') != 'chatgpt':
        raise RuntimeError('Main route requires existing ChatGPT authentication; no fallback')
    identity = {k: account.get(k) for k in ('type', 'email', 'planType')}
    receipt = {'policy': MAIN_ONLY_POLICY, 'account_route': 'main_chatgpt',
        'authentication_source': source, 'runtime_home': str(ROOT/'main-account/home'),
        'account_type': account['type'], 'plan_type': account.get('planType'),
        'identity_sha256': hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
        'verified_by': 'account/read(refreshToken=false)', 'model': 'gpt-6-astra',
        'effort': 'xhigh', 'api_enabled': False, 'auxiliary_enabled': False}
    with (Path(output)/'account_route_verified.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    return receipt


class MainAccountTransport(StdioAppServer):
    def __init__(self, argv, workspace, **kwargs):
        require_main_source()
        self.verified = False
        super().__init__(argv, workspace, **kwargs)

    def request(self, method, params, timeout):
        if method == 'thread/start' and not self.verified:
            verify_account(self, self.workspace.parent)
            self.verified = True
        if method == 'turn/start':
            require_main_source()
            if not self.verified:
                raise RuntimeError('Unverified main account cannot create a turn')
        return super().request(method, params, timeout)


def initial_main_text(adapter):
    """Deliver pinned startup context once; original skills/evidence stay available."""
    from rsi.actor_inputs import verify_actor_inputs
    verify_actor_inputs(adapter.input_manifest, adapter.developer_instructions)
    pieces = []  # Existing runtime already directs use of supplied workspace/CONTROL.
    for name in ('workspace.json', 'CONTROL_CONTRACT.md'):
        path = Path(adapter.workspace) / name
        if str(path.resolve()) not in adapter.input_manifest['files']:
            if name == 'workspace.json':
                raise RuntimeError('Pinned workspace is required for main startup')
            continue
        pieces.append(name + ':\n' + path.read_text())
    pieces.append('Execute the registered next_call: ' + json.dumps(adapter.host.next_call()))
    return '\n\n'.join(pieces)


def run_main(adapter, output, *, transport_factory=MainAccountTransport):
    from rsi.codex_app_server import NETWORK_CONTINUATION
    from rsi.episode_continuation import ClosedNetworkNoProgress, wait_for_network_diagnosis
    record_feedback_intake(output)
    transport = transport_factory([str(LAUNCHER), 'app-server', '--stdio'], Path(output)/'app_server')
    adapter.transport = transport
    try:
        adapter.connect()
        path = Path(output)/'model_backend.json'
        backend = json.loads(path.read_text())
        backend.update(codex_started=True, main_pid=transport.process.pid,
                       verified_account_route='main_chatgpt')
        path.write_text(json.dumps(backend, indent=2))
        text = initial_main_text(adapter)
        idle_turns = 0
        while not (adapter.host.finished and adapter.host.skill_updated):
            before = (adapter.host.actions, adapter.call_index, adapter.host.skill_updated)
            try:
                adapter.run_turn(text)
            except ClosedNetworkNoProgress:
                wait_for_network_diagnosis(adapter, output)
            after = (adapter.host.actions, adapter.call_index, adapter.host.skill_updated)
            idle_turns = idle_turns + 1 if before == after else 0
            if idle_turns >= 2:
                wait_for_network_diagnosis(adapter, output, reason='completed_main_turns_without_new_information')
                idle_turns = 0
            text = NETWORK_CONTINUATION + json.dumps(adapter.host.next_call())
    finally:
        transport.close()


def record_feedback_intake(output):
    """Read the durable human inbox before each new actor, without model calls."""
    inbox = ROOT/'human-feedback/dashboard-upgrade/feedback'
    rows = []
    for path in inbox.glob('answers/FB-*.json'):
        answer = json.loads(path.read_text())
        if answer.get('fixture'):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        review_path = inbox/'reviews'/path.name
        review = json.loads(review_path.read_text()) if review_path.is_file() else {}
        reviewed = review.get('answer_sha256') == digest
        rows.append({'feedback_id':path.stem,'answer_sha256':digest,
            'saved_at':answer.get('saved_at'), 'priority':'highest_user_feedback',
            'review_stage':review.get('stage') if reviewed else 'pending_owner_review',
            'source':str(path), 'review':str(review_path) if reviewed else None,
            'actor_input_use':'Only explicitly reviewed release-bound public feedback may enter actor input'})
    rows.sort(key=lambda x:x.get('saved_at') or '')
    (Path(output)/'human_feedback_intake.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    pending = [r['feedback_id'] for r in rows if r['review_stage']=='pending_owner_review']
    if pending:
        print(json.dumps({'event':'highest_priority_human_feedback_pending','feedback_ids':pending},ensure_ascii=False),flush=True)
