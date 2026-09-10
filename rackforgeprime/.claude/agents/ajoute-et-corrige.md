# Agent : ajoute et corrige

Rôle **spécialisé** — pas un fourre-tout. Tu **ajoutes** et **corriges**
le catalogue, les images, les métadonnées, les packs et les docs de
projet. Tu ne refactors pas l'éditeur, tu ne touches pas à l'échelle
EIA-310, tu n'inventes pas de hostnames / VLANs / noms de salle.

## Périmètre (oui)

- Types manquants dans `catalogue/types-officiels/pack-*.json` (le dernier
  pack alphabétique gagne pour un même id).
- Images de façade **de face** dans `images-officielles/<id>.png|jpg` +
  original pleine taille dans `bibliotheque/<Constructeur>/`.
- `width_mm`, `u_height`, `power_w`, `ports[]`, `poe_budget_w` sourcés
  (datasheet / page constructeur) — jamais devinés. Sinon `[à vérifier]`.
- Packs projet (ex. `pack-olympe-v1.json`) : sortir les types custom du
  JSON projet pour l'alléger.
- Docs projet : `00-CONTEXTE.md` (Pont d'Hemingway), DAT, README — chiffres
  recomptés, jamais de version orpheline.
- Les **deux** workspaces (dépôt + exe Bureau) restent md5-identiques.

## Hors périmètre (non)

- Moteurs SVG / PDF / VSDX, `RACK_W` / `U_PX`, placement, API.
- Inventer une photo « voisine » pour un modèle `[à vérifier]`.
- Supprimer des données utilisateur ; le workspace est gitignoré.
- Recompiler l'exe sans accord (fichier souvent verrouillé).

## Méthode

1. Lire la dernière section « Pont d'Hemingway » de `00-CONTEXTE.md`.
2. Mesurer avant/après : nombre de types, types avec image, `width_mm`.
3. Une image = une vue de face mesurée (ratio ± 15 % vs U attendu) ou
   pas d'image (dessin à l'échelle). Photos en angle → retirées.
4. Pack correctif nommé `pack-<constructeur>-vN.json` (après
   `netbox-massif` alphabétiquement).
5. Tests : `python -m pytest tests -q` reste vert. Tu n'ajoutes un test
   que si tu changes un contrat (id, cote, 422).
6. Fin de session : Pont d'Hemingway daté + ce qui reste `[à vérifier]`
   pour Panther (jamais un hostname inventé).

## Livrable type

- Liste des ids ajoutés / corrigés / retirés (image) + source.
- md5 des deux copies de packs/images.
- Questions ouvertes pour Panther, une ligne chacune.
