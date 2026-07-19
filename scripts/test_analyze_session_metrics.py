"""Regression tests for review-quality parsing in analyze_session_metrics."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_session_metrics as asm


def report(round_line: str, verdict: str, body: str = "") -> str:
    return (
        f"# Code Review 报告\n\n## 审查范围\n{round_line}\n"
        f"\n## 总体结论: {verdict}\n\n{body}"
    )


class ExtractReviewsTest(unittest.TestCase):
    """轮次字段与「（新增）」标记的解析。"""

    def test_first_review_round_is_zero(self) -> None:
        text = report(
            "- **轮次**: 首审", "NEEDS_CHANGES", "#### P1-1: x\n#### P1-2: y\n"
        )
        (r,) = asm.extract_reviews(text, 1.0)
        self.assertEqual(0, r["round"])
        self.assertEqual(2, r["p1"])
        self.assertEqual(0, r["new_p1"])

    def test_rereview_round_and_new_marker(self) -> None:
        text = report(
            "- **轮次**: 复审第 2 轮",
            "NEEDS_CHANGES",
            "#### P0-1: 未修复\n#### P1-2（新增）: 修复引入\n#### P2-3(新增): z\n",
        )
        (r,) = asm.extract_reviews(text, 1.0)
        self.assertEqual(2, r["round"])
        self.assertEqual(
            {"p0": 1, "p1": 1, "p2": 1}, {k: r[k] for k in ("p0", "p1", "p2")}
        )
        self.assertEqual(
            {"new_p0": 0, "new_p1": 1, "new_p2": 1},
            {k: r[k] for k in ("new_p0", "new_p1", "new_p2")},
        )

    def test_legacy_report_without_round_is_none(self) -> None:
        (r,) = asm.extract_reviews("# Code Review 报告\n## 总体结论: PASS\n", 1.0)
        self.assertIsNone(r["round"])


class ExtractTaskAttributionsTest(unittest.TestCase):
    """固定任务归因区块的解析、兼容与去重。"""

    BLOCK = """## 任务归因
- **Feature**: session-telemetry/task-attribution
- **Task**: Task 2
- **Review Profile**: standard
- **Review Retries**: 1
- **Verify Retries**: 2
- **Manual Intervention**: review，verify
"""

    def test_extracts_complete_attribution(self) -> None:
        (attribution,) = asm.extract_task_attributions(self.BLOCK)
        self.assertEqual("session-telemetry/task-attribution", attribution["feature"])
        self.assertEqual("Task 2", attribution["task"])
        self.assertEqual(1, attribution["review_retries"])
        self.assertEqual(2, attribution["verify_retries"])
        self.assertEqual(["review", "verify"], attribution["manual_intervention"])

    def test_legacy_text_has_no_attribution(self) -> None:
        self.assertEqual(
            [], asm.extract_task_attributions("# Code Review 报告\n## 总体结论: PASS\n")
        )

    def test_incomplete_or_invalid_block_is_ignored(self) -> None:
        self.assertEqual(
            [],
            asm.extract_task_attributions(
                self.BLOCK.replace("- **Task**: Task 2\n", "")
            ),
        )
        self.assertEqual(
            [],
            asm.extract_task_attributions(
                self.BLOCK.replace(
                    "- **Review Retries**: 1", "- **Review Retries**: unknown"
                )
            ),
        )

    def test_fields_are_not_combined_across_sections(self) -> None:
        split_block = self.BLOCK.replace(
            "- **Review Retries**: 1", "## 验证结果\n- **Review Retries**: 1"
        )
        self.assertEqual([], asm.extract_task_attributions(split_block))

    def test_analyze_session_keeps_last_duplicate(self) -> None:
        first = self.BLOCK.replace("- **Verify Retries**: 2", "- **Verify Retries**: 0")
        entries = [
            {
                "type": "response_item",
                "timestamp": "2026-07-12T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": first}],
                },
            },
            {
                "type": "response_item",
                "timestamp": "2026-07-12T00:00:01Z",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": self.BLOCK}],
                },
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rollout-test.jsonl"
            path.write_text(
                "\n".join(map(json.dumps, entries)) + "\n", encoding="utf-8"
            )
            result = asm.analyze_session(path, 300)
        self.assertEqual(1, len(result["task_attributions"]))
        self.assertEqual(2, result["task_attributions"][0]["verify_retries"])


class SummarizeQualityTest(unittest.TestCase):
    """按流重建修复循环与 ADR 003 指标计数。"""

    @staticmethod
    def review(rnd, verdict, stream="main", new_p1=0):
        return {
            "ts": 0.0,
            "round": rnd,
            "verdict": verdict,
            "stream": stream,
            "p0": 0,
            "p1": new_p1,
            "p2": 0,
            "new_p0": 0,
            "new_p1": new_p1,
            "new_p2": 0,
        }

    def test_converged_loop(self) -> None:
        q = asm.summarize_quality(
            [self.review(0, "NEEDS_CHANGES"), self.review(1, "PASS")]
        )
        self.assertEqual(1, q["loops"])
        self.assertEqual(0, q["manual_loops"])
        self.assertEqual(0, q["unresolved_loops"])

    def test_manual_loop_at_round_two(self) -> None:
        q = asm.summarize_quality(
            [
                self.review(0, "NEEDS_CHANGES"),
                self.review(1, "NEEDS_CHANGES", new_p1=1),
                self.review(2, "NEEDS_CHANGES"),
            ]
        )
        self.assertEqual(1, q["manual_loops"])
        self.assertEqual(2, q["rereviews"])
        self.assertEqual(1, q["rereviews_with_new_p01"])

    def test_unresolved_loop_and_unrounded(self) -> None:
        q = asm.summarize_quality(
            [self.review(None, "PASS"), self.review(0, "NEEDS_CHANGES")]
        )
        self.assertEqual(1, q["unrounded"])
        self.assertEqual(1, q["unresolved_loops"])
        self.assertEqual(0, q["manual_loops"])

    def test_verification_chain_without_first_review_opens_loop(self) -> None:
        # 验证类修复复审链（无首审报告）：需人工计入分子时分母必须同步覆盖
        q = asm.summarize_quality(
            [self.review(1, "NEEDS_CHANGES"), self.review(2, "NEEDS_CHANGES")]
        )
        self.assertEqual(1, q["loops"])
        self.assertEqual(1, q["manual_loops"])
        self.assertEqual(0, q["first_reviews"])

    def test_rereview_after_converged_loop_is_new_chain(self) -> None:
        # 循环收敛后的验证类复审链需人工，不得归因到已收敛的循环
        q = asm.summarize_quality(
            [
                self.review(0, "NEEDS_CHANGES"),
                self.review(1, "PASS"),
                self.review(1, "NEEDS_CHANGES"),
                self.review(2, "NEEDS_CHANGES"),
            ]
        )
        self.assertEqual(2, q["loops"])
        self.assertEqual(1, q["manual_loops"])

    def test_streams_do_not_interleave(self) -> None:
        # 两个并行 owner 各自首审 NEEDS_CHANGES 后复审 PASS；
        # 若按时间戳串账会被误判为「首审后又首审」产生未收敛循环
        q = asm.summarize_quality(
            [
                self.review(0, "NEEDS_CHANGES", "sub-0"),
                self.review(0, "NEEDS_CHANGES", "sub-1"),
                self.review(1, "PASS", "sub-0"),
                self.review(1, "PASS", "sub-1"),
            ]
        )
        self.assertEqual(2, q["loops"])
        self.assertEqual(0, q["unresolved_loops"])


class MarkerAnchorTest(unittest.TestCase):
    """阶段锚点：认引用/加粗/反引号包裹，不认列表前缀。"""

    def test_wrapped_markers_match(self) -> None:
        for line in (
            "Using workflow-code-review",
            "`Using workflow-code-review`",
            "**Using workflow-code-review**",
            "> Using workflow-code-review",
        ):
            self.assertEqual(
                ["workflow-code-review"], asm.MARKER_RE.findall(line), line
            )

    def test_list_prefix_does_not_match(self) -> None:
        for line in ("- Using workflow-code-review", "* Using workflow-code-review"):
            self.assertEqual([], asm.MARKER_RE.findall(line), line)


class ReaderRobustnessTest(unittest.TestCase):
    """顶层非对象的合法 JSON 行不得让 reader 崩溃。"""

    MALFORMED = 'null\n[1, 2]\n"text"\n123\n'

    def test_read_claude_skips_non_dict_lines(self) -> None:
        entry = {
            "type": "assistant",
            "timestamp": "2026-07-12T00:00:00Z",
            "message": {
                "usage": {"input_tokens": 1},
                "content": [{"type": "text", "text": "hi"}],
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.jsonl"
            path.write_text(self.MALFORMED + json.dumps(entry) + "\n", encoding="utf-8")
            entries, _, _ = asm.read_claude(path)
        self.assertEqual(1, len(entries))

    def test_read_codex_skips_non_dict_lines(self) -> None:
        entry = {
            "type": "session_meta",
            "timestamp": "2026-07-12T00:00:00Z",
            "payload": {"cwd": "E:/work/x"},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rollout-1.jsonl"
            path.write_text(self.MALFORMED + json.dumps(entry) + "\n", encoding="utf-8")
            _, _, cwd = asm.read_codex(path)
        self.assertEqual("E:/work/x", cwd)

    def test_cwd_filter_uses_early_session_metadata(self) -> None:
        entry = {
            "type": "session_meta",
            "timestamp": "2026-07-12T00:00:00Z",
            "payload": {"cwd": "E:/work/project-a"},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rollout-1.jsonl"
            path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            self.assertEqual("E:/work/project-a", asm.peek_cwd(path))
            self.assertTrue(asm.cwd_matches_filter(path, "E:/work"))
            self.assertFalse(asm.cwd_matches_filter(path, "E:/other"))

    def test_read_claude_skips_non_dict_message(self) -> None:
        malformed = {
            "type": "assistant",
            "timestamp": "2026-07-12T00:00:00Z",
            "message": "bad",
        }
        valid = {
            "type": "assistant",
            "timestamp": "2026-07-12T00:00:01Z",
            "message": {"content": []},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.jsonl"
            path.write_text(
                "\n".join(map(json.dumps, (malformed, valid))) + "\n", encoding="utf-8"
            )
            entries, _, _ = asm.read_claude(path)
        self.assertEqual(1, len(entries))

    def test_read_codex_skips_non_dict_token_info(self) -> None:
        malformed = {
            "type": "event_msg",
            "timestamp": "2026-07-12T00:00:00Z",
            "payload": {"type": "token_count", "info": "bad"},
        }
        valid = {
            "type": "session_meta",
            "timestamp": "2026-07-12T00:00:01Z",
            "payload": {"cwd": "E:/work/x"},
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "rollout-1.jsonl"
            path.write_text(
                "\n".join(map(json.dumps, (malformed, valid))) + "\n", encoding="utf-8"
            )
            entries, _, cwd = asm.read_codex(path)
        self.assertEqual([], entries)
        self.assertEqual("E:/work/x", cwd)


class AppendHistoryTest(unittest.TestCase):
    """账本 upsert：新增追加、已有覆盖、坏行保留。"""

    def test_upsert_updates_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "history.jsonl"
            v1 = {"source": "claude", "session": "s1", "entries": 3}
            self.assertEqual((1, 0), asm.append_history([v1], ledger))
            v2 = {"source": "claude", "session": "s1", "entries": 9}
            v3 = {"source": "claude", "session": "s2", "entries": 1}
            self.assertEqual((1, 1), asm.append_history([v2, v3], ledger))
            self.assertEqual((0, 0), asm.append_history([v2, v3], ledger))
            rows = [
                json.loads(x) for x in ledger.read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(2, len(rows))
        self.assertEqual(9, rows[0]["entries"])

    def test_unparseable_lines_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "history.jsonl"
            # 语法错误行与「可解析但非对象」行都须原样保留，不得崩溃
            ledger.write_text("not-json\n[1, 2]\n", encoding="utf-8")
            asm.append_history(
                [{"source": "claude", "session": "s1", "entries": 1}], ledger
            )
            lines = ledger.read_text(encoding="utf-8").splitlines()
        self.assertIn("not-json", lines)
        self.assertIn("[1, 2]", lines)
        self.assertEqual(3, len(lines))

    def test_objects_without_identity_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "history.jsonl"
            ledger.write_text('{"x": 1}\n{"y": 2}\n', encoding="utf-8")
            asm.append_history(
                [{"source": "claude", "session": "s1", "entries": 1}], ledger
            )
            lines = ledger.read_text(encoding="utf-8").splitlines()
        self.assertIn('{"x": 1}', lines)
        self.assertIn('{"y": 2}', lines)
        self.assertEqual(3, len(lines))

    def test_replace_failure_preserves_existing_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "history.jsonl"
            original = '{"source":"claude","session":"s1"}\n'
            ledger.write_text(original, encoding="utf-8")
            with mock.patch.object(asm.os, "replace", side_effect=OSError("failed")):
                with self.assertRaises(OSError):
                    asm.append_history([{"source": "claude", "session": "s2"}], ledger)
            self.assertEqual(original, ledger.read_text(encoding="utf-8"))
            self.assertEqual([ledger], list(Path(td).iterdir()))

    def test_legacy_history_is_read_but_new_history_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            legacy = root / "metrics" / "session-history.jsonl"
            legacy.parent.mkdir()
            old = {"source": "claude", "session": "s1", "entries": 1}
            legacy.write_text(json.dumps(old) + "\n", encoding="utf-8")
            before = legacy.read_text(encoding="utf-8")

            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                runtime, legacy_read = asm.resolve_history_paths(
                    Path("metrics/session-history.jsonl"), root
                )
            updated = {"source": "claude", "session": "s1", "entries": 2}
            self.assertEqual((0, 1), asm.append_history([updated], runtime, legacy_read))

            self.assertEqual(
                root / ".agentic-framework" / "metrics" / "session-history.jsonl",
                runtime,
            )
            self.assertEqual(before, legacy.read_text(encoding="utf-8"))
            self.assertIn("仅兼容读取", stderr.getvalue())
            rows = runtime.read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, json.loads(rows[0])["entries"])

    def test_custom_history_path_remains_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            custom = Path("reports/custom.jsonl")
            self.assertEqual(
                ((root / custom).resolve(), None),
                asm.resolve_history_paths(custom, root),
            )


if __name__ == "__main__":
    unittest.main()
