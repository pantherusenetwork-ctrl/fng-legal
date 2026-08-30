"""Chargement des images officielles depuis le dossier catalogue."""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.catalog import BUILTIN_TYPES
from rackforge.catalog_images import SUBDIR, apply_official_images

# PNG 1x1 valide (le plus petit possible) pour simuler une image officielle.
_PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBg"
    "AAAABQABh6FO1AAAAABJRU5ErkJggg=="
)


def test_sans_dossier_configure_les_types_sont_inchanges(monkeypatch):
    monkeypatch.delenv("RACKFORGE_CATALOG_DIR", raising=False)
    types = apply_official_images(BUILTIN_TYPES)
    assert types == BUILTIN_TYPES


def test_image_presente_chargee_en_data_uri(tmp_path, monkeypatch):
    d = tmp_path / SUBDIR
    d.mkdir()
    (d / "fortinet-fortigate-100f.png").write_bytes(_PNG_1PX)
    monkeypatch.setenv("RACKFORGE_CATALOG_DIR", str(tmp_path))
    types = {t.id: t for t in apply_official_images(BUILTIN_TYPES)}
    img = types["fortinet-fortigate-100f"].faceplate_image
    assert img is not None and img.startswith("data:image/png;base64,")
    # Les autres types restent sans image (placeholder dessiné).
    assert types["fortinet-fortigate-600e"].faceplate_image is None
    # Les objets du catalogue intégré ne sont pas mutés (copies).
    assert all(t.faceplate_image is None for t in BUILTIN_TYPES)


def test_image_existante_du_type_non_ecrasee(tmp_path, monkeypatch):
    d = tmp_path / SUBDIR
    d.mkdir()
    (d / "custom-type.png").write_bytes(_PNG_1PX)
    monkeypatch.setenv("RACKFORGE_CATALOG_DIR", str(tmp_path))
    deja = BUILTIN_TYPES[0].model_copy(update={
        "id": "custom-type",
        "faceplate_image": "data:image/png;base64,QUJD",
    })
    (out,) = apply_official_images([deja])
    assert out.faceplate_image == "data:image/png;base64,QUJD"
