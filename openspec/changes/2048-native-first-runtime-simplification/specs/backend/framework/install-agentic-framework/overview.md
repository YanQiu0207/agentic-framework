# Install Delta — VCS 识别与原生 SVN 初始化

## MODIFIED Requirements

### Requirement：初始化按现有 VCS 识别推荐，不再无条件 Git 优先

初始化在询问版本管理模式前先探测现有 `.git` / `.svn`（含父级 Git 包住 SVN 工作副本与两者并存的形态）：已有纯 SVN 默认推荐原生 SVN；已有 Git 默认推荐纯 Git；双 VCS 并存时展示识别结果并要求用户显式确认开发后端，不隐式选择。「Git + SVN」仍是显式选项，服务于确实要本地 Git + 正式提交走 SVN 的用户。

#### Scenario：已有项目不转换、不删除

已配置桥接或团队镜像的项目保留现状，只标注正式提交后端；不因 `.git` 存在推断桥接正确，不创建镜像/桥接，不删除任何 `.git`、`.svn` 元数据。旧 `.git`、`.svn` 均保留，任何移除另行授权。

#### Scenario：纯 SVN 初始化只 add 不 commit

纯 SVN 模式沿用逐路径 `svn add`、不自动 `svn commit`：初始化产物加入版本控制计划后保持未提交，由用户自行提交。非工作副本目录报告并停止，提示先 `svn checkout` / `svn import`，不擅自 `svnadmin create`。

#### Scenario：Profile 入口描述与当前实现一致

Profile 描述使用当前统一的 `workflow-*` 入口与 Production 三阶段门禁（plan/delivery/archive 的确定性校验），不再引用已退役的独立 OPSX 入口提法；Profile 仍只决定执行生命周期，不改变 `openspec/` Artifact 结构。

## Verification

`python -m pytest scripts/test_profile_contracts.py -q`；`python scripts/lint_skill_graph.py` 退出 0。
