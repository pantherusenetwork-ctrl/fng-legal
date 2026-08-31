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

# Palette du dossier (cohérente avec la DA écran).
_BG = (0.043, 0.055, 0.078)      # #0b0e14
_FRAME = (0.16, 0.20, 0.29)      # #2a3446
_TEXT = (0.80, 0.84, 0.88)       # #cbd5e1
_DIM = (0.39, 0.45, 0.55)        # #64748b
_ACCENT = (0.13, 0.83, 0.93)     # #22d3ee
_CARTOUCHE_H = 46
_MARGIN = 18


def render_project_pdf(project: Project, view: str = "physical") -> bytes:
    """Projet -> PDF (bytes). Le SVG est la source, le PDF une vue.

    ``view`` : « physical » (élévation de baies) ou « logical » (VLANs/liens).
    """
    svg = (render_logical_svg(project) if view == "logical"
           else render_project_svg(project))
    drawing = svg2rlg(io.StringIO(svg))
    if drawing is None:  # SVG illisible : bug de génération, pas de l'utilisateur
        raise RuntimeError("Conversion SVG -> PDF impossible (SVG invalide)")

    page_w, page_h = landscape(A4)
    margin = 24
    # Mise à l'échelle uniforme pour tenir dans la page, sans jamais agrandir
    # (l'échelle U reste exacte relative — on ne déforme rien).
    scale = min((page_w - 2 * margin) / drawing.width,
                (page_h - 2 * margin) / drawing.height, 1.0)
    drawing.scale(scale, scale)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(project.name)
    c.setAuthor("RackForgePrime")
    # Fond sombre pleine page : le rendu écran et le PDF sont le même visuel.
    c.setFillColorRGB(*_BG)
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
                section: str, page_no: int, total: int) -> None:
    """Fond sombre, cadre, et cartouche bas-droite d'une page du dossier."""
    c.setFillColorRGB(*_BG)
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    c.setStrokeColorRGB(*_FRAME)
    c.setLineWidth(1.2)
    c.rect(_MARGIN, _MARGIN, page_w - 2 * _MARGIN, page_h - 2 * _MARGIN)
    # Bandeau cartouche sur toute la largeur, en bas du cadre.
    y0 = _MARGIN
    c.rect(_MARGIN, y0, page_w - 2 * _MARGIN, _CARTOUCHE_H)
    cols = [_MARGIN, page_w * 0.42, page_w * 0.62, page_w * 0.78,
            page_w - _MARGIN - 90, page_w - _MARGIN]
    for x in cols[1:-1]:
        c.line(x, y0, x, y0 + _CARTOUCHE_H)

    def cell(x: float, x_next: float, label: str, value: str,
             accent: bool = False) -> None:
        c.setFillColorRGB(*_DIM)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 8, y0 + _CARTOUCHE_H - 13, label.upper())
        c.setFillColorRGB(*(_ACCENT if accent else _TEXT))
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
    scale = min(w / drawing.width, h / drawing.height, 1.0)
    drawing.scale(scale, scale)
    renderPDF.draw(drawing, c, x, y + h - drawing.height * scale)


def _draw_table_page(c, page_w: float, page_h: float, title: str,
                     headers: list[str], col_w: list[float],
                     rows: list[list[str]]) -> None:
    """Une page de tableau (les lignes DOIVENT tenir : paginé par l'appelant)."""
    x, y, w, _h = _content_zone(page_w, page_h)
    top = page_h - _MARGIN - 26
    c.setFillColorRGB(*_ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x, top, title)
    line_h = 15
    ty = top - 24
    scale_w = w / sum(col_w)
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColorRGB(*_ACCENT)
    cx = x
    for head, cw in zip(headers, col_w):
        c.drawString(cx + 3, ty, head)
        cx += cw * scale_w
    c.setStrokeColorRGB(*_FRAME)
    c.line(x, ty - 4, x + w, ty - 4)
    ty -= line_h + 2
    c.setFont("Helvetica", 8.5)
    for row in rows:
        c.setFillColorRGB(*_TEXT)
        cx = x
        for val, cw in zip(row, col_w):
            c.drawString(cx + 3, ty, str(val)[:60])
            cx += cw * scale_w
        c.setStrokeColorRGB(0.10, 0.13, 0.19)
        c.line(x, ty - 4, x + w, ty - 4)
        ty -= line_h


# Lignes de tableau par page A4 paysage (zone utile ~ 480 pt).
_ROWS_PER_PAGE = 26


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


def render_project_dossier_pdf(project: Project) -> bytes:
    """Dossier complet : élévation, vue logique, brassage, nomenclature.

    Chaque page porte le cadre et le cartouche auto-rempli — le livrable
    à joindre tel quel en annexe d'un DAT.
    """
    page_w, page_h = landscape(A4)
    patch_rows = [[r["rack"], f"U{r['u']}", r["equipment"], r["port"],
                   r["outlet"], r["vlan"], r["usage"]]
                  for r in patch_table(project, type_index(project))]
    patch_pages = _paginate(patch_rows)
    bom_pages = _paginate(_bom_rows(project))
    total = 2 + len(patch_pages) + len(bom_pages)

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"{project.name} — dossier")
    c.setAuthor("RackForgePrime")
    page_no = 1

    _page_frame(c, page_w, page_h, project, "Élévation physique", page_no, total)
    _draw_svg_page(c, render_project_svg(project), page_w, page_h)
    c.showPage()
    page_no += 1

    _page_frame(c, page_w, page_h, project, "Architecture logique", page_no, total)
    _draw_svg_page(c, render_logical_svg(project), page_w, page_h)
    c.showPage()
    page_no += 1

    for chunk in patch_pages:
        _page_frame(c, page_w, page_h, project, "Tableau de brassage",
                    page_no, total)
        _draw_table_page(
            c, page_w, page_h, "Tableau de brassage — généré, jamais dessiné",
            ["Baie", "U", "Équipement", "Port", "Prise murale", "VLAN", "Usage"],
            [10, 6, 24, 12, 14, 8, 26], chunk)
        c.showPage()
        page_no += 1

    for chunk in bom_pages:
        _page_frame(c, page_w, page_h, project, "Nomenclature", page_no, total)
        _draw_table_page(
            c, page_w, page_h, "Nomenclature (BOM)",
            ["Constructeur", "Modèle", "Hauteur", "Qté", "U totaux", "Conso totale"],
            [16, 30, 10, 8, 10, 14], chunk)
        c.showPage()
        page_no += 1

    c.save()
    return buf.getvalue()
