import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';

const root='/home/galbot/lizekai/RSI/api-ground-to-table';
const source='/home/galbot/lizekai/RSI/codex-account-2/workspace/ground-to-table/campaign/episode-0004';
const out=path.join(root,'cases/F001');
fs.mkdirSync(path.join(out,'frames'),{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(path.join(source,p),'utf8'));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const provenance=[];
function copy(relative,destination){
  const from=path.join(source,relative),to=path.join(out,destination);
  fs.mkdirSync(path.dirname(to),{recursive:true});
  fs.copyFileSync(from,to);
  provenance.push({source:from,copy:to,sha256:sha(from)});
}
const actions=[];
for(let n=1;n<=3;n++){
  const id=String(n).padStart(4,'0');
  const execution=read(`rollout/episode/execution_${id}.json`);
  const motion=read(`rollout/episode/motion_${id}/proprioception.json`);
  const first=motion.samples[0],last=motion.samples.at(-1);
  const link=n===1?'right_ankle_roll_link':n===2?'left_ankle_roll_link':'right_wrist_yaw_link';
  const z=first.four_point_world[link].position_world_m[2];
  actions.push({index:n,link,start_sim_s:first.sim_s,end_sim_s:last.sim_s,
    command:execution.response,endpoint_status:execution.receipts[0].status,
    measured_peak_rise_mm:1000*(Math.max(...motion.samples.map(s=>s.four_point_world[link].position_world_m[2]))-z),
    end_rise_mm:1000*(last.four_point_world[link].position_world_m[2]-z),
    sample_count:motion.samples.length,
    pelvis_delta_m:last.pelvis_world.position_world_m.map((v,i)=>v-first.pelvis_world.position_world_m[i])});
  copy(`rollout/episode/motion_${id}/proprioception.json`,`public/motion_${id}.json`);
  copy(`rollout/episode/execution_${id}.json`,`public/execution_${id}.json`);
}
for(let n=0;n<=3;n++){
  const id=String(n).padStart(4,'0');
  for(const f of ['observation.json','head_cam.png','right_wrist_cam.png'])
    copy(`rollout/episode/observations/${id}/${f}`,`public/observation_${id}/${f}`);
}
copy('SKILL.md','public/starting-SKILL.md');
const frames=[{dir:'rollout/episode/observations/0000',label:'PRE ACTION 1 - available before first action'}];
for(let n=1;n<=3;n++)for(let k=0;k<3;k++){
  const id=String(n).padStart(4,'0');
  frames.push({dir:`rollout/episode/motion_${id}/knot_0${k}`,label:`ACTION ${n} - sample ${k+1} - returned AFTER action`});
}
for(let i=0;i<frames.length;i++){
  const f=frames[i],dst=path.join(out,'frames',`${String(i).padStart(2,'0')}.png`);
  for(const camera of ['head_cam','right_wrist_cam'])copy(`${f.dir}/${camera}.png`,`public/frame_${i}/${camera}.png`);
  if(!fs.existsSync(dst))execFileSync('ffmpeg',['-v','error','-n','-threads','1','-filter_complex_threads','1','-i',path.join(source,f.dir,'head_cam.png'),'-i',path.join(source,f.dir,'right_wrist_cam.png'),'-filter_complex',`[0:v][1:v]hstack=inputs=2,pad=iw:ih+64:0:64:black,drawtext=text='F001 | ${f.label}':x=12:y=9:fontcolor=white:fontsize=18,drawtext=text='HEAD RGB (left) | RIGHT WRIST RGB (right) | recorded snapshots - not real-time video':x=12:y=36:fontcolor=white:fontsize=16`,'-frames:v','1',dst]);
}
if(!fs.existsSync(path.join(out,'actor-observations.mp4')))execFileSync('ffmpeg',['-v','error','-n','-framerate','0.5','-i',path.join(out,'frames/%02d.png'),'-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-r','25','-movflags','+faststart',path.join(out,'actor-observations.mp4')]);
const packet={case_id:'F001',episode:'episode-0004',backend:'MuJoCo',purpose:'Human correction of public visual/spatial decisions; not a new physical experiment',
  setting_warning:'Historical diagnostic: table shifted +0.55m; continuous controller contract differs from original. Not original-setting success.',
  evidence_boundary:{actor:'Head/right-wrist RGB, calibration, named robot proprioception, public commands and receipts; intermediate samples were returned only after each action.',review_only:'Original composite video left panel is external diagnostic camera, not an actor input. No target pose/contact truth is included in the API packet.'},
  actions,frames,original_diagnostic_video:path.join(source,'video/episode.mp4'),
  caution:'Actions are sequential, not matched-reset experiments. Peak ankle link height is not a contact sensor. Do not infer policy impossibility or a proven controller bug.'};
fs.writeFileSync(path.join(out,'packet.json'),JSON.stringify(packet,null,2));
fs.writeFileSync(path.join(out,'provenance.json'),JSON.stringify(provenance,null,2));
const summary=actions.map(a=>({index:a.index,link:a.link,command_summary:a.index<3?'80 mm up / plateau / return, 1.8 seconds':'50 mm up / plateau / return, 1.8 seconds',reason_summary:a.index===1?'New intermediate measurements make one repeated pulse informative.':a.index===2?'Left/right contrast, explicitly not matched reset.':'Wrist positive control for whether any target channel responds.',measured_peak_rise_mm:a.measured_peak_rise_mm,end_rise_mm:a.end_rise_mm,endpoint_status:a.endpoint_status,sample_count:a.sample_count,pelvis_delta_m:a.pelvis_delta_m}));
const prompt=`你是独立机器人失败审阅员。只读审阅，不执行物理动作，不调用工具。案例F001：G1 + DEX3，MuJoCo，UMI-4/model_38000 + WristPI。任务是走到地面红块、抓起、运输、桌面释放。用户擅长读图、长程规划、空间推理。请为其提供最多4个高信息量填空/选择问题，帮助区分下一步决策，而不是泛泛问为什么失败。只输出简短、可审查的依据摘要，不输出隐含内部推理。明确事实、假设、信息缺口，不能把假设当结论。提供一个最小的同条件对照方案与能推翻假设的观测。先完成旧失败复现再只改一个因素，不改控制器/模型/稳定阈值，不能给成功承诺。\n附件为初始及第一次动作后的原始头/腕RGB，顺序为初始头、初始腕、动作1后头、动作1后腕。你与用户收到相同图片和以下公开数值，不提供外部相机或host接触真值。全部中间观测在动作结束后才返回。实验依次进行，不是同初态左右脚因果对照。桌子有0.55m历史偏移，这不是原setting正式评测。\n公开摘要：${JSON.stringify(summary)}\n输出中文JSON：visible_facts、uncertainties、competing_hypotheses(最多3)、human_questions(最多4，每题注明答案如何改变下一实验)、matched_retest、do_not_conclude。答案总长约800中文字。`;
fs.writeFileSync(path.join(out,'api-review-prompt.txt'),prompt);
console.log(JSON.stringify({case_id:'F001',actions:summary,frames:frames.length,video:path.join(out,'actor-observations.mp4')}));
