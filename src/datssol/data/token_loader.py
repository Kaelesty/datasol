"""Utilities for reading auth material from disk."""

from __future__ import annotations

from pathlib import Path


def load_token(token_path: str | Path) -> str:
    path = Path(token_path)
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"Token file '{path}' is empty.")
    return token

