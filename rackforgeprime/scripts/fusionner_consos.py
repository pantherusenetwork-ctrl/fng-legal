"""Fusionne des consommations (watts) dans un pack de types constructeurs.

    python scripts/fusionner_consos.py consos.json [catalogue ...]

``consos.json`` : {"<id-du-type>": {"w": 45, "estime": false}, ...}
Chaque catalogue passé (défaut : celui du workspace de dev) voit son
``types-officiels/pack-constructeurs.json`` mis à jour — uniquement les
types dont power_w vaut 0 (jamais d'écrasement d'une valeur existante).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage : fusionner_consos.py consos.json [catalogue ...]")
    consos: dict = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    catalogues = [Path(p) for p in sys.argv[2:]] or [
        Path(__file__).resolve().parent.parent
        / "RackForgePrime-Workspace" / "catalogue"]
    for cat in catalogues:
        pack_path = cat / "types-officiels" / "pack-constructeurs.json"
        types = json.loads(pack_path.read_text(encoding="utf-8"))
        maj, estimes = 0, 0
        for t in types:
            entry = consos.get(t["id"])
            if entry and t.get("power_w", 0) == 0 and entry.get("w"):
                t["power_w"] = float(entry["w"])
                maj += 1
                if entry.get("estime"):
                    estimes += 1
        pack_path.write_text(json.dumps(types, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        print(f"{pack_path} : {maj} consommations posées ({estimes} estimées)")
    restants = [t["id"] for t in types if t.get("power_w", 0) == 0
                and t.get("category") not in ("patch-panel", "blank",
                                              "cable-mgmt")]
    if restants:
        print("Encore à 0 W :", ", ".join(restants))


if __name__ == "__main__":
    main()
