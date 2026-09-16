import fs from 'node:fs';
import path from 'node:path';
import https from 'node:https';
import crypto from 'node:crypto';

const root='/home/galbot/lizekai/RSI/api-ground-to-table';
const out=path.join(root,'api/calibration-001');
fs.mkdirSync(out,{recursive:true});
// Exclusive creation prevents an uncertain request from being resent.
fs.closeSync(fs.openSync(path.join(out,'dispatch.lock'),'wx',0o600));
const config=JSON.parse(fs.readFileSync('/home/galbot/lizekai/RSI/api.json','utf8'));
const url=new URL(config.BASE_URL);
if(url.protocol!=='https:'||url.hostname!=='llm-gateway.galbot.com'||url.username||url.password||url.search)throw Error('Unexpected gateway configuration');
const base=url.pathname.replace(/\/+$/,'');
url.pathname=base+(base.endsWith('/v1')?'/responses':'/v1/responses');
const caseRoot=path.join(root,'cases/F001');
const prompt=fs.readFileSync(path.join(caseRoot,'api-review-prompt.txt'),'utf8');
const imagePaths=[0,1].flatMap(n=>['head_cam','right_wrist_cam'].map(c=>path.join(caseRoot,`public/observation_000${n}/${c}.png`)));
const payload={model:'gpt-6-astra',reasoning:{effort:'xhigh'},store:false,stream:true,max_output_tokens:16384,
  input:[{role:'user',content:[{type:'input_text',text:prompt},...imagePaths.map(p=>({type:'input_image',image_url:'data:image/png;base64,'+fs.readFileSync(p).toString('base64')}))]}]};
const record={request_id:crypto.randomUUID(),started_at:new Date().toISOString(),provider:url.origin,model:payload.model,reasoning_effort:'xhigh',generation_requests:1,max_output_tokens:payload.max_output_tokens,input_images:imagePaths.map(p=>({path:p,sha256:crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')})),prompt_sha256:crypto.createHash('sha256').update(prompt).digest('hex'),cost_cny:null,cost_status:'unsettled_user_authorized_calibration',authorization:'User explicitly requested first use, then price-difference feedback and estimation. Single request; no automatic retry or ongoing paid loop.',state:'dispatching'};
const save=()=>fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(record,null,2));
save();
console.log(JSON.stringify({state:record.state,request_id:record.request_id,started_at:record.started_at}));
const body=JSON.stringify(payload);
let text='',buffer='',terminal=false;
function event(data){
  if(!data||data==='[DONE]')return;
  let e;try{e=JSON.parse(data)}catch{return;}
  if(e.type==='response.output_text.delta')text+=e.delta||'';
  if(e.type==='response.created')record.response_id=e.response?.id;
  if(['response.completed','response.incomplete','response.failed'].includes(e.type)){
    terminal=true;const r=e.response||{};
    record.state=e.type;record.usage=r.usage;record.returned_model=r.model;record.returned_reasoning=r.reasoning;
    record.incomplete_details=r.incomplete_details;record.error=r.error?{code:r.error.code,message:String(r.error.message).replaceAll(config.API_KEY,'[REDACTED]')}:null;
    if(!text)text=(r.output||[]).flatMap(x=>x.content||[]).filter(x=>x.type==='output_text').map(x=>x.text).join('\n');
  }
  if(e.type==='error'){record.api_error={code:e.code,message:String(e.message).replaceAll(config.API_KEY,'[REDACTED]')};}
}
const request=https.request(url,{method:'POST',headers:{Authorization:'Bearer '+config.API_KEY,'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),'X-Client-Request-Id':record.request_id}},response=>{
  record.http_status=response.statusCode;record.provider_request_id=response.headers['x-request-id'];save();
  response.setEncoding('utf8');
  response.on('data',chunk=>{
    if(response.statusCode!==200){buffer=(buffer+chunk).slice(0,5000);return;}
    buffer+=chunk;let index;
    while((index=buffer.indexOf('\n'))!==-1){const line=buffer.slice(0,index).trimEnd();buffer=buffer.slice(index+1);if(line.startsWith('data:'))event(line.slice(5).trim());}
  });
  response.on('end',()=>{
    if(buffer.startsWith('data:'))event(buffer.slice(5).trim());
    if(response.statusCode!==200){record.state='http_error_no_retry';record.error_body=buffer.replaceAll(config.API_KEY,'[REDACTED]');}
    else if(!terminal)record.state='result_unknown_no_retry';
    record.finished_at=new Date().toISOString();save();
    fs.writeFileSync(path.join(out,'review.txt'),text);
    console.log(JSON.stringify({state:record.state,http_status:record.http_status,usage:record.usage,finished_at:record.finished_at}));
  });
});
request.on('error',e=>{record.state='transport_error_result_unknown_no_retry';record.error={code:e.code,message:e.message};record.finished_at=new Date().toISOString();save();console.log(JSON.stringify({state:record.state,error:record.error}));process.exitCode=1;});
// No inference wall-clock timeout and no SDK/provider fallback or automatic retry.
request.end(body);
