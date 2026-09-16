# 原桌位地面红块搬运：重启恢复

当前辅助账号唯一owner：`01a0a982-cec5-71c0-b771-091c31df61f2`，gpt-6-astra/xhigh。旧owner随重启消失，不resume旧线程。

状态：**infrastructure_error / recovery**。本机只读核验得到启动时间2026-09-16 02:08:07（America/Los_Angeles），原PID3537389、3431415不存在。不是仍在进行的长推理。原tmux缺失由用户提供的宿主检查确认；本次沙箱tmux读取得到Operation not permitted，不能声称本次独立验证了会话列表。

重启前最后公开进度为02:07:38，api-ground-002 / episode-0002，54次完成模型调用、23动作、108.98物理秒。恢复更新时间不代表新的物理进展。实际backend为MuJoCo，推理时暂停物理，不声称实时闭环。抓持、携带、放置均未验证。

已另存原状态及回合、批次的762项文件快照与SHA256清单。具体磁盘证据损坏与主机重启分别记录：调用55的receipt和plan为空；还发现动作23的execution、public_tool_0054、部分RGB/运动记录等空文件。最终完整可核验动作与账本引用正在审查，不以最后公开计数替代完整证据。未知费用保留，调用55绝不自动重发。

原录像只读ffprobe失败：moov atom not found。原文件与副本均保留；录像未封口，未恢复，不称完整录像，也不将图像序列称为连续视频。未修改原receipt、ledger、episode/result或录像。

接续条件：只有完整且可校验的sim/controller/history状态才允许同物理回合恢复。否则追加独立基础设施中断审计，不计作真实物理失败或人工求助失败样本，并准备新run/episode/auth及正常执行审查。新尝试保持G1/DEX3/model38000/WristPI、原table0、120请求/180物理秒与原安全阈值；禁止主账号fallback、重复55或冒用旧单episode批准。

当前未发新模型请求。正在审查账本与公共经验，后续测试、审批、启动或阻塞继续写入本目录。UI服务由既有owner维护；本分支只更新公开状态源并交接恢复字段。

## 已完成的恢复核验与新批准备

- 独立中断审计见interruption-audit.json。最后独立完整执行回执为动作22（104.48物理秒）；动作23的命名观测obs_005496及其嵌入ACK仍可读，状态timed_out、reference_finished=true，对应最后公开108.98物理秒。动作23的独立execution、RGB和轨迹证据为空，不能称完整轨迹。检查到21项空文件，history.jsonl/run-002.log亦有NUL；未修改原文件。
- 账本79921字节、JSON可解析；SHA256为8c8c97a3558dd70eb551c10dc43beedba088c2d2d13402f335c7227b6abfbbcd。唯一账本引用hash失配是55的空plan。60条完成但费用未知、1条结果未知55，共742.37元预留；另有3.39元已确认。所有旧row原样保留，未释放hold、未新增收费请求。
- 共享预算owner已发布schema2合同（9008e224…），49项独立离线回归；本分支消费RESULT/FORMAT/部署回执，未修改shared core。先前尚未执行的本地schema1草稿与allowlist拒绝记录均保留且标为superseded。正式新批登记在artifacts/R021/api-ground-003，绑定新的episode-0003、当前恢复授权和公开数据范围，不重用002的单episode审批。
- 本地旧hold守卫7项测试、无工具完整turn接续3项、003真实actor/hook配合隔离账本假transport的2项测试通过；原actor28项回归通过。测试拒绝foreign未知请求、旧row变化、旧55伪completion、重复begin；没有网络或生产ledger写入。原子落盘及完整无工具turn续接只影响下一新回合。
- 新主skill沿用已pin版本，含runtime共745 words / 5786 characters / 5030非空白，满足831/6250/5357。经验来源、拒选、合同与模型hash见public-transfer.json，明确SIMPLE卸载/改站位只是机制假设，原桌位接近/扭转/支撑退步尚未证明步态；不导入隐藏真值，不宣称loaded locomotion已验证。
- 沙箱nvidia-smi失败；正常工具升级后的宿主只读核验成功：RTX 5090 D v2 / driver580.178.04。没有改动驱动或环境。

下一步：对launch-003.sh提交正常执行工具审批，通过后独立tmux+tee启动。未通过审批前不会发送API。准备检查见ready-review.json；运行将写run-003.log、started、exit-code及独立campaign/episode-0003。正式授权保持120请求/180物理秒、原安全阈值、仅直接API，无超时重发或主账号fallback。

## 新回合已正式启动

正常执行工具审批已通过（launch-approval.json，工具返回exit0）。tmux `rsi-api-ground-003-0916`，实际Python PID209247；2026-09-16 09:37:31 UTC完成新reset，UUID `2f13f803-2de9-4e55-bf1b-5307486b2989`，new_model_and_data_instance=true，原table偏移0。不是002恢复，不重放旧动作。首次新请求已进入真实推理等待；本段写入时还未完成新动作。

网页只读接口已核验显示 `api-ground-003 / episode-0003 / MuJoCo / 正在推理`，证据web-live-after-launch.json。恢复历史的纯公开投影另存actor-adapter/recovery-history.json，已交UIowner接入旧回合中断说明；不读取snapshot/host audit到网页。当前动态进度以actor-adapter/auxiliary-progress.json为准。

阶段验收：新回合已完成8次模型调用、3个真实动作、15.04物理秒后进入下一次完整推理等待。原回合/原批次证据零修改，原ledger62条row逐项相同、55仍inflight，核验见preservation-after-launch.json。新回合连续视频正在录制，尚未封口，不称已完成搬运。

四任务网页 `/api/dashboard` 已核验显示搬运episode-0003、3个动作、MuJoCo、等待完整推理，并独立列出最近动作时间，见web-dashboard-milestone.json。当前仍待UIowner完成的部分：在新回合运行时持续显示旧002中断历史，并完成新反馈owner固定路由切换；本分支已发两次有不同证据的恢复/启动交接，另按UIowner邀请写owner-acks/ground.json。旧手册/首次UI交接还引用已消失owner，不能据queue成功声称已切换路由。本分支没有修改UI/server或重启服务。此待交付项不阻塞已经正式运行的独立物理进程。

## 003复盘与004准备
003真实safety_stop；公开倾角25.005°越过25°，高度仍0.76562米；前一target_reached末段倾角上升。原result不改，追加episode003-review/REVIEW.md及review.json。完整18.04秒录像已被网页发现。独立004新skill/auth在artifacts/R021/api-ground-004，预算/控制预检通过，执行审批另行；持续监督实现见supervision。

## 004传输中断与005独立接续
004不是重启或物理安全失败：42完整调用、43缺终态且远端结果未知，19动作/83.04秒，完整录像83.08秒已网页发现。未知43及旧55原预留保持。复盘在episode004-review；005独立审批已执行，不是未知请求恢复。唯一原监督456959继续监听，绑定更新005。阶段详见STAGE-004-TO-005.md与BUDGET-ACK-005.json。

## 005真实HTTP429阻塞（覆盖此前在途快照）
005已结束：9完成调用/10发起、4动作/20.04秒。第10次原日志明确HTTP429；响应体原因未记录，不能判定具体为速率或额度。未知费用与002/55、004/43均保留各1217分。自动接续owner-state已blocked，现有watcher继续存活守候但不得自动发模型请求。需要网关限制解除的可核验证据及恢复条件；不查额度、不自动探测重试、不换账号、不新建006绕过。完整20.08秒录像与追加复盘在episode005-review。

005最终自诊断与交接 1789558131.7046015：episode005-review/REVIEW.md和FINAL.md已完成；20.08秒完整录像网页发现及Range206通过，4动作/20.04秒物理时间保持。原002/004/005清单与旧ground账本行无修改，三笔未知请求不重发。现有watcher456959存活持锁，005 actor已退出；owner-state=blocked绑定当前同一辅助owner日志。当前工程turn自然结束后保持可观测阻塞，恢复需HTTP429限制解除的可核验证据与安全条件，不进行额度/价格查询或自动探测。没有006；框架辅助queue和SIMPLE既有inbox交接完成，未声称消费ACK。

监督阻塞 1789558157.946809: blocked_owner_disposition；未自动重试，请核对supervision/watch-status.json。原物理计数保持。
