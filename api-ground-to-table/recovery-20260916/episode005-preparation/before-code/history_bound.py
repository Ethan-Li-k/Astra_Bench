"""Deterministic public history index; no model, filesystem reader or private export."""
import copy
import json


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


class PublicHistory:
    def __init__(self, instructions, task, initial_content):
        self.prefix = [{'role': 'developer', 'content': instructions},
                       {'role': 'user', 'content': json.dumps(task, ensure_ascii=False)}]
        self.groups = [[{'role': 'user', 'content': initial_content}]]
        self.index = []

    def append_completed_turn(self, response_items, current_content, evidence_ref):
        if any(v.get('type')=='function_call' for v in response_items):
            raise ValueError('No-tool continuation cannot discard function calls')
        self.groups.append(copy.deepcopy(response_items)+[{'role':'user','content':copy.deepcopy(current_content)}])
        self.groups=self.groups[-2:]
        self.index.append({'tool':None,'public_evidence':evidence_ref,'model_turn_completed':True,
            'no_physical_action':True,'notice':'Natural completed model turn; same episode continued without reset or replay.'})

    def append(self, response_items, call, packet, content, evidence_ref):
        calls = [v for v in response_items if v.get('type') == 'function_call']
        if len(calls) != 1 or calls[0]['call_id'] != call['call_id']:
            raise ValueError('Cannot bound an unfinished/multiple function exchange')
        group = copy.deepcopy(response_items)
        group.append({'type': 'function_call_output', 'call_id': call['call_id'],
                      'output': json.dumps(packet, ensure_ascii=False)})
        images = [v for v in content if v.get('type') == 'input_image']
        if len(images) > 2:
            raise ValueError('At most one head/wrist pair per observation group')
        if images:
            group.append({'role': 'user', 'content': [{'type': 'input_text',
                'text': 'RGB from this tool exchange; observation path: '+str(packet.get('observation_path', evidence_ref['path']))}]+images})
        self.groups.append(group)
        # Verbatim excerpts, explicitly labelled; full public arguments/outputs stay retrievable.
        arguments = json.loads(call['arguments'])
        summary = arguments.get('public_decision', {})
        self.index.append({'call_id': call['call_id'], 'tool': call['name'],
            'public_evidence': evidence_ref,
            'public_decision_excerpts_max_160_chars_each': {k: v[:160] for k, v in summary.items()},
            'excerpt_notice': 'Verbatim prefixes, not a generated summary; read public_evidence for full context.',
            'observed_status': {k: packet[k] for k in ('native_outcome', 'stop_reason', 'step_id',
                'remaining_steps', 'observation_path') if k in packet}})
        # Whole exchanges only; encrypted continuation in retained groups remains in memory.
        self.groups = self.groups[-2:]

    def payload(self, base, max_bytes):
        if len(self.index) > 120:
            raise ValueError('History exceeds approved episode')
        index_message = {'role': 'user', 'content': json.dumps({
            'public_history_index': self.index,
            'notice': 'Older full exchanges/RGB omitted offline. Index entries are sourced excerpts and paths, not current observations. Initial task/skill remain authoritative. Retrieved old evidence retains its original timestamp/path; reading it does not refresh robot state.'}, ensure_ascii=False)}
        while self.groups:
            history = self.prefix+[index_message]+[item for group in self.groups for item in group]
            payload = dict(base, input=history)
            if len(encode(payload)) <= max_bytes:
                return payload
            if len(self.groups) == 1:
                raise ValueError('Latest complete exchange exceeds request byte cap; no request sent')
            self.groups.pop(0)
        raise ValueError('Latest observation required')
