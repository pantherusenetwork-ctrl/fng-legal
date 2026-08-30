# RackForgePrime

Application **locale** (zéro abonnement, zéro cloud) de schémas d'infrastructure
pour ingénieurs réseau : **élévations de baies fidèles au terrain** (42U, snap U
exact, collisions refusées) aujourd'hui, **schéma logique** (VLANs, flux, liens)
demain. Le JSON du projet est la source de vérité ; SVG et PDF sont des vues
générées.

## Démarrage

### Exécutable Windows (recommandé sur le poste de travail)

L'exe est compilé automatiquement par GitHub Actions à chaque push :
onglet **Actions** du dépôt → run « Build RackForgePrime Windows exe » →
**Artifacts** → `RackForgePrime-Windows`. Dézippez où vous voulez et
double-cliquez `RackForgePrime.exe` : le navigateur s'ouvre sur
l'application, et l'**espace de travail** est créé à côté de l'exe au
premier lancement :

```
RackForgePrime-Workspace/
├── projets/      ← les JSON de projets (source de vérité)
├── exports/      ← vos SVG / PDF / CSV livrés
├── catalogue/    ← YAML NetBox et faceplates custom à importer
├── datasheets/   ← PDF constructeurs à importer
└── LISEZMOI.txt
```

Tout est local : le serveur n'écoute que sur 127.0.0.1, rien ne sort du poste.

### Depuis les sources (dev)

```bash
cd rackforgeprime
pip install -r requirements.txt
python run.py            # → http://127.0.0.1:8137, navigateur auto-ouvert
python run.py --no-browser --port 9000   # variantes
```

## Le prototype fait déjà

- Baie(s) 42U graduées en U (1U = 44,45 mm, échelle exacte partout).
- Palette gauche par rôle (switch, firewall, patch panel, UPS, serveur,
  obturateur, passe-câbles) filtrable ; catalogue modélisé sur du matériel réel
  (Cisco, Fortinet, HPE/Aruba, Dell, APC).
- **Drag-and-drop avec snap U** : fantôme cyan sur U libre, rouge + refus sur
  collision. Déplacement d'équipements posés, y compris entre baies.
- Multi-baies (bouton « + Baie »).
- Métadonnées par équipement : hostname, rôle, VLAN, prise murale, brassage
  (port/prise/VLAN/usage), n° de série, notes.
- **Tableau de brassage généré** depuis les métadonnées.
- Stats live par baie : U occupés/libres, watts cumulés.
- **Exports SVG** (groupes nommés, rééditable draw.io/Inkscape), **PDF**
  (conversion locale du SVG) et **JSON** (source régénérable). Ouverture d'un
  JSON existant.
- Le backend est l'autorité : un JSON qui chevauche deux équipements est
  refusé avec un message précis, à la sauvegarde comme à l'export.

## Tests

```bash
cd rackforgeprime
python -m pytest tests/ -v
```

## Documentation

- [`docs/RECHERCHE_VISUELLE.md`](docs/RECHERCHE_VISUELLE.md) — étude TSS /
  PATCHBOX / NetBox / Visio / draw.io et DA retenue.
- [`docs/SPEC.md`](docs/SPEC.md) — écrans, flux, data model JSON.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack, arborescence, API.

## Imports de modèles (phase 2 — livrée)

- **YAML NetBox devicetype-library** : glissez un fichier de
  `netbox-community/devicetype-library` → constructeur, modèle, hauteur U et
  ports importés (0.5U arrondi au U supérieur, jamais en dessous du réel).
- **PDF datasheet constructeur** : extraction heuristique (modèle, hauteur U,
  conso, ports) ; les champs devinés sont marqués en ambre et **rien n'entre
  dans la palette sans validation humaine**.
- **Image / SVG custom** : une faceplate photo devient un modèle de palette ;
  l'image vit en data URI dans le JSON du projet (auto-suffisant).
- **« Remplacer par image officielle »** sur tout équipement posé : la photo
  constructeur remplace le placeholder, à l'écran comme dans les exports
  SVG et PDF.
- **Export CSV du brassage** (séparateur `;`, BOM UTF-8 pour Excel FR).

## Schéma logique (phase 3 — livrée)

- Bascule **Physique / Logique** dans la barre supérieure.
- Nœuds = les mêmes équipements que les baies (mêmes IDs) ; auto-layout en
  couches façon DAT (firewall en haut → routeurs → cœur → brassage →
  serveurs), positions réajustables à la souris et persistées dans le JSON.
- Liens typés (trunk / access / uplink / HA) : coudes orthogonaux façon
  Visio/Lucid, étiquette + ports au point médian, pastilles VLAN colorées.
- Gestion des VLANs du projet (id, nom, couleur) + légende intégrée au dessin.
- **Un seul moteur de rendu** : la vue à l'écran EST le SVG du backend ;
  les boutons SVG/PDF exportent la vue active (physique ou logique).

## Suite (dans l'ordre)

1. Exports VSDX et XML draw.io.
2. OCR des datasheets scannées.
3. Matrice de flux générée depuis les liens.
4. Packaging Windows (PyInstaller).
