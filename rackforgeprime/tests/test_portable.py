"""Kit portable : chemins indépendants du cwd, 3 éditions, lanceurs."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import VERSION, app  # noqa: E402
from rackforge import kit  # noqa: E402

PORTABLE = Path(__file__).resolve().parent.parent / "portable"
client = TestClient(app)


def test_version_alignee_sur_le_badge():
    html = (Path(__file__).resolve().parent.parent / "frontend" / "index.html"
            ).read_text(encoding="utf-8")
    assert f">{VERSION}<" in html or f">v{VERSION}<" in html
    assert VERSION == "1.7.1"


def test_workspace_ignore_le_cwd(tmp_path, monkeypatch):
    kit_root = tmp_path / "usb" / "RackForgePrime-Portable"
    kit_root.mkdir(parents=True)
    ailleurs = tmp_path / "ailleurs"
    ailleurs.mkdir()
    monkeypatch.chdir(ailleurs)
    monkeypatch.setenv("RACKFORGE_KIT_DIR", str(kit_root))
    monkeypatch.delenv("RACKFORGE_WORKSPACE", raising=False)
    monkeypatch.delenv("RACKFORGE_PROJECTS_DIR", raising=False)
    ws = kit.ensure_workspace()
    assert ws == (kit_root / "RackForgePrime-Workspace").resolve()
    assert (ws / "projets").is_dir()
    assert (ws / "catalogue" / "images-officielles").is_dir()
    assert (ws / "sauvegardes").is_dir()
    assert os.environ["RACKFORGE_PROJECTS_DIR"] == str(ws / "projets")
    # Rien n'a été créé dans le cwd.
    assert list(ailleurs.iterdir()) == []


def test_env_residuel_ne_detourne_pas_le_kit(tmp_path, monkeypatch):
    ancien = tmp_path / "ancienne-install" / "projets"
    ancien.mkdir(parents=True)
    kit_root = tmp_path / "kit-usb"
    kit_root.mkdir()
    monkeypatch.setenv("RACKFORGE_PROJECTS_DIR", str(ancien))
    monkeypatch.setenv("RACKFORGE_KIT_DIR", str(kit_root))
    monkeypatch.delenv("RACKFORGE_WORKSPACE", raising=False)
    ws = kit.ensure_workspace()
    assert ws.parent == kit_root.resolve()
    assert os.environ["RACKFORGE_PROJECTS_DIR"] == str(ws / "projets")
    assert os.environ["RACKFORGE_PROJECTS_DIR"] != str(ancien)


def test_editions_pc_web_phone():
    pc = kit.edition_defaults("pc")
    web = kit.edition_defaults("web")
    phone = kit.edition_defaults("phone")
    assert pc["host"] == "127.0.0.1" and pc["open_mode"] == "app"
    assert web["host"] == "127.0.0.1" and web["open_mode"] == "browser"
    assert web["keep_alive"] is True
    assert phone["host"] == "0.0.0.0" and phone["keep_alive"] is True
    with pytest.raises(ValueError):
        kit.edition_defaults("tablette")


def test_public_urls_phone_et_local():
    local = kit.public_urls("127.0.0.1", 8137)
    assert local == ["http://127.0.0.1:8137"]
    phone = kit.public_urls("0.0.0.0", 8137)
    assert "http://127.0.0.1:8137" in phone
    # S'il existe une IP LAN, elle est proposée ; sinon au moins le loopback.
    assert all(u.startswith("http://") for u in phone)


def test_navigateur_portable_prioritaire(tmp_path, monkeypatch):
    kit_root = tmp_path / "kit"
    nav = kit_root / "navigateur"
    nav.mkdir(parents=True)
    fake = nav / "msedge.exe"
    fake.write_bytes(b"fake")
    monkeypatch.setenv("RACKFORGE_KIT_DIR", str(kit_root))
    cands = kit.browser_candidates(kit_root)
    assert cands[0] == fake
    assert kit.first_browser(kit_root) == fake


def test_fichier_adresses(tmp_path, monkeypatch):
    kit_root = tmp_path / "kit"
    kit_root.mkdir()
    ws = kit_root / "RackForgePrime-Workspace"
    ws.mkdir()
    path = kit.write_address_file(kit_root, "phone", "0.0.0.0", 8137, ws)
    text = path.read_text(encoding="utf-8")
    assert "Édition          : phone" in text
    assert "127.0.0.1:8137" in text
    assert str(ws) in text


def test_lanceurs_autonomes():
    commun = (PORTABLE / "_commun.cmd").read_text(encoding="utf-8")
    assert "%~dp0" in commun
    assert "RackForgePrime.exe" in commun
    # Recherche locale avant l'ancien schéma 3 dossiers.
    assert commun.find("if exist \"%RFP_KIT%\\RackForgePrime.exe\"") < \
        commun.find("..\\RackForgePrime-PC")
    for name in ("LANCER-PC.bat", "LANCER-WEB.bat", "LANCER-PHONE.bat"):
        text = (PORTABLE / name).read_text(encoding="utf-8")
        assert "_commun.cmd" in text
        assert "cd ..\\RackForgePrime-PC" not in text
        assert "--edition" in text


def test_assemblage_du_kit(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from construire_kit_portable import assemble  # noqa: WPS433
    dest = assemble(tmp_path / "RackForgePrime-Portable")
    assert (dest / "LANCER-PC.bat").is_file()
    assert (dest / "LANCER-WEB.bat").is_file()
    assert (dest / "LANCER-PHONE.bat").is_file()
    assert (dest / "_commun.cmd").is_file()
    assert (dest / "LISEZMOI.txt").is_file()
    assert (dest / "GUIDE-UTILISATEUR.md").is_file()
    assert (dest / "RackForgePrime-Workspace" / "projets").is_dir()
    assert (dest / "KIT-PORTABLE.txt").is_file()
    guide = (dest / "GUIDE-UTILISATEUR.md").read_text(encoding="utf-8")
    assert "Physique" in guide and "Phone" in guide and "8137" in guide


def test_guide_utilisateur_aligne():
    root = Path(__file__).resolve().parent.parent / "GUIDE-UTILISATEUR.md"
    portable = PORTABLE / "GUIDE-UTILISATEUR.md"
    assert root.is_file() and portable.is_file()
    assert root.read_text(encoding="utf-8") == portable.read_text(encoding="utf-8")
    txt = root.read_text(encoding="utf-8")
    assert "LANCER-PC.bat" in txt
    assert "LANCER-WEB.bat" in txt
    assert "LANCER-PHONE.bat" in txt
    assert "Physique" in txt and "Logique" in txt and "Plan" in txt
    assert "VSDX" in txt or ".vsdx" in txt
    assert "SmartScreen" in txt
    assert "8137" in txt


def test_lisezmoi_dit_quoi_copier():
    txt = (PORTABLE / "LISEZMOI.txt").read_text(encoding="utf-8")
    assert "Quoi copier" in txt
    assert "LANCER-PC.bat" in txt and "LANCER-WEB.bat" in txt
    assert "LANCER-PHONE.bat" in txt
    assert "_internal" in txt
    assert "VCRUNTIME140" in txt or "Visual C++" in txt
    assert "Edge" in txt
    assert "GUIDE-UTILISATEUR.md" in txt


def test_readme_et_claude_citent_le_guide():
    root = Path(__file__).resolve().parent.parent
    readme = (root / "README.md").read_text(encoding="utf-8")
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "GUIDE-UTILISATEUR.md" in readme
    assert "GUIDE-UTILISATEUR.md" in claude


def test_phone_message_box_n_est_pas_avant_le_bind():
    """Régression audit 10/09 : MessageBoxW avant server.run() tue Phone."""
    src = (Path(__file__).resolve().parent.parent / "run.py").read_text(
        encoding="utf-8")
    start = src.index("phone_txt = None")
    end = src.index("server.run()")
    chunk = src[start:end]
    assert '_message_box("RackForgePrime — édition Phone"' not in chunk
    assert "_announce_when_listening" in chunk


def test_phone_ecoute_pendant_une_boite_bloquante(tmp_path, monkeypatch):
    """Même si MessageBox dort 8 s, /api/ping répond en moins de 4 s."""
    kit = tmp_path / "kit"
    kit.mkdir()
    monkeypatch.setenv("RACKFORGE_KIT_DIR", str(kit))
    monkeypatch.delenv("RACKFORGE_WORKSPACE", raising=False)
    monkeypatch.delenv("RACKFORGE_PROJECTS_DIR", raising=False)
    port = None
    for cand in range(18937, 18970):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", cand)) != 0:
                port = cand
                break
    assert port is not None
    helper = Path(__file__).resolve().parent / "phone_box_lente.py"
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["RACKFORGE_KIT_DIR"] = str(kit)
    env["RACKFORGE_WORKSPACE"] = str(kit / "RackForgePrime-Workspace")
    cwd = tmp_path / "ailleurs"
    cwd.mkdir()
    proc = subprocess.Popen(
        [sys.executable, str(helper), "--edition", "phone",
         "--port", str(port), "--no-browser"],
        cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    t0 = time.time()
    ping = None
    last = None
    try:
        for _ in range(40):
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/ping", timeout=0.4) as resp:
                    ping = json.loads(resp.read().decode("utf-8"))
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    json.JSONDecodeError) as exc:
                last = exc
                time.sleep(0.1)
        elapsed = time.time() - t0
        assert ping is not None, f"serveur muet ({last})"
        assert elapsed < 4.0, f"écoute trop tardive ({elapsed:.2f}s) — MessageBox encore bloquante ?"
        assert ping.get("app") == "RackForgePrime"
        assert ping.get("edition") == "phone"
        addr = kit / "DERNIERE-ADRESSE.txt"
        assert addr.is_file(), "DERNIERE-ADRESSE.txt doit exister pendant la boîte"
        assert f"127.0.0.1:{port}" in addr.read_text(encoding="utf-8")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=4)


def test_api_kit_et_ping_edition(monkeypatch):
    monkeypatch.setenv("RACKFORGE_EDITION", "web")
    monkeypatch.setenv("RACKFORGE_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("RACKFORGE_BIND_PORT", "8137")
    ping = client.get("/api/ping").json()
    assert ping["version"] == VERSION and ping["edition"] == "web"
    info = client.get("/api/kit").json()
    assert info["ok"] and info["app"] == "RackForgePrime"
    assert info["version"] == VERSION
    assert "kit_dir" in info and "workspace" in info
    assert any("127.0.0.1" in u for u in info["urls"])
