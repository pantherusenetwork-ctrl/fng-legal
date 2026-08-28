"""Tests des exports : SVG bien formé, PDF non vide, JSON round-trip, API."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from rackforge.models import Project  # noqa: E402
from rackforge.pdf_export import render_project_pdf  # noqa: E402
from rackforge.svg_export import U_PX, render_project_svg  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"


def demo_project() -> Project:
    return Project.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def test_example_project_is_valid():
    p = demo_project()
    assert p.racks[0].u_height == 42
    assert len(p.racks[0].items) == 5


def test_json_round_trip():
    p = demo_project()
    dumped = json.dumps(p.model_dump(by_alias=True))
    p2 = Project.model_validate_json(dumped)
    assert p2 == p


def test_svg_well_formed_and_scaled():
    p = demo_project()
    svg = render_project_svg(p)
    root = ET.fromstring(svg)  # XML valide
    assert root.tag.endswith("svg")
    # Groupes nommés : rééditable dans draw.io / Inkscape.
    ids = [g.get("id") for g in root.iter() if g.get("id")]
    assert "rack-rack-a" in ids
    assert any(i and i.startswith("item-") for i in ids)
    # Échelle exacte : la zone U fait u_height * U_PX pixels.
    assert f'height="{42 * U_PX}"' in svg


def test_pdf_generated():
    pdf = render_project_pdf(demo_project())
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000


# --- API ---------------------------------------------------------------

client = TestClient(app)


def test_api_catalog():
    data = client.get("/api/catalog").json()
    assert any(t["id"] == "fortinet-fortigate-100f" for t in data["types"])
    assert data["role_colors"]["switch"]


def test_api_validate_ok_and_stats():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/validate", json=payload)
    assert res.status_code == 200
    assert res.json()["stats"]["rack-a"]["u_used"] == 7


def test_api_rejects_collision():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    # Deux équipements au même U : le backend doit refuser (422).
    payload["racks"][0]["items"][1]["position_u"] = \
        payload["racks"][0]["items"][0]["position_u"]
    res = client.post("/api/export/svg", json=payload)
    assert res.status_code == 422
    assert "collision" in json.dumps(res.json())


def test_api_exports():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    svg = client.post("/api/export/svg", json=payload)
    assert svg.status_code == 200 and b"<svg" in svg.content
    pdf = client.post("/api/export/pdf", json=payload)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_api_patch_table():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/patch-table", json=payload)
    rows = res.json()["rows"]
    assert rows and rows[0]["u"] >= rows[-1]["u"]  # tri haut de baie -> bas
