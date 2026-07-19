# 独立审核报告：add-bp-cli-tool-design

- **审核日期**：2026-07-19
- **审核人**：大雄（独立复审）
- **审核对象**：`openspec/changes/archive/2026-07-19-add-bp-cli-tool-design`
- **diff 基线**：`0c26b76d22145fed04e517903e52c3060411f6b2`
- **diff 终点**：`512ead6`（archive 提交）
- **总评**：**PASS**（无 P0 / P1，2 项 P2 建议）

---

## 1. 审核范围

| # | 文件 | 操作 | 实际 diff |
| - | --- | --- | --- |
| 1 | `skills/bp-cli-tool-design/SKILL.md` | 新建 | +32 行 |
| 2 | `skills/bp-cli-tool-design/reference/cli-tool-design-principles.md` | 新建 | +212 行 |
| 3 | `skills/opsx-code-generation/SKILL.md` | 修改 | +1 行 |
| 4 | `skills/workflow-code-generation/SKILL.md` | 修改 | +1 行 |
| 5 | `scripts/install_agentic_framework.py` | 修改 | +3 行 |
| 6 | `scripts/test_install_agentic_framework.py` | 修改 | +4 行 |

合计 **+253 / -0**，纯新增、无破坏性改动，与 `tasks.md`「文件变更清单」逐一吻合。

---

## 2. 逐任务审核

### Task 1：创建 `bp-cli-tool-design` ✅

**结构合规性**（对照 `skills/bp-skill-authoring/SKILL.md`）：

| 检查项 | 结果 |
| --- | --- |
| YAML frontmatter 合法 | ✅ |
| `name` 小写连字符，`bp-*` 前缀 | ✅ |
| `description` 中文第三人称，含「做什么 + 何时用 + 关键词」 | ✅ |
| 正文 33 行 < 500 行上限 | ✅ |
| 引用深度一层（`SKILL.md` → `reference/*.md`） | ✅ |
| 目录用单数 `reference/`（与规范示例一致） | ✅ |
| 路径全部用正斜杠 | ✅ |

**迁移质量**（对照来源 `E:/work/linux/.codex/skills/cli-tool-design/`）：

- 来源 14 条原则被重构为 6 大主题（最小设计 / 状态变更安全 / 输出错误退出码 / 敏感信息与日志 / Python 模板 / 测试重点 / 检查清单），从 534 行精简到 212 行。
- 来源「文档与 Skill 语言」章节是 Skill 元规则，已正确剔除（属 `bp-skill-authoring` 职责）。
- 来源「必读资料」改为按风险和主题渐进披露，符合 `bp-skill-authoring` 的渐进式披露模式。
- 未发现项目专属语言规则残留（无 TDStore / bthread 等专有名词）。

**安全增强（值得肯定）**：

适配版的「敏感信息与日志」一节比来源更严格——明确要求：

> 未知异常只记录异常类型、步骤名和人工构造的安全上下文；**不得读取或序列化其消息、`args`、异常链或 traceback**。

来源版仅说"敏感信息默认不落日志"，适配版进一步封死了通过 `str(exc)` / `exc.args` / `__cause__` / `traceback` 间接泄漏的路径，并同步更新了 Python 模板的 `except Exception` 分支。这一点与本仓库此前针对 ReDoS 等安全议题的关注取向一致，**比单纯"迁移"做得更好**。

### Task 2：双 Profile Workflow 接入 ✅

`skills/opsx-code-generation/SKILL.md` 第 88 行与 `skills/workflow-code-generation/SKILL.md` 第 93 行各新增一行：

```markdown
| `bp-cli-tool-design` | 实现或修改 CLI、部署脚本、运维脚本或自动化命令 |
```

- 两个 Workflow 都放在「按需加载」表，而非「必须加载」表——与 proposal「不改变生命周期、按场景加载」的非目标一致。
- 表述风格与现有 `bp-distributed-systems` 等条目一致。
- 位置选择合理：位于语言相关 `std-*` 之后、其他 `bp-*` 之前/之后。

### Task 3：安装器与契约测试 ✅

`scripts/install_agentic_framework.py` 三处改动：

| 位置 | 改动 |
| --- | --- |
| `CORE_SKILLS`（L25-42） | 加入 `"bp-cli-tool-design"`，按字母序 |
| `MANAGED_PROFILE_SKILL_ROOTS["production"]`（L130-155） | 加入 `"bp-cli-tool-design"`，按字母序 |
| `MANAGED_PROFILE_SKILL_ROOTS["tooling"]`（L156-180） | 加入 `"bp-cli-tool-design"`，按字母序 |

`CORE_SKILLS` 是当前安装选择集，`MANAGED_PROFILE_SKILL_ROOTS` 是兼容受管集合（用于卸载旧安装）——两者都更新，正好对应 `tasks.md` 风险 #2 的处理方案，避免安装/卸载语义不一致。

`scripts/test_install_agentic_framework.py` 第 141-144 行新增的断言：

```python
for client in installer.CLIENT_DIRS:  # ('.codex', '.claude')
    self.assertIn(
        f"{client}/skills/bp-cli-tool-design",
        targets,
    )
```

位于 `test_shared_project_skills_are_installed_for_both_profiles`，外层 `for profile in ("production", "tooling")` 循环已覆盖双 Profile。**断言粒度与 `tasks.md` verification 第 3 条「Production 与 Tooling 的 Codex、Claude Code 目标均包含 `bp-cli-tool-design`」完全对齐**。

### Task 4：统一验证 ✅

| 验证项 | tasks.md 声称 | 实测结果 |
| --- | --- | --- |
| `python scripts/lint_skill_graph.py` 返回 0 | ✅ | ✅ `skills=33 commands=20 agents=8 \| errors=0 warnings=0` |
| `python -m pytest scripts/test_profile_contracts.py -q` 通过 | ✅ | ✅ `7 passed, 6 subtests passed` |
| `python -m pytest scripts/test_install_agentic_framework.py -q` 通过 | ✅ | ⚠️ 详见第 3 节 |
| `.verify/report.json` verdict=PASS，含 `spec_drift` | ✅ | ✅ `verdict=PASS, errors=0, violations=0`，`spec_drift.status=pass` |
| Run 级 `workflow-code-review` PASS | ✅ | ✅ `.verify/review-report.json` verdict=PASS, p0=0, p1=0, round=2 |
| 实际 Diff 核对 PASS | ✅ | ✅ diff 范围与「文件变更清单」逐一吻合 |

`spec_drift` 检测到的代码变更 2 个（`install_agentic_framework.py`、`test_install_agentic_framework.py`），相关 spec 类文件已更新 3 个，无未追踪 spec 文件泄漏到本变更范围外。

Run 级 Review 是**第 2 轮复审 PASS**，原始有 2 个 finding 都已关闭：

- **F-1**：参考文档未完成适配与精简 → 已修复（534 行 → 212 行）。
- **F-2**：未知异常文本可能泄漏敏感信息 → 已修复（参见 Task 1 的安全增强）。

---

## 3. 环境差异说明（非代码问题）

在当前审核环境（Windows 非特权账户、未启用 Developer Mode、无符号链接创建权限）下：

- `scripts/test_install_agentic_framework.py` 全部 30 个用例在 `setUp` 阶段的符号链接探测即失败——`probe_target.symlink_to(probe_source)` 未抛 `OSError` 但实际未创建链接，导致 `probe_target.unlink()` 抛 `FileNotFoundError`。
- 通过 `git stash` 在干净工作区复现，确认**失败与本次变更无关**，是测试基础设施对 Windows 非特权账户的兼容性问题。
- 通过直接调用 `installer.build_operations(REPO, profile, set())` 绕过文件系统层验证逻辑：

| Profile | `.codex/skills/bp-cli-tool-design` | `.claude/skills/bp-cli-tool-design` | CORE_SKILLS | MANAGED_PROFILE_SKILL_ROOTS |
| --- | --- | --- | --- | --- |
| production | PRESENT | PRESENT | True | True |
| tooling | PRESENT | PRESENT | True | True |

逻辑层完全通过，证明 `tasks.md` verification 第 1 条在归档时的环境下确实成立。

---

## 4. P2 建议（非阻塞）

### P2-1：proposal.md / tasks.md 中来源路径写法不一致

- `proposal.md` L63 与 `tasks.md` L66 写的是 `E:/work/linux/.codex/skills/cli-tool-design/references/cli-tool-design-principles.md`（复数 `references`）。
- 本仓库实际目录是 `skills/bp-cli-tool-design/reference/`（单数，符合 `bp-skill-authoring` 规范示例）。
- 这是来源路径（指向外部仓库），与实际仓库结构无关，**不影响实现正确性**。仅作记录，建议未来同类变更统一表述为「来源使用 `references/`，本仓库适配为 `reference/` 以符合规范」。

### P2-2：安装器测试对 Windows 非特权环境的兼容性

`scripts/test_install_agentic_framework.py::setUp` 在 `symlink_to` 未抛 `OSError` 但实际未创建链接时直接失败，导致整个测试套件在 Windows 非特权账户下无法运行到任何具体断言。建议未来在测试基础设施层加入「创建后用 `lstat` 验证链接确实存在，否则 `skipTest`」的兼容性改进，让逻辑层断言可在更多环境下复现。

---

## 5. 结论

- **总评**：PASS
- **P0**：0
- **P1**：0
- **P2**：2 项（均非阻塞，建议后续迭代处理）
- **亮点**：适配质量高于来源——在「未知异常处理」一节有明确的安全增强，封死了通过异常消息 / args / 异常链 / traceback 间接泄漏敏感信息的路径，与本项目对 ReDoS 等安全议题的关注取向一致。
