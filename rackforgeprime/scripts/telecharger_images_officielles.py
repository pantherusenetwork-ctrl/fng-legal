"""Télécharge les images d'élévation officielles des types du catalogue.

Source : netbox-community/devicetype-library (GitHub, images communautaires
reprises des visuels constructeurs). À exécuter volontairement — c'est le
SEUL moment où quelque chose sort du poste ; l'application, elle, reste
100 % locale et ne lit que le dossier rempli ici.

    python scripts/telecharger_images_officielles.py [dossier-catalogue]

Sans argument : le dossier ``RackForgePrime-Workspace/catalogue`` à côté du
script (cas du dépôt de dev). Les images sont posées dans
``images-officielles/<id-du-type>.<ext>`` — le nommage attendu par
``backend/rackforge/catalog_images.py``.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RAW = ("https://raw.githubusercontent.com/netbox-community/"
       "devicetype-library/master/elevation-images")

# id de type catalogue -> chemin dans elevation-images.
# NB : pour le 9200L-24T, la librairie n'a que le C9200-24T — faceplate
# quasi identique, retenue comme visuel en attendant mieux.
IMAGES = {
    "cisco-catalyst-9300-48p": "Cisco/cisco-c9300-48p.front.png",
    "cisco-catalyst-9200l-24t": "Cisco/cisco-c9200-24t.front.jpg",
    "aruba-6300m-48g": "HPE/hpe-aruba-6300m-48g-4sfp56.front.png",
    "fortinet-fortigate-100f": "Fortinet/fortinet-fg-100f.front.png",
    "hpe-proliant-dl380-g11": "HPE/hpe-proliant-dl380-gen11.front.png",
    # Pas d'image dans la librairie pour : FortiGate 600E, APC Smart-UPS
    # 3000, Dell R650 — ils gardent le placeholder dessiné.
}


def main() -> None:
    if len(sys.argv) > 1:
        catalogue = Path(sys.argv[1])
    else:
        catalogue = (Path(__file__).resolve().parent.parent
                     / "RackForgePrime-Workspace" / "catalogue")
    dest = catalogue / "images-officielles"
    dest.mkdir(parents=True, exist_ok=True)
    ok, ko = 0, 0
    for type_id, rel in IMAGES.items():
        target = dest / f"{type_id}{Path(rel).suffix.lower()}"
        if target.exists():
            print(f"  déjà là   {target.name}")
            ok += 1
            continue
        url = f"{RAW}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                target.write_bytes(resp.read())
            print(f"  téléchargé {target.name}")
            ok += 1
        except OSError as exc:
            print(f"  ÉCHEC      {target.name} — {exc}")
            ko += 1
    print(f"\n{ok} image(s) en place, {ko} échec(s) → {dest}")


if __name__ == "__main__":
    main()
