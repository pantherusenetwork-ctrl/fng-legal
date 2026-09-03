"""Tests de la vue arrière.

La vue arrière est DÉRIVÉE du projet, jamais un second dessin : ces tests
verrouillent les trois règles qui la définissent —
  1. la baie passe en miroir horizontal, les U ne bougent pas ;
  2. on voit le DOS d'un équipement monté sur l'autre face ;
  3. le dos est neutre : aucun port arrière inventé.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from rackforge.models import (EquipmentType, Project, Rack, RackItem,
                              type_index)  # noqa: E402
from rackforge.svg_export import (MM_19_POUCES, RACK_W, _item_box,
                                  render_project_svg)  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"


def demo_project() -> Project:
    return Project.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))


# --- Miroir de la géométrie -------------------------------------------------

def _compact(width_mm: float = 216.0) -> EquipmentType:
    return EquipmentType(id="t-compact", vendor="X", model="Compact",
                         u_height=1, width_mm=width_mm)


def test_item_box_miroir_horizontal():
    """Un compact collé à gauche de face se retrouve à droite de dos."""
    t = _compact()
    item = RackItem(id="i1", type_id="t-compact", position_u=1,
                    position_x_mm=0.0)
    ix_avant, iw, shared = _item_box(t, item, 0.0, "front")
    ix_arriere, _, _ = _item_box(t, item, 0.0, "rear")
    assert shared and iw < RACK_W
    assert ix_avant == 0.0
    # Bord droit de dos = largeur utile - largeur du boîtier.
    attendu = RACK_W * (MM_19_POUCES - 216.0) / MM_19_POUCES
    assert abs(ix_arriere - attendu) < 0.01
    # Deux miroirs successifs ramènent à la position de départ.
    assert abs(ix_avant - (RACK_W - iw - ix_arriere)) < 0.01


def test_item_box_pleine_largeur_ne_bouge_pas():
    """Un rackable 19" occupe toute la façade : le miroir ne change rien."""
    t = EquipmentType(id="t-plein", vendor="X", model="Plein", u_height=1)
    item = RackItem(id="i1", type_id="t-plein", position_u=1)
    assert _item_box(t, item, 12.0, "front") == _item_box(t, item, 12.0, "rear")


# --- Rendu SVG --------------------------------------------------------------

def test_vue_arriere_svg_bien_formee_et_badgee():
    p = demo_project()
    avant = render_project_svg(p, face="front")
    arriere = render_project_svg(p, face="rear")
    ET.fromstring(arriere)  # XML valide
    assert "VUE ARRIÈRE" in arriere
    assert "VUE ARRIÈRE" not in avant
    assert "élévation arrière" in arriere
    assert "élévation avant" in avant


def test_les_u_ne_bougent_pas_entre_les_deux_faces():
    """Le miroir est horizontal : la hauteur de la zone U est identique."""
    p = demo_project()
    u_h = p.racks[0].u_height
    for face in ("front", "rear"):
        svg = render_project_svg(p, face=face)
        from rackforge.svg_export import U_PX
        assert f'height="{u_h * U_PX}"' in svg


def test_equipements_de_facade_vus_de_dos():
    """Le projet démo est monté en façade : de dos, tout est « vu de dos »
    et aucune photo officielle n'est affichée (on ne connaît pas l'arrière)."""
    p = demo_project()
    assert all(i.face == "front" for i in p.racks[0].items)
    arriere = render_project_svg(p, face="rear")
    root = ET.fromstring(arriere)
    titres = [e.text or "" for e in root.iter()
              if e.tag.endswith("title")]
    assert titres and all("vu de dos" in t for t in titres)
    # Aucune image de façade dans la vue arrière du projet démo.
    assert not [e for e in root.iter() if e.tag.endswith("image")]
    # Les groupes d'items sont bien tous là (rien n'est masqué).
    ids = {e.get("id") for e in root.iter() if (e.get("id") or "").startswith("item-")}
    assert len(ids) == len(p.racks[0].items)


def test_equipement_monte_a_l_arriere_montre_sa_facade():
    """Symétrie : monté à l'arrière, il est « de dos » en vue avant et
    normal en vue arrière."""
    p = demo_project()
    p.racks[0].items[0].face = "rear"
    cible = f'item-{p.racks[0].items[0].id}'

    def titre_de(svg: str) -> str:
        root = ET.fromstring(svg)
        for g in root.iter():
            if g.get("id") == cible:
                for e in g.iter():
                    if e.tag.endswith("title"):
                        return e.text or ""
        raise AssertionError(f"groupe {cible} absent du SVG")

    assert "vu de dos" in titre_de(render_project_svg(p, face="front"))
    assert "vu de dos" not in titre_de(render_project_svg(p, face="rear"))


def test_dos_n_invente_aucun_port():
    """Le dos ne doit PAS reprendre le dessin des ports de façade : la
    sérigraphie arrière réelle n'est pas connue, on ne la fabrique pas."""
    p = demo_project()
    types = type_index(p)
    # Un équipement du projet démo a bien des ports en façade.
    assert any(types[i.type_id].ports for i in p.racks[0].items)
    avant = render_project_svg(p, face="front", rendu="dessin")
    arriere = render_project_svg(p, face="rear", rendu="dessin")
    # Les languettes RJ45 (fill-opacity 0.85 sur 4x2.4) du dessin de
    # façade n'existent pas de dos.
    assert avant.count('height="2.4"') > 0
    assert arriere.count('height="2.4"') == 0


# --- API --------------------------------------------------------------------

client = TestClient(app)


def test_api_export_svg_face_arriere():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/export/svg?view=physical&face=rear", json=payload)
    assert res.status_code == 200
    assert "VUE ARRIÈRE" in res.text
    assert "-arriere.svg" in res.headers["content-disposition"]


def test_api_export_pdf_face_arriere():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/export/pdf?view=physical&face=rear", json=payload)
    assert res.status_code == 200 and res.content.startswith(b"%PDF")
    assert "-arriere.pdf" in res.headers["content-disposition"]


def test_api_refuse_une_face_inconnue():
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    res = client.post("/api/export/svg?view=physical&face=cote", json=payload)
    assert res.status_code == 422


def test_face_par_defaut_inchangee():
    """Sans paramètre, l'API rend toujours la face avant (non-régression)."""
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    sans = client.post("/api/export/svg", json=payload)
    avec = client.post("/api/export/svg?face=front", json=payload)
    assert sans.status_code == 200
    assert sans.text == avec.text


def test_projet_avec_equipement_arriere_reste_valide():
    """face n'entre pas dans le moteur de placement : un équipement monté
    à l'arrière occupe le même U (c'est le même châssis)."""
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    u_avant = client.post("/api/validate", json=payload).json()["stats"]
    payload["racks"][0]["items"][0]["face"] = "rear"
    res = client.post("/api/validate", json=payload)
    assert res.status_code == 200
    assert res.json()["stats"] == u_avant
