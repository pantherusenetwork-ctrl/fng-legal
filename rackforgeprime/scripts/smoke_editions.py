#!/usr/bin/env python3
"""Smoke des 3 éditions (PC / Web / Phone) — sans exe Windows.

Simule un kit copié ailleurs (USB / autre PC) : dossier temporaire,
cwd différent du kit, chemins uniquement via RACKFORGE_KIT_DIR.

  python scripts/smoke_editions.py
  python scripts/smoke_editions.py --port 18137

Codes de sortie : 0 = 3 éditions vertes ; 1 = au moins un échec.
Chaque édition : /api/ping, /api/kit, DERNIERE-ADRESSE.txt, binding.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _free_port(start: int) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Aucun port libre pour le smoke")


def _get_json(url: str, timeout: float = 2.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_ping(port: int, tries: int = 40) -> dict:
    last = None
    for _ in range(tries):
        try:
            return _get_json(f"http://127.0.0.1:{port}/api/ping")
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                json.JSONDecodeError) as exc:
            last = exc
            time.sleep(0.25)
    raise RuntimeError(f"Serveur muet sur {port} ({last})")


def _make_kit(base: Path) -> Path:
    kit = base / "kit"
    kit.mkdir(parents=True)
    # Même contrat que le kit réel : lanceurs + workspace à côté.
    portable = ROOT / "portable"
    for name in ("LANCER-PC.bat", "LANCER-WEB.bat", "LANCER-PHONE.bat",
                 "_commun.cmd", "LISEZMOI.txt"):
        shutil.copy2(portable / name, kit / name)
    (kit / "RackForgePrime-Workspace" / "projets").mkdir(parents=True)
    return kit


def _start(kit: Path, edition: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["RACKFORGE_KIT_DIR"] = str(kit)
    env["RACKFORGE_WORKSPACE"] = str(kit / "RackForgePrime-Workspace")
    env["RACKFORGE_EDITION"] = edition
    # cwd volontairement AILLEURS : reproduit le lancement depuis USB
    # ou un raccourci dont le « Démarrer dans » n'est pas le kit.
    cwd = kit.parent / "pas-le-kit"
    cwd.mkdir(exist_ok=True)
    cmd = [sys.executable, str(ROOT / "run.py"),
           "--edition", edition, "--port", str(port), "--no-browser"]
    return subprocess.Popen(
        cmd, cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def _stop(proc: subprocess.Popen) -> str:
    if proc.poll() is None:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=4)
    else:
        out, _ = proc.communicate(timeout=2)
    return out or ""


def smoke_one(kit: Path, edition: str, port: int) -> dict:
    """Lance une édition, vérifie ping + kit + fichier d'adresses."""
    result = {"edition": edition, "port": port, "ok": False, "detail": ""}
    proc = _start(kit, edition, port)
    try:
        ping = _wait_ping(port)
        if ping.get("app") != "RackForgePrime":
            raise RuntimeError(f"ping inattendu : {ping}")
        if ping.get("edition") != edition:
            raise RuntimeError(f"édition ping={ping.get('edition')} ≠ {edition}")
        kit_info = _get_json(f"http://127.0.0.1:{port}/api/kit")
        if Path(kit_info["kit_dir"]).resolve() != kit.resolve():
            raise RuntimeError(
                f"kit_dir fuit hors du kit : {kit_info['kit_dir']}")
        if "RackForgePrime-Workspace" not in kit_info.get("workspace", ""):
            raise RuntimeError(f"workspace inattendu : {kit_info['workspace']}")
        addr = kit / "DERNIERE-ADRESSE.txt"
        if not addr.is_file():
            raise RuntimeError("DERNIERE-ADRESSE.txt absent")
        text = addr.read_text(encoding="utf-8")
        if f"127.0.0.1:{port}" not in text:
            raise RuntimeError(f"adresse locale absente de {addr.name}")
        if edition == "phone":
            if kit_info.get("host") != "0.0.0.0":
                raise RuntimeError(f"Phone doit binder 0.0.0.0, pas {kit_info.get('host')}")
            if "0.0.0.0" not in text and "Édition          : phone" not in text:
                raise RuntimeError("fichier d'adresses Phone incomplet")
        else:
            if kit_info.get("host") not in ("127.0.0.1", "localhost"):
                raise RuntimeError(f"{edition} doit rester local, host={kit_info.get('host')}")
        # Page UI servie (frontend embarqué / source).
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        if "RackForgePrime" not in html or "brand-version" not in html:
            raise RuntimeError("UI HTML inattendue")
        result["ok"] = True
        result["detail"] = f"v{ping.get('version')} kit={kit_info['kit_dir']}"
        result["version"] = ping.get("version")
        result["urls"] = kit_info.get("urls")
    except Exception as exc:  # noqa: BLE001 — le smoke rapporte, ne masque pas
        result["detail"] = f"{type(exc).__name__}: {exc}"
    finally:
        log = _stop(proc)
        if not result["ok"] and log:
            result["log"] = log[-1500:]
    return result


def smoke_moved_kit(base: Path, port: int) -> dict:
    """Copie le kit vers un autre dossier (USB / autre lettre) et reteste Web."""
    src = _make_kit(base / "origine")
    dest = base / "usb-simule" / "RackForgePrime-Portable"
    shutil.copytree(src, dest)
    return smoke_one(dest, "web", port)


def check_launchers() -> dict:
    """Les .bat du kit ne dépendent plus de ..\\RackForgePrime-PC comme seul chemin."""
    portable = ROOT / "portable"
    detail = []
    ok = True
    for name in ("LANCER-PC.bat", "LANCER-WEB.bat", "LANCER-PHONE.bat"):
        text = (portable / name).read_text(encoding="utf-8")
        if "%~dp0" not in text and "_commun.cmd" not in text:
            ok = False
            detail.append(f"{name} n'utilise pas %~dp0")
        if "cd ..\\RackForgePrime-PC" in text or "cd ../RackForgePrime-PC" in text:
            ok = False
            detail.append(f"{name} cd encore vers le dossier frère")
    commun = (portable / "_commun.cmd").read_text(encoding="utf-8")
    if "%~dp0" not in commun:
        ok = False
        detail.append("_commun.cmd sans %~dp0")
    if "RackForgePrime.exe" not in commun:
        ok = False
        detail.append("_commun.cmd ne cherche pas l'exe à côté")
    # Le repli 3 dossiers est accepté, mais après la recherche locale.
    exe_idx = commun.find("RackForgePrime.exe")
    legacy_idx = commun.find("..\\RackForgePrime-PC")
    if legacy_idx != -1 and (exe_idx == -1 or legacy_idx < exe_idx):
        ok = False
        detail.append("repli legacy avant la recherche locale")
    return {"edition": "lanceurs", "ok": ok,
            "detail": "; ".join(detail) or "lanceurs ancrés sur %~dp0"}


def run_all(port_start: int = 18137) -> list[dict]:
    import tempfile
    results = [check_launchers()]
    with tempfile.TemporaryDirectory(prefix="rfp-smoke-") as tmp:
        tmp_path = Path(tmp)
        kit = _make_kit(tmp_path / "principal")
        port = port_start
        for edition in ("pc", "web", "phone"):
            port = _free_port(port)
            results.append(smoke_one(kit, edition, port))
            port += 1
        port = _free_port(port)
        results.append(smoke_moved_kit(tmp_path / "deplace", port))
        results[-1]["edition"] = "web-usb-simule"
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke 3 éditions RackForgePrime")
    parser.add_argument("--port", type=int, default=18137)
    args = parser.parse_args()
    results = run_all(args.port)
    width = max(len(r["edition"]) for r in results)
    failed = 0
    print("Smoke RackForgePrime — 3 éditions + kit déplacé")
    print("=" * 56)
    for row in results:
        mark = "VERT" if row["ok"] else "ROUGE"
        if not row["ok"]:
            failed += 1
        print(f"  {row['edition']:<{width}}  {mark}  {row.get('detail', '')}")
        if row.get("log"):
            print("    --- log ---")
            print(row["log"])
    print("=" * 56)
    print("OK" if failed == 0 else f"{failed} échec(s)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
