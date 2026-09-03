"""Budget PoE cumulé — par switch, jamais une estimation déguisée.

Le budget d'un switch (``EquipmentType.poe_budget_w``) vient de la
datasheet ; la puissance tirée est la somme des ``PortUsage.poe_w``
renseignés (ce que consomme réellement le téléphone, la borne, la
caméra branchée). Un switch sans budget connu est listé « à renseigner »
— on ne devine pas une valeur constructeur.
"""

from __future__ import annotations

import re

from .models import EquipmentType, Project

# Classes 802.3 : puissance max délivrée au port, pour le bouton
# « classe » de l'UI (l'utilisateur choisit, rien n'est déduit).
POE_CLASSES = {"af": 15.4, "at": 30.0, "bt-60": 60.0, "bt-90": 90.0}

_SEUIL_ALERTE = 0.8   # 80 % : le seuil d'alerte classique des NMS


def is_poe_type(t: EquipmentType) -> bool:
    """PoE déduit du nom (POE/FPOE/UPOE, -xxP/-xxU Cisco) — miroir de
    isPoE() côté frontend."""
    s = f"{t.model} {t.id}"
    if re.search(r"(^|[^a-z])(poe|fpoe|upoe)([^a-z]|$)", s, re.I):
        return True
    return t.vendor == "Cisco" and bool(re.search(r"-\d+(p|u)\b", t.model, re.I))


def poe_report(project: Project, types: dict[str, EquipmentType]
               ) -> list[dict]:
    """Une ligne par switch PoE (ou par équipement avec un budget posé) :
    baie, équipement, budget, tiré, ports PoE actifs, taux, état."""
    rows: list[dict] = []
    for rack in project.racks:
        for item in rack.items:
            t = types.get(item.type_id)
            if t is None:
                continue
            budget = (item.meta.poe_budget_w
                      if item.meta.poe_budget_w is not None
                      else t.poe_budget_w)
            drawn = sum(pu.poe_w for pu in item.meta.port_usage)
            if budget is None and not is_poe_type(t) and drawn == 0:
                continue
            n_ports = sum(1 for pu in item.meta.port_usage if pu.poe_w > 0)
            if budget:
                taux = drawn / budget
                etat = ("dépassement" if taux > 1 else
                        "alerte" if taux >= _SEUIL_ALERTE else "ok")
            else:
                taux = None
                etat = "budget à renseigner"
            rows.append({
                "rack": rack.name, "u": item.position_u,
                "equipment": item.meta.hostname or f"{t.vendor} {t.model}",
                "type_id": t.id,
                "budget_w": budget, "drawn_w": round(drawn, 1),
                "ports": n_ports,
                "taux": None if taux is None else round(100 * taux),
                "etat": etat,
            })
    return rows


def poe_rows(project: Project, types: dict[str, EquipmentType]
             ) -> list[list[str]]:
    """Lignes du tableau PDF."""
    out = []
    for r in poe_report(project, types):
        budget = f"{r['budget_w']:g} W" if r["budget_w"] else "à renseigner"
        taux = f"{r['taux']} %" if r["taux"] is not None else "—"
        out.append([r["rack"], f"U{r['u']}", r["equipment"], budget,
                    f"{r['drawn_w']:g} W", str(r["ports"]), taux, r["etat"]])
    return out
