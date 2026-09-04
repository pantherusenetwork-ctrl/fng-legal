# RackForgePrime

Application **de bureau, 100 % locale**, de schémas de baies réseau : élévation 42U à
l'échelle réelle EIA-310 avec photos constructeurs, vue arrière dérivée, vue logique
VLAN/liens (par baie ou complète), plan d'étage (ville › bâtiment › salle), brassage et
étiquettes TIA-606 générés, matrice de flux, budget PoE, dossier DAT PDF, exports SVG / PNG /
draw.io / Visio (.vsdx).

**Version 1.5.2** — le DAT complet de l'application est dans
[`docs/DAT-RACKFORGEPRIME.md`](docs/DAT-RACKFORGEPRIME.md) ; le journal de bord dans
[`00-CONTEXTE.md`](00-CONTEXTE.md) (dernière section = état exact).

## Lancer

| Usage | Commande |
|---|---|
| Application (exe) | `RackForgePrime-PC\RackForgePrime.exe` — fenêtre dédiée, port 8137, fermer la fenêtre = quitter |
| Navigateur / téléphone | `RackForgePrime-Web\LANCER-WEB.bat` · `RackForgePrime-Phone\LANCER-PHONE.bat` |
| Développement | `set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe run.py --port 8138 --no-browser` |
| Tests | `.venv\Scripts\python.exe -m pytest tests -q` (88 verts au 04/09/2026) |
| Compilation | recette PyInstaller au § 9 du DAT (chemins absolus, dossier de build court, version bumpée avant) |

## Arborescence

```
rackforgeprime/
├── run.py                  point d'entrée (workspace, instance unique, fenêtre, chien de garde)
├── backend/app.py          FastAPI : API JSON + frontend statique
├── backend/rackforge/      package pur Python : modèle, placement, moteurs SVG/PDF/draw.io/VSDX, flux, PoE, sauvegarde
├── frontend/               index.html · css/app.css · js/app.js (vanilla, SVG natif) · assets/
├── tests/                  pytest
├── docs/                   DAT-RACKFORGEPRIME.md · SPEC.md · ARCHITECTURE.md · PLAN_DESIGN.md · RECHERCHE_VISUELLE.md
├── assets/icon.ico
└── RackForgePrime-Workspace/  (gitignoré) projets · catalogue (packs, images, bibliothèque, formes) · exports · sauvegardes
```

## Règles gravées

- Échelle réelle au mm : `RACK_W = 440 px` pour 482,6 mm → `U_PX = 40.5` ; images jamais étirées.
- Aucun nom sur le dessin sauf hostname saisi ; un dessin = une vraie photo de façade de face.
- Le backend valide tout (422 en français) ; le JSON est la source de vérité.
- La version change à chaque exe déployé ; rien n'est supprimé (poubelle à valider).
