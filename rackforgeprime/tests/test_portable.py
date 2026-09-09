"""Kit portable : chemins indépendants du cwd, 3 éditions, lanceurs."""

from __future__ import annotations

import os
import sys
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
    assert VERSION == "1.6.1"


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
    assert (dest / "RackForgePrime-Workspace" / "projets").is_dir()
    assert (dest / "KIT-PORTABLE.txt").is_file()


def test_lisezmoi_dit_quoi_copier():
    txt = (PORTABLE / "LISEZMOI.txt").read_text(encoding="utf-8")
    assert "Quoi copier" in txt
    assert "LANCER-PC.bat" in txt and "LANCER-WEB.bat" in txt
    assert "LANCER-PHONE.bat" in txt
    assert "_internal" in txt
    assert "VCRUNTIME140" in txt or "Visual C++" in txt
    assert "Edge" in txt


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
