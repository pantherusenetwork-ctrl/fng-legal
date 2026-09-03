"""Matrice de flux — la pièce n°2 d'un DAT après le schéma logique.

Deux services :

- ``propose_flows`` : à partir de ce que le projet SAIT (VLANs déclarés,
  liens qui traversent un pare-feu/routeur, usage « WAN »), propose les
  lignes manquantes de la matrice — action VIDE (« à définir ») : jamais
  une règle de sécurité inventée à la place de l'ingénieur ;
- ``flow_matrix`` : la vue croisée zones × zones (cellule = action) pour
  l'écran et le dossier, et ``flows_csv`` pour Excel.
"""

from __future__ import annotations

import csv
import io

from .models import EquipmentType, Flow, Project

ACTION_LABELS = {"": "à définir", "allow": "Autorisé", "deny": "Refusé",
                 "nat": "NAT"}


def _zone_of_vlan(project: Project, vid: str) -> str:
    """« VLAN 20 — USERS » si déclaré, sinon « VLAN 20 »."""
    for v in project.logical.vlans:
        if str(v.vid) == str(vid):
            return f"VLAN {v.vid} — {v.name}"
    return f"VLAN {vid}"


def _filtering_items(project: Project, types: dict[str, EquipmentType]):
    for rack in project.racks:
        for item in rack.items:
            t = types.get(item.type_id)
            if t and t.category in ("firewall", "router"):
                yield item


def propose_flows(project: Project, types: dict[str, EquipmentType]
                  ) -> list[Flow]:
    """Lignes proposées (non encore présentes dans project.flows).

    Sources : chaque VLAN déclaré vers chaque autre VLAN à travers le
    pare-feu (ou le routeur) ; un usage de port contenant « WAN » ajoute
    Internet ↔ chaque VLAN. Les paires déjà documentées sont ignorées.
    """
    existing = {(f.src, f.dst) for f in project.flows}
    zones = [_zone_of_vlan(project, str(v.vid))
             for v in sorted(project.logical.vlans, key=lambda v: v.vid)]
    # VLANs cités sur les ports mais non déclarés : on les cite aussi.
    for rack in project.racks:
        for item in rack.items:
            for pu in item.meta.port_usage:
                vid = pu.vlan.strip()
                if vid.isdigit():
                    z = _zone_of_vlan(project, vid)
                    if z not in zones:
                        zones.append(z)
    filters = list(_filtering_items(project, types))
    via = ", ".join(i.meta.hostname or i.id for i in filters)
    has_wan = any("wan" in pu.usage.lower()
                  for rack in project.racks for item in rack.items
                  for pu in item.meta.port_usage)
    out: list[Flow] = []
    n = 0
    if has_wan:
        for z in zones:
            for src, dst in ((z, "Internet"), ("Internet", z)):
                if (src, dst) in existing:
                    continue
                n += 1
                out.append(Flow(id=f"fl-p{n:03d}", src=src, dst=dst,
                                proto="any", via=via, comment="proposé"))
    for a in zones:
        for b in zones:
            if a == b or (a, b) in existing:
                continue
            n += 1
            out.append(Flow(id=f"fl-p{n:03d}", src=a, dst=b, proto="any",
                            via=via, comment="proposé"))
    return out


def flow_matrix(project: Project) -> dict:
    """Zones (ordre d'apparition) + cellules {src -> {dst -> action}}.

    Plusieurs lignes pour une même paire : la cellule garde la plus
    restrictive (deny > nat > allow > vide) — la matrice affichée ne
    cache jamais un refus derrière une autorisation.
    """
    rank = {"": 0, "allow": 1, "nat": 2, "deny": 3}
    zones: list[str] = []
    cells: dict[str, dict[str, str]] = {}
    for f in project.flows:
        for z in (f.src, f.dst):
            if z and z not in zones:
                zones.append(z)
        if not f.src or not f.dst:
            continue
        cur = cells.setdefault(f.src, {}).get(f.dst, "")
        if rank[f.action] >= rank[cur]:
            cells[f.src][f.dst] = f.action
    return {"zones": zones, "cells": cells}


def flows_rows(project: Project) -> list[list[str]]:
    """Lignes du tableau (dossier PDF) : source, destination, proto,
    ports, action, via, commentaire."""
    return [[f.src, f.dst, f.proto, f.ports, ACTION_LABELS.get(f.action, ""),
             f.via, f.comment] for f in project.flows]


def flows_csv(project: Project) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Source", "Destination", "Protocole", "Ports", "Action",
                "Via", "Commentaire"])
    for row in flows_rows(project):
        w.writerow(row)
    return buf.getvalue()
