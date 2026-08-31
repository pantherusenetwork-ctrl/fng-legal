"""Modèle de données RackForgePrime — source de vérité JSON.

Le moteur de placement vit ici : toute position est un entier de U
(``position_u`` = U le plus bas occupé), les chevauchements et les
dépassements de baie sont refusés à la validation. Le frontend applique
les mêmes règles pour l'ergonomie, mais c'est ce module qui fait autorité.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# 1U normalisé EIA-310 : 1,75 pouce = 44,45 mm.
U_MM = 44.45

SCHEMA_VERSION = 1

Category = Literal[
    "switch",
    "firewall",
    "patch-panel",
    "ups",
    "server",
    "blank",       # obturateur
    "cable-mgmt",  # passe-câbles
    "router",
    "other",
]


class Port(BaseModel):
    name: str
    type: str = "1000base-t"


class EquipmentType(BaseModel):
    """Type d'équipement du catalogue (partagé entre projets)."""

    id: str
    vendor: str
    model: str
    category: Category = "other"
    u_height: int = Field(ge=1, le=12)
    power_w: float = 0
    ports: list[Port] = []
    # Couleur de rôle utilisée par le placeholder quand faceplate_svg est absent.
    color: str = "#64748b"
    # SVG officiel constructeur (inline) — None => placeholder fidèle à l'échelle U.
    faceplate_svg: Optional[str] = None
    # Image raster (PNG/JPEG) en data URI — « Remplacer par image officielle ».
    faceplate_image: Optional[str] = None

    @field_validator("faceplate_image")
    @classmethod
    def _image_is_data_uri(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("data:image/"):
            raise ValueError(
                "faceplate_image doit être un data URI (data:image/…)"
            )
        return v


class PortUsage(BaseModel):
    """Une ligne de brassage : alimente le tableau généré."""

    port: str
    outlet: str = ""  # prise murale
    vlan: str = ""
    usage: str = ""
    etat: str = ""    # "" (non renseigné) | up | down | reserve


class ItemMeta(BaseModel):
    hostname: str = ""
    role: str = ""
    vlan: str = ""
    wall_outlet: str = ""
    port_usage: list[PortUsage] = []
    serial: str = ""
    notes: str = ""
    mgmt_ip: str = ""   # IP de management — l'attente pro n°1 (Packet Pushers)
    asset: str = ""     # asset tag / n° d'inventaire


class RackItem(BaseModel):
    """Équipement posé dans une baie. La hauteur vient du type, jamais d'ici."""

    id: str
    type_id: str
    position_u: int = Field(ge=1)  # U le plus bas occupé
    face: Literal["front", "rear"] = "front"
    meta: ItemMeta = ItemMeta()


class Rack(BaseModel):
    id: str
    name: str
    u_height: int = Field(default=42, ge=1, le=60)
    width_inches: int = 19
    location: str = ""
    desc_units: bool = False  # False = U1 en bas (défaut datacenter)
    notes: str = ""
    items: list[RackItem] = []


class Vlan(BaseModel):
    vid: int = Field(ge=1, le=4094)
    name: str
    color: str = "#22d3ee"


class LinkEnd(BaseModel):
    equipment_id: str
    port: str = ""


class LogicalLink(BaseModel):
    id: str
    from_: LinkEnd = Field(alias="from")
    to: LinkEnd
    kind: Literal["access", "trunk", "uplink", "ha", "other"] = "other"
    vlans: list[int] = []
    label: str = ""
    media: str = ""

    model_config = {"populate_by_name": True}


class Position(BaseModel):
    """Position d'un nœud sur le schéma logique (px, grille libre).

    NaN/Infinity refusés : json.loads les accepte, et une seule valeur
    non finie fait planter la conversion svglib de l'export PDF.
    """
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class Logical(BaseModel):
    vlans: list[Vlan] = []
    links: list[LogicalLink] = []
    # Positions des nœuds posées à la main ; un équipement absent d'ici est
    # placé par l'auto-layout en couches (firewall en haut, serveurs en bas).
    positions: dict[str, Position] = {}


class Project(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    name: str
    created: str = ""
    racks: list[Rack] = []
    # Types custom locaux au projet (imports d'images, datasheets…).
    equipment_types: list[EquipmentType] = []
    logical: Logical = Logical()

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, v: int) -> int:
        if v > SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {v} inconnu (max supporté : {SCHEMA_VERSION})"
            )
        return v

    @model_validator(mode="after")
    def _validate_placement(self) -> "Project":
        errors = validate_placement(self, type_index(self))
        if errors:
            raise ValueError(" ; ".join(errors))
        return self


# ---------------------------------------------------------------------------
# Moteur de placement — le cœur : snap U, collisions, bornes de baie.
# ---------------------------------------------------------------------------

def type_index(project: Project, extra_types: list[EquipmentType] | None = None
               ) -> dict[str, EquipmentType]:
    """Index id -> type : catalogue intégré + types custom du projet.

    Les images officielles du workspace sont appliquées ici aussi : l'export
    SVG/PDF montre les mêmes faceplates que l'écran.
    """
    # Imports locaux pour éviter le cycle models <-> catalog.
    from .catalog import BUILTIN_TYPES
    from .catalog_images import apply_official_images
    from .catalog_packs import merged_catalog

    index = {t.id: t
             for t in apply_official_images(merged_catalog(BUILTIN_TYPES))}
    for t in project.equipment_types:
        index[t.id] = t
    for t in extra_types or []:
        index[t.id] = t
    return index


def item_span(item: RackItem, types: dict[str, EquipmentType]) -> range:
    """U occupés par un item : [position_u, position_u + u_height)."""
    t = types[item.type_id]
    return range(item.position_u, item.position_u + t.u_height)


def validate_placement(project: Project, types: dict[str, EquipmentType]
                       ) -> list[str]:
    """Retourne la liste des violations (vide si le projet est valide)."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    for rack in project.racks:
        occupied: dict[int, str] = {}  # U -> item id
        for item in rack.items:
            if item.id in seen_ids:
                errors.append(f"id d'équipement dupliqué : {item.id}")
            seen_ids.add(item.id)
            t = types.get(item.type_id)
            if t is None:
                errors.append(
                    f"{rack.name} / {item.id} : type inconnu « {item.type_id} »"
                )
                continue
            top = item.position_u + t.u_height - 1
            if top > rack.u_height:
                errors.append(
                    f"{rack.name} / {item.id} : dépasse la baie "
                    f"(U{item.position_u}–U{top} sur {rack.u_height}U)"
                )
                continue
            for u in item_span(item, types):
                if u in occupied:
                    errors.append(
                        f"{rack.name} : collision en U{u} entre "
                        f"{occupied[u]} et {item.id}"
                    )
                else:
                    occupied[u] = item.id
    return errors


def free_positions(rack: Rack, u_height_needed: int,
                   types: dict[str, EquipmentType],
                   ignore_item_id: str | None = None) -> list[int]:
    """Positions U valides pour poser un équipement de ``u_height_needed`` U.

    ``ignore_item_id`` permet de déplacer un item existant sans qu'il se
    bloque lui-même.
    """
    occupied: set[int] = set()
    for item in rack.items:
        if item.id == ignore_item_id:
            continue
        occupied.update(item_span(item, types))
    positions = []
    for pos in range(1, rack.u_height - u_height_needed + 2):
        if not any(u in occupied for u in range(pos, pos + u_height_needed)):
            positions.append(pos)
    return positions


def rack_stats(rack: Rack, types: dict[str, EquipmentType]) -> dict:
    """Stats live : U occupés / libres, puissance cumulée."""
    used = sum(types[i.type_id].u_height for i in rack.items
               if i.type_id in types)
    power = sum(types[i.type_id].power_w for i in rack.items
                if i.type_id in types)
    return {
        "u_used": used,
        "u_free": rack.u_height - used,
        "power_w": round(power, 1),
        "items": len(rack.items),
    }


def patch_table(project: Project, types: dict[str, EquipmentType]
                ) -> list[dict]:
    """Tableau de brassage : baie / U / équipement / port / prise / VLAN / usage.

    Trié baie puis U décroissant (lecture haut de baie vers bas), puis port.
    Aucun dessin ne remplace ce tableau.
    """
    rows: list[dict] = []
    for rack in project.racks:
        for item in sorted(rack.items, key=lambda i: -i.position_u):
            t = types.get(item.type_id)
            label = item.meta.hostname or (f"{t.vendor} {t.model}" if t else item.type_id)
            usages = item.meta.port_usage or [PortUsage(port="—")]
            for pu in usages:
                rows.append({
                    "rack": rack.name,
                    "u": item.position_u,
                    "equipment": label,
                    "port": pu.port,
                    "outlet": pu.outlet or item.meta.wall_outlet,
                    "vlan": pu.vlan or item.meta.vlan,
                    "usage": pu.usage,
                    "etat": pu.etat,
                })
    return rows


def patch_table_csv(project: Project, types: dict[str, EquipmentType]) -> str:
    """Tableau de brassage en CSV (séparateur « ; », convention FR/Excel)."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Baie", "U", "Équipement", "Port", "Prise murale",
                     "VLAN", "Usage", "État"])
    for r in patch_table(project, types):
        writer.writerow([r["rack"], f"U{r['u']}", r["equipment"], r["port"],
                         r["outlet"], r["vlan"], r["usage"], r["etat"]])
    return buf.getvalue()
