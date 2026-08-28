"""Catalogue intégré RackForgePrime.

Modélisé sur du matériel réel (hauteurs U, conso et ports d'après les
datasheets publiques). Aucune image constructeur embarquée : chaque type sans
``faceplate_svg`` est rendu comme placeholder fidèle à l'échelle U, avec le
bouton « Remplacer par image officielle » côté UI. L'import de définitions
YAML NetBox devicetype-library viendra enrichir cette liste.
"""

from .models import EquipmentType, Port

# Couleurs par rôle (voir docs/RECHERCHE_VISUELLE.md — DA retenue).
ROLE_COLORS = {
    "switch": "#22d3ee",
    "firewall": "#f97316",
    "patch-panel": "#3b82f6",
    "ups": "#eab308",
    "server": "#a78bfa",
    "blank": "#334155",
    "cable-mgmt": "#64748b",
    "router": "#34d399",
    "other": "#94a3b8",
}


def _ports(prefix: str, count: int, ptype: str = "1000base-t") -> list[Port]:
    """Génère une série de ports nommés (ex : Gi1/0/1 … Gi1/0/48)."""
    return [Port(name=f"{prefix}{i}", type=ptype) for i in range(1, count + 1)]


BUILTIN_TYPES: list[EquipmentType] = [
    EquipmentType(
        id="cisco-catalyst-9300-48p",
        vendor="Cisco", model="Catalyst 9300-48P", category="switch",
        u_height=1, power_w=437,
        ports=_ports("Gi1/0/", 48),
        color=ROLE_COLORS["switch"],
    ),
    EquipmentType(
        id="cisco-catalyst-9200l-24t",
        vendor="Cisco", model="Catalyst 9200L-24T", category="switch",
        u_height=1, power_w=75,
        ports=_ports("Gi1/0/", 24),
        color=ROLE_COLORS["switch"],
    ),
    EquipmentType(
        id="aruba-6300m-48g",
        vendor="HPE Aruba", model="6300M 48G", category="switch",
        u_height=1, power_w=90,
        ports=_ports("1/1/", 48),
        color=ROLE_COLORS["switch"],
    ),
    EquipmentType(
        id="fortinet-fortigate-100f",
        vendor="Fortinet", model="FortiGate 100F", category="firewall",
        u_height=1, power_w=60,
        ports=_ports("port", 16),
        color=ROLE_COLORS["firewall"],
    ),
    EquipmentType(
        id="fortinet-fortigate-600e",
        vendor="Fortinet", model="FortiGate 600E", category="firewall",
        u_height=1, power_w=90,
        ports=_ports("port", 24),
        color=ROLE_COLORS["firewall"],
    ),
    EquipmentType(
        id="generic-patch-panel-24",
        vendor="Générique", model="Panneau de brassage 24 ports", category="patch-panel",
        u_height=1, power_w=0,
        ports=_ports("P", 24, "rj45"),
        color=ROLE_COLORS["patch-panel"],
    ),
    EquipmentType(
        id="generic-patch-panel-48",
        vendor="Générique", model="Panneau de brassage 48 ports", category="patch-panel",
        u_height=2, power_w=0,
        ports=_ports("P", 48, "rj45"),
        color=ROLE_COLORS["patch-panel"],
    ),
    EquipmentType(
        id="apc-smart-ups-3000-2u",
        vendor="APC", model="Smart-UPS 3000 (2U)", category="ups",
        u_height=2, power_w=0,  # source d'énergie, pas une charge
        ports=[],
        color=ROLE_COLORS["ups"],
    ),
    EquipmentType(
        id="dell-poweredge-r650",
        vendor="Dell", model="PowerEdge R650", category="server",
        u_height=1, power_w=450,
        ports=_ports("eno", 4),
        color=ROLE_COLORS["server"],
    ),
    EquipmentType(
        id="hpe-proliant-dl380-g11",
        vendor="HPE", model="ProLiant DL380 Gen11", category="server",
        u_height=2, power_w=500,
        ports=_ports("eno", 4),
        color=ROLE_COLORS["server"],
    ),
    EquipmentType(
        id="generic-blank-1u",
        vendor="Générique", model="Obturateur 1U", category="blank",
        u_height=1, power_w=0, ports=[],
        color=ROLE_COLORS["blank"],
    ),
    EquipmentType(
        id="generic-blank-2u",
        vendor="Générique", model="Obturateur 2U", category="blank",
        u_height=2, power_w=0, ports=[],
        color=ROLE_COLORS["blank"],
    ),
    EquipmentType(
        id="generic-cable-mgmt-1u",
        vendor="Générique", model="Passe-câbles 1U", category="cable-mgmt",
        u_height=1, power_w=0, ports=[],
        color=ROLE_COLORS["cable-mgmt"],
    ),
]
