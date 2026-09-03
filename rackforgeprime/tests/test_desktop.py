"""Application de bureau : battement de cœur, adieu, instance unique,
port libre, chien de garde de la fenêtre."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import run  # noqa: E402
from app import VERSION, app  # noqa: E402

client = TestClient(app)


def test_ping_et_bye():
    app.state.last_ping = 0.0
    r = client.get("/api/ping").json()
    assert r["ok"] and r["app"] == "RackForgePrime" and r["version"] == VERSION
    assert app.state.last_ping > 0
    client.post("/api/bye")
    assert app.state.bye_at > 0
    client.get("/api/ping")           # un rechargement annule l'adieu
    assert app.state.bye_at == 0.0


def test_instance_unique_et_port_libre():
    # Rien n'écoute sur un port improbable : pas d'instance, port libre.
    assert run.running_instance("127.0.0.1", 8199) is None
    assert run.port_is_free("127.0.0.1", 8199)


class _Server:
    should_exit = False


def test_chien_de_garde_arrete_apres_bye():
    srv = _Server()
    t = time.time()
    app.state.last_ping = t - 20              # dernier ping AVANT l'adieu
    app.state.bye_at = t - 10                 # adieu il y a 10 s, silence depuis
    run.watch_window(srv, app, grace=1, silence=1000, bye_delay=4)
    assert srv.should_exit


def test_chien_de_garde_arrete_apres_silence():
    srv = _Server()
    app.state.bye_at = 0.0
    app.state.last_ping = time.time() - 500   # fenêtre tuée sans adieu
    run.watch_window(srv, app, grace=1, silence=180, bye_delay=4)
    assert srv.should_exit


def test_chien_de_garde_tolere_le_rechargement():
    srv = _Server()
    t = time.time()
    app.state.bye_at = t - 10
    app.state.last_ping = t - 1               # un ping APRÈS l'adieu : on vit
    import threading
    th = threading.Thread(target=run.watch_window,
                          args=(srv, app, 1, 1000, 4), daemon=True)
    th.start()
    time.sleep(2.5)
    assert not srv.should_exit
    srv.should_exit = True                     # fin du test
