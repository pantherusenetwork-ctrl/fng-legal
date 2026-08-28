# RackForgePrime — Recherche visuelle

Synthèse de l'étude des outils de référence, et ce qu'on **reprend** / ce qu'on **écarte**
pour la direction artistique de RackForgePrime.

## 1. TSS Rack Planner (tssusa.net/rack-planner)

**Ce qu'on observe :**
- Drag-and-drop de faceplates 1U à 6U dans n'importe quel slot libre.
- Catalogue modélisé sur du matériel **réel** : Cisco, HPE, Arista, Juniper, Dell,
  Fortinet, Ubiquiti, APC…
- **Stats live** pendant la construction : cumul de wattage pour dimensionner
  l'UPS et vérifier la charge du circuit.
- Export PDF portrait « one-pager » : la baie + tous les faceplates labellisés.
- Aucun compte, aucun abonnement — exactement notre philosophie locale.

**Ce qu'on reprend :**
- Le principe *faceplate à l'échelle U exacte* (1U occupe exactement 1U).
- Le panneau de stats live (U occupés / U libres, watts cumulés).
- L'export PDF une page présentable en comité.
- Le catalogue par constructeur réel, pas des rectangles génériques.

## 2. PATCHBOX Rack Planner (rack-planner.patchbox.com)

**Ce qu'on observe :**
- Application web très épurée : palette d'équipements à gauche, baie au centre.
- Graduations U très lisibles le long des montants.
- Snap immédiat au U le plus proche pendant le drag ; pas de placement libre.
- Esthétique produit : faceplates plats, propres, orientés catalogue.

**Ce qu'on reprend :**
- Le layout **palette gauche / canvas droite** (notre UX obligatoire).
- La règle de snap : jamais de position intermédiaire entre deux U.
- La sobriété : peu de chrome d'interface, la baie est la vedette.

## 3. NetBox — Rack elevations

**Ce qu'on observe :**
- Élévations rendues en **SVG** côté serveur : c'est la preuve que SVG est le bon
  format pivot (affichage = export).
- Numérotation des U le long de la baie, ordre croissant ou décroissant configurable.
- Devices colorés par **rôle** (couleur du device role) quand il n'y a pas d'image.
- Bibliothèque communautaire `netbox-community/devicetype-library` : des milliers de
  définitions YAML (constructeur, modèle, hauteur U, ports, conso) + images
  d'élévation avant/arrière. **Source de catalogue légitime et réutilisable.**
- Vue avant / vue arrière distinctes.

**Ce qu'on reprend :**
- SVG comme format de rendu unique (l'écran et l'export sont le même code).
- La couleur-par-rôle comme fallback quand pas d'image officielle.
- Le format de la devicetype-library comme **schéma d'import** de catalogue
  (slug constructeur, `u_height`, ports nommés, `is_full_depth`).
- La distinction face avant / face arrière dans le data model (même si le proto
  ne rend que l'avant).

## 4. Visio / Lucidchart — templates rack & réseau

**Ce qu'on observe :**
- Les gabarits « Rack Diagram » : baie dessinée avec montants, trous de vissage,
  équipements = blocs à hauteur U normalisée avec label centré.
- Les schémas logiques : icônes normalisées (firewall = mur crénelé, switch =
  flèches croisées), liens orthogonaux, zones colorées pour les VLANs.
- C'est le **standard de lecture** des responsables : notre export doit pouvoir
  être posé à côté d'un Visio sans dépayser.

**Ce qu'on reprend :**
- Les proportions : baie 19" avec montants visibles, oreilles de fixation sur
  les équipements, labels lisibles centrés.
- Pour le futur schéma logique : conventions d'icônes reconnues, pas d'invention.

## 5. draw.io — bibliothèques rack / network

**Ce qu'on observe :**
- Bibliothèque `rack` : shapes paramétriques (hauteur en U réglable), rendu plat.
- Format XML ouvert, import SVG natif.

**Ce qu'on reprend :**
- L'export **SVG propre** (groupes nommés, un `<g>` par équipement) pour que le
  fichier soit rééditable dans draw.io / Inkscape, pas juste une image.
- À terme : export XML draw.io natif (le format est documenté et ouvert).

## Direction artistique retenue

- **Fond** : quasi-noir bleuté (`#0b0e14`), panneaux `#11151f`.
- **Baie** : montants gris acier avec trous de vissage suggérés, graduations U
  contrastées, U libres en creux sombre.
- **Équipements** : faceplates sombres `#1a1f2b` avec liseré de couleur **par rôle**
  (switch = cyan, firewall = rouge/orange, serveur = violet, UPS = jaune,
  patch panel = bleu, passe-câbles = gris) — lisible à 1 m d'un écran de salle réseau.
- **Accent** : cyan électrique (`#22d3ee`) pour la sélection et le fantôme de drop.
- **Typo** : sans-serif système + mono pour les U et hostnames (culture terminal).
- **Zéro gadget** : pas d'ombre portée lourde, pas de dégradés décoratifs, pas
  d'animation gratuite. Un glow discret uniquement sur l'état de sélection.
- **Fallback fidèle** : quand pas d'image officielle Aruba/Fortinet/Cisco →
  placeholder à l'échelle U exacte avec constructeur + modèle + ports schématisés,
  et bouton « Remplacer par image officielle ».
