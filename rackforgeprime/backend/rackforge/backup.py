"""Sauvegarde des projets — comme draw.io ou Visio : où on veut, au format
qu'on veut.

Trois questions, tout au choix (jamais de comportement imposé) :
- QUOI    : le projet ouvert, tous les projets, ou tout l'espace de travail
- FORMAT  : JSON ou ZIP côté serveur ; les formats visuels (PDF, SVG, PNG,
            draw.io) sont générés par les exports et déposés via
            ``write_file`` ou téléchargés par le navigateur
- OÙ      : « Enregistrer sous » du navigateur (l'utilisateur choisit),
            le dossier de sauvegarde de l'app, ou n'importe quel chemin
            (autre disque, NAS, clé USB) tapé une fois puis mémorisé

Aucun chemin personnel n'est codé en dur : l'app sera distribuée. Le
dernier dossier utilisé est mémorisé DANS l'espace de travail de chaque
installation (``sauvegardes/.dernier-dossier.txt``).

Un dossier injoignable (NAS éteint…) n'annule jamais les autres
destinations : chaque destination rapporte son propre résultat.
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from . import storage

# Ce qu'on ne met jamais dans une archive de l'espace de travail : la
# sauvegarde elle-même (récursion) et les journaux.
_ZIP_EXCLUDE_DIRS = {"sauvegardes"}
_ZIP_EXCLUDE_SUFFIXES = {".log"}


def workspace_dir() -> Path:
    """L'espace de travail = le parent du dossier des projets."""
    return storage.projects_dir().resolve().parent


def local_dir() -> Path:
    return workspace_dir() / "sauvegardes"


def _last_dir_file() -> Path:
    return local_dir() / ".dernier-dossier.txt"


def get_last_custom_dir() -> str:
    """Le dernier dossier libre utilisé — pré-remplit le champ de l'UI."""
    try:
        return _last_dir_file().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def remember_custom_dir(path: str) -> None:
    try:
        local_dir().mkdir(parents=True, exist_ok=True)
        _last_dir_file().write_text(path.strip(), encoding="utf-8")
    except OSError:
        pass  # mémoriser est un confort, jamais une condition de réussite


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%Hh%M")


def _collect(scope: str, project_payload: dict | None) -> list[tuple[str, bytes]]:
    """Retourne les fichiers à sauver : liste (nom-relatif, contenu)."""
    stamp = _stamp()
    if scope == "projet":
        if not project_payload:
            raise ValueError("Aucun projet ouvert à sauvegarder")
        name = str(project_payload.get("id") or "projet")
        data = json.dumps(project_payload, ensure_ascii=False,
                          indent=2).encode("utf-8")
        return [(f"{name}-{stamp}.json", data)]
    if scope == "projets":
        files = []
        for n in storage.list_projects():
            p = storage.projects_dir() / f"{n}.json"
            files.append((f"{n}-{stamp}.json", p.read_bytes()))
        if not files:
            raise ValueError("Aucun projet enregistré à sauvegarder")
        return files
    if scope == "workspace":
        ws = workspace_dir()
        files = []
        for p in sorted(ws.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ws)
            if rel.parts and rel.parts[0] in _ZIP_EXCLUDE_DIRS:
                continue
            if p.suffix.lower() in _ZIP_EXCLUDE_SUFFIXES:
                continue
            files.append((str(rel), p.read_bytes()))
        return files
    raise ValueError(f"Portée inconnue : {scope}")


def _zip_name(scope: str, project_payload: dict | None) -> str:
    stamp = _stamp()
    if scope == "projet" and project_payload:
        return f"{project_payload.get('id') or 'projet'}-{stamp}.zip"
    return {"projet": f"projet-{stamp}.zip",
            "projets": f"projets-{stamp}.zip",
            "workspace": f"espace-de-travail-{stamp}.zip"}[scope]


def make_archive(scope: str, fmt: str,
                 project_payload: dict | None = None) -> tuple[str, bytes, str]:
    """Fabrique le fichier en mémoire — pour « Enregistrer sous » du
    navigateur. Retourne (nom, contenu, type MIME)."""
    files = _collect(scope, project_payload)
    if scope == "workspace":
        fmt = "zip"
    if fmt == "json" and len(files) == 1:
        return files[0][0], files[0][1], "application/json"
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, data in files:
            z.writestr(rel, data)
    return _zip_name(scope, project_payload), buf.getvalue(), "application/zip"


def _dest_dirs(dest: str, custom_dir: str) -> list[tuple[str, Path]]:
    dirs: list[tuple[str, Path]] = []
    if dest in ("pc", "deux"):
        dirs.append(("Dossier de l'app", local_dir()))
    if dest in ("dossier", "deux"):
        if not custom_dir.strip():
            raise ValueError("Aucun dossier indiqué — tape le chemin voulu")
        dirs.append(("Dossier choisi", Path(custom_dir.strip())))
    return dirs


def run_backup(scope: str, fmt: str, dest: str,
               project_payload: dict | None = None,
               custom_dir: str = "") -> dict:
    """Écrit la sauvegarde côté serveur ; ne lève jamais pour un dossier
    injoignable — chaque destination rapporte son résultat."""
    files = _collect(scope, project_payload)
    if scope == "workspace":
        # Des centaines de fichiers en vrac ne se relisent pas : archive.
        fmt = "zip"
    zip_name = _zip_name(scope, project_payload)

    results, errors = [], []
    for label, d in _dest_dirs(dest, custom_dir):
        try:
            d.mkdir(parents=True, exist_ok=True)
            if fmt == "zip":
                out = d / zip_name
                with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                    for rel, data in files:
                        z.writestr(rel, data)
                results.append({"destination": label, "fichier": str(out),
                                "octets": out.stat().st_size,
                                "elements": len(files)})
            else:
                total = 0
                for rel, data in files:
                    out = d / Path(rel).name
                    out.write_bytes(data)
                    total += len(data)
                results.append({"destination": label, "fichier": str(d),
                                "octets": total, "elements": len(files)})
            if label == "Dossier choisi":
                remember_custom_dir(custom_dir)
        except OSError as exc:
            errors.append({"destination": label,
                           "erreur": f"{d} injoignable — vérifie le chemin "
                                     f"et que le disque/NAS répond "
                                     f"({exc.__class__.__name__})"})
    return {"ok": bool(results), "resultats": results, "erreurs": errors}


def write_file(directory: str, name: str, data: bytes) -> dict:
    """Dépose UN fichier (un export PDF/SVG/PNG/draw.io déjà généré) dans
    un dossier choisi. Le nom est nettoyé : pas de traversée de chemin."""
    if not directory.strip():
        raise ValueError("Aucun dossier indiqué")
    safe = Path(name).name
    if not safe:
        raise ValueError("Nom de fichier vide")
    d = Path(directory.strip())
    d.mkdir(parents=True, exist_ok=True)
    out = d / safe
    out.write_bytes(data)
    remember_custom_dir(directory)
    return {"ok": True, "fichier": str(out), "octets": out.stat().st_size}
