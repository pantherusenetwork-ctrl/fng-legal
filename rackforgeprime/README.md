# RackForgePrime

Application **de bureau, 100 % locale**, de schémas de baies réseau : élévation 42U à
l'échelle réelle EIA-310 avec photos constructeurs, vue arrière dérivée, vue logique
VLAN/liens (par baie ou complète), plan d'étage (ville › bâtiment › salle), brassage et
étiquettes TIA-606 générés, matrice de flux, budget PoE, dossier DAT PDF, exports SVG / PNG /
draw.io / Visio (.vsdx).

**Version 1.6.1** — kit portable (un dossier, 3 éditions). DAT :
[`docs/DAT-RACKFORGEPRIME.md`](docs/DAT-RACKFORGEPRIME.md) ; journal :
[`00-CONTEXTE.md`](00-CONTEXTE.md) (dernière section = état exact).
Mode d'emploi USB / autre PC : [`portable/LISEZMOI.txt`](portable/LISEZMOI.txt).

## Lancer

| Usage | Commande |
|---|---|
| Kit portable (USB / autre PC) | Un seul dossier : `LANCER-PC.bat` · `LANCER-WEB.bat` · `LANCER-PHONE.bat` (à côté de l'exe) |
| Développement | `PYTHONIOENCODING=utf-8 python run.py --port 8138 --no-browser` |
| Édition | `python run.py --edition pc\|web\|phone` |
| Diagnostic kit | `python run.py --diagnostic` |
| Tests | `python -m pytest tests -q` |
| Smoke 3 éditions | `python scripts/smoke_editions.py` |
| Compilation kit | `python scripts/construire_kit_portable.py --build` (Windows, onedir) |

Ancien schéma `RackForgePrime-PC` + `RackForgePrime-Web` + `RackForgePrime-Phone`
(les `.bat` faisaient `cd ..\RackForgePrime-PC`) : cassé dès qu'on copie un seul
dossier. Remplacé par le kit unique.

## Arborescence

```
rackforgeprime/
├── run.py                  point d'entrée (kit, 3 éditions, fenêtre, chien de garde)
├── backend/app.py          FastAPI : API JSON + frontend statique + /api/kit
├── backend/rackforge/      package : modèle, SVG/PDF/draw.io/VSDX, kit portable
├── frontend/               index.html · css/app.css · js/app.js · assets/
├── portable/               LANCER-*.bat · _commun.cmd · LISEZMOI.txt
├── scripts/                construire_kit_portable.py · smoke_editions.py
├── tests/                  pytest (dont test_portable + smoke 3 éditions)
├── docs/                   DAT-RACKFORGEPRIME.md · SPEC.md · ARCHITECTURE.md
└── RackForgePrime-Workspace/  (gitignoré) projets · catalogue · exports · sauvegardes
```

## Règles gravées

- Échelle réelle au mm : `RACK_W = 440 px` pour 482,6 mm → `U_PX = 40.5` ; images jamais étirées.
- Aucun nom sur le dessin sauf hostname saisi ; un dessin = une vraie photo de façade de face.
- Le backend valide tout (422 en français) ; le JSON est la source de vérité.
- La version change à chaque exe déployé ; rien n'est supprimé (poubelle à valider).
- Le kit se copie **en entier** (exe + `_internal\` + workspace + lanceurs). Jamais l'exe seul.
