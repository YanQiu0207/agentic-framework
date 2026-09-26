"""Regression contracts for skill routing and executable task examples.

These checks protect instructions, not LLM behavior. Delivery and pack behavior
are covered separately by their executable gate tests.
"""

from pathlib import Path
import json
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/workflow-code-generation/scripts"))
import lint_task_deps


def read(relative: str) -> str:
    """Read a maintained instruction as UTF-8."""
    return (ROOT / relative).read_text(encoding="utf-8")


def test_task_template_dependency_uses_real_parser() -> None:
    """The actual copyable task template must preserve its dependency edge."""
    guide = read(
        "skills/workflow-code-generation/reference/task_planning_guide.md"
    )
    examples = re.findall(r"```markdown\n(.*?)```", guide, re.S)
    template = next(text for text in examples if "depends_on:" in text)
    tasks = lint_task_deps.parse_tasks(template)
    assert tasks[1]["deps"] == set()
    assert tasks[2]["deps"] == {1}
    assert not lint_task_deps.field_errors(tasks)


def test_no_independent_compatibility_delivery_in_active_instructions() -> None:
    """Old calls cannot continue routing to weaker evidence."""
    for area in ("skills", "commands", "agents"):
        for path in (ROOT / area).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert "Fast-Path" not in text, path
            assert "fast-path-pass" not in text, path
    generation = read("skills/workflow-code-generation/SKILL.md")
    section = generation.split("## Native Delivery", 1)[1].split(
        "## 标准流程", 1
    )[0]
    for required in (
        "review_profile: standard",
        "scope: integration",
        "--native-delivery",
        "--verify-report",
        "--review-report",
        "--knowledge-impact",
        "knowledge-impact-reason",
        "`hit` 而无 Change 时先停止并创建 Change",
    ):
        assert required in section
    assert "review_profile: lightweight" not in section


@pytest.mark.parametrize(
    "skill,pack,reference",
    [
        ("workflow-code-generation", "runtime", "runtime-guide.md"),
        ("project-init", "knowledge-advanced", "advanced-init.md"),
        ("project-knowledge", "knowledge-advanced", "knowledge-advanced.md"),
    ],
)
def test_optional_routes_require_trusted_query(
    skill: str, pack: str, reference: str
) -> None:
    """Every optional route must be reachable and fail closed before work."""
    entry = read(f"skills/{skill}/SKILL.md")
    assert "--show-packs <project>" in entry
    assert "真实路径" in entry and "解析" in entry
    assert "JSON" in entry and "`enabled`" in entry
    assert "不得执行目标 manifest 的 `source`" in entry
    assert "缺包" in entry and "停止" in entry
    assert f"--with {pack}" in entry
    assert f"](reference/{reference})" in entry
    detail = read(f"skills/{skill}/reference/{reference}")
    assert pack in detail


def test_knowledge_reporting_keeps_internal_checks_not_negative_table() -> None:
    text = read("skills/project-knowledge/SKILL.md")
    impact = text.split("## 9.", 1)[1].split("## 10.", 1)[0]
    for signal in ("架构决策", "放弃重要方案", "红线", "故障根因", "跨项目"):
        assert signal in impact
    assert "内部逐项检查" in impact
    assert "目标路径与同步状态" in impact
    assert "无长期知识影响：<具体理由>" in impact
    assert " / 未命中" not in impact
    assert "不得归档或宣布全部完成" in impact


def test_embedded_tests_reach_generation_without_extra_review() -> None:
    text = read("skills/workflow-test-generation/SKILL.md")
    route = next(
        line for line in text.splitlines() if "| **内嵌路径** |" in line
    )
    assert "Step 2 → 3 → 4" in route and "跳过 Step 5" in route
    generation = text.split("## Step 4:", 1)[1].split("### 4.1", 1)[0]
    assert "**内嵌路径**" in generation
    assert "交还编排方" in generation


def test_quick_approval_does_not_skip_route_or_verify() -> None:
    text = read("skills/workflow-quick-design/SKILL.md")
    handoff = text.split("### Step 8：", 1)[1]
    assert "步骤 1 路由" in handoff
    assert "步骤 1.5" in handoff and "Verify" in handoff
    assert "不重复审批" in handoff
    assert "从步骤 4" not in handoff


def test_current_react_contract_and_local_design_numbering() -> None:
    react = read("skills/std-react/SKILL.md")
    for artifact in ("proposal.md", "design.md", "Delta", "ui-spec.md"):
        assert artifact in react
    assert "旧 `spec.md` 只允许迁移读取" in react
    for path in (
        "skills/workflow-system-design/SKILL.md",
        "skills/workflow-system-design/reference/design_template.md",
    ):
        text = read(path)
        assert "可与 proposal.md 的编号重叠" in text
        assert "跨文件引用必须带文件名" in text


def test_manual_initialization_and_telemetry_fields_preserved() -> None:
    init = read("skills/project-init/SKILL.md")
    assert "disable-model-invocation: true" in init
    assert "禁止模型自动调用" in init
    generation = read("skills/workflow-code-generation/SKILL.md")
    for field in (
        "Feature",
        "Task",
        "Review Profile",
        "Review Retries",
        "Verify Retries",
        "Manual Intervention",
    ):
        assert f"**{field}**:" in generation
    delegated = read(
        "skills/workflow-code-generation/reference/delegated-execution-guide.md"
    )
    assert "最多 10 轮" in generation and "最多 10 轮" in delegated
    assert "SVN 命中 Runtime 升级需求时停止，不降级" in generation


def test_existing_svn_is_detected_before_git_initialization() -> None:
    """Existing SVN or an unresolved marker must not become a Git repo."""
    text = read("skills/project-init/SKILL.md")
    routing, initialization = text.split("## 初始化", 1)
    for required in (
        "当前目录及祖先",
        "`svn info`",
        "已有 SVN 工作副本",
        "先查询 `knowledge-advanced`",
        "缺包或查询失败时停止",
        "不能转而执行 `git init`",
        "有 `.svn` 标记但 SVN 不可用",
        "不擅自执行高级初始化",
    ):
        assert required in routing
    assert "确认不存在 SVN 工作副本或未决状态" in initialization
    assert "用户确认 Git 模式后" in initialization
    assert "不把任何失败都当成「不是仓库」" in initialization
    generation = read("skills/workflow-code-generation/SKILL.md")
    assert "普通 SVN Native Delivery 不额外要求高级初始化能力包" in generation
    assert "SVN 命中 Runtime 升级需求时停止，不降级" in generation


def test_native_review_templates_match_profile_specific_machine_gate(
    tmp_path: Path,
) -> None:
    """Both documented flat examples must pass only their governance floor."""
    import check_delivery

    review = read("skills/workflow-code-review/SKILL.md")
    examples = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)```", review, re.S)
    ]
    native = {
        item["review_profile"]: item
        for item in examples
        if item.get("scope") == "integration"
    }
    assert set(native) == {"standard", "strict"}
    fields = {
        "verdict",
        "p0_count",
        "p1_count",
        "scope",
        "review_profile",
        "round",
    }
    for profile, artifact in native.items():
        assert set(artifact) == fields
        report = tmp_path / f"{profile}.json"
        report.write_text(json.dumps(artifact), encoding="utf-8")
        assert not check_delivery.check_native_delivery_review(report, profile)
        wrong = "strict" if profile == "standard" else "standard"
        assert check_delivery.check_native_delivery_review(report, wrong)


def test_shared_native_instructions_respect_governance_not_risk() -> None:
    """All shared handoffs agree on scope, producer and strict risk routing."""
    generation = read("skills/workflow-code-generation/SKILL.md")
    light = generation.split("## Native Delivery", 1)[1].split(
        "## 标准流程", 1
    )[0]
    final = generation.split("4. **一次最终审核**", 1)[1].split(
        "5. **交付前沉淀检查**", 1
    )[0]
    for section in (light, final):
        for required in (
            "Tooling 使用 `review_profile: standard`",
            "Production 使用 `review_profile: strict`",
            "scope: integration",
            "扁平 6 字段",
            "comprehensive-reviewer",
            "独立 Judge",
        ):
            assert required in section
    assert "Tooling 为 `standard`，Production 为 `strict`" in light
    assert "不降低机器门下限" in light
    assert "这不代表任务风险为 `strict`，不单独触发 Runtime" in generation
    assert "两种 Profile 都仍须走 Runtime" in generation
    assert "SVN 命中 Runtime 升级需求时停止，不降级" in generation
    review = read("skills/workflow-code-review/SKILL.md")
    production = next(
        line
        for line in review.splitlines()
        if line.startswith("| Production Native Delivery |")
    )
    assert "未参与实现的独立 Judge" in production
    assert 'scope: "integration"' in production
    assert 'review_profile: "strict"' in production
    assert "不添加 Run 或独立性机器字段" in production
    assert "`strict` 的 Tooling Review 必须升级到完整 Runtime Run" in review
    assert "两种 Profile 都仍须按代码生成路由处理" in review
    assert '不得输出 `scope: "run"` 或 `review_profile: "strict"`' not in review
