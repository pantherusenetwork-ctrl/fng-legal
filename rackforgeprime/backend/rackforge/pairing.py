"""Appariement en masse d'un panneau de brassage avec un switch.

Un cordon par port du panneau, branché sur le port cuivre suivant du
switch (ordre du catalogue). Aucun VLAN, aucun hostname inventé : on
ne crée que les liens manquants. Les liens déjà présents (même paire
d'équipements + mêmes ports) sont laissés tels quels.
"""

from __future__ import annotations

from .models import EquipmentType, LogicalLink, Project, type_index

# Ports « cuivre » : on n'apparie pas un panneau RJ45 sur un SFP/fibre.
_COPPER = ("1000base-t", "100base-tx", "10000base-t", "2.5gbase-t",
           "5gbase-t", "rj45", "10gbase-t")


def _copper_ports(t: EquipmentType) -> list[str]:
    names: list[str] = []
    for p in t.ports:
        kind = (p.type or "").lower()
        if kind in _COPPER or kind.startswith("1000base-t") \
                or kind.startswith("100base-t"):
            names.append(p.name)
        elif kind == "rj45":
            names.append(p.name)
    if names:
        return names
    # Panneau sans type de port renseigné : on prend tous les noms.
    if t.category == "patch-panel":
        return [p.name for p in t.ports]
    return []


def _existing_pairs(project: Project, a: str, b: str) -> set[tuple[str, str]]:
    """(port_panneau, port_switch) déjà liés entre a et b (dans les 2 sens)."""
    seen: set[tuple[str, str]] = set()
    for link in project.logical.links:
        fa, ta = link.from_.equipment_id, link.to.equipment_id
        if {fa, ta} != {a, b}:
            continue
        if fa == a:
            seen.add((link.from_.port, link.to.port))
        else:
            seen.add((link.to.port, link.from_.port))
    return seen


def pair_panel_switch(project: Project, panel_id: str, switch_id: str,
                      media: str = "cuivre-cat6a",
                      kind: str = "access") -> dict:
    """Crée les liens manquants panneau → switch. Mutates ``project``.

    Retourne ``{created, skipped, total, message}``. Lève ``ValueError``
    (message français) si les ids sont inconnus ou les rôles incorrects.
    """
    types = type_index(project)
    items = {i.id: (r, i) for r in project.racks for i in r.items}
    if panel_id not in items:
        raise ValueError(f"Équipement inconnu : « {panel_id} »")
    if switch_id not in items:
        raise ValueError(f"Équipement inconnu : « {switch_id} »")
    if panel_id == switch_id:
        raise ValueError("Le panneau et le switch doivent être deux équipements distincts")
    _, panel = items[panel_id]
    _, switch = items[switch_id]
    tp, ts = types.get(panel.type_id), types.get(switch.type_id)
    if tp is None or ts is None:
        raise ValueError("Type d'équipement introuvable dans le catalogue")
    if tp.category != "patch-panel":
        raise ValueError(
            f"« {panel.meta.hostname or tp.model} » n'est pas un panneau de brassage")
    if ts.category != "switch":
        raise ValueError(
            f"« {switch.meta.hostname or ts.model} » n'est pas un switch")
    panel_ports = _copper_ports(tp)
    switch_ports = _copper_ports(ts)
    if not panel_ports:
        raise ValueError("Ce panneau n'a aucun port déclaré dans le catalogue")
    if not switch_ports:
        raise ValueError("Ce switch n'a aucun port cuivre déclaré dans le catalogue")
    already = _existing_pairs(project, panel_id, switch_id)
    created = 0
    skipped = 0
    n = min(len(panel_ports), len(switch_ports))
    for i in range(n):
        pp, sp = panel_ports[i], switch_ports[i]
        if (pp, sp) in already:
            skipped += 1
            continue
        lid = f"lnk-pair-{panel_id}-{i + 1:02d}"
        # Id unique même si on ré-apparie après suppression partielle.
        existing_ids = {lk.id for lk in project.logical.links}
        k = i + 1
        while lid in existing_ids:
            k += 1
            lid = f"lnk-pair-{panel_id}-{k:02d}"
        project.logical.links.append(LogicalLink.model_validate({
            "id": lid,
            "from": {"equipment_id": panel_id, "port": pp},
            "to": {"equipment_id": switch_id, "port": sp},
            "kind": kind,
            "media": media,
            "label": "",
        }))
        created += 1
    leftover = max(0, len(panel_ports) - len(switch_ports))
    msg = (f"{created} cordon(s) créé(s)"
           + (f", {skipped} déjà en place" if skipped else "")
           + (f" — {leftover} port(s) du panneau sans port cuivre libre "
              f"côté switch" if leftover else ""))
    return {
        "created": created,
        "skipped": skipped,
        "total": n,
        "leftover": leftover,
        "message": msg,
    }
