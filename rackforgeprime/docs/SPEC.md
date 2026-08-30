# RackForgePrime — Spécification produit (v0.1)

Application **locale**, sans abonnement, pour ingénieur réseau / technicien /
administrateur. Deux vues d'un même projet : **schéma physique** (élévation de
baies) et **schéma logique** (VLANs, flux, liens). Le fichier source est toujours
le **JSON du projet** ; les dessins (SVG, PDF) sont des vues générées.

## 1. Écrans

### 1.1 Éditeur de baie (écran principal — c'est le prototype actuel)
- **Palette gauche** : équipements groupés par rôle (switch, firewall, patch
  panel, UPS, serveur, obturateur, passe-câbles), filtrables par constructeur.
  Chaque carte affiche constructeur, modèle, hauteur U.
- **Canvas droite** : la ou les baies (multi-baies, 4 typiques), graduées en U
  (1U = 44,45 mm). Rendu SVG identique à l'export.
- **Drag-and-drop** : glisser depuis la palette → fantôme aligné sur le U le plus
  proche ; U libres = fantôme cyan, collision = fantôme rouge + **refus au drop**.
  Un équipement posé se déplace de la même façon. Le snap U est le cœur : aucune
  position intermédiaire n'existe.
- **Panneau métadonnées** (clic sur un équipement) : hostname, rôle, VLAN, prise
  murale, port, usage, numéro de série. Suppression de l'équipement.
- **Barre d'état** : U occupés / libres par baie, watts cumulés.
- **Exports** : SVG, PDF, JSON (téléchargements directs).

### 1.2 Tableau de brassage (généré, jamais dessiné à la main)
Table triée baie / U / port : `Baie | U | Équipement | Port | Prise murale | VLAN | Usage`.
Toujours régénéré depuis le JSON. Export CSV plus tard.

### 1.3 Éditeur logique (phase 2)
Nœuds = équipements du projet (les mêmes IDs), liens typés (trunk, access,
uplink, HA), zones VLAN colorées, matrice de flux. Même moteur d'export SVG/PDF.

### 1.4 Import (phase 2)
- Image / SVG / faceplate custom → devient un type d'équipement de la palette.
- PDF / datasheet constructeur → extraction (modèle, hauteur U, conso, ports)
  via parseur Python, proposition dans la palette après validation humaine.
- YAML NetBox devicetype-library → import direct de types.

## 2. Flux principaux

1. **Créer un projet** → nom + N baies (défaut 42U) → éditeur.
2. **Peupler** : drag depuis palette → snap U → drop (refus si collision) →
   renseigner métadonnées → répéter.
3. **Documenter** : le tableau de brassage se remplit tout seul depuis les
   métadonnées ports/prises.
4. **Livrer** : export PDF (comité / DAT), SVG (retouche draw.io/Inkscape),
   JSON (archivage, regénération, diff Git).

## 3. Data model (JSON — source de vérité)

Versionné (`schema_version`), tout est régénérable depuis ce fichier.

### 3.1 Projet
```json
{
  "schema_version": 1,
  "id": "prj-8f3a",
  "name": "Salle serveur Siège",
  "created": "2026-08-28T10:00:00Z",
  "racks": [ "...voir 3.2..." ],
  "equipment_types": [ "...types custom locaux au projet..." ],
  "logical": {
    "vlans": [ { "vid": 20, "name": "USERS", "color": "#22d3ee" } ],
    "links": [ "...voir 3.4..." ]
  }
}
```

### 3.2 Baie
```json
{
  "id": "rack-a",
  "name": "Baie A",
  "u_height": 42,
  "width_inches": 19,
  "location": "Local technique RDC",
  "desc_units": false,
  "notes": "",
  "items": [ "...voir 3.3..." ]
}
```
- `u_height` : hauteur totale en U (42 typique, arbitraire autorisé).
- `desc_units` : `false` = U1 en bas (défaut datacenter).

### 3.3 Équipement posé (item de baie)
```json
{
  "id": "eq-01",
  "type_id": "fortinet-fortigate-100f",
  "position_u": 40,
  "face": "front",
  "meta": {
    "hostname": "FW-SIEGE-01",
    "role": "firewall",
    "vlan": "MGMT 99",
    "wall_outlet": "PM-R12",
    "port_usage": [
      { "port": "port1", "outlet": "PM-R12", "vlan": "99", "usage": "Management" }
    ],
    "serial": "FG100F0000000000",
    "notes": ""
  }
}
```
- `position_u` : **U le plus bas occupé** (un 2U en `position_u: 40` occupe 40–41).
- La hauteur vient du type (`equipment_types.u_height`) — jamais dupliquée ici.
- `port_usage` alimente le tableau de brassage.

### 3.4 Type d'équipement (catalogue)
```json
{
  "id": "fortinet-fortigate-100f",
  "vendor": "Fortinet",
  "model": "FortiGate 100F",
  "category": "firewall",
  "u_height": 1,
  "power_w": 60,
  "ports": [ { "name": "port1", "type": "1000base-t" } ],
  "color": "#f97316",
  "faceplate_svg": null,
  "faceplate_image": null
}
```
- `faceplate_svg` : SVG inline officiel ; `faceplate_image` : image (data URI
  `data:image/...`) étirée sur le slot U exact. `null` pour les deux →
  placeholder à l'échelle U (bloc teinté par rôle, constructeur + modèle,
  pastille U, ports en banques ou décor de catégorie).
- Images officielles du workspace : un fichier
  `catalogue/images-officielles/<id-du-type>.png|jpg|svg` est appliqué
  automatiquement au type de même id (catalogue et exports).
- Packs constructeurs : chaque `catalogue/types-officiels/*.json` (liste de
  types au schéma ci-dessus) enrichit la palette ; visibles sur disque, donc
  validables par l'utilisateur. Remplissage via
  `scripts/telecharger_pack_constructeurs.py` (volontaire, hors application).

### 3.5 Lien logique
```json
{
  "id": "lnk-01",
  "from": { "equipment_id": "eq-01", "port": "port3" },
  "to":   { "equipment_id": "eq-02", "port": "Te1/0/48" },
  "kind": "trunk",
  "vlans": [10, 20, 99],
  "label": "Uplink FW → Core",
  "media": "fibre-om4"
}
```

## 4. Exports

| Format | Rôle | Moteur |
|--------|------|--------|
| **JSON** | Source de vérité, régénérable, diffable | natif |
| **SVG**  | Éditable draw.io / Inkscape ; groupes nommés par équipement | générateur Python (même rendu que l'écran) |
| **PDF**  | Lecture universelle, présentation comité | conversion du SVG (svglib + reportlab, 100 % local) |
| VSDX / XML draw.io | plus tard | — |

## 5. Règles non négociables

1. **Snap U** : toute position est un entier de U. Le moteur refuse tout
   chevauchement et tout dépassement de baie — côté frontend **et** côté backend
   (le backend est l'autorité, `models.py` valide à la sauvegarde et à l'export).
2. **1U = 1U** : l'échelle verticale est exacte partout (écran, SVG, PDF).
3. Le dessin ne remplace jamais le tableau de brassage.
4. UI en **français**. Aucune dépendance cloud payante.
