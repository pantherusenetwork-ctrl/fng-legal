# RackForgePrime

Application **de bureau, 100 % locale**, de schémas de baies réseau : élévation 42U à
l'échelle réelle EIA-310 avec photos constructeurs, vue arrière dérivée, vue logique
VLAN/liens (par baie ou complète, **auto-layout compact**), plan d'étage (ville ›
bâtiment › salle), brassage et étiquettes TIA-606 générés, matrice de flux, budget PoE,
dossier DAT PDF, exports SVG / PNG / draw.io / Visio (.vsdx avec connecteurs).

**Version 1.7.0** — le DAT complet est dans
[`docs/DAT-RACKFORGEPRIME.md`](docs/DAT-RACKFORGEPRIME.md) ; le journal de bord dans
[`00-CONTEXTE.md`](00-CONTEXTE.md) (dernière section = état exact).

Vue physique : **pas de noms** sur les équipements par défaut (bouton Noms). Impression
à l'échelle 1:10 / 1:20 écrite sur la page. Export SVG léger (dessin, sans photos)
pour éviter les ~11 Mo d'OLYMPE.

## Lancer

| Usage | Commande |
|---|---|
| Application (exe) | `RackForgePrime-PC\RackForgePrime.exe` — fenêtre dédiée, port 8137, fermer la fenêtre = quitter |
| Navigateur / téléphone | `RackForgePrime-Web\LANCER-WEB.bat` · `RackForgePrime-Phone\LANCER-PHONE.bat` |
| Développement | `set PYTHONIOENCODING=utf-8 && .venv\Scripts\python.exe run.py --port 8138 --no-browser` |
| Tests | `.venv\Scripts\python.exe -m pytest tests -q` (**105** verts au 07/09/2026) |
| Compilation | recette PyInstaller au § 9 du DAT (chemins absolus, dossier de build court, version bumpée avant) |

Instance unique : si 8137 (ou 8138–8146) répond déjà RackForgePrime, on **rouvre**
cette fenêtre — on ne lance pas un second serveur.

## Arborescence

```
rackforgeprime/
├── run.py                  point d'entrée (workspace, instance unique, fenêtre, chien de garde)
├── backend/app.py          FastAPI : API JSON + frontend statique
├── backend/rackforge/      modèle, placement, SVG/PDF/draw.io/VSDX, flux, PoE, câbles, appariement
├── frontend/               index.html · css/app.css · js/app.js (vanilla, SVG natif) · assets/
├── tests/                  pytest
├── .claude/agents/         agent « ajoute-et-corrige » (catalogue / images / packs / docs)
├── docs/                   DAT-RACKFORGEPRIME.md · SPEC.md · ARCHITECTURE.md · PLAN_DESIGN.md
├── assets/icon.ico
└── RackForgePrime-Workspace/  (gitignoré) projets · catalogue · exports · sauvegardes
```

## Règles gravées

- Échelle réelle au mm : `RACK_W = 440 px` pour 482,6 mm → `U_PX = 40.5` ; images jamais étirées.
- Aucun nom forcé sur le dessin physique (toggle Noms, off par défaut).
- Le backend valide tout (422 en français) ; le JSON est la source de vérité.
- La version change à chaque exe déployé ; rien n'est supprimé (poubelle à valider).
