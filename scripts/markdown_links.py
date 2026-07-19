"""Shared helpers for repository-local Markdown links."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def resolve_local_link(source: Path, target: str) -> Path | None:
    """Resolve a Markdown target, or return ``None`` for external links."""
    raw = target.strip().strip("<>")
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme and parsed.scheme.lower() != "file":
        return None

    path_text = unquote(parsed.path)
    if parsed.scheme.lower() == "file" and parsed.netloc:
        path_text = f"//{parsed.netloc}{path_text}"
    elif os.name == "nt" and re.match(r"^/[A-Za-z]:/", path_text):
        path_text = path_text[1:]
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (source.parent / path).resolve()
