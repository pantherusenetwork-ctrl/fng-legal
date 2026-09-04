# RackForgePrime — contexte de travail

Application 100 % locale de schémas de baies réseau (élévation 42U, vue logique
VLAN/liens, tableau de brassage généré). Code dans ce dossier, branche
`claude/rackforgeprimes-foundations-y41pt4`. Exe déployé dans
`C:\Users\koyon\Desktop\CITADEL\RACKFORGEPRIME\RackForgePrime-PC\` (serveur de dev :
`run.py --port 8138`, l'exe garde 8137). Les compteurs ci-dessous sont ceux de
leur date : la DERNIÈRE section « Pont d'Hemingway » fait foi.

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

**Bibliothèque d'images maîtresse (demande Panther 01/09)** : dossier
`catalogue\bibliotheque\<Constructeur>\` dans le workspace du Bureau —
TOUTES les images en TAILLE D'ORIGINE (aucune limite), triées par
constructeur, avec 00-INDEX.md. Il pioche à la main dedans, l'app aussi
(via l'import Image/SVG). À construire par l'agent bibliothécaire dès la
fin de l'aspiration NetBox (les originaux sont dans son extraction).
Les copies optimisées ≤300 Ko restent dans images-officielles\ pour l'app.

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
- Backlog : matrice de flux générée, **vue arrière des baies (redemandée
  le 31/08 soir — « intéressante mais on se concentre »)**, appariement
  en masse panneau↔switch, budget PoE cumulé, export VSDX, OCR datasheets.
- Fait 31/08 tard : câblage port-à-port (bouton « Câbler depuis ce
  port… » dans l'éditeur de port → menu type de câble → clic port
  d'arrivée → lien pré-rempli), suivi des révisions DAT (Project.revision
  + revisions[], badge « Ind. X » cliquable à côté du nom du projet,
  cellule Ind. au cartouche + page « Suivi des révisions » en tête du
  dossier), double-clic-fiche réparé (le re-rendu de sélection tuait le
  dblclick natif — détection manuelle 450 ms).

## Pièges connus

- Serveur : `PYTHONIOENCODING=utf-8` obligatoire en dev (le print de
  démarrage contient une flèche →) ; l'exe est blindé depuis le 31/08.
- Après un changement de modèle Pydantic : RELANCER le serveur avant
  tout PUT (l'ancien process efface les nouveaux champs).
- Le projet démo `reseau-maison.json` existe en DEUX copies (workspace
  du dépôt + workspace de l'exe sur le Bureau) — modifier les deux.

## 🌉 Pont d'Hemingway — 01/09/2026 (après-midi)

**Fait aujourd'hui** : fidélité salle OLYMPE vérifiée contre les 5 photos
(3 écarts corrigés : PP-PROM-B U40, +TIROIR-AH7WC-3 U11, HP TITAN U30 ;
contre-vérif 1 agent 5/5 OK — ⚠️ les photos originales n'existent plus que
dans la session Claude du 01/09, purgées du journal : les redemander à
Panther pour tout nouveau test). Conformité 47/47 tests, benchmark OK
(catalog ~0,1 s, SVG 1,5 s, PDF dossier 7,4 s). **Nettoyage** : build/,
dist/, .spec → `RAZOR LOCK\POUBELLE-A-VALIDER-2026-09-01-NETTOYAGE-RACKFORGE\`
(à faire valider). **Nouvelle base propre** dans CITADEL\RACKFORGEPRIME :
`RackForgePrime-PC\` (exe + workspace, LA seule copie), `RackForgePrime-Web\`
(LANCER-WEB.bat → navigateur), `RackForgePrime-Phone\` (LANCER-PHONE.bat →
--host 0.0.0.0 + IP affichée). Les 3 éditions partagent le même exe/workspace.
⚠️ Le workspace de l'exe a DÉMÉNAGÉ : `RACKFORGEPRIME\RackForgePrime-PC\RackForgePrime-Workspace\`
(l'ancien chemin racine n'existe plus).

**Prochaine étape exacte** : faire tester à Panther LANCER-PHONE.bat depuis
son téléphone (popup pare-feu Windows à autoriser « Réseaux privés » la
1re fois) ; ensuite backlog : vue arrière des baies, budget PoE, export VSDX.

## 🌉 Pont d'Hemingway — 01/09/2026 (soir)

**Fait** : fonction « Sauvegarder » dans le menu Exporter — dialogue à 3 choix
(Quoi : projet ouvert / tous les projets / tout le workspace ; Format : ZIP ou
JSON, workspace toujours ZIP ; Où : PC = `<workspace>\sauvegardes\`, NAS =
`\192.168.1.138\ULTRA\BACKUP\RACKFORGEPRIME\`, ou les deux). Backend
`rackforge/backup.py` + `POST /api/backup` ; échec NAS n'annule jamais la copie
PC. Testé dev + exe recompilé (déployé dans RackForgePrime-PC, ancien archivé
`-f.exe`) : projets→PC 650 Ko, workspace→NAS 126 Mo OK. `Z:` re-monté sur ULTRA
(CLAUDE.md corrigé). Icône barre des tâches : confirmée OK par Panther.

**Prochaine étape exacte** : test LANCER-PHONE.bat par Panther depuis son
téléphone ; puis backlog (vue arrière, budget PoE, VSDX). Idée à proposer :
sauvegarde automatique périodique (case à cocher) — pas encore demandée.

## 🌉 Pont d'Hemingway — 01/09/2026 (20h40)

**Fait** : sauvegarde refaite façon draw.io/Visio. « Enregistrer sous » natif
(showSaveFilePicker, fallback téléchargement) branché sur TOUS les exports
(SVG/PDF/JSON/PNG/drawio/étiquettes/sauvegarde). Dialogue Sauvegarder : 6
formats (ZIP/JSON/PDF/SVG/PNG/draw.io — visuels seulement pour le projet
ouvert) × 3 destinations (Enregistrer sous / dossier de l'app / chemin libre
mémorisé). AUCUN chemin perso en dur (adapté à la distribution) : le NAS de
Panther vit dans `<workspace>\sauvegardes\.dernier-dossier.txt` (seedé sur
les 2 workspaces). API : GET /api/backup/config, POST /api/backup
(dest telecharger|pc|dossier|deux + dir), POST /api/backup/fichier?dir&name.
Exe recompilé/déployé (ancien = `-g.exe`), testé. ⚠️ Piège shell découvert :
les heredocs bash mangent un backslash des UNC → un dossier parasite
`C:\192.168.1.138\` a été créé puis mis en poubelle (00-LISTE mis à jour) ;
toujours passer par un fichier .py (Write) pour manipuler des UNC.

**Prochaine étape exacte** : Panther teste le nouveau dialogue Sauvegarder
dans sa fenêtre salle OLYMPE (rouverte) + LANCER-PHONE.bat depuis le
téléphone. Backlog inchangé (vue arrière, PoE, VSDX).

## 🌉 Pont d'Hemingway — 01/09/2026 (21h20)

**Fait** : échelle réelle en vue photos. Nouveau champ EquipmentType.width_mm
(mm, référence rails 19" = 483 mm) : boîtier compact → SA largeur, centré,
proportions gardées (meet) ; rackable (width_mm absent) → la façade REMPLIT le
slot (preserveAspectRatio "none", façon NetBox). Appliqué aux 2 moteurs
(svg_export.py + drawFaceplate app.js). 6 largeurs posées sur salle-olympe
(2 copies) : livebox 130 / ont 95 / mini-pc 120 / optiplex 160 / audiocodes
345 / rad-etx 215 (datasheet) — estimées sur photos sauf RAD. Aussi ce soir :
cartouches supprimés en mode photos (nom au survol, <title> dans les exports),
minimap redesignée (150×100, translucide, croix pour masquer + case Minimap
dans le menu Calques, localStorage rfp-minimap-off), favicon ?v=2 (cache
d'icône Chrome des fenêtres --app = la cause de la vieille icône taskbar).
Exe recompilé/déployé (anciens -h, -i), 47/47 tests.

**Prochaine étape exacte** : retours de Panther sur l'échelle réelle en vue
photos (risque connu : une photo produit en angle étirée par "none" peut être
moche → si ça arrive, poser width_mm sur ce type ou filtrer par ratio).

## 🌉 Pont d'Hemingway — 01/09/2026 (22h) — ÉCHELLE RÉELLE GRAVÉE

**Décision structurante (demande Panther « les calculs doivent être gravés
bons et respecter au mm »)** : le dessin physique est passé à l'ÉCHELLE
RÉELLE EIA-310. Constantes gravées dans les 2 moteurs (svg_export.py +
app.js) : MM_19_POUCES=482.6, RACK_W=440 px → 0,9117 px/mm → **U_PX=40.5**
(1U=44,45 mm). Conséquences : le slot a le vrai ratio d'une baie, les images
sont TOUJOURS en preserveAspectRatio meet (le "none"/étirement est ABANDONNÉ
— c'était la mauvaise voie, ça déformait les photos en angle) ; une façade
19" remplit le slot d'elle-même ; un boîtier compact s'affiche à sa largeur
exacte via EquipmentType.width_mm (mm réels). Les baies sont ~2× plus
hautes qu'avant à 100 % (zoom/Ajuster compense). 47/47 tests, PDF dossier OK,
exe recompilé/déployé (ancien -j). NE JAMAIS revenir à un U_PX « esthétique ».

**Prochaine étape exacte** : validation visuelle par Panther (fenêtre salle
OLYMPE rouverte). S'il veut les multiprises pleine largeur : remplacer leur
photo en angle par une vraie façade, PAS retoucher l'échelle.

## 🌉 Pont d'Hemingway — 01/09/2026 (23h) — check d'échelle complet

**Campagne « check la mise à l'échelle » (3 agents + audit)** : audit des 1162
images du catalogue → 1027 façades (88 %), 135 étroites (rapport
scratchpad/audit-echelle-rapport.json : mélange vrais compacts = OK et
rackables photographiés en angle = à re-photographier un jour). Agent physique :
échelle exacte au centième (48/48 images, width_mm, espacements 40.5).
Agent logique/diagramme : tout vert, drawio synchronisé. Agent PDF : polices
écrasées → CORRIGÉ : (1) polices du dessin remises à l'échelle U_PX=40.5 dans
les 2 moteurs (graduations 14, cartouche 15/tronc 15 chars, pastille U 36×19
police 13, ports 8×14/10, décors, header baie 19/12, footer 14) ; (2) PDF
physique et dossier = UNE BAIE PAR PAGE A4 PORTRAIT (model_copy racks=[rack]) ;
(3) page logique du dossier en paysage si schéma large (regex viewBox).
Résultat : 11/12 pages ≥4.8 pt, zéro texte <4 pt sauf la PAGE LOGIQUE
(min 1.9 pt — CHANTIER RESTANT : polices de svg_logical à agrandir ou
pagination par zone). 47/47 tests. Exe déployé (ancien -k), fenêtre rouverte.

**Prochaine étape exacte** : lisibilité PDF de la vue logique (le seul rouge
restant) ; retours visuels de Panther sur les nouvelles proportions écran.

## 🌉 Pont d'Hemingway — 01/09/2026 (23h30) — PDF 100 % lisible

**Fait** : la vue logique PDF est découpée en TRANCHES verticales pleine
hauteur (style plan d'architecte) : _logical_slices()/_draw_svg_slice() dans
pdf_export.py (clipPath + translate par page, échelle = hauteur de zone,
jamais réduite pour la largeur). Dossier salle-olympe = 15 pages (1 suivi +
5 élévations portrait + 4 tranches logiques + 5 tableaux), **minimum 4,8 pt,
zéro texte <4 pt sur les 15 pages** (mesuré pypdf). Logical standalone :
4 pages à 7,1 pt. 47/47 tests. Exe déployé (ancien -l), fenêtre rouverte.
Le dernier rouge du check d'échelle est éteint.

**Prochaine étape exacte** : retours visuels de Panther (proportions écran +
feuilleter le nouveau dossier PDF 15 pages). Backlog : re-photographier les
~50 rackables du catalogue à photo en angle (liste dans
scratchpad/audit-echelle-rapport.json — la copier dans le workspace si on
lance ce chantier), vue arrière, budget PoE, export VSDX.

## 🌉 Pont d'Hemingway — 02/09/2026 (minuit) — cohabitation dans le U

**Fait** : plusieurs boîtiers compacts peuvent partager un même U à l'échelle
réelle (demande « deux FGT 60F collés à la place d'un 200F »). Modèle :
RackItem.position_x_mm (bord gauche en mm, réf 482,6 ; None = seul/centré).
Validation models.py : cohabitation OK si tous les occupants ont width_mm +
position_x_mm, sans chevauchement ni débordement — messages français précis
(testés 5/5). rack_stats compte les U en set (un U partagé = 1). Rendu 2
moteurs : position au mm, habillage limité à l'empreinte, pas de pastille U en
partage. UI : déposer un compact sur un U tenu par des compacts → tryShare()
le COLLE au dernier (normalise les centrés depuis la gauche) ; statut « Posé
côte à côte — à N mm » ; déplacé sur U libre → redevient centré. Vérifié :
export SVG x=40.0/158.5 px pour 0/130 mm. Aussi : sauvegarde = dernier choix
mémorisé (localStorage rfp-bk-*) ; agent images → 5 types custom équipés en
« photo de gamme — modèle à confirmer » (mikrotik×2, huawei, fg-200d,
synology-rs1221+), switch-48p-custom et alcatel-oxo restés sans image (rien
d'honnête au catalogue), STORI = item at-srv sur le type switch-48p (à séparer
si NVR confirmé). 47/47 tests, exe déployé (ancien -n).

**Prochaine étape exacte** : Panther teste le côte-à-côte (glisser une Livebox
sur le U d'une autre) ; lui demander le constructeur du switch 48p + le rôle
de STORI pour finir les 2 images manquantes.

## 🌉 Pont d'Hemingway — 02/09/2026 (0h45) — noms manuels, stack Aruba, STORI, fibre

**Règle actée par Panther : AUCUN nom écrit sur le dessin sauf hostname saisi
manuellement** (les 2 moteurs n'affichent plus jamais vendor+model — survol
seulement). ATLAS corrigé (infos Panther) : SW-ATLAS-01/02 supprimés → STACK
4× hpe-aruba-2930f-48g-poep-4sfp U31-34 sans hostnames [48G supposé — à
confirmer 24/48] ; STORI → type dédié stori-nvr ; U41 → type arrivee-fibre-lc.
Agent web (52 outils) : marque STORI N'EXISTE PAS (storiprotection.fr =
intégrateur cloud sans matériel) → photo de gamme Hikvision DS-7616NXI 1U
marquée à confirmer ; fibre = Panduit FD1W24BUDLCZ (24 LC duplex BLEUS,
inconfondables avec RJ45) ; bonus generic-patch-panel-24-v2.png (Belden RJ45
chargés, PAS appliqué — l'existant Panduit vide est intact, à proposer).
Originaux pleine taille dans RackForgePrime-Workspace\bibliotheque\
{Hikvision,Panduit,Belden}\. 2 copies JSON md5-identiques, valid:true,
47/47 tests, exe déployé (ancien 2026-09-02-a).

**Prochaine étape exacte** : demander à Panther (1) 24 ou 48 ports pour les
2930 du stack ; (2) une photo façade+étiquette du vrai boîtier STORI ;
(3) veut-il la v2 Belden (RJ45 visibles) pour tous les panneaux cuivre ?

## 🌉 Pont d'Hemingway — 02/09/2026 (1h45) — fiche manageable complète

**Fait** : fiche équipement = VUE (façade #device-photo en grand) + grille de
ports cliquables. Ports partout : agent NetBox (clone sparse devicetype-library,
6417 YAML) → 888 types complétés, 27 629 interfaces, 0 slug introuvable,
128 sans interfaces légitimes (passifs/châssis) → 1022/1162 types du catalogue
« manageables ». 10 types custom salle-olympe dotés à la main (FG-200F 16+4+4,
2930 48+4, Huawei 24+4, MikroTik 16+2/12+4, Livebox 4, ONT, STORI 2, AudioCodes
4, OXO 2 — gammes, à confirmer). Fiche : bouton ✎ Nom + clic sur le titre =
renommer (nom manuel → s'écrit sur le schéma, vide = rien). CLIC DROIT sur un
port = menu d'état instantané Up/Down/Réservé/Brassé/Libre (Libre demande
confirmation si config saisie ; menu appendé DANS le dialog — top layer, sinon
inerte). 47/47 tests, exe déployé (ancien 2026-09-02-c).

**Prochaine étape exacte** : chantier VUE CÂBLAGE façon PATCHBOX demandé par
Panther (« le câble ne peut pas avoir la même vue que dans Patchbox ») :
dessiner les cordons port-à-port en overlay dans la vue physique, couleur par
type de câble, bouton d'activation. Et toujours en attente de Panther :
24/48 ports pour le stack 2930, photo du vrai STORI, panneau cuivre Belden v2.

## 🌉 Pont d'Hemingway — 02/09/2026 (2h15) — vue câblage PATCHBOX v1

**Fait** : bouton « Câbles » (bandeau physique, actif = orange, localStorage
rfp-cables-visibles). renderCables() : overlay SVG absolu dans #canvas
(#cables-overlay, z-index 5, pointer-events stroke sur .cable-path), un cordon
par logical.link — même baie : sortie à DROITE, goulotte, retour (jamais en
diagonale) ; baies différentes : traversée d'allée côté voisin. Cordons étagés
(sag 26+n%5*9), halo sombre + couleur réelle par media (os2 jaune #eab308,
om4 aqua #22d3ee, cat6a #2563eb, cat6 #60a5fa, dac gris, défaut #94a3b8).
Survol = tooltip (hostnames·ports, media, VLANs), clic = openLinkDialog.
Repère canvas ÷ canvasZoom (stable au zoom/scroll). Testé sur reseau-maison
(7 cordons ✓). Exe déployé (ancien 2026-09-02-d).

**Prochaine étape exacte** : montrer à Panther (activer « Câbles » sur
reseau-maison — salle-olympe n'a que 2 liens pour l'instant) ; v2 possibles :
cordons dans l'export SVG/PDF, ancrage au PORT précis (positions des ports
dessinés), filtre par VLAN/type. Toujours en attente : 24/48 ports du stack
2930, photo du vrai STORI, panneau cuivre Belden v2.

## 🌉 Pont d'Hemingway — 02/09/2026 (2h45) — salle OLYMPE câblée

**Fait** : câblage d'après photos appliqué aux 2 copies (11 liens) :
8 cordons A6KVC a6-pp:P1-P6,P19,P24 → a6-sw (CONSTATÉ photo, port switch
[à vérifier]), réparation ol-up (at-sw1 disparu → at-stk1), pr-ont-lb ONT→LB
nominale [déduit — à vérifier]. HA FGT conservé. Vérifié à l'écran : cordons
bleus étagés dans la goulotte droite du coffret, fidèles à la photo.
LIMITE honnête : les fagots d'ATLAS/CHRONOS/TITAN ne sont PAS traçables
cordon par cordon sur les photos — seul Panther peut compléter (ou re-photos
rapprochées). Exe déployé (ancien 2026-09-02-e). valid:true, 47/47.

**Prochaine étape exacte** : Panther vérifie les cordons à l'écran (bouton
Câbles actif) et complète le brassage réel ; puis v2 câbles (export PDF/SVG,
ancrage au port). Rappels en attente : 24/48 stack, photo STORI, Belden v2.

## 🌉 Pont d'Hemingway — 02/09/2026 (16h50, reprise via Cowork)

**Constat** : la session Claude Code du projet a été perdue (historique
introuvable). Rien n'est perdu côté code : tout est sur disque.
État vérifié (git status, 02/09 16h45) : branche
`claude/rackforgeprimes-foundations-y41pt4` en avance de 73 commits sur
origin (JAMAIS poussée) ; dernier commit 26fed35 du 01/09 15h12 (minimap v15).
Tout le travail du 01/09 soir au 02/09 2h45 (sauvegarde, échelle réelle,
cohabitation U, fiche manageable, vue câbles, salle OLYMPE câblée) est
NON COMMITÉ : 9 fichiers, +1174/-218 (app.py, backup.py nouveau, models.py,
pdf_export.py, svg_export.py, app.css, index.html, app.js, 00-CONTEXTE.md).
Un `CLAUDE.md` a été ajouté à la racine du projet pour que toute nouvelle
session Claude Code lise ce journal d'office.

**Prochaine étape exacte** : (1) commiter + pousser (sécuriser les 73 commits
et le travail de nuit) ; (2) relancer Claude Code DANS ce dossier
(`cd ...\fng-legal\rackforgeprime` puis `claude`) ; (3) reprendre la section
02/09 2h45 : Panther vérifie les cordons (bouton Câbles) puis v2 câbles.
Toujours en attente : 24/48 ports du stack 2930, photo du vrai STORI, Belden v2.

## 🌉 Pont d'Hemingway — 03/09/2026 (soir) — reprise, tout dans CITADEL

**Fait** : reprise après perte de session. État vérifié : git propre (0bab269 du
02/09 16h58 contient tout le travail de nuit), exe `RackForgePrime-PC` = sources
(JS servi 140 818 octets identique, v1.1.0, câbles/cohabitation/échelle présents),
relancé sur 8137. Rangement (ordre Panther « tout dans CITADEL, rien ne traîne ») :
3 originaux Hikvision/Panduit/Belden déplacés dans
`RackForgePrime-PC\RackForgePrime-Workspace\catalogue\bibliotheque\` ; sauvetage
RAZOR LOCK copié dans `SAUVEGARDES\SAUVETAGE-RACKFORGE-2026-09-01\` (10 921 = 10 921) ;
résidus (coquille vide racine, caches Python, 18 exe périmés — gardé `-2026-09-02-e`)
→ `RAZOR LOCK\POUBELLE-A-VALIDER-2026-09-03\` avec 00-LISTE ; ancien workspace en
poubelle 09-01 vérifié : 0 fichier unique. Raccourci menu Démarrer recréé.
Racine = CLAUDE.md + PC/Web/Phone/SAUVEGARDES/fng-legal, rien d'autre.

**Prochaine étape exacte** : Panther confirme la version à l'écran, puis choisit
le chantier (A câbles v2 / B plan d'étage / C vue arrière / D PoE / E VSDX…).
Toujours en attente : 24/48 ports stack 2930, photo STORI, Belden v2, test PHONE.

## 🌉 Pont d'Hemingway — 03/09/2026 (21h) — vue arrière des baies

**Fait** : la **vue arrière**, backlog redemandé 3 fois, livrée comme une
vue **DÉRIVÉE** du même JSON — jamais un second dessin à maintenir (c'est
exactement le piège Visio : deux baies dessinées à la main qui divergent
dès la première modification). Trois règles gravées : (1) la baie passe en
**miroir horizontal** — `position_x_mm` des compacts cohabitants recalculée
au mm par `_item_box()` — et **les U ne bougent pas**, U1 reste U1 ; (2) un
équipement montre sa **façade** quand la face regardée est celle sur
laquelle il est monté (`RackItem.face`, présent au modèle depuis le début
mais **jamais rendu** jusqu'ici), sinon son **dos** ; (3) le dos est
**NEUTRE** — grille d'aération + prise secteur, **aucun port arrière
inventé** : la sérigraphie arrière réelle des types du catalogue n'est pas
connue, on ne la fabrique pas.

Backend : `_item_box()`, `_rear_faceplate()`, `_u_pill(align=)`, badge
`VUE ARRIÈRE` dans le bandeau de baie, paramètre `face` sur `render_rack` /
`render_project_svg` / `render_project_pdf` et sur `/api/export/svg` et
`/api/export/pdf` (face inconnue → 422, suffixe de fichier `-arriere`).
Frontend : bouton **Avant / Arrière** du bandeau (mémorisé `rfp-face`),
miroir JS strictement identique au Python, entrée de menu contextuel
« Monter à l'arrière de la baie », un équipement posé **hérite de la face
regardée**, et les exports suivent l'écran (ce que tu vois est ce que tu
livres). ⚠️ Piège corrigé au passage : sur les 4 thèmes sombres `hole` et
`decor_fill` sont à 1 point de luminance — les fentes d'aération étaient
bien dessinées mais **invisibles** ; elles sont maintenant cernées d'un
filet `face_stroke`.

**Vérifié** : 59/59 tests (47 existants + 12 neufs dans
`tests/test_face_arriere.py`) ; à l'écran sur `salle-olympe` — 61 items
rendus de dos, **0 photo de façade** affichée en vue arrière, face avant
**inchangée** ; exports réels `salle-olympe-arriere.svg` (387 Ko, 5 badges)
et `salle-olympe-arriere.pdf` (238 Ko). Commit **4898977**, poussé.

⚠️ **L'exe N'A PAS été recompilé** : `RackForgePrime.exe` tournait (PID
33180, port 8137) et fermer l'application de Panther sans son accord n'est
pas une décision d'agent. La vue arrière est donc dans le **code et le
dépôt**, pas encore dans l'exe du Bureau.

⚠️ **Une deuxième session Claude travaillait sur le dépôt en parallèle**
(vsdx_export.py, flows.py, svg_plan.py). Répartition convenue par message
inter-sessions : elle ne touchait pas mes 5 fichiers avant mon commit,
elle reprend `app.py` / `app.js` / `index.html` ensuite. `models.py` n'a
pas été modifié ici.

⚠️ `run.py` bind **8137** par défaut, **pas 8138** comme l'annonce le
`CLAUDE.md` du projet : en dev, passer `--port 8138` explicitement (sinon
collision avec l'exe déjà lancé).

**Prochaine étape exacte** : (1) Panther ferme l'app → recompiler l'exe
(PyInstaller, `--add-data`/`--icon` en chemins ABSOLUS, archiver l'ancien
dans `SAUVEGARDES\`) et le redéployer, puis vérifier le bouton
Avant/Arrière sur le vrai workspace ; (2) enchaîner sur le **plan
d'étage** (gros chantier voulu par Panther) ou le **budget PoE**.
Toujours en attente de Panther : 24/48 ports du stack 2930, photo du vrai
STORI, panneau cuivre Belden v2.

## 🌉 Pont d'Hemingway — 03/09/2026 (22h30) — plan d'étage, flux, PoE, VSDX

**Ordre de Panther** : « ne t'arrête pas avant d'avoir mis à jour l'app point
par point ». Deux sessions Claude ont travaillé EN PARALLÈLE sur ce dépôt
(coordination par messages inter-sessions, fichiers séparés, jamais les mêmes
en même temps) : l'autre a livré la **vue arrière** (4898977), celle-ci le lot
296ed4a :

- **Vue PLAN (4e onglet)** : parcours ville → bâtiment → salle → baies.
  Modèle `Project.sites[].buildings[].rooms[]` (Room : plan_image data URI,
  plan_opacity, plan_w/h px, mm_per_px, racks posés {rack_id,x,y,rotation},
  points {ap/prise/camera/equipement/note, radius = couverture Wi-Fi,
  equipment_id}). Validation : baie inconnue ou posée sur 2 plans = 422.
  Moteur `svg_plan.py` (écran = export ; emprise réelle 600×1000 mm, trait
  épais = face avant, liens inter-baies agrégés avec compteur, cercle de
  couverture). Frontend : cartes de navigation, fil d'Ariane, glisser les
  baies/points (transform live, modèle au relâchement), clic droit partout
  (poser une baie ici, borne/prise/caméra/note, image du plan, réglages),
  image de plan réduite à 1 600 px JPEG, curseur d'opacité, dialogue point
  (couverture en mètres), dialogue salle (taille, échelle mm/px).
  API : `view=plan&room=<id>` sur /api/export/svg et /pdf.
- **Matrice de flux** (bouton « Flux ») : `Project.flows[]` (src, dst, proto,
  ports, action ""|allow|deny|nat, via, comment), lignes éditables, vue
  matrice zones × zones (cellule = action la plus restrictive), « Proposer
  depuis le projet » (`flows.py` : paires VLAN↔VLAN via pare-feu/routeur +
  Internet↔VLAN si usage WAN — **action toujours vide**, jamais inventée),
  CSV `/api/flows.csv`, page « Matrice de flux » dans le dossier.
- **Budget PoE** (`energy.py`) : `PortUsage.poe_w` (W tirés, boutons af/at/bt
  dans l'éditeur de port), budget = `ItemMeta.poe_budget_w` (saisi sur la fiche,
  ✎ sur la tuile) sinon `EquipmentType.poe_budget_w`, sinon « à renseigner »
  (jamais deviné). Tuile « PoE tiré / budget (%) » colorée (alerte ≥ 80 %,
  dépassement), `/api/poe`, page « Budget PoE » du dossier.
- **Export Visio .vsdx** (`vsdx_export.py`, menu Exporter) : paquet OPC écrit
  à la main (document, pages Élévation + Logique, formes nommées, unités
  pouces, Y inversé). ⚠️ Validé structurellement (4 tests) mais **pas ouvert
  dans un vrai Visio** (absent du poste) — [à vérifier par Panther].
- Dossier PDF : + pages Plan (une par salle garnie), Matrice de flux, Budget PoE.
- `salle-olympe.json` (2 copies md5 4ed73ee3…) : sites posés — « Ville [à
  vérifier] › Bâtiment [à vérifier] › OLYMPE » (4 baies) et « Local technique
  [étage à vérifier] » (A6KVC). Positions dans la salle [à vérifier].
- Tests : **76 verts** (47 + 12 vue arrière + 17 ce lot). Exe recompilé depuis
  ce commit et déployé dans RackForgePrime-PC (ancien → SAUVEGARDES
  `-ancien-2026-09-03-a.exe`).

**Restent au backlog** : câbles v2 (cordons dans l'export SVG/PDF, ancrage au
port, filtre VLAN), appariement en masse panneau↔switch, multi-sélection +
Ctrl+C/V, connecteurs éditables, re-photos des ~50 rackables en angle, état
vide Diagramme illustré, sauvegarde auto périodique.

**Prochaine étape exacte** : Panther ouvre l'onglet **Plan**, descend Ville →
Bâtiment → OLYMPE, glisse les baies à leur vraie place, charge la photo/plan de
la salle (bouton « Image du plan »), règle l'échelle (Réglages, mm/px). Puis
ouvre un .vsdx dans Visio et dit si ça s'ouvre. Toujours en attente : 24/48 ports
du stack 2930, photo STORI, Belden v2, test LANCER-PHONE.

## 🌉 Pont d'Hemingway — 03/09/2026 (23h30) — v1.3.0 : logique par baie, Projets, appli solide

**Règles actées par Panther ce soir** : (1) **la version change à chaque exe
déployé** (app.py VERSION + badge index.html, ensemble) ; (2) **vraie appli de
bureau, solide, pas un lien HTML** ; (3) tout doit être **fluide**.

**Livré en v1.3.0 (commit 98f902f)** :
- **Vue logique DE LA BAIE** : en vue physique, la dernière baie touchée est
  « active » ; cliquer Logique montre ses équipements + les voisins directs
  des autres baies en pointillés (fantômes, opacité 0,62). Sélecteur
  `#logical-rack` dans le bandeau (« Toute l'architecture » / Baie X), export
  SVG/PDF suit (`rack=<id>`, suffixe `-logique-<id>`), 422 si baie inconnue.
- **Menu Projets** (bouton à côté du nom) : liste de `projets/*.json`, un clic
  = le courant est enregistré (PUT) puis l'autre chargé — sans rechargement,
  URL `?projet=` suivie (F5 rouvre le même), dernier projet rouvert au
  lancement (localStorage `rfp-ws-name`). **Enregistrement automatique** dans
  l'espace de travail 1,5 s après chaque geste (`scheduleWorkspaceSave`),
  « Nouveau projet », « Enregistrer dans l'espace de travail… », « Détacher ».
- **Ajout de baie explicite** : `addRack(after)` dit toujours où elle va
  (« à droite de X » / tout à droite), bouton « + Baie à droite » dans le menu
  de baie, « ＋ Nouvelle baie ici » au clic droit sur le plan d'étage.
- **Appli de bureau solide** (`run.py`) : instance unique (si RackForgePrime
  répond déjà sur 8137 → on rouvre sa fenêtre, pas de 2e serveur muet) ; port
  pris par autre chose → suivant libre ; **fermer la fenêtre = arrêt du
  serveur** (battement `/api/ping` toutes les 5 s, `/api/bye` au pagehide,
  chien de garde : bye + 4 s de silence, ou 180 s sans ping, ou 90 s sans
  fenêtre) ; `--no-browser`, `--host` réseau ou `--keep-alive` = serveur
  partagé jamais arrêté (éditions Web/Phone intactes).
- **Fluidité** : le catalogue (1 162 types + images) était relu à CHAQUE
  requête (2 s) — désormais en cache mémoire invalidé par signature des
  fichiers (`models.base_type_index`, `catalog_packs._PACK_CACHE`) :
  15 ms. Bascule de projet 3,6–5,9 s → 0,9–1,5 s.
- Tests : **84 verts**. Exe v1.2.0 déployé 21h32 (plan/flux/PoE/VSDX/arrière),
  v1.3.0 en cours de déploiement.

**Prochaine étape exacte** : Panther teste (1) clic sur une baie puis Logique,
(2) menu Projets salle-olympe ↔ reseau-maison, (3) fermer la fenêtre = le
processus disparaît (vérifier `Get-Process RackForgePrime` vide). Backlog
inchangé : câbles v2 (export + ancrage port), appariement panneau↔switch,
multi-sélection/Ctrl+C-V, VSDX à ouvrir dans un vrai Visio, re-photos.
Optimisation suivante : ne pas ré-enregistrer un projet inchangé à la bascule.

## 🌉 Pont d'Hemingway — 04/09/2026 (17h) — campagne 4 agents, v1.3.1 → v1.3.2

**4 agents indépendants (lecture seule) sur la v1.3.0 déployée** :
- Testeur API : **85 tests, 85 OK, 0 KO** (routes, exports, 422 en français, perf
  logique médiane 41 ms grâce au cache catalogue).
- Vérificateur UI : 7 captures headless OK, 0 bloquant, 0 texte undefined/NaN ;
  gênant : sélecteur de baie visible en Diagramme, logique OLYMPE coupée à droite.
- Auditeur d'état : **bug de perte de données** — « Importer JSON » ne détachait pas
  le projet de l'espace de travail → l'enregistrement auto a écrasé
  `RackForgePrime-Workspace\projets\reseau-maison.json` du DÉPÔT avec salle-olympe
  (03/09 21:48). Restauré depuis la copie PC (md5 0a9ddca2…), fichier écrasé mis en
  `RAZOR LOCK\POUBELLE-A-VALIDER-2026-09-04\`. Aussi : projets réécrits à l'ouverture
  sans geste ; LANCER-PHONE muet si l'édition PC tourne ; docs périmées.
- Juge vs Visio/draw.io : **7,5/10** (prise en main 7,5 · métier 8,0 · esthétique
  7,0). Meilleur pour ce métier (échelle réelle, vue arrière dérivée, brassage /
  étiquettes / PoE / BOM / dossier générés), moins bien en éditeur généraliste
  (multi-sélection, Ctrl+C/V, connecteurs éditables, impression à l'échelle).
  5 reproches : auto-layout logique inutilisable sur 61 équipements (4 521 px),
  aucune impression à l'échelle, textes tronqués « … » dans le PDF, pas de
  multi-sélection, VSDX sans connecteurs et jamais ouvert dans Visio.

**Corrigé dans la foulée** — v1.3.1 (commit v1.3.1) : import JSON détaché,
pas de PUT si le projet est inchangé (`_wsLastSaved`), LANCER-PHONE → boîte de
message si l'édition PC tourne, logique ajustée à la 1re ouverture, sélecteur de
baie masqué en Diagramme, CLAUDE.md/en-tête à jour. v1.3.2 : **fenêtres
multiples** (chaque fenêtre a un id ; fermer un onglet n'éteint l'app que si
c'était le dernier — le juge avait vu le risque), lettres de baie AA/AB après Z
(fini « Baie [ »), fantômes logiques « ↗ BAIE · Uxx », tableau PoE « par
équipement PoE ». Tests : **87 verts**.

**Prochaine étape exacte (par impact, d'après le juge)** : (1) auto-layout
logique compact (grouper par baie, plusieurs rangées de brassage) ; (2) impression
à l'échelle (1:10 / 1:20 écrit sur la page) ; (3) plus jamais de « … » sur un
identifiant dans le PDF (retour à la ligne) ; (4) multi-sélection + Ctrl+C/V ;
(5) VSDX avec <Connect> + ouverture réelle dans Visio [Panther].
Toujours en attente de Panther : 24/48 ports du stack 2930 + budgets PoE des 2930F,
VLANs d'OLYMPE (sans eux : 0 flux proposable), photo STORI, Belden v2, test PHONE,
vraies positions des baies + image du plan de la salle.

## 🌉 Pont d'Hemingway — 04/09/2026 (17h45) — v1.4.0 Enregistrer sous, nettoyage

**Demande Panther** : « je ne peux pas choisir le chemin où enregistrer mon
projet, ni sous quel format » + « nettoie tout le projet » + « reconstruis la
salle OLYMPE avec la réalité, vue baie, la logique en découle ».

**v1.4.0 (déployée, ping 1.4.0)** : menu Projets → **Ouvrir un fichier .json…
(Ctrl+O)**, **Enregistrer sous… dossier + nom + format (Ctrl+Maj+S)** — même
dialogue que Sauvegarder, préréglé projet/JSON/boîte Windows, 7 formats dont
**Visio .vsdx** —, **Enregistrer dans l'espace de travail (Ctrl+S)**.
Vérifié : aucune option retirée entre v1.1.0 et v1.4.0
(`git diff 0bab269 HEAD -- index.html` : 0 bouton supprimé).

**Nettoyage** : `Nouveau projet.json` (26 baies, 8 équipements, test du 03/09)
→ `RAZOR LOCK\POUBELLE-A-VALIDER-2026-09-04\` (manifeste). Les « 83 doublons
png+jpg » de l'audit sont en fait les originaux de `_originaux-2026-08-31\` :
aucun jumeau mort dans images-officielles (0 déplacé, 1 166 fichiers + 92
originaux). Agent « salle OLYMPE » lancé (proposition JSON + rapport, sans
inventer : les 5 photos n'existent plus sur ce PC).

**Prochaine étape exacte** : intégrer la proposition OLYMPE si justifiée (2 copies),
puis chantiers du juge : layout logique compact, impression à l'échelle, fin des
« … » dans le PDF, multi-sélection.

## 🌉 Pont d'Hemingway — 04/09/2026 (18h30) — v1.5.0 Vider/Remettre + étoile minimap

**Demande Panther (capture du bandeau)** : à gauche des flèches Annuler/Rétablir,
deux icônes — une qui vide le projet (un clic vide tout, un second remet tout) et
une étoile « style Claude » qui affiche la minimap, à améliorer.

**v1.5.0 (déployée, ping 1.5.0)** : bouton **Vider / Remettre** (`#btn-vider`,
gomme) : le projet complet est mis de côté (`projectStash` + localStorage
`rfp-stash`), l'écran montre les baies vides sans liens/VLAN/dessins/plans/flux ;
l'enregistrement automatique ET Ctrl+S sont suspendus tant qu'il est vidé (le
fichier n'est jamais vidé) ; second clic = remise exacte (confirmation si on a
posé des choses entre-temps). Bouton **étoile** (`#btn-minimap`) : affiche /
masque la minimap, qui devient visible même si tout tient à l'écran
(`minimapForce`) ; minimap agrandie 220×140 avec les **noms des baies** dans les
blocs. Vérifié au navigateur : 5 baies 4/17/15/13/12 → 0/0/0/0/0 → remise
4/17/15/13/12, 11 liens, 4 baies posées sur le plan retrouvés.

**Prochaine étape exacte** : proposition de l'agent « salle OLYMPE » (en cours),
puis chantiers du juge (layout logique compact, échelle d'impression, « … » du PDF,
multi-sélection).

## 🌉 Pont d'Hemingway — 04/09/2026 (19h30) — constructeur MikroTik

**Demande Panther** : « tu dois avoir les images de MikroTik aussi, constructeur
important : routeurs, switchs, etc. » Avant : 18 modèles (+4 doublons `nb-`).

**Agent constructeur (1 agent)** : pack `catalogue\types-officiels\pack-mikrotik-v2.json`
= **65 modèles** (32 routeurs, 32 switchs, 1 RDS), 938 ports, power_w 64/65,
**width_mm 28 compacts** (RB5009 220, hEX 113, CRS310, CRS305… lus dans les specs
mikrotik.com), **42 images de façade officielles** neuves (≤ 300 Ko, originaux
pleine taille dans `bibliotheque\MikroTik\`), 14 images NetBox conservées, 9 sans
image honnêtes (vue en angle seulement : RB5009, RB4011 Wi-Fi, CRS106, RB260GS ;
boîtiers extérieurs netPower/PowerBox ; CCR1036 page 404). Déployé à l'identique
dans les 2 workspaces. ⚠️ **Règle apprise : les packs se chargent par ordre
alphabétique, le dernier gagne** → pack renommé `pack-mikrotik-v2.json` (après
`netbox-massif` et `pack-constructeurs`) pour que ses améliorations s'appliquent ;
4 doublons `nb-mikrotik-crs…` retirés de `netbox-massif.json` (entrées + images en
`POUBELLE-A-VALIDER-2026-09-04`). Exe : 1 209 types, **MikroTik 65, 56 avec image**.
Agent « analyse du rendu » lancé (chaque modèle posé en baie, captures, verdicts).

[à vérifier] largeur hEX S 2025 et hEX PoE ; u_height 2 des netPower 15FR / Lite 7R.

## 🌉 Pont d'Hemingway — 04/09/2026 (21h) — MikroTik rendu corrigé, v1.5.1

**Agent analyse du rendu (65 modèles posés dans 3 baies, captures)** : 12 ✅ · 20 ⚠️ ·
33 ❌ — cause n°1 : mikrotik.com publie des photos **piquées de dessus (3/4)**, que le
moteur (meet, jamais de déformation) cale sur la hauteur du U → châssis 19"
rendus à 30-70 % de leur largeur. Aussi : halo blanc des JPEG en thème sombre,
width_mm manquante hEX PoE / hEX S 2025, ports `lte` fantômes, CRS309 avec sa
rallonge, RDS2216 en `other`, et **le mode Dessin ignorait width_mm**.

**Agent correctif images** : 41 façades recadrées sur la bande frontale des
originaux (photos piquées sans lacet → façade rectangulaire, parallélisme ± 5 %
mesuré, ratio largeur/hauteur vérifié contre les cotes mikrotik.com : tous dans
± 30 %), 1 vraie vue de face NetBox (RB4011iGS+RM), 43 **PNG alpha** (fin du halo),
width_mm hEX PoE 114 / hEX S 113 / CRS309 272 (brochures), 4 `lte` retirés,
`100base-tx` sur le port mgmt du CRS326-4C, RDS2216 → `server`. Anciennes images
dans `bibliotheque\MikroTik\_remplacees-2026-09-04\` (2 workspaces, md5 identiques).
Contre-vérifié : CRS510 ratio 10,81 (attendu 10,86), CRS520 10,81, RB4011 11,33.
Exe : **MikroTik 65, 56 avec image** (9 sans face propre restent dessinés).

**v1.5.1 (déployée, ping 1.5.1)** : mode Dessin à la largeur réelle des compacts
(placeholder à `width_mm`, ports limités à la largeur, pas d'équerres, cartouche
seulement si la place existe) — Python + JS miroir, test `test_dessin_compact`.
Tests : **88 verts**.

[à vérifier] 11 des 13 façades NetBox conservées sont des JPEG (halo léger en
sombre), CRS418 légèrement de dessus ; 9 modèles sans image (RB5009UG, RB4011
Wi-Fi, CRS106, RB260GS, PowerBox Pro, netPower ×3, CCR1036-12G-4S).
Reste du backlog inchangé (layout logique, échelle d'impression, « … » PDF,
multi-sélection).

## 🌉 Pont d'Hemingway — 04/09/2026 (21h45) — HERCULE, araignée, images OLYMPE

- **Le coffret mural A6KVC s'appelle HERCULE** (Panther : « c'est la baie Hercule,
  j'ai juste pas encore étiqueté »). Renommé dans les 2 copies (id `rack-a6kvc`
  conservé, révision V3, note dans la baie). Les hostnames de reproduction
  `SW-A6KVC-01` / `PP-A6KVC` restent [à vérifier] (noms non lus sur photo).
- **v1.5.2 déployée** : icône **araignée** (corps, tête, 8 pattes) pour la minimap,
  à la place de l'étoile (« regarde la PJ » : Panther voulait une araignée).
- Agent « images salle OLYMPE » en cours : juge les 21 types custom, cherche des
  façades de face (AudioCodes Mediant 800, UCOPIA, Alcatel OXO Connect — seul type
  sans image —, Livebox, RAD, Synology, Dell), les sort du projet vers
  `pack-olympe-v1.json` + images-officielles (projet 1,7 Mo → léger).
- Panther : « l'application commence à avoir de la gueule » ; demande un **agent
  testeur à la fin**.

## 🌉 Pont d'Hemingway — 04/09/2026 (23h) — OLYMPE allégé, glisser-déposer adaptatif, DAT

- **DAT de l'application** : `docs/DAT-RACKFORGEPRIME.md` (13 sections, code étape par
  étape) + page lisible publiée ; README réécrit (v1.5.2).
- **Agent images OLYMPE** : les 21 types custom sortent du projet vers
  `pack-olympe-v1.json` + `images-officielles` + `bibliotheque\<Constructeur>\` (2
  workspaces, md5 identiques) → `salle-olympe.json` **1 772 452 → 47 330 octets**.
  AudioCodes Mediant 800 : façade officielle + **width_mm 345** (datasheet) ; UCOPIA :
  façade rack 1U 19" (gamme, génération [à vérifier]) ; RAD ETX-205A : datasheet 440 mm
  → 19" (width_mm 215 retiré) ; 6 photos d'angle retirées (KVM Dell, ONT, mini-PC,
  étagère…) → dessinées ; OXO Connect reste dessiné (aucune façade ≥ 800 px).
  Posé dans les 2 copies (md5 90a6f8e2…), app relancée : 61 items, 54 avec image.
- **Glisser-déposer adaptatif** (demande Panther) : le fantôme de dépose prend la vraie
  hauteur ET la vraie largeur du boîtier (width_mm), se place côte à côte quand la
  cohabitation est possible (tryShare), affiche « U5 · 1U · 113 mm ». Vérifié : hEX
  = 103 px sur 440 (113 mm).
- Agent « dimensions réelles » lancé sur tout le catalogue (ratio image / U attendu,
  compacts → width_mm sourcée, photos en angle listées) → `pack-dimensions-v1.json`.
- [à vérifier] pour Panther : génération UCOPIA, Livebox « Business 320 » (130 mm sans
  source), cotes ONT/mini-PC/OptiPlex, OXO S/M/L + photo de face, photos de gamme STORI /
  Huawei / SEWAN / CCR / FGT 200F, stack 2930 24/48.

## 🌉 Pont d'Hemingway — 05/09/2026 — dimensions réelles de tout le catalogue

**Demande Panther** : « pareil pour les passe-câbles et autres : cherche les vraies
dimensions — un équipement posé dans la baie avec sa dimension à l'échelle réelle ».

**Agent « dimensions »** (+ 5 chercheurs par constructeur) : mesure du ratio de chaque
image contre la hauteur U attendue (`mesures.csv`, 1 229 types) → 1 058 types 19"
cohérents, **80 compacts avec width_mm sourcée** (HPE 25, Cisco 21, Fortinet 6, Juniper 6,
Extreme 5…) + 4 u_height corrigés (Arista 7280CR2/7050CX4M 1U → 2U, datasheet « 2RU »),
23 compacts sans fiche (rien posé), 23 photos en angle listées, 15 sans image.
Pack `pack-dimensions-v1.json` (2 workspaces, md5 identiques) ; + 9 cotes du chercheur
Juniper/Ubiquiti/divers intégrées à la main (Ciena 3984 293, Huawei S5735-L8 320/250,
Minisforum 196 [à vérifier — axes], Zyxel 265/165) — 2 faux positifs (PBXact 400 = 19")
retirés. Catalogue servi : **width_mm 36 → 123 types**.

**À refaire (agent « photos de face » en cours)** : `generic-cable-mgmt-1u` (photo en
perspective → 226 mm au lieu de 483), `generic-blank-1u/2u` (texture sans bords), tiroirs
LC 12/48, Corning EDGE, FS FHD, + 23 photos en angle. Règle : vue de face mesurée
(ratio ± 15 %) ou pas d'image.

[à vérifier] 23 compacts sans fiche (SMC, MitraStar, PBXact 75, Vertiv SA1, RackifyUS 10"…),
EC-XS 240 mm, Hikvision K2 52 mm, IE-4000 rail DIN.

## 🌉 Pont d'Hemingway — 05/09/2026 — photos de face, testeur final

- **Agent « photos de face »** (24 types) : **11 remplacées** par une vraie vue de face
  mesurée (passe-câbles Panduit NM1, tiroir LC 12, FS FHD, FPR4115, Arista 7050SX ×4,
  F5 i7800, C8300 ×2), **7 retirées → dessinées à l'échelle** (obturateurs 1U/2U, LC 48,
  Corning EDGE, PA-3060, Vertiv SA1, ERS 3526T — aucune façade 19" propre trouvée),
  6 conservées avec réserve (écart dû au `u_height` du pack : N9K-C93240, Hikvision K2,
  MDX, ENVR, IP Office 500, UDM-Pro-Max → [à corriger dans un pack]). 2 workspaces md5
  identiques ; anciens fichiers dans `bibliotheque\<C>\_remplacees-2026-09-04\`.
  Catalogue servi après relance : **1 229 types, 1 207 avec image, 123 avec width_mm**.
- Agent testeur final lancé (pytest, API, cohérence des packs, échelle réelle mesurée
  dans le SVG, 7 captures UI, appli de bureau).
