"""共享的治理 Profile 读取（change 2041）。

来源是 `.agentic-framework/manifest.json` 的 `profile` 字段——结构化、已
校验、由安装器写入的事实源；不读 `AGENTS.md`，不做任何自然语言解析。
缺失或非法一律失败关闭（抛 GovernanceProfileError），绝不静默回退默认
值；显式 `--governance-profile` 优先于 manifest。
"""

from __future__ import annotations

import json
from pathlib import Path

PROFILES = ("production", "tooling")
MANIFEST_RELATIVE = Path(".agentic-framework") / "manifest.json"


class GovernanceProfileError(Exception):
    """Raised when the governance profile cannot be determined."""


def find_manifest(start: Path) -> Path | None:
    """从 start 向上查找 `.agentic-framework/manifest.json`。"""
    start = start.resolve()
    for candidate in (start, *start.parents):
        manifest = candidate / MANIFEST_RELATIVE
        if manifest.is_file():
            return manifest
    return None


def read_profile(start: Path, override: str | None = None) -> str:
    """取得当前治理 Profile；无法取得时抛 GovernanceProfileError。"""
    if override is not None:
        if override not in PROFILES:
            raise GovernanceProfileError(
                f"--governance-profile 非法：{override!r}（{' / '.join(PROFILES)}）"
            )
        return override
    manifest = find_manifest(start)
    if manifest is None:
        raise GovernanceProfileError(
            "缺少 .agentic-framework/manifest.json 且未传 --governance-profile"
        )
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GovernanceProfileError(f"manifest 读取失败：{error}") from error
    profile = data.get("profile")
    if profile not in PROFILES:
        raise GovernanceProfileError(
            f"manifest 的 profile 非法：{profile!r}（{' / '.join(PROFILES)}）"
        )
    return profile


_PROFILE_RANK = {"lightweight": 0, "standard": 1, "strict": 2}


def review_profile_floor(profile: str) -> str:
    """Profile 决定的 `review_profile` 下限（`framework-unification.md` §5.3）。"""
    if profile == "production":
        return "standard"
    return "lightweight"


def below_floor(value: str, profile: str) -> bool:
    """判定 `review_profile` 取值是否低于 Profile 下限。"""
    return _PROFILE_RANK[value] < _PROFILE_RANK[review_profile_floor(profile)]
