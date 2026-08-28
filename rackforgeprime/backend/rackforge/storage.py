"""Sauvegarde locale des projets — de simples fichiers JSON.

Répertoire : ``./projects`` à côté du dépôt (surchageable via
``RACKFORGE_PROJECTS_DIR``). Pas de base de données : le JSON est la source
de vérité, il se versionne dans Git et se diffe à l'œil nu.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .models import Project

_SAFE_NAME = re.compile(r"^[\w][\w\- ]{0,80}$")


def projects_dir() -> Path:
    d = Path(os.environ.get("RACKFORGE_PROJECTS_DIR", "projects"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path_for(name: str) -> Path:
    if not _SAFE_NAME.match(name):
        raise ValueError(
            "Nom de projet invalide (lettres, chiffres, tirets, espaces)"
        )
    return projects_dir() / f"{name}.json"


def list_projects() -> list[str]:
    return sorted(p.stem for p in projects_dir().glob("*.json"))


def load_project(name: str) -> Project:
    path = _path_for(name)
    if not path.exists():
        raise FileNotFoundError(f"Projet introuvable : {name}")
    return Project.model_validate_json(path.read_text(encoding="utf-8"))


def save_project(name: str, project: Project) -> Path:
    """La validation Pydantic (placement, collisions) a déjà eu lieu :
    on ne peut pas sauvegarder un projet physiquement impossible."""
    path = _path_for(name)
    path.write_text(
        json.dumps(project.model_dump(by_alias=True), ensure_ascii=False,
                   indent=2),
        encoding="utf-8",
    )
    return path
