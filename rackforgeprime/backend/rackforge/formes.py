"""Bibliothèque de formes vectorielles (icônes réseau) du workspace.

``catalogue/formes/<nom>.svg`` — icônes normalisées (SVG autonomes,
viewBox carré). Posées sur l'onglet Diagramme, elles sont INCRUSTÉES en
vecteurs dans le SVG rendu (un ``<g>`` transformé, pas une ``<image>``) :
nettes à tout zoom et convertibles par svglib pour le PDF.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def formes_dir() -> Path | None:
    base = os.environ.get("RACKFORGE_CATALOG_DIR")
    if not base:
        return None
    d = Path(base) / "formes"
    return d if d.is_dir() else None


def list_formes() -> list[str]:
    d = formes_dir()
    if d is None:
        return []
    return sorted(p.stem for p in d.glob("*.svg")
                  if _NAME_RE.match(p.stem))


def _read(name: str) -> str | None:
    if not _NAME_RE.match(name):
        return None
    d = formes_dir()
    if d is None:
        return None
    p = d / f"{name}.svg"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def forme_svg(name: str, color: str = "#888888") -> str | None:
    """SVG brut de l'icône, currentColor résolu (pour l'aperçu palette)."""
    raw = _read(name)
    return raw.replace("currentColor", color) if raw else None


def forme_inline(name: str, x: float, y: float, size: float,
                 color: str) -> str | None:
    """Incrustation vectorielle : contenu de l'icône dans un <g> centré
    sur (x, y) et mis à l'échelle ``size`` — jamais de <image> imbriquée
    (svglib ne rastérise pas un SVG dans un SVG)."""
    raw = _read(name)
    if raw is None:
        return None
    m = re.search(r'viewBox="([\d.\s+-]+)"', raw)
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) != 4:
        return None
    vx, vy, vw, vh = (float(v) for v in parts)
    inner = re.sub(r"^.*?<svg[^>]*>", "", raw, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    inner = inner.replace("currentColor", color)
    scale = size / max(vw, vh)
    tx = x - size / 2 - vx * scale
    ty = y - size / 2 - vy * scale
    return (f'<g transform="translate({tx:.1f},{ty:.1f}) '
            f'scale({scale:.4f})">{inner}</g>')
