"""Retour à la ligne des identifiants — jamais de « … » agressif.

Un hostname, un id TIA-606 ou un libellé de nœud se lit en entier : on
coupe sur un séparateur (- _ . / espace) et on enchaîne les lignes.
Si le texte dépasse encore le nombre de lignes, la dernière ligne
conserve le reste (police plus petite côté appelant) — on n'élide pas
un identifiant.
"""

from __future__ import annotations

import re

_BREAK = re.compile(r"[-_./\s]")


def wrap_label(text: str, width: int, max_lines: int = 3) -> list[str]:
    """Découpe ``text`` en au plus ``max_lines`` lignes ≤ ``width``
    caractères (sauf la dernière, qui peut dépasser pour tout garder)."""
    text = (text or "").strip()
    if not text:
        return []
    if width < 4:
        width = 4
    if len(text) <= width:
        return [text]
    lines: list[str] = []
    rest = text
    while rest and len(lines) < max_lines:
        if len(rest) <= width or len(lines) == max_lines - 1:
            lines.append(rest)
            break
        cut = width
        # Préférer une coupure sur séparateur dans la 2e moitié.
        chunk = rest[:width]
        matches = list(_BREAK.finditer(chunk))
        if matches and matches[-1].end() >= width // 2:
            cut = matches[-1].end()
        lines.append(rest[:cut].rstrip("-_./ "))
        rest = rest[cut:].lstrip("-_./ ")
    return [ln for ln in lines if ln]


def svg_text_lines(lines: list[str], x: float, y: float, line_h: float,
                   *, font: str, size: float, fill: str, weight: str = "",
                   family_extra: str = "", anchor: str = "start") -> str:
    """``<text>`` multi-ligne (tspan) — convertible svglib."""
    if not lines:
        return ""
    extras = f' font-weight="{weight}"' if weight else ""
    extras += family_extra
    parts = [f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
             f'font-family="{font}" font-size="{size}" fill="{fill}"'
             f'{extras}>']
    for i, line in enumerate(lines):
        from xml.sax.saxutils import escape
        dy = 0 if i == 0 else line_h
        parts.append(f'<tspan x="{x:.1f}" dy="{dy}">{escape(line)}</tspan>')
    parts.append("</text>")
    return "".join(parts)
