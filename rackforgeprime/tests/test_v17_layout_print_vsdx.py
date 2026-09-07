"""v1.7 : layout logique compact, échelle d'impression, wrap identifiants,
VSDX <Connect>, appariement panneau↔switch, câbles export, instance unique."""

import io
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import run  # noqa: E402
from app import VERSION, app  # noqa: E402
from rackforge.models import Project, type_index  # noqa: E402
from rackforge.pairing import pair_panel_switch  # noqa: E402
from rackforge.pdf_export import choose_print_scale, render_project_pdf  # noqa: E402
from rackforge.svg_export import render_project_svg  # noqa: E402
from rackforge.svg_logical import MAX_ROW_PX, layout_nodes, render_logical_svg  # noqa: E402
from rackforge.textutil import wrap_label  # noqa: E402
from rackforge.vsdx_export import render_vsdx  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"
NS = "{http://schemas.microsoft.com/office/visio/2012/main}"
client = TestClient(app)


def demo() -> Project:
    return Project.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def _many_panels(n: int = 18) -> Project:
    """Projet avec beaucoup de panneaux (le cas juge : une seule rangée
    trop large)."""
    items = []
    for i in range(n):
        items.append({
            "id": f"pp-{i:02d}",
            "type_id": "generic-patch-panel-24",
            "position_u": max(1, 42 - i),
            "face": "front",
            "meta": {"hostname": f"PP-ATLAS-{chr(65 + (i % 26))}",
                     "role": "patch-panel"},
        })
    items.append({
        "id": "sw-01", "type_id": "cisco-catalyst-9300-48p",
        "position_u": 1, "face": "front",
        "meta": {"hostname": "SW-AGR-C-01", "role": "switch"},
    })
    return Project.model_validate({
        "id": "prj-wide", "name": "Large",
        "racks": [{"id": "rack-a", "name": "ATLAS", "u_height": 42,
                   "items": items}],
        "logical": {"vlans": [], "links": []},
    })


def test_version_badge_alignee():
    assert VERSION == "1.7.0"
    html = (Path(__file__).resolve().parent.parent / "frontend" / "index.html"
            ).read_text(encoding="utf-8")
    assert "v1.7.0" in html


def test_wrap_label_sans_ellipsis():
    lines = wrap_label("FWL-VRS-01-PRIMAIRE", 12, 3)
    assert len(lines) >= 2
    assert all("…" not in ln and "..." not in ln for ln in lines)
    assert "".join(ln.replace("-", "") for ln in lines).replace(" ", "") \
        in "FWLVRS01PRIMAIRE" or "PRIMAIRE" in "".join(lines)


def test_layout_compact_wrap_par_rangee():
    p = _many_panels(18)
    pos = layout_nodes(p, type_index(p))
    xs = [x for x, _ in pos.values()]
    assert max(xs) + 214 < 1600, max(xs)
    assert max(xs) <= MAX_ROW_PX + 80
    # Plusieurs rangées de brassage : des Y distincts parmi les PP.
    ys = {round(pos[f"pp-{i:02d}"][1], 1) for i in range(18)}
    assert len(ys) >= 3


def test_layout_groupe_par_baie():
    payload = {
        "id": "prj-2", "name": "Deux baies",
        "racks": [
            {"id": "rack-a", "name": "ATLAS", "items": [
                {"id": "pa", "type_id": "generic-patch-panel-24",
                 "position_u": 10, "meta": {"hostname": "PP-A"}}]},
            {"id": "rack-b", "name": "TITAN", "items": [
                {"id": "pb", "type_id": "generic-patch-panel-24",
                 "position_u": 10, "meta": {"hostname": "PP-B"}}]},
        ],
        "logical": {"links": []},
    }
    p = Project.model_validate(payload)
    pos = layout_nodes(p, type_index(p))
    # Même couche, ATLAS à gauche de TITAN (ordre des baies).
    assert pos["pa"][0] < pos["pb"][0]


def test_layout_couches_toujours_haut_bas():
    p = demo()
    pos = layout_nodes(p, type_index(p))
    assert pos["eq-01"][1] < pos["eq-02"][1] < pos["eq-04"][1]


def test_logical_svg_sans_ellipsis_identifiant():
    p = _many_panels(1)
    p.racks[0].items[0].meta.hostname = "PP-ATLAS-TRES-LONG-IDENTIFIANT"
    svg = render_logical_svg(p)
    assert "…" not in svg
    assert "PP-ATLAS" in svg


def test_print_scale_1_10_tient_sur_a4():
    # Dessin type 42U (~520 × 1800 px SVG) tient en 1:10 sur A4 portrait.
    s, label = choose_print_scale(520, 1800, 595.27, 841.89, 28, wanted=10)
    assert label == "1:10"
    assert 0.28 < s < 0.34


def test_print_scale_trop_grand_retombe_honnete():
    # Un dessin énorme ne prétend pas être du 1:10.
    s, label = choose_print_scale(4000, 8000, 595.27, 841.89, 28, wanted=10)
    assert label != "1:10"
    assert s * 8000 < 841.89


def test_pdf_physique_ecrit_echelle():
    pdf = render_project_pdf(demo(), view="physical", echelle=10)
    assert pdf.startswith(b"%PDF")
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf))
    text = "".join((p.extract_text() or "") for p in reader.pages)
    meta = " ".join(str(x) for x in (reader.metadata or {}).values())
    blob = text + " " + meta
    assert "1:10" in blob or "chelle" in blob.lower() or "EIA-310" in blob


def test_vsdx_connecteurs_connect():
    p = demo()
    z = zipfile.ZipFile(io.BytesIO(render_vsdx(p)))
    page2 = ET.fromstring(z.read("visio/pages/page2.xml"))
    connects = list(page2.iter(f"{NS}Connect"))
    assert connects, "au moins un <Connect> sur la page logique"
    froms = {c.get("FromCell") for c in connects}
    assert "BeginX" in froms and "EndX" in froms
    # Chaque lien du démo a une forme edge- + 2 Connect.
    names = {s.get("Name") for s in page2.iter(f"{NS}Shape")}
    for link in p.logical.links:
        assert f"edge-{link.id}" in names


def test_pair_panel_switch_cree_cordons():
    p = demo()
    # eq-03 = panneau 24P, eq-02 = Catalyst 9300 48P.
    r = pair_panel_switch(p, "eq-03", "eq-02")
    assert r["created"] == 24
    assert r["skipped"] == 0
    copper = [lk for lk in p.logical.links if lk.from_.equipment_id == "eq-03"]
    assert len(copper) == 24
    assert copper[0].from_.port == "P1"
    assert copper[0].to.port.startswith("Gi1/0/")
    assert copper[0].media == "cuivre-cat6a"
    # Re-appariement : rien de doublé.
    r2 = pair_panel_switch(p, "eq-03", "eq-02")
    assert r2["created"] == 0 and r2["skipped"] == 24


def test_pair_refuse_mauvais_role():
    p = demo()
    try:
        pair_panel_switch(p, "eq-01", "eq-02")  # firewall
        raise AssertionError("aurait dû refuser")
    except ValueError as exc:
        assert "panneau" in str(exc).lower()


def test_api_pair_panel():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/pair-panel?panel=eq-03&switch=eq-02", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["created"] == 24
    assert len(body["project"]["logical"]["links"]) >= 24


def test_export_svg_cables_et_leger():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    # D'abord apparier pour avoir des cordons.
    payload = client.post("/api/pair-panel?panel=eq-03&switch=eq-02",
                          json=payload).json()["project"]
    svg = client.post("/api/export/svg?view=physical&cables=true", json=payload)
    assert svg.status_code == 200
    assert b'id="cables"' in svg.content
    assert b"cable-" in svg.content
    leger = client.post("/api/export/svg?view=physical&leger=true", json=payload)
    assert leger.status_code == 200
    # Export léger = dessin, pas de data URI photo.
    assert b"data:image" not in leger.content


def test_name_plate_wrap_pas_ellipsis():
    p = demo()
    p.racks[0].items[0].meta.hostname = "FW-SIEGE-PRIMAIRE-LONG"
    svg = render_project_svg(p, noms=True)
    assert "…" not in svg
    assert "FW-SIEGE" in svg


def test_instance_unique_scanne_la_plage():
    assert run.find_running_rackforge(8199, lo=8198, hi=8199) == (None, None)
    assert run.port_is_free("127.0.0.1", 8199)
