"""Export Visio (.vsdx) — le format d'échange entreprise.

Un .vsdx est un paquet OPC (zip) de XML « Visio 2012 main ». On l'écrit
directement, sans Visio ni bibliothèque tierce : 100 % local, comme le
reste. Deux pages, comme l'export draw.io :

- « Élévation » : les baies à l'échelle U (mêmes constantes que
  svg_export), un rectangle nommé par équipement, déplaçable ;
- « Logique » : les mêmes nœuds/positions que svg_logical, liens tracés.

Unités Visio = pouces, origine en BAS à gauche (l'axe Y monte). On
convertit depuis les pixels du dessin (96 px = 1 pouce) et on renverse Y.

Limite honnête : le paquet est construit d'après la spécification
publique (MS-VSDX) et validé structurellement par les tests ; il n'a pas
été ouvert dans un Visio réel sur ce poste (Visio n'y est pas installé).
"""

from __future__ import annotations

import io
import math
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape, quoteattr

from .models import EquipmentType, Project, type_index
from .svg_export import (FOOTER_H, FRAME_PAD, HEADER_H, RACK_W, RAIL_W,
                         U_PX, _rack_size, _u_to_y)
from .svg_logical import (LAYER_RANK, NODE_H, NODE_W, ZONE_LABELS,
                          layout_nodes)

PX_PER_IN = 96.0
GAP_X = 80          # espacement entre baies (px)
_MARGIN_IN = 0.4    # marge de page (pouces)

_NS_MAIN = "http://schemas.microsoft.com/office/visio/2012/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Couleurs (thème clair : un document de travail, comme draw.io).
_FRAME_FILL = "#f4f5f6"
_FRAME_STROKE = "#9aa2ad"
_SLOT_FILL = "#ececef"
_TEXT = "#1c2126"

_EDGE_STYLE = {
    # kind -> (couleur, pointillés (LinePattern Visio), épaisseur en pt)
    "trunk": ("#0e7490", 1, 2.25),
    "uplink": ("#15803d", 1, 1.5),
    "access": ("#64748b", 1, 0.75),
    "ha": ("#dc2626", 2, 1.5),
    "other": ("#94a3b8", 2, 0.75),
}


def _px(v: float) -> float:
    return v / PX_PER_IN


def _tint(color: str) -> str:
    """Teinte claire d'une couleur de rôle (fond de forme lisible)."""
    try:
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        mix = tuple(int(c + (255 - c) * 0.85) for c in (r, g, b))
        return "#{:02x}{:02x}{:02x}".format(*mix)
    except (ValueError, IndexError):
        return "#f5f5f5"


class _Page:
    """Accumule les formes d'une page ; convertit px (Y vers le bas) en
    pouces Visio (Y vers le haut) au moment d'écrire."""

    def __init__(self, name: str, width_px: float, height_px: float):
        self.name = name
        self.w_in = _px(width_px) + 2 * _MARGIN_IN
        self.h_in = _px(height_px) + 2 * _MARGIN_IN
        self.shapes: list[str] = []
        self._next_id = 1

    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def _pin(self, x_px: float, y_px: float, w_px: float, h_px: float
             ) -> tuple[float, float, float, float]:
        """(PinX, PinY, Width, Height) en pouces — centre de la forme."""
        w, h = _px(w_px), _px(h_px)
        px = _MARGIN_IN + _px(x_px) + w / 2
        py = self.h_in - _MARGIN_IN - _px(y_px) - h / 2
        return px, py, w, h

    def rect(self, name: str, x: float, y: float, w: float, h: float,
             text: str = "", fill: str = "#ffffff", stroke: str = "#333333",
             line_w_pt: float = 0.75, font_pt: float = 9,
             bold: bool = False, halign: int = 1, valign: int = 1,
             color: str = _TEXT, no_fill: bool = False,
             dashed: bool = False) -> int:
        sid = self._id()
        px, py, wi, hi = self._pin(x, y, w, h)
        cells = [
            ("PinX", px), ("PinY", py), ("Width", wi), ("Height", hi),
            ("LocPinX", wi / 2), ("LocPinY", hi / 2),
            ("Angle", 0), ("FlipX", 0), ("FlipY", 0), ("ResizeMode", 0),
            ("LineWeight", line_w_pt / 72),
            ("LinePattern", 2 if dashed else 1),
            ("FillPattern", 0 if no_fill else 1),
            ("VerticalAlign", valign),
        ]
        s = [f'<Shape ID="{sid}" NameU={quoteattr(name)} Name={quoteattr(name)} '
             f'Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">']
        for n, v in cells:
            s.append(f'<Cell N="{n}" V="{_fmt(v)}"/>')
        s.append(f'<Cell N="LineColor" V="{stroke}"/>')
        s.append(f'<Cell N="FillForegnd" V="{fill}"/>')
        s.append(f'<Cell N="FillBkgnd" V="{fill}"/>')
        # Caractère (police) et paragraphe (alignement horizontal).
        s.append('<Section N="Character"><Row IX="0">'
                 f'<Cell N="Font" V="Calibri"/><Cell N="Color" V="{color}"/>'
                 f'<Cell N="Style" V="{1 if bold else 0}"/>'
                 f'<Cell N="Size" V="{_fmt(font_pt / 72)}"/></Row></Section>')
        s.append('<Section N="Paragraph"><Row IX="0">'
                 f'<Cell N="HorzAlign" V="{halign}"/></Row></Section>')
        s.append(_rect_geometry(wi, hi, no_fill))
        if text:
            s.append(f'<Text><cp IX="0"/><pp IX="0"/>{escape(text)}</Text>')
        s.append('</Shape>')
        self.shapes.append("".join(s))
        return sid

    def line(self, name: str, x1: float, y1: float, x2: float, y2: float,
             color: str = "#333333", line_w_pt: float = 0.75,
             pattern: int = 1, text: str = "") -> int:
        """Segment de (x1,y1) à (x2,y2) en px : forme 1D Visio (Begin/End)."""
        sid = self._id()
        bx = _MARGIN_IN + _px(x1)
        by = self.h_in - _MARGIN_IN - _px(y1)
        ex = _MARGIN_IN + _px(x2)
        ey = self.h_in - _MARGIN_IN - _px(y2)
        length = math.hypot(ex - bx, ey - by)
        angle = math.atan2(ey - by, ex - bx)
        s = [f'<Shape ID="{sid}" NameU={quoteattr(name)} Name={quoteattr(name)} '
             f'Type="Shape" LineStyle="0" FillStyle="0" TextStyle="0">',
             f'<Cell N="BeginX" V="{_fmt(bx)}"/><Cell N="BeginY" V="{_fmt(by)}"/>',
             f'<Cell N="EndX" V="{_fmt(ex)}"/><Cell N="EndY" V="{_fmt(ey)}"/>',
             f'<Cell N="PinX" V="{_fmt((bx + ex) / 2)}"/>',
             f'<Cell N="PinY" V="{_fmt((by + ey) / 2)}"/>',
             f'<Cell N="Width" V="{_fmt(length)}"/><Cell N="Height" V="0"/>',
             f'<Cell N="LocPinX" V="{_fmt(length / 2)}"/><Cell N="LocPinY" V="0"/>',
             f'<Cell N="Angle" V="{_fmt(angle)}"/>',
             '<Cell N="FlipX" V="0"/><Cell N="FlipY" V="0"/>',
             '<Cell N="ObjType" V="1"/>',
             f'<Cell N="LineWeight" V="{_fmt(line_w_pt / 72)}"/>',
             f'<Cell N="LinePattern" V="{pattern}"/>',
             f'<Cell N="LineColor" V="{color}"/><Cell N="FillPattern" V="0"/>',
             '<Section N="Character"><Row IX="0"><Cell N="Font" V="Calibri"/>'
             f'<Cell N="Color" V="{color}"/><Cell N="Size" V="{_fmt(7 / 72)}"/>'
             '</Row></Section>',
             '<Section N="Geometry" IX="0"><Cell N="NoFill" V="1"/>'
             '<Cell N="NoLine" V="0"/>',
             '<Row T="MoveTo" IX="1"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>',
             f'<Row T="LineTo" IX="2"><Cell N="X" V="{_fmt(length)}" F="Width"/>'
             '<Cell N="Y" V="0"/></Row></Section>']
        if text:
            s.append(f'<Text>{escape(text)}</Text>')
        s.append('</Shape>')
        self.shapes.append("".join(s))
        return sid

    def xml(self) -> str:
        return (f'<?xml version="1.0" encoding="utf-8"?>'
                f'<PageContents xmlns="{_NS_MAIN}" xmlns:r="{_NS_R}" '
                f'xml:space="preserve"><Shapes>{"".join(self.shapes)}'
                f'</Shapes></PageContents>')


def _fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def _rect_geometry(w: float, h: float, no_fill: bool) -> str:
    return ('<Section N="Geometry" IX="0">'
            f'<Cell N="NoFill" V="{1 if no_fill else 0}"/><Cell N="NoLine" V="0"/>'
            '<Row T="MoveTo" IX="1"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>'
            f'<Row T="LineTo" IX="2"><Cell N="X" V="{_fmt(w)}" F="Width"/>'
            '<Cell N="Y" V="0"/></Row>'
            f'<Row T="LineTo" IX="3"><Cell N="X" V="{_fmt(w)}" F="Width"/>'
            f'<Cell N="Y" V="{_fmt(h)}" F="Height"/></Row>'
            f'<Row T="LineTo" IX="4"><Cell N="X" V="0"/>'
            f'<Cell N="Y" V="{_fmt(h)}" F="Height"/></Row>'
            '<Row T="LineTo" IX="5"><Cell N="X" V="0"/><Cell N="Y" V="0"/></Row>'
            '</Section>')


# --- Page Élévation ---------------------------------------------------------

def _physical_page(project: Project, types: dict[str, EquipmentType]) -> _Page:
    racks = project.racks
    sizes = [_rack_size(r) for r in racks]
    total_w = sum(w for w, _ in sizes) + GAP_X * max(len(racks) - 1, 0) + 40
    total_h = max((h for _, h in sizes), default=200) + 60
    page = _Page("Élévation", total_w, total_h)
    x_off = 20.0
    for rack, (w, h) in zip(racks, sizes):
        inner_x = x_off + FRAME_PAD + RAIL_W
        page.rect(f"rack-{rack.id}", x_off, 40, w, h,
                  text=rack.name + (f"\n{rack.location}" if rack.location else ""),
                  fill=_FRAME_FILL, stroke=_FRAME_STROKE, line_w_pt=1.2,
                  font_pt=12, bold=True, valign=0)
        page.rect(f"rack-{rack.id}-slots", inner_x, 40 + HEADER_H + FRAME_PAD,
                  RACK_W, rack.u_height * U_PX, fill=_SLOT_FILL,
                  stroke="#c9ced4", line_w_pt=0.5)
        for u in range(1, rack.u_height + 1):
            y = 40 + _u_to_y(rack, u)
            page.rect(f"rack-{rack.id}-u{u}", x_off + FRAME_PAD, y, RAIL_W, U_PX,
                      text=str(u), fill="#ffffff", stroke="#ffffff",
                      no_fill=True, font_pt=6.5, color="#6b7480")
        for item in rack.items:
            t = types.get(item.type_id)
            if t is None:
                continue
            top_u = (item.position_u if rack.desc_units
                     else item.position_u + t.u_height - 1)
            y = 40 + _u_to_y(rack, top_u)
            label = item.meta.hostname or f"{t.vendor} {t.model}"
            sub = f"{t.vendor} {t.model} · {t.u_height}U"
            page.rect(f"item-{item.id}", inner_x, y + 1, RACK_W,
                      t.u_height * U_PX - 2, text=f"{label}\n{sub}",
                      fill=_tint(t.color), stroke=t.color, font_pt=8,
                      halign=0)
        x_off += w + GAP_X
    return page


# --- Page Logique -----------------------------------------------------------

def _logical_page(project: Project, types: dict[str, EquipmentType]) -> _Page:
    pos = layout_nodes(project, types)
    items = {i.id: (r, i) for r in project.racks for i in r.items}
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    total_w = max(xs) + NODE_W + 60
    total_h = max(ys) + NODE_H + 60
    page = _Page("Logique", total_w, total_h)
    # Zones de couche derrière les nœuds.
    ranks: dict[int, list[str]] = {}
    for nid in pos:
        _, item = items[nid]
        t = types.get(item.type_id)
        ranks.setdefault(LAYER_RANK.get(t.category if t else "other", 5),
                         []).append(nid)
    for rank, ids in sorted(ranks.items()):
        zx = [pos[i][0] for i in ids]
        zy = [pos[i][1] for i in ids]
        page.rect(f"zone-{rank}", min(zx) - 16, min(zy) - 26,
                  max(zx) + NODE_W + 16 - (min(zx) - 16),
                  max(zy) + NODE_H + 12 - (min(zy) - 26),
                  text=ZONE_LABELS.get(rank, "AUTRES"), no_fill=True,
                  stroke="#9aa2ad", dashed=True, font_pt=7, color="#6b7480",
                  halign=0, valign=0)
    # Liens (avant les nœuds : ils restent dessous).
    for link in project.logical.links:
        a, b = link.from_.equipment_id, link.to.equipment_id
        if a not in pos or b not in pos:
            continue
        color, pattern, width = _EDGE_STYLE.get(link.kind, _EDGE_STYLE["other"])
        ports = " · ".join(p for p in (link.from_.port, link.to.port) if p)
        text = link.label or link.kind
        if ports:
            text += f" ({ports})"
        page.line(f"edge-{link.id}",
                  pos[a][0] + NODE_W / 2, pos[a][1] + NODE_H / 2,
                  pos[b][0] + NODE_W / 2, pos[b][1] + NODE_H / 2,
                  color=color, line_w_pt=width, pattern=pattern, text=text)
    for nid, (x, y) in pos.items():
        rack, item = items[nid]
        t = types.get(item.type_id)
        label = item.meta.hostname or (f"{t.vendor} {t.model}" if t else nid)
        sub = f"{rack.name} · U{item.position_u}"
        if item.meta.mgmt_ip:
            sub += f" · {item.meta.mgmt_ip}"
        page.rect(f"lnode-{nid}", x, y, NODE_W, NODE_H, text=f"{label}\n{sub}",
                  fill=_tint(t.color if t else "#888888"),
                  stroke=(t.color if t else "#888888"), font_pt=9)
    return page


# --- Paquet OPC -------------------------------------------------------------

_CT = ('<?xml version="1.0" encoding="utf-8"?>'
       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
       '<Default Extension="xml" ContentType="application/xml"/>'
       '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
       '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>'
       '{pages}'
       '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
       '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
       '</Types>')

_ROOT_RELS = ('<?xml version="1.0" encoding="utf-8"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>'
              '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
              '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
              '</Relationships>')

_DOC_RELS = ('<?xml version="1.0" encoding="utf-8"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>'
             '</Relationships>')

# Feuille de style « No Style » : la base dont hérite toute forme. Visio
# s'attend à la trouver (ID 0) — on y pose les propriétés par défaut.
_DOCUMENT = (
    '<?xml version="1.0" encoding="utf-8"?>'
    f'<VisioDocument xmlns="{_NS_MAIN}" xmlns:r="{_NS_R}" xml:space="preserve">'
    '<DocumentSettings TopPage="0" DefaultTextStyle="0" DefaultLineStyle="0" '
    'DefaultFillStyle="0" DefaultGuideStyle="0"/>'
    '<StyleSheets><StyleSheet ID="0" NameU="No Style" Name="No Style">'
    '<Cell N="EnableLineProps" V="1"/><Cell N="EnableFillProps" V="1"/>'
    '<Cell N="EnableTextProps" V="1"/><Cell N="HideForApply" V="0"/>'
    '<Cell N="LineWeight" V="0.01"/><Cell N="LineColor" V="#000000"/>'
    '<Cell N="LinePattern" V="1"/><Cell N="Rounding" V="0"/>'
    '<Cell N="BeginArrow" V="0"/><Cell N="EndArrow" V="0"/>'
    '<Cell N="FillForegnd" V="#ffffff"/><Cell N="FillBkgnd" V="#000000"/>'
    '<Cell N="FillPattern" V="1"/><Cell N="TextBkgnd" V="0"/>'
    '<Cell N="LeftMargin" V="0.0277"/><Cell N="RightMargin" V="0.0277"/>'
    '<Cell N="TopMargin" V="0.0277"/><Cell N="BottomMargin" V="0.0277"/>'
    '<Cell N="VerticalAlign" V="1"/><Cell N="TextDirection" V="0"/>'
    '<Section N="Character"><Row IX="0"><Cell N="Font" V="Calibri"/>'
    '<Cell N="Color" V="#000000"/><Cell N="Style" V="0"/>'
    '<Cell N="Size" V="0.1667"/></Row></Section>'
    '<Section N="Paragraph"><Row IX="0"><Cell N="IndFirst" V="0"/>'
    '<Cell N="IndLeft" V="0"/><Cell N="IndRight" V="0"/>'
    '<Cell N="SpLine" V="-1.2"/><Cell N="SpBefore" V="0"/>'
    '<Cell N="SpAfter" V="0"/><Cell N="HorzAlign" V="1"/></Row></Section>'
    '</StyleSheet></StyleSheets></VisioDocument>')


def _pages_xml(pages: list[_Page]) -> str:
    out = [f'<?xml version="1.0" encoding="utf-8"?>'
           f'<Pages xmlns="{_NS_MAIN}" xmlns:r="{_NS_R}" xml:space="preserve">']
    for i, p in enumerate(pages):
        out.append(
            f'<Page ID="{i}" NameU={quoteattr(p.name)} Name={quoteattr(p.name)}>'
            '<PageSheet LineStyle="0" FillStyle="0" TextStyle="0">'
            f'<Cell N="PageWidth" V="{_fmt(p.w_in)}"/>'
            f'<Cell N="PageHeight" V="{_fmt(p.h_in)}"/>'
            '<Cell N="PageScale" V="1" U="IN"/><Cell N="DrawingScale" V="1" U="IN"/>'
            '<Cell N="DrawingSizeType" V="3"/><Cell N="DrawingScaleType" V="0"/>'
            '<Cell N="PageLockReplace" V="0"/><Cell N="PageLockDuplicate" V="0"/>'
            '</PageSheet>'
            f'<Rel r:id="rId{i + 1}"/></Page>')
    out.append('</Pages>')
    return "".join(out)


def _pages_rels(n: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{i + 1}" '
        f'Type="http://schemas.microsoft.com/visio/2010/relationships/page" '
        f'Target="page{i + 1}.xml"/>' for i in range(n))
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{rels}</Relationships>')


def _core_props(title: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title>'
            '<dc:creator>RackForgePrime</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>')


_APP_PROPS = ('<?xml version="1.0" encoding="utf-8"?>'
              '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
              'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
              '<Application>RackForgePrime</Application></Properties>')


def render_vsdx(project: Project) -> bytes:
    """Projet -> fichier .vsdx (2 pages : Élévation + Logique)."""
    types = type_index(project)
    pages = [_physical_page(project, types), _logical_page(project, types)]
    ct_pages = "".join(
        f'<Override PartName="/visio/pages/page{i + 1}.xml" '
        f'ContentType="application/vnd.ms-visio.page+xml"/>'
        for i in range(len(pages)))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT.format(pages=ct_pages))
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("docProps/core.xml", _core_props(project.name))
        z.writestr("docProps/app.xml", _APP_PROPS)
        z.writestr("visio/document.xml", _DOCUMENT)
        z.writestr("visio/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("visio/pages/pages.xml", _pages_xml(pages))
        z.writestr("visio/pages/_rels/pages.xml.rels", _pages_rels(len(pages)))
        for i, p in enumerate(pages):
            z.writestr(f"visio/pages/page{i + 1}.xml", p.xml())
    return buf.getvalue()
