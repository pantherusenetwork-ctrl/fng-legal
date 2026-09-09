"""Kit portable RackForgePrime — chemins, navigateur, adresses LAN.

Aucun chemin personnel n'est codé en dur. Tout se déduit du dossier du
kit (à côté de l'exe, ou de ``run.py`` en développement), jamais du
répertoire de travail courant : on peut copier le dossier sur une clé
USB, changer de lettre de lecteur, ou lancer depuis un raccourci.
"""

from __future__ import annotations

import os
import socket
import sys
from datetime import datetime
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

WORKSPACE_NAME = "RackForgePrime-Workspace"
ADDRESS_FILE = "DERNIERE-ADRESSE.txt"
BOOT_LOG = "rackforge-demarrage.log"

WORKSPACE_SUBDIRS = (
    "projets",
    "exports",
    "catalogue",
    "datasheets",
    "sauvegardes",
    "catalogue/images-officielles",
    "catalogue/types-officiels",
    "catalogue/formes",
)

WORKSPACE_LISEZMOI = """\
RackForgePrime — espace de travail
==================================

projets/     Vos projets (.json). C'est la SOURCE DE VÉRITÉ : versionnez-les,
             diffez-les, les dessins se régénèrent depuis ces fichiers.
exports/     Rangez ici vos SVG / PDF / CSV exportés depuis l'application.
catalogue/   Déposez ici vos YAML NetBox et vos images / SVG de faceplates,
             puis importez-les depuis la palette.
             Sous-dossier images-officielles/ : une image nommée
             <id-du-type>.png (ex : fortinet-fortigate-100f.png) y est
             chargée automatiquement comme faceplate du type du catalogue.
datasheets/  Déposez ici les PDF constructeurs à importer.
sauvegardes/ Copies datées (PC / NAS / téléchargement).

Ce dossier voyage AVEC l'exe : copiez tout le kit (pas seulement
RackForgePrime.exe) sur l'autre PC ou la clé USB.

Lancement : LANCER-PC.bat / LANCER-WEB.bat / LANCER-PHONE.bat
(ou double-clic sur RackForgePrime.exe). Tout est local.
"""

# Navigateurs Chromium embarqués dans le kit (optionnel).
PORTABLE_BROWSER_RELS = (
    "navigateur/msedge.exe",
    "navigateur/msedge/msedge.exe",
    "navigateur/chrome.exe",
    "navigateur/chrome-win/chrome.exe",
    "chrome-win/chrome.exe",
)


def run_py_dir() -> Path:
    """Dossier qui contient ``run.py`` en développement (racine du code)."""
    return Path(__file__).resolve().parents[2]


def kit_dir() -> Path:
    """Dossier du kit = à côté de l'exe (packagé) ou de ``run.py`` (dev).

    Surcharge : variable ``RACKFORGE_KIT_DIR``. Jamais ``cwd``.
    """
    override = os.environ.get("RACKFORGE_KIT_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if FROZEN:
        return Path(sys.executable).resolve().parent
    return run_py_dir()


def resolve_kit_dir() -> Path:
    """Alias stable de ``kit_dir`` (même contrat)."""
    return kit_dir()


def workspace_path(kit: Path | None = None) -> Path:
    """Racine de l'espace de travail (projets, catalogue, exports…)."""
    override = os.environ.get("RACKFORGE_WORKSPACE")
    if override:
        return Path(override).expanduser().resolve()
    return (kit or resolve_kit_dir()) / WORKSPACE_NAME


def apply_kit_env(kit: Path | None = None, ws: Path | None = None) -> tuple[Path, Path]:
    """Enregistre kit + workspace dans l'environnement du processus.

    Écrase ``RACKFORGE_PROJECTS_DIR`` / ``RACKFORGE_CATALOG_DIR`` pour
    qu'un reste d'une autre installation ne détourne pas un kit USB.
    """
    kit = (kit or resolve_kit_dir()).resolve()
    ws = (ws or workspace_path(kit)).resolve()
    os.environ["RACKFORGE_KIT_DIR"] = str(kit)
    os.environ["RACKFORGE_WORKSPACE"] = str(ws)
    os.environ["RACKFORGE_PROJECTS_DIR"] = str(ws / "projets")
    os.environ["RACKFORGE_CATALOG_DIR"] = str(ws / "catalogue")
    return kit, ws


def ensure_workspace(kit: Path | None = None) -> Path:
    """Crée (idempotent) l'espace de travail et pointe le stockage dessus."""
    kit, ws = apply_kit_env(kit)
    for sub in WORKSPACE_SUBDIRS:
        (ws / sub).mkdir(parents=True, exist_ok=True)
    readme = ws / "LISEZMOI.txt"
    if not readme.exists():
        readme.write_text(WORKSPACE_LISEZMOI, encoding="utf-8")
    return ws


def workspace_is_writable(ws: Path) -> bool:
    """True si on peut écrire dans le workspace, ou à défaut dans son parent.

    Ne crée pas le workspace (le diagnostic ne doit pas polluer le dépôt).
    """
    probe_dir = ws if ws.is_dir() else (ws.parent if ws.parent.is_dir() else None)
    if probe_dir is None:
        return False
    try:
        probe = probe_dir / ".ecriture-ok"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def append_boot_log(message: str, kit: Path | None = None) -> Path | None:
    """Journal tout au début (avant uvicorn) — survit à un plantage muet."""
    kit = kit or resolve_kit_dir()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp}  {message}\n"
    candidates = [kit / BOOT_LOG]
    temp = os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
    candidates.append(Path(temp) / BOOT_LOG)
    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
            return path
        except OSError:
            continue
    return None


def edition_defaults(edition: str) -> dict:
    """Réglages des 3 éditions (PC / Web / Phone)."""
    edition = (edition or "pc").strip().lower()
    if edition not in ("pc", "web", "phone"):
        raise ValueError(f"Édition inconnue : {edition} (pc, web ou phone)")
    if edition == "phone":
        return {
            "edition": "phone",
            "host": "0.0.0.0",
            "open_mode": "none",
            "keep_alive": True,
        }
    if edition == "web":
        return {
            "edition": "web",
            "host": "127.0.0.1",
            "open_mode": "browser",
            "keep_alive": True,
        }
    return {
        "edition": "pc",
        "host": "127.0.0.1",
        "open_mode": "app",
        "keep_alive": False,
    }


def lan_ipv4_addresses() -> list[str]:
    """Adresses IPv4 non-loopback de ce poste (pour l'édition Phone)."""
    found: list[str] = []

    def _add(ip: str) -> None:
        if not ip or ip.startswith("127.") or ip.startswith("169.254."):
            return
        if ip not in found:
            found.append(ip)

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            _add(info[4][0])
    except OSError:
        pass

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            _add(probe.getsockname()[0])
        finally:
            probe.close()
    except OSError:
        pass

    return found


def public_urls(host: str, port: int) -> list[str]:
    """URLs à ouvrir / afficher pour une session."""
    urls = [f"http://127.0.0.1:{port}"]
    if host in ("0.0.0.0", "::", ""):
        for ip in lan_ipv4_addresses():
            url = f"http://{ip}:{port}"
            if url not in urls:
                urls.append(url)
    elif host not in ("127.0.0.1", "localhost"):
        extra = f"http://{host}:{port}"
        if extra not in urls:
            urls.append(extra)
    return urls


def write_address_file(kit: Path, edition: str, host: str, port: int,
                       workspace: Path, extra: str = "") -> Path:
    """Écrit DERNIERE-ADRESSE.txt à la racine du kit (lisible sur USB)."""
    urls = public_urls(host, port)
    lines = [
        "RackForgePrime — adresses de cette session",
        "==========================================",
        "",
        f"Édition          : {edition}",
        f"Date             : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Kit              : {kit}",
        f"Espace de travail: {workspace}",
        "",
        "Ouvrir dans le navigateur :",
    ]
    for url in urls:
        lines.append(f"  {url}")
    if extra:
        lines.extend(["", extra])
    lines.append("")
    path = kit / ADDRESS_FILE
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def windows_browser_paths() -> list[Path]:
    """Emplacements classiques d'Edge / Chrome sous Windows."""
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("LocalAppData") or ""
    return [
        Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(local) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local) / "Chromium" / "Application" / "chrome.exe",
        Path(pf) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
        Path(local) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
    ]


def browser_candidates(kit: Path | None = None) -> list[Path]:
    """Navigateurs possibles, kit portable d'abord puis le poste."""
    import shutil

    kit = kit or resolve_kit_dir()
    ordered: list[Path] = []
    seen: set[str] = set()

    def _push(path: Path) -> None:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            ordered.append(path)

    for rel in PORTABLE_BROWSER_RELS:
        _push(kit / rel)

    if os.name == "nt":
        for path in windows_browser_paths():
            _push(path)
        for name in ("msedge", "msedge.exe", "chrome", "chrome.exe",
                     "brave", "brave.exe"):
            found = shutil.which(name)
            if found:
                _push(Path(found))
    else:
        for name in ("chromium", "google-chrome", "chromium-browser",
                     "microsoft-edge", "google-chrome-stable", "brave-browser"):
            found = shutil.which(name)
            if found:
                _push(Path(found))
    return ordered


def first_browser(kit: Path | None = None) -> Path | None:
    for path in browser_candidates(kit):
        if path.is_file():
            return path
    return None


def open_ui(url: str, mode: str = "app", kit: Path | None = None) -> str:
    """Ouvre l'UI. Retourne ``app``, ``browser`` ou ``none``."""
    import shutil
    import subprocess
    import webbrowser

    if mode in ("none", "", "off"):
        return "none"
    kit = kit or resolve_kit_dir()
    exe = first_browser(kit)
    if mode == "app" and exe is not None:
        profile = kit / "profil-fenetre"
        try:
            profile.mkdir(parents=True, exist_ok=True)
        except OSError:
            profile = Path(os.environ.get("TEMP", "/tmp")) / "rfp-profil-fenetre"
            profile.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(exe),
            f"--app={url}",
            "--window-size=1500,950",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        try:
            subprocess.Popen(cmd)
            return "app"
        except OSError:
            pass
    # Web, ou repli PC : navigateur par défaut (onglet normal).
    if exe is not None and mode == "browser":
        try:
            subprocess.Popen([str(exe), url])
            return "browser"
        except OSError:
            pass
    try:
        if webbrowser.open(url):
            return "browser"
    except Exception:  # noqa: BLE001
        pass
    opener = shutil.which("xdg-open")
    if opener:
        try:
            subprocess.Popen([opener, url])
            return "browser"
        except OSError:
            pass
    return "none"


def diagnostic_report(kit: Path | None = None, ws: Path | None = None) -> dict:
    """État du kit — utilisé par ``--diagnostic`` et ``/api/kit``."""
    kit = (kit or resolve_kit_dir()).resolve()
    ws = (ws or workspace_path(kit)).resolve()
    browser = first_browser(kit)
    frontend = None
    if FROZEN:
        frontend = Path(getattr(sys, "_MEIPASS", kit)) / "frontend"
    else:
        frontend = run_py_dir() / "frontend"
    internal = kit / "_internal"
    return {
        "ok": True,
        "app": "RackForgePrime",
        "frozen": FROZEN,
        "kit_dir": str(kit),
        "workspace": str(ws),
        "workspace_exists": ws.is_dir(),
        "workspace_writable": workspace_is_writable(ws) if ws.parent.exists() or ws.exists() else False,
        "browser": str(browser) if browser else None,
        "frontend": str(frontend),
        "frontend_exists": frontend.is_dir() if frontend else False,
        "onedir": internal.is_dir(),
        "edition": os.environ.get("RACKFORGE_EDITION", "pc"),
        "host": os.environ.get("RACKFORGE_BIND_HOST", "127.0.0.1"),
        "port": os.environ.get("RACKFORGE_BIND_PORT", ""),
        "urls": [u for u in os.environ.get("RACKFORGE_PUBLIC_URLS", "").split("|") if u],
    }
