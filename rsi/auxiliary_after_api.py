"""Explicit, release-pinned auxiliary entry after observed API exhaustion."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/galbot/lizekai/RSI')
LAUNCHER = ROOT/'codex-account-2/run.sh'
AUXILIARY_ONLY_POLICY = 'isolated-auxiliary20x-only-v1'


def verify_exhaustion(path, expected_sha256):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT/'artifacts'):
        raise ValueError('API exhaustion evidence must be local experiment evidence')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('API exhaustion evidence changed')
    proof = json.loads(raw)
    if (proof.get('schema') != 'rsi-observed-api-budget-exhaustion-v1'
            or proof.get('model') != 'gpt-6-astra' or proof.get('effort') != 'xhigh'
            or len(proof.get('sources', [])) < 2):
        raise ValueError('Explicit API budget exhaustion required')
    seen = set()
    for ref in proof['sources']:
        source = (ROOT/ref['path']).resolve()
        if (not source.is_relative_to(ROOT/'artifacts/R019')
                or source.parent.name != 'background-requests' or source in seen):
            raise ValueError('Independent recorded provider responses required')
        seen.add(source)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref['sha256']:
            raise ValueError('Provider exhaustion source changed')
        row = json.loads(data)
        if (row.get('http_status') != 429 or row.get('creation_rejected') is not True
                or row.get('model_posts') != 1
                or row.get('provider_error', {}).get('type') != 'budget_exceeded'):
            raise ValueError('Rate limit or unknown transport error is not budget exhaustion')
    return dict(path=str(path.relative_to(ROOT)), sha256=expected_sha256)


def run_auxiliary(adapter, output, *, transport_factory=None):
    from rsi.stdio_transport import StdioAppServer
    from rsi.codex_app_server import NETWORK_CONTINUATION
    from rsi.episode_continuation import ClosedNetworkNoProgress, wait_for_network_diagnosis
    # No bare codex invocation, account fallback or API retry exists in this path.
    transport = (transport_factory or StdioAppServer)(
        [str(LAUNCHER), 'app-server', '--stdio'], Path(output)/'app_server')
    adapter.transport = transport
    try:
        backend_path = Path(output)/'model_backend.json'
        if backend_path.exists():
            backend = json.loads(backend_path.read_text())
            backend.update(codex_started=True, auxiliary_pid=transport.process.pid)
            backend_path.write_text(json.dumps(backend, indent=2))
        adapter.connect()
        text = 'Read workspace.json; execute the registered next_call: ' + json.dumps(adapter.host.next_call())
        idle_turns = 0
        while not (adapter.host.finished and adapter.host.skill_updated):
            before = (adapter.host.actions, adapter.call_index, adapter.host.skill_updated)
            try:
                adapter.run_turn(text)  # Wait for the matching terminal, without a deadline.
            except ClosedNetworkNoProgress:
                wait_for_network_diagnosis(adapter, output)
            after = (adapter.host.actions, adapter.call_index, adapter.host.skill_updated)
            idle_turns = idle_turns + 1 if before == after else 0
            if idle_turns >= 2:
                wait_for_network_diagnosis(adapter, output, reason='completed_auxiliary_turns_without_new_information')
                idle_turns = 0
            text = NETWORK_CONTINUATION + json.dumps(adapter.host.next_call())
    finally:
        transport.close()
