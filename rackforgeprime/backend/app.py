"""Serveur local RackForgePrime — FastAPI.

Sert l'UI (frontend statique) et l'API JSON. Tout tourne en local :
aucun appel sortant, aucune dépendance cloud. Le backend est l'autorité
de validation : un projet qui viole le snap U ou chevauche deux
équipements est refusé avec un message précis (HTTP 422).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from rackforge import backup, storage
from rackforge.catalog import BUILTIN_TYPES, ROLE_COLORS
from rackforge.catalog_images import (apply_official_images, image_data_uri,
                                      official_image_path)
from rackforge.catalog_packs import merged_catalog
from rackforge.importers import import_netbox_yaml, parse_datasheet_pdf
from rackforge.models import (Project, patch_table, patch_table_csv,
                              rack_stats, type_index)
from rackforge.drawio_export import render_drawio
from rackforge.energy import poe_report
from rackforge.flows import flows_csv, propose_flows
from rackforge.formes import forme_svg, list_formes
from rackforge.svg_plan import render_plan_svg
from rackforge.vsdx_export import render_vsdx
from rackforge.pdf_export import (render_labels_pdf,
                                  render_project_dossier_pdf,
                                  render_project_pdf)
from rackforge.svg_export import render_project_svg
from rackforge.svg_logical import (LOGICAL_LAYERS, render_diagram_svg,
                                   render_logical_svg)

# Packagé (PyInstaller) : le frontend est embarqué sous sys._MEIPASS.
if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(getattr(sys, "_MEIPASS")) / "frontend"
else:
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Version de l'application — à mettre à jour en même temps que le badge
# affiché dans l'UI (frontend/index.html, #brand-version).
VERSION = "1.5.3"

app = FastAPI(title="RackForgePrime", version=VERSION, docs_url="/api/docs")

# Un thème ou un rendu inconnu est refusé (422) au lieu d'être rabattu en
# silence sur le défaut — l'appelant sait tout de suite qu'il s'est trompé.
Theme = Literal["sombre", "clair", "kaki", "nuit"]
Rendu = Literal["photos", "dessin"]
# Face regardée : avant (défaut) ou arrière — même projet, vue dérivée.
Face = Literal["front", "rear"]


def _parse_layers(layers: str | None):
    """``layers=zones,liens`` -> sous-ensemble validé, None = tout."""
    if layers is None or layers == "":
        return None
    asked = {p.strip() for p in layers.split(",") if p.strip()}
    unknown = asked - set(LOGICAL_LAYERS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=[f"Calque inconnu : {', '.join(sorted(unknown))} "
                    f"(attendus : {', '.join(LOGICAL_LAYERS)})"])
    return asked


def _check_rack(project: Project, rack: str | None) -> str | None:
    """``rack=<id>`` : la baie doit exister — 422 lisible sinon."""
    if not rack:
        return None
    if all(r.id != rack for r in project.racks):
        raise HTTPException(status_code=422,
                            detail=[f"Baie inconnue : {rack}"])
    return rack


def _parse_project(payload: dict) -> Project:
    """Valide un projet reçu du frontend ; 422 lisible en français sinon."""
    try:
        return Project.model_validate(payload)
    except ValidationError as exc:
        # Messages du moteur de placement, débarrassés du préfixe pydantic
        # anglais, et préfixés du chemin du champ fautif (sinon impossible
        # de savoir QUEL équipement pose problème).
        msgs = []
        for e in exc.errors():
            msg = e.get("msg", str(e))
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            loc = ".".join(str(p) for p in e.get("loc", ()))
            msgs.append(f"{loc} : {msg}" if loc else msg)
        raise HTTPException(status_code=422, detail=msgs)


# --- Vie de l'application de bureau ----------------------------------------
# La fenêtre envoie un battement toutes les 5 s ; run.py arrête le serveur
# quand la fenêtre a disparu (« bye » au pagehide, ou silence prolongé).
# Sans ça, fermer la fenêtre laissait un processus fantôme sur le port.
app.state.last_ping = 0.0
app.state.bye_at = 0.0
# Fenêtres vivantes : id de client -> dernier battement. Fermer UNE
# fenêtre n'éteint l'app que si c'était la dernière.
app.state.clients = {}


@app.get("/api/ping")
def ping(c: str = "") -> dict:
    now = time.time()
    app.state.last_ping = now
    if c:
        app.state.clients[c] = now
    # Un battement quelconque annule un « bye » SEULEMENT s'il reste
    # une fenêtre connue vivante (ou si les clients ne s'identifient pas).
    if not c or app.state.clients:
        app.state.bye_at = 0.0
    return {"ok": True, "version": VERSION, "app": "RackForgePrime"}


@app.post("/api/bye")
async def bye(request: Request) -> dict:
    """Une fenêtre se ferme (pagehide) : on la retire. S'il n'en reste
    aucune, run.py arrête le serveur après un court délai (un
    rechargement F5 renvoie un ping et annule)."""
    cid = (await request.body()).decode("utf-8", errors="replace").strip()
    app.state.clients.pop(cid, None)
    if not app.state.clients:
        app.state.bye_at = time.time()
    return {"ok": True, "restantes": len(app.state.clients)}


# --- Catalogue --------------------------------------------------------------

@app.get("/api/catalog")
def get_catalog() -> dict:
    """Types intégrés + packs constructeurs. Les images sont en
    CHARGEMENT DIFFÉRÉ (``has_image`` + /api/catalog/image/{id}) : un
    catalogue de 1 000+ types en data URIs pèserait des dizaines de Mo."""
    out = []
    for t in merged_catalog(BUILTIN_TYPES):
        d = t.model_dump()
        d["has_image"] = bool(t.faceplate_image or t.faceplate_svg
                              or official_image_path(t.id))
        out.append(d)
    return {"types": out, "role_colors": ROLE_COLORS}


@app.get("/api/catalog/image/{type_id}")
def get_catalog_image(type_id: str) -> dict:
    """Image officielle d'un type, à la demande (data URI ou null)."""
    return {"id": type_id, "image": image_data_uri(type_id)}


# --- Formes vectorielles (icônes réseau du Diagramme) -----------------------

@app.get("/api/formes")
def get_formes() -> dict:
    """Noms des formes disponibles (catalogue/formes/*.svg)."""
    return {"formes": list_formes()}


@app.get("/api/formes/svg/{name}")
def get_forme_svg(name: str, color: str = "#8b95a3") -> Response:
    """SVG d'une forme, currentColor résolu (aperçus de la palette)."""
    svg = forme_svg(name, color)
    if svg is None:
        raise HTTPException(status_code=404, detail="Forme inconnue")
    return Response(content=svg, media_type="image/svg+xml")


# --- Validation / stats / brassage -----------------------------------------

@app.post("/api/validate")
def validate(payload: dict) -> dict:
    project = _parse_project(payload)
    types = type_index(project)
    return {
        "valid": True,
        "stats": {r.id: rack_stats(r, types) for r in project.racks},
    }


@app.post("/api/patch-table")
def get_patch_table(payload: dict) -> dict:
    project = _parse_project(payload)
    return {"rows": patch_table(project, type_index(project))}


@app.post("/api/patch-table.csv")
def get_patch_table_csv(payload: dict) -> Response:
    project = _parse_project(payload)
    csv_text = patch_table_csv(project, type_index(project))
    return Response(
        # BOM UTF-8 : Excel FR ouvre le fichier avec les accents corrects.
        content="\ufeff" + csv_text, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}-brassage.csv"'},
    )


# --- Imports de types (YAML NetBox, PDF datasheet) --------------------------

@app.post("/api/import/devicetype-yaml")
async def import_devicetype_yaml(file: UploadFile = File(...)) -> dict:
    """YAML NetBox devicetype-library -> type prêt à ajouter à la palette."""
    try:
        text = (await file.read()).decode("utf-8", errors="replace")
        eq_type = import_netbox_yaml(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"type": eq_type.model_dump()}


@app.post("/api/import/datasheet")
async def import_datasheet(file: UploadFile = File(...)) -> dict:
    """PDF datasheet -> proposition de type (l'utilisateur valide dans l'UI)."""
    try:
        return parse_datasheet_pdf(await file.read(), file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# --- Exports (le JSON reste la source de vérité) ----------------------------

@app.post("/api/export/svg")
def export_svg(payload: dict,
               view: Literal["physical", "logical", "diagram",
                             "plan"] = "physical",
               theme: Theme = "sombre", rendu: Rendu = "photos",
               layers: str | None = None, face: Face = "front",
               room: str | None = None, rack: str | None = None) -> Response:
    """``view=physical`` : élévation ; ``logical`` : VLANs/liens
    (``rack=<id>`` : vue logique de cette seule baie) ;
    ``diagram`` : page de dessin libre ; ``plan`` : plan d'étage d'une
    salle (``room`` = id de la salle, vide = la première).
    ``theme`` : sombre/clair/kaki/nuit. ``rendu`` : photos ou dessin.
    ``layers`` : calques logiques à dessiner (csv), vide = tous.
    ``face`` : front (défaut) ou rear — la vue arrière de l'élévation."""
    project = _parse_project(payload)
    if view == "logical":
        svg = render_logical_svg(project, theme=theme,
                                 layers=_parse_layers(layers),
                                 rack=_check_rack(project, rack))
    elif view == "diagram":
        svg = render_diagram_svg(project, theme=theme)
    elif view == "plan":
        svg = render_plan_svg(project, room or None, theme=theme)
    else:
        svg = render_project_svg(project, theme=theme, rendu=rendu,
                                 face=face)
    suffix = {"logical": "-logique", "diagram": "-diagramme",
              "plan": "-plan"}.get(view, "")
    if view == "physical" and face == "rear":
        suffix = "-arriere"
    if view == "logical" and rack:
        suffix += "-" + rack
    return Response(
        content=svg, media_type="image/svg+xml",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}{suffix}.svg"'},
    )


@app.post("/api/export/pdf")
def export_pdf(payload: dict,
               view: Literal["physical", "logical", "diagram", "plan",
                             "dossier"] = "physical",
               theme: Theme = "sombre", rendu: Rendu = "photos",
               layers: str | None = None, face: Face = "front",
               room: str | None = None, rack: str | None = None) -> Response:
    """``view`` : physical, logical, diagram, plan, ou ``dossier``
    (livrable DAT complet : élévation + logique + plans + brassage +
    flux + PoE + nomenclature, cartouche).
    ``theme`` : sombre/clair/kaki/nuit. ``rendu`` : photos ou dessin."""
    project = _parse_project(payload)
    if view == "dossier":
        pdf = render_project_dossier_pdf(project, theme=theme, rendu=rendu)
        suffix = "-dossier"
    else:
        pdf = render_project_pdf(project, view=view, theme=theme, rendu=rendu,
                                 layers=_parse_layers(layers), face=face,
                                 room=room or None,
                                 rack=_check_rack(project, rack))
        suffix = {"logical": "-logique", "diagram": "-diagramme",
                  "plan": "-plan"}.get(view, "")
        if view == "physical" and face == "rear":
            suffix = "-arriere"
        if view == "logical" and rack:
            suffix += "-" + rack
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}{suffix}.pdf"'},
    )


@app.post("/api/export/vsdx")
def export_vsdx(payload: dict) -> Response:
    """Fichier Visio .vsdx (2 pages : élévation + logique), construit
    en local d'après la spécification OPC/Visio 2012."""
    project = _parse_project(payload)
    data = render_vsdx(project)
    return Response(
        content=data,
        media_type="application/vnd.ms-visio.drawing.main+xml",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}.vsdx"'},
    )


# --- Matrice de flux et budget PoE -----------------------------------------

@app.post("/api/flows/propose")
def flows_propose(payload: dict) -> dict:
    """Lignes de flux PROPOSÉES d'après les VLANs, le pare-feu et le
    WAN documentés — action vide : l'ingénieur décide, jamais l'outil."""
    project = _parse_project(payload)
    return {"flows": [f.model_dump()
                      for f in propose_flows(project, type_index(project))]}


@app.post("/api/flows.csv")
def flows_csv_export(payload: dict) -> Response:
    project = _parse_project(payload)
    return Response(
        content="﻿" + flows_csv(project),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}-flux.csv"'},
    )


@app.post("/api/poe")
def poe(payload: dict) -> dict:
    """Budget PoE cumulé par switch : budget (datasheet ou saisi), tiré,
    ports, taux, état (ok / alerte ≥ 80 % / dépassement / à renseigner)."""
    project = _parse_project(payload)
    return {"rows": poe_report(project, type_index(project))}


@app.post("/api/export/drawio")
def export_drawio(payload: dict) -> Response:
    """Fichier .drawio rééditable (2 pages : élévation + logique)."""
    project = _parse_project(payload)
    xml = render_drawio(project)
    return Response(
        content=xml, media_type="application/vnd.jgraph.mxfile",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}.drawio"'},
    )


@app.post("/api/export/etiquettes")
def export_labels(payload: dict) -> Response:
    """Planche d'étiquettes de brassage (PDF A4, identifiants TIA-606)."""
    project = _parse_project(payload)
    pdf = render_labels_pdf(project)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}-etiquettes.pdf"'},
    )


# --- Projets locaux ---------------------------------------------------------

@app.get("/api/projects")
def projects_list() -> dict:
    return {"projects": storage.list_projects()}


@app.get("/api/projects/{name}")
def project_load(name: str) -> dict:
    try:
        return storage.load_project(name).model_dump(by_alias=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.put("/api/projects/{name}")
def project_save(name: str, payload: dict) -> dict:
    project = _parse_project(payload)
    try:
        path = storage.save_project(name, project)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"saved": True, "path": str(path)}


@app.get("/api/backup/config")
def backup_config() -> dict:
    """Pré-remplissage de l'UI : dossier de l'app + dernier dossier libre."""
    return {"dossier_app": str(backup.local_dir()),
            "dernier_dossier": backup.get_last_custom_dir()}


@app.post("/api/backup")
def backup_run(payload: dict):
    """Sauvegarde — l'utilisateur choisit quoi, en quel format, où.

    dest « telecharger » renvoie le fichier au navigateur (« Enregistrer
    sous » : l'utilisateur choisit lui-même l'endroit) ; les autres
    destinations écrivent côté serveur (dossier de l'app, chemin libre)."""
    scope = payload.get("scope", "projet")
    fmt = payload.get("format", "zip")
    dest = payload.get("dest", "pc")
    if scope not in ("projet", "projets", "workspace"):
        raise HTTPException(422, "Portée invalide : projet, projets ou workspace")
    if fmt not in ("json", "zip"):
        raise HTTPException(422, "Format invalide : json ou zip")
    if dest not in ("pc", "dossier", "deux", "telecharger"):
        raise HTTPException(422,
                            "Destination invalide : pc, dossier, deux ou telecharger")
    try:
        if dest == "telecharger":
            name, data, mime = backup.make_archive(scope, fmt,
                                                   payload.get("project"))
            return Response(content=data, media_type=mime, headers={
                "Content-Disposition": f'attachment; filename="{name}"'})
        return backup.run_backup(scope, fmt, dest, payload.get("project"),
                                 str(payload.get("dir") or ""))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/api/backup/fichier")
async def backup_write_file(request: Request, dir: str, name: str) -> dict:
    """Dépose un export déjà généré (PDF, SVG, PNG, draw.io…) dans un
    dossier choisi — le corps de la requête est le fichier lui-même."""
    data = await request.body()
    if not data:
        raise HTTPException(422, "Fichier vide")
    try:
        return backup.write_file(dir, name, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except OSError as exc:
        raise HTTPException(502, f"Dossier injoignable : {dir} "
                                 f"({exc.__class__.__name__})")


# --- Frontend ---------------------------------------------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
