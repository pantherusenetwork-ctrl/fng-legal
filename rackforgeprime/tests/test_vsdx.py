"""Export Visio .vsdx : paquet OPC valide, deux pages, formes nommées.

Validation STRUCTURELLE (zip, XML, relations, types de contenu, formes) :
Visio n'est pas installé sur ce poste, l'ouverture réelle reste à
confirmer par l'utilisateur.
"""

import io
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.models import Project  # noqa: E402
from rackforge.vsdx_export import render_vsdx  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"
NS = "{http://schemas.microsoft.com/office/visio/2012/main}"


def _project() -> Project:
    return Project.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def _open(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


def test_vsdx_est_un_paquet_opc_complet():
    data = render_vsdx(_project())
    assert data[:2] == b"PK"
    z = _open(data)
    assert z.testzip() is None
    names = set(z.namelist())
    for part in ("[Content_Types].xml", "_rels/.rels", "visio/document.xml",
                 "visio/_rels/document.xml.rels", "visio/pages/pages.xml",
                 "visio/pages/_rels/pages.xml.rels", "visio/pages/page1.xml",
                 "visio/pages/page2.xml", "docProps/core.xml",
                 "docProps/app.xml"):
        assert part in names, part
    # Chaque partie est du XML bien formé.
    for n in names:
        ET.fromstring(z.read(n))


def test_vsdx_types_de_contenu_et_relations_coherents():
    z = _open(render_vsdx(_project()))
    ct = z.read("[Content_Types].xml").decode("utf-8")
    assert 'PartName="/visio/pages/page1.xml"' in ct
    assert 'PartName="/visio/pages/page2.xml"' in ct
    assert "application/vnd.ms-visio.drawing.main+xml" in ct
    rels = z.read("_rels/.rels").decode("utf-8")
    assert 'Target="visio/document.xml"' in rels
    prels = z.read("visio/pages/_rels/pages.xml.rels").decode("utf-8")
    assert 'Target="page1.xml"' in prels and 'Target="page2.xml"' in prels
    pages = ET.fromstring(z.read("visio/pages/pages.xml"))
    assert [p.get("Name") for p in pages.iter(f"{NS}Page")] == \
        ["Élévation", "Logique"]


def test_vsdx_formes_nommees_par_equipement():
    p = _project()
    z = _open(render_vsdx(p))
    page1 = ET.fromstring(z.read("visio/pages/page1.xml"))
    names = {s.get("Name") for s in page1.iter(f"{NS}Shape")}
    for rack in p.racks:
        assert f"rack-{rack.id}" in names
        for item in rack.items:
            assert f"item-{item.id}" in names
    # Une forme = pinX/pinY/width/height + géométrie fermée.
    first = next(s for s in page1.iter(f"{NS}Shape")
                 if s.get("Name").startswith("item-"))
    cells = {c.get("N"): c.get("V") for c in first.findall(f"{NS}Cell")}
    assert float(cells["Width"]) > 0 and float(cells["Height"]) > 0
    assert first.find(f"{NS}Section[@N='Geometry']") is not None
    assert first.find(f"{NS}Text") is not None


def test_vsdx_page_logique_noeuds_et_liens():
    p = _project()
    z = _open(render_vsdx(p))
    page2 = ET.fromstring(z.read("visio/pages/page2.xml"))
    names = {s.get("Name") for s in page2.iter(f"{NS}Shape")}
    for rack in p.racks:
        for item in rack.items:
            assert f"lnode-{item.id}" in names
    for link in p.logical.links:
        assert f"edge-{link.id}" in names
    # Unités Visio : Y monte — le nœud le plus haut du dessin (px) a le
    # PinY le plus grand (pouces).
    pins = {}
    for s in page2.iter(f"{NS}Shape"):
        if s.get("Name").startswith("lnode-"):
            cells = {c.get("N"): float(c.get("V")) for c in s.findall(f"{NS}Cell")
                     if c.get("N") in ("PinX", "PinY")}
            pins[s.get("Name")] = cells
    assert all(v["PinY"] > 0 for v in pins.values())
