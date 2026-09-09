"""Smoke automatisé des 3 éditions + kit copié ailleurs (USB simulé)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from smoke_editions import run_all  # noqa: E402


def test_smoke_trois_editions_et_kit_deplace():
    results = run_all(port_start=18237)
    failed = [r for r in results if not r["ok"]]
    assert not failed, " / ".join(
        f"{r['edition']}: {r.get('detail')}" for r in failed)
    names = {r["edition"] for r in results}
    assert {"lanceurs", "pc", "web", "phone", "web-usb-simule"} <= names
