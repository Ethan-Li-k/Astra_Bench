from pathlib import Path
import json
B=Path(__file__).resolve().parent
root=str(B)
base=f'''NO-TRUNCATION-SHARED-SKILLS-20260916 / NT-v1 bounded reviewer delivery. 候选未合并；请读 {root}/FINAL.md 和 INTEGRATION.md。18/18离线测试、3入口结构/长度检查；continuity.patch 与此前 memory-priority/combined-compatible.patch 在当前源副本顺序dry-run通过。只修匹配的已闭合网络turn恢复和不确定turn/start保护，不重做next_message(None)，不恢复重启前丢失状态。仅自然边界采用，勿打断在途推理/重复动作。请用reviewer辅助queue 01a0a94d-6143-74c0-80cd-03d0b61acaf0逐项回ACK/集成版本/后续公共观察、条件经验、兼容或反例；无新证据不逐请求广播。排队≠ACK≠集成≠物理收益。'''
extra={
'SIMPLE':'已核实首轮ARCH-REVIEW ACK与PROGRESS中的memory ACK，并接收你方door15网络证据。door15 boot与当前不同，0 turn/completed，不能从旧running推断仍有推理。你仍唯一公共publisher；请逐hunk审查，保留finish/执行故障/放置及审计边界。skills/simple是完整短入口候选，不要再叠加长core。原任务控制器/reset/反馈层级固定后分别测连续性与技能，不将离线通过称物理收益。',
'API-ground':'已阅读CONTINUATION和最新recovery/RECOVERY：新恢复owner为01a0a982-cec5-71c0-b771-091c31df61f2，第55次未知不得重发，旧owner线程不得resume。本条按获准既有收件入口排队供协作链转交，不要求唤醒旧线程，不接管新owner或授权。API是独立Responses runner，不直接套Codex adapter补丁；ground短入口需新episode授权并保持120次/180秒及共享预算边界。空手步行/持物携带/释放分别验证。',
'IKEA':'已阅读你的OUTBOX/state及SIMPLE的FRAMEWORK_OUTBOX，新场景/资产/门-苹果-冰箱任务均由你持有；本审查不执行旧安装/预算/运行请求。0 actor物理尝试不称门成功。skills/ikea为门机制短入口候选，实际IKEA runtime尚未选定，必须重查真实总长和控制合同；SIMPLE fixed-frame push-open不等于原场景/锁舌。无兼容经验明确不迁移。'}
for name in ('SIMPLE','API-ground','IKEA'):(B/'handoff'/f'{name}.txt').write_text(base+'\n'+extra[name]+'\n')
