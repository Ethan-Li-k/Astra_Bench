// CDP smoke test using the same installed Chrome/Node pipeline as video_browser_check.mjs.
import fs from 'node:fs';
const out='/home/galbot/lizekai/RSI/api-ground-to-table/progress-ui-verification';
const base='http://127.0.0.1:8765';
const port=fs.readFileSync(out+'/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);
await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let seq=0;const pending=new Map(),tests=[],errors=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const run=code=>ev('(async()=>{'+code+'})()');
const assert=(ok,label)=>{if(!ok)throw Error(label);tests.push(label);};
async function until(expression){for(let i=0;i<180;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('browser condition: '+expression);}
try{
  await call('Page.enable');await call('Runtime.enable');await call('Network.enable');
  await call('Fetch.enable',{patterns:[{urlPattern:'*'}]});
  ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Fetch.requestPaused'){const p=m.params,ok=p.request.url.startsWith(base+'/');call(ok?'Fetch.continueRequest':'Fetch.failRequest',ok?{requestId:p.requestId}:{requestId:p.requestId,errorReason:'BlockedByClient'}).catch(()=>{});}});
  await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:base+'/#api-ground-episode-0001'});
  await until("document.querySelector('#player')?.readyState>=2 && document.querySelector('#api-run').textContent.includes('api-ground')");
  assert(await ev("!document.querySelector('form,textarea,input') && document.querySelector('#help-state').textContent.includes('人工求助关闭')"),'original_read_only_and_closed_status');
  assert(await ev("document.querySelector('#player').currentSrc.endsWith('/videos/api-ground-episode-0001.mp4')"),'sealed_first_episode_playable');
  assert(await ev("document.querySelector('#result-note').textContent.includes('预算截断') && document.querySelector('#result-note').textContent.includes('未验证')"),'budget_cutoff_not_physical_failure');
  await ev("window.savedPlayer=document.querySelector('#player');window.realFetch=window.fetch;window.apiReads=0;window.fetch=(...args)=>{if(args[0]==='/api/ground-progress')window.apiReads++;return window.realFetch(...args)};savedPlayer.currentTime=0;savedPlayer.muted=true;savedPlayer.play()");
  await until("window.apiReads>=1 && window.savedPlayer.currentTime>1");
  assert(await ev("savedPlayer===document.querySelector('#player') && !savedPlayer.paused && savedPlayer.currentTime>1"),'ten_second_auto_refresh_preserves_playing_video_node');
  await run("savedPlayer.pause();window.sample=await (await realFetch('/api/ground-progress')).json();window.fake=structuredClone(sample);fake.updated_at_unix=Date.now()/1000-7200;fake.state='inference_waiting_no_deadline';fake.state_label='正在推理 · 无推理截止时间';fake.terminal_kind=null;fake.terminal_label='尚无当前回合 result；终态未验证';window.fetch=(...args)=>args[0]==='/api/ground-progress'?Promise.resolve(new Response(JSON.stringify(fake),{status:200})):realFetch(...args);await refreshAPI()");
  assert(await ev("document.querySelector('#api-updated').textContent.includes('7200') && document.querySelector('#api-state').textContent.includes('正在推理')"),'stale_inference_not_marked_failed');
  await run("window.noticeBefore=document.querySelector('#api-change').textContent;fake.api_calls_completed++;await refreshAPI()");
  assert(await ev("noticeBefore===document.querySelector('#api-change').textContent"),'call_count_changes_do_not_notify');
  await run("fake.state='ended';fake.state_label='回合终止';fake.terminal_kind='budget_limited_incomplete';fake.terminal_label='预算截断 · 未完成（不是物理失败）';await refreshAPI()");
  assert(await ev("document.querySelector('#api-change').textContent.includes('阶段 / 回合终态变化') && document.querySelector('#api-terminal').textContent.includes('不是物理失败')"),'terminal_change_visible_notification');
  await run("window.fetch=(...args)=>args[0]==='/api/ground-progress'?Promise.reject(Error('synthetic backend read error')):realFetch(...args);await refreshAPI()");
  assert(await ev("document.querySelector('#api-error').textContent.includes('保留上次观测') && savedPlayer===document.querySelector('#player')"),'read_error_preserves_last_status_and_player');
  await run("window.fetch=realFetch;await refreshAPI()");
  fs.writeFileSync(out+'/desktop.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
  await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  assert(await ev('document.documentElement.scrollWidth<=window.innerWidth'),'mobile_no_horizontal_overflow');
  fs.writeFileSync(out+'/mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
  assert(errors.length===0,'no_browser_runtime_errors');
  const report={at:new Date().toISOString(),passed:tests.length,tests,errors,health:await(await fetch(base+'/api/health')).json(),robot_tasks_started:0,model_calls:0};
  fs.writeFileSync(out+'/browser-results.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{await call('Browser.close');ws.close();}
