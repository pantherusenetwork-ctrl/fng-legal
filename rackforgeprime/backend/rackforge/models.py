"""Modèle de données RackForgePrime — source de vérité JSON.

Le moteur de placement vit ici : toute position est un entier de U
(``position_u`` = U le plus bas occupé), les chevauchements et les
dépassements de baie sont refusés à la validation. Le frontend applique
les mêmes règles pour l'ergonomie, mais c'est ce module qui fait autorité.
"""

from __future__ import annotations

import os
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
    # Largeur physique réelle en mm — un boîtier compact (FortiGate 60,
    # box opérateur…) s'affiche alors à SA largeur dans la baie, comme
    # dans la réalité, au lieu d'être cadré sur les 19 pouces.
    # None = pleine largeur rack (équipement rackable standard).
    width_mm: Optional[float] = Field(default=None, gt=0, le=483)
    # Budget PoE total délivrable par le switch (W, datasheet). None =
    # pas de PoE ou inconnu — le budget cumulé le signale alors comme
    # « à renseigner » au lieu d'inventer une valeur.
    poe_budget_w: Optional[float] = Field(default=None, ge=0, le=5000)
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
    # Puissance PoE tirée par l'équipement branché (W) — alimente le
    # budget PoE cumulé du switch (0 = pas de PoE / non renseigné).
    poe_w: float = Field(default=0, ge=0, le=100)


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
    # Budget PoE saisi pour CET équipement (W) — prime sur celui du type
    # (utile pour un switch du catalogue dont le budget n'est pas connu).
    poe_budget_w: Optional[float] = Field(default=None, ge=0, le=5000)


class RackItem(BaseModel):
    """Équipement posé dans une baie. La hauteur vient du type, jamais d'ici."""

    id: str
    type_id: str
    position_u: int = Field(ge=1)  # U le plus bas occupé
    # Position horizontale RÉELLE en mm (bord gauche dans le U, référence
    # façade 19" = 482,6 mm). Permet de poser PLUSIEURS boîtiers compacts
    # côte à côte dans le même U (deux FGT 60F = 2×216 mm : ça tient),
    # comme dans la vraie baie. None = équipement pleine largeur/centré.
    position_x_mm: Optional[float] = Field(default=None, ge=0, lt=482.6)
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


class Annotation(BaseModel):
    """Dessin libre sur le schéma logique (esprit draw.io / Visio) :
    texte posé, zone encadrée, flèche. Rendu par le backend — présent
    dans TOUS les exports (SVG, PDF, PNG), pas un artefact d'écran."""
    id: str
    kind: Literal["texte", "zone", "fleche", "ligne", "ellipse", "icone"]
    # icone : nom de la forme de catalogue/formes/ ; x2 = taille (px).
    icon: str = ""
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    # zone : coin opposé ; flèche : pointe d'arrivée.
    x2: float = Field(default=0.0, allow_inf_nan=False)
    y2: float = Field(default=0.0, allow_inf_nan=False)
    text: str = ""
    color: str = ""   # vide = couleur du thème au rendu


class Logical(BaseModel):
    vlans: list[Vlan] = []
    links: list[LogicalLink] = []
    # Positions des nœuds posées à la main ; un équipement absent d'ici est
    # placé par l'auto-layout en couches (firewall en haut, serveurs en bas).
    positions: dict[str, Position] = {}
    annotations: list[Annotation] = []


class Diagram(BaseModel):
    """Page de diagramme libre (esprit Visio/draw.io) : uniquement du
    dessin — texte, zones, flèches, lignes, ellipses."""
    annotations: list[Annotation] = []


class Revision(BaseModel):
    """Ligne du suivi des révisions du DAT (pratique doc d'ingénierie :
    indice A, B, C… + date + objet de la modification)."""
    indice: str
    date: str = ""
    objet: str = ""


class Flow(BaseModel):
    """Ligne de la matrice de flux (pratique DAT : qui parle à qui, sur
    quel port, et ce que le pare-feu en fait)."""
    id: str
    src: str = ""        # zone, VLAN ou hôte source (ex : « VLAN 20 USERS »)
    dst: str = ""        # zone, VLAN ou hôte destination
    proto: str = ""      # tcp / udp / icmp / any
    ports: str = ""      # « 443, 8443 » — libre, tel que documenté
    action: Literal["", "allow", "deny", "nat"] = ""
    via: str = ""        # équipement qui filtre (hostname)
    comment: str = ""


class PlanRack(BaseModel):
    """Une baie posée sur le plan d'une salle (px du plan, rotation)."""
    rack_id: str
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    rotation: Literal[0, 90, 180, 270] = 0


class PlanPoint(BaseModel):
    """Élément posé sur le plan hors baie : borne Wi-Fi (avec rayon de
    couverture), prise murale, caméra, équipement libre, note."""
    id: str
    kind: Literal["ap", "prise", "camera", "equipement", "note"] = "note"
    label: str = ""
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    # Rayon de couverture (px du plan) — bornes Wi-Fi ; 0 = pas de cercle.
    radius: float = Field(default=0, ge=0, allow_inf_nan=False)
    # Équipement de baie relié (id d'item) : la ligne se dessine sur le plan.
    equipment_id: str = ""
    color: str = ""


class Room(BaseModel):
    """Salle : porte le plan d'étage (image) et ce qui est posé dessus."""
    id: str
    name: str
    # Image du plan (data URI PNG/JPG) — fond du dessin, opacité réglable.
    plan_image: Optional[str] = None
    plan_opacity: float = Field(default=0.6, ge=0, le=1)
    # Taille du plan en px (repère de tout ce qui est posé dessus).
    plan_w: float = Field(default=1200, gt=0, le=20000)
    plan_h: float = Field(default=800, gt=0, le=20000)
    # Échelle : millimètres réels par pixel de plan (emprise des baies).
    mm_per_px: float = Field(default=10, gt=0, le=1000)
    racks: list[PlanRack] = []
    points: list[PlanPoint] = []

    @field_validator("plan_image")
    @classmethod
    def _plan_is_data_uri(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("data:image/"):
            raise ValueError("plan_image doit être un data URI (data:image/…)")
        return v


class Building(BaseModel):
    id: str
    name: str
    rooms: list[Room] = []


class Site(BaseModel):
    """Ville / site : le premier niveau du parcours ville → bâtiment →
    salle → baies."""
    id: str
    name: str
    address: str = ""
    buildings: list[Building] = []


class Project(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    name: str
    created: str = ""
    racks: list[Rack] = []
    # Types custom locaux au projet (imports d'images, datasheets…).
    equipment_types: list[EquipmentType] = []
    logical: Logical = Logical()
    diagram: Diagram = Diagram()
    # Version du projet (V1, V2…) + historique (cartouche + page
    # « Suivi des versions » du dossier).
    revision: str = "1"
    revisions: list[Revision] = []
    # Hiérarchie de site (ville → bâtiment → salle) et plans d'étage.
    sites: list[Site] = []
    # Matrice de flux (page du dossier + CSV).
    flows: list[Flow] = []

    @model_validator(mode="after")
    def _validate_plans(self) -> "Project":
        """Une baie posée sur un plan doit exister, et une seule fois."""
        rack_ids = {r.id for r in self.racks}
        item_ids = {i.id for r in self.racks for i in r.items}
        seen: set[str] = set()
        errors: list[str] = []
        for site in self.sites:
            for b in site.buildings:
                for room in b.rooms:
                    for pr in room.racks:
                        if pr.rack_id not in rack_ids:
                            errors.append(f"{room.name} : baie inconnue « {pr.rack_id} » sur le plan")
                        elif pr.rack_id in seen:
                            errors.append(f"{room.name} : la baie « {pr.rack_id} » est posée sur deux plans")
                        seen.add(pr.rack_id)
                    for pt in room.points:
                        if pt.equipment_id and pt.equipment_id not in item_ids:
                            errors.append(f"{room.name} / {pt.label or pt.id} : équipement inconnu « {pt.equipment_id} »")
        if errors:
            raise ValueError(" ; ".join(errors))
        return self

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

def _catalog_signature() -> tuple:
    """Empreinte du catalogue sur disque (packs + images) : un fichier
    ajouté, retiré ou modifié change la signature → le cache se recharge.
    ~1 200 stat() ≈ 20 ms, contre 2 s pour tout relire."""
    from .catalog_images import images_dir
    from .catalog_packs import packs_dir

    sig: list = []
    d = packs_dir()
    if d is not None:
        for p in sorted(d.glob("*.json")):
            st = p.stat()
            sig.append((p.name, st.st_mtime_ns, st.st_size))
    di = images_dir()
    if di is not None:
        n, total = 0, 0
        with os.scandir(di) as it:
            for e in it:
                if e.is_file():
                    n += 1
                    total += e.stat().st_mtime_ns
        sig.append(("images", n, total))
    return tuple(sig)


_BASE_CACHE: dict = {"sig": None, "index": {}}


def base_type_index() -> dict[str, EquipmentType]:
    """Index du catalogue (intégré + packs + images officielles), EN CACHE.

    Relire 1 162 types et 1 162 images à CHAQUE requête coûtait 2 s —
    ouvrir un projet, l'enregistrer, rendre une vue : tout attendait.
    Le cache est invalidé dès qu'un fichier du catalogue change."""
    # Imports locaux pour éviter le cycle models <-> catalog.
    from .catalog import BUILTIN_TYPES
    from .catalog_images import apply_official_images
    from .catalog_packs import merged_catalog

    sig = _catalog_signature()
    if _BASE_CACHE["sig"] != sig:
        _BASE_CACHE["index"] = {
            t.id: t for t in apply_official_images(merged_catalog(BUILTIN_TYPES))}
        _BASE_CACHE["sig"] = sig
    return _BASE_CACHE["index"]


def type_index(project: Project, extra_types: list[EquipmentType] | None = None
               ) -> dict[str, EquipmentType]:
    """Index id -> type : catalogue intégré + types custom du projet.

    Les images officielles du workspace sont appliquées ici aussi : l'export
    SVG/PDF montre les mêmes faceplates que l'écran.
    """
    index = dict(base_type_index())
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
        occupied: dict[int, list[RackItem]] = {}  # U -> items présents
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
                occupied.setdefault(u, []).append(item)
        # Un U partagé n'est PAS une collision si tout le monde y tient EN
        # LARGEUR : chaque cohabitant est un boîtier compact (width_mm)
        # positionné (position_x_mm), et les empreintes ne se chevauchent
        # pas dans les 482,6 mm de la façade 19".
        for u, its in sorted(occupied.items()):
            if len(its) < 2:
                continue
            solid = [i for i in its
                     if not (types[i.type_id].width_mm
                             and i.position_x_mm is not None)]
            if solid:
                errors.append(
                    f"{rack.name} : collision en U{u} entre "
                    f"{' et '.join(i.id for i in its)} — pour cohabiter, "
                    f"chaque équipement doit avoir une largeur réelle "
                    f"(width_mm) et une position (position_x_mm)"
                )
                continue
            spans = sorted((i.position_x_mm,
                            i.position_x_mm + types[i.type_id].width_mm,
                            i.id) for i in its)
            for (a0, a1, aid), (b0, b1, bid) in zip(spans, spans[1:]):
                if b0 < a1 - 0.01:
                    errors.append(
                        f"{rack.name} : chevauchement en U{u} entre {aid} "
                        f"et {bid} ({a1 - b0:.0f} mm de recouvrement)"
                    )
            if spans and spans[-1][1] > 482.6 + 0.01:
                errors.append(
                    f"{rack.name} : U{u} déborde de la façade 19" + '"'
                    f" ({spans[-1][1]:.0f} mm sur 482,6)"
                )
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
    # Ensemble des U réellement occupés : deux compacts côte à côte dans
    # le même U ne comptent qu'une fois.
    used = len({u for i in rack.items if i.type_id in types
                for u in item_span(i, types)})
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
