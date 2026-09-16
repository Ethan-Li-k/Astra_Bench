"""Archive actual public inputs and check host-field separation without model calls."""
from pathlib import Path
import hashlib
import json
import sys
from collections import Counter

OUT=Path(__file__).resolve().parent
FORBIDDEN={'native_outcome','native_task_success','native_task_reward','reward','host_render_state','external_robot_contacts_host_only'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bad_keys(x,path='$'):
    result=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if k in FORBIDDEN:result.append(path+'.'+k)
            result+=bad_keys(v,path+'.'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x):result+=bad_keys(v,path+f'[{i}]')
    return result

def main(n):
    public=OUT/f'trial-{n:03d}/public';audit=OUT/f'host_audit/trial-{n:03d}'
    violations=[]
    for p in public.rglob('*.json'):
        for k in bad_keys(json.loads(p.read_text())):violations.append({'file':str(p),'key':k})
    inputs=[];counts=Counter();waits=[];validation_errors=[]
    for p in sorted((public/'actor/rpc_calls').glob('*request.json')):
        request=json.loads(p.read_text());args=request['arguments'];counts[request['tool']]+=1
        if isinstance(args,str):args=json.loads(args)
        response=p.with_name(p.name.replace('_request','_result'))
        result=json.loads(response.read_text()) if response.exists() else None
        row={'tool':request['tool'],'request_path':str(p),'request_sha256':sha(p),
            'reply_path':str(response),'reply_sha256':sha(response) if response.exists() else None}
        if request['tool']=='evidence_read':row['requested_public_source']=args['path']
        if result and result.get('no_execution'):
            validation_errors.append({'request':str(p),'tool':request['tool'],'error':result.get('error')})
        if result:
            images=result.get('images',result.get('observation',{}).get('images',[]))
            row['images']=[{'path':im['path'],'sha256':sha(Path(im['path']))} for im in images]
        inputs.append(row)
        timing=p.with_name(p.name.replace('_request','_timing'))
        if timing.exists():waits.append(json.loads(timing.read_text()))
    events=audit/'app_server/rpc_out.jsonl';types=Counter();other=[]
    for line in events.open():
        e=json.loads(line)
        if e.get('method')=='item/completed':
            item=e.get('params',{}).get('item',{});typ=item.get('type');types[typ]+=1
            if typ not in ('agentMessage','reasoning','dynamicToolCall','plan','contextCompaction'):
                other.append({'type':typ,'name':item.get('name'), 'tool':item.get('tool')})
    skill=public/'actor/SKILL.md';text=skill.read_text()
    report={'trial':n,'forbidden_public_key_violations':violations,
        'actual_dynamic_tool_inputs':inputs,'tool_counts':dict(counts),
        'validation_errors_no_physics':validation_errors,'completed_item_types':dict(types),
        'other_item_types_for_review':other,'actor_skill_sha256':sha(skill),
        'actor_skill_words':len(text.split()),'actor_skill_characters':len(text),
        'policy_wait_sum_wall_s':sum(x['policy_wait_wall_s'] for x in waits),
        'policy_wait_max_wall_s':max([x['policy_wait_wall_s'] for x in waits],default=0),
        'tool_wall_sum_s':sum(x['tool_wall_s'] for x in waits),
        'timing_note':'Inference/analysis waiting is wall time while physics is paused; action tracker timeout and physical budget are separate.',
        'paid_api_calls_from_engineer':0,'declared_model':'gpt-6-astra','declared_effort':'xhigh',
        'launcher':'/home/galbot/lizekai/RSI/codex-account-2/run.sh'}
    (audit/'actor_input_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('actual_dynamic_tool_inputs','validation_errors_no_physics')},ensure_ascii=False))
    assert not violations
    assert len(text.split())<=831 and len(text)<=6250

if __name__=='__main__':main(int(sys.argv[1]))
