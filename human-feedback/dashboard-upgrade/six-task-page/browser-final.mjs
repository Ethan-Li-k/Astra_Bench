import fs from 'node:fs';
const base='/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade',out=base+'/six-task-page';
const port=fs.readFileSync(out+'/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
let ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let seq=0;const pending=new Map(),errors=[],passed=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const run=code=>ev('(async()=>{'+code+'})()');
const check=(ok,name)=>{if(!ok)throw Error(name);passed.push(name);};
async function until(expression){for(let i=0;i<150;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error(expression);}
try {
 await call('Page.enable');await call('Runtime.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1080,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'http://127.0.0.1:8765/simple-six'});await until("document.querySelectorAll('.six-card').length===6");
 check(await ev("!document.querySelector('#phase').textContent.includes('目标已达成')&&[...document.querySelectorAll('.six-card')].every(c=>c.textContent.includes('下一步：'))"),'current_episode_not_completed_by_historical_goal_and_next_step_visible');
 await ev('window.scrollTo(0,0)');
 fs.writeFileSync(out+'/simple-six-desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 check(await ev('document.documentElement.scrollWidth<=document.documentElement.clientWidth'),'final_mobile_layout');
 fs.writeFileSync(out+'/simple-six-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1080,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'http://127.0.0.1:8765/#framework'});await until("document.querySelector('#problem')?.textContent.includes('完整回合审计已报告')");
 check(await ev("document.querySelector('#summary').textContent.includes('首个完整回合受限审计通过')&&document.querySelector('#phase').textContent.includes('真实断线恢复尚未验证')"),'original_page_body_publication_and_nt_distinct');
 fs.writeFileSync(out+'/original-framework.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 const d=await(await fetch('http://127.0.0.1:8765/api/dashboard')).json();
 fs.writeFileSync(out+'/production-public.json',JSON.stringify({at:new Date().toISOString(),tasks:d.tasks,help:d.help},null,2));
 fs.writeFileSync(out+'/browser-final-results.json',JSON.stringify({at:new Date().toISOString(),passed,errors,production_feedback_submissions:0,user_browser_accessed:false},null,2));console.log(JSON.stringify({passed,errors}));
}catch(e){console.error(e);throw e;}finally{await call('Browser.close');ws.close();}
