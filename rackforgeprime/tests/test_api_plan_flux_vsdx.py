"""API : vue plan (SVG/PDF), export VSDX, flux proposés + CSV, budget PoE,
et dossier PDF enrichi (pages plan / flux / PoE)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "projet-demo.json"
client = TestClient(app)


def _payload() -> dict:
    p = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    p["sites"] = [{"id": "s1", "name": "Paris", "buildings": [
        {"id": "b1", "name": "Siège", "rooms": [
            {"id": "r1", "name": "Local RDC", "mm_per_px": 10,
             "racks": [{"rack_id": "rack-a", "x": 120, "y": 90}],
             "points": [{"id": "ap1", "kind": "ap", "label": "AP-RDC-01",
                         "x": 500, "y": 300, "radius": 150}]}]}]}]
    p["flows"] = [{"id": "f1", "src": "VLAN 20 — USERS", "dst": "Internet",
                   "proto": "tcp", "ports": "80, 443", "action": "allow",
                   "via": "FW-SIEGE-01"}]
    p["racks"][0]["items"][1]["meta"]["poe_budget_w"] = 740
    p["racks"][0]["items"][1]["meta"]["port_usage"][0]["poe_w"] = 15.4
    return p


def test_api_plan_svg_et_pdf():
    svg = client.post("/api/export/svg?view=plan&room=r1&theme=clair",
                      json=_payload())
    assert svg.status_code == 200
    assert b"planrack-rack-a" in svg.content and b"AP-RDC-01" in svg.content
    assert "-plan.svg" in svg.headers["content-disposition"]
    pdf = client.post("/api/export/pdf?view=plan&room=r1", json=_payload())
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    # Salle inconnue : 422 lisible (comme rack=) ; sans room = première salle.
    svg2 = client.post("/api/export/svg?view=plan&room=zz", json=_payload())
    assert svg2.status_code == 422 and "Salle inconnue" in svg2.text
    svg3 = client.post("/api/export/svg?view=plan", json=_payload())
    assert svg3.status_code == 200 and b"planrack-rack-a" in svg3.content


def test_api_vsdx():
    res = client.post("/api/export/vsdx", json=_payload())
    assert res.status_code == 200
    assert res.content[:2] == b"PK"
    assert ".vsdx" in res.headers["content-disposition"]


def test_api_flux_propose_et_csv():
    res = client.post("/api/flows/propose", json=_payload())
    assert res.status_code == 200
    flows = res.json()["flows"]
    assert flows and all(f["action"] == "" for f in flows)
    # La paire déjà documentée (USERS -> Internet) n'est pas re-proposée.
    assert not any(f["src"] == "VLAN 20 — USERS" and f["dst"] == "Internet"
                   for f in flows)
    csv_res = client.post("/api/flows.csv", json=_payload())
    assert csv_res.status_code == 200
    assert "Autorisé" in csv_res.text and "80, 443" in csv_res.text


def test_api_poe():
    rows = client.post("/api/poe", json=_payload()).json()["rows"]
    sw = next(r for r in rows if r["equipment"] == "SW-CORE-01")
    assert sw["budget_w"] == 740 and sw["drawn_w"] == 15.4 and sw["etat"] == "ok"


def test_dossier_contient_plan_flux_poe():
    res = client.post("/api/export/pdf?view=dossier", json=_payload())
    assert res.status_code == 200
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(res.content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Plan — Local RDC" in text or "Local RDC" in text
    assert "Matrice de flux" in text
    assert "Budget PoE" in text


def test_api_refuse_baie_inconnue_sur_plan():
    p = _payload()
    p["sites"][0]["buildings"][0]["rooms"][0]["racks"][0]["rack_id"] = "nope"
    res = client.post("/api/validate", json=p)
    assert res.status_code == 422
    assert "baie inconnue" in json.dumps(res.json(), ensure_ascii=False)
