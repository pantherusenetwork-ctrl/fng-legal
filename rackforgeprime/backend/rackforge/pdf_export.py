"""Export PDF — conversion locale du SVG pivot.

Le PDF n'est jamais un troisième dessin : c'est le SVG du projet converti
par svglib + reportlab (100 % Python, aucun binaire système, aucun cloud).
Une page A4 paysage par défaut, le dessin mis à l'échelle pour tenir dedans.
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from svglib.svglib import svg2rlg

from .models import Project, patch_table, type_index
from .svg_export import render_project_svg
from .svg_logical import render_logical_svg

# Palettes du dossier par thème (sombre = écran, clair = impression DAT).
_PDF_PALETTES = {
    "sombre": {
        "bg": (0.043, 0.055, 0.078),   # #0b0e14
        "frame": (0.16, 0.20, 0.29),   # #2a3446
        "text": (0.80, 0.84, 0.88),    # #cbd5e1
        "dim": (0.39, 0.45, 0.55),     # #64748b
        "accent": (0.976, 0.451, 0.086),  # #f97316
        "row_line": (0.10, 0.13, 0.19),
    },
    "clair": {
        "bg": (1.0, 1.0, 1.0),
        "frame": (0.79, 0.81, 0.83),   # #c9ced4
        "text": (0.11, 0.13, 0.15),    # #1c2126
        "dim": (0.42, 0.46, 0.50),     # #6b7480
        "accent": (0.918, 0.345, 0.047),  # #ea580c
        "row_line": (0.91, 0.92, 0.93),
    },
}
_CARTOUCHE_H = 46
_MARGIN = 18


def _pdf_palette(theme: str) -> dict:
    return _PDF_PALETTES.get(theme, _PDF_PALETTES["sombre"])


def render_project_pdf(project: Project, view: str = "physical",
                       theme: str = "sombre",
                       rendu: str = "photos") -> bytes:
    """Projet -> PDF (bytes). Le SVG est la source, le PDF une vue.

    ``view`` : « physical » (élévation de baies) ou « logical » (VLANs/liens).
    ``theme`` : « sombre » (écran) ou « clair » (impression).
    """
    svg = (render_logical_svg(project, theme=theme) if view == "logical"
           else render_project_svg(project, theme=theme, rendu=rendu))
    drawing = svg2rlg(io.StringIO(svg))
    if drawing is None:  # SVG illisible : bug de génération, pas de l'utilisateur
        raise RuntimeError("Conversion SVG -> PDF impossible (SVG invalide)")

    page_w, page_h = landscape(A4)
    margin = 24
    # Mise à l'échelle uniforme pour REMPLIR la page (agrandissement borné :
    # l'échelle U reste exacte relative — on ne déforme rien).
    scale = min((page_w - 2 * margin) / drawing.width,
                (page_h - 2 * margin) / drawing.height, 1.75)
    drawing.scale(scale, scale)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(project.name)
    c.setAuthor("RackForgePrime")
    # Fond pleine page dans le thème demandé.
    c.setFillColorRGB(*_pdf_palette(theme)["bg"])
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    renderPDF.draw(drawing, c, margin,
                   page_h - margin - drawing.height * scale)
    c.showPage()
    c.save()
    return buf.getvalue()


# --- Dossier DAT : cadre + cartouche + pagination multi-vues ----------------
#
# L'enseignement Visio (docs/RECHERCHE_VISUELLE.md, analyse v2) : ce qui fait
# « document d'ingénierie », c'est le cadre, le cartouche auto-rempli depuis
# les métadonnées, et la pagination élévation + logique + tableaux dans un
# seul PDF. Aucun champ n'est saisi deux fois : tout vient du JSON du projet.

def _page_frame(c, page_w: float, page_h: float, project: Project,
                section: str, page_no: int, total: int,
                pal: dict) -> None:
    """Fond, cadre, et cartouche bas d'une page du dossier."""
    c.setFillColorRGB(*pal["bg"])
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    c.setStrokeColorRGB(*pal["frame"])
    c.setLineWidth(1.2)
    c.rect(_MARGIN, _MARGIN, page_w - 2 * _MARGIN, page_h - 2 * _MARGIN)
    # Bandeau cartouche sur toute la largeur, en bas du cadre.
    y0 = _MARGIN
    c.rect(_MARGIN, y0, page_w - 2 * _MARGIN, _CARTOUCHE_H)
    cols = [_MARGIN, page_w * 0.38, page_w * 0.56, page_w * 0.68,
            page_w - _MARGIN - 76, page_w - _MARGIN]
    for x in cols[1:-1]:
        c.line(x, y0, x, y0 + _CARTOUCHE_H)

    def cell(x: float, x_next: float, label: str, value: str,
             accent: bool = False) -> None:
        c.setFillColorRGB(*pal["dim"])
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 8, y0 + _CARTOUCHE_H - 13, label.upper())
        c.setFillColorRGB(*(pal["accent"] if accent else pal["text"]))
        c.setFont("Helvetica-Bold", 10)
        # Tronqué à la largeur réelle de la case (jamais de débordement).
        max_w = x_next - x - 16
        while value and c.stringWidth(value, "Helvetica-Bold", 10) > max_w:
            value = value[:-2] + "…" if len(value) > 2 else ""
        c.drawString(x + 8, y0 + 10, value)

    labels = [("Projet", project.name, True), ("Section", section, False),
              ("Généré le", date.today().strftime("%d/%m/%Y"), False),
              ("Source", f"{project.id}.json", False),
              ("Page", f"{page_no} / {total}", False)]
    for (label, value, accent), x, x_next in zip(labels, cols, cols[1:]):
        cell(x, x_next, label, value, accent)


def _content_zone(page_w: float, page_h: float) -> tuple[float, float, float, float]:
    """(x, y, largeur, hauteur) utiles au-dessus du cartouche."""
    pad = 10
    x = _MARGIN + pad
    y = _MARGIN + _CARTOUCHE_H + pad
    return (x, y, page_w - 2 * (_MARGIN + pad),
            page_h - _MARGIN - pad - y)


def _draw_svg_page(c, svg: str, page_w: float, page_h: float) -> None:
    drawing = svg2rlg(io.StringIO(svg))
    if drawing is None:
        raise RuntimeError("Conversion SVG -> PDF impossible (SVG invalide)")
    x, y, w, h = _content_zone(page_w, page_h)
    # Le dessin REMPLIT la page (agrandi si besoin, borné pour ne pas
    # pixelliser les textes) et est centré — plus de page aux 2/3 vide.
    scale = min(w / drawing.width, h / drawing.height, 1.75)
    dw, dh = drawing.width * scale, drawing.height * scale
    drawing.scale(scale, scale)
    renderPDF.draw(drawing, c, x + (w - dw) / 2, y + (h - dh) / 2)


def _draw_table_page(c, page_w: float, page_h: float, title: str,
                     headers: list[str], col_w: list[float],
                     rows: list[list[str]], pal: dict) -> None:
    """Une page de tableau (les lignes DOIVENT tenir : paginé par l'appelant)."""
    x, y, w, _h = _content_zone(page_w, page_h)
    line_h = 18
    # Aligné en haut de page, comme une page de rapport — le lecteur
    # attaque le tableau sans chercher.
    top = page_h - _MARGIN - 30
    c.setFillColorRGB(*pal["accent"])
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x, top, title)
    ty = top - 30
    scale_w = w / sum(col_w)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(*pal["text"])
    cx = x
    for head, cw in zip(headers, col_w):
        c.drawString(cx + 3, ty, head)
        cx += cw * scale_w
    c.setStrokeColorRGB(*pal["frame"])
    c.line(x, ty - 5, x + w, ty - 5)
    ty -= line_h + 3
    c.setFont("Helvetica", 10)
    for row in rows:
        c.setFillColorRGB(*pal["text"])
        cx = x
        for val, cw in zip(row, col_w):
            # Tronqué à la largeur réelle de la colonne : une colonne
            # générée n'entre jamais en collision avec la suivante.
            txt = str(val)
            max_w = cw * scale_w - 8
            while txt and c.stringWidth(txt, "Helvetica", 10) > max_w:
                txt = txt[:-2] + "…" if len(txt) > 2 else ""
            c.drawString(cx + 3, ty, txt)
            cx += cw * scale_w
        c.setStrokeColorRGB(*pal["row_line"])
        c.line(x, ty - 5, x + w, ty - 5)
        ty -= line_h
    return ty


# Lignes de tableau par page A4 paysage (corps 10 pt, interligne 18 pt).
_ROWS_PER_PAGE = 22


def _paginate(rows: list, per_page: int = _ROWS_PER_PAGE) -> list[list]:
    return [rows[i:i + per_page] for i in range(0, len(rows), per_page)] or [[]]


def _bom_rows(project: Project) -> list[list[str]]:
    """Nomenclature : quantités agrégées par type réellement posé en baie."""
    types = type_index(project)
    counts: dict[str, int] = {}
    for rack in project.racks:
        for item in rack.items:
            counts[item.type_id] = counts.get(item.type_id, 0) + 1
    rows = []
    for type_id, qty in sorted(counts.items()):
        t = types.get(type_id)
        if t is None:
            rows.append([type_id, "?", "?", str(qty), "?", "?"])
            continue
        rows.append([t.vendor, t.model, f"{t.u_height}U", str(qty),
                     f"{t.u_height * qty}U", f"{t.power_w * qty:g} W"])
    return rows


# --- Planche d'étiquettes (TIA-606 : identifiants générés de la donnée) -----

# Abréviations d'interfaces (convention IOS) : l'identifiant reste court
# ET discriminant — Gi0-0-0 et Gi0-0-1 ne se confondent jamais.
_PORT_ABBREV = [("TenGigabitEthernet", "Te"), ("GigabitEthernet", "Gi"),
                ("FastEthernet", "Fa"), ("Ethernet", "Eth"), ("Port ", "P")]


def _abbrev_port(port: str) -> str:
    """Abréviation IOS d'un nom de port (Gi0/0/0 reste discriminant là
    où « GigabitEtherne… » tronqué ne l'est pas)."""
    for long, court in _PORT_ABBREV:
        if port.startswith(long):
            return court + port[len(long):]
    return port


def _label_id(rack_name: str, u: int, port: str) -> str:
    """Identifiant d'étiquette : BAIE-Uxx-PORT, généré — jamais retapé."""
    rack = "".join(ch if ch.isalnum() else "-" for ch in rack_name.upper())
    while "--" in rack:
        rack = rack.replace("--", "-")
    for long, court in _PORT_ABBREV:
        if port.startswith(long):
            port = court + port[len(long):]
            break
    port_c = "".join(ch if ch.isalnum() else "-" for ch in port)
    return f"{rack.strip('-')}-U{u}-{port_c}"


def render_labels_pdf(project: Project) -> bytes:
    """Planche d'étiquettes A4 portrait à découper, une par ligne de
    brassage renseignée. Toujours en clair : c'est fait pour l'imprimante.
    """
    from reportlab.lib.pagesizes import A4 as _A4
    pal = _pdf_palette("clair")
    page_w, page_h = _A4
    rows = [r for r in patch_table(project, type_index(project))
            if r["port"] and r["port"] != "—"]

    # Grille : 3 colonnes × 12 lignes d'étiquettes ~64×22 mm.
    cols_n, rows_n = 3, 12
    margin = 24
    lw = (page_w - 2 * margin) / cols_n
    lh = (page_h - 2 * margin - 30) / rows_n
    per_page = cols_n * rows_n

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=_A4)
    c.setTitle(f"{project.name} — étiquettes")
    for page_start in range(0, max(len(rows), 1), per_page):
        c.setFillColorRGB(*pal["text"])
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, page_h - margin, f"{project.name} — étiquettes de brassage")
        c.setFillColorRGB(*pal["dim"])
        c.setFont("Helvetica", 7.5)
        c.drawString(margin, page_h - margin - 11,
                     "Schéma d'identification : BAIE-Uxx-PORT — généré depuis "
                     "le projet (TIA-606 : ne jamais retaper un identifiant).")
        for idx, r in enumerate(rows[page_start:page_start + per_page]):
            cx = margin + (idx % cols_n) * lw
            cy = page_h - margin - 30 - ((idx // cols_n) + 1) * lh
            # Cadre de découpe en pointillés.
            c.setStrokeColorRGB(*pal["frame"])
            c.setDash(2, 2)
            c.rect(cx + 2, cy + 2, lw - 4, lh - 4)
            c.setDash()
            c.setFillColorRGB(*pal["text"])
            c.setFont("Courier-Bold", 10)
            c.drawString(cx + 8, cy + lh - 16,
                         _label_id(r["rack"], r["u"], r["port"])[:30])
            c.setFillColorRGB(*pal["accent"])
            c.setFont("Helvetica-Bold", 8)
            c.drawString(cx + 8, cy + lh - 28, str(r["equipment"])[:34])
            c.setFillColorRGB(*pal["dim"])
            c.setFont("Helvetica", 7.5)
            details = " · ".join(x for x in (
                f"prise {r['outlet']}" if r["outlet"] else "",
                f"VLAN {r['vlan']}" if r["vlan"] else "",
                str(r["usage"] or "")) if x)
            # Deux lignes plutôt qu'un texte coupé : une étiquette
            # imprimée doit se lire en entier.
            if len(details) <= 44:
                c.drawString(cx + 8, cy + lh - 39, details)
            else:
                coupe = details.rfind(" ", 0, 44)
                coupe = coupe if coupe > 20 else 44
                c.drawString(cx + 8, cy + lh - 39, details[:coupe])
                c.drawString(cx + 8, cy + lh - 48, details[coupe:].strip()[:44])
        c.showPage()
    c.save()
    return buf.getvalue()


def render_project_dossier_pdf(project: Project, theme: str = "sombre",
                               rendu: str = "photos") -> bytes:
    """Dossier complet : élévation, vue logique, brassage, nomenclature.

    Chaque page porte le cadre et le cartouche auto-rempli — le livrable
    à joindre tel quel en annexe d'un DAT. ``theme="clair"`` pour un
    dossier imprimable en blanc.
    """
    pal = _pdf_palette(theme)
    page_w, page_h = landscape(A4)
    patch_rows = [[r["rack"], f"U{r['u']}", r["equipment"],
                   _abbrev_port(r["port"]), r["outlet"], r["vlan"],
                   r["usage"], r["etat"]]
                  for r in patch_table(project, type_index(project))]
    patch_pages = _paginate(patch_rows)
    bom_pages = _paginate(_bom_rows(project))
    total = 2 + len(patch_pages) + len(bom_pages)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"{project.name} — dossier")
    c.setAuthor("RackForgePrime")
    page_no = 1

    _page_frame(c, page_w, page_h, project, "Élévation physique",
                page_no, total, pal)
    _draw_svg_page(c, render_project_svg(project, theme=theme, rendu=rendu),
                   page_w, page_h)
    c.showPage()
    page_no += 1

    # Page logique en PORTRAIT (pratique DAT : l'orientation suit le
    # dessin) — un schéma en colonne remplit une page verticale.
    c.setPageSize(A4)
    _page_frame(c, page_h, page_w, project, "Architecture logique",
                page_no, total, pal)
    _draw_svg_page(c, render_logical_svg(project, theme=theme),
                   page_h, page_w)
    c.showPage()
    c.setPageSize(landscape(A4))
    page_no += 1

    for chunk in patch_pages:
        _page_frame(c, page_w, page_h, project, "Tableau de brassage",
                    page_no, total, pal)
        _draw_table_page(
            c, page_w, page_h, "Tableau de brassage — généré, jamais dessiné",
            ["Baie", "U", "Équipement", "Port", "Prise murale", "VLAN",
             "Usage", "État"],
            [10, 6, 22, 11, 13, 8, 20, 9], chunk, pal)
        c.showPage()
        page_no += 1

    types = type_index(project)
    total_w_charge = sum(
        types[i.type_id].power_w
        for r in project.racks for i in r.items if i.type_id in types)
    # Capacité onduleur : valeurs constructeur pour les gammes connues
    # (APC : 1500 VA -> 1000 W réels), sinon VA du modèle × 0,66 marqué
    # comme estimation — jamais présentée comme mesurée.
    import re as _re
    _UPS_W = {"1500": 1000, "2200": 1980, "3000": 2700}
    ups_w, ups_estime = 0.0, False
    for r in project.racks:
        for i in r.items:
            t = types.get(i.type_id)
            if not t or t.category != "ups":
                continue
            m = _re.search(r"(\d{3,5})", t.model)
            if not m:
                continue
            va = m.group(1)
            if va in _UPS_W:
                ups_w += _UPS_W[va]
            else:
                ups_w += int(va) * 0.66
                ups_estime = True
    for k, chunk in enumerate(bom_pages):
        _page_frame(c, page_w, page_h, project, "Nomenclature",
                    page_no, total, pal)
        end_y = _draw_table_page(
            c, page_w, page_h, "Nomenclature (BOM)",
            ["Constructeur", "Modèle", "Hauteur", "Qté", "U totaux", "Conso totale"],
            [16, 30, 10, 8, 10, 14], chunk, pal)
        if k == len(bom_pages) - 1:
            # Bilan énergie sous le tableau (pas collé au pied de page) :
            # charge vs capacité onduleur.
            if ups_w:
                taux = 100 * total_w_charge / ups_w
                src = ("estimée du modèle" if ups_estime
                       else "valeur constructeur")
                bilan = (f"Charge totale estimée : {total_w_charge:g} W · "
                         f"capacité onduleur {ups_w:g} W ({src}) → "
                         f"taux de charge ≈ {taux:.0f} %")
            else:
                bilan = (f"Charge totale estimée : {total_w_charge:g} W "
                         f"(hors budget PoE délivré — aucun onduleur en baie)")
            c.setFillColorRGB(*pal["accent"])
            c.setFont("Helvetica-Bold", 11)
            c.drawString(_MARGIN + 22, end_y - 14, bilan)
        c.showPage()
        page_no += 1

    c.save()
    return buf.getvalue()
