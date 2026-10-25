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
    """The compatibility alias cannot claim Runtime or bypass v2 evidence."""
    generation = read("skills/workflow-code-generation/SKILL.md")
    assert "Fast-Path 仅作兼容别名" in generation
    assert "reference/delivery-guide.md" in generation
    guide = read("skills/workflow-code-generation/reference/delivery-guide.md")
    for required in (
        "scope: integration",
        "--native-delivery",
        "--verify-report",
        "--review-report",
        "--knowledge-impact",
        "knowledge-impact-reason",
        "不得声明 strict Review 或 Trust Gate PASS",
    ):
        assert required in guide
    report = read("skills/workflow-code-review/reference/report-format.md")
    alias = next(line for line in report.splitlines()
                 if line.startswith("| Fast-Path 兼容别名 |"))
    for required in ("v2", 'scope: "integration"',
                     'review_profile: "lightweight"', "不得声明 Runtime 证据"):
        assert required in alias
    assert "旧六字段报告只按旧合同展示历史，不能作为新交付证据" in report
    prompts = read("skills/workflow-code-review/reference/reviewer-prompts.md")
    for required in ("report-format.md", "schema_version: 2", "`subject_id`",
                     "不得猜测或退回旧六字段报告", "strict 由独立 Judge"):
        assert required in prompts
    for entry in (prompts, read("agents/comprehensive-reviewer.md")):
        assert "6 字段 JSON Artifact" not in entry


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
    assert "reference/delivery-guide.md#统一交付证据格式" in generation
    delivery = read("skills/workflow-code-generation/reference/delivery-guide.md")
    for field in (
        "Feature",
        "Task",
        "Review Profile",
        "Review Retries",
        "Verify Retries",
        "Manual Intervention",
    ):
        assert f"**{field}**:" in delivery
    assert "最多十轮" in generation and "最多 10 轮" in delivery
    assert "SVN 命中 Runtime 升级需求时停止，不降级" in generation


def test_existing_svn_is_detected_before_git_initialization() -> None:
    """Existing SVN or an unresolved marker must not become a Git repo."""
    text = read("skills/project-init/SKILL.md")
    routing, initialization = text.split("### 4. 初始化版本控制", 1)
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


def test_native_review_templates_match_profile_specific_machine_gate() -> None:
    """The documented v2 template and strict declarations match the gate."""
    import native_delivery

    review = read("skills/workflow-code-review/reference/report-format.md")
    examples = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)```", review, re.S)
    ]
    template = next(item for item in examples
                    if item.get("scope") == "integration")
    assert template["schema_version"] == 2
    assert template["subject_id"] == "sha256:<64-hex>"
    template["subject_id"] = "sha256:" + "0" * 64
    independence = {
        "implementer_actor": "implementer",
        "judge_actor": "independent-reviewer",
        "independence_basis": "Judge did not implement this change",
    }
    for field in independence:
        assert f"`{field}`" in review
    for profile in ("lightweight", "standard", "strict"):
        artifact = {**template, "review_profile": profile}
        if profile == "strict":
            with pytest.raises(native_delivery.NativeDeliveryError):
                native_delivery.validate_review_report(artifact, profile)
            artifact.update(independence)
        native_delivery.validate_review_report(artifact, profile)
        wrong = "strict" if profile != "strict" else "standard"
        with pytest.raises(native_delivery.NativeDeliveryError):
            native_delivery.validate_review_report(artifact, wrong)
        for override in ({"run_id": "fake-run"}, {"scope": "run"}):
            with pytest.raises(native_delivery.NativeDeliveryError):
                native_delivery.validate_review_report({**artifact, **override})
    with pytest.raises(native_delivery.NativeDeliveryError):
        native_delivery.validate_review_report({**template, **independence})
    with pytest.raises(native_delivery.NativeDeliveryError):
        native_delivery.validate_review_report({
            **template, **independence, "review_profile": "strict",
            "judge_actor": independence["implementer_actor"],
        })
    legacy = {key: value for key, value in template.items()
              if key not in {"schema_version", "subject_id"}}
    with pytest.raises(native_delivery.NativeDeliveryError):
        native_delivery.validate_review_report(legacy)


def test_shared_native_instructions_respect_governance_not_risk() -> None:
    """Risk selects review rigor; only explicit requirements select Runtime."""
    generation = read("skills/workflow-code-generation/SKILL.md")
    for required in ("--execution-mode runtime", "--audit-required",
                     "--cross-host-capability-verification",
                     "不因风险自动建 Run", "三项独立性声明",
                     "独立 v2 验证报告，不初始化 Run"):
        assert required in generation
    assert "SVN 命中 Runtime 升级需求时停止，不降级" in generation
    review = read("skills/workflow-code-review/SKILL.md")
    for required in ("Tooling Native Delivery 默认 `standard`",
                     "Production 仍按其生命周期选择 `strict`",
                     "独立 Judge 与三项独立性声明，不因此要求 Run",
                     "无 Run 的 strict 写成 `scope: integration` 的 v2 报告",
                     "编排方与实现者只能原样保存完整 JSON"):
        assert required in review
    report = read("skills/workflow-code-review/reference/report-format.md")
    assert '不得输出 `scope: "run"` 或 `review_profile: "strict"`' not in report
    assert "不得提供 `run_id`、Harness、Trust Gate、Manifest 声明" in report
    delivery = read("skills/workflow-code-generation/reference/delivery-guide.md")
    assert "任务声明 `strict` 时使用 `strict`，由独立 Judge" in delivery
    assert "与独立 v2 Verify，校验同一 `subject_id`" in delivery
    runtime = read("skills/workflow-code-generation/reference/runtime-guide.md")
    assert "strict 风险本身不启用 Runtime" in runtime
    assert "--execution-mode runtime --long-task-recovery" in runtime
    assert "不自动创建 Git 镜像或桥接" in runtime
