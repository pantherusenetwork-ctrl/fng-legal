"""Plan d'étage d'une salle — SVG (écran ET export, un seul moteur).

Le parcours voulu : ville → bâtiment → salle → baies. Ici on dessine
UNE salle : l'image du plan en fond (opacité réglable), les baies posées
dessus à leur emprise réelle (600 × 1000 mm par défaut, via
``Room.mm_per_px``), les liens inter-baies agrégés (un trait, le nombre
de cordons), et les points hors baie (bornes Wi-Fi avec cercle de
couverture, prises, caméras, notes).

Même contrat que les autres moteurs : attributs inline, ``<g id>`` par
objet, thèmes miroir de svg_logical.LPALETTES.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .models import Project, Room
from .svg_logical import FONT, FONT_MONO, LPALETTES

# Emprise standard d'une baie 19" (mm) — largeur × profondeur.
RACK_FOOT_MM = (600.0, 1000.0)
HEADER_H = 44

POINT_STYLE = {
    "ap": ("#22d3ee", "Borne Wi-Fi"),
    "prise": ("#3b82f6", "Prise"),
    "camera": ("#a78bfa", "Caméra"),
    "equipement": ("#34d399", "Équipement"),
    "note": ("#94a3b8", "Note"),
}


def find_room(project: Project, room_id: str | None) -> tuple[Room | None, str]:
    """(salle, fil d'Ariane « Ville › Bâtiment › Salle »)."""
    for site in project.sites:
        for b in site.buildings:
            for room in b.rooms:
                if room_id is None or room.id == room_id:
                    return room, f"{site.name} › {b.name} › {room.name}"
    return None, ""


def rack_footprint_px(room: Room) -> tuple[float, float]:
    return (RACK_FOOT_MM[0] / room.mm_per_px, RACK_FOOT_MM[1] / room.mm_per_px)


def _rack_center(room: Room, pr) -> tuple[float, float]:
    w, d = rack_footprint_px(room)
    if pr.rotation in (90, 270):
        w, d = d, w
    return pr.x + w / 2, pr.y + d / 2


def inter_rack_links(project: Project, room: Room) -> dict[tuple[str, str], int]:
    """Nombre de liens logiques entre chaque paire de baies POSÉES."""
    rack_of = {i.id: r.id for r in project.racks for i in r.items}
    placed = {pr.rack_id for pr in room.racks}
    counts: dict[tuple[str, str], int] = {}
    for link in project.logical.links:
        a = rack_of.get(link.from_.equipment_id)
        b = rack_of.get(link.to.equipment_id)
        if not a or not b or a == b or a not in placed or b not in placed:
            continue
        key = tuple(sorted((a, b)))
        counts[key] = counts.get(key, 0) + 1
    return counts


def render_plan_svg(project: Project, room_id: str | None = None,
                    theme: str = "sombre") -> str:
    p = LPALETTES.get(theme, LPALETTES["sombre"])
    room, crumb = find_room(project, room_id)
    racks = {r.id: r for r in project.racks}
    if room is None:
        w, h = 900, 300
        return "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">',
            f'<rect width="{w}" height="{h}" fill="{p["bg"]}"/>',
            f'<text x="{w / 2}" y="{h / 2 - 8}" text-anchor="middle" font-size="18" '
            f'font-weight="bold" fill="{p["text"]}">Aucune salle sur le plan</text>',
            f'<text x="{w / 2}" y="{h / 2 + 18}" text-anchor="middle" font-size="13" '
            f'fill="{p["dim"]}">Créez une ville, un bâtiment puis une salle, '
            f'et posez-y vos baies.</text>', '</svg>'])
    W, H = room.plan_w, room.plan_h
    total_w, total_h = W + 40, H + HEADER_H + 40
    s: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_w:g}" '
        f'height="{total_h:g}" viewBox="0 0 {total_w:g} {total_h:g}" '
        f'font-family="{FONT}">',
        f'<rect width="{total_w:g}" height="{total_h:g}" fill="{p["bg"]}"/>',
        f'<text x="20" y="26" font-size="16" font-weight="bold" fill="{p["text"]}">'
        f'{escape(project.name)}</text>',
        f'<text x="20" y="42" font-family="{FONT_MONO}" font-size="12" fill="{p["dim"]}">'
        f'Plan — {escape(crumb)} · échelle 1 px = {room.mm_per_px:g} mm</text>',
        f'<g id="plan-{escape(room.id)}" transform="translate(20,{HEADER_H + 20})">',
        f'<rect x="0" y="0" width="{W:g}" height="{H:g}" fill="{p["node"]}" '
        f'stroke="{p["line"]}" stroke-width="1"/>',
    ]
    # Fond : l'image du plan, à l'opacité choisie ; sinon une grille.
    if room.plan_image:
        s.append(f'<image x="0" y="0" width="{W:g}" height="{H:g}" '
                 f'preserveAspectRatio="xMidYMid meet" opacity="{room.plan_opacity:g}" '
                 f'href="{room.plan_image}" xlink:href="{room.plan_image}"/>')
    else:
        step = max(20.0, 1000.0 / room.mm_per_px)   # un carreau = 1 m
        x = step
        while x < W:
            s.append(f'<line x1="{x:g}" y1="0" x2="{x:g}" y2="{H:g}" '
                     f'stroke="{p["line"]}" stroke-width="0.6" stroke-opacity="0.6"/>')
            x += step
        y = step
        while y < H:
            s.append(f'<line x1="0" y1="{y:g}" x2="{W:g}" y2="{y:g}" '
                     f'stroke="{p["line"]}" stroke-width="0.6" stroke-opacity="0.6"/>')
            y += step
        s.append(f'<text x="{W - 8:g}" y="{H - 8:g}" text-anchor="end" font-size="10" '
                 f'font-family="{FONT_MONO}" fill="{p["dim"]}">carreau = 1 m</text>')
    # Couverture Wi-Fi d'abord (sous tout le reste).
    for pt in room.points:
        if pt.kind == "ap" and pt.radius > 0:
            col = pt.color or POINT_STYLE["ap"][0]
            s.append(f'<circle cx="{pt.x:g}" cy="{pt.y:g}" r="{pt.radius:g}" '
                     f'fill="{col}" fill-opacity="0.10" stroke="{col}" '
                     f'stroke-opacity="0.45" stroke-dasharray="6,4"/>')
    # Liens inter-baies agrégés.
    centers = {pr.rack_id: _rack_center(room, pr) for pr in room.racks}
    for (a, b), n in sorted(inter_rack_links(project, room).items()):
        (x1, y1), (x2, y2) = centers[a], centers[b]
        s.append(f'<g id="planlink-{escape(a)}-{escape(b)}">')
        s.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
                 f'stroke="{p["accent"]}" stroke-width="{1.5 + min(n, 8) * 0.4:g}" '
                 f'stroke-opacity="0.85"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        s.append(f'<rect x="{mx - 14:g}" y="{my - 9:g}" width="28" height="18" rx="9" '
                 f'fill="{p["bg"]}" stroke="{p["accent"]}" stroke-width="1"/>')
        s.append(f'<text x="{mx:g}" y="{my + 4:g}" text-anchor="middle" font-size="11" '
                 f'font-family="{FONT_MONO}" fill="{p["accent"]}">{n}</text>')
        s.append('</g>')
    # Liens point ↔ équipement de baie.
    rack_of = {i.id: r.id for r in project.racks for i in r.items}
    for pt in room.points:
        rid = rack_of.get(pt.equipment_id)
        if rid in centers:
            cx, cy = centers[rid]
            col = pt.color or POINT_STYLE.get(pt.kind, POINT_STYLE["note"])[0]
            s.append(f'<line x1="{pt.x:g}" y1="{pt.y:g}" x2="{cx:g}" y2="{cy:g}" '
                     f'stroke="{col}" stroke-width="1.2" stroke-dasharray="4,3" '
                     f'stroke-opacity="0.8"/>')
    # Baies : emprise réelle, nom, rotation.
    fw, fd = rack_footprint_px(room)
    for pr in room.racks:
        rack = racks.get(pr.rack_id)
        if rack is None:
            continue
        cx, cy = _rack_center(room, pr)
        s.append(f'<g id="planrack-{escape(pr.rack_id)}" '
                 f'transform="translate({cx:g},{cy:g}) rotate({pr.rotation})">')
        s.append(f'<rect x="{-fw / 2:g}" y="{-fd / 2:g}" width="{fw:g}" height="{fd:g}" '
                 f'rx="3" fill="{p["accent"]}" fill-opacity="0.18" '
                 f'stroke="{p["accent"]}" stroke-width="1.6"/>')
        # Face avant marquée (trait épais) : on sait de quel côté on ouvre.
        s.append(f'<line x1="{-fw / 2 + 3:g}" y1="{fd / 2 - 3:g}" x2="{fw / 2 - 3:g}" '
                 f'y2="{fd / 2 - 3:g}" stroke="{p["accent"]}" stroke-width="3"/>')
        s.append('</g>')
        # Le nom reste droit, lisible, quelle que soit la rotation — police
        # réduite pour les noms longs (PROMETHEE sur 60 px), jamais tronqué.
        avail = fd if pr.rotation in (90, 270) else fw
        fs = min(12.0, max(7.0, (avail - 6) / max(len(rack.name), 1) * 1.7))
        s.append(f'<text x="{cx:g}" y="{cy + 4:g}" text-anchor="middle" font-size="{fs:.1f}" '
                 f'font-weight="bold" fill="{p["text"]}">{escape(rack.name)}</text>')
        used = sum(1 for _ in rack.items)
        s.append(f'<text x="{cx:g}" y="{cy + 18:g}" text-anchor="middle" font-size="9" '
                 f'font-family="{FONT_MONO}" fill="{p["dim"]}">{used} éq. · {rack.u_height}U</text>')
    # Points.
    for pt in room.points:
        col = pt.color or POINT_STYLE.get(pt.kind, POINT_STYLE["note"])[0]
        s.append(f'<g id="planpoint-{escape(pt.id)}">')
        if pt.kind == "ap":
            s.append(f'<circle cx="{pt.x:g}" cy="{pt.y:g}" r="9" fill="{p["bg"]}" '
                     f'stroke="{col}" stroke-width="2"/>')
            s.append(f'<path d="M {pt.x - 5:g} {pt.y + 1:g} a 7 7 0 0 1 10 0 '
                     f'M {pt.x - 2.5:g} {pt.y + 3:g} a 3.5 3.5 0 0 1 5 0" '
                     f'fill="none" stroke="{col}" stroke-width="1.4"/>')
        elif pt.kind == "prise":
            s.append(f'<rect x="{pt.x - 7:g}" y="{pt.y - 7:g}" width="14" height="14" rx="2" '
                     f'fill="{p["bg"]}" stroke="{col}" stroke-width="2"/>')
        elif pt.kind == "camera":
            s.append(f'<path d="M {pt.x - 8:g} {pt.y - 5:g} h 11 v 10 h -11 z '
                     f'M {pt.x + 3:g} {pt.y - 1:g} l 6 -4 v 10 l -6 -4" '
                     f'fill="{p["bg"]}" stroke="{col}" stroke-width="1.8"/>')
        else:
            s.append(f'<circle cx="{pt.x:g}" cy="{pt.y:g}" r="7" fill="{col}" '
                     f'fill-opacity="0.35" stroke="{col}" stroke-width="1.6"/>')
        if pt.label:
            s.append(f'<text x="{pt.x + 12:g}" y="{pt.y + 4:g}" font-size="11" '
                     f'fill="{p["text"]}">{escape(pt.label)}</text>')
        s.append('</g>')
    s.append('</g>')
    # Légende.
    lx, ly = 20, total_h - 14
    s.append(f'<text x="{lx}" y="{ly}" font-size="10" font-family="{FONT_MONO}" '
             f'fill="{p["dim"]}">Baie = emprise réelle {RACK_FOOT_MM[0]:g}×{RACK_FOOT_MM[1]:g} mm, '
             f'trait épais = face avant · trait orange = cordons inter-baies (nombre) · '
             f'cercle pointillé = couverture Wi-Fi</text>')
    s.append('</svg>')
    return "\n".join(s)
