"""Export PDF — conversion locale du SVG pivot.

Le PDF n'est jamais un troisième dessin : c'est le SVG du projet converti
par svglib + reportlab (100 % Python, aucun binaire système, aucun cloud).
Une page A4 paysage par défaut, le dessin mis à l'échelle pour tenir dedans.
"""

from __future__ import annotations

import io

from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from svglib.svglib import svg2rlg

from .models import Project
from .svg_export import render_project_svg
from .svg_logical import render_logical_svg


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
    c.setFillColorRGB(0.043, 0.055, 0.078)  # #0b0e14
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    renderPDF.draw(drawing, c, margin,
                   page_h - margin - drawing.height * scale)
    c.showPage()
    c.save()
    return buf.getvalue()
