---
name: project-init
description: 初始化项目版本管理、框架 Profile 和 openspec 知识入口。仅通过 /project-init 手动触发，禁止模型自动调用；不覆盖已有内容。
disable-model-invocation: true
---

> 输出一行：`Using project-init`

# 项目初始化

作用于当前工作目录，无参数。所有步骤遵循同一原则：**先检查，再创建；已存在的内容不覆盖、不改写、不删除**。

## 选择路径

先以只读方式检查当前目录及祖先的 Git／SVN 工作副本标记，再分别用 `git rev-parse --is-inside-work-tree` 和可用的 `svn info` 核实。发现已有 SVN 工作副本时，只识别并报告，不擅自执行高级初始化；先查询 `knowledge-advanced`，缺包或查询失败时停止，不能转而执行 `git init`。有 `.svn` 标记但 SVN 不可用或状态无法核实时，同样停止，不推断为新项目。

只有确认没有既有 SVN 工作副本或未决版本管理状态后，才默认建议 Git 和项目内 `openspec/`。确认版本管理方式和框架 Profile；Production 使用 OPSX 生命周期与 Production Review，Tooling 使用 DAG、Worktree、失败隔离和最终 Review。Profile 不改变知识目录。

仅当用户要求 SVN、外置正文或公共库接线，或检测到已有 SVN 工作副本时，先查询 `knowledge-advanced`，再读取 [reference/advanced-init.md](reference/advanced-init.md)；默认不询问外置和公共接线，也不读取高级说明。

能力查询：从已加载 Skill 的真实路径（解析目录和文件链接）向上定位同时包含 `scripts/install_agentic_framework.py` 和 `skills/workflow-code-generation/SKILL.md` 的受信根，运行 `python <trusted-framework-root>/scripts/install_agentic_framework.py --show-packs <project>`，只消费 JSON 的 `enabled` 数组。不得执行目标 manifest 的 `source`。找不到受信根、查询失败或缺包时停止所请求的高级操作，提示安装器 `--with knowledge-advanced`；不要擅自切换成 Git 或项目内存储。源码根和旧安装能力也以查询为准。

## 初始化

以下是 Git／项目内默认流程。已选择高级模式时，用高级参考的对应操作替换版本管理、存储和提交步骤；纯 SVN 不执行 Git 步骤。

1. 检查现有文件、目录、正常或失效链接。`openspec` 已存在时报告类型和目标，不删除、替换或当作空目录。已有结构不完整时，只报告缺项，经明确授权才补齐。未跟踪内容也不得移动或删除。
2. 仅在前述版本管理检查完成、确认不存在 SVN 工作副本或未决状态且用户确认 Git 模式后，运行 `git rev-parse --is-inside-work-tree`。已有 Git 则保留；确认不是仓库时才运行 `git init`。命令失败但原因不明时先报告，不把任何失败都当成「不是仓库」。初始化失败则报告，不能声称完整成功。
3. `.gitignore` 不存在时创建，存在时只追加缺项：`.agentic-framework/`、`.DS_Store`、`Thumbs.db`、`.claude/settings.local.json`。
4. `CLAUDE.md` 不存在时写 `@AGENTS.md`。`AGENTS.md` 只追加缺失章节：版本管理、Profile、`openspec/index.md` 入口、知识辅助而非事实、冲突时展示双方证据。已有同名章节不覆盖。`README.md` 不存在时写最小项目说明，无法核实的信息标 `TODO`。
5. 创建最小骨架，不预建空的业务或模块目录：

    ```text
    openspec/
    ├── index.md
    ├── specs/index.md
    ├── changes/archive/.gitkeep
    └── issues/index.md
    ```

    根索引记录概览、知识路由、活跃 Change 和写入／冲突规则；Specs 索引保存长期知识分类；Issues 索引保存已验证故障。所有中文 Markdown 写入前按 `md-zh` 自检。
6. 从项目路径读取 `openspec/index.md`、`openspec/specs/index.md` 和 `openspec/issues/index.md`，验证入口可用。链接失效时停止，不创建同名目录或复制正文掩盖问题。
7. 只逐路径 `git add` 本次产物，禁止 `git add .`；本地提交 `chore: 初始化项目脚手架`，不 push。报告本次创建／保留路径、验证结果、Profile、提交状态及未完成项。全部已存在则报告「无需初始化」，不做覆盖性修改。
