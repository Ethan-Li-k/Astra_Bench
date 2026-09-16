'use strict';
const $=id=>document.getElementById(id);
let index;
let apiSignature, refreshing=false, lastAPI=null;
const knownVideos=new Set();
const show=value=>value===null||value===undefined?'未知 / 未提供':String(value);
function addVideo(v){
  if(knownVideos.has(v.id))return;
  knownVideos.add(v.id);
  const b=document.createElement('button');b.type='button';b.dataset.id=v.id;
  const title=document.createElement('strong'),meta=document.createElement('span');title.textContent=v.title;meta.textContent=`${v.duration_s.toFixed(2)} 秒 · ${v.kind.includes('baseline')?'基线 / 非新成功':'完整运行记录'}`;
  b.append(title,meta);b.onclick=()=>selectVideo(v.id);$('video-list').append(b);
}
function age(){
  if(!lastAPI)return;
  const t=lastAPI.updated_at_unix;
  $('api-updated').textContent=t===null?'来源更新时间未知':`来源更新：${new Date(t*1000).toLocaleString()} · 已 ${Math.max(0,Math.floor(Date.now()/1000-t))} 秒未观察到更新（不据此判断推理故障）`;
}
async function refreshAPI(){
  if(refreshing||!index)return;refreshing=true;
  try{
    const response=await fetch('/api/ground-progress',{cache:'no-store'});
    if(!response.ok)throw Error('公开进度暂不可读');
    const data=await response.json();lastAPI=data;
    const signature=JSON.stringify([data.run_id,data.episode,data.state,data.task_stage,data.terminal_kind,data.episodes.map(x=>[x.episode,x.terminal_kind])]);
    if(signature!==apiSignature){$('api-change').textContent=`${new Date().toLocaleTimeString()} · ${apiSignature?'阶段 / 回合终态变化':'首次观测'}：${show(data.episode)} · ${data.state_label} · ${data.terminal_label}`;apiSignature=signature;}
    $('api-run').textContent=`Run：${show(data.run_id)} · Episode：${show(data.episode)} · 实际后端：${data.backend}`;
    $('api-state').textContent=`当前阶段：${data.state_label} · ${data.task_stage} · 物理暂停：${data.physics_paused===null?'未知 / 已终止':data.physics_paused?'是':'否'}`;
    $('api-counts').textContent=`API 已完成：${show(data.api_calls_completed)} · 真实动作：${show(data.actions)} · 物理秒：${data.physical_s===null?'未知 / 未提供':data.physical_s.toFixed(2)}`;
    $('api-terminal').textContent=`实际终态分类：${data.terminal_label}`;
    $('api-error').textContent=data.source_error||'';age();
    $('api-episodes').replaceChildren();
    for(const row of data.episodes){const p=document.createElement('p');p.textContent=`${row.episode} · ${row.terminal_label} · API ${show(row.api_calls_completed)} / 动作 ${show(row.actions)} · ${row.video_status}`;$('api-episodes').append(p);}
    $('api-sources').replaceChildren();
    const refs=[...data.sources,...data.episodes.filter(x=>x.source).map(x=>x.source)];
    if(data.public_history)refs.push(data.public_history);
    for(const ref of refs){const p=document.createElement('p');p.className='caption';p.textContent=`${ref.source} · SHA256 ${ref.sha256}${ref.entries===undefined?'':` · 公开经验索引 ${ref.entries} 条（不代表成功经验）`}`;$('api-sources').append(p);}
    for(const v of data.videos){const existing=index.videos.findIndex(x=>x.id===v.id);if(existing>=0)index.videos[existing]=v;else index.videos.push(v);addVideo(v);}
    // Revoke unavailable choices without touching the current player or its src.
    for(const b of $('video-list').querySelectorAll('button'))if(b.dataset.id.startsWith('api-ground-'))b.disabled=!data.videos.some(v=>v.id===b.dataset.id);
  }catch(e){$('api-error').textContent='进度读取错误；保留上次观测，无法据此判断机器人状态。';}
  finally{refreshing=false;}
}
function selectVideo(id){
  const v=index.videos.find(x=>x.id===id);if(!v)return;
  $('video-title').textContent=v.title;$('player').src=v.url;
  $('dimensions').textContent=`${v.duration_s.toFixed(2)} 秒 · ${v.width} × ${v.height} · ${v.fps||25} fps · 可拖动进度条跳转`;
  for(const [element,key] of [['result-note','result_note'],['view','view'],['timing','timing'],['source','source'],['provenance','provenance_basis']])$(element).textContent=v[key];
  $('hash').textContent='SHA256 '+v.sha256;$('direct-video').href=v.url;
  for(const button of $('video-list').querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.id===id));
  history.replaceState(null,'','#'+id);$('message').textContent='';
}
async function init(){
  const response=await fetch('/api/progress');index=await response.json();if(!response.ok)throw Error(index.error);
  for(const v of index.videos)addVideo(v);
  $('h001-progress').textContent=index.h001_progress.summary;
  $('selected-warning').textContent=index.selected_frame_warning;
  for(const reply of index.feedback.H001.replies){const q=document.createElement('blockquote'),caption=document.createElement('p');q.textContent=reply.verbatim;caption.className='caption';caption.textContent=reply.question_id;$('h001-quotes').append(caption,q);}
  $('h001-receipt').href=index.feedback.H001.receipt_url;$('h001-receipt').textContent='已导入 · '+index.feedback.H001.annotation_id;
  $('f001-quote').textContent=index.feedback.F001.verbatim;$('f001-source').textContent=`保留来源：${index.feedback.F001.source} · human_proposed，未据此声明已掌握行走或抓取。`;
  await refreshAPI();
  const requested=location.hash.slice(1);selectVideo(index.videos.some(v=>v.id===requested)?requested:index.videos[0].id);
  setInterval(refreshAPI,10000);setInterval(age,1000);
}
$('player').addEventListener('error',()=>{$('message').textContent='视频未加载，请查看来源是否仍可用；不会以静止帧序列代替。';});
init().catch(e=>{$('message').textContent='只读进展暂不可用：'+e.message;});
