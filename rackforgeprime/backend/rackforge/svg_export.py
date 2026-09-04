"""Génération SVG des élévations de baies.

Le SVG est le format de rendu pivot : ce que l'écran affiche, ce que
l'export livre, et la source de la conversion PDF. Contraintes :

- échelle exacte : 1U = ``U_PX`` pixels partout, jamais d'à-peu-près ;
- attributs inline uniquement (pas de CSS) pour rester convertible par
  svglib et rééditable dans draw.io / Inkscape ;
- un ``<g id="...">`` nommé par baie et par équipement (réédition facile) ;
- deux thèmes : « sombre » (écran) et « clair » (impression / DAT), mêmes
  géométries, seules les couleurs changent (miroir des THEMES de app.js).
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .models import (EquipmentType, Project, Rack, RackItem, rack_stats,
                     type_index)

# --- Constantes d'échelle (le frontend utilise les mêmes valeurs) -----------
# ÉCHELLE RÉELLE, GRAVÉE AU MM (EIA-310) : la façade 19" fait 482,6 mm,
# 1U fait 44,45 mm. Avec RACK_W = 440 px pour 482,6 mm, l'échelle est
# 0,9117 px/mm et 1U = 40,5 px : le slot a le VRAI ratio d'une baie —
# une image de façade le remplit SANS déformation, un boîtier compact
# (width_mm) s'affiche à sa largeur exacte. Ne jamais revenir à un U
# « esthétique » : c'est ce qui forçait à étirer ou rapetisser les photos.
MM_19_POUCES = 482.6
MM_PER_U = 44.45
U_PX = 40.5         # hauteur d'1U = MM_PER_U × (RACK_W / MM_19_POUCES)
RACK_W = 440        # largeur intérieure 19" utile
RAIL_W = 26         # montant (rail) de chaque côté, graduations comprises
FRAME_PAD = 14      # cadre extérieur de la baie
HEADER_H = 40       # bandeau nom de baie
FOOTER_H = 30       # bandeau stats
GAP_X = 60          # espacement entre baies

# --- Palettes par thème (miroir des THEMES de app.js) -----------------------
PALETTES: dict[str, dict[str, str]] = {
    "sombre": {
        "bg": "#0b0e14", "frame": "#1b2230", "rail": "#2a3446",
        "hole": "#0e1420", "slot": "#0e131d", "slot_line": "#1a2130",
        "text": "#cbd5e1", "dim": "#64748b", "face": "#1a1f2b",
        "accent": "#f97316", "face_stroke": "#2c3547", "pill": "#33405a",
        "port_fill": "#0a0e16", "decor_fill": "#10151f",
        "decor_stroke": "#2c3547", "ring": "#3a465c", "lcd": "#0a2027",
        "band": "#0b0e14",
    },
    "clair": {
        "bg": "#ffffff", "frame": "#ffffff", "rail": "#e2e6ea",
        "hole": "#c6ccd4", "slot": "#f3f4f6", "slot_line": "#e2e5e9",
        "text": "#1c2126", "dim": "#6b7480", "face": "#ffffff",
        "accent": "#ea580c", "face_stroke": "#d3d8de", "pill": "#c9ced4",
        "port_fill": "#ffffff", "decor_fill": "#eef0f3",
        "decor_stroke": "#c9ced4", "ring": "#b8bec7", "lcd": "#fdf3ec",
        "band": "#1c2126",
    },
    "kaki": {
        "bg": "#0c0e06", "frame": "#1c220e", "rail": "#2b3316",
        "hole": "#070903", "slot": "#161b0b", "slot_line": "#262e12",
        "text": "#d4d9b8", "dim": "#8a935f", "face": "#20270f",
        "accent": "#eb9c14", "face_stroke": "#39421c", "pill": "#4a5522",
        "port_fill": "#0e1206", "decor_fill": "#1a200d",
        "decor_stroke": "#39421c", "ring": "#4d5926", "lcd": "#12200e",
        "band": "#0c0e06",
    },
    "nuit": {
        "bg": "#000000", "frame": "#0b0b0e", "rail": "#17171d",
        "hole": "#050507", "slot": "#060608", "slot_line": "#121218",
        "text": "#dde3ec", "dim": "#59637a", "face": "#0d0d11",
        "accent": "#ff7a1a", "face_stroke": "#20202a", "pill": "#2e2e3e",
        "port_fill": "#000000", "decor_fill": "#0a0a0e",
        "decor_stroke": "#20202a", "ring": "#38384c", "lcd": "#141005",
        "band": "#000000",
    },
}


def palette(theme: str) -> dict[str, str]:
    """Palette du thème demandé (repli silencieux sur « sombre »)."""
    return PALETTES.get(theme, PALETTES["sombre"])


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


def _port_banks(n: int, color: str, x: int, y: int, w: int, h: int,
                p: dict[str, str]) -> list[str]:
    """Ports groupés en banques de 6, sur 2 rangées au-delà de 12 — la
    lecture d'un vrai switch (esprit PATCHBOX), pas une frise de carrés."""
    s: list[str] = []
    n = min(n, 48)
    if not n:
        return s
    rows = 2 if n > 12 else 1
    # Boîtier compact : on ne dessine que les ports qui TIENNENT dans sa
    # largeur (jamais de banque qui déborde du châssis).
    pw_, gapx_ = 8, 2
    cols_max = max(1, int((w - 54 + gapx_) / (pw_ + gapx_)) - 1)
    n = min(n, cols_max * rows)
    cols = -(-n // rows)  # ceil
    # Dimensions à l'échelle U_PX=40.5 (48 ports 2 rangées = 256 px,
    # tient pile dans la zone après cartouche).
    pw, gapx, group, ggap = 8, 2, 6, 6
    ph = 10 if rows == 2 else 14
    groups = -(-cols // group)
    total_w = cols * (pw + gapx) - gapx + (groups - 1) * ggap
    x0 = x + w - 46 - total_w
    block_h = rows * ph + (rows - 1) * 4
    y0 = y + (h - block_h) / 2
    for i in range(n):
        r, c = i % rows, i // rows
        px = x0 + c * (pw + gapx) + (c // group) * ggap
        py = y0 + r * (ph + 4)
        s.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw}" height="{ph}" '
                 f'rx="1" fill="{p["port_fill"]}" stroke="{color}" '
                 f'stroke-width="0.8"/>')
        # Languette RJ45 : le détail qui fait « connecteur » et plus « pixel ».
        s.append(f'<rect x="{px + 2:.1f}" y="{py + ph - 2.4:.1f}" width="4" '
                 f'height="2.4" fill="{color}" fill-opacity="0.85"/>')
    return s


def _category_decor(t: EquipmentType, x: int, y: int, w: int, h: int,
                    p: dict[str, str]) -> list[str]:
    """Décor par catégorie pour les types sans ports (serveur, onduleur,
    passe-câbles) : silhouette reconnaissable au premier coup d'œil."""
    s: list[str] = []
    if t.category == "server":
        # Baies disques verticales, LED d'activité en tête.
        bw, gap, count = 17, 4, 10
        x0 = x + w - 46 - count * (bw + gap)
        for i in range(count):
            bx = x0 + i * (bw + gap)
            s.append(f'<rect x="{bx}" y="{y + 4}" width="{bw}" '
                     f'height="{h - 8}" rx="1" fill="{p["decor_fill"]}" '
                     f'stroke="{p["decor_stroke"]}" stroke-width="0.7"/>')
            s.append(f'<circle cx="{bx + bw / 2:.1f}" cy="{y + 7:.1f}" '
                     f'r="1.3" fill="{t.color}"/>')
    elif t.category == "ups":
        # Écran LCD + grille d'aération.
        s.append(f'<rect x="{x + w - 210}" y="{y + h / 2 - 12:.1f}" width="40" '
                 f'height="24" rx="3" fill="{p["lcd"]}" stroke="{t.color}" '
                 f'stroke-width="1"/>')
        for i in range(24):
            vx = x + w - 155 + i * 6
            s.append(f'<rect x="{vx}" y="{y + h / 2 - 10:.1f}" width="3" '
                     f'height="20" rx="1.5" fill="{p["decor_fill"]}"/>')
    elif t.category == "cable-mgmt":
        # Anneaux passe-câbles (à droite du libellé, avant la pastille U).
        for i in range(4):
            rx0 = x + 200 + i * 50
            s.append(f'<rect x="{rx0}" y="{y + 4}" width="30" '
                     f'height="{h - 8}" rx="6" fill="none" '
                     f'stroke="{p["ring"]}" stroke-width="3"/>')
    return s


def _u_pill(t: EquipmentType, x: float, yc: float, w: float,
            p: dict[str, str], align: str = "right") -> list[str]:
    """Pastille de hauteur U — le même badge sur photo et sur dessin.

    ``align="left"`` : vue arrière — tout est en miroir, la pastille
    passe donc du côté opposé pour rester en face du même montant.
    """
    px = x + 8 if align == "left" else x + w - 44
    return [
        f'<rect x="{px:.1f}" y="{yc - 9.5:.1f}" width="36" height="19" '
        f'rx="9" fill="{p["face"]}" fill-opacity="0.85" '
        f'stroke="{p["pill"]}" stroke-width="1"/>',
        f'<text x="{px + 18:.1f}" y="{yc + 4.5:.1f}" text-anchor="middle" '
        f'font-family="{FONT_MONO}" font-size="13" fill="{p["dim"]}">'
        f'{t.u_height}U</text>',
    ]


# Cartouche de nom À CÔTÉ de l'équipement (style Patchdocs) : le texte ne
# se pose jamais sur le matériel.
_LABEL_W = 138


def _name_plate(label: str, x: float, y: float, ih: float,
                color: str, p: dict) -> list[str]:
    # Polices À L'ÉCHELLE du dessin (U_PX=40.5) : lisibles à l'écran ET
    # une fois la page PDF réduite — jamais les tailles de l'ancien U 22.
    txt = label if len(label) <= 15 else label[:14] + "…"
    return [
        f'<rect x="{x + 4}" y="{y + 2}" width="{_LABEL_W - 6}" '
        f'height="{ih - 4}" rx="3" fill="{p["band"]}"/>',
        f'<text x="{x + 12}" y="{y + ih / 2 + 5:.1f}" '
        f'font-family="{FONT}" font-size="15" font-weight="bold" '
        f'fill="#f1f5f9">{escape(txt)}</text>',
    ]


def _faceplate_placeholder(t: EquipmentType, x: int, y: int, w: int,
                           label: str, p: dict[str, str]) -> list[str]:
    """Placeholder fidèle à l'échelle U quand pas d'image officielle.

    Style PATCHBOX / Lucidchart : bloc plat teinté par rôle, libellé net,
    pastille de hauteur U, ports en banques réalistes ou décor de catégorie.
    """
    h = t.u_height * U_PX
    yc = y + h / 2
    s: list[str] = []
    # Corps plat, coins arrondis (léger retrait pour lire la séparation U).
    s.append(f'<rect x="{x}" y="{y + 1}" width="{w}" height="{h - 2}" '
             f'rx="3" fill="{p["face"]}" stroke="{p["face_stroke"]}" '
             f'stroke-width="1"/>')
    # Teinte du rôle sur tout le bloc — l'identité couleur PATCHBOX,
    # lisible à 1 m sans crier.
    s.append(f'<rect x="{x}" y="{y + 1}" width="{w}" height="{h - 2}" '
             f'rx="3" fill="{t.color}" fill-opacity="0.07"/>')
    s.append(f'<rect x="{x}" y="{y + 1}" width="4" height="{h - 2}" '
             f'fill="{t.color}"/>')
    # Oreilles de fixation sur les rails (vis suggérées) — seulement pour
    # un châssis 19" ; un boîtier compact n'a pas d'équerres.
    if w >= RACK_W - 1:
        for ex in (x - RAIL_W + 6, x + w + RAIL_W - 12):
            s.append(f'<circle cx="{ex + 3}" cy="{yc:.1f}" r="2.5" '
                     f'fill="{p["hole"]}"/>')
    # Cartouche de nom À CÔTÉ, décor de l'équipement dans la zone
    # restante : rien d'écrit sur le matériel. Sur un boîtier trop étroit
    # le nom vit au survol (<title>) — jamais un cartouche qui déborde.
    lw = _LABEL_W if (label and w > _LABEL_W + 70) else 0
    if lw:
        s.extend(_name_plate(label, x, y, h, t.color, p))
    if t.category in ("server", "ups", "cable-mgmt") and w - lw > 200:
        s.extend(_category_decor(t, x + lw, y, w - lw, h, p))
    elif t.ports:
        s.extend(_port_banks(len(t.ports), t.color, x + lw, y, w - lw, h, p))
    if w > 60:
        s.extend(_u_pill(t, x, yc, w, p))
    return s



# ---------------------------------------------------------------------------
# Vue arrière — LA MÊME donnée regardée de l'autre côté
# ---------------------------------------------------------------------------
# Le piège Visio, c'est de redessiner une deuxième baie à la main : deux
# dessins qui divergent dès la première modification. Ici la vue arrière
# est DÉRIVÉE du projet, donc toujours juste :
#   - la baie passe en miroir horizontal (ce qui est à gauche de face est
#     à droite de dos) — mais aucun texte n'est retourné, tout est
#     recalculé ;
#   - un équipement monté en façade (``item.face == "front"``) montre son
#     DOS quand on regarde par l'arrière, et inversement ;
#   - les U, eux, ne bougent pas : U1 reste U1 des deux côtés.


def _item_box(t: EquipmentType, item: RackItem, inner_x: float,
              face: str = "front") -> tuple[float, float, bool]:
    """Empreinte réelle de l'équipement dans la façade 19", au mm.

    Renvoie ``(x, largeur, cohabite)`` déjà mis en miroir quand la baie
    est regardée par l'arrière : la donnée (``position_x_mm``) ne bouge
    jamais, seule sa projection à l'écran change.
    """
    iw = RACK_W
    if t.width_mm:
        iw = min(RACK_W, RACK_W * t.width_mm / MM_19_POUCES)
    shared = bool(t.width_mm and item.position_x_mm is not None)
    if shared:
        x_mm = item.position_x_mm
        if face == "rear":
            x_mm = MM_19_POUCES - x_mm - t.width_mm
        ix = inner_x + RACK_W * x_mm / MM_19_POUCES
    else:
        ix = inner_x + (RACK_W - iw) / 2
    return ix, iw, shared


def _rear_faceplate(t: EquipmentType, x: float, y: float, w: float,
                    label: str, p: dict[str, str]) -> list[str]:
    """Dos d'un équipement — dessiné NEUTRE, jamais inventé.

    La sérigraphie arrière réelle des types du catalogue n'est pas connue :
    on ne la fabrique donc pas. Le dos montre ce que TOUT rackable a — une
    grille d'aération et une prise secteur — plus les repères de lecture
    (cartouche de nom, pastille U, liseré de rôle) passés en miroir.
    """
    h = t.u_height * U_PX
    yc = y + h / 2
    lw = _LABEL_W if (label and w > _LABEL_W + 70) else 0
    s: list[str] = [
        f'<rect x="{x:.1f}" y="{y + 1}" width="{w:.1f}" height="{h - 2}" '
        f'rx="3" fill="{p["decor_fill"]}" stroke="{p["face_stroke"]}" '
        f'stroke-width="1"/>',
        f'<rect x="{x:.1f}" y="{y + 1}" width="{w:.1f}" height="{h - 2}" '
        f'rx="3" fill="{t.color}" fill-opacity="0.05"/>',
        # Liseré de rôle à DROITE : le miroir exact de celui de la façade.
        f'<rect x="{x + w - 4:.1f}" y="{y + 1}" width="4" height="{h - 2}" '
        f'fill="{t.color}" fill-opacity="0.5"/>',
    ]
    # Grille d'aération, entre la pastille U (à gauche) et la prise secteur.
    vx0, vx1 = x + 52, x + w - lw - 14
    vx = vx0
    while vx < vx1 - 40:
        # Filet de contour : sans lui, les fentes se confondent avec le
        # corps sur les thèmes sombres (hole ≈ decor_fill).
        s.append(f'<rect x="{vx:.1f}" y="{y + 5:.1f}" width="3" '
                 f'height="{h - 10:.1f}" rx="1.5" fill="{p["hole"]}" '
                 f'stroke="{p["face_stroke"]}" stroke-width="0.5"/>')
        vx += 7
    # Prise secteur IEC : le repère qui dit « c'est bien un dos ».
    if vx1 - vx0 > 40:
        s.append(f'<rect x="{vx1 - 32:.1f}" y="{yc - 7:.1f}" width="24" '
                 f'height="14" rx="2" fill="{p["port_fill"]}" '
                 f'stroke="{p["decor_stroke"]}" stroke-width="1"/>')
        for k in range(3):
            s.append(f'<rect x="{vx1 - 27 + k * 6:.1f}" y="{yc - 3:.1f}" '
                     f'width="2.4" height="6" rx="1" fill="{t.color}" '
                     f'fill-opacity="0.7"/>')
    if lw:
        s.extend(_name_plate(label, x + w - _LABEL_W, y, h, t.color, p))
    if w > 60:
        s.extend(_u_pill(t, x, yc, w, p, align="left"))
    return s


def render_rack(rack: Rack, types: dict[str, EquipmentType],
                offset_x: int = 0, offset_y: int = 0,
                theme: str = "sombre", rendu: str = "photos",
                face: str = "front") -> str:
    """Rend une baie complète dans un <g> nommé.

    ``rendu="dessin"`` ignore les images officielles : toute la baie en
    faceplates dessinées — un seul langage visuel.
    ``face="rear"`` : la même baie vue de derrière (miroir horizontal,
    dos des équipements montés en façade, façade de ceux montés à
    l'arrière).
    """
    p = palette(theme)
    w, h = _rack_size(rack)
    inner_x = FRAME_PAD + RAIL_W
    s: list[str] = [f'<g id="rack-{escape(rack.id)}" '
                    f'transform="translate({offset_x},{offset_y})">']
    # Cadre extérieur.
    s.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="6" '
             f'fill="{p["frame"]}" stroke="{p["face_stroke"]}" '
             f'stroke-width="1.5"/>')
    # Bandeau : nom + localisation.
    s.append(f'<text x="{w / 2:.0f}" y="22" text-anchor="middle" '
             f'font-family="{FONT}" font-size="19" font-weight="bold" '
             f'fill="{p["text"]}">{escape(rack.name)}</text>')
    if rack.location:
        s.append(f'<text x="{w / 2:.0f}" y="{HEADER_H - 2}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="12" fill="{p["dim"]}">'
                 f'{escape(rack.location)}</text>')
    # Badge de face : impossible de confondre les deux vues sur un
    # export imprimé (l'erreur classique du DAT fait à la main).
    if face == "rear":
        s.append(f'<rect x="{w - 104}" y="7" width="96" height="18" rx="9" '
                 f'fill="{p["accent"]}" fill-opacity="0.16" '
                 f'stroke="{p["accent"]}" stroke-width="1"/>')
        s.append(f'<text x="{w - 56}" y="20" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="11" font-weight="bold" '
                 f'fill="{p["accent"]}">VUE ARRIÈRE</text>')
    # Zone U (fond en creux) + rails.
    zone_y = HEADER_H + FRAME_PAD
    zone_h = rack.u_height * U_PX
    s.append(f'<rect x="{inner_x}" y="{zone_y}" width="{RACK_W}" '
             f'height="{zone_h}" fill="{p["slot"]}"/>')
    for rx in (FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W):
        s.append(f'<rect x="{rx}" y="{zone_y}" width="{RAIL_W}" '
                 f'height="{zone_h}" fill="{p["rail"]}"/>')
    # Graduations U : numéro + trous de vissage (3 par U, EIA-310 suggéré).
    for u in range(1, rack.u_height + 1):
        y = _u_to_y(rack, u)
        s.append(f'<line x1="{inner_x}" y1="{y}" x2="{inner_x + RACK_W}" '
                 f'y2="{y}" stroke="{p["slot_line"]}" stroke-width="1"/>')
        for rx in (FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W):
            s.append(f'<text x="{rx + RAIL_W / 2:.0f}" y="{y + U_PX / 2 + 5:.1f}" '
                     f'text-anchor="middle" font-family="{FONT_MONO}" '
                     f'font-size="14" fill="{p["dim"]}">{u}</text>')
            for k in range(3):
                hy = y + 4 + k * ((U_PX - 8) / 2)
                s.append(f'<rect x="{rx + 2}" y="{hy:.1f}" width="3" height="3" '
                         f'rx="1" fill="{p["hole"]}"/>')
    s.append(f'<line x1="{inner_x}" y1="{zone_y + zone_h}" '
             f'x2="{inner_x + RACK_W}" y2="{zone_y + zone_h}" '
             f'stroke="{p["slot_line"]}" stroke-width="1"/>')
    # Équipements — un groupe nommé chacun.
    for item in rack.items:
        t = types.get(item.type_id)
        if t is None:
            continue
        top_u = item.position_u + t.u_height - 1
        y = _u_to_y(rack, top_u if not rack.desc_units else item.position_u)
        # RÈGLE : rien n'est écrit sur le dessin SAUF un hostname saisi
        # PAR L'UTILISATEUR. Jamais de « constructeur modèle » auto-posé.
        label = item.meta.hostname
        ih = t.u_height * U_PX
        # Empreinte au mm, déjà mise en miroir si on regarde par l'arrière.
        ix, iw, shared = _item_box(t, item, inner_x, face)
        bx, bw = (ix, iw) if shared else (inner_x, RACK_W)
        # On voit la FAÇADE d'un équipement quand la face regardée est
        # celle sur laquelle il est monté ; sinon on voit son dos.
        facade = (item.face == face)
        s.append(f'<g id="item-{escape(item.id)}">')
        # Le nom complet vit au SURVOL (tooltip natif du SVG), toujours.
        s.append(f'<title>{escape(label or f"{t.vendor} {t.model}")}'
                 f'{"" if facade else " — vu de dos"}</title>')
        if not facade:
            # Dos : neutre et honnête, jamais de ports arrière inventés.
            s.extend(_rear_faceplate(t, bx, y, bw, label, p))
        elif t.faceplate_svg and rendu != "dessin":
            # SVG officiel : injecté tel quel, cadré à l'échelle U.
            s.append(f'<g transform="translate({inner_x},{y})">'
                     f'{t.faceplate_svg}</g>')
        elif t.faceplate_image and rendu != "dessin":
            # Image officielle aux PROPORTIONS RESPECTÉES : en mode
            # photos, AUCUN cartouche — le nom vit dans le <title> au
            # survol. Un boîtier compact (width_mm renseigné) occupe SA
            # largeur réelle, à l'échelle des 19 pouces (483 mm),
            # centré — comme posé dans la vraie baie.
            # Le slot est à l'ÉCHELLE RÉELLE : jamais d'étirement
            # (« meet » toujours). Une façade 19" le remplit d'elle-même ;
            # un boîtier compact (width_mm) est cadré à SA largeur, au mm.
            s.append(f'<rect x="{bx:.1f}" y="{y + 1}" width="{bw:.1f}" '
                     f'height="{ih - 2}" fill="{p["face"]}"/>')
            s.append(f'<image x="{ix:.1f}" y="{y + 1}" '
                     f'width="{iw:.1f}" height="{ih - 2}" '
                     f'preserveAspectRatio="xMidYMid meet" '
                     f'href="{t.faceplate_image}" '
                     f'xlink:href="{t.faceplate_image}"/>')
            s.append(f'<rect x="{bx:.1f}" y="{y + 1}" width="{bw:.1f}" '
                     f'height="{ih - 2}" rx="2" fill="none" '
                     f'stroke="{p["face_stroke"]}" stroke-width="1"/>')
            s.append(f'<rect x="{bx:.1f}" y="{y + 1}" width="4" '
                     f'height="{ih - 2}" fill="{t.color}"/>')
            if not shared:
                s.extend(_u_pill(t, inner_x, y + ih / 2, RACK_W, p))
        elif t.width_mm:
            # Dessin d'un boîtier compact : à SA largeur réelle, comme la
            # photo — l'échelle ne dépend pas du rendu choisi.
            s.append(f'<rect x="{bx:.1f}" y="{y + 1}" width="{bw:.1f}" '
                     f'height="{ih - 2}" fill="{p["face"]}" fill-opacity="0.35"/>')
            s.extend(_faceplate_placeholder(t, ix, y, iw, label, p))
        else:
            s.extend(_faceplate_placeholder(t, inner_x, y, RACK_W, label, p))
        s.append('</g>')
    # Pied : stats de la baie (esprit TSS — stats live aussi à l'export).
    st = rack_stats(rack, types)
    s.append(f'<text x="{w / 2:.0f}" y="{h - FOOTER_H / 2:.0f}" '
             f'text-anchor="middle" font-family="{FONT_MONO}" font-size="14" '
             f'fill="{p["accent"]}">{st["u_used"]}U occupés · '
             f'{st["u_free"]}U libres · {st["power_w"]:g} W</text>')
    s.append('</g>')
    return "\n".join(s)


def render_project_svg(project: Project, theme: str = "sombre",
                       rendu: str = "photos", face: str = "front") -> str:
    """SVG complet : toutes les baies du projet côte à côte.

    ``face="rear"`` rend la vue arrière — dérivée du même JSON, jamais
    un second dessin à maintenir.
    """
    p = palette(theme)
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
        f'<rect x="0" y="0" width="{total_w}" height="{total_h}" fill="{p["bg"]}"/>',
        f'<text x="20" y="28" font-family="{FONT}" font-size="16" '
        f'font-weight="bold" fill="{p["text"]}">{escape(project.name)}</text>',
        f'<text x="20" y="46" font-family="{FONT_MONO}" font-size="12" '
        f'fill="{p["dim"]}">RackForgePrime — élévation '
        f'{"arrière" if face == "rear" else "avant"} générée depuis le '
        f'JSON du projet</text>',
    ]
    x = 20
    for rack, (w, _h) in zip(racks, sizes):
        parts.append(render_rack(rack, types, offset_x=x, offset_y=52,
                                 theme=theme, rendu=rendu, face=face))
        x += w + GAP_X
    parts.append('</svg>')
    return "\n".join(parts)
