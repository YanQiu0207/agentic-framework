# Design：批准门安全硬化

**变更**：2030-approval-gate-hardening
**状态**：Quick Draft

---

## 1. 范围

三处改动,适配 Change 2029 落地的现有结构:

1. `scripts/validate_change.py`:新增 OPSX055 双向耦合 + 三个 `LOOSE_*` 失败关闭正则。
2. `scripts/tests/test_validate_change.py`:对应测试。
3. `openspec/specs/`:长期规格同步 OPSX055 行为。

不动:`_stable_waves`、`_condition_set`、`_approval_conditions`、`_validate_approval_evidence` 既有结构、`workflow_control.py`、`runtime_*`、`verify.py`。

## 2. OPSX055 双向耦合

### 2.1 判定逻辑

对每个 Task,在已解析 `Escalation`(经 `_condition_set`)与 `Review Profile`(经既有正则)之后:

- 声明了 `Escalation` 字段(含「无」)且 `irreversible ∈ escalation`,但 `Review Profile != strict` → OPSX055。
- 声明了 `Escalation` 字段,`Review Profile == strict`,但 `irreversible ∉ escalation` → OPSX055。反向这条堵住 §1.1 的削弱路径。

### 2.2 opt-in 边界

只对**声明了 `Escalation` 字段**的 Task 生效。字段缺失(非「无」,而是整行不存在)直接跳过——兼容既有 strict 归档 Change。这与 §3 权衡一致:「两个字段同时省略」是无法机器发现的残余风险。

注意区分:字段存在但值为「无」(`Escalation: 无`)算「声明了字段」,参与校验;字段整行不存在算「未声明」,跳过。

### 2.3 阶段生效

`_validate_approval_evidence` 当前只在 `require_completed=True` 时调用(见 `validate_change` 函数的 delivery/archive 分支)。要让 OPSX055 在 plan 也生效,需要把档位耦合的调用从该函数里提出来,放在 `_validate_tasks` 主循环里(那里 plan 和 delivery 都会跑),且不受 `require_completed` 门控。

`Escalation` 与 `Review Profile` 都是规划期产物,不依赖执行证据,因此在 plan 阶段校验是合理的。

## 3. LOOSE 失败关闭正则

### 3.1 三个正则

```
LOOSE_ESCALATION_RE  = ^\s*[-*]\s*Escalation\s*[:：]
LOOSE_APPROVAL_RE    = ^\s*[-*]\s*Approval\s*[:：]
LOOSE_APPROVAL_MODE_RE = ^\s*(?:[>*-]\s*)*批准模式\s*[:：]\s*(?P<mode>\S+)
```

严格正则只认 `^-\s*`(字段)与 `^>?\s*`(模式)。宽松正则额外接受缩进与列表标记。

### 3.2 判定规则

对每个 Task 的 metadata:宽松命中数 > 严格命中数 ⇒ 格式错误,报 OPSX053。对批准模式:头部严格扫描未命中但全文宽松命中 ⇒ 错位,报 OPSX053。

方向必须失败关闭:`Escalation`/`Approval` 是可选字段,写错位置的默认后果是门禁无声消失,与必填字段的失效方向相反。

### 3.3 围栏口径一致

`_metadata_text` 已剔除围栏。LOOSE 探测必须在剔除围栏后的文本上做,否则围栏内的示例(规划指南用围栏展示这些字段)会被误报。复用 `_metadata_text(lines)`。

## 4. 已知限制(不在本 Change 解决)

- **`Approval` 是自证**:Agent 自写文本,校验器只验格式,无法区分用户真批准与 Agent 自授。本 Change 改善留痕与一致性,不提供可信证据。需要把批准证据移到确定性产物(Run Context)才能根治,属另一个 Change。
- **`gate-failure` 自指**:依赖 Agent 产出的 review JSON 的 p0/p1,可构造 p0=0 绕过。
- **围栏内声明不识别**:`_metadata_text` 剔除围栏后,围栏内的 `Escalation`/`Approval` 等价于没写。
- **两字段同时省略**:`standard` + 无 `Escalation` 的高风险 Task 机器无法发现(opt-in 的代价)。

## 5. 不确定性

- OPSX055 的 opt-in 边界靠「字段是否存在」判定。规划期若把 `Escalation` 写进缩进或围栏,会先被 §3 的 LOOSE 检查拦下(失败关闭),不会无声进入 opt-in 跳过分支——这条依赖 §3 与 §2 的顺序:先格式检查,再耦合判定。
