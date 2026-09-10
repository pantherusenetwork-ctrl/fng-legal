"""Aide de test : simule une MessageBox Windows que l'utilisateur tarde à fermer.

Lancé comme ``python tests/phone_box_lente.py --edition phone --no-browser``.
Si ``_message_box`` est encore appelé sur le thread principal avant
``server.run()``, le ping smoke reste mort pendant 8 s.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import run  # noqa: E402


def _slow_box(title: str, text: str) -> None:
    time.sleep(8)


run._message_box = _slow_box  # type: ignore[method-assign]

if __name__ == "__main__":
    run.main()
