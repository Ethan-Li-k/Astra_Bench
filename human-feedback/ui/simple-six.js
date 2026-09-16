'use strict';
window.renderSimpleSix=(parent,snapshot,selected,choose)=>{
 const cards=document.getElementById('six-cards');
 const rate=r=>!r?.denominator?'未测评（0 个已完成样本）':`${r.numerator} / ${r.denominator} · ${r.percent.toFixed(1)}%`;
 const levelRate=r=>!r?.denominator?'未测评':`${r.numerator}/${r.denominator} · ${r.percent.toFixed(1)}%`;
 const scope=p=>p==='current'?'当前范围学习':p==='history'?'历史学习':'时间范围未确认';
 const layer=a=>a==='assisted'?'人工反馈辅助':a==='autonomous'?'自主（无人工反馈）':'辅助类型未知';
 const line=(el,label,value,cls='')=>el.append(text('p',label+value,cls));
 document.getElementById('six-scope').textContent=(parent.focus_acknowledged?'六项精确入口：负责人已确认。':'六项精确入口已登记；确认以公开回执为准。')+' 正式计划 6 项 × 3 等级 × 10 回合 = 180；学习和五次稳定性另计。';
 document.getElementById('benchmark-status').textContent='正式对齐待完成：环境配置 / 预注册 split / 等级映射 / 同步 Isaac 策略输入证据待核验（物理后端仍为 MuJoCo）。';
 for(const task of parent.subtasks||[]){
  let card=cards.querySelector(`[data-card="${task.id}"]`);
  if(!card){card=text('section','','six-card');card.dataset.card=task.id;cards.append(card);}
  const s=task.scorecard;if(!s)continue;
  const open=card.querySelector('details')?.open;
  const focused=card.contains(document.activeElement)?document.activeElement.className||document.activeElement.tagName:null;
  card.setAttribute('aria-label',task.name);card.dataset.selected=String(selected===task.id);card.replaceChildren();
  const title=text('button',task.name,'six-title');title.type='button';title.onclick=()=>choose(task.id,true);title.setAttribute('aria-pressed',String(selected===task.id));card.append(title);
  const phase=s.frozen.registered?'冻结测评':s.stability.registered?'固定候选稳定性检查':s.records.length?'技能学习':'适配 / 未开始';
  line(card,'阶段：',phase,'six-phase');
  const live=text('p',task.episode?`${task.episode} · 动作 ${task.actions??'未知'}`:'精确入口尚无实际回合','six-current');
  live.dataset.episode=task.episode||'';live.dataset.action=task.actions??'';card.append(live);
  line(card,'执行记录：',task.state_label,'fine');
  if(task.last_action_at)line(card,'动作证据：',stamp(task.last_action_at)+' · '+age(task.last_action_at),'fine');
  if(task.phase_report_at)line(card,'阶段上报：',stamp(task.phase_report_at)+' · '+age(task.phase_report_at),'fine');
  const current=s.groups.filter(g=>g.period==='current');
  if(!current.length)line(card,'当前学习：','未测评 / 无已完成审计样本','six-rate');
  for(const g of current){line(card,'学习 · ',layer(g.assistance),'fine');line(card,'原生 ',rate(g.native),'six-rate');line(card,'完整审计 ',rate(g.semantic),'six-rate');if(current.length>1)line(card,'条件：',g.variant+' / '+g.control,'fine');}
  for(const g of s.groups.filter(g=>g.period==='history'))line(card,`历史学习 · ${layer(g.assistance)}：`,`原生 ${rate(g.native)}；完整审计 ${rate(g.semantic)}`,'fine');
  line(card,'候选连续：',s.stability.registered?`${s.stability.consecutive??'待核验'} / 5`:'未登记 / 目标 5 次','fine');
  line(card,'正式测评：','每级计划 10 · 本项共 30 回合','fine');
  const levels=text('div','','benchmark-levels');
  for(const [level,v] of Object.entries(s.frozen.levels||{})){
   line(levels,level+' · ',`${v.state==='alignment-pending'?'待对齐 · ':''}原生 ${levelRate(v.native)}；完整审计 ${levelRate(v.semantic)}`,'fine');
  }
  card.append(levels);
  const unresolved=s.dispositions;
  const labels={inflight:'未封口',pending:'待判定',infrastructure:'系统中断',paused:'暂停',replay:'回放/诊断',duplicate:'重复reset'};
  const pending=Object.entries(labels).filter(([k])=>unresolved[k]).map(([k,v])=>`${v} ${unresolved[k]}`).join(' · ');
  if(pending)line(card,'另列：',pending,'fine');
  line(card,'卡点：',task.problem,'six-blocker');
  if(task.recent_audit_note)line(card,'上次审计：',task.recent_audit_note,'fine');
  line(card,'下一步：',s.frozen.registered?'按已登记批次完成并审计。':s.stability.registered?'按同候选独立 reset 检查连续成功。':task.next,'fine');
  if(task.preview){const frame=text('button',`最新画面 · 动作 ${task.preview.action} · ${age(task.preview.at)} ↘`,'six-frame');frame.type='button';frame.onclick=()=>{choose(task.id,false);document.querySelector('.preview-panel').scrollIntoView({block:'center'});};card.append(frame);}
  const link=text('button',task.videos?.length?'看最新已封口录像 ↘':'查看进展 / 补充建议 ↘','six-link');link.type='button';link.onclick=()=>choose(task.id,true);card.append(link);
  if(task.videos?.length)line(card,'录像：',task.videos[0].episode+' · '+age(task.videos[0].at)+'（不代表当前画面）','fine');
  const details=document.createElement('details');details.open=Boolean(open);details.append(text('summary','分层成绩、分母与历史记录'));
  line(details,'',s.definition,'fine');
  for(const g of s.groups){line(details,'',`${scope(g.period)} · ${layer(g.assistance)} · ${g.variant} / ${g.control}`);line(details,'原生 ',rate(g.native));line(details,'完整语义审计 ',rate(g.semantic));line(details,'技能版本 ',`${g.skill_versions}；${g.episodes.join('、')}`,'fine');}
  line(details,'固定候选：',s.stability.note);line(details,'正式测评：',s.frozen.note);
  if(s.legacy_frozen?.registered)line(details,'旧冻结批次（未对齐官方等级）：',`原生 ${rate(s.legacy_frozen.native)}；完整审计 ${rate(s.legacy_frozen.semantic)}，不计 L0/L1/L2。`);
  for(const r of s.records)line(details,'',`${r.episode} · ${scope(r.period)} / ${layer(r.assistance)} · ${r.reason}`,'fine');
  line(details,'入口：',task.native_env_id,'fine');card.append(details);
  if(focused){const target=focused==='six-title'?'.six-title':focused==='six-link'?'.six-link':focused==='SUMMARY'?'summary':null;if(target)card.querySelector(target)?.focus({preventScroll:true});}
 }
 const valid=sixCases();const help=document.getElementById('six-help');help.replaceChildren(text('strong',valid.length?`待你回答：${valid.length} 个已核验问题`:'目前无必答问题'));
 if(valid.length)for(const c of valid){const b=text('button',c.question);b.type='button';b.onclick=()=>{bindForm(c);document.getElementById('answer-form').scrollIntoView();};help.append(b);}
 else help.append(text('span',' · 尚无满足“三次同阶段、同机制、可比独立失败且自主修订未解决”的新问题；预算结束数量不直接生成求助。'));
 const a=text('a','主动补充观察 / 建议');a.href='#answer-form';help.append(a);
 renderOfficialReference(parent);
};

function renderOfficialReference(parent){
 const plan=parent.subtasks?.[0]?.scorecard?.frozen;
 document.getElementById('alignment-blocker').textContent=plan?.blocker||'对齐证据尚未核验。';
 document.getElementById('alignment-limit').textContent=plan?.protocol_limit||'';
 const runtime=parent.benchmark_plan?.learning_runtime;
 document.getElementById('learning-runtime').textContent=(runtime?.note||'持续学习和中央技能发布 / 加载状态待确认。')+(runtime?.at?' 发布证据：'+stamp(runtime.at)+'。':'');
 const b=parent.official_baseline,table=document.getElementById('official-table'),source=document.getElementById('baseline-source');
 const signature=JSON.stringify([b,parent.subtasks?.map(t=>t.scorecard.frozen)]);if(table.dataset.signature===signature)return;table.dataset.signature=signature;table.replaceChildren();source.replaceChildren();
 if(!b?.available){source.textContent=b?.reason||'官网基线来源未提供';return;}
 const link=text('a','SIMPLE 指定官网 results');link.href=b.source_url;link.target='_blank';link.rel='noopener';source.append(link,text('span',' · 抓取时间 '+b.read_at+'（不是浏览器刷新时间）'));
 const caption=text('caption','成功数 / 10；每格从左到右为 L0、L1、L2');table.append(caption);
 const head=document.createElement('thead'),hr=document.createElement('tr');
 for(const name of ['方法',...b.task_order]){const th=text('th',name);th.scope='col';hr.append(th);}head.append(hr);table.append(head);
 const body=document.createElement('tbody');
 for(const r of b.rows){const tr=document.createElement('tr'),name=text('th',r.method);name.scope='row';tr.append(name);
  for(const triple of r.values){const td=text('td',triple.map(n=>`${n}/10`).join(' · '));td.dataset.values=triple.join(',');tr.append(td);}body.append(tr);}
 const ours=document.createElement('tr');ours.className='our-benchmark';const label=text('th','我们的方法 · 正式测评');label.scope='row';ours.append(label);
 for(const task of parent.subtasks||[]){const td=document.createElement('td');
  const metric=r=>r.denominator?`${r.numerator}/${r.denominator} · ${r.percent.toFixed(1)}%`:'未测评';
  for(const [level,v] of Object.entries(task.scorecard.frozen.levels))td.append(text('span',`${level}：${v.state==='alignment-pending'?'待对齐；':''}原生 ${metric(v.native)}；完整审计 ${metric(v.semantic)}（计划 ${v.planned}）`));ours.append(td);}
 body.append(ours);table.append(body);
}
