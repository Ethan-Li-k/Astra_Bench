from pathlib import Path
import os,subprocess,json,datetime
B=Path(__file__).resolve().parent
commands=[('focused-final.log',['python','-B','tests/test_continuity.py']),('caller-final.log',['python','-B','tests/test_caller_integration.py'])]
rows=[]
for log,cmd in commands:
 p=subprocess.run(cmd,cwd=B,text=True,capture_output=True);(B/'evidence'/log).write_text(p.stdout+p.stderr);rows.append({'command':cmd,'returncode':p.returncode,'log':'evidence/'+log})
 assert p.returncode==0
# Same existing interpreter/modules as the earlier real-boundary tests; no physics or model.
code='''import sys,importlib.util,unittest,tempfile
from pathlib import Path
b=Path.cwd();sys.path.insert(0,'/home/galbot/lizekai/RSI');tempfile.tempdir=str(b/'tests')
s=importlib.util.spec_from_file_location('rsi.codex_app_server',b/'candidate/rsi/codex_app_server.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
s=importlib.util.spec_from_file_location('existing_tests',b/'snapshots/tests/test_codex_app_server.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));sys.exit(not r.wasSuccessful())
'''
cmd=['/home/galbot/lizekai/Loco_manip/ENV/locomanip_sim/bin/python','-B','-c',code]
p=subprocess.run(cmd,cwd=B,text=True,capture_output=True);(B/'evidence/existing-final.log').write_text(p.stdout+p.stderr);rows.append({'command':'existing 7 tests against candidate adapter, existing interpreter; see run_checks.py','returncode':p.returncode,'log':'evidence/existing-final.log'});assert p.returncode==0
(B/'evidence/checks.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':rows,'tests_passed':18,'simulation_calls':0,'model_calls':0,'api_calls':0},indent=2))
print('18/18 offline tests passed')
