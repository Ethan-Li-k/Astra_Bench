import { Stack, Row, Grid, H1, H2, Text, Table, Card, CardBody, Button, Pill, Divider, useHostTheme, useCanvasState, useCanvasAction } from "cursor/canvas";

const root = "/home/galbot/lizekai/RSI";
const roles = [
  ["Manager", "新指令、资源变化、任务切换、晋升请求", "单写入者；真实门槛；版本发布与回滚"],
  ["Planner", "新机制、前置条件改变、重大失败", "可检验子目标；真实可调用技能；单项变化"],
  ["Engineer", "观测 → 有界动作 → 实测", "完整推理；动作 ACK；独立重置；全回合录像"],
  ["Reviewer", "回合结束、接口改变、共享晋升", "host 证据优先；事实与假设分离；回归验收"],
];
const layers = [
  ["共同控制", "坐标、单位、时序、腕/手指校准", "接口/机器人不同先重验"],
  ["Locomotion", "站稳、移重、步进、接近、绕障", "步行未验证，不能作为已掌握能力"],
  ["交互机制", "抓放、容器、接触关节物", "按机制匹配，排除负迁移"],
  ["任务实例", "推/拉、可达侧、铰链、把手/锁舌", "门的名称相同不足以迁移"],
];
const findings = [
  ["Selector", "Engineer 调用点是 >50 技能时执行前一次", "当前少技能先确定性过滤，无需新模型调用"],
  ["History", "成功回合使用过就记分；git commit 不覆盖未提交改动", "内容+依赖哈希、失败分母、reset 去重"],
  ["Validator", "临时覆盖共享 skill 后还原", "隔离副本验证，回合中 pin 版本"],
  ["Wiki", "失败观察与解释分开、旧条目归档", "管理同意仍不等于物理验证"],
];

export default function RoleSkillReview() {
  const theme = useHostTheme();
  const [tab, setTab] = useCanvasState("r020-review-tab", "角色");
  const open = useCanvasAction();
  return <Stack gap={18} style={{ padding: 24, maxWidth: 1100, color: theme.text.primary }}>
    <Text tone="secondary" size="small">RSI · Account 2 · 2026-09-16 本地代码评审快照</Text>
    <H1>同一 Astra 分工，学习保存在 skill 与证据中</H1>
    <Text>保留现有 supervisor 和每环境唯一执行者；按事件规划与审查。当前不训练四套模型，不引入 MoE。</Text>
    <Grid columns="2fr 1fr" gap={20}>
      <Stack gap={8}>
        <H2>最短闭环</H2>
        <Text>事件 → 前置条件过滤 → 选择版本 → 物理执行 → host 审计 → 本地经验</Text>
        <Text tone="secondary">共享提案先隔离验证，再做匹配任务与原抓取回归；SIMPLE supervisor 唯一发布。失败、反证和旧版本保留。</Text>
      </Stack>
      <Card><CardBody><Stack gap={8}>
        <Text weight="semibold">IKEA 保持待机</Text>
        <Text>推门尚未达到 3 次真实独立成功门槛；预算已授权：全任务合计10000元，每1500元汇报；来源和计费仍待核实。</Text>
        <Text tone="secondary" size="small">主控已真实 ACK，包含预算文件；当前状态见 JSON。未启动探索。</Text>
      </Stack></CardBody></Card>
    </Grid>
    <Divider />
    <Row gap={8}>{["角色", "相似性", "参考实现"].map(x => <Pill key={x} active={tab === x} onClick={() => setTab(x)}>{x}</Pill>)}</Row>
    {tab === "角色" ? <Stack gap={10}><H2>事件触发与角色验收</H2><Table headers={["职责", "何时触发", "验收"]} rows={roles} /></Stack>
      : tab === "相似性" ? <Stack gap={10}><H2>四层技能匹配与排除条件</H2><Table headers={["层", "共享内容", "边界"]} rows={layers} /></Stack>
      : <Stack gap={10}><H2>可借鉴机制与需要修正的限制</H2><Table headers={["模块", "本地代码发现", "RSI 设计"]} rows={findings} /></Stack>}
    <Text tone="secondary" size="small">来源：GPT-as-Policy gpt-only SKILL / teacher_context / EEF contract；RoboRSI manager、planner、engineer、reviewer、selector/history、validator/wiki。完整引用与源文件哈希在报告和 source-manifest.json。</Text>
    <Row gap={8} wrap>
      <Button onClick={() => open({ type: "openFile", path: root + "/ref/ACCOUNT2_ROLE_SKILL_REVIEW.md" })}>阅读引用报告</Button>
      <Button onClick={() => open({ type: "openFile", path: root + "/artifacts/R020/coordination-status.json" })}>查看当前门槛与 ACK</Button>
      <Button onClick={() => open({ type: "openFile", path: root + "/tools/coordination/README.md" })}>查看恢复入口</Button>
    </Row>
  </Stack>;
}
