"""Construit le pack de types constructeurs depuis un manifeste vérifié.

Entrée : un manifeste JSON (liste d'objets {yaml, image, category, modele})
pointant vers netbox-community/devicetype-library. Pour chaque entrée :

1. télécharge le YAML device-type et le convertit avec le MÊME importeur
   que l'application (``import_netbox_yaml``) — u_height et ports exacts ;
2. télécharge l'image d'élévation avant dans ``images-officielles/`` sous
   le nom ``<id-du-type>.<ext>`` (la convention de ``catalog_images``) ;
3. écrit tous les types dans ``types-officiels/pack-constructeurs.json``.

À exécuter volontairement — seul moment où quelque chose sort du poste.

    python scripts/telecharger_pack_constructeurs.py manifeste.json [catalogue]

Sans 2e argument : le catalogue du workspace de dev à côté du script.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rackforge.catalog import ROLE_COLORS  # noqa: E402
from rackforge.importers import import_netbox_yaml  # noqa: E402

RAW = "https://raw.githubusercontent.com/netbox-community/devicetype-library/master"


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage : telecharger_pack_constructeurs.py manifeste.json [catalogue]")
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if len(sys.argv) > 2:
        catalogue = Path(sys.argv[2])
    else:
        catalogue = (Path(__file__).resolve().parent.parent
                     / "RackForgePrime-Workspace" / "catalogue")
    img_dir = catalogue / "images-officielles"
    pack_dir = catalogue / "types-officiels"
    img_dir.mkdir(parents=True, exist_ok=True)
    pack_dir.mkdir(parents=True, exist_ok=True)

    types: list[dict] = []
    ko = 0
    for entry in manifest:
        try:
            text = _fetch(f"{RAW}/{entry['yaml']}").decode("utf-8")
            eq = import_netbox_yaml(text)
            update: dict = {}
            if entry.get("category") in ROLE_COLORS:
                update = {"category": entry["category"],
                          "color": ROLE_COLORS[entry["category"]]}
            eq = eq.model_copy(update=update)
            target = img_dir / f"{eq.id}{Path(entry['image']).suffix.lower()}"
            if not target.exists():
                target.write_bytes(_fetch(f"{RAW}/{entry['image']}"))
            types.append(eq.model_dump())
            print(f"  ok    {eq.id} ({eq.u_height}U, {len(eq.ports)} ports)")
        except Exception as exc:  # réseau, YAML invalide… on continue.
            ko += 1
            print(f"  ÉCHEC {entry.get('yaml', '?')} — {exc}")

    out = pack_dir / "pack-constructeurs.json"
    out.write_text(json.dumps(types, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n{len(types)} type(s) dans {out}, {ko} échec(s)")


if __name__ == "__main__":
    main()
