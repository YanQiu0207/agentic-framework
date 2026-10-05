# change 2048 真实任务效果记录（Task 16）

**日期**：2026-10-05。**环境**：隔离实验室（`~/2048-task16-lab`），框架经安装器以目录链接装入 target（tooling）与 target-prod（production），全部命令经安装入口（`.claude/skills/...` 链接）真实执行；SVN 1.14.5 本地仓库。**口径**：与 2028 试点一致——只记录实际执行的命令与输出，不以估算补数；缺失记 `unknown`。主会话 token 不可分离计量，记 `unknown`；子代理 token/duration 为 harness 实测。

## 五类真实任务

| 任务 | 类别/档位 | 验证（真实 v2） | 评审（真实子代理） | 返工 | 交付门（逐字结论） | 门耗时 | 评审子代理 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 修复 calc.sub 运算符笔误 | 小修复 / lightweight（Fast-Path 别名） | PASS，subject 绑定 | PASS，1×P2（测试覆盖广度） | 无 | `fast-path-pass`（5 checks） | 0.4s | 56s / 18.6k tok |
| T2 新增 mul（类型守卫） | 普通功能 / standard | PASS | PASS，0 finding | 无 | `native-delivery-pass`（10 checks） | 1.3s | 63s / 19.5k tok |
| T3 add/sub/mul 统一 int/float 守卫 | strict / 五维+独立 Judge | PASS（修复后重验 ×2） | 首审 2×P1+12×P2 → 修复 → 定向复轮 1 PASS → Judge 终裁 PASS（r1，三项独立性声明入 Verdict） | 1 轮（契约措辞对齐+docstring+错误消息可诊断化+测试扩展 10→20） | `native-delivery-pass`（10 checks，strict） | 1.6s | 五维 51–135s/17–19k each；复审 69s/18.5k；Judge 202s/49k（重绑 ×2：90s/56k、32s/58k） |
| T4 stringutil+listutil 两 worktree | 并行 Git / standard | PASS（集成树） | PASS，0 finding | 无 | `native-delivery-pass`（10 checks）；两次 --no-ff 串行合并，无冲突 | 1.6s | 29s / 14.8k tok |
| T5 shout 增加 excited 参数 | SVN 串行 / standard | PASS ×3（改前/文档后/提交后 r2） | PASS（重绑 ×2：主体随文档与提交演进） | 无代码返工；2 次「内容主体已变」门拒收→按流程重取证（正确拦截） | 先 `svn-pending-commit`（10 checks，显式「不是正式交付 PASS」），授权提交 r2 后 `svn-revision-verified`（10 checks，revision_subject 绑定） | 2.9s / 3.8s | 157s/36.7k（重绑 30s/38.2k、32s/39.4k） |

命令与产物（每任务实际执行）：`python <installed>/verify.py --report … [--diff-base <H0>]`（2.2–3.1s/次）；`python <installed>/check_delivery.py …`（0.4–3.8s/次）；T5 另有 `svn add/commit/update`（提交只在授权步骤，门全程只读）。产物：每任务 verify-report.json、review.json、verdict.json（T5 两份：pending+revision）。

## Runtime 对照（显式启用）

- 路由：`route --execution-mode runtime` → `runtime-run`（reason: explicit-execution-mode）；同任务默认路由 → `native-delivery`（零升级原因）——自动升级已消除。
- `init-run`：真实成功（run-context.json + config_digest 落盘，adapter 探测经 `--adapter-command python <abs>` 分词传参；首次失败为单字符串传参所致）。
- Run-bound Verify：`verify.py --run-dir … --task-id 1 --attempt 1` → v1 Envelope Artifact `verify-1-1.json` PASS（Runtime v1 合同不变）。
- Run 级 finalize/Trust：未在实验项目完成（需 Run 级 strict Review Envelope）；由全量回归（`test_runtime_workflow/test_runtime_trust/test_runtime_schema`，804 passed 矩阵内）承担合同级证据——与 2028 试点口径一致，不冒充 Run 级审计。
- 刷新保护：重装后用户文件（USER-NOTE.md）与既有 run 目录逐字保留，manifest profile 不变（安装测试固定断言）。

## 默认零 Runtime 副作用

T1–T5 全程无 `init-run`、无能力探测、无 Journal/Manifest 写入（`.agentic-framework/runs/` 仅在显式对照时出现）。

## 过程事实（如实记录）

- 门的三方主体拦截真实发生 3 次：T3 AGENTS.md 后加、T5 变更文档后加、T5 提交后主体基准变化——每次按流程重取证后通过，无绕过。
- `.pytest_cache`/`__pycache__` 两次触发 Git-clean/SVN 残留拦截（正确）；实验项目 .gitignore 未含 `__pycache__` 是真实摩擦点，记为 follow-up（不阻塞）。
- 一次 API 5 小时限额中断（T5 首次评审被杀，重派完成；主会话恢复）——人工介入：仅该中断的等待，其余 0。
- 主会话墙钟总量 unknown（含限额中断）；各门/验证/评审耗时见上表。
- 修复轮次：T3 一轮（P1×2 → fixed）；复审上限内收敛。

## 结论

五类任务在安装入口上端到端走通四种 v2 终态（fast-path-pass、native-delivery-pass×3、svn-pending-commit、svn-revision-verified）与 strict 独立 Judge 链；默认路径零 Runtime 副作用；SVN 两段式交付语义（待提交≠正式交付）在真实门输出中可辨。不据此承诺固定耗时/token 降幅（主会话计量缺失）；数据供后续对照，不做删除 Runtime 的依据。
