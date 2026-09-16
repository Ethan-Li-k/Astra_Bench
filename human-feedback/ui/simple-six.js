'use strict';
window.renderSimpleSix=(parent,snapshot,selected,choose)=>{
 const cards=document.getElementById('six-cards');
 const rate=r=>!r?.denominator?'未测评（0 个已完成样本）':`${r.numerator} / ${r.denominator} · ${r.percent.toFixed(1)}%`;
 const scope=p=>p==='current'?'当前范围学习':p==='history'?'历史学习':'时间范围未确认';
 const layer=a=>a==='assisted'?'人工反馈辅助':a==='autonomous'?'自主（无人工反馈）':'辅助类型未知';
 const line=(el,label,value,cls='')=>el.append(text('p',label+value,cls));
 document.getElementById('six-scope').textContent=parent.focus_acknowledged?'六项精确入口：负责人已确认。固定候选和实际加载按独立回执记录。':'六项精确入口已登记；负责人确认以公开回执为准。';
 for(const task of parent.subtasks||[]){
  let card=cards.querySelector(`[data-card="${task.id}"]`);
  if(!card){card=text('section','','six-card');card.dataset.card=task.id;cards.append(card);}
  const s=task.scorecard;if(!s)continue;
  const open=card.querySelector('details')?.open;
  if(card.contains(document.activeElement)&&card.children.length)continue;
  card.setAttribute('aria-label',task.name);card.dataset.selected=String(selected===task.id);card.replaceChildren();
  const title=text('button',task.name,'six-title');title.type='button';title.onclick=()=>choose(task.id,true);title.setAttribute('aria-pressed',String(selected===task.id));card.append(title);
  const phase=s.frozen.registered?'冻结测评':s.stability.registered?'固定候选稳定性检查':s.records.length?'技能学习':'适配 / 未开始';
  line(card,'阶段：',phase,'six-phase');
  const current=s.groups.filter(g=>g.period==='current');
  if(!current.length)line(card,'当前学习：','未测评 / 无已完成审计样本','six-rate');
  for(const g of current){line(card,'学习 · ',layer(g.assistance),'fine');line(card,'原生 ',rate(g.native),'six-rate');line(card,'完整审计 ',rate(g.semantic),'six-rate');if(current.length>1)line(card,'条件：',g.variant+' / '+g.control,'fine');}
  for(const g of s.groups.filter(g=>g.period==='history'))line(card,`历史学习 · ${layer(g.assistance)}：`,`原生 ${rate(g.native)}；完整审计 ${rate(g.semantic)}`,'fine');
  line(card,'候选连续：',s.stability.registered?`${s.stability.consecutive??'待核验'} / 5`:'未登记 / 目标 5 次','fine');
  line(card,'冻结测评：',rate(s.frozen.semantic)+'；计划 '+s.frozen.planned+' 回合','fine');
  const unresolved=s.dispositions;
  const labels={inflight:'未封口',pending:'待判定',infrastructure:'系统中断',paused:'暂停',replay:'回放/诊断',duplicate:'重复reset'};
  const pending=Object.entries(labels).filter(([k])=>unresolved[k]).map(([k,v])=>`${v} ${unresolved[k]}`).join(' · ');
  if(pending)line(card,'另列：',pending,'fine');
  line(card,'卡点：',task.episode?(task.scorecard.dispositions.inflight?'最近回合未封口；完整结果与当前存活待负责人核验。':task.problem):'精确入口尚无实际回合；等待控制适配。','six-blocker');
  line(card,'下一步：',s.frozen.registered?'按已登记批次完成并审计。':s.stability.registered?'按同候选独立 reset 检查连续成功。':s.dispositions.inflight?'当前回合完整收尾，再审计与登记候选。':'由原负责人完成适配 / 学习并登记候选。','fine');
  const link=text('button',task.videos?.length?'看最新已封口录像 ↘':'查看进展 / 补充建议 ↘','six-link');link.type='button';link.onclick=()=>choose(task.id,true);card.append(link);
  if(task.videos?.length)line(card,'录像：',task.videos[0].episode+' · '+age(task.videos[0].at)+'（不代表当前画面）','fine');
  const details=document.createElement('details');details.open=Boolean(open);details.append(text('summary','分层成绩、分母与历史记录'));
  line(details,'',s.definition,'fine');
  for(const g of s.groups){line(details,'',`${scope(g.period)} · ${layer(g.assistance)} · ${g.variant} / ${g.control}`);line(details,'原生 ',rate(g.native));line(details,'完整语义审计 ',rate(g.semantic));line(details,'技能版本 ',`${g.skill_versions}；${g.episodes.join('、')}`,'fine');}
  line(details,'固定候选：',s.stability.note);line(details,'冻结：',s.frozen.note);line(details,'冻结原生 ',rate(s.frozen.native));line(details,'冻结完整审计 ',rate(s.frozen.semantic));
  for(const r of s.records)line(details,'',`${r.episode} · ${scope(r.period)} / ${layer(r.assistance)} · ${r.reason}`,'fine');
  line(details,'入口：',task.native_env_id,'fine');card.append(details);
 }
 const valid=sixCases();const help=document.getElementById('six-help');help.replaceChildren(text('strong',valid.length?`待你回答：${valid.length} 个已核验问题`:'目前无必答问题'));
 if(valid.length)for(const c of valid){const b=text('button',c.question);b.type='button';b.onclick=()=>{bindForm(c);document.getElementById('answer-form').scrollIntoView();};help.append(b);}
 else help.append(text('span',' · 尚无满足“三次同阶段、同机制、可比独立失败且自主修订未解决”的新问题；预算结束数量不直接生成求助。'));
 const a=text('a','主动补充观察 / 建议');a.href='#answer-form';help.append(a);
};
