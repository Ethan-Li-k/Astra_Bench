"""Candidate for central owner: expose a closed quota terminal, not auto-retry."""


class CodexQuotaBoundary(RuntimeError):
    def __init__(self, *, thread_id, turn_id, reset_id):
        super().__init__('current_codex_usage_limit_closed_boundary')
        self.thread_id=thread_id
        self.turn_id=turn_id
        self.reset_id=reset_id
        self.unknown_request_replay_allowed=False


def quota_terminal(turn):
    if not isinstance(turn,dict) or turn.get('status')!='failed': return False
    error=turn.get('error')
    if not isinstance(error,dict): return False
    for key in ('codexErrorInfo','codex_error_info','code'):
        value=error.get(key)
        if value=='usageLimitExceeded' or isinstance(value,dict) and value.get('type')=='usageLimitExceeded':
            return True
    return False
