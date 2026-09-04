"""Fenêtres multiples : fermer un onglet n'éteint pas l'app tant qu'un
autre vit ; la dernière fermée déclenche l'arrêt."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import run  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app)


class _Server:
    should_exit = False


def _reset():
    app.state.clients = {}
    app.state.bye_at = 0.0
    app.state.last_ping = 0.0


def test_deux_fenetres_une_se_ferme_l_app_vit():
    _reset()
    client.get("/api/ping?c=w-a")
    client.get("/api/ping?c=w-b")
    r = client.post("/api/bye", content="w-a").json()
    assert r["restantes"] == 1
    assert app.state.bye_at == 0.0          # pas d'arrêt programmé
    srv = _Server()
    # Chien de garde : w-b vit → pas d'arrêt (on force bye_at ancien pour
    # prouver que ce sont les clients vivants qui protègent).
    app.state.bye_at = time.time() - 10
    app.state.last_ping = time.time() - 20
    import threading
    th = threading.Thread(target=run.watch_window, args=(srv, app, 1, 180, 4), daemon=True)
    th.start()
    time.sleep(2.2)
    assert not srv.should_exit
    srv.should_exit = True


def test_derniere_fenetre_fermee_arrete():
    _reset()
    client.get("/api/ping?c=w-a")
    r = client.post("/api/bye", content="w-a").json()
    assert r["restantes"] == 0 and app.state.bye_at > 0
    srv = _Server()
    app.state.bye_at = time.time() - 10
    app.state.last_ping = time.time() - 20
    run.watch_window(srv, app, grace=1, silence=180, bye_delay=4)
    assert srv.should_exit


def test_rechargement_annule_l_arret():
    _reset()
    client.get("/api/ping?c=w-a")
    client.post("/api/bye", content="w-a")
    assert app.state.bye_at > 0
    client.get("/api/ping?c=w-c")            # F5 : nouvelle fenêtre
    assert app.state.bye_at == 0.0
