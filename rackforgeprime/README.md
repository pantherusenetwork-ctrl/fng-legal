# RackForgePrime

Application **locale** (zéro abonnement, zéro cloud) de schémas d'infrastructure
pour ingénieurs réseau : **élévations de baies fidèles au terrain** (42U, snap U
exact, collisions refusées) aujourd'hui, **schéma logique** (VLANs, flux, liens)
demain. Le JSON du projet est la source de vérité ; SVG et PDF sont des vues
générées.

## Démarrage

```bash
cd rackforgeprime
pip install -r requirements.txt
python run.py
# → http://127.0.0.1:8137
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

## Suite (dans l'ordre)

1. Import YAML NetBox devicetype-library + images/SVG custom → palette.
2. Parse PDF datasheet (modèle, U, conso, ports) → proposition de type.
3. Éditeur logique (VLANs, flux, liens) sur les mêmes IDs d'équipements.
4. Export CSV du brassage, VSDX, XML draw.io.
5. Packaging Windows (PyInstaller).
