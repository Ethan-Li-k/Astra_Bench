import fs from 'node:fs';
const base='/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade',out=base+'/candidate-delivery-schema';
const port=fs.readFileSync(out+'/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let seq=0;const pending=new Map(),errors=[],passed=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const run=code=>ev('(async()=>{'+code+'})()');
const check=(ok,name)=>{if(!ok)throw Error(name);passed.push(name);};
async function until(expression){for(let i=0;i<150;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error(expression);}
try {
 await call('Page.enable');await call('Runtime.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1080,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'http://127.0.0.1:8765/#framework'});
 await until("document.querySelector('#task-title')?.textContent==='Skill/Harness优化' && document.querySelector('#summary').textContent.includes('候选已交付')");
 const response=await fetch('http://127.0.0.1:8765/api/dashboard');const status=await response.json();const framework=status.tasks.find(t=>t.id==='framework');
 check(response.ok && !status.fixture && framework.current_work.state==='candidate-delivered' && await ev("document.querySelector('#summary').textContent.includes('候选已交付；待发布者审查集成') && document.querySelector('#problem').textContent.includes('候选已完成') && !document.querySelector('#problem').textContent.includes('正在核对') && document.querySelector('#next').textContent.includes('唯一发布者') && document.querySelector('#next').textContent.includes('自然边界')"),'real_schema_delivered_replaces_old_review_problem_and_next');
 check(framework.current_work.deployed===false && framework.current_work.physical_benefit_verified===false && await ev("document.querySelector('#problem').textContent.includes('未部署') && document.querySelector('#problem').textContent.includes('物理收益未验证') && document.querySelector('#milestones').textContent.includes('交接已排队；负责人尚未确认')"),'candidate_queued_is_not_ack_deployment_or_physical_verification');
 const before=JSON.parse(fs.readFileSync(out+'/production-before.json','utf8'));
 check(JSON.stringify(framework.nt_publication)===JSON.stringify(before.nt_publication) && await ev("document.querySelector('#phase').textContent==='续接审计已发布；门19已加载；真实断线恢复尚未验证'"),'nt_publication_loading_and_physical_network_status_unchanged');
 fs.writeFileSync(out+'/production-framework.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 fs.writeFileSync(out+'/production-framework.json',JSON.stringify(framework,null,2));
 const report={at:new Date().toISOString(),url:'http://127.0.0.1:8765/#framework',passed,errors,screenshot:'production-framework.png',feedback_submissions:0,queue_messages:0,model_api_calls:0};
 fs.writeFileSync(out+'/browser-results.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(e){fs.writeFileSync(out+'/browser-failure.json',JSON.stringify({passed,errors,error:String(e)},null,2));throw e;}finally{await call('Browser.close');ws.close();}
