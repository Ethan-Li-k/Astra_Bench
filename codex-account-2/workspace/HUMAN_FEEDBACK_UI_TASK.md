在第二账号 Astra/xhigh 完成一个有边界的工程任务：把用户的失败纠错流程做成实际可用的问答/填空标注界面。先读 AGENTS.md、ref/USER_UPDATE_20260916_HUMAN_FEEDBACK.md、human-feedback/README.md、human-feedback/cases/H001/case.json。不要读凭据、不要调用付费API、不要启动或改任何仿真；不写rsi/tools/skills公共控制代码或其他campaign。你独占 human-feedback/tools、human-feedback/ui、human-feedback/annotations、human-feedback/reviews 等新文件；现有cases/H001作为只读输入，桌面正在等待用户对H001的回答。

目标：用户与策略看到相同公开证据；用户只指出图像线索、判断分歧、下一规划方向和可观察的阶段门槛，agent负责具体复现和实验。现在没有用户标签，禁止预填答案或把模型假设称为用户意见。

界面要求：
1. H001有真实8对左右目图，默认停在动作59；显示当前步骤/模拟时间/闭合度、之前动作、下一动作，并明确原图来自当时策略输入。优先大图，可切换前后步骤/左右目，完整画幅不裁掉边缘。额外机器人状态/标定/原始公开动作可展开。不要读host trace或物体真值。
2. 分阶段：先独立看图回答，再主动展开已冻结的agent判断摘要与后果；用户已经知道该例失败，要标注并不称盲测。判断摘要包括事实、假设、缺失信息、预期现象，不输出私有思维链。不可把静止帧当连续录像。
3. 用case.json的针对性问题，核心只要 observation/priority/gate 三项，可选counterexample和置信程度。保留用户原话，之后agent提炼另存rule；支持“不足以判断/需要另一视角”。用户提交必须实际持久化，返回可核验annotation ID；不能仅浏览器临时状态然后声称已保存。
4. 使用已有标准库、浏览器，不装依赖。优先极简localhost页面/服务（仅127.0.0.1、路径白名单、JSON提交、无shell插值、不向外网发数据）；所有图片/标注只在RSI。按canvas技能另提供单文件 .canvas.tsx 可交互副本/阅读入口（所有数据内联、唯一import cursor/canvas，SDK在~/.cursor/skills-cursor/canvas/sdk），用户要求全部文件RSI覆盖skill的Mac默认目录。若当前Codex不能渲染canvas，主要交付必须是已在浏览器真实验证可用的页面，不能用未运行的canvas代替工作界面。Canvas无需维护独立生产标注存储，避免两个权威源。保持实现简洁，不建立通用平台。
5. 记录annotations/不可变提交，case/source哈希绑定；新规则为human_proposed，原话与agent归纳分离。提供最小导入入口接收桌面转录的JSON答案，不自动发模型调用。记录用户是否看过agent假设/结果，用于后续公平评价。不要由UI执行机器人动作、skill发布或启动复现。
6. 针对来源缺失/篡改、无答案、重复提交、目录越界做必要测试；实际提交一次标记synthetic的测试不污染production人工反馈记录。长任务tmux+tee，不重复启动已有端口。完成保存human-feedback/delivery.json，包含URL、启动方式、PID/session、测试、真实用户提交数及局限。不要在交付时停止页面服务器。

同时写一个简洁的review protocol：收到用户纠正后，公共证据对齐→原失败复现（旧控制/同初态/历史，不能把回放算新成功）→只修改一个判断规则的新物理回合→仍失败再向用户问一个区分性问题→新seed/场景验证→按机制晋升skill。未知复现状态不可冒称已复现。公共skill唯一发布者仍SIMPLE supervisor。已自主Direct与human_feedback_assisted分层统计，不声称GPT权重被训练。

借鉴GPT-as-Policy的短skill/历史及RoboRSI human_review的错误分层，但其expert_trajectory_reflection读取contact_points/oracle的做法不适用，不复制。桌面已问API来源和IKEA门槛，以及H001两个问题；不要重复问用户。该界面完成后自然结束，页面与SIMPLE工作继续。
