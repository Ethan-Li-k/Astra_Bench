import fs from 'node:fs';
const base='/home/galbot/lizekai/RSI/human-feedback/dashboard-upgrade',out=base+'/ikea-label-fix';
const port=fs.readFileSync(base+'/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
let seq=0;const pending=new Map(),errors=[],passed=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const run=code=>ev('(async()=>{'+code+'})()');
const check=(ok,name)=>{if(!ok)throw Error(name);passed.push(name);};
async function until(expression){for(let i=0;i<150;i++){if(await ev(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error(expression);}
try{
 await call('Page.enable');await call('Runtime.enable');await call('Runtime.discardConsoleEntries');errors.length=0;
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1080,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'http://127.0.0.1:8765/#ikea'});
 await until("document.querySelector('#task-title')?.textContent==='IKEA探索' && document.querySelector('#player').readyState>=2");
 check(await ev("document.querySelector('#video-caption').textContent.includes('策略尝试（未完成）') && document.querySelector('#video-caption').textContent.includes('12动作') && document.querySelector('#video-caption').textContent.includes('宿主记录错误中断') && document.querySelector('#video-caption').textContent.includes('未审计成功') && !document.querySelector('#video-caption').textContent.includes('工程诊断')"),'production_policy_incomplete_caption_correct');
 check(await ev("document.querySelector('#context').textContent.includes('不等同原始 USD 场景完整物理验证') && !document.querySelector('#context').textContent.includes('原始带锁舌') && !document.querySelector('#context').textContent.includes('原始无锁舌')"),'original_usd_latch_not_asserted');
 check(await ev("document.querySelector('#video-note').textContent.includes('不代表任务成功或回合完整完成') && document.querySelector('#summary').textContent.includes('审计成功 0')"),'sealed_video_does_not_increase_success');
 await run("window.playerBefore=document.querySelector('#player');window.srcBefore=playerBefore.currentSrc;playerBefore.muted=true;await playerBefore.play()");
 await until('playerBefore.currentTime>1');await ev('playerBefore.currentTime=10');await until('!playerBefore.seeking && playerBefore.currentTime>=10');
 check(true,'actual_policy_video_play_and_seek');
 await ev("window.timeBefore=playerBefore.currentTime;lastVideo={...lastVideo,task:'旧文字缓存测试',outcome:'待刷新'};videoCaption();");
 await until("playerBefore.currentTime>timeBefore+5 && document.querySelector('#video-caption').textContent.includes('策略尝试（未完成）')");
 check(await ev("playerBefore===document.querySelector('#player') && playerBefore.currentSrc===srcBefore && !playerBefore.paused"),'same_url_metadata_corrects_on_poll_without_playback_reset');
 check(await ev("document.querySelector('#answer-form') && document.querySelectorAll('#lanes button').length===4"),'existing_progress_and_feedback_form_preserved');
 const iframeResponse=await fetch('http://127.0.0.1:8765/videos/ikea-door-v1-001.mp4',{headers:{Range:'bytes=64-127'}});
 check(iframeResponse.status===206&&(await iframeResponse.arrayBuffer()).byteLength===64,'existing_diagnostic_video_range_preserved');
 await ev('playerBefore.pause()');
 fs.writeFileSync(out+'/production-ikea.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 check(errors.length===0,'no_browser_runtime_errors');
 const report={at:new Date().toISOString(),passed,errors,feedback_submissions:0,model_calls:0};fs.writeFileSync(out+'/browser-results.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}catch(e){fs.writeFileSync(out+'/browser-failure.json',JSON.stringify({passed,errors,error:String(e)},null,2));throw e;}finally{await call('Browser.close');ws.close();}
