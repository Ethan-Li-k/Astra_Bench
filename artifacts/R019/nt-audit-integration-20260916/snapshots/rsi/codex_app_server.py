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


class CodexPolicyAdapter:
    """Route one persistent Codex thread to one stateful loco-manip tool host."""

    def __init__(self, transport, host, workspace, *, developer_instructions,
                 model='gpt-6-astra', effort='xhigh', model_provider='openai', timeout=900,
                 normal_tools=False):
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
        self.turn_id = response['turn']['id']
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
        self.last_reply_time = time.monotonic()
        return packet

    def run_turn(self, text):
        turn_id = self.start_turn(text)
        while True:
            # Inference has no wall-clock deadline. EOF still arrives immediately
            # through the transport; never resend a turn merely because it is slow.
            event = self.transport.next_message(None)
            if event.get('method') == 'item/tool/call':
                self.handle_tool_call(event)
                continue
            params = event.get('params', {})
            if (event.get('method') == 'turn/completed'
                    and params.get('threadId') == self.thread_id
                    and params.get('turn', {}).get('id') == turn_id):
                turn = params['turn']
                self.turn_id = None
                if turn.get('status') != 'completed':
                    raise RuntimeError(f'Codex turn failed: {turn.get("error")}')
                return turn
            if 'id' in event and 'method' in event:
                raise RuntimeError(f'Unexpected Codex request: {event.get("method")}')
