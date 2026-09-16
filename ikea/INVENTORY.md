# IKEA 交互候选库存

范围：独立 usd-core 26.8 已只读打开原 Flatten（402 prim）与苹果子资产；非 Flatten 主层因缺 FBX 插件为部分组合。所有源文件哈希前后不变。没有 Isaac 执行成绩。

- brown_bedroom_door：照片右侧棕色卧室门，Door_West已有静态视觉对应。
  原源属性：{"joint": "none found in successfully composed Flatten stage", "collision": "target door/fridge meshes have no PhysicsCollisionAPI in Flatten stage", "mass": "not authored; runtime absent/unknown", "latch_linkage": "none found in successfully composed Flatten stage"}。
  适配项：保留mesh38/39门板及40独立把手几何；建立声明的无锁舌铰接变体，验证轴/净空/闭门reset，质量摩擦为适配假设。
- other_door：Door_East另一扇同名卧室门；是否洗手间门未证实。
  原源属性：{"joint": "none found in successfully composed Flatten stage", "collision": "target door/fridge meshes have no PhysicsCollisionAPI in Flatten stage", "mass": "not authored; runtime absent/unknown", "latch_linkage": "none found in successfully composed Flatten stage"}。
  适配项：不得仅凭命名声称洗手间门；保留视觉身份待核；门板与把手分离不证明可动或联动。
- table_apple：已确认Props/apple/apple.usd及Flatten内pingguo_straightened网格，纹理pingguo_Color.jpg。
  原源属性：{"joint": "free dynamic rigid body schema, no explicit joint", "collision": "enabled, authored mesh approximation=sdf", "mass": "not authored; simulator effective default unknown", "latch_linkage": "not applicable"}。
  适配项：保留USD苹果网格与初始位姿；MuJoCo碰撞近似与质量需明确标注并验证桌面支撑。
- fridge：Refrigerator1及两片上门、两层抽屉。
  原源属性：{"joint": "none found in successfully composed Flatten stage", "collision": "target door/fridge meshes have no PhysicsCollisionAPI in Flatten stage", "mass": "not authored; runtime absent/unknown", "latch_linkage": "none found in successfully composed Flatten stage"}。
  适配项：门126/127分离；铰轴/内腔/门封/质量未知；抽屉128—131分离；滑轨关节未知。
- cabinet_drawers：Counter/Drawer3及橱柜拉手，具体移动边界需核对。
  原源属性：{"joint": "unknown", "collision": "unknown", "mass": "unknown", "latch_linkage": "unknown"}。
  适配项：确认抽屉整体壳体与把手所属关系；建立滑动碰撞与限位前不能称可交互。

当前派生门：MuJoCo usd-aligned-door-west-no-latch-v3，原FBX视觉几何整体平移(-3.105,3.02,0)m匹配USD；保留原苹果几何/初态。门新增铰链、20kg质量/阻尼/摩擦，门把手刚性附着，未建模锁舌；这些是显式工程假设，不是原源物理。门框口用原形状三盒分解；苹果由SDF改凸网格且质量假设0.18kg。详情见场景manifest。

验证：6s闭门/站立与11s真实接触球探针诊断已完成，均无任务成功信用；策略另记。原源缺少门Joint不等于已经证明真实门没有锁舌。
