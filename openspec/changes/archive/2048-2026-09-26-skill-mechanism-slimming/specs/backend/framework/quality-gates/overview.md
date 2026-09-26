# 交付门 Delta

## REMOVED

- 退役隐式 Fast-Path 和 `fast-path-pass` 独立裁决。旧调用失败并提示迁移，不继续接受弱证据。

## MODIFIED

- `skills/workflow-code-generation/scripts/check_delivery.py --native-delivery` 统一普通与轻量交付，要求 integration Review（Tooling 为 standard，Production 为 strict）、完整独立 Verify、知识影响结论与有界 Verdict。
- 轻量交付仅在 `knowledge-impact none` 且有具体理由时可同时省略 Spec／Tasks；两参数不得只传一个，知识命中时先建 Change。
- Runtime 必须提供 Spec／Tasks，Production 既有严格下限不降低。

同步目标：`openspec/specs/backend/framework/quality-gates/overview.md`。
