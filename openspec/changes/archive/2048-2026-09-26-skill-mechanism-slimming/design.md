# 设计方案

## 4.1 方案概览

只维护一条普通交付路径。轻量任务可无 Proposal／Tasks，但仍使用 integration Review（Tooling 为 standard，Production 保留 strict）、完整独立 Verify、知识影响结论与 Native Delivery Verdict；有任务文件时仍检查终态、归档和知识同步。旧的隐式 Fast-Path 调用拒绝并提示迁移，禁止弱证据继续放行。

复用安装器 `--with` 与 manifest.packs。新增 `runtime` 和 `knowledge-advanced` 能力标记；前端与 `open-code-review` 原本已选装，无需重建。新安装默认核心包。普通重装继承已选能力，显式增减由参数表达。旧清单用明确版本标记区分并继承此前默认可用的 Runtime／高级知识能力；已禁用的新清单不得被刷新重新启用。

## 4.2 组件边界

- 安装器维护包选择、迁移、刷新和只读能力查询，不从目标清单加载可执行代码。
- 共享 `scripts/framework_packs.py` 提供 `enabled_packs(repo: Path) -> set[str]` 与 `require_pack(repo: Path, pack: str) -> None`。缺失或非法安装清单在受管项目失败关闭；直接运行受信框架源码（同时存在安装器、核心 Skill 等标记且无安装清单）允许现有完整能力，不能让普通无安装目录假冒源码根。
- `workflow_control.py` 在需要 Runtime 的 route 和 init-run 前使用共享能力检查。Runtime 仍在严格风险、并行隔离、恢复、跨宿主或明确审计时要求；缺包停止并提示启用，而不是降低 Review 档位。
- 高级知识能力控制项目初始化的 SVN／外置模式及公共知识晋升入口；正常项目内知识读取、冲突保护和归档保持核心能力。
- Core Skill 保留明确条件和停止规则；详细 Runtime／高级知识规则放专门参考文档，普通路径无需全文读取。

## 4.3 交付与报告

删除 Fast-Path 独立裁决实现及其活跃调用，使用 `--native-delivery`。保留必要的未知旧调用报错提示，不承诺旧弱证据可继续通过。

沉淀内部仍逐项判断。未命中只给一句结论和具体理由；命中时只列命中项、目标路径与同步状态。机器 `knowledge-impact` 与理由不变。遥测机器字段不改名。

## 5. 规则冲突解决

1. 测试内嵌路径进入 Step 4，仍跳过独立确认与收尾 Review。
2. Quick Design 的批准可复用，但代码生成仍先经过路由及 Verify 配置检查。
3. React 使用活跃 Proposal、存在时的 Design／Delta 和必需 UI 规格；旧 spec 仅迁移读取。
4. Design 的 4～9 为历史局部编号，可与 Proposal 编号重叠；跨文件必须带文件名，不重编号。

## 6. 风险控制

旧安装兼容、Production 的严格审查下限、运行证据真实性和用户文件保护优先。只删除本次明确退役的兼容实现；不清理无关旧代码，不增加复杂配置系统。

## 7. 验证

安装选择、继承、显式移除、旧清单迁移、非法清单失败关闭；新轻量交付、旧路径拒绝、伪造 Verify 拒绝、有／无 Tasks 对称校验；Runtime 缺包阻止 dispatch；Skill 规则与引用图；全量 `python -m pytest scripts -q` 与 UTF-8／CP936 检查。
