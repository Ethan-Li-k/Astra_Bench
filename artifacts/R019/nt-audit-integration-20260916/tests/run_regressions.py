from support import *
import tempfile,unittest,shutil
B=Path(__file__).resolve().parents[1];tempfile.tempdir=str(B/'tests')
sys.path.insert(0,'/home/galbot/lizekai/Loco_manip/locomanip/src')
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
 if "." in name:
  parent, child=name.rsplit(".",1)
  if parent in sys.modules:setattr(sys.modules[parent],child,m)
 return m
module('rsi.codex_app_server',B/'candidate/rsi/codex_app_server.py')
module('tools.learn_grasp_skill',B/'candidate/tools/learn_grasp_skill.py')
suite=unittest.TestSuite()
for file in ('test_codex_app_server.py','test_learning_host.py'):
 m=module('reg_'+file[:-3],B/'snapshots/tests'/file);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
# Original audit cases, redirected only to candidate reader and local temporary directory.
p=RSI/'tests/test_campaign_status.py';source=p.read_text();(B/'snapshots/tests/test_campaign_status.py').write_text(source)
source=source.replace('ROOT=Path(__file__).resolve().parents[1]',f'ROOT=Path({str(B)!r})').replace("ROOT/'tools/audit_simple_campaigns.py'","ROOT/'candidate/tools/audit_simple_campaigns.py'").replace("ROOT/'artifacts/R018/tmp'","ROOT/'tests'")
m=types.ModuleType('reg_campaign');m.__file__=str(p);exec(compile(source,str(p),'exec'),m.__dict__);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
# Existing 18 audit/ranking regression cases, with storage redirected under this task.
origin=RSI/'artifacts/architecture-review-20260916/memory-priority';p=origin/'tests/test_memory_priority.py';source=p.read_text();(B/'snapshots/tests/test_memory_priority.py').write_text(source)
source=source.replace('ROOT=Path(__file__).resolve().parents[1]',f'ROOT=Path({str(B)!r})').replace("TREE/'rsi/skill_learning.py'","ROOT/'snapshots/rsi/skill_learning.py'").replace("TREE/'tools'/name",f"Path({str(RSI)!r})/'tools'/name")
source=source.replace("ROOT/'evidence/public-experience-0001.json'",f"Path({str(origin)!r})/'evidence/public-experience-0001.json'").replace("ROOT/'evidence/host-only/success_review.json'",f"Path({str(origin)!r})/'evidence/host-only/success_review.json'")
m=types.ModuleType('reg_memory_priority');m.__file__=str(p);exec(compile(source,str(p),'exec'),m.__dict__);suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(m))
r=unittest.TextTestRunner(verbosity=2).run(suite)
(B/'evidence/regressions.json').write_text(json.dumps({'run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'no_physics':True,'no_model_api':True,'test_root_redirections':'see tests/run_regressions.py; assertions unchanged'},indent=2));sys.exit(not r.wasSuccessful())
