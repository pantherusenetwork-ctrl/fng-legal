"""Cordons de brassage pour l'export SVG/PDF (câbles v2).

Même langage visuel que l'overlay écran (goulotte à droite, allée entre
baies, couleur = média). L'ancrage vise le PORT quand son nom figure
sur le type (index dans la liste des ports) ; sinon le milieu de la
façade. Coordonnées = repère de ``render_project_svg``.
"""

from __future__ import annotations

from .models import EquipmentType, LogicalLink, Project, Rack, type_index
from .svg_export import (FRAME_PAD, GAP_X, RAIL_W, RACK_W, U_PX,
                         _item_box, _rack_size, _u_to_y)

CABLE_COLORS = {
    "cuivre-cat6a": "#2563eb",
    "cuivre-cat6": "#60a5fa",
    "fibre-om4": "#22d3ee",
    "fibre-os2": "#eab308",
    "fibre": "#22d3ee",
    "dac": "#64748b",
}


def _port_index(t: EquipmentType, port: str) -> tuple[int, int]:
    """(index 0-based, total) du port nommé ; (0, 1) si inconnu."""
    names = [p.name for p in t.ports]
    if port and port in names:
        return names.index(port), max(len(names), 1)
    return 0, 1


def _item_xy(rack: Rack, item, t: EquipmentType, offset_x: float,
             offset_y: float, face: str, port: str
             ) -> tuple[float, float, float, float]:
    """(x_gauche, x_droite, y_port, y_milieu) en px SVG."""
    inner_x = FRAME_PAD + RAIL_W
    top_u = item.position_u + t.u_height - 1
    y_top = offset_y + _u_to_y(rack, top_u if not rack.desc_units
                               else item.position_u)
    ih = t.u_height * U_PX
    ix, iw, shared = _item_box(t, item, inner_x, face)
    bx = offset_x + (ix if shared else inner_x)
    bw = iw if shared else RACK_W
    idx, n = _port_index(t, port)
    # Répartition verticale dans la façade (haut → bas, comme les ports).
    y_port = y_top + (idx + 0.5) / n * ih
    return bx, bx + bw, y_port, y_top + ih / 2


def render_cables_svg(project: Project, face: str = "front") -> list[str]:
    """Fragments SVG des cordons (à insérer avant ``</svg>``)."""
    types = type_index(project)
    offsets: dict[str, float] = {}
    x = 20.0
    for rack in project.racks:
        offsets[rack.id] = x
        w, _h = _rack_size(rack)
        x += w + GAP_X
    items = {i.id: (r, i) for r in project.racks for i in r.items}
    out = ['<g id="cables" fill="none" stroke-linecap="round">']
    n = 0
    for link in project.logical.links:
        a, b = link.from_.equipment_id, link.to.equipment_id
        if a not in items or b not in items:
            continue
        ra, ia = items[a]
        rb, ib = items[b]
        ta, tb = types.get(ia.type_id), types.get(ib.type_id)
        if ta is None or tb is None:
            continue
        ax1, ax2, ay, _ = _item_xy(ra, ia, ta, offsets[ra.id], 52, face,
                                   link.from_.port)
        bx1, bx2, by, _ = _item_xy(rb, ib, tb, offsets[rb.id], 52, face,
                                   link.to.port)
        sag = 26 + (n % 5) * 9
        same = ra.id == rb.id
        if same:
            x1, x2 = ax2, bx2
            g = max(x1, x2) + sag
            d = f"M {x1:.1f} {ay:.1f} C {g:.1f} {ay:.1f}, {g:.1f} {by:.1f}, {x2:.1f} {by:.1f}"
        else:
            to_right = offsets[rb.id] >= offsets[ra.id]
            x1 = ax2 if to_right else ax1
            x2 = bx1 if to_right else bx2
            dx = sag if to_right else -sag
            d = (f"M {x1:.1f} {ay:.1f} C {x1 + dx:.1f} {ay:.1f}, "
                 f"{x2 - dx:.1f} {by:.1f}, {x2:.1f} {by:.1f}")
        color = CABLE_COLORS.get(link.media or "", "#94a3b8")
        tip = _cable_title(link, ia, ib)
        out.append(f'<path d="{d}" stroke="rgba(0,0,0,.45)" stroke-width="4.5"/>')
        out.append(f'<path id="cable-{link.id}" class="cable-path" d="{d}" '
                   f'stroke="{color}" stroke-width="2.2"><title>{tip}</title></path>')
        n += 1
    out.append("</g>")
    return out if n else []


def _cable_title(link: LogicalLink, ia, ib) -> str:
    from xml.sax.saxutils import escape
    a = ia.meta.hostname or link.from_.equipment_id
    b = ib.meta.hostname or link.to.equipment_id
    if link.from_.port:
        a += f" · {link.from_.port}"
    if link.to.port:
        b += f" · {link.to.port}"
    extra = []
    if link.media:
        extra.append(link.media)
    if link.vlans:
        extra.append("VLAN " + ",".join(str(v) for v in link.vlans))
    return escape(f"{a}  →  {b}" + (f"  ({', '.join(extra)})" if extra else ""))
