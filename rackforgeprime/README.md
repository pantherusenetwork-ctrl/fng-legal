# RackForgePrime

Application **de bureau, 100 % locale**, de schémas de baies réseau : élévation 42U à
l'échelle réelle EIA-310 avec photos constructeurs, vue arrière dérivée, vue logique
VLAN/liens (par baie ou complète, **auto-layout compact**), plan d'étage (ville ›
bâtiment › salle), brassage et étiquettes TIA-606 générés, matrice de flux, budget PoE,
dossier DAT PDF, exports SVG / PNG / draw.io / Visio (.vsdx avec connecteurs).

**Version 1.7.1** — features éditeur 1.7.0 + kit portable USB (3 éditions) + correctif
Phone (le serveur écoute avant la boîte d'URL). DAT :
[`docs/DAT-RACKFORGEPRIME.md`](docs/DAT-RACKFORGEPRIME.md) ; journal :
[`00-CONTEXTE.md`](00-CONTEXTE.md) (dernière section = état exact).
**Guide utilisateur** : [`GUIDE-UTILISATEUR.md`](GUIDE-UTILISATEUR.md)
(recopié dans le kit : [`portable/GUIDE-UTILISATEUR.md`](portable/GUIDE-UTILISATEUR.md)).
Mode d'emploi USB / autre PC : [`portable/LISEZMOI.txt`](portable/LISEZMOI.txt).

Vue physique : **pas de noms** sur les équipements par défaut (bouton Noms). Impression
à l'échelle 1:10 / 1:20 écrite sur la page. Export SVG léger (dessin, sans photos)
pour éviter les ~11 Mo d'OLYMPE.

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

Instance unique : si 8137 (ou 8138–8146) répond déjà RackForgePrime, on **rouvre**
cette fenêtre — on ne lance pas un second serveur.

## Arborescence

```
rackforgeprime/
├── GUIDE-UTILISATEUR.md    mode d'emploi FR (PC / Web / Phone, vues, exports)
├── run.py                  point d'entrée (kit, 3 éditions, fenêtre, chien de garde)
├── backend/app.py          FastAPI : API JSON + frontend statique + /api/kit
├── backend/rackforge/      modèle, SVG/PDF/draw.io/VSDX, câbles, appariement, kit
├── frontend/               index.html · css/app.css · js/app.js · assets/
├── portable/               LANCER-*.bat · _commun.cmd · LISEZMOI.txt · GUIDE
├── scripts/                construire_kit_portable.py · smoke_editions.py
├── tests/                  pytest (dont test_portable + smoke 3 éditions + v1.7)
├── .claude/agents/         agent « ajoute-et-corrige » (catalogue / images / packs)
├── docs/                   DAT-RACKFORGEPRIME.md · SPEC.md · ARCHITECTURE.md
└── RackForgePrime-Workspace/  (gitignoré) projets · catalogue · exports · sauvegardes
```

## Règles gravées

- Échelle réelle au mm : `RACK_W = 440 px` pour 482,6 mm → `U_PX = 40.5` ; images jamais étirées.
- Aucun nom forcé sur le dessin physique (toggle Noms, off par défaut).
- Le backend valide tout (422 en français) ; le JSON est la source de vérité.
- La version change à chaque exe déployé ; rien n'est supprimé (poubelle à valider).
- Le kit se copie **en entier** (exe + `_internal\` + workspace + lanceurs). Jamais l'exe seul.
- Ne pas inventer de hostname / VLAN / nom de salle OLYMPE.
