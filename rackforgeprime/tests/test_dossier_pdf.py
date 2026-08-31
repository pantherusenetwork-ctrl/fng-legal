"""Export dossier DAT : PDF multi-pages avec cartouche."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.models import Project, Rack, RackItem
from rackforge.pdf_export import _bom_rows, render_project_dossier_pdf


def _project() -> Project:
    return Project(
        id="prj-test", name="Test dossier",
        racks=[Rack(id="rack-a", name="Baie A", u_height=42, items=[
            RackItem(id="eq-01", type_id="fortinet-fortigate-100f",
                     position_u=40,
                     meta={"hostname": "FW-01",
                           "port_usage": [{"port": "port1", "outlet": "PM-R1",
                                           "vlan": "99", "usage": "Mgmt"}]}),
            RackItem(id="eq-02", type_id="fortinet-fortigate-100f",
                     position_u=38, meta={}),
            RackItem(id="eq-03", type_id="generic-patch-panel-24",
                     position_u=36, meta={}),
        ])],
    )


def test_dossier_pdf_genere_et_pagine():
    pdf = render_project_dossier_pdf(_project())
    assert pdf.startswith(b"%PDF")
    # 4 pages minimum : élévation, logique, brassage, nomenclature.
    assert pdf.count(b"/Type /Page") >= 4 or pdf.count(b"/Type/Page") >= 4


def test_bom_agrege_par_type():
    rows = _bom_rows(_project())
    # 2 FortiGate 100F agrégés + 1 panneau : 2 lignes.
    assert len(rows) == 2
    fg = next(r for r in rows if "FortiGate 100F" in r[1])
    assert fg[3] == "2" and fg[4] == "2U"
