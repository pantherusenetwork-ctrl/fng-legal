"""Serveur local RackForgePrime — FastAPI.

Sert l'UI (frontend statique) et l'API JSON. Tout tourne en local :
aucun appel sortant, aucune dépendance cloud. Le backend est l'autorité
de validation : un projet qui viole le snap U ou chevauche deux
équipements est refusé avec un message précis (HTTP 422).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from rackforge import storage
from rackforge.catalog import BUILTIN_TYPES, ROLE_COLORS
from rackforge.catalog_images import apply_official_images
from rackforge.catalog_packs import merged_catalog
from rackforge.importers import import_netbox_yaml, parse_datasheet_pdf
from rackforge.models import (Project, patch_table, patch_table_csv,
                              rack_stats, type_index)
from rackforge.drawio_export import render_drawio
from rackforge.pdf_export import (render_labels_pdf,
                                  render_project_dossier_pdf,
                                  render_project_pdf)
from rackforge.svg_export import render_project_svg
from rackforge.svg_logical import render_logical_svg

# Packagé (PyInstaller) : le frontend est embarqué sous sys._MEIPASS.
if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(getattr(sys, "_MEIPASS")) / "frontend"
else:
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Version de l'application — à mettre à jour en même temps que le badge
# affiché dans l'UI (frontend/index.html, #brand-version).
VERSION = "1.0.0"

app = FastAPI(title="RackForgePrime", version=VERSION, docs_url="/api/docs")

# Un thème ou un rendu inconnu est refusé (422) au lieu d'être rabattu en
# silence sur le défaut — l'appelant sait tout de suite qu'il s'est trompé.
Theme = Literal["sombre", "clair", "kaki", "nuit"]
Rendu = Literal["photos", "dessin"]


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


# --- Catalogue --------------------------------------------------------------

@app.get("/api/catalog")
def get_catalog() -> dict:
    """Types intégrés + packs constructeurs + images officielles du workspace."""
    types = apply_official_images(merged_catalog(BUILTIN_TYPES))
    return {
        "types": [t.model_dump() for t in types],
        "role_colors": ROLE_COLORS,
    }


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
def export_svg(payload: dict, view: Literal["physical", "logical"] = "physical",
               theme: Theme = "sombre", rendu: Rendu = "photos") -> Response:
    """``view=physical`` : élévation ; ``view=logical`` : VLANs/liens.
    ``theme`` : sombre/clair/kaki/nuit. ``rendu`` : photos ou dessin."""
    project = _parse_project(payload)
    svg = (render_logical_svg(project, theme=theme) if view == "logical"
           else render_project_svg(project, theme=theme, rendu=rendu))
    suffix = "-logique" if view == "logical" else ""
    return Response(
        content=svg, media_type="image/svg+xml",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}{suffix}.svg"'},
    )


@app.post("/api/export/pdf")
def export_pdf(payload: dict,
               view: Literal["physical", "logical", "dossier"] = "physical",
               theme: Theme = "sombre", rendu: Rendu = "photos") -> Response:
    """``view`` : physical, logical, ou ``dossier`` (livrable DAT complet :
    élévation + logique + brassage + nomenclature, cadre et cartouche).
    ``theme`` : sombre/clair/kaki/nuit. ``rendu`` : photos ou dessin."""
    project = _parse_project(payload)
    if view == "dossier":
        pdf = render_project_dossier_pdf(project, theme=theme, rendu=rendu)
        suffix = "-dossier"
    else:
        pdf = render_project_pdf(project, view=view, theme=theme, rendu=rendu)
        suffix = "-logique" if view == "logical" else ""
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}{suffix}.pdf"'},
    )


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


# --- Frontend ---------------------------------------------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
