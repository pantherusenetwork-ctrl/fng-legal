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
                       theme: str = "sombre") -> bytes:
    """Projet -> PDF (bytes). Le SVG est la source, le PDF une vue.

    ``view`` : « physical » (élévation de baies) ou « logical » (VLANs/liens).
    ``theme`` : « sombre » (écran) ou « clair » (impression).
    """
    svg = (render_logical_svg(project, theme=theme) if view == "logical"
           else render_project_svg(project, theme=theme))
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
    # Bloc titre + tableau centré verticalement quand il est court —
    # fini les pages remplies au tiers.
    block = 60 + len(rows) * line_h
    top = min(page_h - _MARGIN - 30, y + (_h + block) / 2)
    c.setFillColorRGB(*pal["accent"])
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x, top, title)
    ty = top - 30
    scale_w = w / sum(col_w)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(*pal["accent"])
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
            c.drawString(cx + 3, ty, str(val)[:60])
            cx += cw * scale_w
        c.setStrokeColorRGB(*pal["row_line"])
        c.line(x, ty - 5, x + w, ty - 5)
        ty -= line_h


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


def render_project_dossier_pdf(project: Project,
                               theme: str = "sombre") -> bytes:
    """Dossier complet : élévation, vue logique, brassage, nomenclature.

    Chaque page porte le cadre et le cartouche auto-rempli — le livrable
    à joindre tel quel en annexe d'un DAT. ``theme="clair"`` pour un
    dossier imprimable en blanc.
    """
    pal = _pdf_palette(theme)
    page_w, page_h = landscape(A4)
    patch_rows = [[r["rack"], f"U{r['u']}", r["equipment"], r["port"],
                   r["outlet"], r["vlan"], r["usage"], r["etat"]]
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
    _draw_svg_page(c, render_project_svg(project, theme=theme), page_w, page_h)
    c.showPage()
    page_no += 1

    _page_frame(c, page_w, page_h, project, "Architecture logique",
                page_no, total, pal)
    _draw_svg_page(c, render_logical_svg(project, theme=theme), page_w, page_h)
    c.showPage()
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
    for k, chunk in enumerate(bom_pages):
        _page_frame(c, page_w, page_h, project, "Nomenclature",
                    page_no, total, pal)
        _draw_table_page(
            c, page_w, page_h, "Nomenclature (BOM)",
            ["Constructeur", "Modèle", "Hauteur", "Qté", "U totaux", "Conso totale"],
            [16, 30, 10, 8, 10, 14], chunk, pal)
        if k == len(bom_pages) - 1:
            # Bilan énergie : la somme que l'exploitant confronte à la
            # capacité de son onduleur.
            c.setFillColorRGB(*pal["accent"])
            c.setFont("Helvetica-Bold", 11)
            c.drawString(_MARGIN + 10, _MARGIN + _CARTOUCHE_H + 12,
                         f"Charge totale estimée : {total_w_charge:g} W "
                         f"(hors budget PoE délivré — à confronter à la "
                         f"capacité de l'onduleur)")
        c.showPage()
        page_no += 1

    c.save()
    return buf.getvalue()
