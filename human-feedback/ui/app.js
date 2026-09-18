'use strict';
const $=id=>document.getElementById(id);
const sixPage=document.body.dataset.view==='simple-six';
const show=x=>x===null||x===undefined?'未知':String(x);
const stamp=x=>x?new Date(x*1000).toLocaleString('zh-CN',{hour12:false}):'未知';
function age(x){if(!x)return'时间未知';const s=Math.max(0,Math.floor(Date.now()/1000-x));return s<60?`${s} 秒前`:s<3600?`${Math.floor(s/60)} 分钟前`:`${(s/3600).toFixed(1)} 小时前`;}
function text(tag,value,cls){const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;}
let formSnapshot=null,draftLocked=false;
let data=null,selected='simple',subtask=null,refreshing=false,pinned=null,caseSelected=null,correction=null,request=null,lastVideo=null,pendingVideo=null,answerSignature='',caseSignature='',historyLoaded=false;
const initialHash=location.hash.slice(1).replace(/-progress$/,'');if(!sixPage&&['simple','ground','ikea','framework'].includes(initialHash))selected=initialHash;
function task(){return data?.tasks.find(t=>t.id===selected);}
function detail(){const t=task();return [...(t?.subtasks||[]),...(t?.history_subtasks||[])].find(x=>x.id===subtask)||t;}
function bindForm(c=null,parent=null){caseSelected=c;correction=parent;request=null;const t=task();if(!t)return;draftLocked=Boolean(c||parent);formSnapshot=structuredClone(t);pinned={task_id:t.id,case_id:c?.case_id||null,source_version:c?.version||t.version};const chosen=[...(t.subtasks||[]),...(t.history_subtasks||[])].find(x=>x.id===subtask);if(!c&&chosen?.native_env_id)pinned.context={subtask_id:chosen.id,native_env_id:chosen.native_env_id};$('form-title').textContent=c?'回答这一个问题':'给此任务补充观察 / 建议';$('form-binding').textContent=`绑定：${t.name}${pinned.context?' / '+chosen.name:''} · ${c?.case_id||'主动补充'} · 证据 ${pinned.source_version.slice(0,10)}（开始输入后证据固定于此版本）`;$('choice').replaceChildren(new Option('不选择，直接写观察',''));for(const x of c?.choices||[])$('choice').append(new Option(x,x));$('choice').hidden=!c;$('choice').previousElementSibling.hidden=!c;$('cancel-case').hidden=!c&&!parent;$('correction-label').textContent=parent?`本条纠正此前回答 ${parent.slice(0,11)}…，旧原话保留。`:'';$('submit-status').textContent='';}
function selectTask(id){if(id===selected&&pinned)return;draftLocked=false;formSnapshot=null;selected=id;subtask=null;lastVideo=null;pendingVideo=null;caseSignature='';answerSignature='';history.replaceState(null,'','#'+id);$('answer').value='';render();bindForm();}
function renderLanes(){
 for(const t of data.tasks){let b=$('lanes').querySelector(`[data-task="${t.id}"]`);if(!b){b=document.createElement('button');b.className='lane';b.type='button';b.dataset.task=t.id;b.onclick=()=>selectTask(t.id);b.append(text('strong',''),text('span','','badge'),text('small',''),text('small',''));$('lanes').append(b);}b.setAttribute('aria-pressed',String(t.id===selected));b.children[0].textContent=t.name;b.children[1].textContent=t.state_label;b.children[1].dataset.state=t.state;b.children[2].textContent=t.summary;b.children[3].textContent=`最近${t.last_action_at?'动作':'证据'}：${age(t.last_action_at||t.source_at)}`;
 }
}
function loadVideo(v){pendingVideo=null;$('load-latest').hidden=true;lastVideo=v||null;const player=$('player');if(v){if(player.getAttribute('src')!==v.url)player.src=v.url;player.hidden=false;$('video-link').href=v.url;$('video-link').hidden=false;}else{player.pause();player.removeAttribute('src');player.load();player.hidden=true;$('video-link').hidden=true;}videoCaption();}
function videoCaption(){const v=lastVideo;$('video-caption').textContent=v?`${v.task||task()?.name} · ${v.episode||v.title} · ${v.duration_s.toFixed(1)} 秒 · ${stamp(v.at)}（${age(v.at)}${v.at&&Date.now()/1000-v.at>300?'，录像较旧':''}）${v.outcome?' · '+v.outcome:''}`:'暂无可播放的已完成录像';$('video-view').textContent=v?`${v.view} ${v.timing||''}`:'';}
function renderSubtasks(nav,rows){for(const row of rows){let b=nav.querySelector(`[data-subtask="${row.id}"]`);if(!b){b=document.createElement('button');b.type='button';b.dataset.subtask=row.id;b.onclick=()=>{subtask=row.id;lastVideo=null;if(sixPage&&!draftLocked)bindForm();render();};nav.append(b);}b.textContent=row.nav_label||`${row.name} ${show(row.success)}/${show(row.goal)}`;b.setAttribute('aria-pressed',String(row.id===subtask));}for(const b of [...nav.children])if(!rows.some(x=>x.id===b.dataset.subtask))b.remove();}
function render(){if(!data)return;if(pinned&&!draftLocked&&!caseSelected&&!correction&&!request)bindForm();renderLanes();const t=task();if(!t)return;if(![...(t.subtasks||[]),...(t.history_subtasks||[])].some(x=>x.id===subtask))subtask=t.subtasks?.[0]?.id||null;const d=detail();if(!d)return;$('task-title').textContent=t.name;$('phase').textContent=d.state_label;$('phase').dataset.state=d.state;
 renderSubtasks($('subtasks'),t.subtasks||[]);renderSubtasks($('history-subtasks'),t.history_subtasks||[]);$('task-history').hidden=!t.history_subtasks?.length;$('scope-note').hidden=!t.scope_notice;$('scope-note').textContent=t.scope_notice||'';
 const old=d.historical_status;$('prior-status').hidden=!old;$('prior-status-body').replaceChildren(...(old?[text('p',`暂停前记录 · ${old.episode||'回合未上报'} · ${old.state_label||'阶段未知'}`),text('p',old.problem||'原卡点未上报'),text('p','当时的下一步：'+(old.next||'未上报')),text('p','原来源时间：'+stamp(old.source_at))]:[]));
 $('prerequisite').textContent=(draftLocked&&formSnapshot?formSnapshot:t).prerequisite_note||'';$('recovery-note').textContent=d.recovery_note||'';$('delivery-note').textContent=t.delivery_note||'';$('delivery-note').hidden=!t.delivery_note;
 $('summary').textContent=d.summary||`${d.name}：审计成功 ${show(d.success)} / ${show(d.goal)} · ${d.episode||'暂无回合'} · 公开动作 ${show(d.actions)}`;
 $('problem').textContent=d.problem;$('next').textContent=d.next;$('who').textContent=d.who;$('last-action').textContent=d.last_action_at?`最近实际动作证据：${stamp(d.last_action_at)} · ${age(d.last_action_at)}`:'最近实际动作：未提供可核验记录；准备或心跳不计物理执行';
 $('source-age').textContent=`来源更新：${stamp(d.source_at)} · ${age(d.source_at)}${d.source_at&&Date.now()/1000-d.source_at>300?' · 来源已陈旧；不能据此判断停止':''}${t.supervisor_at?' · 管理汇总 '+age(t.supervisor_at):''}${d.source_time_note?' · '+d.source_time_note:''}${d.heartbeat_at?' · 心跳 '+age(d.heartbeat_at)+'（不是动作证据）':''}`;$('source-age').className=d.source_at&&Date.now()/1000-d.source_at>300?'stale':'';
 $('context').textContent=`${d.backend} · ${d.mode} · ${d.variant}`;$('milestones').replaceChildren(...(d.milestones||[]).map(x=>text('p',`${x.name}：${x.state}`,'fine')));
 if(t.id==='framework'){const a=text('a','Harness：闭环、真实工具接口、参数与角色说明 ↗');a.href='/harness';a.target='_blank';a.rel='noopener';$('milestones').append(a,text('p','源码核验与当前回合加载分开；参数只读，物理和视觉来源分别确认。','fine'));}
 const p=d.preview;if(p){if($('preview').getAttribute('src')!==p.url)$('preview').src=p.url;$('preview').hidden=false;$('preview-empty').hidden=true;$('preview-caption').textContent=`${p.view} · ${p.episode} / 动作 ${p.action} · ${stamp(p.at)}（${age(p.at)}${p.at&&Date.now()/1000-p.at>300?'，画面已陈旧':''}） · ${p.time_basis}`;}else{$('preview').hidden=true;$('preview-caption').textContent='';$('preview-empty').hidden=false;$('preview-empty').textContent='尚无实时公开画面。显示的进展来自公开状态文件，不以静态资产预览代替当前运行。';}
 const v=d.videos?.[0];if(!lastVideo)loadVideo(v);else if(v&&v.url===lastVideo.url)lastVideo=v;else if(v&&v.url!==lastVideo.url){if($('player').paused||$('player').ended)loadVideo(v);else{pendingVideo=v;$('load-latest').hidden=false;}}$('video-note').textContent=d.video_note||'';videoCaption();
 $('sources').replaceChildren(...(d.sources||[]).map(s=>text('p',`${s.path} · ${stamp(s.at)} · SHA256 ${s.sha256}`)));
 renderCoverage(data.simple_coverage,t);renderProgressClip(d);renderCases();renderAnswers();if(!pinned)bindForm();if(sixPage&&window.renderSimpleSix)window.renderSimpleSix(t,data,subtask,chooseSix);
}
function sixCases(){const ids=new Set(task()?.subtasks?.flatMap(t=>t.scorecard?.records.map(r=>'simple/'+r.campaign+'/'+r.episode)||[])||[]);return data.help.cases.filter(c=>c.task_id==='simple'&&c.attempts.every(a=>ids.has(a.record_id)));}
function chooseSix(id,focus=false){subtask=id;lastVideo=null;if(!draftLocked)bindForm();render();if(focus)$('detail').scrollIntoView({behavior:'smooth'});}
function renderCases(){const all=sixPage?sixCases():data.help.cases.filter(c=>c.task_id===selected);const sig=JSON.stringify(all);$('help-status').textContent=all.length?`${all.length} 个待你回答的问题 · 最新 ${stamp(data.help.latest_case_at)} · 等待用户判断。`:`当前没有符合门槛的新求助题。${data.help.reason}`;if(sig===caseSignature)return;caseSignature=sig;$('cases').replaceChildren();for(const c of all){const el=text('div','','case');el.append(text('h3',c.title),text('p',`${c.mechanism} · 控制版本 ${c.control_version}`),text('p','已尝试：'+c.already_tried),text('p','观察事实：'+c.facts),text('p','待检验假设：'+c.hypothesis));for(const a of c.attempts){const box=document.createElement('details');box.append(text('summary',a.record_id+' · 独立 reset '+a.reset_id));const v=document.createElement('video');v.controls=true;v.preload='none';v.src=a.video_url;v.setAttribute('aria-label','失败轨迹连续录像');const image=document.createElement('img');image.src=a.keyframe_url;image.alt='该失败轨迹的公开关键帧';box.append(text('p',`变化：${a.change}；结果：${a.outcome}；关键时间 ${a.timestamps.join('、')} 秒`),v,image);el.append(box);}el.append(text('p',c.question));const b=text('button','回答此问题');b.type='button';b.onclick=()=>{bindForm(c);$('answer').focus();};el.append(b);$('cases').append(el);}}
function renderAnswers(){const rows=data.answers.filter(x=>x.submission.task_id===selected);const sig=JSON.stringify(rows);if(sig===answerSignature)return;answerSignature=sig;$('answers').replaceChildren();if(!rows.length){$('answers').append(text('p','此任务尚无网页新增回答。历史 H001 / F001 在下方保留。','fine'));return;}for(const a of rows.slice().reverse()){const el=text('div','','answer-item'),s=a.submission;el.append(text('small',`${a.kind==='requested_case'?'问题回答':'主动补充'} · ${new Date(a.saved_at).toLocaleString()}${s.correction_of?' · 纠正旧回答':''}`),text('blockquote',(s.choice?s.choice+'\n':'')+s.text));const st=a.status;el.append(text('p',`已保存 → ${st.handoff==='authorized_owner_inbox'?'最高优先级 · 已交接统一API主管':st.main_account_inbox?'最高优先级 · 已进入主账号待办':st.queued?'已排队':st.fixture?'测试隔离，不排队':st.delivery_uncertain?'投递未确认，保留待核，不自动重试':'最高优先级 · 本地已交接，待消费'} → ${st.owner_ack?'执行者已确认':'待执行者确认'} → ${st.adoption?st.adoption.state==='adopted'?'已采纳，待实际使用/验证':'未采纳（保留原话）':'采纳未上报'} → ${st.actual_loaded?'实际加载已核验':'实际加载待核验'} → ${st.physical_verified?'已报告物理验证（结果另记）':'生效待物理验证'}`,'answer-status'));if(st.evidence_binding?.state==='unverified')el.append(text('p','原话已保存；证据绑定待核查：'+st.evidence_binding.reason,'notice'));if(st.coordination){el.append(text('p',(st.coordination.priority==='highest'?'最高优先级 · ':'')+(st.coordination.stage==='implemented'?'规则已实现':'已接收，正在落实')+'：'+st.coordination.note+'；实际回合使用与物理验证另记。','notice'));}else if(st.attention_required){el.append(text('p','反馈已保存，但超过5分钟没有处理回执；这是执行流程待处理，不是拒绝你的意见。','notice'));}const b=text('button','补充 / 纠正此条');b.type='button';b.onclick=()=>{bindForm(null,a.feedback_id);$('answer').focus();};el.append(b);$('answers').append(el);}}
async function refresh(){if(refreshing)return;refreshing=true;try{const r=await fetch('/api/dashboard',{cache:'no-store'});if(!r.ok)throw Error('读取失败');data=await r.json();$('fixture-warning').hidden=!data.fixture;$('connection').textContent='公开证据已连接 · 每 5 秒更新';$('refreshed').textContent='浏览器读取：'+new Date().toLocaleTimeString('zh-CN');$('global-note').textContent=data.notice;$('error').textContent='';render();}catch(e){$('connection').textContent='连接暂不可用';$('error').textContent='读取失败；保留上次证据和正在播放的视频，无法据此判断机器人停止。';}finally{refreshing=false;}}
for(const id of ['answer','choice'])$(id).addEventListener('input',()=>{if(!draftLocked){formSnapshot=structuredClone(task());draftLocked=true;$('form-binding').textContent+=' · 正在回答：反馈引用已固定，最新画面继续更新';}});
$('answer-form').addEventListener('submit',async e=>{e.preventDefault();if(!pinned||!data)return;if(!$('answer').value.trim()&&!$('choice').value){$('submit-status').textContent='请写下观察或选择答案。';return;}const payload={...pinned,request_id:request?.request_id||crypto.randomUUID(),text:$('answer').value,choice:$('choice').value,user_timestamp:request?.user_timestamp||new Date().toISOString(),correction_of:correction};if(request&&JSON.stringify(request)!==JSON.stringify(payload)){payload.request_id=crypto.randomUUID();payload.user_timestamp=new Date().toISOString();}request=payload;$('submit').disabled=true;try{const r=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':data.csrf},body:JSON.stringify(payload)});const result=await r.json();if(!r.ok)throw Error(result.error);$('answer').value='';request=null;await refresh();bindForm();$('submit-status').textContent=`已保存原话 ${result.feedback_id.slice(0,11)}…。${data.fixture?'测试隔离，不排队。':'投递状态见下方；执行者尚未确认。'}`;}catch(err){$('submit-status').textContent='未确认保存：'+err.message+' 原文已保留，可重试同一提交。';}finally{$('submit').disabled=false;}});
$('cancel-case').onclick=()=>bindForm();$('load-latest').onclick=()=>loadVideo(pendingVideo);$('refresh').onclick=refresh;
$('player').addEventListener('error',()=>{$('video-caption').textContent='视频加载失败；请查看来源与封口状态。';});
async function loadHistory(){if(historyLoaded)return;try{const r=await fetch('/api/progress');const h=await r.json();for(const reply of h.feedback.H001.replies)$('historical-feedback').append(text('blockquote',reply.verbatim));$('historical-feedback').append(text('blockquote','F001：'+h.feedback.F001.verbatim));for(const v of h.videos){const a=text('a',v.title);a.href=v.url;a.target='_blank';a.rel='noopener';$('historical-videos').append(a);}historyLoaded=true;}catch(e){$('historical-feedback').textContent='历史资料暂不可读，原文件仍保留。';}}
refresh();loadHistory();setInterval(refresh,5000);
window.addEventListener('hashchange',()=>{const id=location.hash.slice(1).replace(/-progress$/,'');if(!sixPage&&data&&data.tasks.some(t=>t.id===id))selectTask(id);});

let currentClip=null,nextClip=null,clipTask=null;
function renderProgressClip(d){
 const v=d.progress_clip,player=$('progress-clip');$('progress-clip-panel').hidden=!d.native_env_id;
 if(clipTask!==d.id){player.pause();player.removeAttribute('src');player.load();player.hidden=true;currentClip=null;nextClip=null;clipTask=d.id;}
 function load(v){player.src=v.url;player.hidden=false;currentClip=v;nextClip=null;$('clip-latest').hidden=true;}
 if(v?.url&&!currentClip)load(v);else if(v?.url&&currentClip?.url!==v.url){if(player.paused||player.ended)load(v);else{nextClip=v;$('clip-latest').hidden=false;}}
 player.onended=()=>{if(nextClip)load(nextClip);};
 $('clip-latest').onclick=()=>{if(nextClip)load(nextClip);renderProgressClip(d);};
 $('clip-status').textContent=v?(v.pending?'新公开帧已到；编码/发布等待。 ':'')+(v.note||''):'当前暂无可用片段；最新公开单帧和已封口连续录像分别保留。';
 $('clip-caption').textContent=currentClip?`${currentClip.label} · ${currentClip.episode} · 动作 ${currentClip.first_action}–${currentClip.last_action} · ${currentClip.camera} · 源 ${stamp(currentClip.source_at)}（${age(currentClip.source_at)}）`:'非连续片段不能用作三次失败求助所需的连续视频证据。';
 const i=d.episode_interface;if(i)$('context').textContent+=` · 观测 ${i.observation_id||'未上报'} · 相机 ${i.cameras.map(c=>c.camera+' / '+(c.version||'版本未报')).join('、')||'未上报'} · 控制 ${i.control_source||'未上报'} · runtime ${i.runtime_sha256?.slice(0,12)||'未上报'}`;
}

// Named HTML controls supplement native media controls without changing the source.
function syncClipPlaybackControl(){const v=$('progress-clip'),b=$('clip-play-toggle');b.disabled=!v.getAttribute('src')||v.readyState<1;b.textContent=v.paused||v.ended?'播放公开观测片段':'暂停公开观测片段';}
$('clip-play-toggle').onclick=async()=>{const v=$('progress-clip');$('clip-play-status').textContent='';try{if(v.paused||v.ended)await v.play();else v.pause();}catch(e){$('clip-play-status').textContent='暂未开始播放，可重试。'+e.name;}syncClipPlaybackControl();};
for(const event of ['loadedmetadata','canplay','play','pause','ended','emptied','error'])$('progress-clip').addEventListener(event,syncClipPlaybackControl);

function renderCoverage(c,t){
 const root=$('coverage-overview');if(!root)return;
 root.hidden=!c?.active||t.id!=='simple';if(root.hidden)return;
 if(!$('coverage-environments')){const lanes=text('div','');lanes.id='coverage-environments';const summary=text('div','');summary.id='coverage-summary';root.replaceChildren(lanes,summary);}
 renderParallelEnvironments(c.environments||[]);
 const panel=$('coverage-summary');
 const sig=JSON.stringify([c.mainline,c.goal,c.window_metrics,c.actual_parallel,c.parallel_target,c.live_workers,c.paused_workers,c.count_status,c.reported_lanes,c.source_at,c.completed,c.next,c.deferred,c.untriaged,c.psi_amo,c.preflights,c.pending_audit,c.active_environments]);
 if(panel.dataset.signature===sig)return;panel.dataset.signature=sig;panel.replaceChildren();
 if(c.mainline){
  panel.append(text('h2','固定主线：相似任务训练 → 六项 Isaac 测试'));
  panel.append(text('p','原60×5覆盖计划已撤销。已有成功任务只提取经验，不再重复采集。','lead'));
  panel.append(text('p',c.mainline.closeout_status||'等待停止派发回执','notice'));
  panel.append(text('p','固定测试项：'+c.mainline.tests.map(r=>r.label).join('、')+'。'));
  panel.append(text('p',c.mainline.training_status+'；'+c.mainline.test_status+'。','fine'));
  if(c.mainline.selected_training?.length){const list=text('ul','');for(const r of c.mainline.selected_training)list.append(text('li',`${r.label} → ${r.similar_to.join('、')} · 至少 ${r.minimum_complete_attempts} 次完整尝试`));panel.append(list);}
  panel.append(text('p',c.new_mainline_execution?`新主线：${c.live_workers??'待回执'} 路存活进程；${c.actual_parallel??'待回执'} 路已有动作回执；完整尝试 ${c.mainline.training_counts?.complete_attempts??'待核验'} / 20。`:`旧计划：${c.active_environments??0} 个待收尾回合；存活进程 ${c.live_workers??'待回执'}。`,'fine'));
  panel.append(text('p',`历史经验保留：${c.completed_tasks} 类任务/变体，${c.audited_successes} 次审计成功。`,'fine'));
  panel.append(text('p','测试前固定技能与记忆版本、控制器参数、初始条件、随机化级别、相机和完成判据；物理后端与图像来源分别说明。','fine'));
  const link=text('a','主线流程、训练清单与经验调用');link.href='http://127.0.0.1:8766/';link.target='_blank';link.rel='noopener';panel.append(link);
  if(c.mainline.schedule){const s=c.mainline.schedule;panel.append(text('h3','50回合 · 并行时间安排'));for(const p of s.summary||[])panel.append(text('p',p,'fine'));const rows=text('ul','');for(const r of s.scenarios||[])rows.append(text('li',`${r.label}：${r.duration}。${r.condition}`));panel.append(rows);panel.append(text('p','条件估算，非截止时间。首两完整回合后校正；Isaac接入与渲染等待另计，原始成功任务不重试。','fine'));}
  return;
 }
 if(c.goal){
  const g=c.goal,m=c.window_metrics;
  panel.append(text('h2',`24小时 · ${g.target_tasks}项任务 × 每项${g.minimum_complete_attempts_per_task}次完整尝试`));
  panel.append(text('p',`窗口：${stamp(g.started_at)} 至 ${stamp(g.deadline_at)}；API 优先 · ${g.model} / ${g.effort}`,'fine'));
  panel.append(text('p',m?`已完整尝试 ${m.complete_attempts} / ${g.target_complete_attempts} 次 · 已覆盖 ${m.attempted_tasks} / ${g.target_tasks} 项 · 满五次 ${m.tasks_at_least_five} 项`:'完整尝试 / 覆盖任务 / 满五次：等待统一主管回执，尚未核验不补零。','lead'));
  panel.append(text('p',`当前调度槽位 ${c.parallel_target??g.initial_parallel_target}；已有动作回执的存活环境 ${c.actual_parallel??'待回执'}；存活执行进程 ${c.live_workers??'待回执'}（其中暂停 ${c.paused_workers??'待回执'}）。本页 ${c.active_environments??0} 个未封口回合另计，不能替代进程存活回执。`,'fine'));
  panel.append(text('p',(c.count_status||'')+(c.source_at?` · 主管更新 ${stamp(c.source_at)}（${age(c.source_at)}）`:''),'fine'));
  if(c.reported_lanes?.length){const list=text('ul','');for(const l of c.reported_lanes)list.append(text('li',`${l.task_key||l.env_id||'未分配'} · ${l.route||'路线待确认'} · ${l.state||'状态待确认'} · 已回执动作 ${l.actions??'未知'}`));panel.append(list);}
  panel.append(text('p',`历史经验：${c.completed_tasks} 类成功任务/变体、${c.audited_successes} 次审计成功；不抵扣本窗口五次。`,'fine'));
  panel.append(text('p','完整尝试须有独立重置、真实动作、明确任务终态与封存证据；准备、系统中断、未知请求和任意截断另列。','fine'));
  const link=text('a','打开统一流程图、任务矩阵与经验调用');link.href='http://127.0.0.1:8766/';link.target='_blank';link.rel='noopener';panel.append(link);
  return;
 }
 panel.append(text('h2','简单任务优先 · 成功一次就换下一项'),text('p',`已完成 ${c.completed_tasks} 类任务/学习变体 · ${c.pending_audit??0} 个终态待审计 · ${c.active_environments??0} 个独立环境未封口 · 累计 ${c.audited_successes} 次审计成功。已成功项退出重试，正式测评暂停。`,'lead'),text('p',c.inventory_note,'fine'));
 const add=(title,items,fmt,open)=>{const box=text('details','');box.open=open;box.append(text('summary',title+' · '+items.length));const list=text('ul','');for(const r of items){const li=text('li',fmt(r));if(r.detail_id){const b=text('button',r.video?'播放成功录像':'查看证据');b.type='button';b.onclick=()=>{chooseSix(r.detail_id,true);if(r.video)loadVideo(r.video);};li.append(document.createTextNode(' '),b);}list.append(li);}box.append(list);panel.append(box);};
 add('尚无回合证据 · 等待启动',c.next.filter(r=>!(c.environments||[]).some(e=>e.native_env_id===r.env_id)),r=>r.label+' — '+r.reuse+'；'+(c.preflights?.some(p=>p.env_id===r.env_id)?'7 秒站立预检通过；':'')+(r.state==='ready'?'已准入，等待真实启动证据':'任务准入准备'),true);
 add('已成功 · 不再重试',c.completed,r=>r.label+'：'+r.successes+' 次；'+r.scope,true);
 add('暂缓 · 本轮不攻难点',c.deferred,r=>r.env_id.replace('simple/G1Wholebody','')+'：'+r.reason,false);
 add('其余入口 · 待筛选简单项',c.untriaged,r=>r.replace('simple/G1Wholebody',''),false);
 panel.append(text('p','Ψ／AMO：'+(c.psi_amo.independently_verified?'已核实成功配置，按实际运行回执显示进展。':'用户报告已有成功方案；具体配置待核对，不用旧失败候选代替。'),'fine'));
}


function renderParallelEnvironments(rows){
 const root=$('coverage-environments');
 if(!root.firstChild){root.append(text('h2','并行独立环境 · 每 5 秒读取证据'));const grid=text('div','');grid.className='parallel-grid';root.append(grid);}
 const grid=root.querySelector('.parallel-grid');
 for(const row of rows){
  let card=[...grid.children].find(c=>c.dataset.environment===row.environment_id);
  if(!card){
   card=text('section','','six-card');card.dataset.environment=row.environment_id;
   for(const key of ['title','env','episode','phase','action','source','video-note']){const el=text(key==='title'?'h3':'p','');el.dataset.field=key;card.append(el);}
   const video=document.createElement('video');video.controls=true;video.preload='metadata';video.hidden=true;video.setAttribute('aria-label','本独立环境证据视频');card.append(video);
   const load=text('button','加载本回合最新视频');load.type='button';load.dataset.load='true';load.hidden=true;card.append(load);
   const image=document.createElement('img');image.hidden=true;image.alt='当前独立环境最新公开观测（非连续视频）';card.append(image);
   const detail=text('button','查看证据 / 补充建议');detail.type='button';detail.dataset.detail='true';card.append(detail);grid.append(card);
  }
  const field=(key,value)=>{card.querySelector(`[data-field="${key}"]`).textContent=value;};
  field('title',row.name);field('env',row.native_env_id);
  field('episode',`${row.campaign} / ${row.episode} · 动作 ${show(row.actions)}`);
  field('phase',row.state_label+(row.retired?' · 已退出重试':''));
  field('action',row.last_action_at?`最近实际动作：${stamp(row.last_action_at)} · ${age(row.last_action_at)}（执行回执时间）`:'最近实际动作：尚无已完成执行回执');
  field('source',`证据更新：${stamp(row.source_at)}；阶段上报：${stamp(row.phase_report_at)}。刷新不代表物理动作。`);
  const media=row.videos?.[0]||row.progress_clip,video=card.querySelector('video'),load=card.querySelector('[data-load]');
  const loadMedia=()=>{if(!media?.url)return;video.src=media.url;video.hidden=false;load.hidden=true;card.dataset.playingEpisode=media.episode;card.dataset.mediaKind=row.videos?.length?'完整封口录像':'公开观测片段（非连续录像）';};
  if(media?.url&&(!video.getAttribute('src')||((video.paused||video.ended)&&video.getAttribute('src')!==media.url)))loadMedia();
  video.onended=()=>{if(media?.url&&video.getAttribute('src')!==media.url)loadMedia();};
  load.hidden=!media?.url||video.getAttribute('src')===media.url;load.onclick=loadMedia;
  field('video-note',video.getAttribute('src')?`${card.dataset.playingEpisode} · ${card.dataset.mediaKind}${!load.hidden?'；新视频已到，点击加载':''}`:row.video_note);
  const image=card.querySelector('img');image.hidden=!row.preview?.url;
  if(!image.hidden&&image.getAttribute('src')!==row.preview.url)image.src=row.preview.url;
  card.querySelector('[data-detail]').onclick=()=>chooseSix(row.id,true);
 }
 for(const card of [...grid.children])if(!rows.some(r=>r.environment_id===card.dataset.environment))card.remove();
 if(!rows.length){let empty=root.querySelector('.parallel-empty');if(!empty){empty=text('p','尚无绑定到已准入精确任务的独立环境证据。','parallel-empty');root.append(empty);}}
 else root.querySelector('.parallel-empty')?.remove();
}
