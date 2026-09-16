当前问题：005已因HTTP429结束，9调用完成、4动作/20.04秒；自动接续阻塞，没有006。
总目标：原桌位红块走近→站稳抓持→携物移动→桌面释放/退手/保持，网页真实进度与录像。
不可重犯的错误：不重发002/55、004/43、005/10，不绕过网关/预算/审批，不放宽安全线，不伪报actor存活。

本次监督接续完成004复盘，并以独立reset、新schema2 batch/auth和正常执行审批实际推进005。005尚未抓持，真实后端MuJoCo。005的原结果、10份回执、公开动作和原视频保持原样；[追加复盘](REVIEW.md)、[条件化经验](experience-v005.json)、[完整录像](http://127.0.0.1:8765/videos/api-ground-episode-0005.mp4)已可查。004的83.08秒完整录像也保留。

新005首个及后续共9个API调用完成，验证了本分支schema2适配和HTTP200流证据记录路径；第10次返回HTTP429，远端结果/费用仍未知。共享库发布不等于实际运行验证，实际完成也不等于费用已结算。集成ACK及路径在../BUDGET-ACK-005.json；本最终阻塞记录补充该较早ACK。三笔异常未知请求各1217分预留未释放；旧已完成但费用未知的hold同样保留，没有修改共享库或其它分支账本行。

005启动前44项离线回归通过；本停止边界只读核验原002/004/005证据、原ground账本行均无变化，005视频ffprobe与网页Range206通过。第一次宿主命令核验误把相对watch.py当不存在，已核对cwd并修正断言，未影响进程；记录见verification-first-pass.txt。没有为005停止新增model请求、006、环境修改或服务重启。

最终宿主记录[final-verification.json](final-verification.json)：旧005 actor已退出；现有唯一watcher PID456959存活且持有owner.lock，当前辅助工程owner仍为01a0a982-cec5-71c0-b771-091c31df61f2。owner-state为blocked、episode-0005，owner_log与active-owner精确一致，written_ns晚于当前turn开始。

下一边界是本工程turn自然结束后，既有watcher读取blocked并保持可观测阻塞；它不自动恢复、不重试探测网关。其现有代码届时会将短监督说明写成通用blocked_owner_disposition，具体HTTP429依据与恢复条件永久保留在本复盘、blocker.json、owner-state及公共blocker字段。未热改或另起watcher。

真正需要的是网关限制解除的可核验证据和明确的安全恢复条件，再按既有授权流程准备独立reset。HTTP429正文/子码未记录，不能断言额度或限流；不查询额度、价格、不请求预算追加、不换账号。自动监督暂停并不表示搬运目标完成。工程网页ACK已更新，暂无新ground人工回答，未伪造人工反馈使用或物理验证。
