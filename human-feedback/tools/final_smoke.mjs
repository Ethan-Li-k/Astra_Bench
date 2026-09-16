import fs from 'node:fs';
const root='/home/galbot/lizekai/RSI/human-feedback';
const port=fs.readFileSync(root+'/reviews/browser-profile/DevToolsActivePort','utf8').split('\n')[0];
const target=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(x=>x.type==='page');
const ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let seq=0;const callbacks=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id){const cb=callbacks.get(m.id);callbacks.delete(m.id);m.error?cb.reject(Error(JSON.stringify(m.error))):cb.resolve(m.result);}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;callbacks.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
const ev=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
await call('Page.navigate',{url:'http://127.0.0.1:8765/'});
for(let i=0;i<100;i++){if(await ev("!!document.querySelector('#gate')&&document.images[0]?.complete"))break;await new Promise(r=>setTimeout(r,100));}
const checks={
 default_production_form_blank:await ev("['observation','priority','gate'].every(k=>document.getElementById(k).value==='')"),
 default_step_59:await ev("document.querySelector('#frame-title').textContent.includes('59')"),
 default_large_left_image:await ev("document.images.length===1&&document.images[0].naturalWidth===640&&document.images[0].clientWidth>900"),
 prior_exposure_control:await ev("document.querySelector('#prior-exposure').value==='unknown'"),
 all_16_original_images_decode:await ev("(async()=>{const d=await(await fetch('/api/case')).json();const ok=await Promise.all(d.case.frames.flatMap(f=>f.images).map(im=>new Promise(resolve=>{const img=new Image();img.onload=()=>resolve(img.naturalWidth===640&&img.naturalHeight===360);img.onerror=()=>resolve(false);img.src='/evidence/'+im.file})));return ok.length===16&&ok.every(Boolean)})()")
};
await ev("document.querySelector('#eye').value='head_stereo_right';document.querySelector('#eye').dispatchEvent(new Event('change'))");
checks.right_eye_switch=await ev("document.images[0].alt.includes('head_stereo_right')");
await ev("document.querySelector('#eye').value='both';document.querySelector('#eye').dispatchEvent(new Event('change'))");
checks.stereo_switch=await ev('document.images.length===2');
await ev("document.querySelector('#eye').value='head_stereo_left';document.querySelector('#eye').dispatchEvent(new Event('change'))");
fs.writeFileSync(root+'/reviews/tests/browser-final-production.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
checks.mobile_no_horizontal_overflow=await ev('document.documentElement.scrollWidth<=window.innerWidth');
fs.writeFileSync(root+'/reviews/tests/browser-mobile.png',Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
const health=await(await fetch('http://127.0.0.1:8765/api/health')).json();
checks.live_server_evidence_valid=health.evidence_valid===true;
const before=JSON.parse(fs.readFileSync(root+'/reviews/tests/production-before-browser-final.json','utf8'));
const crypto=await import('node:crypto');
checks.production_records_unchanged=Object.entries(before).every(([p,h])=>crypto.createHash('sha256').update(fs.readFileSync('/home/galbot/lizekai/RSI/'+p)).digest('hex')===h);
if(!Object.values(checks).every(Boolean))throw Error(JSON.stringify(checks));
const result={at:new Date().toISOString(),checks,passed:Object.keys(checks).length,health,production_submissions_in_this_test:0};
fs.writeFileSync(root+'/reviews/tests/final-smoke.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
await call('Browser.close');ws.close();
