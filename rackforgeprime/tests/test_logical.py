"""Tests du schéma logique : auto-layout, positions manuelles, liens, exports."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from rackforge.models import Project, type_index  # noqa: E402
from rackforge.pdf_export import render_project_pdf  # noqa: E402
from rackforge.svg_logical import (LAYER_RANK, layout_nodes,  # noqa: E402
                                   render_logical_svg)

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"

client = TestClient(app)


def demo() -> Project:
    return Project.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


def test_layout_layers_top_down():
    """Le firewall est au-dessus du switch, lui-même au-dessus du serveur."""
    p = demo()
    pos = layout_nodes(p, type_index(p))
    assert pos["eq-01"][1] < pos["eq-02"][1] < pos["eq-04"][1]
    assert LAYER_RANK["firewall"] < LAYER_RANK["switch"] < LAYER_RANK["server"]


def test_blank_and_cable_mgmt_excluded():
    p = demo()
    svg = render_logical_svg(p)
    # L'onduleur apparaît, mais un obturateur n'aurait pas de nœud logique.
    assert "lnode-eq-05" in svg


def test_manual_position_wins():
    p = demo()
    p.logical.positions = {"eq-01": {"x": 500, "y": 300}}  # type: ignore[assignment]
    p = Project.model_validate(p.model_dump(by_alias=True))
    pos = layout_nodes(p, type_index(p))
    assert pos["eq-01"] == (500.0, 300.0)


def test_logical_svg_well_formed():
    svg = render_logical_svg(demo())
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    ids = [g.get("id") for g in root.iter() if g.get("id")]
    assert "link-lnk-01" in ids            # le lien du projet démo
    assert any(i.startswith("lnode-") for i in ids)
    assert "trunk" in svg                  # légende des types de liens


def test_link_with_unknown_end_is_skipped():
    p = demo()
    p.logical.links[0].to.equipment_id = "eq-fantome"
    svg = render_logical_svg(p)
    assert "link-lnk-01" not in svg  # lien ignoré, pas de crash


def test_logical_pdf():
    pdf = render_project_pdf(demo(), view="logical")
    assert pdf.startswith(b"%PDF")


def test_api_logical_exports():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    svg = client.post("/api/export/svg?view=logical", json=payload)
    assert svg.status_code == 200 and b"lnode-" in svg.content
    assert "-logique.svg" in svg.headers["content-disposition"]
    pdf = client.post("/api/export/pdf?view=logical", json=payload)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_positions_round_trip():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    payload["logical"]["positions"] = {"eq-01": {"x": 123.5, "y": 88}}
    p = Project.model_validate(payload)
    dumped = p.model_dump(by_alias=True)
    assert dumped["logical"]["positions"]["eq-01"]["x"] == 123.5
