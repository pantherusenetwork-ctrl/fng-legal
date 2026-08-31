"""Export draw.io : XML bien formé, cellules et liens présents."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.drawio_export import render_drawio  # noqa: E402
from rackforge.models import Project, Rack, RackItem  # noqa: E402


def _project() -> Project:
    return Project(
        id="prj-dio", name="Test draw.io",
        racks=[Rack(id="rack-a", name="Baie A", u_height=12, items=[
            RackItem(id="eq-01", type_id="fortinet-fortigate-100f",
                     position_u=10, meta={"hostname": "FW-01"}),
            RackItem(id="eq-02", type_id="aruba-6300m-48g",
                     position_u=8, meta={"hostname": "SW-01"}),
        ])],
        logical={"vlans": [], "links": [
            {"id": "lk-1", "from": {"equipment_id": "eq-01", "port": "port1"},
             "to": {"equipment_id": "eq-02", "port": "1/1/1"},
             "kind": "trunk", "vlans": [], "label": "Uplink", "media": ""},
        ]},
    )


def test_drawio_bien_forme_et_complet():
    xml = render_drawio(_project())
    root = ET.fromstring(xml)  # lève si mal formé
    assert root.tag == "mxfile"
    diagrams = root.findall("diagram")
    assert [d.get("name") for d in diagrams] == ["Élévation", "Logique"]
    # Équipements sur la page élévation, nœuds + lien sur la logique.
    elev = ET.tostring(diagrams[0], encoding="unicode")
    logi = ET.tostring(diagrams[1], encoding="unicode")
    assert 'id="item-eq-01"' in elev and 'id="item-eq-02"' in elev
    assert "FW-01" in elev and "SW-01" in logi
    assert 'id="edge-lk-1"' in logi and 'source="lnode-eq-01"' in logi


def test_drawio_lien_extremite_inconnue_ignore():
    p = _project()
    p.logical.links[0].to.equipment_id = "eq-fantome"
    xml = render_drawio(p)
    assert "edge-lk-1" not in xml
