# Plan design — Objectif 8/10 partout

> Établi le 31/08/2026 après notation par un jury de 3 agents (esthétique,
> prise en main, métier). Scores : esthétique 5,8 · prise en main 7,5 ·
> métier 6,3. Cible : **≥ 8 sur chaque lentille**. Version lisible :
> artefact « Objectif 8/10 » (claude.ai).

## Chantier 1 — Identité & chrome (esthétique)
1. **Une seule couleur de marque : orange** (#ea580c clair / #f97316 sombre)
   dans les deux thèmes, les exports et l'éclair de l'icône. Le cyan ne
   reste que comme couleur de rôle « switch ».
2. **Barre d'outils redessinée** : icônes + libellés, groupes
   Édition · Vues · Livrables, « Dossier » en bouton primaire,
   SVG/PDF/JSON dans un menu Exporter.
3. **Palette vivante** : vignette de faceplate par carte, groupes
   constructeur repliables, contraste renforcé.
4. **Un seul langage visuel en baie** : cadre commun + bandeau hostname
   superposé aussi sur les photos officielles.

## Chantier 2 — Gestes visibles (prise en main)
5. **Affordances** : crayon sur le nom de baie, bouton « ⋯ » au survol
   d'un équipement, ports qui s'allument.
6. **Astuces rotatives** en barre d'état (façon PATCHBOX, sobres).
7. **Recherche globale Ctrl+K** (hostname / VLAN / modèle → surlignage).

## Chantier 3 — Livrables irréprochables (métier)
8. **Export clair** (SVG/PDF/Dossier en blanc — un DAT s'imprime en blanc).
9. **Schéma logique avec zones** WAN/CŒUR/ACCÈS/SERVEURS, layout resserré,
   libellés non tronqués, IP de management en meta.
10. **Consommations réelles** pour les 78 modèles du pack (collecte agents).
11. **Export draw.io** + **vue arrière** des baies.

## Idées différenciantes (après les chantiers)
- Chemin de brassage illuminé (prise → panneau → port → équipement)
- Mode présentation plein écran (écran de salle réseau)
- Planche d'étiquettes imprimables générée du brassage
- Diff visuel entre deux révisions du projet
- Contrôles métier live (budget PoE, poids, U consécutifs)
- Gabarits de baies pré-remplis

## Validation
Re-notation par le même jury de 3 agents après **chaque** chantier, sur
pièces regénérées (captures + PDF). Itérer jusqu'à ≥ 8 partout.

---

## Bilan du 31/08/2026 (13 notations d agents au total)

| Lentille | Départ | Final | Objectif |
|---|---|---|---|
| Prise en main | 7,5 | **8,75** | ✅ atteint |
| Métier réseau | 6,3 | **8,25** | ✅ atteint |
| Esthétique | 5,8 | **7,63** | 🔶 reste 0,4 |

Derniers reproches esthétique (v5) et pistes retenues :
1. Mélange photo/dessin dans la baie → proposer un réglage « rendu :
   photos officielles / tout en dessin » par projet (un seul langage).
2. Pages tableaux du PDF à 60 % de blanc → fusionner brassage + BOM
   sur une page quand ils sont courts.
3. Canvas vide à droite d une baie unique → bouton fantôme « + Baie »
   en place de la future baie.

Idées métier notées au passage : taux de charge onduleur calculé
(capacité catalogue vs charge totale), liens d alimentation vers la
zone ÉNERGIE.

---

## Cap 9/10 — enseignements de la recherche terrain (31/08/2026, 2 agents)

Sources : issues/discussions GitHub NetBox, NANOG, Cisco Community,
Capterra/G2, guides TIA-606/DCIM, Packet Pushers, Auvik. Verbatims Reddit
inaccessibles (fetch bloqué) — non fabriqués.

**Fait dans la foulée** : IP de management + asset tag partout (attente
pro n°1), import CSV de brassage (plainte n°1 : saisie de masse),
export PNG (demande NetBox #1182), rendu photos/dessin, baie fantôme,
taux de charge onduleur.

**Backlog priorisé restant** :
1. Trace de câble de bout en bout (prise → panneau → switch) — LE moment
   « enfin ! » du terrain ; on a déjà l'idée « chemin illuminé ».
2. Étiquettes TIA-606 imprimables générées du brassage (`BAIE-Uxx-Pyy`),
   identifiants générés depuis la donnée, jamais retapés.
3. Appariement en masse panneau↔switch (bulk connect, NetBox #2855).
4. Face avant/arrière des panneaux (pass-through) + vue arrière des baies.
5. Export draw.io XML (interop) puis VSDX.
6. Type de média + couleur par ligne de brassage (Cat6a/OM4/DAC).
7. Vue salle/plan d'étage au-dessus des baies (floorplan) — plus tard.
Hors périmètre assumé : découverte réseau live, multi-utilisateurs cloud.
