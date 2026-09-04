"""Mode dessin : un boîtier compact (width_mm) est dessiné à SA largeur,
comme sa photo — l'échelle ne dépend pas du rendu."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.models import EquipmentType, Port, Project, Rack, RackItem  # noqa: E402
from rackforge.svg_export import RACK_W, render_project_svg  # noqa: E402


def test_placeholder_compact_a_sa_largeur():
    t = EquipmentType(id="hex-test", vendor="MikroTik", model="hEX test",
                      category="router", u_height=1, width_mm=113,
                      ports=[Port(name=f"ether{i}") for i in range(1, 6)])
    p = Project(id="p", name="p", equipment_types=[t], racks=[Rack(
        id="r", name="R", items=[RackItem(id="i1", type_id="hex-test", position_u=10)])])
    svg = render_project_svg(p, rendu="dessin")
    g = svg[svg.index('id="item-i1"'):]
    g = g[:g.index("</g>")]
    widths = [float(w) for w in re.findall(r'<rect [^>]*width="([\d.]+)"', g)]
    expected = RACK_W * 113 / 482.6
    assert any(abs(w - expected) < 0.6 for w in widths), widths
    assert not any(abs(w - RACK_W) < 0.6 and 'rx="3"' in g for w in widths[1:2])
    # Pas d'oreilles de rail sur un compact, ports présents (5 tiennent).
    assert g.count("<circle") == 0
    assert g.count('fill-opacity="0.85"') >= 5


def test_passe_cables_avec_hostname_reste_dans_la_baie():
    p = Project(id="p", name="p", racks=[Rack(id="r", name="R", items=[
        RackItem(id="cm", type_id="generic-cable-mgmt-1u", position_u=5,
                 meta={"hostname": "PASSE-CABLES-01"})])])
    svg = render_project_svg(p, rendu="dessin")
    g = svg[svg.index('id="item-cm"'):]
    g = g[:g.index("</g>")]
    xs = [float(x) for x in re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="30"', g)]
    assert len(xs) == 4 and max(xs) + 30 <= 40 + RACK_W, xs
