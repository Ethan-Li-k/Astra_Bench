// Existing Chrome + Node built-ins only. All navigation restricted to loopback.
import fs from 'node:fs';
const root='/home/galbot/lizekai/RSI/human-feedback';
const port=fs.readFileSync(root+'/reviews/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const target=targets.find(t=>t.type==='page');
const ws=new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej;});
let id=0;const callbacks=new Map(), errors=[], urls=[], tests=[];
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const cb=callbacks.get(m.id);callbacks.delete(m.id);m.error?cb.reject(Error(JSON.stringify(m.error))):cb.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);else if(m.method==='Network.requestWillBeSent')urls.push(m.params.request.url);};
function call(method,params={}){return new Promise((resolve,reject)=>{const n=++id;callbacks.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(expression){for(let i=0;i<100;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('timed out: '+expression);}
function assert(value,name){if(!value)throw Error(name);tests.push(name);}
await call('Page.enable');await call('Runtime.enable');await call('Network.enable');
await call('Network.setBlockedURLs',{urls:['https://*','http://*']});
// Override broad block with explicit local-only interception, avoiding external requests.
await call('Network.setBlockedURLs',{urls:[]});
await call('Fetch.enable',{patterns:[{urlPattern:'*'}]});
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.method==='Fetch.requestPaused'){const p=m.params;const local=p.request.url.startsWith('http://127.0.0.1:8765/');call(local?'Fetch.continueRequest':'Fetch.failRequest',local?{requestId:p.requestId}:{requestId:p.requestId,errorReason:'BlockedByClient'}).catch(()=>{});}});
await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:'http://127.0.0.1:8765/?synthetic=1'});
await until("document.querySelector('#observation') && [...document.images].every(x=>x.complete&&x.naturalWidth===640)");
assert(await evaluate("document.querySelector('#step').selectedOptions[0].textContent.startsWith('动作 59')"),'default_step59');
assert(await evaluate("['observation','priority','gate','counterexample'].every(k=>document.getElementById(k).value==='')"),'answers_blank');
assert(await evaluate("document.getElementById('assessment').hidden && document.getElementById('next').disabled"),'assessment_and_future_frames_initially_hidden');
assert(await evaluate("[...document.images].every(x=>getComputedStyle(x).objectFit==='contain'&&Math.abs(x.clientWidth/x.clientHeight-640/360)<0.02)"),'uncropped_original_aspect_ratio');
await evaluate("document.querySelector('#eye').value='head_stereo_left';document.querySelector('#eye').dispatchEvent(new Event('change'))");
await until('document.images.length===1&&document.images[0].complete');assert(await evaluate('document.images[0].clientWidth>900'),'large_eye_view');
fs.writeFileSync(root+'/reviews/tests/browser-initial.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
await evaluate("document.querySelector('#prev').click()");assert(await evaluate("document.querySelector('#frame-title').textContent.includes('57')"),'previous_frame_switch');
await evaluate("document.querySelector('#next').click();document.querySelector('#robot-details').open=true");
await until("document.querySelector('#robot').textContent.includes('joint_names')");tests.push('public_robot_state_expansion');
await evaluate("document.querySelector('#observation').value='SYNTHETIC 浏览器测试：不足以判断';document.querySelector('#priority').value='SYNTHETIC 浏览器测试：需要另一视角';document.querySelector('#gate').value='SYNTHETIC 浏览器测试：只有看到测试线索，才继续';document.querySelector('#answers').requestSubmit()");
await until("document.querySelector('#receipts a')&& !document.querySelector('#reveal').hidden");
const firstUrl=await evaluate("document.querySelector('#receipts a').getAttribute('href')");
const record=await (await fetch('http://127.0.0.1:8765'+firstUrl)).json();
assert(record.submission.synthetic===true&&record.submission.exposure.agent_assessment_seen===false,'initial_synthetic_persisted_with_exposure');
assert(fs.existsSync(root+'/annotations/synthetic/'+record.annotation_id+'.json'),'actual_immutable_disk_record');
await evaluate("document.querySelector('#reveal').click();document.querySelector('#next').click()");
assert(await evaluate("!document.querySelector('#assessment').hidden && document.querySelector('#frame-title').textContent.includes('60')"),'explicit_reveal_and_future_frame');
await evaluate("document.querySelector('#comparison').value='SYNTHETIC 对照后补充';document.querySelector('#answers').requestSubmit()");
await until("document.querySelectorAll('#receipts a').length===2");
const secondUrl=await evaluate("document.querySelectorAll('#receipts a')[1].getAttribute('href')");
const comparison=await(await fetch('http://127.0.0.1:8765'+secondUrl)).json();
assert(comparison.submission.parent_annotation_id===record.annotation_id&&comparison.submission.exposure.agent_assessment_seen===true,'comparison_is_separate_linked_record');
fs.writeFileSync(root+'/reviews/tests/browser-saved.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
const meta=await(await fetch('http://127.0.0.1:8765/api/case')).json();
const post=(p,extra={})=>fetch('http://127.0.0.1:8765/api/annotations',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':meta.csrf,...extra},body:JSON.stringify(p)});
const repeat=await(await post(record.submission)).json();assert(repeat.duplicate&&repeat.annotation_id===record.annotation_id,'HTTP_duplicate_is_idempotent');
const empty=structuredClone(record.submission);empty.request_id='synthetic-http-empty';empty.answers.gate='';assert((await post(empty)).status===409,'HTTP_empty_answer_rejected');
assert((await post(record.submission,{'Origin':'http://untrusted.invalid'})).status===409,'cross_origin_rejected');
assert((await post(record.submission,{'X-CSRF-Token':'wrong'})).status===409,'wrong_csrf_rejected');
for(const path of ['/api.json','/evidence/../case.json','/evidence/%2e%2e/%2e%2e/api.json','/api/annotation/../../outside'])assert((await fetch('http://127.0.0.1:8765'+path)).status!==200,'whitelist_rejects_'+path);
assert(errors.length===0,'no_browser_runtime_exception');
assert(urls.every(u=>u.startsWith('http://127.0.0.1:8765/')),'page_requested_only_loopback');
const result={at:new Date().toISOString(),browser:await call('Browser.getVersion'),tests,passed:tests.length,errors,
  synthetic_annotation_ids:[record.annotation_id,comparison.annotation_id],screenshots:['browser-initial.png','browser-saved.png'],
  real_user_submission_created:false,chrome_sandbox_disabled:false,dependencies_installed:false};
fs.writeFileSync(root+'/reviews/tests/browser-results.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));ws.close();
