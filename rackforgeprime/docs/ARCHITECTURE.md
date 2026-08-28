# RackForgePrime — Architecture & stack

## Stack

| Couche | Choix | Pourquoi |
|--------|-------|----------|
| Cœur | **Python 3.11+** | parse PDF futur, modèle de données, génération SVG/PDF |
| Modèle | **Pydantic v2** | validation stricte du JSON (snap U, collisions) |
| Serveur local | **FastAPI + Uvicorn** | UI web locale, API JSON, zéro cloud |
| Frontend | **HTML/CSS/JS vanilla** (SVG natif) | drag-and-drop fluide sans build step ; le rendu écran EST le SVG d'export |
| Export SVG | générateur Python maison (`svg_export.py`) | groupes nommés, rééditable draw.io/Inkscape |
| Export PDF | **svglib + reportlab** | conversion SVG→PDF 100 % locale, aucun binaire système |
| Tests | **pytest** | moteur de placement et exports testés |
| Packaging (plus tard) | PyInstaller | exécutable Windows une fois stable |

Principe clé : **une seule source de rendu**. Le backend génère le SVG de la
baie ; le frontend rend la même géométrie (mêmes constantes d'échelle) ; le PDF
est une conversion du SVG. Pas trois dessins qui divergent.

## Arborescence

```
rackforgeprime/
├── docs/
│   ├── RECHERCHE_VISUELLE.md   # étude TSS / PATCHBOX / NetBox / Visio / draw.io
│   ├── SPEC.md                 # écrans, flux, data model JSON
│   └── ARCHITECTURE.md         # ce fichier
├── backend/
│   ├── app.py                  # FastAPI : API + sert le frontend
│   └── rackforge/
│       ├── __init__.py
│       ├── models.py           # Pydantic : Project, Rack, RackItem, EquipmentType…
│       │                       #   + moteur de placement (snap U, collisions)
│       ├── catalog.py          # catalogue intégré (Cisco, Fortinet, HPE/Aruba, APC…)
│       ├── svg_export.py       # élévation de baie → SVG (groupes nommés)
│       ├── pdf_export.py       # SVG → PDF (svglib/reportlab)
│       └── storage.py          # sauvegarde/chargement des projets (~/.rackforgeprime ou ./projects)
├── frontend/
│   ├── index.html              # UI française : palette / canvas / métadonnées
│   ├── css/app.css             # DA sombre futuriste sobre
│   └── js/app.js               # drag-and-drop, snap U, collisions, appels API
├── tests/
│   ├── test_placement.py       # snap, collisions, bornes de baie
│   └── test_exports.py         # SVG bien formé, PDF non vide, JSON round-trip
├── examples/
│   └── projet-demo.json        # projet exemple (1 baie 42U peuplée)
├── requirements.txt
└── run.py                      # point d'entrée : `python run.py` → http://127.0.0.1:8137
```

## API locale

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/` | UI (frontend statique) |
| GET | `/api/catalog` | types d'équipements disponibles |
| POST | `/api/validate` | valide un projet (placement, collisions) → erreurs détaillées |
| POST | `/api/export/svg` | projet JSON → SVG (une baie ou toutes) |
| POST | `/api/export/pdf` | projet JSON → PDF |
| POST | `/api/patch-table` | projet JSON → tableau de brassage (JSON structuré) |
| GET/PUT | `/api/projects/{name}` | chargement / sauvegarde locale |
| GET | `/api/projects` | liste des projets locaux |

Le frontend garde l'état du projet en mémoire (et `localStorage` en secours) ;
le backend est **l'autorité de validation** : tout export ou sauvegarde repasse
par le moteur de placement Pydantic. Un JSON trafiqué à la main qui chevauche
deux équipements est refusé avec un message précis.

## Extension vendable (plus tard, sans réécriture)

- `rackforge/` est un package pur-Python sans dépendance au serveur → utilisable
  en CLI, en lib, ou derrière une future gestion de licences.
- Le catalogue est une liste de `EquipmentType` sérialisables → marketplace de
  packs constructeurs possible.
- Les exports sont des fonctions pures `Project -> bytes` → ajout VSDX/draw.io
  = un module de plus, rien à toucher ailleurs.
