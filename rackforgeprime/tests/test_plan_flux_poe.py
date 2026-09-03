"""Plan d'étage (hiérarchie site/bâtiment/salle), matrice de flux, budget PoE."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.energy import poe_report, poe_rows  # noqa: E402
from rackforge.flows import (flow_matrix, flows_csv,  # noqa: E402
                             propose_flows)
from rackforge.models import (EquipmentType, Flow, Port, PortUsage,  # noqa: E402
                              Project, Rack, RackItem, type_index)
from rackforge.svg_plan import (inter_rack_links,  # noqa: E402
                                rack_footprint_px, render_plan_svg)


def _project() -> Project:
    return Project(
        id="prj-plan", name="Plan test",
        equipment_types=[EquipmentType(
            id="sw-poe-test", vendor="Test", model="SW 24 PoE", category="switch",
            u_height=1, poe_budget_w=370,
            ports=[Port(name=f"p{i}") for i in range(1, 5)])],
        racks=[
            Rack(id="rack-a", name="ATLAS", items=[
                RackItem(id="fw", type_id="fortinet-fortigate-100f", position_u=40,
                         meta={"hostname": "FW-01",
                               "port_usage": [{"port": "wan1", "usage": "WAN fibre"}]}),
                RackItem(id="sw", type_id="sw-poe-test", position_u=38,
                         meta={"hostname": "SW-01", "port_usage": [
                             {"port": "p1", "vlan": "20", "poe_w": 15.4},
                             {"port": "p2", "vlan": "20", "poe_w": 30},
                             {"port": "p3", "vlan": "10"}]}),
            ]),
            Rack(id="rack-b", name="TITAN", items=[
                RackItem(id="srv", type_id="dell-poweredge-r650", position_u=10,
                         meta={"hostname": "PX-01"}),
            ]),
        ],
        logical={"vlans": [{"vid": 10, "name": "MGMT"}, {"vid": 20, "name": "USERS"}],
                 "links": [{"id": "l1", "from": {"equipment_id": "sw"},
                            "to": {"equipment_id": "srv"}, "kind": "trunk"},
                           {"id": "l2", "from": {"equipment_id": "fw"},
                            "to": {"equipment_id": "sw"}, "kind": "uplink"}]},
        sites=[{"id": "s1", "name": "Paris", "buildings": [
            {"id": "b1", "name": "Siège", "rooms": [
                {"id": "r1", "name": "OLYMPE", "mm_per_px": 10,
                 "racks": [{"rack_id": "rack-a", "x": 100, "y": 100},
                           {"rack_id": "rack-b", "x": 400, "y": 100, "rotation": 90}],
                 "points": [{"id": "ap1", "kind": "ap", "label": "AP-01",
                             "x": 600, "y": 300, "radius": 120,
                             "equipment_id": "sw"}]}]}]}],
    )


# --- Plan d'étage -----------------------------------------------------------

def test_plan_svg_baies_liens_et_couverture():
    p = _project()
    svg = render_plan_svg(p, "r1", theme="clair")
    root = ET.fromstring(svg)
    ids = {g.get("id") for g in root.iter() if g.get("id")}
    assert {"plan-r1", "planrack-rack-a", "planrack-rack-b",
            "planlink-rack-a-rack-b", "planpoint-ap1"} <= ids
    assert "Paris › Siège › OLYMPE" in svg
    # Emprise réelle : 600 × 1000 mm à 10 mm/px = 60 × 100 px.
    assert rack_footprint_px(p.sites[0].buildings[0].rooms[0]) == (60.0, 100.0)
    assert 'width="60"' in svg and 'height="100"' in svg
    # Un seul lien inter-baies (sw -> srv) ; fw -> sw est interne à ATLAS.
    assert inter_rack_links(p, p.sites[0].buildings[0].rooms[0]) == {
        ("rack-a", "rack-b"): 1}
    assert 'r="120"' in svg  # couverture Wi-Fi


def test_plan_sans_salle_est_un_etat_vide_propre():
    p = _project()
    p = p.model_copy(update={"sites": []})
    svg = render_plan_svg(p)
    assert "Aucune salle" in svg
    ET.fromstring(svg)


def test_plan_refuse_baie_inconnue_ou_posee_deux_fois():
    data = _project().model_dump(by_alias=True)
    data["sites"][0]["buildings"][0]["rooms"][0]["racks"].append(
        {"rack_id": "rack-zz", "x": 1, "y": 1})
    with pytest.raises(ValueError, match="baie inconnue"):
        Project.model_validate(data)
    data = _project().model_dump(by_alias=True)
    data["sites"][0]["buildings"][0]["rooms"][0]["racks"].append(
        {"rack_id": "rack-a", "x": 1, "y": 1})
    with pytest.raises(ValueError, match="deux plans"):
        Project.model_validate(data)


# --- Matrice de flux --------------------------------------------------------

def test_flux_proposes_depuis_vlans_et_wan():
    p = _project()
    props = propose_flows(p, type_index(p))
    pairs = {(f.src, f.dst) for f in props}
    assert ("VLAN 10 — MGMT", "VLAN 20 — USERS") in pairs
    assert ("VLAN 20 — USERS", "Internet") in pairs
    assert all(f.action == "" for f in props)      # jamais de règle inventée
    assert all("FW-01" in f.via for f in props)


def test_matrice_garde_l_action_la_plus_restrictive_et_csv():
    p = _project()
    p.flows = [Flow(id="f1", src="A", dst="B", action="allow"),
               Flow(id="f2", src="A", dst="B", action="deny", ports="22"),
               Flow(id="f3", src="B", dst="A", action="nat")]
    m = flow_matrix(p)
    assert m["zones"] == ["A", "B"]
    assert m["cells"]["A"]["B"] == "deny"
    assert m["cells"]["B"]["A"] == "nat"
    csv_text = flows_csv(p)
    assert csv_text.splitlines()[0].startswith("Source;Destination")
    assert "Refusé" in csv_text and ";22;" in csv_text


# --- Budget PoE -------------------------------------------------------------

def test_budget_poe_par_switch():
    p = _project()
    rep = poe_report(p, type_index(p))
    sw = next(r for r in rep if r["equipment"] == "SW-01")
    assert sw["budget_w"] == 370 and sw["drawn_w"] == 45.4
    assert sw["ports"] == 2 and sw["taux"] == 12 and sw["etat"] == "ok"
    rows = poe_rows(p, type_index(p))
    assert rows[0][3] == "370 W" and rows[0][6] == "12 %"


def test_budget_poe_alerte_et_inconnu():
    p = _project()
    # 320 W tirés sur 370 : alerte (>= 80 %).
    p.racks[0].items[1].meta.port_usage[0].poe_w = 90
    p.racks[0].items[1].meta.port_usage[1].poe_w = 90
    p.racks[0].items[1].meta.port_usage[2].poe_w = 90
    p.racks[0].items[1].meta.port_usage.append(
        PortUsage(port="p4", poe_w=50))
    rep = poe_report(p, type_index(p))
    assert rep[0]["etat"] == "alerte"
    # Switch PoE du catalogue sans budget connu : « à renseigner », pas inventé.
    p2 = Project(id="x", name="x", racks=[Rack(id="r", name="R", items=[
        RackItem(id="s", type_id="cisco-catalyst-9300-48p", position_u=1)])])
    rep2 = poe_report(p2, type_index(p2))
    assert rep2 and rep2[0]["etat"] == "budget à renseigner"
    assert poe_rows(p2, type_index(p2))[0][3] == "à renseigner"
