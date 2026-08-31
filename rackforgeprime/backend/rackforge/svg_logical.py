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
NODE_W = 214
NODE_H = 64
LAYER_GAP = 120      # espace vertical entre couches (zones comprises)
NODE_GAP = 40        # espace horizontal entre nœuds d'une couche
MARGIN = 40
LEGEND_H = 70

# Zones par couche — la lecture DAT (conteneurs Lucid : bordure + titre).
ZONE_LABELS = {
    0: "SÉCURITÉ — PARE-FEU", 1: "ROUTAGE", 2: "CŒUR / DISTRIBUTION",
    3: "BRASSAGE", 4: "SERVEURS", 5: "ÉNERGIE & AUTRES",
}

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

# --- Palettes par thème (cohérentes avec svg_export.PALETTES) ---------------
LPALETTES = {
    "sombre": {"bg": "#0b0e14", "node": "#161b28", "line": "#2c3547",
               "text": "#cbd5e1", "dim": "#64748b"},
    "clair": {"bg": "#ffffff", "node": "#f7f8f9", "line": "#d3d8de",
              "text": "#1c2126", "dim": "#6b7480"},
}
# Palette active du rendu en cours (posée par render_logical_svg — module
# mono-thread côté serveur, même modèle que le reste du fichier).
_P = LPALETTES["sombre"]
C_BG = _P["bg"]
C_NODE = _P["node"]
C_LINE = _P["line"]
C_TEXT = _P["text"]
C_TEXT_DIM = _P["dim"]
FONT = "Helvetica, Arial, sans-serif"
FONT_MONO = "Courier, monospace"


def _set_theme(theme: str) -> None:
    global _P, C_BG, C_NODE, C_LINE, C_TEXT, C_TEXT_DIM
    _P = LPALETTES.get(theme, LPALETTES["sombre"])
    C_BG, C_NODE, C_LINE = _P["bg"], _P["node"], _P["line"]
    C_TEXT, C_TEXT_DIM = _P["text"], _P["dim"]


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
                       + (f" · {item.meta.mgmt_ip}" if item.meta.mgmt_ip else "")
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
    # Couches centrées sur la plus large (lecture en colonne, pas en
    # escalier) + léger décalage alterné anti-traversée de nœuds.
    row_w = {rank: len(row) * (NODE_W + NODE_GAP) - NODE_GAP
             for rank, row in layers.items()}
    max_w = max(row_w.values(), default=NODE_W)
    # Un WAN documenté (usage contenant « WAN ») réserve de la place en
    # tête pour le nuage Internet.
    top_extra = 78 if _wan_item(project) else 0
    for rank in sorted(layers):
        row = layers[rank]
        stagger = (rank % 2) * (NODE_W / 2 + 30)
        x0 = MARGIN + 26 + (max_w - row_w[rank]) / 2 + stagger
        for i, n in enumerate(row):
            if n["id"] in manual:
                p = manual[n["id"]]
                pos[n["id"]] = (p.x, p.y)
            else:
                pos[n["id"]] = (
                    x0 + i * (NODE_W + NODE_GAP),
                    MARGIN + 40 + top_extra + rank * LAYER_GAP,
                )
    return pos


def _wan_item(project: Project):
    """Premier équipement dont un port documente le WAN (usage « WAN… »)."""
    for rack in project.racks:
        for item in rack.items:
            for pu in item.meta.port_usage:
                if "wan" in (pu.usage or "").lower():
                    return item
    return None


def _elbow(x1: float, y1: float, x2: float, y2: float) -> str:
    """Chemin orthogonal à coude mi-hauteur, coins arrondis (rayon Lucid)."""
    if abs(y1 - y2) < 4:
        return f"M {x1:.0f} {y1:.0f} L {x2:.0f} {y2:.0f}"
    my = (y1 + y2) / 2
    if abs(x1 - x2) < 4:
        return f"M {x1:.0f} {y1:.0f} L {x2:.0f} {y2:.0f}"
    # Rayon borné par la place disponible sur chaque segment.
    r = min(8.0, abs(x2 - x1) / 2, abs(my - y1), abs(y2 - my))
    sy = 1 if my > y1 else -1      # sens vertical du 1er segment
    sx = 1 if x2 > x1 else -1      # sens horizontal du segment médian
    return (f"M {x1:.0f} {y1:.0f} "
            f"L {x1:.0f} {my - sy * r:.1f} "
            f"Q {x1:.0f} {my:.0f} {x1 + sx * r:.1f} {my:.0f} "
            f"L {x2 - sx * r:.1f} {my:.0f} "
            f"Q {x2:.0f} {my:.0f} {x2:.0f} {my + sy * r:.1f} "
            f"L {x2:.0f} {y2:.0f}")


def tw_side(link: LogicalLink) -> float:
    """Largeur estimée de l'étiquette complète d'un lien (px)."""
    label = link.label or link.kind
    ports = " · ".join(p for p in (link.from_.port, link.to.port) if p)
    return max(len(label + (f"  ({ports})" if ports else "")) * 5.6, 30)


def _render_link(link: LogicalLink, pos: dict[str, tuple[float, float]],
                 vlan_colors: dict[int, str],
                 placed: list[tuple[float, float, float]] | None = None,
                 fan: tuple[int, int] = (0, 1)) -> tuple[list[str], list[str]]:
    """(trait, étiquette) — le trait passe SOUS les nœuds, l'étiquette
    au-dessus de tout (sinon les nœuds la recouvrent)."""
    a, b = pos.get(link.from_.equipment_id), pos.get(link.to.equipment_id)
    if a is None or b is None:
        return [], [], None  # extrémité inconnue : lien ignoré au dessin
    (ax, ay), (bx, by) = a, b
    same_layer = abs(ay - by) < NODE_H / 2
    if same_layer:
        # Même couche : bord à bord (jamais derrière les nœuds).
        left, right = (a, b) if ax <= bx else (b, a)
        x1, y1 = left[0] + NODE_W, left[1] + NODE_H / 2
        x2, y2 = right[0], right[1] + NODE_H / 2
    else:
        # Couches différentes : bas du nœud du haut -> haut du nœud du bas.
        # Liens parallèles (même paire) : en éventail, jamais superposés.
        idx, n = fan
        dx = (idx - (n - 1) / 2) * min(44, (NODE_W - 24) / max(n - 1, 1))
        x1, y1 = ax + NODE_W / 2 + dx, ay + (NODE_H if ay <= by else 0)
        x2, y2 = bx + NODE_W / 2 + dx, by + (NODE_H if by < ay else 0)
    width, color, dash = LINK_STYLES.get(link.kind, LINK_STYLES["other"])
    s = [f'<g id="link-{escape(link.id)}">']
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    s.append(f'<path d="{_elbow(x1, y1, x2, y2)}" fill="none" '
             f'stroke="{color}" stroke-width="{width}"{dash_attr}/>')
    s.append('</g>')
    # Étiquette + ports + pastilles VLAN au point médian, dans un groupe
    # séparé rendu APRÈS les nœuds.
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if same_layer:
        # L'entre-deux est trop étroit : étiquette au-dessus des nœuds.
        my = min(a[1], b[1]) - 2
    elif abs(y2 - y1) > LAYER_GAP * 1.2:
        # Lien qui traverse plusieurs couches : étiquette À CÔTÉ du
        # segment vertical, près de l'ARRIVÉE (le couloir du départ est
        # occupé par les faisceaux) — jamais sur une couche intermédiaire.
        mx, my = x2 + tw_side(link) / 2 + 14, max(y1, y2) - 26
    label = link.label or link.kind
    ports = " · ".join(p for p in (link.from_.port, link.to.port) if p)
    idx, n = fan
    lbl = [f'<g id="link-label-{escape(link.id)}">']
    if n >= 3 and not same_layer:
        # Faisceau de liens parallèles : pastille numérotée sur chaque
        # fil, le détail part dans une liste déportée (pratique des
        # plans d'ingénierie — le couloir reste lisible).
        my += -10 + 20 * (idx % 2)
        lbl.append(f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="7.5" '
                   f'fill="{C_BG}" stroke="{color}" stroke-width="1.3"/>')
        lbl.append(f'<text x="{mx:.0f}" y="{my + 3:.0f}" text-anchor="middle" '
                   f'font-family="{FONT_MONO}" font-size="9" '
                   f'font-weight="bold" fill="{color}">{idx + 1}</text>')
        lbl.append('</g>')
        stack = (f"{idx + 1}.  {label}" + (f"  ({ports})" if ports else ""),
                 color)
        return s, lbl, stack
    text = label + (f"  ({ports})" if ports else "")
    tw = max(len(text) * 5.6, 30)
    # Anti-chevauchement : si une étiquette déjà posée est trop proche,
    # celle-ci descend d'un cran (jusqu'à trouver une place).
    if placed is not None:
        for _ in range(6):
            if not any(abs(mx - px) < (tw + pw) / 2 + 8 and abs(my - py) < 16
                       for px, py, pw in placed):
                break
            my += 19
        placed.append((mx, my, tw))
    lbl.append(f'<rect x="{mx - tw / 2 - 4:.0f}" y="{my - 17:.0f}" '
               f'width="{tw + 8:.0f}" height="14" rx="3" fill="{C_BG}" '
               f'stroke="{C_LINE}" stroke-width="0.5"/>')
    # Étiquette colorée comme le lien (convention Lucid : la couleur porte
    # la sémantique du flux, le texte la reprend).
    lbl.append(f'<text x="{mx:.0f}" y="{my - 7:.0f}" text-anchor="middle" '
               f'font-family="{FONT_MONO}" font-size="11" fill="{color}">'
               f'{escape(text)}</text>')
    for j, vid in enumerate(link.vlans[:8]):
        lbl.append(f'<circle cx="{mx - len(link.vlans[:8]) * 6 + 6 + j * 12:.0f}" '
                   f'cy="{my + 8:.0f}" r="4" '
                   f'fill="{vlan_colors.get(vid, "#64748b")}"/>')
    lbl.append('</g>')
    return s, lbl, None


def render_logical_svg(project: Project, theme: str = "sombre") -> str:
    """Schéma logique complet du projet -> SVG."""
    _set_theme(theme)
    types = type_index(project)
    nodes = _collect_nodes(project, types)
    pos = layout_nodes(project, types)
    vlan_colors = {v.vid: v.color for v in project.logical.vlans}

    max_x = max((x for x, _ in pos.values()), default=0) + NODE_W + MARGIN
    max_y = max((y for _, y in pos.values()), default=0) + NODE_H + MARGIN
    # Un faisceau de liens parallèles (>= 3) déporte sa liste numérotée
    # à droite : on réserve la colonne.
    counts: dict[frozenset, int] = {}
    for link in project.logical.links:
        pair = frozenset((link.from_.equipment_id, link.to.equipment_id))
        counts[pair] = counts.get(pair, 0) + 1
    stack_w = 320 if any(v >= 3 for v in counts.values()) else 0
    total_w = max(max_x + stack_w, 640)
    total_h = max_y + LEGEND_H + 40

    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" '
        f'height="{total_h}" viewBox="0 0 {total_w} {total_h}" '
        f'font-family="{FONT}">',
        f'<rect x="0" y="0" width="{total_w}" height="{total_h}" fill="{C_BG}"/>',
        f'<text x="{MARGIN}" y="28" font-size="18" font-weight="bold" '
        f'fill="{C_TEXT}">{escape(project.name)} — schéma logique</text>',
    ]

    # Zones de couche (conteneurs Lucid : bordure + titre, pas de fond) —
    # dessinées en premier, derrière tout.
    ranks: dict[int, list[str]] = {}
    cat_by_id = {n["id"]: n["category"] for n in nodes}
    for nid, (x, y) in pos.items():
        rank = LAYER_RANK.get(cat_by_id.get(nid, "other"), 5)
        ranks.setdefault(rank, []).append(nid)
    for rank, ids in sorted(ranks.items()):
        xs = [pos[i][0] for i in ids]
        ys = [pos[i][1] for i in ids]
        zx, zy = min(xs) - 16, min(ys) - 24
        zw = max(xs) + NODE_W + 16 - zx
        zh = max(ys) + NODE_H + 12 - zy
        s.append(f'<g id="zone-{rank}">')
        s.append(f'<rect x="{zx:.0f}" y="{zy:.0f}" width="{zw:.0f}" '
                 f'height="{zh:.0f}" rx="10" fill="none" '
                 f'stroke="{C_LINE}" stroke-width="1" '
                 f'stroke-dasharray="5,4"/>')
        s.append(f'<text x="{zx + 12:.0f}" y="{zy + 14:.0f}" '
                 f'font-family="{FONT}" font-size="11" letter-spacing="1.5" '
                 f'fill="{C_TEXT_DIM}">'
                 f'{escape(ZONE_LABELS.get(rank, "AUTRES"))}</text>')
        s.append('</g>')

    # Traits des liens d'abord (sous les nœuds) ; étiquettes gardées pour
    # la fin (au-dessus de tout).
    labels: list[str] = []
    placed: list[tuple[float, float, float]] = []
    # Liens parallèles (même paire d'équipements) : index d'éventail.
    pair_total: dict[frozenset, int] = {}
    for link in project.logical.links:
        pair = frozenset((link.from_.equipment_id, link.to.equipment_id))
        pair_total[pair] = pair_total.get(pair, 0) + 1
    pair_seen: dict[frozenset, int] = {}
    stacks: list[tuple[str, str]] = []
    for link in project.logical.links:
        pair = frozenset((link.from_.equipment_id, link.to.equipment_id))
        idx = pair_seen.get(pair, 0)
        pair_seen[pair] = idx + 1
        line, lbl, stack = _render_link(link, pos, vlan_colors, placed,
                                        fan=(idx, pair_total[pair]))
        s.extend(line)
        labels.extend(lbl)
        if stack:
            stacks.append(stack)

    # Liste déportée des faisceaux numérotés, à droite du schéma.
    if stacks:
        sx = max((x for x, _ in pos.values()), default=0) + NODE_W + 34
        sy = min((y for _, y in pos.values()), default=100) + 30
        labels.append(f'<text x="{sx}" y="{sy - 16}" font-family="{FONT}" '
                      f'font-size="11.5" letter-spacing="1" '
                      f'fill="{C_TEXT_DIM}">LIAISONS NUMÉROTÉES</text>')
        for k, (text, color) in enumerate(stacks):
            labels.append(f'<text x="{sx}" y="{sy + k * 17}" '
                          f'font-family="{FONT_MONO}" font-size="11" '
                          f'fill="{color}">{escape(text)}</text>')

    # Nuage WAN / Internet — dessiné seulement s'il est documenté (un
    # port dont l'usage mentionne WAN) : jamais inventé.
    wan = _wan_item(project)
    if wan is not None and wan.id in pos:
        wx = pos[wan.id][0] + NODE_W / 2
        wy = pos[wan.id][1] - 62
        s.append(f'<g id="wan-cloud">')
        s.append(f'<path d="M {wx - 46:.0f} {wy + 14:.0f} '
                 f'a 16 16 0 0 1 14 -22 a 20 20 0 0 1 36 -6 '
                 f'a 15 15 0 0 1 24 12 a 13 13 0 0 1 -8 24 '
                 f'l -56 0 a 14 14 0 0 1 -10 -8 z" '
                 f'fill="{C_NODE}" stroke="{C_TEXT_DIM}" '
                 f'stroke-width="1.3" stroke-dasharray="5,3"/>')
        s.append(f'<text x="{wx:.0f}" y="{wy + 8:.0f}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="12" font-weight="bold" '
                 f'fill="{C_TEXT}">WAN — Internet</text>')
        s.append(f'<line x1="{wx:.0f}" y1="{wy + 26:.0f}" x2="{wx:.0f}" '
                 f'y2="{pos[wan.id][1]:.0f}" stroke="{C_TEXT_DIM}" '
                 f'stroke-width="1.5" stroke-dasharray="5,3"/>')
        s.append('</g>')

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
        # Libellé jamais tronqué en plein mot : ellipse au-delà de 26 car.
        lbl = n["label"] if len(n["label"]) <= 26 else n["label"][:25] + "…"
        s.append(f'<text x="{x + 38:.0f}" y="{y + 24:.0f}" font-size="14" '
                 f'fill="{C_TEXT}">{escape(lbl)}</text>')
        s.append(f'<text x="{x + 38:.0f}" y="{y + 40:.0f}" font-size="11" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT_DIM}">'
                 f'{escape(n["sub"])}</text>')
        s.append('</g>')

    # Étiquettes de liens par-dessus les nœuds.
    s.extend(labels)

    # Légende : VLANs puis types de liens.
    ly = total_h - LEGEND_H
    s.append(f'<line x1="{MARGIN}" y1="{ly}" x2="{total_w - MARGIN}" y2="{ly}" '
             f'stroke="{C_LINE}" stroke-width="1"/>')
    lx = MARGIN
    for v in project.logical.vlans:
        s.append(f'<circle cx="{lx + 5}" cy="{ly + 20}" r="5" fill="{v.color}"/>')
        s.append(f'<text x="{lx + 14}" y="{ly + 24}" font-size="12" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT}">'
                 f'{v.vid} {escape(v.name)}</text>')
        lx += 24 + len(f"{v.vid} {v.name}") * 6
    lx = MARGIN
    for kind, (w, color, dash) in LINK_STYLES.items():
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        s.append(f'<line x1="{lx}" y1="{ly + 45}" x2="{lx + 26}" y2="{ly + 45}" '
                 f'stroke="{color}" stroke-width="{w}"{dash_attr}/>')
        s.append(f'<text x="{lx + 32}" y="{ly + 48}" font-size="12" '
                 f'font-family="{FONT_MONO}" fill="{C_TEXT_DIM}">{kind}</text>')
        lx += 32 + len(kind) * 6 + 22

    s.append('</svg>')
    return "\n".join(s)
