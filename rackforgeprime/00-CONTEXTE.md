# RackForgePrime — contexte de travail

Application 100 % locale de schémas de baies réseau (élévation 42U, vue logique
VLAN/liens, tableau de brassage généré). Code dans ce dossier, branche
`claude/rackforgeprimes-foundations-y41pt4`. Exe déployé sur
`C:\Users\koyon\Desktop\CITADEL\RACKFORGEPRIME\` (serveur de dev : port 8138,
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
