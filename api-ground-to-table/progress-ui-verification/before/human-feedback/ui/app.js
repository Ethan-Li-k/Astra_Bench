'use strict';
const $=id=>document.getElementById(id);
let index;
function selectVideo(id){
  const v=index.videos.find(x=>x.id===id);if(!v)return;
  $('video-title').textContent=v.title;$('player').src=v.url;
  $('dimensions').textContent=`${v.duration_s.toFixed(2)} 秒 · ${v.width} × ${v.height} · 25 fps · 可拖动进度条跳转`;
  for(const [element,key] of [['result-note','result_note'],['view','view'],['timing','timing'],['source','source'],['provenance','provenance_basis']])$(element).textContent=v[key];
  $('hash').textContent='SHA256 '+v.sha256;$('direct-video').href=v.url;
  for(const button of $('video-list').querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.id===id));
  history.replaceState(null,'','#'+id);$('message').textContent='';
}
async function init(){
  const response=await fetch('/api/progress');index=await response.json();if(!response.ok)throw Error(index.error);
  for(const v of index.videos){const b=document.createElement('button');b.type='button';b.dataset.id=v.id;
    const title=document.createElement('strong'),meta=document.createElement('span');title.textContent=v.title;meta.textContent=`${v.duration_s.toFixed(2)} 秒 · ${v.kind.includes('baseline')?'基线 / 非新成功':'完整运行记录'}`;
    b.append(title,meta);b.onclick=()=>selectVideo(v.id);$('video-list').append(b);}
  $('h001-progress').textContent=index.h001_progress.summary;
  $('selected-warning').textContent=index.selected_frame_warning;
  for(const reply of index.feedback.H001.replies){const q=document.createElement('blockquote'),caption=document.createElement('p');q.textContent=reply.verbatim;caption.className='caption';caption.textContent=reply.question_id;$('h001-quotes').append(caption,q);}
  $('h001-receipt').href=index.feedback.H001.receipt_url;$('h001-receipt').textContent='已导入 · '+index.feedback.H001.annotation_id;
  $('f001-quote').textContent=index.feedback.F001.verbatim;$('f001-source').textContent=`保留来源：${index.feedback.F001.source} · human_proposed，未据此声明已掌握行走或抓取。`;
  const requested=location.hash.slice(1);selectVideo(index.videos.some(v=>v.id===requested)?requested:index.videos[0].id);
}
$('player').addEventListener('error',()=>{$('message').textContent='视频未加载，请查看来源是否仍可用；不会以静止帧序列代替。';});
init().catch(e=>{$('message').textContent='只读进展暂不可用：'+e.message;});
