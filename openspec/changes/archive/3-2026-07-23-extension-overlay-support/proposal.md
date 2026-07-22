# Proposal: 外部 Overlay 扩展支持（Quick Draft）

**作者**：Codex
**日期**：2026-07-23
**变更**：extension-overlay-support
**状态**：Archived

---

## 1. 问题与目标

### 问题

当前框架只会安装内置白名单中的 Skill，README 也要求用户将自定义 `std-*` Skill 注册到核心 workflow。用户若直接在框架克隆中加入私有规范或修改安装器，后续同步上游时会产生合并冲突。

### 目标

- 定义独立于框架源仓库的 Overlay 清单。
- 安装器能够校验 Overlay、为其 Skill 创建受管链接，并在刷新和卸载时维护其生命周期。
- 核心编码和测试 workflow 能通过只读校验入口按目标文件匹配已验证的 Overlay 规则并加载相应 Skill。
- 文档明确 Core 与 Overlay 的边界及无冲突更新流程。

### 非目标

- 不支持 Overlay 修改、覆盖或删除核心 Skill、Agent、Command 和脚本。
- 不支持 Overlay 的任意代码执行、命令注入或自动修改目标项目的 `AGENTS.md`。
- 不迁移已有复制式安装的私有修改。

### 验收标准

- 给定合法 Overlay 清单，安装器在 `.codex/skills/` 与 `.claude/skills/` 中创建对应目录链接，并单独记录 Overlay Manifest。
- 非法名称、非法相对路径、重复 Skill、与核心或其他 Overlay 冲突的 Skill 均失败且不改变目标项目。
- 重新安装、`--refresh-all` 与卸载均能验证 Overlay 链接完整性，且不会删除不受管文件。
- 编码和测试 workflow 通过只读校验入口消费已验证的 Overlay 规则，并按文件后缀加载 Skill。
- 安装器测试、Skill 图校验和 Markdown 检查通过。

## 2. 设计方案

### 2.1 整体方案

每个私有仓库在根目录提供 `agentic-extension.json`。核心安装器以可重复的 `--extension <路径>` 参数读取该清单，将其中 Skill 链接到目标项目，并在 `.agentic-framework/extensions/<name>.json` 保存独立的受管状态。核心框架 Manifest 与 Registry 记录安装所选 Overlay，以便 `--refresh-all` 恢复同一选择。

### 2.2 核心组件

- **Overlay 清单解析器**：校验名称、Skill 名称、Skill 相对路径与匹配后缀；拒绝路径穿越和无效 JSON。
- **Overlay 链接生命周期**：在核心链接操作之外创建、校验、刷新及删除 Overlay Skill 链接，并保存独立 Manifest。
- **安装选择记录**：扩展核心 Manifest 和用户级 Registry 的选择字段；旧 v2 Manifest 保持可读并要求显式升级。
- **Workflow 发现规则**：编码和测试 workflow 从当前已加载的核心 workflow 真实路径定位受信框架根，运行只读校验入口并只消费其 JSON，按目标文件后缀加载列出的 Skill。

### 2.3 主要接口或 API

```text
python scripts/install_agentic_framework.py <target> --profile <profile> \
    --extension <overlay-source> [--extension <overlay-source> ...]
```

Overlay 清单的最小结构：

```json
{
    "schema_version": 1,
    "name": "company-standards",
    "skills": [
        {
            "name": "std-company-python",
            "path": "skills/std-company-python",
            "files": [".py"]
        }
    ]
}
```

### 2.4 数据模型

Overlay 状态文件记录 Overlay 名称、绝对源路径、清单哈希、规则和已创建的链接。核心 Manifest 记录有序的 Overlay 描述符及 Skill、链接快照，Registry 保存来源路径；只读校验入口交叉验证三者并验证实际链接。

### 2.5 关键权衡

- 选择独立 Overlay Manifest，而非把私有链接并入核心 `manifest.json`，使核心卸载与私有资产所有权保持清晰。
- 选择声明式文件后缀规则，而非允许 Overlay 补丁核心 workflow，避免重新引入 Git 合并冲突与任意代码执行。
- `--refresh-all` 重新读取已登记的 Overlay 源；若源目录已移动或链接被篡改则显式失败，不静默跳过。

## 3. 知识影响

- 修改 `openspec/specs/backend/framework/install-agentic-framework/overview.md`，同步安装器、Manifest 与 Registry 的长期约定。

## 4. 运维

- Overlay 源必须保持在稳定路径；移动后须以新路径显式重装。
- 安装、卸载和刷新仍不支持并发运行。
- Windows 仍要求创建符号链接的权限；失败不得降级为复制。

## 5. 参考资料

- `README.md`
- `scripts/install_agentic_framework.py`
- `scripts/test_install_agentic_framework.py`
- `openspec/specs/backend/framework/install-agentic-framework/overview.md`
