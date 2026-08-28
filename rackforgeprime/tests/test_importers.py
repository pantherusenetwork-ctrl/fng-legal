"""Tests des importeurs (YAML NetBox, PDF datasheet), du CSV de brassage
et du rendu des images de faceplate."""

import base64
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen import canvas as pdf_canvas  # noqa: E402

from app import app  # noqa: E402
from rackforge.importers import (guess_category, import_netbox_yaml,  # noqa: E402
                                 parse_datasheet_pdf)
from rackforge.models import (Project, Rack, RackItem, patch_table_csv,  # noqa: E402
                              type_index)
from rackforge.pdf_export import render_project_pdf  # noqa: E402
from rackforge.svg_export import render_project_svg  # noqa: E402

client = TestClient(app)

NETBOX_YAML = """\
manufacturer: Cisco
model: Catalyst 9200L-48P-4G
slug: cisco-c9200l-48p-4g
u_height: 1
is_full_depth: false
interfaces:
  - name: GigabitEthernet1/0/1
    type: 1000base-t
  - name: GigabitEthernet1/0/2
    type: 1000base-t
"""


def fake_datasheet_pdf() -> bytes:
    """Génère un PDF de datasheet synthétique (texte extractible)."""
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    for i, line in enumerate([
        "FortiGate 200F Series",
        "Next-Generation Firewall — Fortinet",
        "Form factor: 1 RU rack mount",
        "Power Consumption (Maximum): 115 W",
        "18 x GE RJ45 interfaces",
    ]):
        c.drawString(50, 800 - 20 * i, line)
    c.showPage()
    c.save()
    return buf.getvalue()


# --- YAML NetBox ------------------------------------------------------------

def test_yaml_import():
    t = import_netbox_yaml(NETBOX_YAML)
    assert t.id == "cisco-c9200l-48p-4g"
    assert t.vendor == "Cisco" and t.u_height == 1
    assert t.category == "switch" and len(t.ports) == 2


def test_yaml_half_u_rounded_up():
    t = import_netbox_yaml("manufacturer: X\nmodel: Y\nu_height: 0.5\n")
    assert t.u_height == 1  # jamais en dessous de la réalité physique


def test_yaml_invalid_rejected():
    with pytest.raises(ValueError, match="manufacturer"):
        import_netbox_yaml("model: incomplet\n")
    with pytest.raises(ValueError, match="YAML illisible"):
        import_netbox_yaml("juste du texte")


def test_guess_category():
    assert guess_category("FortiGate 100F firewall") == "firewall"
    assert guess_category("Catalyst 9300 switch") == "switch"
    assert guess_category("truc mystère") == "other"


# --- PDF datasheet ----------------------------------------------------------

def test_datasheet_parse():
    out = parse_datasheet_pdf(fake_datasheet_pdf(), "fortigate-200f.pdf")
    p = out["proposal"]
    assert p["vendor"] == "Fortinet"
    assert p["u_height"] == 1 and out["confidence"]["u_height"]
    assert p["power_w"] == 115.0 and out["confidence"]["power_w"]
    assert len(p["ports"]) == 18
    assert p["category"] == "firewall"


def test_datasheet_api():
    res = client.post("/api/import/datasheet",
                      files={"file": ("fg.pdf", fake_datasheet_pdf(),
                                      "application/pdf")})
    assert res.status_code == 200
    assert res.json()["proposal"]["vendor"] == "Fortinet"


def test_yaml_api():
    res = client.post("/api/import/devicetype-yaml",
                      files={"file": ("sw.yaml", NETBOX_YAML.encode(),
                                      "text/yaml")})
    assert res.status_code == 200
    assert res.json()["type"]["category"] == "switch"


# --- CSV de brassage --------------------------------------------------------

def test_patch_table_csv():
    p = Project(id="prj", name="P", racks=[Rack(id="r", name="Baie A", items=[
        RackItem(id="eq-01", type_id="fortinet-fortigate-100f", position_u=40,
                 meta={"hostname": "FW-01",
                       "port_usage": [{"port": "port1", "outlet": "PM-R12",
                                       "vlan": "99", "usage": "Mgmt"}]}),
    ])])
    csv_text = patch_table_csv(p, type_index(p))
    assert "Baie;U;Équipement" in csv_text.replace('"', "")
    assert "Baie A;U40;FW-01;port1;PM-R12;99;Mgmt" in csv_text

    res = client.post("/api/patch-table.csv",
                      json=p.model_dump(by_alias=True))
    assert res.status_code == 200
    assert res.text.startswith("﻿")  # BOM pour Excel FR


# --- Image de faceplate (data URI) ------------------------------------------

def _tiny_png_uri() -> str:
    # PNG 1x1 minimal, suffisant pour le rendu.
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    return "data:image/png;base64," + base64.b64encode(png).decode()


def image_project() -> Project:
    return Project(
        id="prj-img", name="Image",
        equipment_types=[{
            "id": "custom-img", "vendor": "Aruba", "model": "Photo 1U",
            "category": "switch", "u_height": 1,
            "faceplate_image": _tiny_png_uri(),
        }],
        racks=[Rack(id="r", name="R", items=[
            RackItem(id="eq-01", type_id="custom-img", position_u=10),
        ])],
    )


def test_faceplate_image_in_svg_and_pdf():
    p = image_project()
    svg = render_project_svg(p)
    assert "<image" in svg and "data:image/png" in svg
    pdf = render_project_pdf(p)
    assert pdf.startswith(b"%PDF")


def test_faceplate_image_must_be_data_uri():
    with pytest.raises(Exception, match="data URI"):
        Project(id="p", name="P", equipment_types=[{
            "id": "x", "vendor": "V", "model": "M", "u_height": 1,
            "faceplate_image": "https://exemple.com/image.png",
        }])
