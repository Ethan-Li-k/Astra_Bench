import json
import tempfile
import unittest
from pathlib import Path

from rsi.codex_app_server import CodexPolicyAdapter
from rsi.four_point import FOUR_POINT_NAMES


class FakeTransport:
    def __init__(self):
        self.requests = []
        self.notifications = []
        self.replies = []

    def request(self, method, params, timeout):
        self.requests.append((method, params, timeout))
        if method == 'initialize':
            return {}
        if method == 'thread/start':
            return {'thread': {'id': 'thread-1'}, 'model': 'gpt-6-astra',
                    'reasoningEffort': 'xhigh',
                    'sandbox': {'type': 'workspaceWrite', 'networkAccess': False},
                    'approvalsReviewer': 'auto_review', 'approvalPolicy': 'on-request',
                    'runtimeWorkspaceRoots': [params['cwd']]}
        if method == 'turn/start':
            return {'turn': {'id': 'turn-1'}}
        raise AssertionError(method)

    def notify(self, method, params):
        self.notifications.append((method, params))

    def reply(self, identifier, result):
        self.replies.append((identifier, result))


class FakeHost:
    method = 'direct'

    def __init__(self):
        self.calls = []

    def dispatch(self, name, arguments):
        self.calls.append((name, arguments))
        return {'native_outcome': 'in_progress', 'images': []}


class CodexPolicyAdapterTests(unittest.TestCase):
    def test_turn_start_wait_is_unbounded_and_unknown_ack_is_not_reissued(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            adapter = CodexPolicyAdapter(transport, host, root, developer_instructions='policy')
            adapter.connect()
            original = transport.request
            calls = []
            def uncertain(method, params, timeout):
                if method == 'turn/start':
                    calls.append(timeout)
                    raise EOFError('unknown ACK')
                return original(method, params, timeout)
            transport.request = uncertain
            with self.assertRaises(EOFError):
                adapter.start_turn('go')
            with self.assertRaisesRegex(RuntimeError, 'uncertain'):
                adapter.start_turn('do not resend')
            self.assertEqual(calls, [None])

    def test_model_receipt_omits_repeated_targets_but_full_audit_is_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            record = {'command_id': 'move:0', 'status': 'timed_out',
                'actual_error_m': .002, 'actual_rotation_error_rad': .07,
                'fingerprint': list(range(300)),
                'observation_anchor': {'positions': list(range(100))},
                'requested_target': {'positions': list(range(100))},
                'approved_target': {'positions': list(range(100))}}
            packet = {'observation': {'images': [], 'command_status': record},
                'execution': [record], 'native_outcome': 'in_progress'}
            original = json.dumps(packet)
            host.dispatch = lambda name, args: packet
            adapter = CodexPolicyAdapter(transport, host, root, developer_instructions='policy')
            adapter.connect(); adapter.start_turn('go')
            adapter.handle_tool_call({'id': 7, 'method': 'item/tool/call', 'params': {
                'threadId': 'thread-1', 'turnId': 'turn-1', 'tool': 'scalebfm_act',
                'callId': 'call-1', 'arguments': {}}})
            text = transport.replies[0][1]['contentItems'][0]['text']
            visible = json.loads(text)
            self.assertLess(len(text), len(original)*.6)
            self.assertEqual(visible['execution'][0]['actual_error_m'], .002)
            self.assertEqual(visible['observation']['command_status']['status'], 'timed_out')
            self.assertEqual(json.loads(Path(visible['full_receipt_path']).read_text()), packet)
            self.assertEqual(json.dumps(packet), original)

    def test_policy_wait_has_no_inference_deadline_or_duplicate_turn(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            waits = []
            def next_message(timeout):
                waits.append(timeout)
                self.assertIsNone(timeout, 'A slow policy must not be terminated by a timer')
                return {'method': 'turn/completed', 'params': {
                    'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'completed'}}}
            transport.next_message = next_message
            adapter = CodexPolicyAdapter(transport, host, root, developer_instructions='policy')
            adapter.connect()
            self.assertEqual(adapter.run_turn('go')['status'], 'completed')
            self.assertEqual(waits, [None])
            self.assertEqual(sum(r[0] == 'turn/start' for r in transport.requests), 1)

    def test_global_model_effort_lock_rejects_downgrade_before_connect(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, 'always gpt-6-astra/xhigh'):
                CodexPolicyAdapter(FakeTransport(), FakeHost(), root,
                    developer_instructions='policy', effort='high')

    def test_connect_and_turn_payload_match_current_app_server_contract(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            adapter = CodexPolicyAdapter(
                transport, host, root, developer_instructions='policy contract',
                model='gpt-6-astra', effort='xhigh')
            adapter.connect()
            adapter.start_turn('start the visual task')
            self.assertEqual([r[0] for r in transport.requests],
                             ['initialize', 'thread/start', 'turn/start'])
            thread = transport.requests[1][1]
            self.assertEqual(thread['model'], 'gpt-6-astra')
            self.assertEqual(thread['developerInstructions'], 'policy contract')
            self.assertEqual(thread['cwd'], str(Path(root).resolve()))
            self.assertEqual(thread['runtimeWorkspaceRoots'], [str(Path(root).resolve())])
            self.assertEqual(thread['approvalPolicy'], 'on-request')
            self.assertEqual(thread['approvalsReviewer'], 'auto_review')
            self.assertEqual(thread['sandbox'], 'workspace-write')
            self.assertIn('four_point_translate',
                          {tool['name'] for tool in thread['dynamicTools']})
            turn = transport.requests[2][1]
            self.assertEqual(turn['approvalPolicy'], 'on-request')
            self.assertEqual(turn['approvalsReviewer'], 'auto_review')
            self.assertEqual(turn['threadId'], 'thread-1')
            self.assertEqual(turn['input'], [{'type': 'text',
                                              'text': 'start the visual task'}])
            self.assertEqual(transport.notifications, [('initialized', {})])

    def test_wrong_permission_receipt_is_rejected_before_model_turn(self):
        for mismatch in ({'sandbox': {'type': 'readOnly'}},
                         {'approvalsReviewer': 'user'},
                         {'runtimeWorkspaceRoots': ['/']},
                         {'approvalPolicy': 'never'}):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as root:
                transport = FakeTransport()
                original = transport.request
                def request(method, params, timeout):
                    response = original(method, params, timeout)
                    if method == 'thread/start': response.update(mismatch)
                    return response
                transport.request = request
                adapter = CodexPolicyAdapter(transport, FakeHost(), root,
                                             developer_instructions='policy')
                with self.assertRaisesRegex(RuntimeError, 'permission'):
                    adapter.connect()
                self.assertIsNone(adapter.thread_id)
                self.assertFalse(any(r[0] == 'turn/start' for r in transport.requests))

    def test_dynamic_tool_call_is_checked_dispatched_audited_and_replied(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            adapter = CodexPolicyAdapter(
                transport, host, root, developer_instructions='policy')
            adapter.connect()
            adapter.start_turn('go')
            event = {'jsonrpc': '2.0', 'id': 7, 'method': 'item/tool/call',
                     'params': {'threadId': 'thread-1', 'turnId': 'turn-1',
                                'callId': 'call-1', 'namespace': None,
                                'tool': 'loco_start',
                                'arguments': json.dumps({
                                    'task': 'grasp red cube',
                                    'output_dir': str(Path(root)/'episode')})}}
            adapter.handle_tool_call(event)
            self.assertEqual(host.calls[0][0], 'loco_start')
            identifier, response = transport.replies[0]
            self.assertEqual(identifier, 7)
            self.assertTrue(response['success'])
            payload = json.loads(response['contentItems'][0]['text'])
            self.assertEqual(payload['native_outcome'], 'in_progress')
            self.assertTrue((Path(root)/'rpc_calls'/'0000_request.json').is_file())
            self.assertTrue((Path(root)/'rpc_calls'/'0000_result.json').is_file())

    def test_tool_call_from_wrong_turn_is_fatal_before_dispatch(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            adapter = CodexPolicyAdapter(
                transport, host, root, developer_instructions='policy')
            adapter.connect()
            adapter.start_turn('go')
            event = {'id': 8, 'method': 'item/tool/call',
                     'params': {'threadId': 'thread-1', 'turnId': 'wrong',
                                'callId': 'call-2', 'tool': 'loco_start',
                                'arguments': {}}}
            with self.assertRaises(RuntimeError):
                adapter.handle_tool_call(event)
            self.assertEqual(host.calls, [])
            self.assertEqual(transport.replies, [])

    def test_malformed_tool_json_returns_recoverable_no_execution(self):
        with tempfile.TemporaryDirectory() as root:
            transport, host = FakeTransport(), FakeHost()
            adapter = CodexPolicyAdapter(
                transport, host, root, developer_instructions='policy')
            adapter.connect()
            adapter.start_turn('go')
            event = {'id': 9, 'method': 'item/tool/call',
                     'params': {'threadId': 'thread-1', 'turnId': 'turn-1',
                                'callId': 'call-3', 'tool': 'loco_start',
                                'arguments': '{bad json'}}
            packet = adapter.handle_tool_call(event)
            self.assertTrue(packet['no_execution'])
            self.assertTrue(packet['retryable'])
            self.assertFalse(transport.replies[0][1]['success'])
            self.assertEqual(host.calls, [])



if __name__ == '__main__':
    unittest.main()
