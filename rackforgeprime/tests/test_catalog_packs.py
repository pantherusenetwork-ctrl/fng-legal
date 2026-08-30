"""Chargement des packs de types constructeurs depuis le catalogue."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.catalog import BUILTIN_TYPES
from rackforge.catalog_packs import SUBDIR, load_pack_types, merged_catalog

PACK = [{
    "id": "fortinet-fortiswitch-124f",
    "vendor": "Fortinet", "model": "FortiSwitch 124F", "category": "switch",
    "u_height": 1, "power_w": 20,
    "ports": [{"name": "port1", "type": "1000base-t"}],
    "color": "#22d3ee",
}]


def test_sans_dossier_aucun_pack(monkeypatch):
    monkeypatch.delenv("RACKFORGE_CATALOG_DIR", raising=False)
    assert load_pack_types() == []
    assert merged_catalog(BUILTIN_TYPES) == BUILTIN_TYPES


def test_pack_charge_et_fusionne(tmp_path, monkeypatch):
    d = tmp_path / SUBDIR
    d.mkdir()
    (d / "pack.json").write_text(json.dumps(PACK), encoding="utf-8")
    monkeypatch.setenv("RACKFORGE_CATALOG_DIR", str(tmp_path))
    merged = {t.id: t for t in merged_catalog(BUILTIN_TYPES)}
    assert "fortinet-fortiswitch-124f" in merged
    assert len(merged) == len(BUILTIN_TYPES) + 1


def test_pack_invalide_ignore_sans_planter(tmp_path, monkeypatch):
    d = tmp_path / SUBDIR
    d.mkdir()
    (d / "casse.json").write_text("{pas du json", encoding="utf-8")
    (d / "entree-invalide.json").write_text(
        json.dumps([{"id": "x"}, PACK[0]]), encoding="utf-8")
    monkeypatch.setenv("RACKFORGE_CATALOG_DIR", str(tmp_path))
    types = load_pack_types()
    # L'entrée valide passe, le reste est ignoré.
    assert [t.id for t in types] == ["fortinet-fortiswitch-124f"]
