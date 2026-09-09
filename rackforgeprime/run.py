"""Point d'entrée RackForgePrime.

    python run.py                 → édition PC, http://127.0.0.1:8137
    python run.py --edition web   → navigateur local, serveur partagé
    python run.py --edition phone → LAN (0.0.0.0) + adresses affichées
    python run.py --diagnostic    → vérifie le kit sans lancer le serveur

Packagé (PyInstaller onedir, recommandé pour USB) : l'exe crée son
espace de travail **à côté de lui**, jamais dans %TEMP% ni dans le cwd.

    <kit>/
    ├── RackForgePrime.exe
    ├── _internal/                 ← DLLs (onedir : pas d'extraction TEMP)
    ├── LANCER-PC.bat
    ├── LANCER-WEB.bat
    ├── LANCER-PHONE.bat
    ├── LISEZMOI.txt
    └── RackForgePrime-Workspace/  ← projets, catalogue, exports

Local uniquement : aucune donnée ne sort du poste.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

# En développement, le package vit dans backend/ ; on l'ajoute au path.
# Dans l'exe, PyInstaller a déjà embarqué les modules (via --paths backend).
if not FROZEN:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from rackforge.kit import (  # noqa: E402
    ADDRESS_FILE,
    apply_kit_env,
    append_boot_log,
    diagnostic_report,
    edition_defaults,
    ensure_workspace,
    first_browser,
    open_ui,
    public_urls,
    resolve_kit_dir,
    workspace_is_writable,
    workspace_path,
    write_address_file,
)


def open_app_window(url: str) -> bool:
    """Compat : fenêtre ``--app`` Chromium, sinon False (repli navigateur)."""
    return open_ui(url, mode="app") == "app"


def running_instance(host: str, port: int) -> str | None:
    """Version de RackForgePrime qui écoute déjà sur ce port, sinon None
    (port libre, ou occupé par autre chose)."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/ping",
                                    timeout=1.5) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("version") if data.get("app") == "RackForgePrime" else None
    except Exception:  # noqa: BLE001 — pas d'instance joignable
        return None


def _message_box(title: str, text: str) -> None:
    """Boîte de message Windows (l'exe est fenêtré : pas de console où
    lire un print). Silencieux ailleurs."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
    except Exception:  # noqa: BLE001
        pass


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host if host != "0.0.0.0" else "127.0.0.1",
                             port)) != 0


def watch_window(server, app_obj, grace: float = 90.0,
                 silence: float = 180.0, bye_delay: float = 4.0) -> None:
    """Arrête le serveur quand la fenêtre de l'app a disparu.

    - « bye » (pagehide) puis aucun ping pendant ``bye_delay`` s ;
    - ou plus aucun ping depuis ``silence`` s (fenêtre tuée, PC en veille
      prolongée — jamais un simple onglet en arrière-plan : Chrome ralentit
      les timers d'une fenêtre masquée à 1/min, bien sous 180 s).
    Avant le premier ping, ``grace`` s de tolérance (navigateur lent)."""
    start = time.time()
    while not server.should_exit:
        time.sleep(1.0)
        now = time.time()
        st = app_obj.state
        clients = getattr(st, "clients", {})
        alive = [t for t in clients.values() if now - t < silence]
        if st.bye_at and now - st.bye_at > bye_delay and not alive \
                and st.last_ping < st.bye_at:
            print("Dernière fenêtre fermée : arrêt du serveur.")
            server.should_exit = True
        elif st.last_ping and now - st.last_ping > silence:
            print("Plus de fenêtre depuis 3 min : arrêt du serveur.")
            server.should_exit = True
        elif not st.last_ping and now - start > grace:
            print("Aucune fenêtre ne s'est présentée : arrêt du serveur.")
            server.should_exit = True


def _redirect_stdio(ws: Path) -> None:
    """Exe fenêtré (--noconsole) : stdout/stderr valent None sous Windows."""
    if sys.stdout is None or sys.stderr is None:
        log = open(ws / "rackforge.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    else:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(errors="replace")
            except (AttributeError, ValueError):
                pass


def _print_diagnostic(report: dict) -> int:
    print("RackForgePrime — diagnostic du kit portable")
    print("==========================================")
    for key in ("frozen", "kit_dir", "workspace", "workspace_exists",
                "workspace_writable", "browser", "frontend",
                "frontend_exists", "onedir", "edition"):
        print(f"  {key:22} {report.get(key)}")
    urls = report.get("urls") or []
    if urls:
        print("  urls")
        for url in urls:
            print(f"                         {url}")
    ok = bool(report.get("workspace_writable"))
    if report.get("frozen") and not report.get("frontend_exists"):
        print("  ERREUR : frontend embarqué introuvable (rebuild onedir).")
        ok = False
    if not report.get("browser"):
        print("  ATTENTION : aucun Edge/Chrome/Chromium trouvé.")
        print("  L'édition PC ouvrira le navigateur par défaut ; à défaut,")
        print(f"  ouvrez à la main l'URL écrite dans {ADDRESS_FILE}.")
    print("  résultat               " + ("OK" if ok else "À CORRIGER"))
    return 0 if ok else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="RackForgePrime — serveur local")
    parser.add_argument("--port", type=int, default=8137)
    parser.add_argument("--host", default=None,
                        help="défaut : 127.0.0.1 (pc/web) ou 0.0.0.0 (phone)")
    parser.add_argument("--edition", choices=("pc", "web", "phone"), default="pc",
                        help="pc = fenêtre ; web = navigateur ; phone = LAN")
    parser.add_argument("--no-browser", action="store_true",
                        help="ne pas ouvrir de fenêtre / navigateur")
    parser.add_argument("--keep-alive", action="store_true",
                        help="ne jamais s'arrêter quand la fenêtre se ferme "
                             "(serveur partagé : éditions Web / Phone)")
    parser.add_argument("--diagnostic", action="store_true",
                        help="vérifier le kit (chemins, écriture, navigateur) "
                             "sans lancer le serveur")
    args = parser.parse_args()

    defaults = edition_defaults(args.edition)
    if args.host is None:
        args.host = defaults["host"]
    keep_alive = args.keep_alive or defaults["keep_alive"]
    open_mode = "none" if args.no_browser else defaults["open_mode"]

    kit = resolve_kit_dir()
    append_boot_log(
        f"démarrage edition={args.edition} host={args.host} "
        f"port={args.port} frozen={FROZEN} kit={kit}",
        kit,
    )

    ws_target = workspace_path(kit)
    if not workspace_is_writable(ws_target):
        # USB en lecture seule, dossier verrouillé, quota…
        msg = (
            "Impossible d'écrire l'espace de travail :\n"
            f"  {ws_target}\n\n"
            "Vérifiez que le kit n'est pas en lecture seule (clé USB\n"
            "verrouillée, dossier OneDrive hors ligne, droits manquants)."
        )
        print(msg)
        _message_box("RackForgePrime — espace de travail", msg)
        append_boot_log(f"ERREUR workspace illisible: {ws_target}", kit)
        sys.exit(3)

    try:
        ws = ensure_workspace(kit)
    except OSError as exc:
        msg = f"Création de l'espace de travail impossible :\n{ws_target}\n\n{exc}"
        print(msg)
        _message_box("RackForgePrime — espace de travail", msg)
        append_boot_log(f"ERREUR ensure_workspace: {exc}", kit)
        sys.exit(3)

    os.environ["RACKFORGE_EDITION"] = args.edition
    os.environ["RACKFORGE_BIND_HOST"] = args.host
    os.environ["RACKFORGE_BIND_PORT"] = str(args.port)

    if args.diagnostic:
        apply_kit_env(kit, ws)
        report = diagnostic_report(kit, ws)
        sys.exit(_print_diagnostic(report))

    # INSTANCE UNIQUE : si RackForgePrime tourne déjà sur ce port, on ne
    # lance pas un second serveur (qui échouerait en silence) — on rouvre
    # simplement sa fenêtre. C'est le comportement d'une vraie application.
    already = running_instance("127.0.0.1", args.port)
    if already:
        url = f"http://127.0.0.1:{args.port}"
        if args.host not in ("127.0.0.1", "localhost"):
            msg = (
                f"RackForgePrime v{already} tourne déjà en édition PC "
                f"sur le port {args.port}.\n\nFermez sa fenêtre, puis "
                f"relancez LANCER-PHONE.bat : le serveur s'ouvrira alors "
                f"au réseau (téléphone)."
            )
            print(msg)
            _message_box("RackForgePrime — édition Phone", msg)
            return
        print(f"RackForgePrime v{already} tourne déjà → {url} (fenêtre rouverte)")
        if open_mode != "none":
            opened = open_ui(url, mode=open_mode, kit=kit)
            if opened == "none":
                webbrowser.open(url)
        return

    if not port_is_free(args.host, args.port):
        for cand in range(args.port + 1, args.port + 10):
            if port_is_free(args.host, cand):
                print(f"Port {args.port} occupé par un autre programme → {cand}")
                args.port = cand
                os.environ["RACKFORGE_BIND_PORT"] = str(args.port)
                break

    _redirect_stdio(ws)

    urls = public_urls(args.host, args.port)
    os.environ["RACKFORGE_PUBLIC_URLS"] = "|".join(urls)
    try:
        addr_file = write_address_file(kit, args.edition, args.host, args.port, ws)
    except OSError as exc:
        addr_file = None
        append_boot_log(f"adresse non écrite: {exc}", kit)

    # Import APRÈS ensure_workspace (l'env RACKFORGE_PROJECTS_DIR est posé).
    import uvicorn
    from app import VERSION, app  # noqa: WPS433 — objet importé pour le mode packagé

    print(f"RackForgePrime v{VERSION}  édition {args.edition}")
    print(f"Kit : {kit}")
    print(f"Espace de travail : {ws}")
    for url in urls:
        print(f"Ouvrir : {url}")
    if addr_file:
        print(f"Adresses : {addr_file}")
    browser = first_browser(kit)
    if browser:
        print(f"Navigateur : {browser}")
    elif open_mode != "none":
        print("Aucun Edge/Chrome trouvé — repli sur le navigateur par défaut.")

    if args.edition == "phone":
        lan = [u for u in urls if "127.0.0.1" not in u]
        phone_txt = (
            "Édition Phone — ouvrez sur le téléphone (même Wi-Fi) :\n\n"
            + ("\n".join(lan) if lan else
               "Aucune IP LAN détectée. Vérifiez le Wi-Fi, ou lisez\n"
               f"{ADDRESS_FILE} à la racine du kit.")
            + "\n\nSur ce PC : "
            + urls[0]
            + "\nFermez la fenêtre du lanceur pour arrêter le serveur."
        )
        print(phone_txt)
        _message_box("RackForgePrime — édition Phone", phone_txt)

    if open_mode != "none":
        url_local = urls[0]

        def _open() -> None:
            opened = open_ui(url_local, mode=open_mode, kit=kit)
            if opened == "none":
                if not webbrowser.open(url_local):
                    _message_box(
                        "RackForgePrime — navigateur",
                        "Impossible d'ouvrir un navigateur automatiquement.\n\n"
                        f"Ouvrez à la main :\n{url_local}\n\n"
                        "Prérequis : Microsoft Edge ou Google Chrome "
                        "(édition PC en fenêtre). "
                        "Sinon utilisez LANCER-WEB.bat avec Firefox.",
                    )

        threading.Timer(1.2, _open).start()

    config = uvicorn.Config(app, host=args.host, port=args.port,
                            log_level="warning")
    server = uvicorn.Server(config)
    # Application de bureau : fermer la fenêtre = quitter. Un serveur
    # partagé (--no-browser, --host réseau, --keep-alive, web/phone)
    # reste en vie.
    desktop = (open_mode == "app" and not keep_alive
               and args.host in ("127.0.0.1", "localhost"))
    if desktop:
        threading.Thread(target=watch_window, args=(server, app),
                         daemon=True).start()
    try:
        server.run()
    except OSError as exc:
        msg = (
            f"Le serveur n'a pas pu démarrer ({args.host}:{args.port}).\n\n"
            f"{exc}\n\n"
            "Causes fréquentes hors du PC de build : antivirus qui bloque\n"
            "l'exe, Visual C++ Redistributable manquant, ou port filtré."
        )
        print(msg)
        _message_box("RackForgePrime — démarrage", msg)
        append_boot_log(f"ERREUR serveur: {exc}", kit)
        sys.exit(4)


if __name__ == "__main__":
    main()
