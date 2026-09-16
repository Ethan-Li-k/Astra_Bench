"""Host-only static evaluator probes. No simulator import, model, or physics."""
import ast, copy, hashlib, io, json, unittest
from pathlib import Path
import numpy as np
src=Path('evidence/workspace/ground_task.py')
tree=ast.parse(src.read_text())
keep=[n for n in tree.body if (isinstance(n,ast.ClassDef) and n.name=='PhaseAudit') or (isinstance(n,ast.FunctionDef) and n.name=='model_digest') or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CRITERIA' for t in n.targets))]
ns={'np':np,'hashlib':hashlib}
exec(compile(ast.Module(body=keep,type_ignores=[]),str(src),'exec'),ns)
tests=ast.parse(Path('evidence/workspace/tests/test_ground_audit.py').read_text())
body=[n for n in tests.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
ns.update(copy=copy,unittest=unittest)
exec(compile(ast.Module(body=body,type_ignores=[]),'frozen_test_ground_audit.py','exec'),ns)
stream=io.StringIO()
r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ns['Counterexamples']))
Path('logic_probe.log').write_text(stream.getvalue())
initial,advance,walk,Audit=[ns[k] for k in ('initial','advance','walk','PhaseAudit')]
out={'method':'AST-only classes/functions; no mujoco import, no model inference, no physics','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'existing_tests':{'run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors)},'probes':[]}
def finish(a,s):
    s['cube'][0]+=.2;advance(a,s)
    s.update(table_contact=True,inside_table=True,hand_contact=False,grasped=False,cube_bottom=.63)
    advance(a,s,110)
def add(name,a,expected,detail):
    out['probes'].append({'name':name,'expected':expected,'actual':copy.deepcopy(a.result()),'detail':detail})
s=initial();a=Audit(copy.deepcopy(s))
s.update(grasped=True,hand_contact=True,floor_contact=False,cube_bottom=.1)
advance(a,s,30);walk(a,s);advance(a,s,30);finish(a,s)
add('grasp_before_locomotion_is_accepted',a,False,'Grasp/lift starts before walking and is never released; audit marks ground_grasp only after walking, hiding reversed physical order.')
s=initial();a=Audit(copy.deepcopy(s));walk(a,s)
s.update(grasped=True,hand_contact=True,floor_contact=False,cube_bottom=.1);advance(a,s,30)
s['cube'][0]+=.2;advance(a,s)
s.update(grasped=False,hand_contact=True,table_contact=True,inside_table=False,cube_bottom=.54)
advance(a,s,25)
s.update(inside_table=True,hand_contact=False,cube_bottom=.63);advance(a,s,110)
add('table_side_contact_keeps_transport_credit',a,False,'After carry, loss of grasp with cube below tabletop but table contact preserves transport; later pushed placement can pass. Synthetic table_contact represents side contact, not tabletop support.')
s=initial();a=Audit(copy.deepcopy(s));walk(a,s)
s.update(grasped=True,hand_contact=True,floor_contact=False,cube_bottom=.1);advance(a,s,30)
s['cube'][0]+=.2;advance(a,s)
s.update(grasped=False,hand_contact=False,table_contact=False,inside_table=True,cube_bottom=.63);advance(a,s,110)
add('floating_above_table_is_rejected',a,False,'Without table contact, apparent tabletop position cannot pass.')
class Dummy: pass
m=Dummy();m.opt=Dummy();m.opt.timestep=.004;m.opt.gravity=np.array([0.,0.,-9.81])
fields=('body_pos','body_quat','body_mass','body_inertia','geom_pos','geom_quat','geom_size','geom_friction','geom_contype','geom_conaffinity','jnt_type','jnt_range','dof_damping','dof_frictionloss','dof_armature','eq_data','eq_active0','actuator_gear','actuator_gainprm','actuator_biasprm','pair_friction','pair_solref','pair_solimp')
for k in fields:setattr(m,k,np.zeros(1))
m.geom_solref=np.array([[.02,1.]]);m.body_gravcomp=np.array([0.])
digest=ns['model_digest'];before=digest(m);m.geom_solref[:]=[.002,1.];m.body_gravcomp[:]=1.
out['model_digest_probe']={'changed_fields':['geom_solref','body_gravcomp'],'hash_unchanged':before==digest(m),'method':'attribute stub for field-coverage check, no physical effect tested'}
Path('logic_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'existing_tests':out['existing_tests'],'probes':[{k:v for k,v in x.items() if k!='actual'}|{'actual_overall_success':x['actual']['overall_success']} for x in out['probes']],'model_digest_probe':out['model_digest_probe']},ensure_ascii=False,indent=2))
