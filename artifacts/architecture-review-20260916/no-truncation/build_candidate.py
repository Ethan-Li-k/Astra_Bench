from pathlib import Path
import difflib
B=Path(__file__).resolve().parent
s=(B/'snapshots/rsi/codex_app_server.py').read_text()
s=s.replace('\n\nclass CodexPolicyAdapter:', '''

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


class CodexPolicyAdapter:''')
s=s.replace('        self.last_reply_time = None','''        self.last_reply_time = None
        self._start_uncertain = False
        self._recovery_actions = getattr(host, 'actions', 0)
        self._recovery_index = 0
        self.continuity = self.workspace/'continuity'
        self.continuity.mkdir(exist_ok=True)''')
s=s.replace("        if self.turn_id is not None:\n            raise RuntimeError('A Codex turn is already active')", "        if self._start_uncertain:\n            raise RuntimeError('Previous turn/start ACK is uncertain; do not reissue')\n        if self.turn_id is not None:\n            raise RuntimeError('A Codex turn is already active')\n        self._start_uncertain = True")
s=s.replace("'input': [{'type': 'text', 'text': text}]}, self.timeout)","'input': [{'type': 'text', 'text': text}]}, None)")
s=s.replace("        self.turn_id = response['turn']['id']\n", "        self.turn_id = response['turn']['id']\n        self._start_uncertain = False\n")
s=s.replace("                if turn.get('status') != 'completed':\n                    raise RuntimeError(f'Codex turn failed: {turn.get(\"error\")}')", '''                if turn.get('status') != 'completed':
                    actions = getattr(self.host, 'actions', 0)
                    network = _closed_network_failure(turn)
                    reason = 'nonrecoverable_terminal'
                    if network:
                        reason = ('episode_terminal' if getattr(self.host, 'finished', True)
                                  or getattr(self.host, 'skill_updated', False) else
                                  'execution_pending' if getattr(getattr(self.host, 'backend', None), 'active', True) else
                                  'no_new_physical_progress' if actions <= self._recovery_actions else
                                  'confirmed_closed_network_turn')
                    record = {'thread_id': self.thread_id, 'turn': turn,
                              'reason': reason, 'actions': actions,
                              'tool_replies_written': self.call_index,
                              'same_backend': True, 'reset_or_action_replay': False}
                    path = self.continuity/f'{self._recovery_index:04d}_terminal.json'
                    path.write_text(json.dumps(record, indent=2))
                    self._recovery_index += 1
                    if reason != 'confirmed_closed_network_turn':
                        raise RuntimeError(f'Codex turn failed ({reason}): {turn.get("error")}')
                    self._recovery_actions = actions
                    # A tool reply was written locally, not necessarily received by the
                    # model. Supply public next_call and insist on reconciliation first.
                    text = ('The previous turn ended in a confirmed network failure. '
                            'The same robot episode and thread remain. Do not reset or '
                            'replay any previous action. Read your existing NOTES and '
                            'public rpc_calls receipts; obtain a fresh allowed observation '
                            'and reconcile the last command before any new action. '
                            'Follow SKILL.md and current next_call: '
                            + json.dumps(self.host.next_call()))
                    turn_id = self.start_turn(text)
                    continue''')
(B/'candidate/rsi/codex_app_server.py').write_text(s)
orig=(B/'snapshots/rsi/codex_app_server.py').read_text()
(B/'continuity.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile='a/rsi/codex_app_server.py',tofile='b/rsi/codex_app_server.py')))
