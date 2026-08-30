"""Packs de types constructeurs — chargés depuis l'espace de travail.

Le dossier ``catalogue/types-officiels/`` contient des fichiers JSON, chacun
étant une **liste** d'objets ``EquipmentType`` (le même schéma que le
catalogue intégré). Ils enrichissent la palette sans toucher au code — et
restent visibles sur disque : l'utilisateur voit et valide ce qui entre.

Un type de pack portant l'id d'un type intégré le remplace (même mécanisme
que les types du projet). Les images officielles s'appliquent ensuite via
``catalog_images`` (fichier ``images-officielles/<id>.png``).

Aucun appel réseau : le remplissage du dossier se fait à la main ou via
``scripts/telecharger_pack_constructeurs.py`` (hors application).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from .models import EquipmentType

SUBDIR = "types-officiels"


def packs_dir() -> Path | None:
    base = os.environ.get("RACKFORGE_CATALOG_DIR")
    if not base:
        return None
    d = Path(base) / SUBDIR
    return d if d.is_dir() else None


def load_pack_types() -> list[EquipmentType]:
    """Tous les types des packs, dans l'ordre des fichiers (tri par nom).

    Un fichier illisible ou une entrée invalide est ignoré silencieusement :
    un pack cassé ne doit jamais empêcher l'application de démarrer.
    """
    d = packs_dir()
    if d is None:
        return []
    out: list[EquipmentType] = []
    for path in sorted(d.glob("*.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            try:
                out.append(EquipmentType.model_validate(entry))
            except ValidationError:
                continue
    return out


def merged_catalog(builtin: list[EquipmentType]) -> list[EquipmentType]:
    """Catalogue intégré + packs (un pack remplace un intégré de même id)."""
    index = {t.id: t for t in builtin}
    for t in load_pack_types():
        index[t.id] = t
    return list(index.values())
