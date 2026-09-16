"""H001 bounded correction: frozen physics, restricted public tools, persistent actor."""
import os
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = ROOT / 'human-feedback/reproductions/H001'
SOURCE = ROOT / 'artifacts/R019/apple-campaign/episode-0003'
LAUNCHER = ROOT / 'codex-account-2/run.sh'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE/'host_audit/runtime'))

def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        p = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1:3]
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
            isinstance(flags, int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and p != Path('/dev/null') and OUT not in p.parents:
            raise PermissionError('H001 write root: '+str(p))
        if not writing and p.name in ('api.json', 'auth.json', 'credentials.json'):
            raise PermissionError('Engineer process cannot read credentials')
    if event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'):
        for v in args[:2] if event == 'os.rename' else args[:1]:
            if isinstance(v, (str, bytes)):
                p = Path(os.fsdecode(v)).resolve()
                if p != OUT and OUT not in p.parents:
                    raise PermissionError('H001 mutation root: '+str(p))

sys.addaudithook(guard)
import ast
import base64
import datetime
import hashlib
import json
import math
import shutil
import time
import traceback
import importlib.metadata
import numpy as np
from scipy.spatial.transform import Rotation
from rsi.tool_host import LocoManipToolHost
from rsi.simple_recording import simple_video, named_render_state
from rsi.simple_hand_geometry import finger_geometry
from rsi.policy_harness import tool_specs, _object
from rsi.evaluator import SimpleNativeEvaluator
from rsi.codex_app_server import CodexPolicyAdapter
from rsi.stdio_transport import StdioAppServer
from rsi.scalebfm import MODEL, MODEL_SHA256
import rsi.simple_environment as environment
environment.ROOT = ROOT

def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=lambda x:
        x.tolist() if isinstance(x, (np.ndarray, np.generic)) else str(x)))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def status(phase, **kwargs):
    old = json.loads((OUT/'status.json').read_text())
    old.update(phase=phase, updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **kwargs)
    dump(OUT/'status.json', old)
    print(json.dumps({'phase':phase, **kwargs}, ensure_ascii=False), flush=True)

def decision(problem, goal, error):
    text = f'当前问题：{problem}\n总目标：{goal}\n不可重犯：{error}\n'
    with (OUT/'DECISIONS.md').open('a') as f: f.write('\n'+text)
    print(text, flush=True)

def public_only(value):
    if isinstance(value, dict):
        return {k:public_only(v) for k,v in value.items() if k not in (
            'native_outcome','native_task_success','native_task_reward','reward',
            'host_render_state','external_robot_contacts_host_only')}
    if isinstance(value, list): return [public_only(x) for x in value]
    return value

def prepare_sources():
    """Only original public RGB/proprio and explicit recorded action reasons."""
    public = OUT/'public/sources/original'
    if public.exists(): return
    for step in range(66):
        src = SOURCE/f'rollout/episode/observations/{step:04d}'
        dest = public/f'observations/{step:04d}';dest.mkdir(parents=True)
        obs = public_only(json.loads((src/'observation.json').read_text()))
        for im in obs['images']:
            p = src/Path(im['path']).name
            shutil.copyfile(p, dest/p.name);im['path'] = str(dest/p.name)
        dump(dest/'observation.json', obs)
    provenance=[]
    for p in (OUT/'public/sources').rglob('*'):
        if p.is_file():provenance.append({'public_path':str(p),'sha256':sha(p)})
    dump(OUT/'host_audit/public_source_manifest.json',provenance)

class PublicHost:
    method = 'direct'
    def __init__(self, number):
        self.number=number;self.directory=OUT/f'trial-{number:03d}'
        self.public=self.directory/'public';self.audit=OUT/f'host_audit/trial-{number:03d}'
        self.directory.mkdir(exist_ok=False);self.public.mkdir();self.audit.mkdir(parents=True)
        self.calls=self.actions=0;self.finished=False;self.report=None;self.declaration=None
        self.packet=None;self.start_sim_s=None;self.prefix_end=None
        self.enclosure=None;self.closure_attempted=False
        self.action_boundaries=[];self.stop_reason=None
        self.host=LocoManipToolHost(self.public/'rollout', self.factory,
            evaluator_factory=SimpleNativeEvaluator,
            image_capture_factory=lambda b:simple_video(b,self.audit/'video',
                label=f'H001 correction {number} | HUMAN FEEDBACK | FIXED PREFIX | NON-RTC'))

    def factory(self):
        b=environment.create_native_task_backend('simple/G1WholebodyPickAndPlaceAppleTeleop-v0',seed=3,settle_ticks=250)
        self.start_sim_s=float(b.data.time)
        dump(self.audit/'initial_state.json',{'named_state':named_render_state(b),
            'qvel':b.data.qvel,'policy_history':b.adapter.policy_history,
            'action_history':b.adapter.action_history,'scene_setup':b.scene_setup})
        return b

    def augment(self,packet):
        if 'observation' in packet:
            packet['observation']['finger_geometry']=finger_geometry(self.host.backend)
            dump(packet['observation_path'],packet['observation'])
        return packet

    def initialize(self):
        task=json.loads((OUT/'public/sources/original-task.json').read_text())['task']
        packet=self.host.dispatch('loco_start',{'task':task,'output_dir':str(self.public/'rollout/episode')})
        if self.host.initialization_error:raise RuntimeError(str(self.host.initialization_error))
        self.augment(packet)
        dump(self.public/'rollout/episode/tool_result.json',public_only(packet))
        original_actions=json.loads((OUT/'public/sources/original-actions.json').read_text())
        baseline_initial=json.loads((BASE/'attempt-002/rollout/episode/observations/0000/observation.json').read_text())
        self.prefix_comparisons=[self.compare_public(0,packet['observation'],baseline_initial)]
        for row in original_actions[:59]:
            action=row['action'];out=self.public/f'rollout/prefix-{action:04d}'
            packet=self.host.dispatch('scalebfm_act',{'observation_path':str(self.host.harness.latest_path),
                'response':row['response'],'output_dir':str(out)})
            self.augment(packet);dump(out/'tool_result.json',public_only(packet))
            old=json.loads((BASE/f'attempt-002/rollout/episode/observations/{action:04d}/observation.json').read_text())
            self.prefix_comparisons.append(self.compare_public(action,packet['observation'],old))
            if action%10==0 or action==59:status('rebuilding_fixed_prefix',trial=self.number,old_action=action,new_actions=0)
            if self.host.backend.reason:raise RuntimeError('Prefix safety stop: '+str(self.host.backend.reason))
        self.prefix_end=float(self.host.backend.data.time)
        dump(self.audit/'prefix_comparison.json',self.prefix_comparisons)
        if any(r['max_robot_error']>1e-8 or r['time_error_s']>1e-8 for r in self.prefix_comparisons):
            raise RuntimeError('Prefix robot state mismatch; do not claim controlled intervention')
        self.packet=public_only(packet)
        self.packet.update(self.flags())
        self.packet['public_sources']=str(OUT/'public/sources')
        dump(self.public/'initial_actor_packet.json',self.packet)
        status('actor_ready',trial=self.number,old_action=59,new_actions=0,
               prefix_sim_s=self.prefix_end,remaining_physics_s=self.remaining(),prefix_robot_match=True,
               prefix59_image_hash_match=self.prefix_comparisons[-1]['image_hash_match'])

    def compare_public(self,step,new,old):
        vals=[]
        for key in ('joint_position_rad','finger_position_rad'):
            vals.append(float(np.max(np.abs(np.asarray(new[key])-np.asarray(old[key])))))
        for name,p in new['four_point_world'].items():
            vals.append(float(np.max(np.abs(np.asarray(p['position_world_m'])-np.asarray(old['four_point_world'][name]['position_world_m'])))))
        images={}
        for desc in new['images']:
            name=Path(desc['path']).name
            images[name]=sha(desc['path'])==sha(BASE/f'attempt-002/rollout/episode/observations/{step:04d}'/name)
        return {'action':step,'max_robot_error':max(vals),'time_error_s':abs(new['sim_s']-old['sim_s']),'image_hash_match':images}

    def remaining(self):return max(0.,240.-(float(self.host.backend.data.time)-self.start_sim_s))
    def next_call(self):
        return {'tool':'scalebfm_act','observation_path':str(self.host.harness.latest_path),
                'output_dir':str(self.public/f'rollout/new-{self.calls:04d}')}
    def flags(self):
        return {'rollout_finished':self.finished,'new_actions':self.actions,
            'remaining_physics_s':self.remaining(),'physical_budget_including_prefix_s':240,
            'human_feedback_used':True,'human_demonstration_used':False,
            'next_call':self.next_call(),'non_RTC':True}

    def tool_specs(self):
        s={'type':'string'};n={'type':'integer'}
        specs=[x for x in tool_specs('direct') if x['name']!='loco_start']
        for spec in specs:
            if spec['name']=='scalebfm_act':spec['description']='Execute one new four-point waypoint, returning current public RGB and named robot state. Host reward/outcome unavailable.'
        extras=[
            ('current_observation','Read the current RGB/robot packet without advancing physics.',{}),
            ('evidence_read','Read a listed public file, original action/observation, or your own record. Directories list available children. PNG returns image.',{'path':s,'start_line':n,'max_lines':n}),
            ('calculate','Pure numerical Python expression using np, Rotation, math; no files, imports or simulator. Returns numerical result.',{'expression':s}),
            ('declare_test','Before first new action declare one grasp-method-conditioned test from current visible hand; no numerical action recipe is supplied.',{
                'current_problem':s,'overall_goal':s,'never_repeat':s,'grasp_candidate':{'type':'string','enum':['side','top_down']},
                'one_main_change':s,'visible_evidence':s,'uncertainty':s,'predicted_observable':s,'comparison_to_previous':s}),
            ('save_note','Append your concise public evidence/working memory without physical action.',{'note':s}),
            ('enclosure_check','H001-004: record your visible enclosure judgment before increasing closure. A declaration is not host confirmation.',{
                'observation_path':s,'grasp_candidate':{'type':'string','enum':['side','top_down']},
                'enclosure_established':{'type':'boolean'},'visible_evidence':s,'remaining_uncertainty':s}),
            ('finish_trial','After at least three new actions, record observed success/hold or stall. No reward is returned; submit an evidence-based candidate, not a global skill edit.',{
                'observed_result':s,'visible_retained_lift':{'type':'boolean'},'evidence_paths':{'type':'array','items':s},
                'candidate_rule':s,'applicable_when':s,'not_applicable_when':s,'next_test':s})]
        return specs+[{'type':'function','name':name,'description':desc,'inputSchema':_object(props)} for name,desc,props in extras]

    def allowed_path(self,value):
        p=Path(value).resolve()
        roots=[OUT/'public/sources',self.public]
        roots += [OUT/f'trial-{i:03d}/public' for i in range(1,self.number)]
        if not any(p==r or r in p.parents for r in roots):raise ValueError('Only public evidence is readable')
        return p

    def dispatch(self,name,args):
        if name=='current_observation':return self.packet|self.flags()
        if name=='evidence_read':
            p=self.allowed_path(args['path'])
            if p.is_dir():return {'path':str(p),'children':[str(x) for x in sorted(p.iterdir())]}
            if p.suffix=='.png':return {'images':[{'path':str(p)}]}
            if p.suffix not in ('.json','.jsonl','.md','.txt'):raise ValueError('Unsupported public file type')
            lines=p.read_text().splitlines();start=max(0,args['start_line']-1);count=max(1,min(400,args['max_lines']))
            return {'path':str(p),'total_lines':len(lines),'start_line':start+1,'text':'\n'.join(lines[start:start+count])}
        if name=='calculate':
            text=args['expression'];tree=ast.parse(text,mode='eval')
            allowed_attrs={'array','asarray','linalg','norm','inv','pinv','solve','lstsq','svd','cross','dot','stack','vstack','hstack','column_stack','concatenate','mean','min','max','sum','sqrt','sin','cos','tan','arctan','arctan2','arcsin','arccos','deg2rad','rad2deg','pi','eye','zeros','ones','reshape','T','transpose','tolist','from_quat','from_rotvec','from_matrix','as_matrix','as_quat','as_rotvec','apply','radians','degrees','atan2','acos','asin','clip','abs','arange','diag'}
            for node in ast.walk(tree):
                if isinstance(node,(ast.Lambda,ast.NamedExpr,ast.comprehension)):raise ValueError('Only pure numerical expressions')
                if isinstance(node,ast.Name) and node.id not in {'np','Rotation','math','abs','min','max','sum','len','float','int','round','list'}:raise ValueError('Unknown numerical name')
                if isinstance(node,ast.Attribute) and node.attr not in allowed_attrs:raise ValueError('Numerical attribute not allowed')
            value=eval(compile(tree,'<public numerical analysis>','eval'),{'__builtins__':{},'np':np,'Rotation':Rotation,'math':math,
                'abs':abs,'min':min,'max':max,'sum':sum,'len':len,'float':float,'int':int,'round':round,'list':list},{})
            return {'value':json.loads(json.dumps(value,default=lambda x:x.tolist()))}
        if name=='declare_test':
            if self.actions:raise ValueError('Test frozen after first new physical action')
            if args['grasp_candidate'] not in ('side','top_down'):raise ValueError('Specify side or top_down')
            if any(not str(v).strip() for v in args.values()):raise ValueError('All declaration fields required')
            self.declaration=args;dump(self.public/'test_declaration.json',args)
            decision(args['current_problem'],args['overall_goal'],args['never_repeat'])
            return {'test_recorded':True,**self.flags()}
        if name=='save_note':
            with (self.public/'NOTES.md').open('a') as f:f.write(args['note']+'\n')
            return {'saved':True}
        if name=='enclosure_check':
            if args['observation_path']!=str(self.host.harness.latest_path):raise ValueError('Use latest observation')
            if not self.declaration or args['grasp_candidate']!=self.declaration['grasp_candidate']:raise ValueError('Use declared grasp method')
            if not args['visible_evidence'].strip():raise ValueError('Visible evidence is required')
            self.enclosure=args
            with (self.public/'enclosure_checks.jsonl').open('a') as f:f.write(json.dumps(args,ensure_ascii=False)+'\n')
            return {'recorded':True,'host_verified_enclosure':False,**self.flags()}
        if name=='finish_trial':
            if self.actions<3:raise ValueError('Need at least three new physical actions')
            if not self.finished and not self.closure_attempted and self.remaining()>0:
                raise ValueError('No closure/lift interaction yet: when safe continue open-hand evidence acquisition to physical budget; three actions alone do not justify ending')
            rule=args['candidate_rule']
            if len(rule)>6250 or len(rule.split())>831:raise ValueError('Candidate exceeds short-skill cap')
            for p in args['evidence_paths']:
                if not self.allowed_path(p).is_file():raise ValueError('Evidence file does not exist')
            self.finished=True;self.report=args
            self.stop_reason=self.stop_reason or 'actor_declared_trial_end'
            dump(self.public/'actor_report.json',args)
            dump(OUT/f'candidates/trial-{self.number:03d}.json',dict(args,status='candidate_not_published',
                words=len(rule.split()),characters=len(rule),human_feedback_used=True))
            return {'report_saved':True,**self.flags()}
        if self.finished:raise ValueError('Physical trial finished; submit finish_trial')
        if name not in self.host.allowed or name=='loco_start':raise ValueError('Tool unavailable')
        if name=='scalebfm_act':
            if self.declaration is None:raise ValueError('Read current images and declare_test first')
            if len(args.get('response',{}).get('trajectory',[]))!=1:raise ValueError('One waypoint then reobserve')
            reason=args['response'].get('reason','')
            if not all(s in reason for s in ('当前问题','总目标','不可重犯')):raise ValueError('Three public lines required in action reason')
            grips=args['response']['trajectory'][0]['grippers']
            increasing=any(grips[s]>self.host.backend.grips[s]+1e-8 for s in ('left','right'))
            if increasing and (not self.enclosure or not self.enclosure['enclosure_established'] or
                    self.enclosure['observation_path']!=str(self.host.harness.latest_path)):
                raise ValueError('H001-004: before increased closure record established visual enclosure at latest observation; unresolved enclosure requires open-hand adjustment/observation, not closure probe')
        before=float(self.host.backend.data.time)
        packet=self.host.dispatch(name,args);self.augment(packet);self.calls+=1
        if name=='scalebfm_act':
            self.actions+=1
            if increasing:self.closure_attempted=True
            native=self.host.harness.evaluator.outcome(self.host.backend)
            self.action_boundaries.append({'new_action':self.actions,'before_sim_s':before,'after_sim_s':float(self.host.backend.data.time),
                'observation_path':packet['observation_path'],'response':args['response'],'native_outcome':native})
            dump(self.audit/'action_boundaries.json',self.action_boundaries)
            if native in ('success','failure'):self.stop_reason='host_episode_end';self.finished=True
            if self.remaining()<=0:self.stop_reason='physical_budget';self.finished=True
            if self.host.backend.reason:self.stop_reason='robot_safety_stop';self.finished=True
            with (self.public/'history.jsonl').open('a') as f:
                f.write(json.dumps({'tool':name,'arguments':args,'observation_path':packet['observation_path'],
                    'execution':packet.get('execution'),'new_action':self.actions},ensure_ascii=False)+'\n')
            status('actor_closed_loop',trial=self.number,new_actions=self.actions,
                sim_s=float(self.host.backend.data.time),remaining_physics_s=self.remaining(),
                tracking_status=self.host.backend.status().get('status'),rollout_finished=self.finished)
        packet=public_only(packet);packet.update(self.flags())
        dump(Path(args['output_dir'])/'tool_result.json',packet)
        if 'observation' in packet:self.packet=packet
        return packet

class RestrictedAdapter(CodexPolicyAdapter):
    """Existing persistent transport; disable unrestricted native reads/execution."""
    def connect(self):
        self.transport.request('initialize',{'clientInfo':{'name':'H001-correction','version':'1'},
            'capabilities':{'experimentalApi':True}},self.timeout)
        self.transport.notify('initialized',{})
        params={'cwd':str(self.workspace),'model':self.model,'modelProvider':'openai',
            'config':{'model_reasoning_effort':'xhigh','features.shell_tool':False,
                'features.unified_exec':False,'features.view_image':False,'features.multi_agent':False,
                'features.memories':False,'web_search':'disabled'},
            'developerInstructions':self.developer_instructions,'dynamicTools':self.host.tool_specs(),
            'ephemeral':True,'allowProviderModelFallback':False,'approvalPolicy':'never',
            'approvalsReviewer':'auto_review','runtimeWorkspaceRoots':[str(self.workspace)]}
        reply=self.transport.request('thread/start',params,self.timeout)
        if reply.get('model')!='gpt-6-astra' or reply.get('reasoningEffort')!='xhigh':
            raise RuntimeError('Exact Astra/xhigh unavailable; no fallback')
        self.thread_id=reply['thread']['id'];return reply

def main(number):
    assert 1<=number<=3
    # Explicitly re-read latest instructions before every new physical trial.
    updates={p.name:sha(p) for p in [ROOT/'AGENTS.md',ROOT/'ref/USER_UPDATE_20260916_PARALLEL_SKILLS.md',
        ROOT/'ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md']}
    for p in updates:
        q=ROOT/p if p=='AGENTS.md' else ROOT/'ref'/p
        q.read_text()
    if not os.access(LAUNCHER,os.X_OK):raise RuntimeError('Second-account launcher unavailable')
    assert sha(MODEL)==MODEL_SHA256
    skill=(OUT/'SKILL.md').read_text()
    assert len(skill.split())<=831 and len(skill)<=6250
    if number>1:
        previous=json.loads((OUT/f'trial-{number-1:03d}/result.json').read_text())
        if previous.get('error'):raise RuntimeError('Previous model/technical error requires explicit diagnosis before another trial')
    prepare_sources()
    host=PublicHost(number);transport=None;adapter=None;error=None
    dump(host.audit/'version.json',{'instruction_hashes':updates,'backend':'SIMPLE / MuJoCo',
        'model38000_sha256':sha(MODEL),'baseline_manifest_sha256':sha(BASE/'BASELINE_FROZEN.json'),
        'frozen_runtime_sha256':{str(p.relative_to(BASE/'host_audit/runtime')):sha(p) for p in (BASE/'host_audit/runtime').rglob('*.py')},
        'runner_sha256':sha(__file__),'skill_sha256':sha(OUT/'SKILL.md'),
        'packages':{p:importlib.metadata.version(p) for p in ('mujoco','numpy','onnxruntime','gymnasium')},
        'reset':'native seed=3 + checkpoint posture + 250 tracker ticks + original actions 1-59',
        'physics_dt_s':.005,'tracker_dt_s':.02,'physical_episode_budget_s':240,
        'inference_timeout':None,'action_tracking_timeout':'duration + 2s',
        'original_dependency_history_incomplete':True,'control_version_changed':False})
    decision(f'第{number}次独立reset纠正实验；读取最新约束并重建前缀',
             '冻结控制合同，检验抓法条件化包夹判断；新动作由Astra选择',
             '旧重放不计尝试；隐藏评估不给actor；推理等待不限时')
    try:
        status('resetting',trial=number,attempts_started=number,actor_thread_id=None,new_actions=0)
        host.initialize()
        agent=host.public/'actor';agent.mkdir();(agent/'SKILL.md').write_text(skill)
        transport=StdioAppServer([str(LAUNCHER),'app-server','--stdio'],host.audit/'app_server')
        adapter=RestrictedAdapter(transport,host,agent,developer_instructions=skill,normal_tools=False)
        reply=adapter.connect();dump(host.audit/'model_connection.json',reply)
        status('awaiting_astra',trial=number,actor_thread_id=adapter.thread_id,new_actions=0,
            account_route='second_account_run_sh',inference_timeout=None)
        prompt=('本次是H001人工反馈辅助受控诊断，第'+str(number)+'次独立reset。'
            '固定前缀已完成；不要loco_start或重置。先读current_observation及公开来源。'
            '原任务、短skill、自己原动作和四条人类原话均在 '+str(OUT/'public/sources')+'. '
            '最新004：侧抓包络未确认时保持张手，不能以试闭合绕过前置条件；读004后通过enclosure_check公开判断再增加闭合。'
            '先基于可见手姿声明侧抓或顶抓，再一次检验一个主要判断变化。'
            '所有数值目标由你从公开观测选择，工程师未提供动作配方。'
            '原记录240秒预算包含前缀，当前剩余'+str(round(host.remaining(),3))+'秒物理时间，推理不限时。'
            '原始任务保持；本诊断重点验证纠正后的抓持和独立保持。'
            'finish_trial保存候选和结果，不向用户求助。')
        if number>1:prompt+='前次公开尝试和候选在 '+str(OUT/f'trial-{number-1:03d}/public')+'；必须依据结果改进一个主要检验，或对已可见成功做独立复验。'
        while host.report is None:
            turn=adapter.run_turn(prompt)
            dump(host.audit/f'turn-{adapter.turns_started:03d}.json',turn)
            prompt='已自然完成上一模型turn；物理尝试尚未提交报告。依据现有公开记录继续同一持久线程，调用finish_trial完成记录。不得新reset。'
    except Exception as exc:
        error=f'{type(exc).__name__}: {exc}';traceback.print_exc()
        status('stopped_model_or_technical_error',trial=number,error=error,
            automatic_retry=False,usage_limit_exceeded='usageLimitExceeded' in error)
    finally:
        if host.host:
            try:host.host.close()
            except Exception as exc:error=(error or '')+' close: '+repr(exc)
        if transport:transport.close()
        result={'trial':number,'new_physical_actions':host.actions,'error':error,
            'stop_reason':host.stop_reason,'actor_report':host.report,'prefix_end_sim_s':host.prefix_end,
            'final_sim_s':float(host.host.backend.data.time) if host.host.backend else None,
            'thread_id':adapter.thread_id if adapter else None,'model':'gpt-6-astra','effort':'xhigh',
            'launcher':str(LAUNCHER),'paid_api_calls':0,'human_feedback_used':True,
            'human_demonstration_used':False,'formal_campaign_success_credit':False,
            'trial_kind':'fixed_original_prefix_human_feedback_assisted_diagnostic',
            'native_outcome_host_only':host.host.harness.evaluator.outcome(host.host.backend) if host.host.harness else None,
            'video':str(host.audit/'video/episode.mp4'),'host_evaluation':'pending',
            'non_RTC':True,'independent_native_reset':True}
        result['feedback_versions_used']=['001','002','003','004']
        dump(host.directory/'result.json',result)
        status('trial_complete_audit_pending' if not error else 'stopped_model_or_technical_error',
            trial=number,attempts_completed=number if host.actions else number-1,new_actions=host.actions,error=error)
    return int(error is not None)

if __name__=='__main__':sys.exit(main(int(sys.argv[1])))
