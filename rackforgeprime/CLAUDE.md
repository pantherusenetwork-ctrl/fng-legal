# RackForgePrime : consignes pour Claude Code

Tu travailles sur RackForgePrime, application 100 % locale de schémas de baies
réseau (élévation 42U à l'échelle réelle EIA-310, vue logique, brassage, exports).

## À faire EN PREMIER à chaque session
1. Lire `00-CONTEXTE.md` en entier : c'est le journal de bord (sections
   « Pont d'Hemingway »). La DERNIÈRE section donne l'état exact et la
   « Prochaine étape exacte ». Ne jamais repartir de zéro.
2. Vérifier `git status` et `git log -3`.
3. Lancer les tests : `python -m pytest tests -q` (**105** verts attendus au
   07/09/2026). ⛔ RÈGLE PANTHER : la version (`backend/app.py` VERSION + badge
   `#brand-version` de `frontend/index.html`) CHANGE À CHAQUE exe déployé.

## Repères
- Code : ce dossier (`backend/`, `frontend/`, `tests/`, `docs/`).
- Agent spécialisé catalogue/images/packs/docs : `.claude/agents/ajoute-et-corrige.md`
  (pas un fourre-tout — voir aussi le DAT § 13).
- Serveur de dev : `run.py --port 8138 --no-browser` (run.py écoute 8137 par
  défaut = le port de l'exe), avec `PYTHONIOENCODING=utf-8`. `find_running_rackforge`
  sonde 8137–8146 : une instance déjà vivante → on rouvre sa fenêtre, on ne
  rebind pas (plus de port fantôme type 10048).
- Exe déployé : `..\..\RackForgePrime-PC\RackForgePrime.exe` (port 8137),
  workspace `..\..\RackForgePrime-PC\RackForgePrime-Workspace\`.
  Avant de recompiler : fermer l'app (fichier verrouillé sinon).
  Archiver l'ancien exe dans `..\..\SAUVEGARDES\` (suffixe -ancien-AAAA-MM-JJ-x.exe).
- Projet démo `reseau-maison.json` et `salle-olympe` existent en DEUX copies
  (workspace du dépôt + workspace de l'exe) : modifier les deux.
- Le workspace est gitignoré : images/bibliothèque vivent sur disque seulement.

## Règles gravées (ne jamais revenir dessus)
- Échelle réelle : MM_19_POUCES=482.6, RACK_W=440 px, U_PX=40.5. Images
  toujours en preserveAspectRatio meet.
- Aucun nom forcé sur le dessin physique : le toggle « Noms » est **off** par
  défaut (v1.6.0+). Un hostname saisi ne s'écrit que si Noms est actif.
- Toute manipulation de chemin UNC (\\192.168.1.138\...) passe par un fichier
  .py écrit avec Write, jamais par un heredoc bash.
- Ne pas inventer de hostname / VLAN / nom de salle OLYMPE : `[à vérifier]`.

## En fin de session
- Ajouter une section « Pont d'Hemingway » datée dans `00-CONTEXTE.md` :
  fait / prochaine étape exacte / questions en attente pour Panther.
- Commiter le travail (message en français) et pousser la branche.
