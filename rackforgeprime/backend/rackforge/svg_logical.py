"""Génération SVG du schéma logique (VLANs, liens, flux).

Conventions reprises de Lucidchart / Visio (voir docs/RECHERCHE_VISUELLE.md) :

- topologie **en couches** : firewall en haut, routeurs, cœur de réseau,
  brassage, puis serveurs et le reste — le sens de lecture d'un DAT ;
- liens typés : trunk épais, access fin, uplink accentué, HA en pointillés ;
- étiquettes de lien posées au milieu, pastilles VLAN colorées ;
- légende (VLANs + types de liens) intégrée au dessin.

Même contrat que l'élévation physique : attributs inline uniquement
(convertible svglib, rééditable draw.io/Inkscape), un ``<g>`` nommé par
nœud et par lien, mêmes nœuds/IDs que le schéma physique.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .models import EquipmentType, LogicalLink, Project, type_index

# --- Géométrie --------------------------------------------------------------
NODE_W = 170
NODE_H = 56
LAYER_GAP = 110      # espace vertical entre couches
NODE_GAP = 40        # espace horizontal entre nœuds d'une couche
MARGIN = 40
LEGEND_H = 70

# Ordre des couches (rang d'auto-layout) — lecture DAT du haut vers le bas.
LAYER_RANK = {
    "firewall": 0, "router": 1, "switch": 2, "patch-panel": 3,
    "server": 4, "ups": 5, "blank": 5, "cable-mgmt": 5, "other": 5,
}

# Styles de lien par type : (largeur, couleur, pointillés)
LINK_STYLES = {
    "trunk": (2.5, "#22d3ee", ""),
    "uplink": (2.0, "#34d399", ""),
    "access": (1.4, "#64748b", ""),
    "ha": (1.8, "#f87171", "6,4"),
    "other": (1.4, "#94a3b8", "3,3"),
}

# --- Palette (identique à svg_export.py) ------------------------------------
C_BG = "#0b0e14"
C_NODE = "#161b28"
C_LINE = "#2c3547"
C_TEXT = "#cbd5e1"
C_TEXT_DIM = "#64748b"
FONT = "Helvetica, Arial, sans-serif"
FONT_MONO = "Courier, monospace"


def _node_glyph(category: str, x: float, y: float, color: str) -> list[str]:
    """Petit pictogramme de rôle (conventions Visio simplifiées, trait fin)."""
    s: list[str] = []
    cx, cy = x + 16, y + NODE_H / 2
    a = f'stroke="{color}" stroke-width="1.4" fill="none"'
    if category == "firewall":
        # Mur crénelé : trois rangées de briques.
        for r in range(3):
            s.append(f'<rect x="{cx - 8}" y="{cy - 9 + r * 6}" width="16" '
                     f'height="5" {a}/>')
            s.append(f'<line x1="{cx - 8 + (4 if r % 2 else 8)}" '
                     f'y1="{cy - 9 + r * 6}" x2="{cx - 8 + (4 if r % 2 else 8)}" '
                     f'y2="{cy - 4 + r * 6}" {a}/>')
    elif category in ("switch", "patch-panel"):
        # Flèches croisées du symbole switch.
        s.append(f'<rect x="{cx - 10}" y="{cy - 7}" width="20" height="14" rx="2" {a}/>')
        s.append(f'<path d="M {cx - 6} {cy - 3} h 8 m -3 -3 l 3 3 l -3 3" {a}/>')
        s.append(f'<path d="M {cx + 6} {cy + 3} h -8 m 3 -3 l -3 3 l 3 3" {a}/>')
    elif category == "router":
        s.append(f'<circle cx="{cx}" cy="{cy}" r="10" {a}/>')
        s.append(f'<path d="M {cx - 5} {cy - 3} h 7 m -3 -3 l 3 3 l -3 3" {a}/>')
        s.append(f'<path d="M {cx + 5} {cy + 4} h -7 m 3 -3 l -3 3 l 3 3" {a}/>')
    elif category == "server":
        for r in range(3):
            s.append(f'<rect x="{cx - 9}" y="{cy - 10 + r * 7}" width="18" '
                     f'height="5" rx="1" {a}/>')
    elif category == "ups":
        # Éclair dans un rectangle.
        s.append(f'<rect x="{cx - 9}" y="{cy - 9}" width="18" height="18" rx="2" {a}/>')
        s.append(f'<path d="M {cx + 2} {cy - 6} l -6 7 h 5 l -3 6" {a}/>')
    else:
        s.append(f'<rect x="{cx - 9}" y="{cy - 9}" width="18" height="18" rx="3" {a}/>')
    return s


def _collect_nodes(project: Project, types: dict[str, EquipmentType]) -> list[dict]:
    """Tous les équipements posés, avec leur libellé et leur baie/U."""
    nodes = []
    for rack in project.racks:
        for item in rack.items:
            t = types.get(item.type_id)
            if t is None or t.category in ("blank", "cable-mgmt"):
                continue  # les obturateurs n'existent pas logiquement
            nodes.append({
                "id": item.id,
                "label": item.meta.hostname or f"{t.vendor} {t.model}",
                "sub": f"{rack.name} · U{item.position_u}"
                       + (f" · VLAN {item.meta.vlan}" if item.meta.vlan else ""),
                "category": t.category,
                "color": t.color,
            })
    return nodes


def layout_nodes(project: Project, types: dict[str, EquipmentType]
                 ) -> dict[str, tuple[float, float]]:
    """Positions des nœuds : celles posées à la main, sinon auto-layout
    en couches (le frontend applique exactement le même algorithme)."""
    nodes = _collect_nodes(project, types)
    layers: dict[int, list[dict]] = {}
    for n in nodes:
        layers.setdefault(LAYER_RANK.get(n["category"], 5), []).append(n)

    pos: dict[str, tuple[float, float]] = {}
    manual = project.logical.positions
    for rank in sorted(layers):
        row = layers[rank]
        for i, n in enumerate(row):
            if n["id"] in manual:
                p = manual[n["id"]]
                pos[n["id"]] = (p.x, p.y)
            else:
                pos[n["id"]] = (
                    MARGIN + i * (NODE_W + NODE_GAP),
                    MARGIN + 30 + rank * LAYER_GAP,
                )
    return pos


def _elbow(x1: float, y1: float, x2: float, y2: float) -> str:
    """Chemin orthogonal (coude à mi-hauteur) — convention Visio/Lucid."""
    if abs(y1 - y2) < 4:
        return f"M {x1:.0f} {y1:.0f} L {x2:.0f} {y2:.0f}"
    my = (y1 + y2) / 2
    return (f"M {x1:.0f} {y1:.0f} L {x1:.0f} {my:.0f} "
            f"L {x2:.0f} {my:.0f} L {x2:.0f} {y2:.0f}")


def _render_link(link: LogicalLink, pos: dict[str, tuple[float, float]],
                 vlan_colors: dict[int, str]) -> list[str]:
    a, b = pos.get(link.from_.equipment_id), pos.get(link.to.equipment_id)
    if a is None or b is None:
        return []  # extrémité inconnue : lien ignoré au dessin
    # Ancres : bas du nœud du haut -> haut du nœud du bas.
    (ax, ay), (bx, by) = a, b
    x1, y1 = ax + NODE_W / 2, ay + (NODE_H if ay <= by else 0)
    x2, y2 = bx + NODE_W / 2, by + (NODE_H if by < ay else 0)
    width, color, dash = LINK_STYLES.get(link.kind, LINK_STYLES["other"])
    s = [f'<g id="link-{escape(link.id)}">']
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    s.append(f'<path d="{_elbow(x1, y1, x2, y2)}" fill="none" '
             f'stroke="{color}" stroke-width="{width}"{dash_attr}/>')
    # Étiquette + ports + pastilles VLAN au point médian.
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    label = link.label or link.kind
    ports = " · ".join(p for p in (link.from_.port, link.to.port) if p)
    text = label + (f"  ({ports})" if ports else "")
    tw = max(len(text) * 5.4, 30)
    s.append(f'<rect x="{mx - tw / 2 - 4:.0f}" y="{my - 17:.0f}" '
             f'width="{tw + 8:.0f}" height="14" rx="3" fill="{C_BG}" '
             f'stroke="{C_LINE}" stroke-width="0.5"/>')
    s.append(f'<text x="{mx:.0f}" y="{my - 7:.0f}" text-anchor="middle" '
             f'font-family="{FONT_MONO}" font-size="9" fill="{C_TEXT}">'
             f'{escape(text)}</text>')
    for j, vid in enumerate(link.vlans[:8]):
        s.append(f'<circle cx="{mx - len(link.vlans[:8]) * 6 + 6 + j * 12:.0f}" '
                 f'cy="{my + 8:.0f}" r="4" '
                 f'fill="{vlan_colors.get(vid, "#64748b")}"/>')
    s.append('</g>')
    return s


def render_logical_svg(project: Project) -> str:
    """Schéma logique complet du projet -> SVG."""
    types = type_index(project)
    nodes = _collect_nodes(project, types)
    pos = layout_nodes(project, types)
    vlan_colors = {v.vid: v.color for v in project.logical.vlans}

    max_x = max((x for x, _ in pos.values()), default=0) + NODE_W + MARGIN
    max_y = max((y for _, y in pos.values()), default=0) + NODE_H + MARGIN
    total_w = max(max_x, 640)
    total_h = max_y + LEGEND_H + 40

    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" '
        f'height="{total_h}" viewBox="0 0 {total_w} {total_h}" '
        f'font-family="{FONT}">',
        f'<rect x="0" y="0" width="{total_w}" height="{total_h}" fill="{C_BG}"/>',
        f'<text x="{MARGIN}" y="28" font-size="16" font-weight="bold" '
        f'fill="{C_TEXT}">{escape(project.name)} — schéma logique</text>',
    ]

    # Liens d'abord (sous les nœuds).
    for link in project.logical.links:
        s.extend(_render_link(link, pos, vlan_colors))

    # Nœuds.
    for n in nodes:
        x, y = pos[n["id"]]
        s.append(f'<g id="lnode-{escape(n["id"])}">')
        s.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{NODE_W}" '
                 f'height="{NODE_H}" rx="6" fill="{C_NODE}" '
                 f'stroke="{C_LINE}" stroke-width="1"/>')
        s.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="4" height="{NODE_H}" '
                 f'rx="2" fill="{n["color"]}"/>')
        s.extend(_node_glyph(n["category"], x + 8, y, n["color"]))
        s.append(f'<text x="{x + 38:.0f}" y="{y + 24:.0f}" font-size="12" '
                 f'fill="{C_TEXT}">{escape(n["label"][:22])}</text>')
        s.append(f'<text x="{x + 38:.0f}" y="{y + 40:.0f}" font-size="9" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT_DIM}">'
                 f'{escape(n["sub"])}</text>')
        s.append('</g>')

    # Légende : VLANs puis types de liens.
    ly = total_h - LEGEND_H
    s.append(f'<line x1="{MARGIN}" y1="{ly}" x2="{total_w - MARGIN}" y2="{ly}" '
             f'stroke="{C_LINE}" stroke-width="1"/>')
    lx = MARGIN
    for v in project.logical.vlans:
        s.append(f'<circle cx="{lx + 5}" cy="{ly + 20}" r="5" fill="{v.color}"/>')
        s.append(f'<text x="{lx + 14}" y="{ly + 24}" font-size="10" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT}">'
                 f'{v.vid} {escape(v.name)}</text>')
        lx += 24 + len(f"{v.vid} {v.name}") * 6
    lx = MARGIN
    for kind, (w, color, dash) in LINK_STYLES.items():
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        s.append(f'<line x1="{lx}" y1="{ly + 45}" x2="{lx + 26}" y2="{ly + 45}" '
                 f'stroke="{color}" stroke-width="{w}"{dash_attr}/>')
        s.append(f'<text x="{lx + 32}" y="{ly + 48}" font-size="10" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT_DIM}">{kind}</text>')
        lx += 32 + len(kind) * 6 + 22

    s.append('</svg>')
    return "\n".join(s)
