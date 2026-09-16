'use strict';
// Add alongside the existing app. Status refresh never touches the video element.
(() => {
  const el=id=>document.getElementById(id),show=x=>x===null||x===undefined?'未知 / 未提供':String(x);
  let last=null,busy=false,noticeKey;
  const stamp=t=>t===null?'未知 / 未提供':`${new Date(t*1000).toLocaleString()}（${Math.max(0,Math.floor(Date.now()/1000-t))} 秒前）`;
  function ages(){
    if(!last)return;
    el('ikea-progress-time').textContent=`最后实际进展：${stamp(last.last_progress_at_unix)}${last.progress_time_basis==='legacy_engineering_record'?' · 兼容旧工程记录；不是动作时间':''}`;
    el('ikea-heartbeat-time').textContent=`心跳：${stamp(last.heartbeat_at_unix)} · 只证明心跳，不证明动作或进展`;
    el('ikea-fetched-time').textContent=`页面获取：${stamp(last.fetched_at_unix)} · 不作为实际进展时间`;
  }
  async function refresh(){
    if(busy||!el('ikea-progress'))return;busy=true;
    try{
      const response=await fetch('/api/ikea-progress',{cache:'no-store'});
      if(!response.ok)throw Error('read failed');
      const d=await response.json();last=d;
      const key=JSON.stringify([d.phase,d.terminal_kind,d.needs_human]);
      if(key!==noticeKey){el('ikea-change').textContent=`${new Date().toLocaleTimeString()} · ${noticeKey?'阶段 / 终态 / 人工介入状态变化':'首次观测'}：${d.phase_label} · ${d.terminal_label}`;noticeKey=key;}
      el('ikea-chain').textContent=d.tasks.map(x=>`${x.title}：${x.verification}`).join(' → ');
      el('ikea-backend').textContent=`实际后端：${d.backend} · ${d.variant} · 原 USD 门关节：${d.original_usd_joints}`;
      el('ikea-state').textContent=`${d.state_label} · ${d.phase_label}`;
      el('ikea-counts').textContent=`真实独立策略尝试：${show(d.physical_attempts)} · 审计成功：${show(d.audited_successes)} · 动作：${show(d.actions)} · 模拟秒：${show(d.simulated_seconds)} · 工程诊断：${show(d.diagnostic_runs)} 次 / ${show(d.diagnostic_simulated_seconds)} 秒`;
      el('ikea-terminal').textContent=`终态分类：${d.terminal_label}`;
      el('ikea-human').textContent=`人工介入：${d.needs_human===null?'未提供':d.needs_human?'来源标记需要人工介入':'当前未请求'}`;
      el('ikea-restart').textContent=d.host_restart_observed?'本机曾于 09:08 UTC 左右重启，旧进程已中断；重启前状态仅为最后已知记录。当前运行是否恢复须看新的任务证据。':'运行状态仅按来源最近记录显示，不能用心跳证明任务推进。';
      el('ikea-media').textContent=d.media_note;
      el('ikea-error').textContent='';ages();
      el('ikea-sources').replaceChildren();
      for(const ref of d.sources){const p=document.createElement('p');p.className='caption';p.textContent=`${ref.source} · SHA256 ${ref.sha256}`;el('ikea-sources').append(p);}
      el('ikea-videos').replaceChildren();
      for(const v of d.videos){
        const p=document.createElement('p'),a=document.createElement('a');
        a.href=v.url;a.textContent=`${v.title} · ${v.duration_s.toFixed(2)} 秒 · 打开已完成录像`;
        p.append(a);el('ikea-videos').append(p);
        // Compatibility with the existing player's catalog; only add options, never select.
        if(typeof index!=='undefined'&&index?.videos&&typeof addVideo==='function'){
          const old=index.videos.findIndex(x=>x.id===v.id);if(old>=0)index.videos[old]=v;else index.videos.push(v);addVideo(v);
        }
      }
      for(const b of document.querySelectorAll('#video-list button'))if(b.dataset.id?.startsWith('ikea-'))b.disabled=!d.videos.some(v=>v.id===b.dataset.id);
    }catch(e){el('ikea-error').textContent='IKEA 公开记录暂不可读；保留上次观测，不推断任务故障。';}
    finally{busy=false;}
  }
  window.refreshIKEAProgress=refresh;
  refresh();setInterval(refresh,10000);setInterval(ages,1000);
})();
