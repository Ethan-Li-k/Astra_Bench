"""Codex app-server policy boundary; importing it never starts a model turn."""
import base64
import json
import time
from pathlib import Path

from rsi.policy_harness import tool_specs


def _brief_receipt(record):
    return {k: v for k, v in record.items() if not k.startswith('_') and k not in (
        'fingerprint', 'observation_anchor', 'requested_target', 'approved_target')}


def _content_items(packet, full_receipt_path=None):
    visible = dict(packet)
    if 'observation' in packet:
        observation = dict(packet['observation'])
        if 'command_status' in observation:
            observation['command_status'] = _brief_receipt(observation['command_status'])
        visible['observation'] = observation
    if 'execution' in packet:
        visible['execution'] = [_brief_receipt(r) for r in packet['execution']]
    if full_receipt_path is not None:
        visible['full_receipt_path'] = str(full_receipt_path)
    items = [{'type': 'inputText',
              'text': json.dumps(visible, separators=(',', ':'))}]
    observation = packet.get('observation', {}) if isinstance(packet, dict) else {}
    images = packet.get('images', observation.get('images', []))
    for descriptor in images:
        path = Path(descriptor['path'])
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        items.append({'type': 'inputImage',
                      'imageUrl': 'data:image/png;base64,' + encoded})
    return items


TURN_RECORD_CONTRACT = 'codex-terminal-sequence-v1'
NETWORK_CONTINUATION = 'Observe; next_call: '


def _closed_network_failure(turn):
    # Only called after a matching terminal event, never for an error notification.
    error = json.dumps(turn.get('error'), ensure_ascii=False).lower()
    compact = ''.join(c for c in error if c.isalnum())
    if any(word in compact for word in (
            'usagelimit', 'quota', 'ratelimit', 'budget', 'authorization',
            'unauthorized', 'authentication', 'permissiondenied', 'invalidapikey',
            'safety', 'contentfilter', 'contextwindow', 'maxtokens',
            'httpstatuscode401', 'httpstatuscode402', 'httpstatuscode403', 'httpstatuscode429')):
        return False
    return turn.get('status') == 'failed' and any(word in compact for word in (
        'responsestreamdisconnected', 'streamdisconnected', 'networkerror',
        'connectionreset', 'connectionclosed', 'tlsclose'))

class CodexPolicyAdapter:
    """Route one persistent Codex thread to one stateful loco-manip tool host."""

    def __init__(self, transport, host, workspace, *, developer_instructions,
                 model='gpt-6-astra', effort='xhigh', model_provider='openai', timeout=900,
                 normal_tools=False, terminal_callback=None):
        if model != 'gpt-6-astra' or effort != 'xhigh':
            raise ValueError('Global constraint: always gpt-6-astra/xhigh')
        if not isinstance(developer_instructions, str) or not developer_instructions.strip():
            raise ValueError('developer_instructions must be nonempty')
        self.transport = transport
        self.host = host
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.calls = self.workspace/'rpc_calls'
        self.calls.mkdir(exist_ok=True)
        self.developer_instructions = developer_instructions
        self.model = model
        self.effort = effort
        self.model_provider = model_provider
        self.timeout = timeout
        self.normal_tools = normal_tools
        self.thread_id = self.turn_id = None
        self.call_index = 0
        self.turns_started = 0
        self.last_reply_time = None
        self._start_uncertain = False
        self.turn_ids = []
        self.terminal_callback = terminal_callback
        self._recovery_actions = getattr(host, 'actions', 0)
        self._episode_host = host
        self._episode_backend = self._episode_reset_id = None

    def connect(self):
        if self.thread_id is not None:
            raise RuntimeError('Codex policy thread is already connected')
        self.transport.request('initialize', {
            'clientInfo': {'name': 'loco-manip-four-point-policy', 'version': '1'},
            'capabilities': {'experimentalApi': True}}, self.timeout)
        self.transport.notify('initialized', {})
        params = {
            'cwd': str(self.workspace), 'model': self.model,
            'modelProvider': self.model_provider,
            'config': {'model_reasoning_effort': self.effort,
                       'features.shell_tool': self.normal_tools, 'features.unified_exec': self.normal_tools,
                       'features.view_image': True,
                       'features.multi_agent': False,
                       'features.memories': False, 'web_search': 'disabled'},
            'developerInstructions': self.developer_instructions,
            'dynamicTools': (self.host.tool_specs() if hasattr(self.host, 'tool_specs') else tool_specs(self.host.method)),
            'ephemeral': True,
            'allowProviderModelFallback': False, 'approvalPolicy': 'on-request',
            'sandbox': 'workspace-write',
            'approvalsReviewer': 'auto_review',
            'runtimeWorkspaceRoots': [str(self.workspace)]}
        response = self.transport.request('thread/start', params, self.timeout)
        if (response.get('model') != self.model
                or response.get('reasoningEffort') != self.effort):
            raise RuntimeError('Codex app-server returned a different model or effort')
        if (response.get('sandbox', {}).get('type') != 'workspaceWrite'
                or response.get('sandbox', {}).get('networkAccess', False)
                or response.get('approvalPolicy') != 'on-request'
                or response.get('approvalsReviewer') != 'auto_review'
                or response.get('runtimeWorkspaceRoots') != [str(self.workspace)]):
            raise RuntimeError('Codex app-server returned a different permission contract')
        self.thread_id = response['thread']['id']
        return response

    def start_turn(self, text):
        if self.thread_id is None:
            raise RuntimeError('Call connect before start_turn')
        if self._start_uncertain:
            raise RuntimeError('Previous turn/start ACK is uncertain; do not reissue')
        if self.turn_id is not None:
            raise RuntimeError('A Codex turn is already active')
        self._start_uncertain = True
        response = self.transport.request('turn/start', {
            'threadId': self.thread_id, 'model': self.model, 'effort': self.effort,
            'approvalPolicy': 'on-request', 'approvalsReviewer': 'auto_review',
            'cwd': str(self.workspace),
            'runtimeWorkspaceRoots': [str(self.workspace)],
            'input': [{'type': 'text', 'text': text}]}, None)
        identifier = response['turn']['id']
        if not isinstance(identifier, str) or not identifier or identifier in self.turn_ids:
            raise RuntimeError('Invalid or duplicate turn/start identity; do not reissue')
        self.turn_id = identifier
        self.turn_ids.append(identifier)
        self._start_uncertain = False
        self.turns_started += 1
        self.last_reply_time = time.monotonic()
        return self.turn_id

    def _write(self, suffix, value):
        path = self.calls/f'{self.call_index:04d}_{suffix}.json'
        path.write_text(json.dumps(value, indent=2))

    def handle_tool_call(self, event):
        if event.get('method') != 'item/tool/call' or 'id' not in event:
            raise RuntimeError('Expected one app-server dynamic tool request')
        params = event.get('params', {})
        if (params.get('threadId') != self.thread_id
                or params.get('turnId') != self.turn_id):
            raise RuntimeError('Tool call belongs to another Codex thread or turn')
        raw_arguments = params.get('arguments')
        received = time.monotonic()
        request = {'call_id': params.get('callId'), 'tool': params.get('tool'),
                   'arguments': raw_arguments}
        self._write('request', request)
        try:
            arguments = (json.loads(raw_arguments)
                         if isinstance(raw_arguments, str) else raw_arguments)
            if not isinstance(arguments, dict):
                raise ValueError('Tool arguments must be a JSON object')
            packet = self.host.dispatch(params.get('tool'), arguments)
        except ValueError as error:
            packet = {'error_type': type(error).__name__, 'error': str(error),
                      'no_execution': True, 'retryable': True}
            success = False
        else:
            success = True
        self._write('result', packet)
        self._write('timing', {
            'tool': params.get('tool'),
            'policy_wait_wall_s': received-self.last_reply_time,
            'tool_wall_s': time.monotonic()-received})
        self.transport.reply(event['id'], {
            'success': success, 'contentItems': _content_items(
                packet, self.calls/f'{self.call_index:04d}_result.json')})
        self.call_index += 1
        if self._episode_backend is None and getattr(self.host, 'backend', None) is not None:
            self._episode_backend = self.host.backend
            self._episode_reset_id = self._reset_id()
        self.last_reply_time = time.monotonic()
        return packet

    def _reset_id(self):
        return (getattr(getattr(self.host, 'backend', None), 'scene_setup', {})
                .get('reset_provenance', {}).get('reset_id'))

    def _recovery_reason(self, turn):
        if not _closed_network_failure(turn):
            return 'nonrecoverable_terminal'
        if self.terminal_callback is None:
            return 'terminal_recorder_required'
        backend = getattr(self.host, 'backend', None)
        if (self.host is not self._episode_host or backend is not self._episode_backend
                or not self._episode_reset_id or self._reset_id() != self._episode_reset_id):
            return 'episode_identity_unverified'
        if (getattr(self.host, 'finished', True) or getattr(self.host, 'skill_updated', False)
                or getattr(self.host, 'execution_error', None)
                or getattr(self.host, 'initialization_error', None)
                or getattr(backend, 'reason', None)):
            return 'episode_terminal'
        if getattr(backend, 'active', True):
            return 'execution_pending'
        if getattr(self.host, 'actions', 0) <= self._recovery_actions:
            return 'no_new_physical_progress'
        return 'confirmed_closed_network_turn'

    def run_turn(self, text):
        turn_id = self.start_turn(text)
        while True:
            # No inference deadline; notifications/EOF never authorize a new turn.
            event = self.transport.next_message(None)
            if event.get('method') == 'item/tool/call':
                self.handle_tool_call(event)
                continue
            params = event.get('params', {})
            if (event.get('method') == 'turn/completed'
                    and params.get('threadId') == self.thread_id
                    and params.get('turn', {}).get('id') == turn_id):
                turn = params['turn']
                reason = None if turn.get('status') == 'completed' else self._recovery_reason(turn)
                # Persist every matched terminal BEFORE returning, raising or starting
                # a successor. A write failure must escape without any continuation.
                if self.terminal_callback is not None:
                    self.terminal_callback(self.turns_started, self.thread_id, turn,
                                           reason, self._reset_id())
                self.turn_id = None
                if turn.get('status') == 'completed':
                    return turn
                if reason != 'confirmed_closed_network_turn':
                    raise RuntimeError(f'Codex turn failed ({reason}): {turn.get("error")}')
                self._recovery_actions = self.host.actions
                turn_id = self.start_turn(NETWORK_CONTINUATION + json.dumps(self.host.next_call()))
                continue
            if 'id' in event and 'method' in event:
                raise RuntimeError(f'Unexpected Codex request: {event.get("method")}')
