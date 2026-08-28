"""Serveur local RackForgePrime — FastAPI.

Sert l'UI (frontend statique) et l'API JSON. Tout tourne en local :
aucun appel sortant, aucune dépendance cloud. Le backend est l'autorité
de validation : un projet qui viole le snap U ou chevauche deux
équipements est refusé avec un message précis (HTTP 422).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from rackforge import storage
from rackforge.catalog import BUILTIN_TYPES, ROLE_COLORS
from rackforge.importers import import_netbox_yaml, parse_datasheet_pdf
from rackforge.models import (Project, patch_table, patch_table_csv,
                              rack_stats, type_index)
from rackforge.pdf_export import render_project_pdf
from rackforge.svg_export import render_project_svg

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="RackForgePrime", version="0.1.0", docs_url="/api/docs")


def _parse_project(payload: dict) -> Project:
    """Valide un projet reçu du frontend ; 422 lisible en français sinon."""
    try:
        return Project.model_validate(payload)
    except ValidationError as exc:
        # On remonte les messages du moteur de placement tels quels.
        msgs = [e.get("msg", str(e)) for e in exc.errors()]
        raise HTTPException(status_code=422, detail=msgs)


# --- Catalogue --------------------------------------------------------------

@app.get("/api/catalog")
def get_catalog() -> dict:
    """Types intégrés + couleurs de rôle (la palette de gauche)."""
    return {
        "types": [t.model_dump() for t in BUILTIN_TYPES],
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
def export_svg(payload: dict) -> Response:
    project = _parse_project(payload)
    svg = render_project_svg(project)
    return Response(
        content=svg, media_type="image/svg+xml",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}.svg"'},
    )


@app.post("/api/export/pdf")
def export_pdf(payload: dict) -> Response:
    project = _parse_project(payload)
    pdf = render_project_pdf(project)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{project.id}.pdf"'},
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
