"""Images officielles du catalogue — lues depuis l'espace de travail.

Le dossier ``catalogue/images-officielles/`` de l'espace de travail contient
des images de faceplate nommées par id de type : ``<type-id>.png`` (ou
``.jpg`` / ``.jpeg`` / ``.svg``). Au chargement du catalogue, chaque type
dont l'image existe reçoit son ``faceplate_image`` en data URI — le projet
sauvegardé reste auto-suffisant, comme pour un import manuel.

Aucun appel réseau ici : l'application reste 100 % locale. Le remplissage
du dossier se fait à la main ou via ``scripts/telecharger_images_officielles.py``
(exécuté volontairement par l'utilisateur, hors application).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from .models import EquipmentType

# Extensions acceptées → type MIME du data URI.
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}

SUBDIR = "images-officielles"


def images_dir() -> Path | None:
    """Dossier des images officielles, ou None si non configuré/absent."""
    base = os.environ.get("RACKFORGE_CATALOG_DIR")
    if not base:
        return None
    d = Path(base) / SUBDIR
    return d if d.is_dir() else None


def _to_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    # Le MIME est déduit des OCTETS, pas de l'extension : le catalogue
    # contient des JPEG déguisés en .png — une data URI menteuse passe
    # dans un navigateur (qui sniffe) mais peut être refusée par un
    # convertisseur strict (svglib, draw.io).
    if raw.startswith(b"\x89PNG"):
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8"):
        mime = "image/jpeg"
    elif raw.lstrip()[:5] in (b"<svg ", b"<?xml"):
        mime = "image/svg+xml"
    else:
        mime = _MIME[path.suffix.lower()]
    payload = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{payload}"


def apply_official_images(types: list[EquipmentType]) -> list[EquipmentType]:
    """Retourne des copies des types, enrichies de leur image si présente.

    Un type qui a déjà une image (ou un SVG) inline garde la sienne : le
    fichier sur disque ne l'écrase pas. Relu à chaque appel : déposer une
    image puis recharger la page suffit, sans redémarrer l'application.
    """
    d = images_dir()
    if d is None:
        return types
    out: list[EquipmentType] = []
    for t in types:
        if not t.faceplate_image and not t.faceplate_svg:
            for ext in _MIME:
                candidate = d / f"{t.id}{ext}"
                if candidate.is_file():
                    t = t.model_copy(
                        update={"faceplate_image": _to_data_uri(candidate)})
                    break
        out.append(t)
    return out
