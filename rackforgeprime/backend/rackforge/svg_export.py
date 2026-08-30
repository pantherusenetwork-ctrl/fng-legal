"""Génération SVG des élévations de baies.

Le SVG est le format de rendu pivot : ce que l'écran affiche, ce que
l'export livre, et la source de la conversion PDF. Contraintes :

- échelle exacte : 1U = ``U_PX`` pixels partout, jamais d'à-peu-près ;
- attributs inline uniquement (pas de CSS) pour rester convertible par
  svglib et rééditable dans draw.io / Inkscape ;
- un ``<g id="...">`` nommé par baie et par équipement (réédition facile).
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .models import EquipmentType, Project, Rack, rack_stats, type_index

# --- Constantes d'échelle (le frontend utilise les mêmes valeurs) -----------
U_PX = 22           # hauteur d'1U à l'écran et à l'export
RACK_W = 440        # largeur intérieure 19" utile
RAIL_W = 26         # montant (rail) de chaque côté, graduations comprises
FRAME_PAD = 14      # cadre extérieur de la baie
HEADER_H = 40       # bandeau nom de baie
FOOTER_H = 30       # bandeau stats
GAP_X = 60          # espacement entre baies

# --- Palette (DA sombre futuriste sobre — docs/RECHERCHE_VISUELLE.md) -------
C_BG = "#0b0e14"
C_FRAME = "#1b2230"
C_RAIL = "#2a3446"
C_HOLE = "#0e1420"
C_SLOT = "#0e131d"
C_SLOT_LINE = "#1a2130"
C_TEXT = "#cbd5e1"
C_TEXT_DIM = "#64748b"
C_FACE = "#1a1f2b"
C_ACCENT = "#22d3ee"

FONT = "Helvetica, Arial, sans-serif"
FONT_MONO = "Courier, monospace"


def _rack_size(rack: Rack) -> tuple[int, int]:
    """(largeur, hauteur) totales d'une baie dessinée."""
    w = RACK_W + 2 * RAIL_W + 2 * FRAME_PAD
    h = rack.u_height * U_PX + HEADER_H + FOOTER_H + 2 * FRAME_PAD
    return w, h


def _u_to_y(rack: Rack, u: int) -> int:
    """Y (haut) du U donné, dans le repère local de la baie.

    U1 en bas par défaut (desc_units=False) : le haut de la zone U est
    U max, comme sur une baie réelle.
    """
    top = HEADER_H + FRAME_PAD
    if rack.desc_units:
        return top + (u - 1) * U_PX
    return top + (rack.u_height - u) * U_PX


def _port_banks(n: int, color: str, x: int, y: int, w: int,
                h: int) -> list[str]:
    """Ports groupés en banques de 6, sur 2 rangées au-delà de 12 — la
    lecture d'un vrai switch (esprit PATCHBOX), pas une frise de carrés."""
    s: list[str] = []
    n = min(n, 48)
    if not n:
        return s
    rows = 2 if n > 12 else 1
    cols = -(-n // rows)  # ceil
    pw, gapx, group, ggap = 7, 2, 6, 4
    ph = 6 if rows == 2 else 8
    groups = -(-cols // group)
    total_w = cols * (pw + gapx) - gapx + (groups - 1) * ggap
    x0 = x + w - 46 - total_w
    block_h = rows * ph + (rows - 1) * 3
    y0 = y + (h - block_h) / 2
    for i in range(n):
        r, c = i % rows, i // rows
        px = x0 + c * (pw + gapx) + (c // group) * ggap
        py = y0 + r * (ph + 3)
        s.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw}" height="{ph}" '
                 f'rx="1" fill="#0a0e16" stroke="{color}" stroke-width="0.7"/>')
        # Languette RJ45 : le détail qui fait « connecteur » et plus « pixel ».
        s.append(f'<rect x="{px + 2:.1f}" y="{py + ph - 1.6:.1f}" width="3" '
                 f'height="1.6" fill="{color}" fill-opacity="0.85"/>')
    return s


def _category_decor(t: EquipmentType, x: int, y: int, w: int,
                    h: int) -> list[str]:
    """Décor par catégorie pour les types sans ports (serveur, onduleur,
    passe-câbles) : silhouette reconnaissable au premier coup d'œil."""
    s: list[str] = []
    if t.category == "server":
        # Baies disques verticales, LED d'activité en tête.
        bw, gap, count = 13, 3, 10
        x0 = x + w - 46 - count * (bw + gap)
        for i in range(count):
            bx = x0 + i * (bw + gap)
            s.append(f'<rect x="{bx}" y="{y + 4}" width="{bw}" '
                     f'height="{h - 8}" rx="1" fill="#10151f" '
                     f'stroke="#2c3547" stroke-width="0.7"/>')
            s.append(f'<circle cx="{bx + bw / 2:.1f}" cy="{y + 7:.1f}" '
                     f'r="1.3" fill="{t.color}"/>')
    elif t.category == "ups":
        # Écran LCD + grille d'aération.
        s.append(f'<rect x="{x + w - 200}" y="{y + h / 2 - 8:.1f}" width="30" '
                 f'height="16" rx="2" fill="#0a2027" stroke="{t.color}" '
                 f'stroke-width="0.8"/>')
        for i in range(24):
            vx = x + w - 155 + i * 5
            s.append(f'<rect x="{vx}" y="{y + h / 2 - 6:.1f}" width="2" '
                     f'height="12" rx="1" fill="#10151f"/>')
    elif t.category == "cable-mgmt":
        # Anneaux passe-câbles (à droite du libellé, avant la pastille U).
        for i in range(4):
            rx0 = x + 200 + i * 50
            s.append(f'<rect x="{rx0}" y="{y + 3}" width="30" '
                     f'height="{h - 6}" rx="4" fill="none" '
                     f'stroke="#3a465c" stroke-width="2"/>')
    return s


def _faceplate_placeholder(t: EquipmentType, x: int, y: int, w: int,
                           label: str) -> list[str]:
    """Placeholder fidèle à l'échelle U quand pas d'image officielle.

    Style PATCHBOX / Lucidchart : bloc plat teinté par rôle, libellé net,
    pastille de hauteur U, ports en banques réalistes ou décor de catégorie.
    """
    h = t.u_height * U_PX
    yc = y + h / 2
    s: list[str] = []
    # Corps plat, coins arrondis (léger retrait pour lire la séparation U).
    s.append(f'<rect x="{x}" y="{y + 1}" width="{w}" height="{h - 2}" '
             f'rx="3" fill="{C_FACE}" stroke="#2c3547" stroke-width="1"/>')
    # Teinte du rôle sur tout le bloc — l'identité couleur PATCHBOX,
    # lisible à 1 m sans crier.
    s.append(f'<rect x="{x}" y="{y + 1}" width="{w}" height="{h - 2}" '
             f'rx="3" fill="{t.color}" fill-opacity="0.07"/>')
    s.append(f'<rect x="{x}" y="{y + 1}" width="4" height="{h - 2}" '
             f'fill="{t.color}"/>')
    # Oreilles de fixation sur les rails (vis suggérées).
    for ex in (x - RAIL_W + 6, x + w + RAIL_W - 12):
        s.append(f'<circle cx="{ex + 3}" cy="{yc:.1f}" r="2.5" '
                 f'fill="{C_HOLE}"/>')
    # Label principal : hostname s'il existe, sinon constructeur + modèle.
    s.append(f'<text x="{x + 14}" y="{yc + 4:.1f}" '
             f'font-family="{FONT}" font-size="11" fill="{C_TEXT}">'
             f'{escape(label)}</text>')
    # Pastille de hauteur U (esprit Lucid : badge, pas texte flottant).
    s.append(f'<rect x="{x + w - 34}" y="{yc - 7:.1f}" width="26" height="14" '
             f'rx="7" fill="none" stroke="#33405a" stroke-width="1"/>')
    s.append(f'<text x="{x + w - 21}" y="{yc + 3:.1f}" text-anchor="middle" '
             f'font-family="{FONT_MONO}" font-size="8.5" fill="{C_TEXT_DIM}">'
             f'{t.u_height}U</text>')
    # Serveur / onduleur / passe-câbles : la silhouette prime sur les
    # quelques ports de management — c'est elle qu'on reconnaît en baie.
    if t.category in ("server", "ups", "cable-mgmt"):
        s.extend(_category_decor(t, x, y, w, h))
    elif t.ports:
        s.extend(_port_banks(len(t.ports), t.color, x, y, w, h))
    return s


def render_rack(rack: Rack, types: dict[str, EquipmentType],
                offset_x: int = 0, offset_y: int = 0) -> str:
    """Rend une baie complète dans un <g> nommé."""
    w, h = _rack_size(rack)
    inner_x = FRAME_PAD + RAIL_W
    s: list[str] = [f'<g id="rack-{escape(rack.id)}" '
                    f'transform="translate({offset_x},{offset_y})">']
    # Cadre extérieur.
    s.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="6" '
             f'fill="{C_FRAME}" stroke="#2c3547" stroke-width="1.5"/>')
    # Bandeau : nom + localisation.
    s.append(f'<text x="{w / 2:.0f}" y="24" text-anchor="middle" '
             f'font-family="{FONT}" font-size="15" font-weight="bold" '
             f'fill="{C_TEXT}">{escape(rack.name)}</text>')
    if rack.location:
        s.append(f'<text x="{w / 2:.0f}" y="{HEADER_H - 2}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="9" fill="{C_TEXT_DIM}">'
                 f'{escape(rack.location)}</text>')
    # Zone U (fond en creux) + rails.
    zone_y = HEADER_H + FRAME_PAD
    zone_h = rack.u_height * U_PX
    s.append(f'<rect x="{inner_x}" y="{zone_y}" width="{RACK_W}" '
             f'height="{zone_h}" fill="{C_SLOT}"/>')
    for rx in (FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W):
        s.append(f'<rect x="{rx}" y="{zone_y}" width="{RAIL_W}" '
                 f'height="{zone_h}" fill="{C_RAIL}"/>')
    # Graduations U : numéro + trous de vissage (3 par U, EIA-310 suggéré).
    for u in range(1, rack.u_height + 1):
        y = _u_to_y(rack, u)
        s.append(f'<line x1="{inner_x}" y1="{y}" x2="{inner_x + RACK_W}" '
                 f'y2="{y}" stroke="{C_SLOT_LINE}" stroke-width="1"/>')
        for rx in (FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W):
            s.append(f'<text x="{rx + RAIL_W / 2:.0f}" y="{y + U_PX / 2 + 3:.1f}" '
                     f'text-anchor="middle" font-family="{FONT_MONO}" '
                     f'font-size="8" fill="{C_TEXT_DIM}">{u}</text>')
            for k in range(3):
                hy = y + 4 + k * ((U_PX - 8) / 2)
                s.append(f'<rect x="{rx + 2}" y="{hy:.1f}" width="3" height="3" '
                         f'rx="1" fill="{C_HOLE}"/>')
    s.append(f'<line x1="{inner_x}" y1="{zone_y + zone_h}" '
             f'x2="{inner_x + RACK_W}" y2="{zone_y + zone_h}" '
             f'stroke="{C_SLOT_LINE}" stroke-width="1"/>')
    # Équipements — un groupe nommé chacun.
    for item in rack.items:
        t = types.get(item.type_id)
        if t is None:
            continue
        top_u = item.position_u + t.u_height - 1
        y = _u_to_y(rack, top_u if not rack.desc_units else item.position_u)
        label = item.meta.hostname or f"{t.vendor} {t.model}"
        s.append(f'<g id="item-{escape(item.id)}">')
        if t.faceplate_svg:
            # SVG officiel : injecté tel quel, cadré à l'échelle U.
            s.append(f'<g transform="translate({inner_x},{y})">'
                     f'{t.faceplate_svg}</g>')
        elif t.faceplate_image:
            # Image officielle (PNG/JPEG en data URI) étirée sur le slot U
            # exact — c'est la convention des outils rack (TSS, NetBox).
            ih = t.u_height * U_PX
            s.append(f'<rect x="{inner_x}" y="{y + 1}" width="{RACK_W}" '
                     f'height="{ih - 2}" fill="{C_FACE}"/>')
            s.append(f'<image x="{inner_x}" y="{y + 1}" width="{RACK_W}" '
                     f'height="{ih - 2}" preserveAspectRatio="none" '
                     f'href="{t.faceplate_image}" '
                     f'xlink:href="{t.faceplate_image}"/>')
        else:
            s.extend(_faceplate_placeholder(t, inner_x, y, RACK_W, label))
        s.append('</g>')
    # Pied : stats de la baie (esprit TSS — stats live aussi à l'export).
    st = rack_stats(rack, types)
    s.append(f'<text x="{w / 2:.0f}" y="{h - FOOTER_H / 2:.0f}" '
             f'text-anchor="middle" font-family="{FONT_MONO}" font-size="10" '
             f'fill="{C_ACCENT}">{st["u_used"]}U occupés · '
             f'{st["u_free"]}U libres · {st["power_w"]:g} W</text>')
    s.append('</g>')
    return "\n".join(s)


def render_project_svg(project: Project) -> str:
    """SVG complet : toutes les baies du projet côte à côte."""
    types = type_index(project)
    racks = project.racks
    if not racks:
        racks = []
    sizes = [_rack_size(r) for r in racks]
    total_w = sum(w for w, _ in sizes) + GAP_X * max(len(racks) - 1, 0) + 40
    total_h = (max((h for _, h in sizes), default=200)) + 60
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_w}" '
        f'height="{total_h}" viewBox="0 0 {total_w} {total_h}" '
        f'font-family="{FONT}">',
        f'<rect x="0" y="0" width="{total_w}" height="{total_h}" fill="{C_BG}"/>',
        f'<text x="20" y="28" font-family="{FONT}" font-size="16" '
        f'font-weight="bold" fill="{C_TEXT}">{escape(project.name)}</text>',
        f'<text x="20" y="44" font-family="{FONT_MONO}" font-size="9" '
        f'fill="{C_TEXT_DIM}">RackForgePrime — élévation générée depuis le '
        f'JSON du projet</text>',
    ]
    x = 20
    for rack, (w, _h) in zip(racks, sizes):
        parts.append(render_rack(rack, types, offset_x=x, offset_y=52))
        x += w + GAP_X
    parts.append('</svg>')
    return "\n".join(parts)
