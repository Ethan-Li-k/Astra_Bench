from pathlib import Path
import ast
B=Path(__file__).resolve().parent
current=(B/'snapshots/rsi/codex_app_server.py').read_text()
old=(B.parent/'candidate/rsi/codex_app_server.py').read_text()
def source(text,kind,name):
 t=ast.parse(text)
 n=next(n for n in ast.walk(t) if isinstance(n,kind) and n.name==name)
 return '\n'.join(text.splitlines()[n.lineno-1:n.end_lineno])
helper=source(old,ast.FunctionDef,'_closed_network_failure')
run=source(old,ast.FunctionDef,'run_turn')
s=current.replace('\n\nclass CodexPolicyAdapter:', '\n\n'+helper+'\n\nclass CodexPolicyAdapter:')
s=s.replace('        self._start_uncertain = False\n','        self._start_uncertain = False\n        self._recovery_actions = getattr(host, "actions", 0)\n        self._recovery_index = 0\n        self.continuity = self.workspace/"continuity"\n        self.continuity.mkdir(exist_ok=True)\n',1)
s=s[:s.index('    def run_turn(')]+run+'\n'
p=B/'evidence/previous-recovery-on-current.py';p.write_text(s)
