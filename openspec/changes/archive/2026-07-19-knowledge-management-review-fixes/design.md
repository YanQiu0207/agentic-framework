# 知识管理审查问题修复设计

## 1. Finding 复核结论

| Finding | 结论 | 处理 |
| --- | --- | --- |
| P0-1 | 存在 | 将 `relative_to` 改为单个 `Path` 参数，并增加所有来源区域的定向测试 |
| P1-1 | 存在 | 在文档扫描前预计算 Legacy 路径的字符串和解析后路径 |
| P1-2 | 存在 | `main()` 捕获 `OSError`、`UnicodeError` 和递归遍历错误，统一返回退出码 `2` |
| P1-3 | 存在表述偏差 | 保留历史文件原有 `Archived`、`Implemented` 等生命周期状态；把验收项改为准确的目录级 `Superseded` 入口和逐文件映射 |
| P1-4 | 存在证据缺口 | 增加两个项目目录与公共库桥接边界测试；明确这是主动检索范围约束，不是 ACL |
| P1-5 | 存在 | Fast-Path 调用交付门时强制传结构化知识影响结论；「无影响」必须附理由 |
| P1-6 | 存在 | Verification 扫描长期知识 `meta.yaml`，对 Git 来源过期或不可解析输出非阻塞 `WARN` |
| P1-7 | 存在 | 提取共享 Markdown 链接解析 Helper，统一 Scheme、Fragment 和 `file:` 语义 |
| P1-8 | 存在 | 在写入路由与代码派生文件清单中明确 `meta.yaml` 归属 |

## 2. 关键设计

### 2.1 Markdown 扫描

共享 Helper 只负责解析 Markdown 链接目标，不负责公共库边界判断。任意非空外部 Scheme 返回 `None`，`file:` 返回本地路径；普通相对路径相对来源文档解析。迁移扫描使用可剪枝且不跟随目录链接的遍历，避免进入 `.git`、`.venv`、`.worktrees` 和 `node_modules`。

### 2.2 Fast-Path 交付门

Fast-Path 必须调用：

```text
check_delivery.py --knowledge-impact hit|none [--knowledge-impact-reason <理由>]
```

`none` 缺少理由时失败；Standard Change 仍由 Proposal、Tasks 和 Archive 知识同步表证明，不重复要求该参数。

### 2.3 来源新鲜度

Verification 读取 `openspec/specs/**/meta.yaml` 中的 `source_ref` 和 `source_paths`。对每个来源路径读取最近修改 Commit；若该 Commit 不是 `source_ref` Commit 的祖先，说明来源路径在知识生成后发生变化，输出 `WARN`。无法解析 Ref、路径或 Git 关系同样告警，但不改变总判定。

## 3. P2 处理

- 接受：遍历剪枝、符号链接不跟随、路径深度显式校验、公共条目单次读取缓存、共享 Standard Artifact Archive/Delta 测试、独立 Profile 与控制器合同测试、移除测试文件 Shebang、补充 `custom/` 权威清单。
- 不合并 Frontmatter Helper：两个实现分别服务 Change 机器合同和公共库顶层元数据，当前字段语义及错误报告不同；强行共用会扩大耦合，暂不构成缺陷。
- Follow-up Note 已由迁移文档说明「脚本不能证明泛化或脱敏，必须人工 Review」；本次补充用户确认边界措辞，不引入自动审批假象。
