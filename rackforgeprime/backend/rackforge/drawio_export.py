"""Export draw.io (.drawio) — le schéma RÉÉDITABLE chez eux.

Deux pages dans un même fichier : « Élévation » (baies à l'échelle U,
mêmes constantes que svg_export) et « Logique » (mêmes positions que
svg_logical). Chaque équipement est une cellule nommée et déplaçable :
l'utilisateur peut finir son schéma dans app.diagrams.net ou le bureau
draw.io, hors de RackForgePrime — aucun enfermement.

XML mxGraphModel non compressé : lisible, diffable, importable partout.
"""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from .models import EquipmentType, Project, type_index
from .svg_export import (FRAME_PAD, HEADER_H, RACK_W, RAIL_W, U_PX,
                         _rack_size, _u_to_y)
from .svg_logical import (LAYER_RANK, LINK_STYLES, NODE_H, NODE_W,
                          ZONE_LABELS, layout_nodes)

GAP_X = 80  # espacement entre baies dans la page draw.io

# Couleurs draw.io (thème clair : c'est un document de travail).
_FRAME_FILL = "#f4f5f6"
_FRAME_STROKE = "#9aa2ad"
_SLOT_FILL = "#ececef"
_TEXT = "#1c2126"

_EDGE_STYLE = {
    # kind -> (strokeColor, dashed, strokeWidth)
    "trunk": ("#0e7490", 0, 3),
    "uplink": ("#15803d", 0, 2),
    "access": ("#64748b", 0, 1),
    "ha": ("#dc2626", 1, 2),
    "other": ("#94a3b8", 1, 1),
}


def _cell(cid: str, value: str, style: str, x: float, y: float,
          w: float, h: float, parent: str = "1") -> str:
    return (f'<mxCell id={quoteattr(cid)} value={quoteattr(value)} '
            f'style={quoteattr(style)} vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" '
            f'height="{h:.0f}" as="geometry"/></mxCell>')


def _tint(color: str) -> str:
    """Teinte claire d'une couleur de rôle (fond de cellule lisible)."""
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        mix = tuple(int(c + (255 - c) * 0.85) for c in (r, g, b))
        return "#{:02x}{:02x}{:02x}".format(*mix)
    except (ValueError, IndexError):
        return "#f5f5f5"


def _physical_cells(project: Project,
                    types: dict[str, EquipmentType]) -> list[str]:
    cells: list[str] = []
    x_off = 40.0
    for rack in project.racks:
        w, h = _rack_size(rack)
        inner_x = x_off + FRAME_PAD + RAIL_W
        # Cadre de baie + titre.
        cells.append(_cell(
            f"rack-{rack.id}",
            f"{rack.name}" + (f"\n{rack.location}" if rack.location else ""),
            "rounded=1;fillColor=" + _FRAME_FILL + ";strokeColor="
            + _FRAME_STROKE + ";verticalAlign=top;fontSize=14;fontStyle=1;"
            "fontColor=" + _TEXT + ";arcSize=4;",
            x_off, 40, w, h))
        # Zone U (fond) — un rectangle discret, non imbriqué (les cellules
        # restent au premier niveau : déplaçables individuellement).
        cells.append(_cell(
            f"rack-{rack.id}-slots", "",
            "fillColor=" + _SLOT_FILL + ";strokeColor=#c9ced4;",
            inner_x, 40 + HEADER_H + FRAME_PAD, RACK_W,
            rack.u_height * U_PX))
        # Numéros de U (rail gauche).
        for u in range(1, rack.u_height + 1):
            y = 40 + _u_to_y(rack, u)
            cells.append(_cell(
                f"rack-{rack.id}-u{u}", str(u),
                "text;fontSize=8;fontColor=#6b7480;align=center;",
                x_off + FRAME_PAD, y, RAIL_W, U_PX))
        # Équipements.
        for item in rack.items:
            t = types.get(item.type_id)
            if t is None:
                continue
            top_u = (item.position_u if rack.desc_units
                     else item.position_u + t.u_height - 1)
            y = 40 + _u_to_y(rack, top_u)
            label = item.meta.hostname or f"{t.vendor} {t.model}"
            sub = f"{t.vendor} {t.model} · {t.u_height}U"
            cells.append(_cell(
                f"item-{item.id}", f"{label}\n{sub}",
                "rounded=1;arcSize=8;fillColor=" + _tint(t.color)
                + ";strokeColor=" + t.color + ";fontColor=" + _TEXT
                + ";fontSize=10;align=left;spacingLeft=8;whiteSpace=wrap;",
                inner_x, y + 1, RACK_W, t.u_height * U_PX - 2))
        x_off += w + GAP_X
    return cells


def _logical_cells(project: Project,
                   types: dict[str, EquipmentType]) -> list[str]:
    cells: list[str] = []
    pos = layout_nodes(project, types)
    items = {i.id: (r, i) for r in project.racks for i in r.items}
    # Zones de couche (dessinées d'abord : elles restent derrière).
    ranks: dict[int, list[str]] = {}
    for nid in pos:
        _, item = items[nid]
        t = types.get(item.type_id)
        rank = LAYER_RANK.get(t.category if t else "other", 5)
        ranks.setdefault(rank, []).append(nid)
    for rank, ids in sorted(ranks.items()):
        xs = [pos[i][0] for i in ids]
        ys = [pos[i][1] for i in ids]
        cells.append(_cell(
            f"zone-{rank}", ZONE_LABELS.get(rank, "AUTRES"),
            "rounded=1;dashed=1;fillColor=none;strokeColor=#9aa2ad;"
            "verticalAlign=top;align=left;spacingLeft=10;fontSize=9;"
            "fontColor=#6b7480;",
            min(xs) - 16, min(ys) - 26,
            max(xs) + NODE_W + 16 - (min(xs) - 16),
            max(ys) + NODE_H + 12 - (min(ys) - 26)))
    # Nœuds.
    for nid, (x, y) in pos.items():
        rack, item = items[nid]
        t = types.get(item.type_id)
        label = item.meta.hostname or (f"{t.vendor} {t.model}" if t else nid)
        sub = f"{rack.name} · U{item.position_u}"
        if item.meta.mgmt_ip:
            sub += f" · {item.meta.mgmt_ip}"
        cells.append(_cell(
            f"lnode-{nid}", f"{label}\n{sub}",
            "rounded=1;arcSize=10;fillColor=" + _tint(t.color if t else "#888")
            + ";strokeColor=" + (t.color if t else "#888888")
            + ";fontColor=" + _TEXT + ";fontSize=11;whiteSpace=wrap;",
            x, y, NODE_W, NODE_H))
    # Liens.
    for link in project.logical.links:
        if (link.from_.equipment_id not in pos
                or link.to.equipment_id not in pos):
            continue
        color, dashed, width = _EDGE_STYLE.get(link.kind,
                                               _EDGE_STYLE["other"])
        label = link.label or link.kind
        ports = " · ".join(p for p in (link.from_.port, link.to.port) if p)
        if ports:
            label += f"\n({ports})"
        cells.append(
            f'<mxCell id={quoteattr("edge-" + link.id)} '
            f'value={quoteattr(label)} edge="1" parent="1" '
            f'source={quoteattr("lnode-" + link.from_.equipment_id)} '
            f'target={quoteattr("lnode-" + link.to.equipment_id)} '
            f'style="edgeStyle=orthogonalEdgeStyle;rounded=1;'
            f'strokeColor={color};strokeWidth={width};dashed={dashed};'
            f'fontSize=9;fontColor={color};endArrow=none;">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')
    return cells


def _diagram(name: str, cells: list[str]) -> str:
    body = "".join(cells)
    return (f'<diagram name={quoteattr(name)}>'
            f'<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" '
            f'page="1" pageScale="1" pageWidth="1169" pageHeight="826" '
            f'math="0" shadow="0"><root>'
            f'<mxCell id="0"/><mxCell id="1" parent="0"/>'
            f'{body}</root></mxGraphModel></diagram>')


def render_drawio(project: Project) -> str:
    """Projet -> fichier .drawio (2 pages : Élévation + Logique)."""
    types = type_index(project)
    return ('<mxfile host="RackForgePrime" type="device">'
            + _diagram("Élévation", _physical_cells(project, types))
            + _diagram("Logique", _logical_cells(project, types))
            + "</mxfile>")
