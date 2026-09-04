"""Vue logique D'UNE BAIE : ses équipements, voisins externes en fantômes,
le reste du projet absent ; baie inconnue refusée."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from rackforge.models import Project, type_index  # noqa: E402
from rackforge.svg_logical import (_collect_nodes,  # noqa: E402
                                   render_logical_svg)

client = TestClient(app)


def _project() -> Project:
    return Project(
        id="prj-lr", name="Logique par baie",
        racks=[
            {"id": "rack-a", "name": "ATLAS", "items": [
                {"id": "fw", "type_id": "fortinet-fortigate-100f", "position_u": 40,
                 "meta": {"hostname": "FW-01"}},
                {"id": "sw", "type_id": "cisco-catalyst-9300-48p", "position_u": 38,
                 "meta": {"hostname": "SW-01"}}]},
            {"id": "rack-b", "name": "TITAN", "items": [
                {"id": "srv", "type_id": "dell-poweredge-r650", "position_u": 10,
                 "meta": {"hostname": "PX-01"}},
                {"id": "ups", "type_id": "apc-smart-ups-3000-2u", "position_u": 2,
                 "meta": {"hostname": "UPS-01"}}]},
        ],
        logical={"links": [
            {"id": "l1", "from": {"equipment_id": "fw"}, "to": {"equipment_id": "sw"}, "kind": "uplink"},
            {"id": "l2", "from": {"equipment_id": "sw"}, "to": {"equipment_id": "srv"}, "kind": "trunk"},
        ]},
    )


def test_vue_baie_garde_ses_equipements_et_ses_voisins():
    p = _project()
    nodes = _collect_nodes(p, type_index(p), "rack-a")
    by_id = {n["id"]: n for n in nodes}
    assert set(by_id) == {"fw", "sw", "srv"}      # ups (TITAN, non relié) absent
    assert not by_id["fw"]["ghost"] and not by_id["sw"]["ghost"]
    assert by_id["srv"]["ghost"] and by_id["srv"]["sub"].startswith("↗ ")


def test_svg_baie_fantome_pointille_et_titre():
    p = _project()
    svg = render_logical_svg(p, rack="rack-a")
    assert "schéma logique — baie ATLAS" in svg
    assert 'id="lnode-srv"' in svg and 'stroke-dasharray="5,4"' in svg
    assert 'id="lnode-ups"' not in svg
    assert 'id="link-l1"' in svg and 'id="link-l2"' in svg
    # Vue complète inchangée : tout le monde, personne en fantôme.
    full = render_logical_svg(p)
    assert 'id="lnode-ups"' in full and "— baie" not in full


def test_api_rack_inconnue_422_et_suffixe():
    payload = json.loads(_project().model_dump_json(by_alias=True))
    ok = client.post("/api/export/svg?view=logical&rack=rack-b", json=payload)
    assert ok.status_code == 200
    assert "-logique-rack-b.svg" in ok.headers["content-disposition"]
    assert b"lnode-ups" in ok.content and b"lnode-fw" not in ok.content
    ko = client.post("/api/export/svg?view=logical&rack=nope", json=payload)
    assert ko.status_code == 422 and "Baie inconnue" in ko.text
    pdf = client.post("/api/export/pdf?view=logical&rack=rack-a", json=payload)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
