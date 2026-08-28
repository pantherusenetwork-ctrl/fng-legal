"""Tests du moteur de placement — le cœur : snap U, collisions, bornes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from pydantic import ValidationError  # noqa: E402

from rackforge.models import (  # noqa: E402
    Project, Rack, RackItem, free_positions, patch_table, rack_stats,
    type_index, validate_placement,
)


def make_project(items: list[RackItem], u_height: int = 42) -> Project:
    return Project(
        id="prj-test", name="Test",
        racks=[Rack(id="rack-a", name="Baie A", u_height=u_height, items=items)],
    )


def test_valid_project_accepted():
    p = make_project([
        RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p", position_u=42),
        RackItem(id="eq-02", type_id="hpe-proliant-dl380-g11", position_u=10),
    ])
    assert validate_placement(p, type_index(p)) == []


def test_collision_rejected():
    # Un 2U en U10 occupe U10-U11 : un 1U en U11 doit être refusé.
    with pytest.raises(ValidationError, match="collision"):
        make_project([
            RackItem(id="eq-01", type_id="hpe-proliant-dl380-g11", position_u=10),
            RackItem(id="eq-02", type_id="cisco-catalyst-9300-48p", position_u=11),
        ])


def test_overflow_rejected():
    # Un 2U en U42 dépasserait la baie (U42-U43 sur 42U).
    with pytest.raises(ValidationError, match="dépasse la baie"):
        make_project([
            RackItem(id="eq-01", type_id="apc-smart-ups-3000-2u", position_u=42),
        ])


def test_position_u_is_integer_only():
    # Le snap U est structurel : une position non entière est un type invalide.
    with pytest.raises(ValidationError):
        make_project([
            RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p",
                     position_u=1.5),  # type: ignore[arg-type]
        ])


def test_unknown_type_rejected():
    with pytest.raises(ValidationError, match="type inconnu"):
        make_project([
            RackItem(id="eq-01", type_id="n-existe-pas", position_u=1),
        ])


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError, match="dupliqué"):
        make_project([
            RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p", position_u=1),
            RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p", position_u=5),
        ])


def test_free_positions_excludes_occupied_and_edges():
    p = make_project([
        RackItem(id="eq-01", type_id="hpe-proliant-dl380-g11", position_u=10),
    ], u_height=12)
    types = type_index(p)
    free_2u = free_positions(p.racks[0], 2, types)
    # 2U posable en 1..8 (9 chevaucherait U10, 11 déborderait la baie).
    assert free_2u == [1, 2, 3, 4, 5, 6, 7, 8]
    # En ignorant l'item lui-même (déplacement), U10 redevient posable.
    assert 10 in free_positions(p.racks[0], 2, types, ignore_item_id="eq-01")


def test_stats():
    p = make_project([
        RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p", position_u=42),
        RackItem(id="eq-02", type_id="apc-smart-ups-3000-2u", position_u=1),
    ])
    st = rack_stats(p.racks[0], type_index(p))
    assert st["u_used"] == 3 and st["u_free"] == 39
    assert st["power_w"] == 437


def test_patch_table_sorted_top_down():
    p = make_project([
        RackItem(id="eq-01", type_id="cisco-catalyst-9300-48p", position_u=5),
        RackItem(id="eq-02", type_id="fortinet-fortigate-100f", position_u=40,
                 meta={"hostname": "FW-01",
                       "port_usage": [{"port": "port1", "outlet": "PM-R12",
                                       "vlan": "99", "usage": "Mgmt"}]}),
    ])
    rows = patch_table(p, type_index(p))
    assert rows[0]["equipment"] == "FW-01" and rows[0]["u"] == 40
    assert rows[0]["outlet"] == "PM-R12"
    assert rows[-1]["u"] == 5


def test_custom_project_type_usable():
    p = Project(
        id="prj-x", name="X",
        equipment_types=[{
            "id": "custom-1", "vendor": "Aruba", "model": "Truc 3U",
            "category": "switch", "u_height": 3,
        }],
        racks=[Rack(id="r", name="R", items=[
            RackItem(id="eq-01", type_id="custom-1", position_u=1),
        ])],
    )
    assert validate_placement(p, type_index(p)) == []
