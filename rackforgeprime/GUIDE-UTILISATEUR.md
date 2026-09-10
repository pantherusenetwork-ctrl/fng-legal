# Guide utilisateur — RackForgePrime

Application de bureau **100 % locale** pour dessiner des baies réseau à l’échelle
réelle (EIA-310), un schéma logique VLAN/liens, et un plan d’étage. Rien ne
sort du poste : pas de compte, pas de cloud.

Ce guide décrit le quotidien : ouvrir l’app, créer un projet, travailler les
trois vues, exporter, enregistrer. Pour copier le kit sur une clé USB ou un
autre PC, lisez aussi `LISEZMOI.txt` (à côté de l’exe).

Version concernée : **1.7.1**.

---

## 1. Ouvrir l’application

Copiez **tout** le dossier du kit (exe + `_internal\` + workspace + lanceurs).
Ne séparez jamais l’exe du reste.

| Édition | Lanceur | Ce que vous obtenez |
|---|---|---|
| **PC** | `LANCER-PC.bat` (ou double-clic `RackForgePrime.exe`) | Fenêtre sans barre d’adresse (Edge ou Chrome). Fermer la fenêtre = quitter. |
| **Web** | `LANCER-WEB.bat` | L’app dans le navigateur de ce PC, adresse `http://127.0.0.1:8137`. Fermez la fenêtre noire du lanceur pour arrêter. |
| **Phone** | `LANCER-PHONE.bat` | Le serveur s’ouvre au réseau. Une boîte affiche l’URL LAN (ex. `http://192.168.1.12:8137`). Sur le téléphone / la tablette, **même Wi-Fi**, ouvrez cette URL. |

Le serveur écoute **avant** que vous cliquiez OK sur la boîte Phone. L’URL est
aussi recopiée dans `DERNIERE-ADRESSE.txt` à la racine du kit — utile si la
boîte passe derrière une autre fenêtre.

Une seule instance à la fois : si RackForgePrime tourne déjà (port 8137, ou
8138–8146), relancer rouvre la fenêtre existante. Pour Phone, **fermez d’abord**
l’édition PC : elle tient le port en local et le téléphone ne pourra pas
rejoindre le serveur.

Firefox convient pour Web / Phone, pas pour la fenêtre PC (`--app` = Edge ou
Chrome).

---

## 2. Créer ou ouvrir un projet

Le **projet** est un fichier JSON : c’est la source de vérité. Les dessins se
régénèrent depuis ce fichier.

- **Nouveau** (bouton en haut, ou double-clic / clic droit sur le fond) : projet
  vide, nouvelle page de diagramme, nouvelle baie, ou niveau de plan
  (ville / bâtiment / salle).
- **Projets** : liste des fichiers déjà dans l’espace de travail. Le projet
  courant est enregistré avant le basculement.
- **Ouvrir** (ou `Ctrl+O`) : charger un `.json` depuis le disque. Ce fichier
  n’écrase pas le projet de l’espace de travail tant que vous n’enregistrez pas.
- Le champ de nom en haut de fenêtre renomme le projet affiché.

Ne tapez pas de VLAN, hostname ou nom de salle « pour faire joli » : saisissez
ce que vous avez relevé sur site.

---

## 3. Les vues

Le bandeau **Physique · Logique · Diagramme · Plan** change uniquement
l’affichage. C’est le même projet.

### Physique

Élévation 42U à l’échelle : 1 U = 44,45 mm, façade 19" = 482,6 mm. Les photos
constructeurs ne sont jamais étirées.

- Glissez un équipement depuis la palette de gauche dans une baie. Le fantôme
  se cale sur un U entier ; rouge = collision, le dépôt est refusé.
- **Baie** ajoute un coffret. Clic droit sur une baie : dupliquer, supprimer
  (les équipements partent aussi, `Ctrl+Z` annule).
- **Photos / Dessin** : façades photo ou dessin unifié.
- **Noms** : masqués par défaut (le dessin reste propre). Le hostname vit au
  survol, dans la fiche et les tableaux. Activez Noms pour l’écrire sur la
  façade.
- **n°U**, **Avant / Arrière**, **Câbles** : graduations, face arrière dérivée
  (dos neutre, aucun port inventé), cordons de brassage colorés.
- Clic sur un équipement : fiche à droite (hostname, rôle, ports).
- **Multi-sélection** : `Ctrl` ou `Maj` + clic ; `Maj` + rectangle.
  `Ctrl+C` / `Ctrl+V` copie-colle dans la baie (ou la baie active).
  `Suppr` retire la sélection et ses liens. Flèches : déplacer d’un U.

### Logique

Schéma VLAN / liens, **compact** : les nœuds sont groupés par baie et passent
à la ligne (plus de bandeau immense). Le sélecteur **Toute l’architecture**
ou une baie isole le périmètre (les voisins des autres baies restent en
pointillés).

- **Lien** : relier deux équipements (ports, média).
- **VLAN** : id, nom, couleur — uniquement ceux que vous déclarez.
- **Calques** : zones, liens, étiquettes, équipements, dessin libre.
- Texte, zone, flèche, ligne, ellipse, **Formes** : annotations sur le schéma.
- Clic droit sur un panneau de brassage : **Apparier au switch** (un cordon
  par port cuivre, aucun VLAN inventé).

### Plan

Parcours **ville → bâtiment → salle**, puis les baies posées sur le plan.

- **+ Ville** (puis bâtiment, salle) crée le niveau suivant.
- **Poser une baie** : une baie déjà dans le projet, à l’emprise réelle
  (600 × 1 000 mm par défaut, échelle mm/px dans Réglages).
- **+ Point** : borne Wi-Fi (couverture), prise, caméra, note.
- **Image du plan** : PNG/JPG en fond ; le curseur d’opacité règle la lecture.
- Clic sur une baie du plan : ouvrir sa vue physique.

### Diagramme

Page de dessin libre (hors baie), pour un croquis ou une légende. **Nouveau**
peut ajouter une page.

---

## 4. Exporter

Menu **Exporter** (la vue affichée, sauf mention) :

| Livrable | Usage |
|---|---|
| **SVG** | Rééditable (Inkscape, draw.io). Photos = fichier lourd. |
| **SVG léger** | Même élévation en **dessin**, sans photos — beaucoup plus petit. |
| **PDF** | La vue affichée, une baie par page en physique. |
| **PDF 1:10** / **1:20** | Impression à l’échelle EIA-310 ; l’échelle est **écrite** sur la page. Si le dessin ne tient pas, l’app n’écrit pas un faux 1:10. |
| **PNG** | Image à coller / imprimer. |
| **JSON** | Le projet, source de vérité. |
| **Étiquettes** | Planche A4 TIA-606 du brassage. |
| **draw.io** | Deux pages (élévation + logique), rééditables. |
| **Visio (.vsdx)** | Deux pages ; les liens logiques ont des connecteurs `<Connect>` (collés aux nœuds). Les formes sont des rectangles nommés, pas des photos. |
| **Dossier** (bouton dédié) | Livrable DAT : élévations + logique + plans + brassage + flux + PoE + nomenclature, cartouche. |

**Enregistrer sous** (`Ctrl+Maj+S`) : vous choisissez le dossier, le nom et le
format (JSON, SVG, PDF, VSDX…).

Les fichiers atterrissent où vous les enregistrez ; le dossier `exports\` de
l’espace de travail est un bon rangement par défaut.

---

## 5. Espace de travail et sauvegarde

À côté de l’exe :

```
RackForgePrime-Workspace\
├── projets\       vos .json (source de vérité)
├── exports\       livrables que vous y rangez
├── catalogue\     images officielles, packs, formes
├── datasheets\    PDF constructeurs à importer
└── sauvegardes\   copies datées
```

- **Enregistrer** (`Ctrl+S`) : écrit le JSON dans `projets\`. Dès qu’un projet
  a un nom dans l’espace de travail, chaque geste est réenregistré
  automatiquement (~1,5 s).
- **Sauvegarder** (menu Exporter) : copie datée — dossier local, NAS, ou
  téléchargement, au choix.
- **Vider / Remettre** (icône gomme) : tout disparaît de l’écran, **rien n’est
  perdu**. Recliquez pour tout remettre. Ce n’est pas un outil de dessin.
- **Nouvelle version** : fige une V suivante dans le dossier du projet.

Le workspace voyage avec le kit. Un exe tout seul recrée un workspace **vide**
(normal, mais sans vos projets ni le catalogue).

---

## 6. Dépannage court

**Port 8137 occupé.** Fermez l’autre fenêtre RackForgePrime (ou l’onglet Web).
Si un autre programme tient le port, l’app prend le suivant (8138… jusqu’à
+9). L’URL exacte est dans `DERNIERE-ADRESSE.txt`.

**La fenêtre PC ne s’ouvre pas.** Il faut Edge ou Chrome. Ouvrez l’URL du
fichier d’adresses dans Edge, ou utilisez `LANCER-WEB.bat`. Option : copiez un
Edge/Chrome portable dans `<kit>\navigateur\msedge.exe`.

**SmartScreen / antivirus** (« Windows a protégé votre ordinateur »). Cliquez
**Informations complémentaires** → **Exécuter quand même**. Clic droit sur
l’exe → Propriétés → **Débloquer** si la case existe. Au premier lancement
depuis une clé USB, c’est fréquent et sans rapport avec un virus.

**Phone : page blanche ou « site inaccessible ».**

1. PC et téléphone sur le **même Wi-Fi** (pas le réseau invité isolé).
2. Fermez l’édition PC avant `LANCER-PHONE.bat`.
3. Autorisez le pare-feu Windows (réseaux privés) pour RackForgePrime.
4. Collez l’URL LAN (`http://192.168.…:8137`), **pas** `127.0.0.1` (ça, c’est
   le PC). Relisez `DERNIERE-ADRESSE.txt` si la boîte a disparu.
5. L’URL répond dès le lancement : inutile d’attendre d’avoir cliqué OK.

**« VCRUNTIME140.dll introuvable ».** Recopiez le dossier `_internal\`
complet, ou installez `vc_redist.x64.exe` (Visual C++ 2015-2022).

**Catalogue vide / sans photos.** Le dossier
`RackForgePrime-Workspace\catalogue\` n’a pas été copié.

**Rien ne s’ouvre, pas d’erreur.** Lisez `rackforge-demarrage.log` (racine du
kit) et `RackForgePrime-Workspace\rackforge.log`. Causes fréquentes : USB en
lecture seule, `_internal\` oublié, antivirus en quarantaine.

**Rebuild Windows** (quand le code a changé), dans `fng-legal\rackforgeprime` :

```
python scripts\construire_kit_portable.py --build
```

Bumper `VERSION` (app.py) **et** le badge (`#brand-version`) ensemble **avant**
de compiler. Fermer l’app d’abord (fichier verrouillé sinon). Recette complète :
`LISEZMOI.txt`.

---

Tout reste local. Aucune donnée ne sort du poste.
