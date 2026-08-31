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

4 thèmes : Sombre, Clair, Kaki (olive foncé, accent ambre) et Nuit (noir pur). Version affichée : v1.0.0 (badge UI + app.py VERSION, à bumper ensemble).
Exports : SVG, PDF (dossier avec cartouche + page logique portrait),
PNG, CSV, étiquettes TIA-606, draw.io.

**Campagne de test 6 agents (31/08 soir) : 194 tests.** Aucun 500 sur
l'API, exports tous valides, UI sans erreur JS, exe Bureau opérationnel.
Tout ce qui a été trouvé (1 majeur NaN, 1 majeur palette, 4 mineurs) a
été corrigé le soir même ; exe redeployé à 18h06.

**2e campagne 6 agents (31/08, ~21h) : 237 tests** sur les fonctions et
les images constructeurs — app saine, 83/91 types avec image officielle,
0 ratio aberrant. 4 correctifs mineurs commités (MIME sniffé, WAN borné,
422 lisibles, commentaire CSS) — ⚠️ **pas encore dans l'exe déployé** :
recompiler au prochain redémarrage de l'app (elle tournait pendant le
correctif, fichier verrouillé). **Images v2 (31/08, ~22h, 3 agents)** : audit des 83 images + chasse
NetBox devicetype-library + réadaptation Pillow en série (rognage,
≤2000 px, ré-encodage). Résultat : 4 remplacées haute résolution,
34 rognées, trou APC Smart-UPS 3000 comblé (84 types avec image),
12,74 → 8,70 Mo, catalogues DEV et EXE md5-identiques, originaux dans
`_originaux-2026-08-31\` de chaque catalogue. ⚠️ Le workspace est
gitignoré : ces images ne vivent QUE sur disque — les inclure dans
toute sauvegarde. Restent 2 trous sans source NetBox (fortigate-600e,
poweredge-r650) et 11 modèles à ~700 px sans meilleure source connue.

## Principe directeur (Panther, 31/08 soir)

**« On doit avoir des options, avoir le choix, la liberté »** — et être
« aussi complet que Visio ou draw.io mais en qualité supérieure ».
Traduction : jamais d'action bloquée sans raison (suppression, options au
clic droit partout), et combler la mécanique d'éditeur généraliste.

**Feuille de route complétude (2 analystes Visio + draw.io, 31/08, ~55
fonctions comparées)** — acquis : le métier réseau bat déjà les deux
(brassage généré, trace de câble, validation 422, livrables DAT/TIA-606,
146 types/135 photos). Manques par priorité :
1. ~~Zoom / pan du canvas~~ ✅ FAIT le 31/08 au soir (Ctrl+molette, boutons, pan)
2. **Multi-sélection + déplacement groupé** (haute, moyen)
3. **Copier/coller clavier** Ctrl+C/V, Suppr, flèches (moyenne, petit)
4. **Connecteurs éditables** (waypoints/ancrages) (haute, gros)
5. **Export VSDX** (haute, moyen — format d'échange entreprise)
6. Multi-pages libres, calques, groupes/verrouillage (moyenne, gros)
7. Impression à l'échelle, styles à l'objet, texte riche (moyenne)

## 🌉 Pont d'Hemingway — prochaine étape exacte

**Vue plan d'étage + navigation hiérarchique** : le 31/08 Panther a
montré 2 captures d'un outil type Patchdocs (équipements posés sur le
plan, liaisons, couverture AP, réglages opacité/contraste du plan) puis
précisé le parcours voulu : **on clique la VILLE → le BÂTIMENT → la
SALLE (ex. « OLYMPE ») → les baies avec leur nom**. C'est le prochain
gros chantier. À concevoir : hiérarchie site/bâtiment/salle dans le
projet, import d'une image de plan (PNG/JPG), pose d'équipements dessus.

**Projet « salle-olympe »** (dans les 2 workspaces) : reproduction des
5 baies photographiées par Panther le 31/08 — A6KVC (coffret mural 12U),
ATLAS (brassage + 2 FortiGate HA), PROMETHEE (opérateurs : SEWAN, CCR,
2 Livebox BTIP, tiroirs optiques), CHRONOS (voix AudioCodes, UCOPIA,
5 ProLiant), TITAN (2 Proxmox, Synology, OXO, FTTO). 18 types custom
embarqués dans le projet pour les modèles hors catalogue ; tout ce qui
est illisible sur les photos porte [à vérifier]. Sert de projet de
démonstration réaliste ET de base au chantier plan d'étage (la salle
s'appelle OLYMPE).

**U libres** : idée de Panther à implémenter — motif discret dans les
U vides (suivant le fond choisi : ruche/points/grille), version très
atténuée, débrayable, sobre dans les exports.

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
