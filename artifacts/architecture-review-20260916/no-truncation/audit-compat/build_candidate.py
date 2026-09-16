from pathlib import Path
import ast,difflib
B=Path(__file__).resolve().parent
old=(B/'evidence/previous-recovery-on-current.py').read_text()
helper=old[old.index('def _closed_network_failure'):old.index('\n\nclass CodexPolicyAdapter:')]
a=(B/'snapshots/rsi/codex_app_server.py').read_text()
a=a.replace('\n\nclass CodexPolicyAdapter:', '\n\nTURN_RECORD_CONTRACT = \'codex-terminal-sequence-v1\'\nNETWORK_CONTINUATION = \'Observe; next_call: \'\n\n\n'+helper+'\n\nclass CodexPolicyAdapter:')
a=a.replace('                 normal_tools=False):','                 normal_tools=False, terminal_callback=None):')
a=a.replace('        self._start_uncertain = False\n','''        self._start_uncertain = False
        self.turn_ids = []
        self.terminal_callback = terminal_callback
        self._recovery_actions = getattr(host, 'actions', 0)
        self._episode_host = host
        self._episode_backend = self._episode_reset_id = None
''',1)
a=a.replace("        self.turn_id = response['turn']['id']\n", """        identifier = response['turn']['id']
        if not isinstance(identifier, str) or not identifier or identifier in self.turn_ids:
            raise RuntimeError('Invalid or duplicate turn/start identity; do not reissue')
        self.turn_id = identifier
        self.turn_ids.append(identifier)
""")
a=a.replace('        self.call_index += 1\n','''        self.call_index += 1
        if self._episode_backend is None and getattr(self.host, 'backend', None) is not None:
            self._episode_backend = self.host.backend
            self._episode_reset_id = self._reset_id()
''')
pos=a.index('    def run_turn(')
a=a[:pos]+'''    def _reset_id(self):
        setup = getattr(getattr(self.host, 'backend', None), 'scene_setup', None)
        reset = setup.get('reset_provenance') if isinstance(setup, dict) else None
        identity = reset.get('reset_id') if isinstance(reset, dict) else None
        return identity if isinstance(identity, str) and identity else None

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
'''
(B/'candidate/rsi/codex_app_server.py').write_text(a)
c=(B/'snapshots/tools/learn_grasp_skill.py').read_text().replace('from rsi.codex_app_server import CodexPolicyAdapter','from rsi.codex_app_server import CodexPolicyAdapter, TURN_RECORD_CONTRACT, NETWORK_CONTINUATION')
c=c.replace('    combined_size = validate_policy_instructions(prompt, immutable)\n    memory.runtime_instructions = immutable','''    # Reserve the additional network prompt for admission AND later skill updates.
    instruction_overhead = immutable + NETWORK_CONTINUATION
    combined_size = validate_policy_instructions(prompt, instruction_overhead)
    memory.runtime_instructions = instruction_overhead''')
c=c.replace('hashlib.sha256(immutable.encode()).hexdigest()', 'hashlib.sha256(instruction_overhead.encode()).hexdigest()').replace('hashlib.sha256((prompt+immutable).encode()).hexdigest()', 'hashlib.sha256((prompt+instruction_overhead).encode()).hexdigest()')
c=c.replace("'scope': 'Actor developer instructions; task data, observations and tool schemas separate.'", "'scope': 'Actor developer instructions plus reserved network continuation; task data, observations and schemas separate.',\n        'network_continuation': NETWORK_CONTINUATION,\n        'developer_instructions_sha256': hashlib.sha256((prompt+immutable).encode()).hexdigest()")
c=c.replace('    adapter = CodexPolicyAdapter(transport, host, agent,\n        developer_instructions=prompt+immutable, normal_tools=True)', '''    def record_terminal(sequence, thread_id, turn, recovery_reason, reset_id):
        if '_rsi_terminal' in turn:
            raise ValueError('Reserved terminal receipt metadata collision')
        receipt = dict(turn, _rsi_terminal={'contract': TURN_RECORD_CONTRACT,
            'sequence': sequence, 'thread_id': thread_id,
            'recovery_reason': recovery_reason, 'reset_id': reset_id})
        # Exclusive creation preserves earlier evidence; partial writes fail audit.
        with (output/f'turn_{sequence:03d}.json').open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())

    adapter = CodexPolicyAdapter(transport, host, agent,
        developer_instructions=prompt+immutable, normal_tools=True,
        terminal_callback=record_terminal)''')
c=c.replace("            (output/f'turn_{adapter.turns_started:03d}.json').write_text(json.dumps(turn, indent=2))\n",'')
c=c.replace("        'codex_turns': adapter.turns_started, 'dynamic_tool_calls': adapter.call_index,", "        'codex_turns': adapter.turns_started, 'dynamic_tool_calls': adapter.call_index,\n        'turn_record_contract': TURN_RECORD_CONTRACT,\n        'codex_thread_id': adapter.thread_id, 'codex_turn_ids': list(adapter.turn_ids),")
(B/'candidate/tools/learn_grasp_skill.py').write_text(c)
audit_base=B/'snapshots/final/tools/audit_simple_campaigns.py'
u=audit_base.read_text()
helper='''def turn_completeness(episode, result):
    """Validate host terminal receipts; never expose them as actor observations."""
    paths = {p.name: p for p in episode.glob('turn_*.json') if p.is_file()}
    contract = (result or {}).get('turn_record_contract')
    try:
        records = {name: json.loads(p.read_text()) for name, p in paths.items()}
        if any(not isinstance(row, dict) for row in records.values()):
            raise ValueError('non-object terminal')
        numbered = (result or {}).get('codex_turns')
        if contract is None:
            if any('_rsi_terminal' in row for row in records.values()):
                raise ValueError('new receipts without result contract')
            # Old no-recovery receipts retain their previous interpretation. Where
            # the historical count exists, do not accept a known numbering gap.
            if type(numbered) is int and numbered > 0:
                if set(records) != {f'turn_{i:03d}.json' for i in range(1, numbered+1)}:
                    raise ValueError('legacy numbering gap')
                last = records[f'turn_{numbered:03d}.json']
            else:
                last = records[sorted(records)[-1]] if records else {}
            return bool(last.get('status') == 'completed'), 'legacy_no_identity_proof'
        if contract != 'codex-terminal-sequence-v1':
            raise ValueError('unsupported terminal contract')
        identities = result.get('codex_turn_ids')
        thread = result.get('codex_thread_id')
        if (type(numbered) is not int or numbered < 1 or not isinstance(identities, list)
                or len(identities) != numbered or not isinstance(thread, str) or not thread
                or any(not isinstance(i, str) or not i for i in identities)
                or len(set(identities)) != numbered):
            raise ValueError('invalid ACK identity sequence')
        if set(records) != {f'turn_{i:03d}.json' for i in range(1, numbered+1)}:
            raise ValueError('missing or extra terminal number')
        recovered_reset = None
        for i, identity in enumerate(identities, 1):
            row = records[f'turn_{i:03d}.json']
            meta = row.get('_rsi_terminal')
            if (not isinstance(meta, dict) or meta.get('contract') != contract
                    or type(meta.get('sequence')) is not int or meta['sequence'] != i
                    or meta.get('thread_id') != thread or row.get('id') != identity):
                raise ValueError('terminal identity/order mismatch')
            reset_id = meta.get('reset_id')
            if recovered_reset is not None and reset_id != recovered_reset:
                raise ValueError('reset changed after recovered failure')
            if row.get('status') == 'completed':
                if row.get('error') or meta.get('recovery_reason') is not None:
                    raise ValueError('completed terminal has error/recovery label')
            elif (row.get('status') == 'failed' and i < numbered and row.get('error')
                    and meta.get('recovery_reason') == 'confirmed_closed_network_turn'
                    and isinstance(reset_id, str) and reset_id):
                recovered_reset = reset_id
            else:
                raise ValueError('unrecovered or incomplete terminal')
        return True, 'complete_terminal_sequence'
    except (OSError, ValueError, TypeError, KeyError) as error:
        return False, 'invalid_terminal_sequence: '+str(error)


'''
u=u.replace('def episode_status(episode):',helper+'def episode_status(episode):')
u=u.replace("    turns=[json.loads(p.read_text()) for p in sorted(episode.glob('turn_*.json')) if p.is_file()]\n    full_turn=bool(turns and turns[-1].get('status')=='completed')",'    full_turn, turn_integrity = turn_completeness(episode, result)')
u=u.replace("'physical_attempt':actions>0,'actions':actions,'full_turn_completed':full_turn,", "'physical_attempt':actions>0,'actions':actions,'full_turn_completed':full_turn,\n        'turn_record_integrity':turn_integrity,")
(B/'candidate/tools/audit_simple_campaigns.py').write_text(u)
paths=('rsi/codex_app_server.py','tools/learn_grasp_skill.py','tools/audit_simple_campaigns.py')
patch=''
for name in paths:
 old=(audit_base if name=='tools/audit_simple_campaigns.py' else B/'snapshots'/name).read_text();new=(B/'candidate'/name).read_text();ast.parse(new)
 patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(B/'audit-compatible.patch').write_text(patch)
