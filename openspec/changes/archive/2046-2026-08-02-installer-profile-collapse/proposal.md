# Proposal：安装器 Profile 常量坍缩与失效交叉污染检查清理（Quick Draft）

**作者**：YanQiu0207
**日期**：2026-08-02
**变更**：installer-profile-collapse
**状态**：Archived

---

## 1. 问题与目标

### 问题

change 2045 退役 `opsx-*` 后，Production 与 Tooling 在文件安装层面已合并为一套 `workflow-*` 入口。`openspec/specs/backend/framework/install-agentic-framework/overview.md` 第 27 行明确：「`--switch-profile` 切换只改 manifest 字段，不增减已安装文件（两个 Profile 的文件集合已一致）」。

但 `scripts/install_agentic_framework.py` 仍保留合并前的两套等价常量：

- `PRODUCTION_SKILLS`（L46）与 `TOOLING_SKILLS`（L53）逐元素相同
- `PRODUCTION_COMMANDS`（L68）与 `TOOLING_COMMANDS`（L77）逐元素相同
- `MANAGED_PROFILE_SKILL_ROOTS`（L132）两个 key 指向内容完全相同的 `frozenset`
- `MANAGED_PROFILE_COMMAND_FILES`（L184）同样两份相同

由此衍生的 `_forbidden_entry_paths`（L895）+ `_cross_pollution_errors`（L905）原本防止「Production 装出 Tooling 入口／反之」。两个 Profile 入口集合自 change 2045 起完全相同后，`install()` 中的两处调用退化为不同形态：

- **装前调用** `_cross_pollution_errors(target, profile, old_paths)`：检查目标是「对面入口」（合并后等于本 Profile 自己的 delivery 入口，非空 24 条）；fresh install 时磁盘无残留、reinstall 时被 `old_paths` 覆盖，恒返回空集，属失效死逻辑。
- **装后调用** `_cross_pollution_errors(target, profile, set())`：在所有受管链接创建完成后检查，24 条 delivery 路径全部 `lexists` 且不在空集内，**恒返回全部 24 条并抛 `FileExistsError("Profile installation is contaminated")`**——这是 change 2045 后退化的 always-fail 隐患：任何真实（非 dry-run）`install()` 都会在此回滚并失败。因 `install()` 全路径测试被符号链接能力守门，在无 Developer Mode 的 Windows 上 skip，该隐患未被 2045 当场捕获。

删除这两处既清理死逻辑、也修复上述 always-fail 隐患。原「拒绝替换未受管目标」的前置防护由 `_preflight`（L987）独立承载，不受影响。

### 目标

- 把四组等价常量坍缩为单一集合，消除「一处改、另一处忘改」的静默漂移风险。
- 删除失效的交叉污染检查，避免误导后续维护者以为它仍在防护。
- 把「两个 Profile 安装内容等价（除 `validate_change.py`）」固化为机器断言。
- 修正 README 两处与实际安装行为不符的措辞。

### 非目标

- 不改 `--profile production|tooling` CLI 参数、manifest 的 `profile` 字段、registry 的 `profile` 字段——它们是运行时门禁（`governance_profile.py`、`governance_guards.py`）的硬契约。
- 不改 `validate_change.py` 仅 Production 安装（符合 `framework-unification.md` §5.3／§14.2，有意保留）。
- 不改 `frontend` pack 仅 Tooling（符合 §11，有意保留）。
- 不调整 manifest／registry schema 版本。

### 验收标准

1. `install_agentic_framework.py` 不再出现 `PRODUCTION_SKILLS`、`TOOLING_SKILLS`、`PRODUCTION_COMMANDS`、`TOOLING_COMMANDS` 四个符号；`MANAGED_PROFILE_SKILL_ROOTS`／`MANAGED_PROFILE_COMMAND_FILES` 不再按 profile 分 key。
2. `_forbidden_entry_paths` 与 `_cross_pollution_errors` 函数及其在 `install()` 中的两处调用删除。
3. 现有 `scripts/test_install_agentic_framework.py` 与 `scripts/test_profile_contracts.py` 全部通过。
4. 新增测试断言 `build_operations(production, set())` 与 `build_operations(tooling, set())` 的目标路径集合完全相同，唯一差异为 Production 多出 `.codex/scripts/validate_change.py` 与 `.claude/scripts/validate_change.py`。
5. README L113 不再宣称「复制根目录 `scripts/` 目录」；L16-28 区间点明两个 Profile 安装内容相同、差异只在运行时治理强度。

## 2. 设计方案

### 2.1 整体方案

合并等价常量 + 删死逻辑，纯实现追平已合并的设计，无新决策。

### 2.2 核心组件

- `DELIVERY_SKILLS`：合并自 `PRODUCTION_SKILLS` ∪ `TOOLING_SKILLS`（两者相同，取一份）。
- `DELIVERY_COMMANDS`：合并自 `PRODUCTION_COMMANDS` ∪ `TOOLING_COMMANDS`。
- `MANAGED_SKILL_ROOTS`：单一 `frozenset`，合并自两 key 同值的 `MANAGED_PROFILE_SKILL_ROOTS`。
- `MANAGED_COMMAND_FILES`：单一 `frozenset`，合并自 `MANAGED_PROFILE_COMMAND_FILES`。
- `_selected_names`：去掉 `if profile == "production" … else …` 分支，统一 `update(DELIVERY_*)`。
- `_manifest_allowed_path`：改用 `MANAGED_SKILL_ROOTS`／`MANAGED_COMMAND_FILES`，保留 `profile` 参数仅供 `scripts/validate_change.py` 规则使用。

### 2.5 关键权衡

- **为什么不删 `profile` 参数**：`_manifest_allowed_path` 的 `scripts` 分支仍需区分 Production（`validate_change.py` 仅 Production），且 manifest 校验、registry 校验、CLI choices 都硬依赖 profile 取值。profile 在「安装内容选择」上已失效，但在「运行时治理 + 两处有意差异」上仍是契约。
- **为什么直接删 `_cross_pollution_errors` 而非重定义语义**：它的原始语义（防两套不同入口混装）已不存在；装前那处是恒为空的死逻辑，装后那处是 change 2045 后退化的 always-fail 隐患（详见 §1），`_preflight` 已覆盖「拒绝替换未受管目标」的前置防护。重定义会引入新语义，超出本次清理范围。

## 3. 知识影响

- MODIFIED `openspec/specs/backend/framework/install-agentic-framework/overview.md`：补记安装器代码已坍缩为单一 delivery 常量（spec 文本已说「文件集合一致」，本次让代码追平文本，不改变 spec 语义）。

## 4. 运维

无运维影响，纯代码／文档清理。

## 5. 参考资料

- `openspec/specs/backend/framework/install-agentic-framework/overview.md`（§白名单统一 change 2045）
- `openspec/specs/backend/engineering/tech/framework-unification.md` §3.2、§8.1、§14.2
