"""Point d'entrée RackForgePrime.

    python run.py              → http://127.0.0.1:8137 (navigateur auto-ouvert)
    python run.py --port N     → port custom
    python run.py --no-browser → sans ouverture du navigateur

Fonctionne aussi packagé en exécutable Windows (PyInstaller) : au premier
lancement, l'exe crée son **espace de travail** à côté de lui :

    RackForgePrime-Workspace/
    ├── projets/      ← les JSON de projets (source de vérité)
    ├── exports/      ← vos SVG / PDF / CSV livrés
    ├── catalogue/    ← YAML NetBox et faceplates custom à importer
    ├── datasheets/   ← PDF constructeurs à importer
    └── LISEZMOI.txt

Local uniquement : le serveur n'écoute que sur 127.0.0.1.
"""

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)  # True dans l'exe PyInstaller

# En développement, le package vit dans backend/ ; on l'ajoute au path.
# Dans l'exe, PyInstaller a déjà embarqué les modules (via --paths backend).
if not FROZEN:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

LISEZMOI = """\
RackForgePrime — espace de travail
==================================

projets/     Vos projets (.json). C'est la SOURCE DE VÉRITÉ : versionnez-les,
             diffez-les, les dessins se régénèrent depuis ces fichiers.
exports/     Rangez ici vos SVG / PDF / CSV exportés depuis l'application.
catalogue/   Déposez ici vos YAML NetBox devicetype-library et vos images /
             SVG de faceplates, puis importez-les depuis la palette.
             Sous-dossier images-officielles/ : une image nommée
             <id-du-type>.png (ex : fortinet-fortigate-100f.png) y est
             chargée automatiquement comme faceplate du type du catalogue.
datasheets/  Déposez ici les PDF constructeurs à importer.

Lancement : RackForgePrime.exe (ou `python run.py`), l'interface s'ouvre sur
http://127.0.0.1:8137 — tout est local, aucune donnée ne sort du poste.
"""


def ensure_workspace() -> Path:
    """Crée (idempotent) l'espace de travail et pointe le stockage dessus.

    À côté de l'exe quand on est packagé, à côté du code sinon.
    """
    base = (Path(sys.executable).resolve().parent if FROZEN
            else Path(__file__).resolve().parent)
    ws = base / "RackForgePrime-Workspace"
    for sub in ("projets", "exports", "catalogue", "datasheets",
                "catalogue/images-officielles", "catalogue/types-officiels"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    readme = ws / "LISEZMOI.txt"
    if not readme.exists():
        readme.write_text(LISEZMOI, encoding="utf-8")
    # Le backend (storage.py) lit cette variable pour savoir où sauvegarder.
    os.environ.setdefault("RACKFORGE_PROJECTS_DIR", str(ws / "projets"))
    # catalog_images.py lit celle-ci pour trouver les images officielles.
    os.environ.setdefault("RACKFORGE_CATALOG_DIR", str(ws / "catalogue"))
    return ws


def open_app_window(url: str) -> bool:
    """Ouvre l'UI dans une fenêtre applicative dédiée (mode ``--app`` de
    Edge/Chrome : pas de barre d'adresse, pas d'onglets — le rendu d'une
    vraie application de bureau, sans dépendance supplémentaire).

    Retourne False si aucun navigateur Chromium n'est trouvé (l'appelant
    retombe alors sur le navigateur par défaut).
    """
    import shutil
    import subprocess

    candidates: list[Path] = []
    if os.name == "nt":
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        local = os.environ.get("LocalAppData", "")
        candidates = [
            Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
    else:
        for name in ("chromium", "google-chrome", "chromium-browser"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
    for exe in candidates:
        if exe.exists():
            subprocess.Popen([str(exe), f"--app={url}",
                              "--window-size=1500,950"])
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="RackForgePrime — serveur local")
    parser.add_argument("--port", type=int, default=8137)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true",
                        help="ne pas ouvrir de fenêtre au démarrage")
    args = parser.parse_args()

    ws = ensure_workspace()

    # Exe fenêtré (--noconsole) : sys.stdout/stderr valent None sous Windows
    # et le moindre print planterait l'app. On redirige tout vers un log
    # dans l'espace de travail — utile aussi pour diagnostiquer à distance.
    if sys.stdout is None or sys.stderr is None:
        log = open(ws / "rackforge.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    else:
        # Console cp1252 (cmd, PowerShell) : la flèche « → » du message de
        # démarrage tuerait le process en UnicodeEncodeError.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError):
                pass

    # Import APRÈS ensure_workspace (l'env RACKFORGE_PROJECTS_DIR est posé).
    import uvicorn
    from app import app  # noqa: WPS433 — objet importé pour le mode packagé

    url = f"http://{args.host}:{args.port}"
    print(f"RackForgePrime → {url}")
    print(f"Espace de travail : {ws}")
    if not args.no_browser:
        # Le serveur met ~1 s à écouter ; fenêtre app dédiée, sinon navigateur.
        def _open() -> None:
            if not open_app_window(url):
                webbrowser.open(url)
        threading.Timer(1.2, _open).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
