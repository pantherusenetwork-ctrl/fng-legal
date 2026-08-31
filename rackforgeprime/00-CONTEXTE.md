# RackForgePrime — contexte de travail

Application 100 % locale de schémas de baies réseau (élévation 42U, vue logique
VLAN/liens, tableau de brassage généré). Code dans ce dossier, branche
`claude/rackforgeprimes-foundations-y41pt4`. Exe déployé sur
`C:\Users\koyon\Desktop\RackForgePrime\` (serveur de dev : port 8138,
l'exe garde 8137).

## État au 31/08/2026

**🎯 9/10 partout — officiel (verdict jury v13)** : prise en main 9,0 ·
métier réseau 9,0 · esthétique 9,0 (13 notations, de 5,8 à 9,0).
47 tests pytest verts. Exe recompilé et déployé le 31/08 à 16h30
(anciens conservés `-ancien-2026-08-30.exe` / `-ancien-2026-08-31.exe`).

4 thèmes : Sombre, Clair, Pastel (lavande) et Nuit (noir pur).
Exports : SVG, PDF (dossier avec cartouche + page logique portrait),
PNG, CSV, étiquettes TIA-606, draw.io.

## 🌉 Pont d'Hemingway — prochaine étape exacte

**Vue plan d'étage** : le 31/08 Panther a montré 2 captures d'un outil
type Patchdocs (plan d'étage avec équipements posés dans les pièces,
liaisons dessinées, couverture des AP en pointillés orange, panneau
Floor Settings avec opacité/contraste du plan). C'est le prochain gros
chantier qu'il veut. À concevoir : import d'une image de plan (PNG/JPG),
pose d'équipements dessus, liaisons vers la baie.

Autres attentes notées :
- Faces avant photoréalistes style Lucidchart (il a montré la baie Dell
  de Lucid : « c'est propre ») — améliorer la netteté/cadrage de nos
  images officielles dans l'élévation.
- Micro-frictions résiduelles du juge v13 (non bloquantes) : pastille
  n°3 légèrement détachée de son arête, faisceau SW↔PP dense, réserve
  blanche à droite de la page logique portrait.
- Backlog : matrice de flux générée, vue arrière des baies, appariement
  en masse panneau↔switch, budget PoE cumulé, export VSDX, OCR datasheets.

## Pièges connus

- Serveur : `PYTHONIOENCODING=utf-8` obligatoire en dev (le print de
  démarrage contient une flèche →) ; l'exe est blindé depuis le 31/08.
- Après un changement de modèle Pydantic : RELANCER le serveur avant
  tout PUT (l'ancien process efface les nouveaux champs).
- Le projet démo `reseau-maison.json` existe en DEUX copies (workspace
  du dépôt + workspace de l'exe sur le Bureau) — modifier les deux.
