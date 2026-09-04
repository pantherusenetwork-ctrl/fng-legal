/* RackForgePrime — éditeur de baies.
 *
 * Principes :
 *  - le projet (JSON) est la source de vérité ; l'écran n'est qu'une vue ;
 *  - snap U : toute position est un entier de U, aucune position intermédiaire ;
 *  - collision = refus au drop (fantôme rouge), côté frontend ET backend ;
 *  - mêmes constantes d'échelle que backend/rackforge/svg_export.py :
 *    le rendu écran et l'export SVG sont géométriquement identiques.
 */
"use strict";

/* ---- Constantes d'échelle (miroir de svg_export.py) ----
 * ÉCHELLE RÉELLE, GRAVÉE AU MM (EIA-310) : façade 19" = 482,6 mm sur
 * RACK_W = 440 px → 0,9117 px/mm → 1U (44,45 mm) = 40,5 px. Le slot a
 * le VRAI ratio d'une baie : les façades le remplissent sans étirement,
 * les boîtiers compacts (width_mm) s'affichent à leur largeur exacte. */
const MM_19_POUCES = 482.6;
const U_PX = 40.5, RACK_W = 440, RAIL_W = 26, FRAME_PAD = 14,
      HEADER_H = 40, FOOTER_H = 30;

/* ---- Palettes de dessin SVG par thème ----
 * « sombre » est le miroir de svg_export.py ; « clair » est la DA
 * blanc/gris/orange (meilleur de PATCHBOX/Lucid/Visio). */
const THEMES = {
  sombre: {
    frame: "#1b2230", rail: "#2a3446", hole: "#0e1420", slot: "#0e131d",
    slotLine: "#1a2130", text: "#cbd5e1", dim: "#64748b", face: "#1a1f2b",
    accent: "#f97316", danger: "#f87171",
    faceStroke: "#2c3547", pill: "#33405a", portFill: "#0a0e16",
    decorFill: "#10151f", decorStroke: "#2c3547", ring: "#3a465c",
    lcd: "#0a2027", band: "#0b0e14",
  },
  clair: {
    frame: "#ffffff", rail: "#e2e6ea", hole: "#c6ccd4", slot: "#f3f4f6",
    slotLine: "#e2e5e9", text: "#1c2126", dim: "#6b7480", face: "#ffffff",
    accent: "#ea580c", danger: "#dc2626",
    faceStroke: "#d3d8de", pill: "#c9ced4", portFill: "#ffffff",
    decorFill: "#eef0f3", decorStroke: "#c9ced4", ring: "#b8bec7",
    lcd: "#fdf3ec", band: "#1c2126",
  },
  kaki: {
    frame: "#1c220e", rail: "#2b3316", hole: "#070903", slot: "#161b0b",
    slotLine: "#262e12", text: "#d4d9b8", dim: "#8a935f", face: "#20270f",
    accent: "#eb9c14", danger: "#e06c5a",
    faceStroke: "#39421c", pill: "#4a5522", portFill: "#0e1206",
    decorFill: "#1a200d", decorStroke: "#39421c", ring: "#4d5926",
    lcd: "#12200e", band: "#0c0e06",
  },
  nuit: {
    frame: "#0b0b0e", rail: "#17171d", hole: "#050507", slot: "#060608",
    slotLine: "#121218", text: "#dde3ec", dim: "#59637a", face: "#0d0d11",
    accent: "#ff7a1a", danger: "#ff6b6b",
    faceStroke: "#20202a", pill: "#2e2e3e", portFill: "#000000",
    decorFill: "#0a0a0e", decorStroke: "#20202a", ring: "#38384c",
    lcd: "#141005", band: "#000000",
  },
};
/* Ordre du cycle du bouton thème. */
const THEME_ORDER = ["sombre", "clair", "kaki", "nuit"];
const THEME_LABELS = { sombre: "Sombre", clair: "Clair",
                       kaki: "Kaki", nuit: "Nuit" };
/* "pastel" (supprimé) mémorisé chez un utilisateur → bascule sur kaki. */
if (localStorage.getItem("rfp-theme") === "pastel")
  localStorage.setItem("rfp-theme", "kaki");
let theme = THEMES[localStorage.getItem("rfp-theme")]
  ? localStorage.getItem("rfp-theme") : "sombre";
let C = THEMES[theme];
/* Le script est chargé en fin de <body> : on peut poser le thème tout de
   suite, avant le premier rendu (pas de flash). */
document.body.dataset.theme = theme;

/* Libellés français des catégories (ordre d'affichage de la palette). */
const CATEGORY_LABELS = {
  "switch": "Switchs", "firewall": "Firewalls", "router": "Routeurs",
  "patch-panel": "Panneaux de brassage", "server": "Serveurs", "ups": "Onduleurs",
  "blank": "Obturateurs", "cable-mgmt": "Passe-câbles", "other": "Autres",
};

/* ---- État global ---- */
let catalog = { types: [], role_colors: {} };
let typesById = {};
let project = null;
let selectedItemId = null;
/* Vue active : "physical" (baies) ou "logical" (VLANs / liens). */
let viewMode = "physical";
/* Face regardée dans la vue physique : "front" ou "rear".
 * La vue arrière n'est PAS une seconde baie à redessiner (le piège
 * Visio) : c'est LA MÊME donnée vue de l'autre côté — la baie passe en
 * miroir, les U ne bougent pas, et un équipement monté en façade y
 * montre son dos. Miroir exact du backend (svg_export.py). */
let rackFace = localStorage.getItem("rfp-face") === "rear" ? "rear" : "front";
/* Baie « active » (dernière touchée en vue physique) : c'est elle que la
   vue Logique montre quand on bascule — la vue logique DE LA BAIE. */
let focusRackId = null;
/* Périmètre de la vue logique : null = toute l'architecture, sinon id de baie. */
let logicalRack = null;
/* Nom du projet dans l'espace de travail (fichier projets/<nom>.json) —
   null = projet local non encore enregistré. */
let workspaceName = localStorage.getItem("rfp-ws-name") || null;
/* Numéros U visibles (toggle façon Visio « Hide U sizes »). */
let showUNumbers = localStorage.getItem("rfp-show-u") !== "0";
/* Rendu des faceplates : "photos" (images officielles) ou "dessin"
 * (tout en faceplates dessinées — un seul langage visuel). */
let renderMode = localStorage.getItem("rfp-render") === "dessin" ? "dessin" : "photos";
/* Drag en cours : { type, itemId?, fromRackId?, ghost SVG en cours } */
let drag = null;
let itemSeq = 1;

const $ = (sel) => document.querySelector(sel);
const SVGNS = "http://www.w3.org/2000/svg";

/* =====================================================================
 * Projet
 * =================================================================== */

function newProject() {
  return {
    schema_version: 1,
    id: "prj-" + Math.random().toString(36).slice(2, 8),
    name: "Nouveau projet",
    created: new Date().toISOString(),
    racks: [newRack("A")],
    equipment_types: [],
    logical: { vlans: [], links: [] },
  };
}

function newRack(letter) {
  return {
    id: "rack-" + letter.toLowerCase(), name: "Baie " + letter,
    u_height: 42, width_inches: 19, location: "", desc_units: false,
    notes: "", items: [],
  };
}

function nextItemId() {
  /* Id unique croissant, robuste après un import (on repart du max). */
  let max = 0;
  for (const r of project.racks)
    for (const it of r.items) {
      const m = /^eq-(\d+)$/.exec(it.id);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    }
  itemSeq = Math.max(itemSeq, max + 1);
  return "eq-" + String(itemSeq++).padStart(2, "0");
}

/* =====================================================================
 * Moteur de placement (miroir de models.py — le backend fait autorité)
 * =================================================================== */

function itemSpan(item) {
  const t = typesById[item.type_id];
  const us = [];
  for (let u = item.position_u; u < item.position_u + t.u_height; u++) us.push(u);
  return us;
}

/* Position valide ? bornes de baie + aucune collision (ignoreId = déplacement). */
function canPlace(rack, positionU, uHeight, ignoreId) {
  if (positionU < 1 || positionU + uHeight - 1 > rack.u_height) return false;
  const occupied = new Set();
  for (const it of rack.items) {
    if (it.id === ignoreId) continue;
    for (const u of itemSpan(it)) occupied.add(u);
  }
  for (let u = positionU; u < positionU + uHeight; u++)
    if (occupied.has(u)) return false;
  return true;
}

/* Cohabitation dans un U (échelle réelle) : si le U visé est tenu par
 * des boîtiers compacts et que le nouveau (compact aussi) tient dans les
 * 482,6 mm restants, il se COLLE au dernier — deux FGT 60F côte à côte,
 * comme dans la vraie baie. Retourne la position x en mm, ou null. */
function tryShare(rack, u, type, ignoreId) {
  if (!type.width_mm) return null;
  const span = new Set();
  for (let uu = u; uu < u + type.u_height; uu++) span.add(uu);
  const occ = rack.items.filter((it) => it.id !== ignoreId &&
    [...itemSpan(it)].some((uu) => span.has(uu)));
  if (!occ.length) return null;            // U libre : placement normal
  for (const it of occ) {
    const t = typesById[it.type_id];
    if (!t || !t.width_mm) return null;    // un pleine-largeur : refus
  }
  /* Normalise : les compacts encore « centrés » (sans x) sont empilés
     depuis la gauche, puis le nouveau se colle à la suite. */
  let cursor = 0;
  for (const it of occ.filter((i) => i.position_x_mm != null)
                      .sort((a, b) => a.position_x_mm - b.position_x_mm))
    cursor = Math.max(cursor,
                      it.position_x_mm + typesById[it.type_id].width_mm);
  for (const it of occ.filter((i) => i.position_x_mm == null)) {
    it.position_x_mm = cursor;
    cursor += typesById[it.type_id].width_mm;
  }
  return cursor + type.width_mm <= MM_19_POUCES + 0.01 ? cursor : null;
}

function rackStats(rack) {
  let used = 0, power = 0;
  for (const it of rack.items) {
    const t = typesById[it.type_id];
    if (!t) continue;
    used += t.u_height; power += t.power_w;
  }
  return { used, free: rack.u_height - used, power };
}

/* =====================================================================
 * Rendu SVG d'une baie (géométrie identique à svg_export.py)
 * =================================================================== */

function rackSize(rack) {
  return {
    w: RACK_W + 2 * RAIL_W + 2 * FRAME_PAD,
    h: rack.u_height * U_PX + HEADER_H + FOOTER_H + 2 * FRAME_PAD,
  };
}

/* Y (haut) d'un U — U1 en bas par défaut, comme une baie réelle. */
function uToY(rack, u) {
  const top = HEADER_H + FRAME_PAD;
  return rack.desc_units ? top + (u - 1) * U_PX
                         : top + (rack.u_height - u) * U_PX;
}

/* Y écran -> U visé (pour le snap pendant le drag). */
function yToU(rack, y, uHeight) {
  const top = HEADER_H + FRAME_PAD;
  let u;
  if (rack.desc_units) {
    u = Math.floor((y - top) / U_PX) + 1;
  } else {
    /* On vise le U du BAS de l'équipement : le curseur pointe son centre. */
    const uTop = rack.u_height - Math.floor((y - top) / U_PX);
    u = uTop - uHeight + 1;
  }
  return Math.max(1, Math.min(u, rack.u_height - uHeight + 1));
}

function svgEl(tag, attrs, text) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (text !== undefined) el.textContent = text;
  return el;
}

/* Types disponibles = catalogue intégré + types du projet (imports).
 * Un type projet portant le même id qu'un type intégré le REMPLACE :
 * c'est le mécanisme « Remplacer par image officielle ». */
function refreshTypes() {
  typesById = {};
  for (const t of catalog.types) typesById[t.id] = t;
  for (const t of (project?.equipment_types || [])) typesById[t.id] = t;
}

/* Images de catalogue en CHARGEMENT DIFFÉRÉ : le catalogue arrive léger
   (has_image), l'image d'un type n'est récupérée que quand un équipement
   posé en a besoin — indispensable avec 1 000+ types. */
const _imgFetching = new Set();
function ensureProjectImages() {
  const wanted = new Set();
  for (const rack of project?.racks || [])
    for (const it of rack.items) wanted.add(it.type_id);
  const missing = [...wanted].filter((id) => {
    const t = typesById[id];
    return t && t.has_image && !t.faceplate_image && !t.faceplate_svg
           && !_imgFetching.has(id);
  });
  if (!missing.length) return;
  missing.forEach((id) => _imgFetching.add(id));
  Promise.all(missing.map((id) =>
    fetch("/api/catalog/image/" + encodeURIComponent(id))
      .then((r) => r.json())
      .then((d) => { if (d.image && typesById[id]) typesById[id].faceplate_image = d.image; })
      .catch(() => {})
  )).then(() => {
    if (viewMode === "physical") renderAll();
  });
}
function allTypes() {
  return Object.values(typesById);
}

/* =====================================================================
 * Info-bulle de survol (esprit AirWave : la config du port sous la souris)
 * =================================================================== */

let tipEl = null;
function showTip(html, evt) {
  if (!tipEl) {
    tipEl = document.createElement("div");
    tipEl.id = "hover-tip";
    document.body.appendChild(tipEl);
  }
  tipEl.innerHTML = html;
  tipEl.style.display = "block";
  /* Décalé du curseur, rabattu si bord d'écran. */
  const pad = 14;
  const rect = tipEl.getBoundingClientRect();
  let tx = evt.clientX + pad, ty = evt.clientY + pad;
  if (tx + rect.width > window.innerWidth - 8) tx = evt.clientX - rect.width - pad;
  if (ty + rect.height > window.innerHeight - 8) ty = evt.clientY - rect.height - pad;
  tipEl.style.left = tx + "px";
  tipEl.style.top = ty + "px";
}
function hideTip() {
  if (tipEl) tipEl.style.display = "none";
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
/* Un drag qui démarre chasse l'info-bulle. */
document.addEventListener("pointerdown", hideTip, true);

/* Config d'un port : la ligne de brassage si elle existe, sinon les
 * valeurs héritées de l'équipement. */
function portTipHTML(t, item, port) {
  const pu = (item?.meta?.port_usage || []).find((p) => p.port === port.name);
  const vlan = pu?.vlan || item?.meta?.vlan || "";
  const outlet = pu?.outlet || item?.meta?.wall_outlet || "";
  const rows = [
    ["Type", port.type],
    ["VLAN", vlan],
    ["Prise murale", outlet],
    ["Usage", pu?.usage || ""],
    ["État", ETAT_LABELS[pu?.etat] || ""],
    ["PoE", (isPoE(t) && /base-t/i.test(port.type || "")) ? "oui ⚡" : ""],
  ].filter(([, v]) => v);
  return `<div class="tip-title">${esc(port.name)}</div>` +
    (rows.length
      ? rows.map(([k, v]) => `<div class="tip-row"><span>${k}</span>${esc(v)}</div>`).join("")
      : `<div class="tip-empty">non brassé — à renseigner dans l'inspecteur</div>`);
}

/* Résumé d'un équipement (survol d'une image officielle : les ports
 * individuels n'y sont pas cliquables, on montre la fiche). */
function itemTipHTML(t, item) {
  const m = item?.meta || {};
  const rows = [
    ["Modèle", `${t.vendor} ${t.model}`],
    ["Hauteur", t.u_height + "U"],
    ["IP mgmt", m.mgmt_ip],
    ["VLAN", m.vlan],
    ["Prise murale", m.wall_outlet],
    ["N° série", m.serial],
    ["Asset", m.asset],
    ["Ports brassés", (m.port_usage || []).length || ""],
  ].filter(([, v]) => v);
  return `<div class="tip-title">${esc(m.hostname || t.model)}</div>` +
    rows.map(([k, v]) => `<div class="tip-row"><span>${k}</span>${esc(v)}</div>`).join("");
}

/* Cartouche de nom À CÔTÉ de l'équipement (style Patchdocs) — miroir
   de _name_plate() côté Python : rien d'écrit sur le matériel. */
const LABEL_W = 138;
function drawNamePlate(g, label, x, y, h) {
  /* Polices à l'échelle U_PX=40.5 — miroir Python. */
  const txt = label.length <= 15 ? label : label.slice(0, 14) + "…";
  g.appendChild(svgEl("rect", {
    x: x + 4, y: y + 2, width: LABEL_W - 6, height: h - 4, rx: 3, fill: C.band,
  }));
  g.appendChild(svgEl("text", {
    x: x + 12, y: y + h / 2 + 5, "font-size": 15, "font-weight": "bold",
    fill: "#f1f5f9", "font-family": "system-ui, sans-serif",
  }, txt));
}

/* Empreinte réelle de l'équipement dans la façade 19", au mm — déjà mise
 * en MIROIR quand la baie est regardée par l'arrière. La donnée
 * (position_x_mm) ne bouge jamais : seule sa projection change.
 * Miroir exact de _item_box() côté Python. */
function itemBox(t, item, x) {
  const iw = t.width_mm
    ? Math.min(RACK_W, RACK_W * t.width_mm / MM_19_POUCES) : RACK_W;
  const shared = !!(t.width_mm && item && item.position_x_mm != null);
  let ix;
  if (shared) {
    let xmm = item.position_x_mm;
    if (rackFace === "rear") xmm = MM_19_POUCES - xmm - t.width_mm;
    ix = x + RACK_W * xmm / MM_19_POUCES;
  } else {
    ix = x + (RACK_W - iw) / 2;
  }
  return { ix, iw, shared };
}

/* Dos d'un équipement — dessiné NEUTRE, jamais inventé. La sérigraphie
 * arrière réelle des types du catalogue n'est pas connue : on ne la
 * fabrique pas. On montre ce que TOUT rackable a (grille d'aération +
 * prise secteur) et les repères de lecture passés en miroir.
 * Miroir exact de _rear_faceplate() côté Python. */
function drawRearFaceplate(g, t, x, y, w, label, selected) {
  const h = t.u_height * U_PX;
  const yc = y + h / 2;
  const lw = (label && w > LABEL_W + 70) ? LABEL_W : 0;
  g.appendChild(svgEl("rect", { x, y: y + 1, width: w, height: h - 2, rx: 3,
    fill: C.decorFill || C.face, stroke: selected ? C.accent : C.faceStroke,
    "stroke-width": selected ? 1.6 : 1 }));
  g.appendChild(svgEl("rect", { x, y: y + 1, width: w, height: h - 2, rx: 3,
    fill: t.color, "fill-opacity": 0.05 }));
  /* Liseré de rôle à DROITE : le miroir exact de celui de la façade. */
  g.appendChild(svgEl("rect", { x: x + w - 4, y: y + 1, width: 4,
    height: h - 2, fill: t.color, "fill-opacity": 0.5 }));
  const vx0 = x + 52, vx1 = x + w - lw - 14;
  for (let vx = vx0; vx < vx1 - 40; vx += 7)
    /* Filet de contour : sans lui, les fentes se confondent avec le
       corps sur les thèmes sombres (hole ≈ decorFill). */
    g.appendChild(svgEl("rect", { x: vx, y: y + 5, width: 3, height: h - 10,
      rx: 1.5, fill: C.hole, stroke: C.faceStroke, "stroke-width": 0.5 }));
  if (vx1 - vx0 > 40) {
    g.appendChild(svgEl("rect", { x: vx1 - 32, y: yc - 7, width: 24,
      height: 14, rx: 2, fill: C.portFill || C.slot,
      stroke: C.decorStroke || C.faceStroke, "stroke-width": 1 }));
    for (let k = 0; k < 3; k++)
      g.appendChild(svgEl("rect", { x: vx1 - 27 + k * 6, y: yc - 3,
        width: 2.4, height: 6, rx: 1, fill: t.color, "fill-opacity": 0.7 }));
  }
  if (lw) drawNamePlate(g, label, x + w - LABEL_W, y, h);
  if (w > 60) {
    g.appendChild(svgEl("rect", { x: x + 8, y: yc - 9.5, width: 36,
      height: 19, rx: 9, fill: C.face, "fill-opacity": 0.85,
      stroke: C.pill, "stroke-width": 1 }));
    g.appendChild(svgEl("text", { x: x + 26, y: yc + 4.5,
      "text-anchor": "middle", "font-size": 13, fill: C.dim,
      "font-family": "monospace" }, t.u_height + "U"));
  }
}

/* Faceplate placeholder — même dessin que _faceplate_placeholder() côté Python. */
function drawFaceplate(g, t, x, y, label, selected, item) {
  const h = t.u_height * U_PX;
  const lw = label ? LABEL_W : 0;
  if (t.faceplate_image && renderMode !== "dessin") {
    /* Mode photos : AUCUN cartouche — le nom vient au survol (fiche).
       Le slot est à l'ÉCHELLE RÉELLE : jamais d'étirement (meet
       toujours). Une façade 19" le remplit d'elle-même ; un boîtier
       compact (width_mm) est cadré à SA largeur, au mm — et s'il a une
       position_x_mm, il cohabite côte à côte avec ses voisins du même U
       (deux FGT 60F collés, comme en vrai). Miroir Python. */
    const { ix, iw, shared } = itemBox(t, item, x);
    const bx = shared ? ix : x, bw = shared ? iw : RACK_W;
    g.appendChild(svgEl("rect", { x: bx, y: y + 1, width: bw, height: h - 2, fill: C.face }));
    const img = svgEl("image", {
      x: ix, y: y + 1, width: iw, height: h - 2,
      preserveAspectRatio: "xMidYMid meet",
      href: t.faceplate_image,
    });
    g.appendChild(img);
    /* Sur une photo officielle les ports ne sont pas localisables :
       le survol montre la fiche de l'équipement. */
    if (item) {
      img.addEventListener("mousemove", (e) => showTip(itemTipHTML(t, item), e));
      img.addEventListener("mouseleave", hideTip);
    }
    /* Le MÊME cadre que les dessins : bordure, liseré de rôle, pastille
       U — limité à l'EMPREINTE de l'équipement quand il cohabite
       (miroir Python ; pas de pastille à deux : fouillis). */
    g.appendChild(svgEl("rect", {
      x: bx, y: y + 1, width: bw, height: h - 2, rx: 2, fill: "none",
      stroke: C.faceStroke, "stroke-width": 1,
    }));
    g.appendChild(svgEl("rect", { x: bx, y: y + 1, width: 4, height: h - 2, fill: t.color }));
    if (!shared) {
      g.appendChild(svgEl("rect", {
        x: x + RACK_W - 44, y: y + h / 2 - 9.5, width: 36, height: 19, rx: 9,
        fill: C.face, "fill-opacity": 0.85, stroke: C.pill, "stroke-width": 1,
      }));
      g.appendChild(svgEl("text", {
        x: x + RACK_W - 26, y: y + h / 2 + 4.5, "text-anchor": "middle",
        "font-size": 13, fill: C.dim, "font-family": "monospace",
      }, t.u_height + "U"));
    }
    if (selected)
      g.appendChild(svgEl("rect", { x: bx, y: y + 1, width: bw, height: h - 2,
        fill: "none", stroke: C.accent, "stroke-width": 1.6 }));
    return;
  }
  const yc = y + h / 2;
  /* Corps plat teinté par rôle — style PATCHBOX/Lucid (miroir Python). */
  g.appendChild(svgEl("rect", {
    x, y: y + 1, width: RACK_W, height: h - 2, rx: 3, fill: C.face,
    stroke: selected ? C.accent : C.faceStroke, "stroke-width": selected ? 1.6 : 1,
  }));
  g.appendChild(svgEl("rect", {
    x, y: y + 1, width: RACK_W, height: h - 2, rx: 3,
    fill: t.color, "fill-opacity": 0.07,
  }));
  g.appendChild(svgEl("rect", { x, y: y + 1, width: 4, height: h - 2, fill: t.color }));
  /* Cartouche de nom à côté, décor dans la zone restante (miroir Python). */
  if (label) drawNamePlate(g, label, x, y, h);
  if (["server", "ups", "cable-mgmt"].includes(t.category))
    drawCategoryDecor(g, t, x + lw, y, RACK_W - lw, h);
  else if ((t.ports || []).length)
    drawPortBanks(g, t, item, x + lw, y, RACK_W - lw, h);
  /* Pastille de hauteur U. */
  g.appendChild(svgEl("rect", {
    x: x + RACK_W - 44, y: yc - 9.5, width: 36, height: 19, rx: 9,
    fill: C.face, "fill-opacity": 0.85, stroke: C.pill, "stroke-width": 1,
  }));
  g.appendChild(svgEl("text", {
    x: x + RACK_W - 26, y: yc + 4.5, "text-anchor": "middle",
    "font-size": 13, fill: C.dim, "font-family": "monospace",
  }, t.u_height + "U"));
}

/* Ports groupés en banques de 6, 2 rangées au-delà de 12 (miroir Python).
 * Chaque port a une zone de survol élargie → info-bulle de config. */
function drawPortBanks(g, t, item, x, y, w, h) {
  const color = t.color;
  const n = Math.min((t.ports || []).length, 48);
  const rows = n > 12 ? 2 : 1;
  const cols = Math.ceil(n / rows);
  /* Dimensions à l'échelle U_PX=40.5 — miroir Python. */
  const pw = 8, gapx = 2, group = 6, ggap = 6;
  const ph = rows === 2 ? 10 : 14;
  const groups = Math.ceil(cols / group);
  const totalW = cols * (pw + gapx) - gapx + (groups - 1) * ggap;
  const x0 = x + w - 46 - totalW;
  const blockH = rows * ph + (rows - 1) * 4;
  const y0 = y + (h - blockH) / 2;
  for (let i = 0; i < n; i++) {
    const r = i % rows, c = Math.floor(i / rows);
    const px = x0 + c * (pw + gapx) + Math.floor(c / group) * ggap;
    const py = y0 + r * (ph + 4);
    const portRect = svgEl("rect", {
      x: px, y: py, width: pw, height: ph, rx: 1,
      fill: C.portFill, stroke: color, "stroke-width": 0.7,
    });
    g.appendChild(portRect);
    g.appendChild(svgEl("rect", {
      x: px + 2, y: py + ph - 1.6, width: 3, height: 1.6,
      fill: color, "fill-opacity": 0.85,
    }));
    /* Zone de survol invisible, plus large que le port dessiné ;
       le port s'allume sous la souris (affordance). */
    const port = t.ports[i];
    const hit = svgEl("rect", {
      x: px - 1, y: py - 2, width: pw + 3, height: ph + 5,
      fill: "transparent", class: "port-hit",
    });
    hit.addEventListener("mousemove", (e) => {
      portRect.setAttribute("stroke-width", "1.8");
      showTip(portTipHTML(t, item, port), e);
    });
    hit.addEventListener("mouseleave", () => {
      portRect.setAttribute("stroke-width", "0.7");
      hideTip();
    });
    g.appendChild(hit);
  }
}

/* Décor par catégorie pour les types sans ports (miroir Python). */
function drawCategoryDecor(g, t, x, y, w, h) {
  /* Dimensions à l'échelle U_PX=40.5 — miroir Python. */
  if (t.category === "server") {
    const bw = 17, gap = 4, count = 10;
    const x0 = x + w - 46 - count * (bw + gap);
    for (let i = 0; i < count; i++) {
      const bx = x0 + i * (bw + gap);
      g.appendChild(svgEl("rect", {
        x: bx, y: y + 4, width: bw, height: h - 8, rx: 1,
        fill: C.decorFill, stroke: C.decorStroke, "stroke-width": 0.7,
      }));
      g.appendChild(svgEl("circle", {
        cx: bx + bw / 2, cy: y + 9, r: 2, fill: t.color,
      }));
    }
  } else if (t.category === "ups") {
    g.appendChild(svgEl("rect", {
      x: x + w - 210, y: y + h / 2 - 12, width: 40, height: 24, rx: 3,
      fill: C.lcd, stroke: t.color, "stroke-width": 1,
    }));
    for (let i = 0; i < 24; i++)
      g.appendChild(svgEl("rect", {
        x: x + w - 155 + i * 6, y: y + h / 2 - 10, width: 3, height: 20,
        rx: 1.5, fill: C.decorFill,
      }));
  } else if (t.category === "cable-mgmt") {
    for (let i = 0; i < 4; i++)
      g.appendChild(svgEl("rect", {
        x: x + 200 + i * 50, y: y + 4, width: 30, height: h - 8, rx: 6,
        fill: "none", stroke: C.ring, "stroke-width": 3,
      }));
  }
}

/* Motif discret dans les U LIBRES (idée Panther) : suit le fond du plan
   choisi — ruche, points, carreaux, lignes — en version très atténuée.
   « Uni » = U libres unis. Écran seulement : les exports DAT restent sobres. */
function makeSlotPattern(rackId) {
  if (canvasBg === "uni") return null;
  const col = C.slotLine;
  const pat = svgEl("pattern", {
    id: "slotpat-" + rackId, patternUnits: "userSpaceOnUse",
    width: 12, height: 12,
  });
  if (canvasBg === "points") {
    pat.setAttribute("width", 10); pat.setAttribute("height", 10);
    pat.appendChild(svgEl("circle", { cx: 2, cy: 2, r: 1, fill: col,
      "fill-opacity": 0.6 }));
  } else if (canvasBg === "carreaux") {
    pat.appendChild(svgEl("path", { d: "M12 0H0V12", fill: "none",
      stroke: col, "stroke-opacity": 0.5, "stroke-width": 1 }));
  } else if (canvasBg === "lignes") {
    pat.appendChild(svgEl("line", { x1: 0, y1: 6, x2: 12, y2: 6,
      stroke: col, "stroke-opacity": 0.5 }));
  } else {  /* ruche */
    pat.setAttribute("width", 14); pat.setAttribute("height", 24.5);
    pat.appendChild(svgEl("path", {
      d: "M7 4.6l6.5 3.75v7.5L7 19.6.5 15.85v-7.5L7 4.6z"
         + "M0 16.25l6.5 3.75v8M13.5 16.25L7 20m0-16.5L.5 0m6.5 3.5L13.5 0",
      fill: "none", stroke: col, "stroke-opacity": 0.45, "stroke-width": 0.8,
    }));
  }
  return pat;
}

function renderRackSVG(rack) {
  const { w, h } = rackSize(rack);
  const innerX = FRAME_PAD + RAIL_W;
  const svg = svgEl("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}` });
  svg.dataset.rackId = rack.id;
  svg.addEventListener("pointerdown", () => { focusRackId = rack.id; }, true);
  const slotPat = makeSlotPattern(rack.id);
  if (slotPat) {
    const defs = svgEl("defs", {});
    defs.appendChild(slotPat);
    svg.appendChild(defs);
  }

  svg.appendChild(svgEl("rect", { x: 0, y: 0, width: w, height: h, rx: 6,
    fill: C.frame, stroke: C.faceStroke, "stroke-width": 1.5 }));
  /* Nom de baie éditable — le crayon apparaît au survol (affordance). */
  const titleG = svgEl("g", { class: "rack-title", style: "cursor: pointer;" });
  titleG.appendChild(svgEl("text", { x: w / 2, y: 22, "text-anchor": "middle",
    "font-size": 19, "font-weight": "bold", fill: C.text }, rack.name));
  const pencil = svgEl("g", { class: "rack-pencil",
    transform: `translate(${w / 2 + rack.name.length * 5.3 + 14}, 10)` });
  pencil.appendChild(svgEl("path", {
    d: "M 0 9 L 8 1 L 11 4 L 3 12 L 0 12 Z", fill: "none",
    stroke: C.accent, "stroke-width": 1.4, "stroke-linejoin": "round",
  }));
  titleG.appendChild(pencil);
  titleG.addEventListener("click", (e) => openRackMenu(e, rack));
  svg.appendChild(titleG);
  /* Clic droit n'importe où sur la baie (hors équipement) : mêmes
     options — plus besoin de connaître le clic sur le nom. */
  svg.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    openRackMenu(e, rack);
  });
  /* Badge de face : impossible de confondre les deux vues, à l'écran
     comme sur un export imprimé. */
  if (rackFace === "rear") {
    svg.appendChild(svgEl("rect", { x: w - 104, y: 7, width: 96, height: 18,
      rx: 9, fill: C.accent, "fill-opacity": 0.16, stroke: C.accent,
      "stroke-width": 1 }));
    svg.appendChild(svgEl("text", { x: w - 56, y: 20, "text-anchor": "middle",
      "font-size": 11, "font-weight": "bold", fill: C.accent }, "VUE ARRIÈRE"));
  }
  /* Localisation (salle, adresse) sous le nom — comme à l'export. */
  if (rack.location)
    svg.appendChild(svgEl("text", { x: w / 2, y: 37, "text-anchor": "middle",
      "font-size": 12, fill: C.dim }, rack.location));

  const zoneY = HEADER_H + FRAME_PAD, zoneH = rack.u_height * U_PX;
  svg.appendChild(svgEl("rect", { x: innerX, y: zoneY, width: RACK_W, height: zoneH, fill: C.slot }));
  for (const rx of [FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W])
    svg.appendChild(svgEl("rect", { x: rx, y: zoneY, width: RAIL_W, height: zoneH, fill: C.rail }));

  /* Graduations U + trous de vissage. */
  for (let u = 1; u <= rack.u_height; u++) {
    const y = uToY(rack, u);
    svg.appendChild(svgEl("line", { x1: innerX, y1: y, x2: innerX + RACK_W, y2: y,
      stroke: C.slotLine, "stroke-width": 1 }));
    for (const rx of [FRAME_PAD, FRAME_PAD + RAIL_W + RACK_W]) {
      if (showUNumbers)
        svg.appendChild(svgEl("text", { x: rx + RAIL_W / 2, y: y + U_PX / 2 + 5,
          "text-anchor": "middle", "font-size": 14, fill: C.dim,
          "font-family": "monospace" }, String(u)));
      for (let k = 0; k < 3; k++)
        svg.appendChild(svgEl("rect", { x: rx + 2, y: y + 4 + k * ((U_PX - 8) / 2),
          width: 3, height: 3, rx: 1, fill: C.hole }));
    }
  }
  svg.appendChild(svgEl("line", { x1: innerX, y1: zoneY + zoneH,
    x2: innerX + RACK_W, y2: zoneY + zoneH, stroke: C.slotLine, "stroke-width": 1 }));

  /* Équipements. */
  for (const item of rack.items) {
    const t = typesById[item.type_id];
    if (!t) continue;
    const topU = rack.desc_units ? item.position_u : item.position_u + t.u_height - 1;
    const y = uToY(rack, topU);
    const g = svgEl("g", { "data-item-id": item.id, class: "rack-item" });
    if (item.id === selectedItemId) g.classList.add("item-selected");
    /* RÈGLE : rien n'est écrit sur le dessin SAUF un hostname saisi PAR
       L'UTILISATEUR — jamais de « constructeur modèle » auto-posé (le
       survol, lui, donne toujours la fiche complète). */
    const label = item.meta.hostname || "";
    /* On voit la FAÇADE d'un équipement quand la face regardée est celle
       sur laquelle il est monté ; sinon on voit son dos. */
    if ((item.face || "front") === rackFace) {
      drawFaceplate(g, t, innerX, y, label, item.id === selectedItemId, item);
    } else {
      const b = itemBox(t, item, innerX);
      drawRearFaceplate(g, t, b.shared ? b.ix : innerX, y,
        b.shared ? b.iw : RACK_W, label, item.id === selectedItemId);
    }
    /* Clic = inspection ; pointerdown long = déplacement (géré globalement). */
    g.addEventListener("pointerdown", (e) => startItemDrag(e, rack, item));
    /* Survol = surlignage des équipements connectés (esprit PATCHBOX). */
    g.addEventListener("mouseenter", () => { if (!drag) highlightConnections(item.id); });
    g.addEventListener("mouseleave", clearHighlight);
    /* Clic droit = menu contextuel ; double-clic = fiche de l'équipement
       (ports, VLANs, état de chaque interface — esprit Aruba Central). */
    g.addEventListener("contextmenu", (e) => openItemMenu(e, rack, item));
    g.addEventListener("dblclick", () => openDeviceSheet(item.id));
    /* Bouton « ⋯ » visible au survol : le menu sans connaître le clic
       droit (affordance). */
    const t2 = typesById[item.type_id];
    const my = uToY(rack, rack.desc_units ? item.position_u
      : item.position_u + t2.u_height - 1) + (t2.u_height * U_PX) / 2;
    const more = svgEl("g", { class: "item-more", style: "cursor: pointer;" });
    more.appendChild(svgEl("circle", { cx: innerX + RACK_W - 46, cy: my,
      r: 7.5, fill: C.frame, stroke: C.accent, "stroke-width": 1 }));
    for (const dx of [-3.4, 0, 3.4])
      more.appendChild(svgEl("circle", { cx: innerX + RACK_W - 46 + dx,
        cy: my, r: 1, fill: C.accent }));
    more.addEventListener("click", (e) => {
      e.stopPropagation();
      openItemMenu(e, rack, item);
    });
    more.addEventListener("pointerdown", (e) => e.stopPropagation());
    g.appendChild(more);
    svg.appendChild(g);
  }

  /* Slots libres cliquables (geste PATCHBOX) : pointillés au survol,
   * clic = popover d'ajout rapide sans passer par le drag. */
  const occupied = new Set();
  for (const it of rack.items) for (const u of itemSpan(it)) occupied.add(u);
  for (let u = 1; u <= rack.u_height; u++) {
    if (occupied.has(u)) continue;
    const slot = svgEl("rect", {
      x: innerX + 2, y: uToY(rack, u) + 2, width: RACK_W - 4, height: U_PX - 4,
      rx: 2, class: "slot-free",
      fill: slotPat ? `url(#slotpat-${rack.id})` : "transparent",
    });
    slot.addEventListener("click", (e) => openSlotPopover(e, rack, u));
    svg.appendChild(slot);
  }

  /* Stats de la baie. */
  const st = rackStats(rack);
  svg.appendChild(svgEl("text", { x: w / 2, y: h - FOOTER_H / 2, "text-anchor": "middle",
    "font-size": 14, fill: C.accent, "font-family": "monospace" },
    `${st.used}U occupés · ${st.free}U libres · ${st.power} W`));

  return svg;
}

/* =====================================================================
 * Fiche équipement (vue type Aruba Central) : tuiles + grille de ports
 * =================================================================== */

let deviceItemId = null; // équipement affiché dans la fiche

function portUsageOf(item, portName) {
  return (item.meta.port_usage || []).find((p) => p.port === portName);
}

/* PoE ? — déduit du nom du modèle (POE/FPOE/UPOE, et -xxP / -xxU Cisco). */
function isPoE(t) {
  const s = `${t.model} ${t.id}`;
  return /(^|[^a-z])(poe|fpoe|upoe)([^a-z]|$)/i.test(s) ||
         (t.vendor === "Cisco" && /-\d+(p|u)\b/i.test(t.model));
}

const ETAT_LABELS = { up: "Up", down: "Down", reserve: "Réservé" };

function openDeviceSheet(itemId) {
  const found = findItem(itemId);
  if (!found) return;
  const { rack, item } = found;
  const t = typesById[item.type_id];
  deviceItemId = itemId;
  $("#device-port-form").hidden = true;
  $("#device-trace").hidden = true;

  $("#device-title").textContent = item.meta.hostname || `${t.vendor} ${t.model}`;
  $("#device-sub").textContent =
    `${t.vendor} ${t.model} · ${t.u_height}U · ${rack.name} U${item.position_u}` +
    (isPoE(t) ? " · PoE ⚡" : "") +
    (item.meta.mgmt_ip ? ` · ${item.meta.mgmt_ip}` : "") +
    (item.meta.serial ? ` · S/N ${item.meta.serial}` : "") +
    (item.meta.asset ? ` · ${item.meta.asset}` : "");

  /* Renommer depuis la fiche : le nom saisi ICI est un nom MANUEL — il
     s'écrit donc sur le schéma (c'est la règle : rien d'automatique). */
  const doRename = async () => {
    const nom = await askText("Nom de l'équipement",
      "Laisse vide pour ne rien écrire sur le schéma (le survol garde la fiche).",
      item.meta.hostname || "");
    if (nom === null) return;
    item.meta.hostname = nom.trim();
    $("#device-title").textContent = item.meta.hostname ||
      `${t.vendor} ${t.model}`;
    saveLocal();
    renderAll();
  };
  $("#btn-rename-device").onclick = doRename;
  $("#device-title").onclick = doRename;

  /* La VUE : la façade réelle de l'équipement, en grand dans la fiche. */
  const photo = $("#device-photo");
  if (t.faceplate_image) {
    photo.querySelector("img").src = t.faceplate_image;
    photo.hidden = false;
  } else {
    photo.hidden = true;
  }

  const ports = t.ports || [];
  const used = ports.filter((p) => portUsageOf(item, p.name)).length;
  const tiles = [
    ["Ports totaux", ports.length],
    ["Brassés", used],
    ["Libres", ports.length - used],
    ["Consommation", `${t.power_w} W`],
  ];
  /* Budget PoE : tiré (somme des ports) / budget (saisi sur l'équipement,
     sinon datasheet du type, sinon « ? » — jamais deviné). */
  const poeDrawn = (item.meta.port_usage || [])
    .reduce((a, pu) => a + (parseFloat(pu.poe_w) || 0), 0);
  const poeBudget = item.meta.poe_budget_w ?? t.poe_budget_w ?? null;
  let poeCls = "";
  if (poeBudget) {
    const taux = poeDrawn / poeBudget;
    poeCls = taux > 1 ? " tile-poe-depassement" : taux >= 0.8 ? " tile-poe-alerte" : "";
  }
  if (isPoE(t) || poeBudget || poeDrawn)
    tiles.push(["PoE tiré / budget",
      `${+poeDrawn.toFixed(1)} / ${poeBudget ? poeBudget + " W" : "?"}` +
      (poeBudget ? ` (${Math.round(100 * poeDrawn / poeBudget)} %)` : ""), poeCls]);
  $("#device-tiles").innerHTML = tiles.map(([k, v, cls]) =>
    `<div class="tile${cls || ""}"><div class="tile-k">${k}` +
    (k.startsWith("PoE") ? ' <span class="tile-edit" title="Saisir le budget PoE (datasheet)">✎</span>' : "") +
    `</div><div class="tile-v">${v}</div></div>`).join("");
  $("#device-tiles .tile-edit")?.addEventListener("click", async () => {
    const v = await askText("Budget PoE de cet équipement (W)",
      "Valeur datasheet (ex : 370 pour un 2930F-48G-PoE+ 370 W). Vide = inconnu.",
      poeBudget ? String(poeBudget) : "");
    if (v === null) return;
    const n = parseFloat(String(v).replace(",", "."));
    item.meta.poe_budget_w = Number.isFinite(n) && n >= 0 ? n : null;
    saveLocal();
    openDeviceSheet(deviceItemId);
  });

  /* Grille façon switch réel : impairs en haut, pairs en bas. */
  const grid = $("#device-grid");
  grid.innerHTML = "";
  if (!ports.length) {
    grid.innerHTML = '<div class="dialog-hint">Cet équipement n\'expose pas de ports.</div>';
  } else {
    const cols = Math.ceil(ports.length / 2);
    grid.style.gridTemplateColumns = `repeat(${cols}, 30px)`;
    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < 2; r++) {
        const i = c * 2 + r;
        const port = ports[i];
        const cell = document.createElement("div");
        cell.className = "dp-cell";
        if (!port) { grid.appendChild(cell); continue; }
        const pu = portUsageOf(item, port.name);
        cell.classList.add(pu ? "p-used" : "p-free");
        if (pu?.etat) cell.classList.add("p-" + pu.etat);
        const poe = isPoE(t) && /base-t/i.test(port.type || "");
        cell.innerHTML = `<span class="dp-num">${i + 1}</span>` +
          (poe ? '<span class="dp-poe">⚡</span>' : "");
        cell.title = port.name;
        cell.addEventListener("mousemove", (e) => showTip(portTipHTML(t, item, port), e));
        cell.addEventListener("mouseleave", hideTip);
        cell.addEventListener("click", () => {
          /* Mode câblage actif : ce clic est le port d'ARRIVÉE. */
          if (cableFrom && cableFrom.itemId !== item.id) {
            finishCabling(item, port);
            return;
          }
          openPortEditor(item, port);
        });
        /* Clic droit = état direct : Up / Down / Réservé / Brassé /
           Libre — la couleur change en un geste, sans formulaire. */
        cell.addEventListener("contextmenu", (e) => {
          e.preventDefault();
          openPortStateMenu(e, item, port);
        });
        grid.appendChild(cell);
      }
    }
  }

  /* VLANs vus sur cet équipement. */
  const vlans = new Set();
  if (item.meta.vlan) vlans.add(item.meta.vlan);
  for (const pu of item.meta.port_usage || []) if (pu.vlan) vlans.add(pu.vlan);
  const vlanNames = { };
  for (const v of project.logical?.vlans || []) vlanNames[String(v.vid)] = v;
  $("#device-vlans").innerHTML = vlans.size
    ? "VLANs : " + [...vlans].map((v) => {
        const known = vlanNames[String(v)];
        const color = known?.color || "#8b95a3";
        const name = known ? ` ${esc(known.name)}` : "";
        return `<span class="vlan-chip"><span class="role-dot" ` +
               `style="background:${color}"></span>${esc(v)}${name}</span>`;
      }).join(" ")
    : '<span class="dialog-hint">Aucun VLAN renseigné sur cet équipement.</span>';

  $("#device-dialog").showModal();
}

/* ---- Câblage libre port-à-port : clic port -> type de câble -> clic
   port d'arrivée (dans la fiche d'un autre équipement) -> lien créé. */
let cableFrom = null; // {itemId, port, media}

const CABLE_TYPES = [
  ["Cuivre cat6a", "cuivre-cat6a"], ["Cuivre cat6", "cuivre-cat6"],
  ["Fibre OM4 (multimode)", "fibre-om4"], ["Fibre OS2 (monomode)", "fibre-os2"],
  ["DAC / Twinax", "dac"], ["Autre", ""],
];

function startCabling(e, item, port) {
  /* La modale passe au-dessus de tout : on la ferme AVANT le menu. */
  $("#device-dialog").close();
  _logicalMenu(e, `Câble depuis ${port.name}`, CABLE_TYPES.map(
    ([label, media]) => [label, () => {
      cableFrom = { itemId: item.id, port: port.name, media };
      renderStatus(`Câblage ${label} depuis ` +
        `${item.meta.hostname || item.id} · ${port.name} — double-cliquez ` +
        "l'équipement d'arrivée puis cliquez son port (Échap pour annuler)");
    }]));
}

function finishCabling(item, port) {
  const cf = cableFrom;
  cableFrom = null;
  $("#device-dialog").close();
  openLinkDialog(null, { from: cf.itemId, to: item.id });
  const f = $("#link-form");
  f.elements.from_port.value = cf.port;
  f.elements.to_port.value = port.name;
  f.elements.media.value = cf.media;
  renderStatus("");
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && cableFrom) {
    cableFrom = null;
    renderStatus("Câblage annulé");
  }
});

let editingPort = null;
/* Menu d'état rapide d'un port (clic droit dans la fiche) : la couleur
   change en un geste — Up / Down / Réservé / Brassé / Libre. */
function openPortStateMenu(e, item, port) {
  document.getElementById("port-state-menu")?.remove();
  const menu = document.createElement("div");
  menu.id = "port-state-menu";
  const states = [
    ["up", "● Up", "#22c55e"],
    ["down", "● Down", "#ef4444"],
    ["reserve", "● Réservé", "#eab308"],
    ["", "● Brassé", "#f97316"],
    ["libre", "○ Libre", ""],
  ];
  for (const [val, lbl, color] of states) {
    const b = document.createElement("button");
    b.textContent = lbl;
    if (color) b.style.color = color;
    b.addEventListener("click", async () => {
      menu.remove();
      let pu = portUsageOf(item, port.name);
      if (val === "libre") {
        if (pu && (pu.vlan || pu.outlet || pu.usage)) {
          const ok = await askConfirm(`Libérer le port ${port.name} ?`,
            "Sa config de brassage (VLAN, prise, usage) sera effacée.");
          if (!ok) return;
        }
        item.meta.port_usage =
          (item.meta.port_usage || []).filter((u) => u.port !== port.name);
      } else {
        if (!pu) {
          pu = { port: port.name, outlet: "", vlan: "", usage: "", etat: "" };
          item.meta.port_usage = item.meta.port_usage || [];
          item.meta.port_usage.push(pu);
        }
        pu.etat = val;
      }
      saveLocal();
      openDeviceSheet(deviceItemId);   // la grille se recolore
      renderAll();
    });
    menu.appendChild(b);
  }
  /* Dans le dialog (top layer) : ajouté au body il serait derrière le
     modal et inerte. position:fixed = coordonnées viewport, inchangées. */
  $("#device-dialog").appendChild(menu);
  menu.style.left = Math.min(e.clientX, window.innerWidth - 130) + "px";
  menu.style.top = Math.min(e.clientY, window.innerHeight - 180) + "px";
  const close = (ev) => {
    if (!menu.contains(ev.target)) { menu.remove();
      document.removeEventListener("pointerdown", close, true); }
  };
  document.addEventListener("pointerdown", close, true);
}

function openPortEditor(item, port) {
  editingPort = { item, port };
  $("#device-trace").hidden = true;
  const f = $("#device-port-form");
  const pu = portUsageOf(item, port.name) || {};
  $("#dpf-title").textContent = `${port.name} — ${port.type}`;
  f.elements.outlet.value = pu.outlet || "";
  f.elements.vlan.value = pu.vlan || "";
  f.elements.usage.value = pu.usage || "";
  f.elements.etat.value = pu.etat || "";
  f.elements.poe_w.value = pu.poe_w ? pu.poe_w : "";
  f.hidden = false;
  f.elements.outlet.focus();
}

$("#device-port-form").addEventListener("submit", (e) => {
  e.preventDefault();
  if (!editingPort) return;
  const { item, port } = editingPort;
  const f = e.target;
  let pu = portUsageOf(item, port.name);
  if (!pu) {
    pu = { port: port.name, outlet: "", vlan: "", usage: "", etat: "" };
    item.meta.port_usage = item.meta.port_usage || [];
    item.meta.port_usage.push(pu);
  }
  pu.outlet = f.elements.outlet.value.trim();
  pu.vlan = f.elements.vlan.value.trim();
  pu.usage = f.elements.usage.value.trim();
  pu.etat = f.elements.etat.value;
  const poe = parseFloat(String(f.elements.poe_w.value).replace(",", "."));
  pu.poe_w = Number.isFinite(poe) && poe > 0 ? Math.min(poe, 100) : 0;
  renderAll();
  openDeviceSheet(deviceItemId);
});
/* Boutons de classe 802.3 : af 15,4 W · at 30 W · bt 60 W — un clic, pas de table à retenir. */
document.querySelectorAll(".poe-class").forEach((b) =>
  b.addEventListener("click", () => {
    $("#device-port-form").elements.poe_w.value = b.dataset.w;
  }));
$("#dpf-cable").addEventListener("click", (e) => {
  if (!editingPort) return;
  startCabling(e, editingPort.item, editingPort.port);
});
$("#dpf-clear").addEventListener("click", () => {
  if (!editingPort) return;
  const { item, port } = editingPort;
  item.meta.port_usage =
    (item.meta.port_usage || []).filter((p) => p.port !== port.name);
  renderAll();
  openDeviceSheet(deviceItemId);
});
$("#btn-close-device").addEventListener("click", () => $("#device-dialog").close());

/* =====================================================================
 * Trace de câble de bout en bout — le « enfin ! » du terrain : suivre
 * une liaison à travers liens et panneaux, avec baie · U · port · prise
 * à chaque saut. Un panneau de brassage est traversé (pass-through).
 * =================================================================== */

function traceFrom(itemId, portName) {
  const hops = [];
  const visited = new Set();
  let cur = { itemId, port: portName };
  const hopInfo = (id, port) => {
    const f = findItem(id);
    if (!f) return null;
    const t = typesById[f.item.type_id];
    const pu = portUsageOf(f.item, port);
    return {
      itemId: id, port,
      label: f.item.meta.hostname || `${t.vendor} ${t.model}`,
      lieu: `${f.rack.name} · U${f.item.position_u}`,
      outlet: pu?.outlet || "",
      panel: t.category === "patch-panel",
    };
  };
  hops.push({ noeud: hopInfo(cur.itemId, cur.port), lien: null });
  for (let step = 0; step < 32; step++) {
    const link = (project.logical?.links || []).find((l) => {
      if (visited.has(l.id)) return false;
      return (l.from.equipment_id === cur.itemId && l.from.port === cur.port) ||
             (l.to.equipment_id === cur.itemId && l.to.port === cur.port);
    });
    if (!link) break;
    visited.add(link.id);
    const other = link.from.equipment_id === cur.itemId ? link.to : link.from;
    const info = hopInfo(other.equipment_id, other.port);
    if (!info) break;
    hops.push({ noeud: info, lien: link });
    /* Panneau : on ressort de l'autre face sur le même port et on
       continue ; sinon l'équipement est un terminus. */
    cur = { itemId: other.equipment_id, port: other.port };
    if (!info.panel) break;
  }
  return hops;
}

function showTrace(itemId, portName) {
  const hops = traceFrom(itemId, portName);
  const box = $("#device-trace");
  if (hops.length < 2) {
    box.innerHTML = '<div class="dialog-hint">Aucun lien ne part de ce port — ' +
      "créez-en un (vue Logique, ou « Démarrer une connexion »).</div>";
    box.hidden = false;
    return;
  }
  box.innerHTML = '<div class="trace-title">Trace du câble</div>' +
    hops.map((h, i) => {
      const badge = h.lien
        ? `<span class="trace-link">${esc(h.lien.label || h.lien.kind)}` +
          (h.lien.media ? ` · ${esc(h.lien.media)}` : "") + "</span>"
        : "";
      return (i ? `<div class="trace-arrow">↓ ${badge}</div>` : "") +
        `<div class="trace-hop${h.noeud.panel ? " trace-panel" : ""}">` +
        `<b>${esc(h.noeud.label)}</b> · ${esc(h.noeud.port)}` +
        `<span class="trace-lieu">${esc(h.noeud.lieu)}` +
        (h.noeud.outlet ? ` · prise ${esc(h.noeud.outlet)}` : "") + "</span></div>";
    }).join("");
  box.hidden = false;
  /* La chaîne s'illumine dans la baie pendant quelques secondes. */
  const ids = new Set(hops.map((h) => h.noeud.itemId));
  for (const g of document.querySelectorAll("g.rack-item"))
    g.classList.add(ids.has(g.dataset.itemId) ? "conn-lit" : "conn-dim");
  setTimeout(clearHighlight, 6000);
}

$("#dpf-trace").addEventListener("click", () => {
  if (editingPort)
    showTrace(deviceItemId, editingPort.port.name);
});

/* =====================================================================
 * Astuces rotatives (barre d'état) — les gestes qui ne se voient pas
 * =================================================================== */

const TIPS = [
  "Astuce : double-cliquez un équipement — sa fiche (ports, VLANs, trace de câble).",
  "Astuce : clic droit sur un équipement — dupliquer, connecter, supprimer.",
  "Astuce : cliquez un U libre pour ajouter sans glisser.",
  "Astuce : survolez un port pour voir VLAN, prise et usage.",
  "Astuce : cliquez le nom d'une baie pour la renommer ou changer sa hauteur.",
  "Astuce : Ctrl+K cherche un hostname, un VLAN ou un modèle.",
  "Astuce : Ctrl+Z annule — tout est réversible.",
  "Astuce : survolez un équipement câblé, ses voisins reliés restent allumés.",
];
let tipIndex = Math.floor(Date.now() / 60000) % TIPS.length;
function showNextTip() {
  tipIndex = (tipIndex + 1) % TIPS.length;
  $("#tip-text").textContent = TIPS[tipIndex];
}
$("#tip-text").textContent = TIPS[tipIndex];
$("#tip-text").addEventListener("click", showNextTip);
setInterval(showNextTip, 20000);

/* =====================================================================
 * Recherche globale (Ctrl+K) : hostname, VLAN, modèle → sélection
 * =================================================================== */

function closeSearch() {
  document.getElementById("search-overlay")?.remove();
}

function searchMatches(q) {
  const out = [];
  for (const rack of project.racks)
    for (const item of rack.items) {
      const t = typesById[item.type_id];
      if (!t) continue;
      const hay = (`${item.meta.hostname} ${t.vendor} ${t.model} ` +
        `${item.meta.vlan} ${item.meta.serial} ${item.meta.mgmt_ip} ` +
        `${item.meta.asset}`).toLowerCase();
      if (hay.includes(q))
        out.push({ item, rack, t,
          label: item.meta.hostname || `${t.vendor} ${t.model}`,
          sub: `${rack.name} · U${item.position_u}` +
               (item.meta.vlan ? ` · VLAN ${item.meta.vlan}` : "") });
    }
  return out.slice(0, 12);
}

function openSearch() {
  closeSearch();
  const ov = document.createElement("div");
  ov.id = "search-overlay";
  ov.innerHTML = '<div class="search-box">' +
    '<input type="search" placeholder="Hostname, VLAN, modèle… (Échap pour fermer)">' +
    '<div class="search-results"></div></div>';
  document.body.appendChild(ov);
  const input = ov.querySelector("input");
  const list = ov.querySelector(".search-results");
  const fill = () => {
    const q = input.value.trim().toLowerCase();
    list.innerHTML = "";
    if (!q) return;
    const matches = searchMatches(q);
    if (!matches.length) {
      list.innerHTML = '<div class="search-empty">Aucun équipement ne correspond.</div>';
      return;
    }
    for (const m of matches) {
      const row = document.createElement("div");
      row.className = "search-row";
      row.innerHTML =
        `<span class="role-dot" style="background:${m.t.color}"></span>` +
        `<span class="sr-label">${esc(m.label)}</span>` +
        `<span class="sr-sub">${esc(m.sub)}</span>`;
      row.addEventListener("click", () => {
        closeSearch();
        if (viewMode !== "physical") setView("physical");
        selectItem(m.item.id);
        document.querySelector(`g[data-item-id="${m.item.id}"]`)
          ?.scrollIntoView({ block: "center", behavior: "smooth" });
      });
      list.appendChild(row);
    }
  };
  input.addEventListener("input", fill);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") list.querySelector(".search-row")?.click();
  });
  ov.addEventListener("pointerdown", (e) => { if (e.target === ov) closeSearch(); });
  input.focus();
}

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    openSearch();
  }
  if (e.key === "Escape") closeSearch();
});

/* =====================================================================
 * Édition de baie (clic sur son nom) : nom, hauteur, localisation
 * =================================================================== */

function closeRackMenu() {
  document.getElementById("rack-menu")?.remove();
}

/* Purge des références d'une baie qui part (liens logiques, positions,
   sélection) — jamais de liens orphelins dans le projet. */
function _purgeRackRefs(rack) {
  const ids = new Set(rack.items.map((i) => i.id));
  project.logical.links = (project.logical.links || []).filter((l) =>
    !ids.has(l.from.equipment_id) && !ids.has(l.to.equipment_id));
  for (const id of ids) {
    if (project.logical.positions) delete project.logical.positions[id];
    if (selectedItemId === id) { selectedItemId = null; closeInspector(); }
  }
}

function openRackMenu(e, rack) {
  e.stopPropagation();
  closeRackMenu();
  closeItemMenu();
  closeSlotPopover();
  const maxUsed = Math.max(0, ...rack.items.map((i) =>
    i.position_u + (typesById[i.type_id]?.u_height || 1) - 1));
  const menu = document.createElement("div");
  menu.id = "rack-menu";
  menu.style.position = "fixed";
  menu.style.zIndex = "70";
  menu.innerHTML =
    '<div class="menu-title">Baie</div>' +
    '<label class="rk-field">Nom<input name="name" value="' + esc(rack.name) + '"></label>' +
    '<label class="rk-field">Hauteur (U)<input name="u" type="number" min="6" max="60" value="' + rack.u_height + '"></label>' +
    '<label class="rk-field">Localisation<input name="loc" value="' + esc(rack.location || "") + '"></label>' +
    '<div class="rk-actions"><button class="rk-apply">Appliquer</button>' +
    '<button class="rk-add-right" title="Nouvelle baie vide, posée juste à droite de celle-ci">+ Baie à droite</button>' +
    '<button class="rk-duplicate">Dupliquer</button>' +
    '<button class="rk-empty menu-danger">Vider</button>' +
    '<button class="rk-delete menu-danger">Supprimer</button></div>' +
    '<div class="rk-msg"></div>';
  document.body.appendChild(menu);
  const pad = 6;
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.max(pad, Math.min(e.clientX - r.width / 2,
    window.innerWidth - r.width - pad)) + "px";
  menu.style.top = Math.max(pad, Math.min(e.clientY + 10,
    window.innerHeight - r.height - pad)) + "px";
  const msg = menu.querySelector(".rk-msg");
  menu.querySelector(".rk-apply").addEventListener("click", () => {
    const u = parseInt(menu.querySelector('input[name="u"]').value, 10);
    if (!(u >= 6 && u <= 60)) { msg.textContent = "Hauteur entre 6 et 60 U."; return; }
    if (u < maxUsed) {
      msg.textContent = `Impossible : un équipement occupe le U${maxUsed}.`;
      return;
    }
    rack.name = menu.querySelector('input[name="name"]').value.trim() || rack.name;
    rack.u_height = u;
    rack.location = menu.querySelector('input[name="loc"]').value.trim();
    closeRackMenu();
    renderAll();
  });
  menu.querySelector(".rk-add-right").addEventListener("click", () => {
    closeRackMenu();
    addRack(rack);
  });
  menu.querySelector(".rk-duplicate").addEventListener("click", () => {
    const copy = JSON.parse(JSON.stringify(rack));
    copy.id = "rack-" + Date.now().toString(36);
    copy.name = rack.name + " (copie)";
    // Les équipements copiés prennent de nouveaux ids (liens/brassage
    // restent sur les originaux — pas de doublons fantômes).
    copy.items.forEach((it, k) => {
      it.id = "eq-" + Date.now().toString(36) + "-" + k;
      it.meta.hostname = it.meta.hostname ? it.meta.hostname + "-copie" : "";
    });
    project.racks.splice(project.racks.indexOf(rack) + 1, 0, copy);
    closeRackMenu();
    renderAll();
  });
  menu.querySelector(".rk-empty").addEventListener("click", async () => {
    if (!rack.items.length) { msg.textContent = "La baie est déjà vide."; return; }
    closeRackMenu();
    if (!await askConfirm(`Vider « ${rack.name} » ?`,
      `Ses ${rack.items.length} équipements, leurs liens et leur brassage `
      + "seront retirés du projet (Ctrl+Z pour annuler).")) return;
    _purgeRackRefs(rack);
    rack.items = [];
    renderAll();
  });
  menu.querySelector(".rk-delete").addEventListener("click", async () => {
    if (project.racks.length <= 1) {
      msg.textContent = "Le projet garde au moins une baie (videz-la plutôt).";
      return;
    }
    const n = rack.items.length;
    closeRackMenu();
    if (n && !await askConfirm(`Supprimer « ${rack.name} » ?`,
      `Ses ${n} équipements, leurs liens et leur brassage partent avec `
      + "(Ctrl+Z pour annuler).")) return;
    _purgeRackRefs(rack);
    project.racks = project.racks.filter((r2) => r2 !== rack);
    renderAll();
  });
  menu.querySelector('input[name="name"]').focus();
}

document.addEventListener("pointerdown", (e) => {
  const menu = document.getElementById("rack-menu");
  if (menu && !menu.contains(e.target)) closeRackMenu();
}, true);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeRackMenu();
});

/* =====================================================================
 * Menu contextuel d'équipement (clic droit) : dupliquer, connecter, supprimer
 * =================================================================== */

/* U libre le plus proche de la position d'origine (pour la duplication). */
function nearestFreeSlot(rack, uHeight, fromU) {
  let best = null;
  for (let u = 1; u <= rack.u_height - uHeight + 1; u++) {
    if (!canPlace(rack, u, uHeight)) continue;
    if (best === null || Math.abs(u - fromU) < Math.abs(best - fromU)) best = u;
  }
  return best;
}

function duplicateItem(rack, item) {
  const t = typesById[item.type_id];
  const u = nearestFreeSlot(rack, t.u_height, item.position_u);
  if (u === null) {
    renderStatus('<span class="stat-err">Duplication impossible : plus de place dans la baie</span>');
    return;
  }
  const meta = JSON.parse(JSON.stringify(item.meta));
  if (meta.hostname) meta.hostname += " (copie)";
  rack.items.push({ id: nextItemId(), type_id: item.type_id,
                    position_u: u, face: item.face || "front", meta });
  renderAll();
}

function closeItemMenu() {
  document.getElementById("item-menu")?.remove();
}

function openItemMenu(e, rack, item) {
  e.preventDefault();
  e.stopPropagation();
  closeItemMenu();
  closeSlotPopover();
  const t = typesById[item.type_id];
  const name = item.meta.hostname || `${t.vendor} ${t.model}`;
  const menu = document.createElement("div");
  menu.id = "item-menu";
  menu.style.position = "fixed";
  menu.style.zIndex = "70";
  menu.innerHTML = `<div class="menu-title">${esc(name)}</div>`;
  const actions = [
    ["Fiche de l'équipement", () => openDeviceSheet(item.id)],
    ["Dupliquer", () => duplicateItem(rack, item)],
    ["Démarrer une connexion", () => {
      selectItem(item.id);
      $("#btn-start-connection").click();
    }],
    ["Ouvrir les métadonnées", () => selectItem(item.id)],
    [(item.face || "front") === "rear"
      ? "Monter en façade (avant)" : "Monter à l'arrière de la baie",
     () => {
       item.face = (item.face || "front") === "rear" ? "front" : "rear";
       renderAll();
       renderStatus(item.face === "rear"
         ? "Monté à l'arrière — visible en vue arrière, de dos en vue avant"
         : "Monté en façade — visible en vue avant, de dos en vue arrière");
     }],
    ["Supprimer", () => {
      rack.items = rack.items.filter((i) => i.id !== item.id);
      if (selectedItemId === item.id) { selectedItemId = null; closeInspector(); }
      renderAll();
    }, "danger"],
  ];
  for (const [label, fn, cls] of actions) {
    const row = document.createElement("div");
    row.className = "menu-item" + (cls ? " menu-" + cls : "");
    row.textContent = label;
    row.addEventListener("click", () => { closeItemMenu(); fn(); });
    menu.appendChild(row);
  }
  document.body.appendChild(menu);
  const pad = 6;
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.max(pad, Math.min(e.clientX,
    window.innerWidth - r.width - pad)) + "px";
  menu.style.top = Math.max(pad, Math.min(e.clientY,
    window.innerHeight - r.height - pad)) + "px";
}

document.addEventListener("pointerdown", (e) => {
  const menu = document.getElementById("item-menu");
  if (menu && !menu.contains(e.target)) closeItemMenu();
}, true);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeItemMenu();
});

/* =====================================================================
 * Popover d'ajout rapide sur slot libre (esprit PATCHBOX : clic → choisir)
 * =================================================================== */

function closeSlotPopover() {
  document.getElementById("slot-popover")?.remove();
}

function openSlotPopover(evt, rack, u) {
  closeSlotPopover();
  const pop = document.createElement("div");
  pop.id = "slot-popover";
  pop.innerHTML =
    `<div class="pop-title">${rack.name} — U${u}</div>` +
    `<input type="search" placeholder="Filtrer (modèle, marque…)" class="pop-filter">` +
    `<div class="pop-list"></div><div class="pop-msg"></div>`;
  /* Géométrie posée en inline : le popover ne dépend pas d'un état de
     cache CSS pour être utilisable. */
  pop.style.position = "fixed";
  pop.style.width = "280px";
  pop.style.zIndex = "70";
  document.body.appendChild(pop);

  const list = pop.querySelector(".pop-list");
  const msg = pop.querySelector(".pop-msg");
  const filterInput = pop.querySelector(".pop-filter");
  const fill = (f) => {
    list.innerHTML = "";
    const q = (f || "").toLowerCase();
    for (const t of allTypes()) {
      if (q && !`${t.vendor} ${t.model}`.toLowerCase().includes(q)) continue;
      const fits = canPlace(rack, u, t.u_height);
      const row = document.createElement("div");
      row.className = "pop-item" + (fits ? "" : " pop-item-off");
      row.innerHTML =
        `<span class="role-dot" style="background:${t.color}"></span>` +
        `<span class="pop-name">${esc(t.vendor)} ${esc(t.model)}</span>` +
        `<span class="pop-uh">${t.u_height}U</span>`;
      row.addEventListener("click", () => {
        if (!fits) {
          msg.textContent = `Ne rentre pas en U${u} (${t.u_height}U, collision ou bord de baie).`;
          return;
        }
        rack.items.push({
          id: nextItemId(), type_id: t.id, position_u: u, face: rackFace,
          meta: { hostname: "", role: t.category, vlan: "", wall_outlet: "",
                  port_usage: [], serial: "", notes: "" },
        });
        closeSlotPopover();
        renderAll();
      });
      list.appendChild(row);
    }
    if (!list.children.length)
      list.innerHTML = '<div class="pop-empty">Aucun modèle ne correspond.</div>';
  };
  fill("");
  /* Position près du clic, rabattue aux bords (mesurée une fois rempli). */
  const pad = 8;
  const rect = pop.getBoundingClientRect();
  pop.style.left = Math.max(pad, Math.min(evt.clientX + pad,
    window.innerWidth - rect.width - pad)) + "px";
  pop.style.top = Math.max(pad, Math.min(evt.clientY + pad,
    window.innerHeight - rect.height - pad)) + "px";
  filterInput.addEventListener("input", () => fill(filterInput.value));
  filterInput.focus();
}

/* Fermeture du popover : clic ailleurs ou Échap. */
document.addEventListener("pointerdown", (e) => {
  const pop = document.getElementById("slot-popover");
  if (pop && !pop.contains(e.target)) closeSlotPopover();
}, true);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSlotPopover();
});

function renderAll() {
  if (viewMode === "logical") { renderLogical(); return; }
  if (viewMode === "diagram") { renderDiagram(); return; }
  if (viewMode === "plan") { renderPlan(); return; }
  ensureProjectImages();
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  for (const rack of project.racks) canvas.appendChild(renderRackSVG(rack));
  /* Baie fantôme : le vide à droite invite à construire la suivante. */
  const ghost = document.createElement("div");
  ghost.id = "ghost-rack";
  ghost.innerHTML = '<div class="ghost-plus">+</div><div>Baie</div>';
  ghost.title = "Ajouter une baie";
  ghost.addEventListener("click", () => $("#btn-add-rack").click());
  canvas.appendChild(ghost);
  requestAnimationFrame(updateMinimap);
  requestAnimationFrame(renderCables);
  renderOnboarding();
  renderStatus();
  saveLocal();
}

/* =====================================================================
 * Vue câblage (esprit PATCHBOX) : les cordons de brassage dessinés
 * par-dessus l'élévation. Chaque lien part du bord de l'équipement,
 * descend dans la « goulotte » entre les baies et rejoint sa cible —
 * couleur = type de câble (les vraies couleurs de cordons : monomode
 * jaune, OM4 aqua, cuivre bleu, DAC gris). Survol = détail du lien.
 * =================================================================== */
const CABLE_COLORS = {
  "cuivre-cat6a": "#2563eb", "cuivre-cat6": "#60a5fa",
  "fibre-om4": "#22d3ee", "fibre-os2": "#eab308",
  "fibre": "#22d3ee", "dac": "#64748b",
};
let cablesVisible = localStorage.getItem("rfp-cables-visibles") === "1";

function renderCables() {
  document.getElementById("cables-overlay")?.remove();
  if (!cablesVisible || viewMode !== "physical") return;
  const canvas = $("#canvas");
  const links = project.logical?.links || [];
  if (!links.length) return;
  const cRect = canvas.getBoundingClientRect();
  const overlay = svgEl("svg", { id: "cables-overlay" });
  /* Le canvas est zoomé en CSS : les rects mesurés sont en pixels
     écran — on redivise pour dessiner dans le repère du canvas. */
  const z = canvasZoom;
  overlay.setAttribute("width", canvas.scrollWidth);
  overlay.setAttribute("height", canvas.scrollHeight);
  let n = 0;
  for (const link of links) {
    const gFrom = canvas.querySelector(
      `[data-item-id="${CSS.escape(link.from.equipment_id)}"]`);
    const gTo = canvas.querySelector(
      `[data-item-id="${CSS.escape(link.to.equipment_id)}"]`);
    if (!gFrom || !gTo) continue;
    const a = gFrom.getBoundingClientRect(), b = gTo.getBoundingClientRect();
    const aCx = (a.left + a.right) / 2, bCx = (b.left + b.right) / 2;
    const y1 = (a.top + a.height / 2 - cRect.top) / z;
    const y2 = (b.top + b.height / 2 - cRect.top) / z;
    const sag = 26 + (n % 5) * 9;   // cordons étagés dans la goulotte
    const sameBay = Math.abs(aCx - bCx) < a.width / 2;
    let d;
    if (sameBay) {
      /* Même baie : le cordon sort à DROITE, longe la goulotte du rail
         et revient — jamais en diagonale à travers les équipements. */
      const x1 = (a.right - cRect.left) / z;
      const x2 = (b.right - cRect.left) / z;
      const g = Math.max(x1, x2) + sag;
      d = `M ${x1} ${y1} C ${g} ${y1}, ${g} ${y2}, ${x2} ${y2}`;
    } else {
      /* Baies différentes : sortie côté voisin, traversée de l'allée. */
      const toRight = bCx >= aCx;
      const x1 = ((toRight ? a.right : a.left) - cRect.left) / z;
      const x2 = ((toRight ? b.left : b.right) - cRect.left) / z;
      const dx = toRight ? sag : -sag;
      d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
    }
    const color = CABLE_COLORS[link.media] || "#94a3b8";
    /* Halo sombre dessous : le cordon se lit sur les photos claires. */
    const halo = svgEl("path", { d, fill: "none", stroke: "rgba(0,0,0,.45)",
      "stroke-width": 4.5, "stroke-linecap": "round" });
    const path = svgEl("path", { d, fill: "none", stroke: color,
      "stroke-width": 2.2, "stroke-linecap": "round", class: "cable-path" });
    const fi = findItem(link.from.equipment_id), ti = findItem(link.to.equipment_id);
    const tip = `${fi?.item.meta.hostname || link.from.equipment_id}` +
      (link.from.port ? ` · ${link.from.port}` : "") + "  ⟶  " +
      `${ti?.item.meta.hostname || link.to.equipment_id}` +
      (link.to.port ? ` · ${link.to.port}` : "") +
      (link.media ? `  (${link.media})` : "") +
      (link.vlans?.length ? `  VLAN ${link.vlans.join(",")}` : "");
    path.addEventListener("mousemove", (e) => showTip(esc(tip), e));
    path.addEventListener("mouseleave", hideTip);
    path.addEventListener("click", () => openLinkDialog(link));
    overlay.appendChild(halo);
    overlay.appendChild(path);
    n++;
  }
  canvas.appendChild(overlay);
}

/* Carte de prise en main : visible tant que les baies sont vides,
 * disparaît au premier équipement posé (esprit PATCHBOX, en mieux). */
function renderOnboarding() {
  document.getElementById("onboard-card")?.remove();
  const empty = project.racks.every((r) => r.items.length === 0);
  if (!empty) return;
  const card = document.createElement("div");
  card.id = "onboard-card";
  card.innerHTML =
    "<h3>Votre première baie en 30 secondes</h3>" +
    '<div class="onboard-step"><span class="num">1</span><span class="txt">' +
    "<b>Glissez</b> un équipement depuis la palette de gauche… ou <b>cliquez un U libre</b> dans la baie.</span></div>" +
    '<div class="onboard-step"><span class="num">2</span><span class="txt">' +
    "Cliquez l'équipement posé pour remplir <b>hostname, VLAN, prise, brassage</b>.</span></div>" +
    '<div class="onboard-step"><span class="num">3</span><span class="txt">' +
    "Survolez un port pour voir sa config, puis exportez le <b>Dossier</b> complet.</span></div>";
  $("#canvas-wrap").appendChild(card);
}

function renderStatus(extra) {
  const parts = project.racks.map((r) => {
    const st = rackStats(r);
    return `${r.name} : <span class="stat-accent">${st.used}/${r.u_height}U</span> · ${st.power} W`;
  });
  $("#status-text").innerHTML =
    (extra ? extra + " — " : "") + parts.join(" | ");
}

/* =====================================================================
 * Palette
 * =================================================================== */

/* Catégories repliées (persistées) — la palette de 90+ modèles se
 * balaye par groupes, pas en liste infinie. */
let collapsedCats;
try { collapsedCats = new Set(JSON.parse(localStorage.getItem("rfp-collapsed") || "[]")); }
catch { collapsedCats = new Set(); }

function renderPalette(filter) {
  const wrap = $("#palette-groups");
  wrap.innerHTML = "";
  const f = (filter || "").toLowerCase();
  for (const [cat, label] of Object.entries(CATEGORY_LABELS)) {
    const types = allTypes().filter((t) =>
      t.category === cat &&
      (!f || `${t.vendor} ${t.model}`.toLowerCase().includes(f)));
    if (!types.length) continue;
    /* Un filtre actif déplie tout : on cherche, on doit voir. */
    const collapsed = !f && collapsedCats.has(cat);
    const title = document.createElement("div");
    title.className = "palette-group-title" + (collapsed ? " collapsed" : "");
    title.innerHTML =
      `<span class="role-dot" style="background:${catalog.role_colors[cat] || "#666"}"></span>` +
      `${label} <span class="group-count">${types.length}</span>` +
      `<span class="chevron">${collapsed ? "▸" : "▾"}</span>`;
    title.addEventListener("click", () => {
      if (collapsedCats.has(cat)) collapsedCats.delete(cat);
      else collapsedCats.add(cat);
      localStorage.setItem("rfp-collapsed", JSON.stringify([...collapsedCats]));
      renderPalette($("#palette-filter").value);
    });
    wrap.appendChild(title);
    if (collapsed) continue;
    for (const t of types) {
      const card = document.createElement("div");
      card.className = "palette-item";
      card.style.borderLeftColor = t.color;
      card.innerHTML = `<span class="uh">${t.u_height}U</span>` +
        `<div class="vendor">${t.vendor}</div><div class="model">${t.model}</div>`;
      card.addEventListener("pointerdown", (e) => startPaletteDrag(e, t));
      wrap.appendChild(card);
    }
  }
}

/* =====================================================================
 * Drag-and-drop — pointer events + fantôme snappé au U
 * =================================================================== */

let _lastClickItem = null;
let _lastClickAt = 0;

/* Touche Suppr : retire l'équipement sélectionné (vue physique), avec
   purge de ses liens — hors champs de saisie. */
document.addEventListener("keydown", (e) => {
  if (e.key !== "Delete" || viewMode !== "physical" || !selectedItemId) return;
  const tag = (document.activeElement?.tagName || "").toLowerCase();
  if (["input", "textarea", "select"].includes(tag)) return;
  for (const rack of project.racks) {
    const item = rack.items.find((i) => i.id === selectedItemId);
    if (!item) continue;
    project.logical.links = (project.logical.links || []).filter((l) =>
      l.from.equipment_id !== item.id && l.to.equipment_id !== item.id);
    if (project.logical.positions) delete project.logical.positions[item.id];
    rack.items = rack.items.filter((i) => i !== item);
    selectedItemId = null;
    closeInspector();
    renderAll();
    renderStatus("Équipement supprimé — Ctrl+Z pour annuler");
    return;
  }
});

function startPaletteDrag(e, type) {
  e.preventDefault();
  drag = { type, itemId: null, fromRackId: null };
  document.body.style.cursor = "grabbing";
}

function startItemDrag(e, rack, item) {
  e.preventDefault();
  e.stopPropagation();
  /* La sélection se fait au pointerup si l'item n'a pas bougé. */
  drag = { type: typesById[item.type_id], itemId: item.id,
           fromRackId: rack.id, moved: false, startX: e.clientX, startY: e.clientY };
  document.body.style.cursor = "grabbing";
}

/* Baie + U sous le curseur (null si hors zone U). */
function hitTest(e) {
  for (const svg of $("#canvas").querySelectorAll("svg")) {
    const r = svg.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right ||
        e.clientY < r.top || e.clientY > r.bottom) continue;
    const rack = project.racks.find((rk) => rk.id === svg.dataset.rackId);
    const y = (e.clientY - r.top) / canvasZoom;  // écran -> px logiques
    const zoneY = HEADER_H + FRAME_PAD;
    if (y < zoneY || y > zoneY + rack.u_height * U_PX) return null;
    return { svg, rack, u: yToU(rack, y, drag.type.u_height) };
  }
  return null;
}

function clearGhost() {
  document.querySelectorAll(".drag-ghost").forEach((g) => g.remove());
}

document.addEventListener("pointermove", (e) => {
  if (!drag) return;
  if (drag.itemId &&
      Math.abs(e.clientX - drag.startX) + Math.abs(e.clientY - drag.startY) > 4)
    drag.moved = true;
  clearGhost();
  const hit = hitTest(e);
  if (!hit) return;
  const { rack, svg, u } = hit;
  const ok = canPlace(rack, u, drag.type.u_height, drag.itemId);
  /* Fantôme : cadre cyan si posable, rouge barré si collision (= refus). */
  const topU = rack.desc_units ? u : u + drag.type.u_height - 1;
  const y = uToY(rack, topU);
  const g = svgEl("g", { class: "drag-ghost" });
  g.appendChild(svgEl("rect", {
    x: FRAME_PAD + RAIL_W, y: y + 1, width: RACK_W,
    height: drag.type.u_height * U_PX - 2, rx: 2,
    fill: ok ? "rgba(249,115,22,.12)" : "rgba(248,113,113,.15)",
    stroke: ok ? C.accent : C.danger, "stroke-width": 1.5,
    "stroke-dasharray": ok ? "" : "5,4",
  }));
  g.appendChild(svgEl("text", {
    x: FRAME_PAD + RAIL_W + RACK_W / 2, y: y + (drag.type.u_height * U_PX) / 2 + 4,
    "text-anchor": "middle", "font-size": 11, "font-family": "monospace",
    fill: ok ? C.accent : C.danger,
  }, ok ? `U${u}` : "collision"));
  svg.appendChild(g);
});

document.addEventListener("pointerup", (e) => {
  if (!drag) return;
  clearGhost();
  document.body.style.cursor = "";
  const hit = hitTest(e);
  const d = drag; drag = null;

  /* Mode câblage : le clic d'arrivée crée le lien (dialogue pré-rempli). */
  if (connectFrom && d.itemId && !d.moved && d.itemId !== connectFrom) {
    const from = connectFrom;
    cancelConnection();
    openLinkDialog(null, { from, to: d.itemId });
    return;
  }

  /* Simple clic sur un item posé (pas de mouvement) = inspecteur.
     Deux clics rapprochés = fiche équipement — détection manuelle : le
     re-rendu de la sélection détruit l'élément, l'événement dblclick
     natif ne peut jamais aboutir. */
  if (d.itemId && !d.moved) {
    if (_lastClickItem === d.itemId && Date.now() - _lastClickAt < 450) {
      _lastClickItem = null;
      openDeviceSheet(d.itemId);
    } else {
      _lastClickItem = d.itemId;
      _lastClickAt = Date.now();
      selectItem(d.itemId);
    }
    return;
  }

  if (!hit) { renderAll(); return; }
  const { rack, u } = hit;
  let shareX = null;
  if (!canPlace(rack, u, d.type.u_height, d.itemId)) {
    /* U occupé : peut-être une cohabitation côte à côte (compacts). */
    shareX = tryShare(rack, u, d.type, d.itemId);
    if (shareX == null) {
      renderStatus('<span class="stat-err">Collision — dépôt refusé'
        + (d.type.width_mm ? " (plus assez de place dans le U)" : "")
        + '</span>');
      renderAll();
      return;
    }
  }
  if (d.itemId) {
    /* Déplacement (y compris entre baies). */
    const fromRack = project.racks.find((r) => r.id === d.fromRackId);
    const idx = fromRack.items.findIndex((i) => i.id === d.itemId);
    const [item] = fromRack.items.splice(idx, 1);
    item.position_u = u;
    item.position_x_mm = shareX;           // null = redevient seul/centré
    rack.items.push(item);
  } else {
    /* Nouveau depuis la palette. */
    rack.items.push({
      id: nextItemId(), type_id: d.type.id, position_u: u, face: rackFace,
      position_x_mm: shareX,
      meta: { hostname: "", role: d.type.category, vlan: "", wall_outlet: "",
              port_usage: [], serial: "", notes: "" },
    });
  }
  if (shareX != null)
    renderStatus(`Posé côte à côte — à ${Math.round(shareX)} mm du bord gauche du U${u}`);
  renderAll();
});

/* =====================================================================
 * Inspecteur (métadonnées)
 * =================================================================== */

function findItem(id) {
  for (const r of project.racks) {
    const it = r.items.find((i) => i.id === id);
    if (it) return { rack: r, item: it };
  }
  return null;
}

function selectItem(id) {
  selectedItemId = id;
  const found = findItem(id);
  if (!found) return;
  const { rack, item } = found;
  const t = typesById[item.type_id];
  $("#inspector").classList.remove("hidden");
  $("#inspector-type").textContent =
    `${t.vendor} ${t.model} — ${t.u_height}U — ${rack.name} U${item.position_u}`;
  const f = $("#inspector-form");
  for (const k of ["hostname", "role", "vlan", "wall_outlet", "mgmt_ip",
                   "serial", "asset", "notes"])
    f.elements[k].value = item.meta[k] || "";
  renderPortRows(item);
  renderAll();
}

function renderPortRows(item) {
  const wrap = $("#port-usage-rows");
  wrap.innerHTML = "";
  item.meta.port_usage.forEach((pu, i) => {
    const row = document.createElement("div");
    row.className = "pu-row";
    row.innerHTML =
      `<input placeholder="Port" value="${pu.port || ""}" data-k="port">` +
      `<input placeholder="Prise" value="${pu.outlet || ""}" data-k="outlet">` +
      `<input placeholder="VLAN" value="${pu.vlan || ""}" data-k="vlan">` +
      `<input placeholder="Usage" value="${pu.usage || ""}" data-k="usage">` +
      `<button type="button" title="Supprimer la ligne">×</button>`;
    row.querySelectorAll("input").forEach((inp) =>
      inp.addEventListener("input", () => { pu[inp.dataset.k] = inp.value; saveLocal(); }));
    row.querySelector("button").addEventListener("click", () => {
      item.meta.port_usage.splice(i, 1); renderPortRows(item); saveLocal();
    });
    wrap.appendChild(row);
  });
}

$("#inspector-form").addEventListener("input", (e) => {
  const found = findItem(selectedItemId);
  if (!found || !e.target.name) return;
  found.item.meta[e.target.name] = e.target.value;
  if (e.target.name === "hostname") renderAll();  // le label sur la faceplate
  saveLocal();
});

$("#btn-add-port").addEventListener("click", () => {
  const found = findItem(selectedItemId);
  if (!found) return;
  found.item.meta.port_usage.push({ port: "", outlet: "", vlan: "", usage: "" });
  renderPortRows(found.item);
});

$("#btn-delete-item").addEventListener("click", () => {
  const found = findItem(selectedItemId);
  if (!found) return;
  found.rack.items = found.rack.items.filter((i) => i.id !== selectedItemId);
  closeInspector();
  renderAll();
});

function closeInspector() {
  selectedItemId = null;
  $("#inspector").classList.add("hidden");
}
$("#btn-close-inspector").addEventListener("click", () => { closeInspector(); renderAll(); });

/* =====================================================================
 * Exports / import — le backend valide toujours avant de générer
 * =================================================================== */

function currentProject() {
  project.name = $("#project-name").value.trim() || "Sans nom";
  return project;
}

/* « Enregistrer sous » — comme draw.io / Visio : la vraie boîte Windows
 * quand le navigateur la propose (Chromium), sinon téléchargement
 * classique. L'utilisateur choisit lui-même le dossier et le nom. */
const SAVE_TYPES = {
  ".json":   { description: "Projet RackForgePrime", accept: { "application/json": [".json"] } },
  ".zip":    { description: "Archive ZIP",           accept: { "application/zip": [".zip"] } },
  ".pdf":    { description: "Document PDF",          accept: { "application/pdf": [".pdf"] } },
  ".svg":    { description: "Image SVG",             accept: { "image/svg+xml": [".svg"] } },
  ".png":    { description: "Image PNG",             accept: { "image/png": [".png"] } },
  ".drawio": { description: "Schéma draw.io",        accept: { "application/xml": [".drawio"] } },
};
async function saveBlob(blob, filename) {
  const ext = "." + filename.split(".").pop().toLowerCase();
  if (window.showSaveFilePicker && SAVE_TYPES[ext]) {
    try {
      const handle = await showSaveFilePicker({
        suggestedName: filename, types: [SAVE_TYPES[ext]],
      });
      const w = await handle.createWritable();
      await w.write(blob);
      await w.close();
      renderStatus(`Enregistré ✓ ${handle.name}`);
      return true;
    } catch (err) {
      if (err.name === "AbortError") {          // l'utilisateur a annulé
        renderStatus("Enregistrement annulé");
        return false;
      }
      /* API refusée (iframe, politique…) : téléchargement classique. */
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
  return true;
}

async function fetchExportBlob(url) {
  const res = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    renderStatus(`<span class="stat-err">Export refusé : ${JSON.stringify(err.detail)}</span>`);
    return null;
  }
  return res.blob();
}
async function postForBlob(url, filename) {
  const blob = await fetchExportBlob(url);
  if (blob) await saveBlob(blob, filename);
}

/* Les exports suivent la vue active ET le thème affiché : ce que tu
 * vois est ce que tu livres. */
function viewSuffix() {
  if (viewMode === "physical") return rackFace === "rear" ? "-arriere" : "";
  if (viewMode === "logical") return "-logique" + (logicalRack ? "-" + logicalRack : "");
  return { diagram: "-diagramme", plan: "-plan" }[viewMode] || "";
}
function exportQuery(view) {
  const q = new URLSearchParams();
  const v = view ||
    ({ logical: "logical", diagram: "diagram", plan: "plan" }[viewMode] || "physical");
  q.set("view", v);
  /* Plan d'étage : la salle affichée est celle exportée. */
  if (v === "plan" && planNav.roomId) q.set("room", planNav.roomId);
  q.set("theme", theme);
  q.set("rendu", renderMode);
  /* Ce que tu vois est ce que tu livres : l'élévation exportée est celle
     de la face regardée. */
  if (v === "physical") q.set("face", rackFace);
  if (v === "logical" && logicalRack) q.set("rack", logicalRack);
  /* Les calques masqués à l'écran le sont aussi à l'export. */
  if (v === "logical" && hiddenLayers.size)
    q.set("layers", ALL_LAYERS.filter((l) => !hiddenLayers.has(l)).join(","));
  return "?" + q.toString();
}

$("#btn-export-svg").addEventListener("click", () =>
  postForBlob("/api/export/svg" + exportQuery(),
              currentProject().id + viewSuffix() + ".svg"));
$("#btn-export-pdf").addEventListener("click", () =>
  postForBlob("/api/export/pdf" + exportQuery(),
              currentProject().id + viewSuffix() + ".pdf"));
$("#btn-export-dossier").addEventListener("click", () =>
  postForBlob("/api/export/pdf" + exportQuery("dossier"),
              currentProject().id + "-dossier.pdf"));

$("#btn-export-labels").addEventListener("click", () =>
  postForBlob("/api/export/etiquettes",
              currentProject().id + "-etiquettes.pdf"));
$("#btn-export-drawio").addEventListener("click", () =>
  postForBlob("/api/export/drawio", currentProject().id + ".drawio"));
$("#btn-export-vsdx").addEventListener("click", () =>
  postForBlob("/api/export/vsdx", currentProject().id + ".vsdx"));

/* PNG : le SVG d'export rasterisé en local (à imprimer, scotcher sur la
 * baie — la demande NetBox n°1182 jamais servie). Échelle 2x. */
async function makePngBlob() {
  const res = await fetch("/api/export/svg" + exportQuery(), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) {
    renderStatus('<span class="stat-err">Export refusé — projet invalide</span>');
    return null;
  }
  const svgText = await res.text();
  const size = /viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/.exec(svgText);
  const w = size ? parseFloat(size[1]) : 1200;
  const h = size ? parseFloat(size[2]) : 900;
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(new Blob([svgText], { type: "image/svg+xml" }));
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = w * 2;
      canvas.height = h * 2;
      const ctx = canvas.getContext("2d");
      ctx.scale(2, 2);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => resolve(blob), "image/png");
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      renderStatus('<span class="stat-err">Rasterisation PNG impossible</span>');
      resolve(null);
    };
    img.src = url;
  });
}
$("#btn-export-png").addEventListener("click", async () => {
  const blob = await makePngBlob();
  if (blob) await saveBlob(blob, currentProject().id + viewSuffix() + ".png");
});
$("#btn-export-json").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(currentProject(), null, 2)],
                       { type: "application/json" });
  saveBlob(blob, currentProject().id + ".json");
});

$("#btn-import-json input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    /* Un fichier importé n'est PAS le projet de l'espace de travail
       ouvert avant : on le détache (sinon l'enregistrement automatique
       l'écrirait par-dessus l'autre — bug constaté le 03/09). */
    if (workspaceName) await saveToWorkspace();
    _installProject(data, null);
    renderStatus(`Fichier importé (${esc(file.name)}) — non rattaché à l'espace de ` +
      "travail : Projets › Enregistrer pour lui donner un nom");
  } catch {
    renderStatus('<span class="stat-err">JSON illisible</span>');
  }
  e.target.value = "";
});

/* =====================================================================
 * Vue logique — le SVG est rendu par le BACKEND (un seul moteur de
 * dessin : ce qu'on voit est exactement ce qu'on exporte), le frontend
 * pose l'interactivité par-dessus : drag des nœuds, clic sur les liens.
 * =================================================================== */

function rackQuery() {
  if (logicalRack && !project.racks.some((r) => r.id === logicalRack)) logicalRack = null;
  return logicalRack ? "&rack=" + encodeURIComponent(logicalRack) : "";
}
function syncLogicalRackSelect() {
  const sel = $("#logical-rack");
  if (!sel) return;
  if (logicalRack && !project.racks.some((r) => r.id === logicalRack)) logicalRack = null;
  sel.innerHTML = '<option value="">Toute l\'architecture</option>' +
    project.racks.map((r) => `<option value="${esc(r.id)}">Baie ${esc(r.name)}</option>`).join("");
  sel.value = logicalRack || "";
}
$("#logical-rack").addEventListener("change", (e) => {
  logicalRack = e.target.value || null;
  renderAll();
});
let _logicalFitted = false;
async function renderLogical() {
  syncLogicalRackSelect();
  const res = await fetch("/api/export/svg?view=logical&theme=" + theme
                          + layersQuery() + rackQuery(), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  const canvas = $("#canvas");
  if (!res.ok) {
    canvas.innerHTML = "";
    renderStatus('<span class="stat-err">Projet invalide — vue logique indisponible</span>');
    return;
  }
  canvas.innerHTML = await res.text();
  wireLogical(canvas.querySelector("svg"));
  /* Première ouverture d'un schéma logique plus large que l'écran :
     on l'ajuste d'office (sinon la droite est coupée et il faut
     deviner le bouton Ajuster). Ensuite le zoom de l'utilisateur prime. */
  if (!_logicalFitted) {
    _logicalFitted = true;
    const wrap = $("#canvas-wrap");
    if (wrap.scrollWidth > wrap.clientWidth + 8) $("#btn-zoom-fit").click();
  }
  if (logicalRack) {
    const rk = project.racks.find((r) => r.id === logicalRack);
    const n = canvas.querySelectorAll('g[id^="lnode-"]').length;
    const ghosts = canvas.querySelectorAll('g[id^="lnode-"][opacity]').length;
    renderStatus(`Logique — baie ${rk ? rk.name : ""} : ${n - ghosts} équipement(s)` +
      (ghosts ? `, ${ghosts} voisin(s) d'autres baies en pointillés` : "") +
      " — « Toute l'architecture » dans la liste pour le projet entier");
  } else renderStatus();
  saveLocal();
  requestAnimationFrame(updateMinimap);
}

/* ---- Boîte de saisie interne (remplace prompt/confirm natifs, absents
   de certains environnements : webview, navigateurs pilotés) ---------- */
function _ask(title, sub, initial, withInput) {
  return new Promise((resolve) => {
    const d = $("#ask-dialog"), form = $("#ask-form"), inp = $("#ask-input");
    $("#ask-title").textContent = title;
    $("#ask-sub").textContent = sub || "";
    $("#ask-sub").hidden = !sub;
    inp.hidden = !withInput;
    inp.value = initial || "";
    const done = (v) => {
      form.removeEventListener("submit", onOk);
      $("#ask-cancel").removeEventListener("click", onCancel);
      d.removeEventListener("cancel", onCancel);
      d.close();
      resolve(v);
    };
    const onOk = (e) => { e.preventDefault(); done(withInput ? inp.value : true); };
    const onCancel = (e) => { if (e) e.preventDefault(); done(null); };
    form.addEventListener("submit", onOk);
    $("#ask-cancel").addEventListener("click", onCancel);
    d.addEventListener("cancel", onCancel);
    d.showModal();
    if (withInput) { inp.focus(); inp.select(); }
  });
}
const askText = (title, sub, initial) => _ask(title, sub, initial, true);
const askConfirm = (title, sub) => _ask(title, sub, "", false);

/* ---- Version du PROJET (V1 -> V2 -> V3…) — on sait où on en est ----- */
function projectVersion() {
  /* Migration : un ancien indice lettre (A, B…) redevient un numéro. */
  const r = String(project.revision || "1");
  if (/^\d+$/.test(r)) return parseInt(r, 10);
  return r.toUpperCase().charCodeAt(0) - 64; // A=1, B=2…
}
$("#btn-new-version").addEventListener("click", async () => {
  const cur = projectVersion();
  const objet = await askText(`Passer le projet en V${cur + 1}`,
    `Le projet est en V${cur}. Qu'est-ce qui change dans cette nouvelle version ?`);
  if (!objet) return;
  project.revisions = project.revisions || [];
  if (!project.revisions.length)
    project.revisions.push({ indice: "V" + cur,
      date: new Date().toLocaleDateString("fr-FR"), objet: "Version initiale" });
  project.revision = String(cur + 1);
  project.revisions.push({ indice: "V" + (cur + 1),
    date: new Date().toLocaleDateString("fr-FR"), objet });
  saveLocal();
  renderStatus(`Projet passé en V${cur + 1} — historique dans le dossier DAT`);
});

/* ---- Sauvegarde façon draw.io / Visio : quoi, format, où — tout au
   choix. Les formats visuels (PDF, SVG, PNG, draw.io) ne valent que pour
   le projet ouvert ; « Enregistrer sous » laisse choisir librement ;
   « un dossier précis » accepte n'importe quel chemin (NAS, clé USB…)
   et le mémorise pour la fois suivante. -------------------------------- */
let backupCfg = { dossier_app: "", dernier_dossier: "" };
/* Le DERNIER choix devient LE défaut (quoi / format / où) : celui qui
   sauvegarde toujours en PDF retrouve PDF pré-coché. */
function restoreBackupChoices() {
  for (const name of ["bk-scope", "bk-format", "bk-dest"]) {
    const saved = localStorage.getItem("rfp-" + name);
    const radio = saved &&
      document.querySelector(`#backup-form input[name="${name}"][value="${saved}"]`);
    if (radio && radio.closest("label").style.display !== "none")
      radio.checked = true;
  }
}
$("#btn-backup").addEventListener("click", async () => {
  try {
    backupCfg = await (await fetch("/api/backup/config")).json();
  } catch { /* la config est un confort, pas une condition */ }
  $("#bk-dossier-app").textContent = backupCfg.dossier_app || "";
  const dir = $("#bk-dir");
  if (!dir.value) dir.value = backupCfg.dernier_dossier || "";
  restoreBackupChoices();
  syncBackupForm();
  $("#backup-dialog").showModal();
});
$("#backup-cancel").addEventListener("click", (e) => {
  e.preventDefault();
  $("#backup-dialog").close();
});
function syncBackupForm() {
  const f = new FormData($("#backup-form"));
  const scope = f.get("bk-scope");
  /* Un lot de projets ou l'espace de travail ne se dessine pas : les
     formats visuels ne valent que pour LE projet ouvert. */
  const visualsOk = scope === "projet";
  document.querySelectorAll("#bk-format-group .bk-visual").forEach((l) => {
    l.style.display = visualsOk ? "" : "none";
  });
  const fmt = f.get("bk-format");
  if (!visualsOk && !["zip", "json"].includes(fmt))
    $('#backup-form input[name="bk-format"][value="zip"]').checked = true;
  $("#bk-dir").hidden = f.get("bk-dest") !== "dossier";
}
$("#backup-form").addEventListener("change", syncBackupForm);
$("#backup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData($("#backup-form"));
  const scope = f.get("bk-scope"), fmt = f.get("bk-format"),
        dest = f.get("bk-dest"), dir = $("#bk-dir").value.trim();
  localStorage.setItem("rfp-bk-scope", scope);
  localStorage.setItem("rfp-bk-format", fmt);
  localStorage.setItem("rfp-bk-dest", dest);
  if (dest === "dossier" && !dir) {
    renderStatus('<span class="stat-err">Tape le chemin du dossier voulu</span>');
    return;
  }
  $("#backup-dialog").close();
  renderStatus("Sauvegarde en cours…");
  try {
    if (["zip", "json"].includes(fmt)) {
      /* Fichiers de données : le serveur les fabrique. */
      const body = { scope, format: fmt, dest, dir, project: currentProject() };
      const res = await fetch("/api/backup", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (dest === "telecharger") {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || "échec");
        }
        const name = /filename="([^"]+)"/
          .exec(res.headers.get("Content-Disposition") || "");
        await saveBlob(await res.blob(), name ? name[1] : "sauvegarde." + fmt);
        return;
      }
      const r = await res.json();
      if (!res.ok) throw new Error(r.detail || "échec");
      reportBackup(r);
      return;
    }
    /* Formats visuels : on génère l'export, puis on le range. */
    const id = currentProject().id;
    let blob = null, name = "";
    if (fmt === "pdf") {
      blob = await fetchExportBlob("/api/export/pdf" + exportQuery("dossier"));
      name = id + "-dossier.pdf";
    } else if (fmt === "svg") {
      blob = await fetchExportBlob("/api/export/svg" + exportQuery());
      name = id + viewSuffix() + ".svg";
    } else if (fmt === "png") {
      blob = await makePngBlob();
      name = id + viewSuffix() + ".png";
    } else if (fmt === "drawio") {
      blob = await fetchExportBlob("/api/export/drawio");
      name = id + ".drawio";
    }
    if (!blob) return;                       // l'erreur est déjà affichée
    if (dest === "telecharger") {
      await saveBlob(blob, name);
      return;
    }
    const targets = [];
    if (dest === "pc" || dest === "deux") targets.push(backupCfg.dossier_app);
    if (dest === "dossier" || dest === "deux") targets.push(dir);
    const oks = [], kos = [];
    for (const t of targets) {
      const res = await fetch("/api/backup/fichier?dir=" +
        encodeURIComponent(t) + "&name=" + encodeURIComponent(name),
        { method: "POST", body: blob });
      const r = await res.json().catch(() => ({}));
      if (res.ok) oks.push(r.fichier);
      else kos.push((r.detail || "échec") + " (" + t + ")");
    }
    if (kos.length)
      renderStatus(`<span class="${oks.length ? "stat-warn" : "stat-err"}">` +
        (oks.length ? `Enregistré ${oks.join(" · ")} — MAIS ` : "Échec — ") +
        kos.join(" · ") + "</span>");
    else
      renderStatus(`Enregistré ✓ ${oks.join(" · ")}`);
  } catch (err) {
    renderStatus(`<span class="stat-err">Sauvegarde échouée — ${err.message}</span>`);
  }
});
function reportBackup(r) {
  const oks = (r.resultats || []).map((x) =>
    `${x.destination} : ${x.elements} élément(s), ${(x.octets / 1048576).toFixed(1)} Mo`);
  const kos = (r.erreurs || []).map((x) => `${x.destination} : ${x.erreur}`);
  if (kos.length && oks.length)
    renderStatus(`<span class="stat-warn">Sauvé ${oks.join(" · ")} — MAIS ${kos.join(" · ")}</span>`);
  else if (kos.length)
    renderStatus(`<span class="stat-err">Sauvegarde échouée — ${kos.join(" · ")}</span>`);
  else
    renderStatus(`Sauvegardé ✓ ${oks.join(" · ")}`);
}

/* ---- Vue câblage : bouton bandeau, état mémorisé ------------------- */
function syncCablesBtn() {
  $("#btn-cables").classList.toggle("actif", cablesVisible);
}
$("#btn-cables").addEventListener("click", () => {
  cablesVisible = !cablesVisible;
  localStorage.setItem("rfp-cables-visibles", cablesVisible ? "1" : "0");
  syncCablesBtn();
  renderCables();
  renderStatus(cablesVisible
    ? "Cordons affichés — couleur = type de câble, cliquez un cordon pour l'éditer"
    : "Cordons masqués");
});
syncCablesBtn();

/* ---- Face avant / arrière : bouton bandeau, état mémorisé ----------
 * La vue arrière est DÉRIVÉE du projet, pas un second dessin : rien à
 * maintenir en double, elle ne peut donc pas diverger. */
function syncFaceBtn() {
  const lbl = $("#btn-face-label");
  if (lbl) lbl.textContent = rackFace === "rear" ? "Arrière" : "Avant";
  $("#btn-face").classList.toggle("actif", rackFace === "rear");
}
$("#btn-face").addEventListener("click", () => {
  rackFace = rackFace === "rear" ? "front" : "rear";
  localStorage.setItem("rfp-face", rackFace);
  syncFaceBtn();
  renderAll();
  renderStatus(rackFace === "rear"
    ? "Vue arrière — baie en miroir, dos des équipements montés en façade ; les U ne bougent pas"
    : "Vue avant");
});
syncFaceBtn();

/* ---- Fond du plan : 5 options, mémorisé, cyclé depuis le bandeau ---- */
const CANVAS_BGS = ["points", "carreaux", "ruche", "lignes", "uni"];
const CANVAS_BG_LABELS = { points: "Points", carreaux: "Carreaux",
                           ruche: "Ruche", lignes: "Lignes", uni: "Uni" };
let canvasBg = CANVAS_BGS.includes(localStorage.getItem("rfp-canvas-bg"))
  ? localStorage.getItem("rfp-canvas-bg") : "points";
document.body.dataset.canvasBg = canvasBg;
$("#btn-canvas-bg").addEventListener("click", () => {
  canvasBg = CANVAS_BGS[(CANVAS_BGS.indexOf(canvasBg) + 1) % CANVAS_BGS.length];
  document.body.dataset.canvasBg = canvasBg;
  localStorage.setItem("rfp-canvas-bg", canvasBg);
  renderStatus("Fond du plan : " + CANVAS_BG_LABELS[canvasBg]);
  if (viewMode === "physical") renderAll();  // les U libres suivent le motif
});

/* ---- Zoom / pan du plan — Ctrl+molette, boutons, glisser le fond ----
   CSS zoom (Chromium) : la mise en page ET les rectangles clients sont
   mis à l'échelle — chaque calcul écran->logique divise par canvasZoom. */
let canvasZoom = 1;

function setCanvasZoom(z, cx, cy) {
  const wrap = $("#canvas-wrap");
  z = Math.min(3, Math.max(0.25, Math.round(z * 100) / 100));
  if (z === canvasZoom) return;
  const r = wrap.getBoundingClientRect();
  const px = (cx ?? r.left + r.width / 2) - r.left;
  const py = (cy ?? r.top + r.height / 2) - r.top;
  /* Le point sous le curseur reste sous le curseur. */
  const lx = (wrap.scrollLeft + px) / canvasZoom;
  const ly = (wrap.scrollTop + py) / canvasZoom;
  canvasZoom = z;
  $("#canvas").style.zoom = canvasZoom;
  $("#btn-zoom-reset").textContent = Math.round(canvasZoom * 100) + " %";
  wrap.scrollLeft = lx * canvasZoom - px;
  wrap.scrollTop = ly * canvasZoom - py;
  requestAnimationFrame(updateMinimap);
}
$("#btn-zoom-in").addEventListener("click", () => setCanvasZoom(canvasZoom * 1.2));
$("#btn-zoom-out").addEventListener("click", () => setCanvasZoom(canvasZoom / 1.2));
$("#btn-zoom-reset").addEventListener("click", () => setCanvasZoom(1));
$("#btn-zoom-fit").addEventListener("click", () => {
  /* Ajuster : tout le plan visible d'un coup. */
  const wrap = $("#canvas-wrap");
  const fit = canvasZoom * Math.min(
    wrap.clientWidth / wrap.scrollWidth,
    wrap.clientHeight / wrap.scrollHeight);
  setCanvasZoom(Math.min(1, fit * 0.98));
  wrap.scrollLeft = 0;
  wrap.scrollTop = 0;
});
$("#canvas-wrap").addEventListener("wheel", (e) => {
  if (!e.ctrlKey) return;  // molette seule = défilement normal
  e.preventDefault();
  setCanvasZoom(canvasZoom * (e.deltaY < 0 ? 1.12 : 1 / 1.12),
                e.clientX, e.clientY);
}, { passive: false });

/* Pan : glisser le fond vide (ou bouton du milieu n'importe où). */
$("#canvas-wrap").addEventListener("pointerdown", (e) => {
  const wrap = $("#canvas-wrap");
  const onBg = e.target === wrap || e.target.id === "canvas";
  if (annotTool || drag) return;
  if (e.button !== 1 && !onBg) return;
  e.preventDefault();
  const sx = e.clientX + wrap.scrollLeft, sy = e.clientY + wrap.scrollTop;
  document.body.style.cursor = "grabbing";
  const move = (ev) => {
    wrap.scrollLeft = sx - ev.clientX;
    wrap.scrollTop = sy - ev.clientY;
  };
  const up = () => {
    document.body.style.cursor = "";
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", up);
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
});

/* ---- Minimap de navigation (coin bas-droit, toutes vues) ------------
   Dessin schématique : une boîte par élément posé + le rectangle du
   viewport. Cachée quand tout tient à l'écran. */
let minimapOff = localStorage.getItem("rfp-minimap-off") === "1";
function updateMinimap() {
  const wrap = $("#canvas-wrap");
  const mini = $("#minimap");
  if (!wrap || !mini) return;
  /* Ne s'affiche que si le débord vaut la peine d'être navigué —
     et jamais si l'utilisateur l'a fermée (son choix, mémorisé). */
  const fits = wrap.scrollWidth <= wrap.clientWidth + 40 &&
               wrap.scrollHeight <= wrap.clientHeight + 40;
  mini.classList.toggle("hidden", fits || minimapOff);
  if (fits || minimapOff) return;
  /* Épingle au coin bas-droit du VIEWPORT (le conteneur défile). */
  mini.style.left = (wrap.scrollLeft + wrap.clientWidth - 150 - 12) + "px";
  mini.style.top = (wrap.scrollTop + wrap.clientHeight - 100 - 12) + "px";
  const cv = mini.querySelector("canvas");
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height;
  const sw = wrap.scrollWidth, sh = wrap.scrollHeight;
  const PAD = 7;                     /* marge interne : rien ne colle au bord */
  const k = Math.min((W - PAD * 2) / sw, (H - PAD * 2) / sh);
  const ox = (W - sw * k) / 2, oy = (H - sh * k) / 2;
  const css = getComputedStyle(document.body);
  ctx.clearRect(0, 0, W, H);         /* le fond du panneau (CSS) respire */
  /* Une boîte DOUCE par bloc posé (baie, schéma, page) — coins ronds,
     teinte estompée : un plan, pas un pavage.
     getBoundingClientRect obligatoire : offsetLeft n'existe pas sur les
     éléments SVG (NaN silencieux = minimap vide). */
  ctx.fillStyle = css.getPropertyValue("--text-dim").trim() || "#64748b";
  ctx.globalAlpha = 0.35;
  const wr = wrap.getBoundingClientRect();
  for (const el of $("#canvas").children) {
    const r = el.getBoundingClientRect();
    const x = r.left - wr.left + wrap.scrollLeft;
    const y = r.top - wr.top + wrap.scrollTop;
    ctx.beginPath();
    ctx.roundRect(ox + x * k + 0.5, oy + y * k + 0.5,
                  Math.max(3, r.width * k - 1), Math.max(3, r.height * k - 1), 2);
    ctx.fill();
  }
  /* Viewport : liseré accent fin + voile léger — on voit OÙ on est sans
     que le rectangle écrase le plan. */
  const vx = ox + wrap.scrollLeft * k, vy = oy + wrap.scrollTop * k;
  const vw = wrap.clientWidth * k, vh = wrap.clientHeight * k;
  const accent = css.getPropertyValue("--accent").trim() || "#f97316";
  ctx.globalAlpha = 0.12;
  ctx.fillStyle = accent;
  ctx.beginPath(); ctx.roundRect(vx, vy, vw, vh, 3); ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = accent;
  ctx.lineWidth = 1.25;
  ctx.beginPath(); ctx.roundRect(vx + 0.5, vy + 0.5, vw - 1, vh - 1, 3);
  ctx.stroke();
}

(function wireMinimap() {
  const mini = $("#minimap");
  const wrap = $("#canvas-wrap");
  if (!mini || !wrap) return;
  const goTo = (e) => {
    const r = mini.getBoundingClientRect();
    const cv = mini.querySelector("canvas");
    const sw = wrap.scrollWidth, sh = wrap.scrollHeight;
    const k = Math.min(cv.width / sw, cv.height / sh);
    const ox = (cv.width - sw * k) / 2, oy = (cv.height - sh * k) / 2;
    const mx = (e.clientX - r.left) * (cv.width / r.width);
    const my = (e.clientY - r.top) * (cv.height / r.height);
    wrap.scrollLeft = (mx - ox) / k - wrap.clientWidth / 2;
    wrap.scrollTop = (my - oy) / k - wrap.clientHeight / 2;
  };
  /* La croix masque la minimap — le choix est mémorisé, et la case
     « Minimap » du menu Calques la ramène quand on veut. */
  const closeBtn = $("#minimap-close");
  const chk = $("#calque-minimap");
  if (chk) chk.checked = !minimapOff;
  const setMinimap = (off) => {
    minimapOff = off;
    localStorage.setItem("rfp-minimap-off", off ? "1" : "0");
    if (chk) chk.checked = !off;
    updateMinimap();
  };
  if (closeBtn) closeBtn.addEventListener("pointerdown", (e) => {
    e.stopPropagation();
    e.preventDefault();
    setMinimap(true);
    renderStatus("Minimap masquée — réactivable dans le menu Calques");
  });
  if (chk) chk.addEventListener("change", () => setMinimap(!chk.checked));
  mini.addEventListener("pointerdown", (e) => {
    if (e.target === closeBtn) return;
    e.preventDefault();
    goTo(e);
    const move = (ev) => goTo(ev);
    const up = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  });
  wrap.addEventListener("scroll", () => updateMinimap());
  window.addEventListener("resize", () => updateMinimap());
})();

/* ---- Calques du schéma logique (superposer sans mélanger) ----------- */
const ALL_LAYERS = ["zones", "liens", "etiquettes", "noeuds", "dessin"];
let hiddenLayers = new Set(
  JSON.parse(localStorage.getItem("rfp-calques-masques") || "[]"));

function layersQuery() {
  if (!hiddenLayers.size) return "";
  const shown = ALL_LAYERS.filter((l) => !hiddenLayers.has(l));
  return "&layers=" + shown.join(",");
}

$("#btn-calques").addEventListener("click", () => {
  const menu = $("#calques-menu");
  menu.hidden = !menu.hidden;
  if (!menu.hidden)
    menu.querySelectorAll("[data-calque]").forEach((cb) => {
      cb.checked = !hiddenLayers.has(cb.dataset.calque);
    });
});
document.querySelectorAll("#calques-menu [data-calque]").forEach((cb) =>
  cb.addEventListener("change", () => {
    if (cb.checked) hiddenLayers.delete(cb.dataset.calque);
    else hiddenLayers.add(cb.dataset.calque);
    localStorage.setItem("rfp-calques-masques",
      JSON.stringify([...hiddenLayers]));
    renderLogical();
  }));

/* ---- Bibliothèque de formes (icônes réseau vectorielles) ------------ */
let formesList = null;   // noms chargés à la demande
let pendingIcon = null;  // forme choisie, en attente d'un clic de pose

async function openFormesMenu() {
  const menu = $("#formes-menu");
  if (menu.hidden === false) { menu.hidden = true; return; }
  if (!formesList) {
    try {
      formesList = (await (await fetch("/api/formes")).json()).formes || [];
    } catch { formesList = []; }
  }
  renderFormesGrid($("#formes-filter").value || "");
  menu.hidden = false;
  $("#formes-filter").focus();
}

function renderFormesGrid(filter) {
  const grid = $("#formes-grid");
  grid.innerHTML = "";
  const f = filter.trim().toLowerCase();
  const names = (formesList || []).filter((n) => !f || n.includes(f));
  if (!names.length) {
    grid.innerHTML = '<div class="dialog-hint">Aucune forme' +
      (formesList?.length ? " ne correspond." : " dans le workspace (catalogue/formes/).") + "</div>";
    return;
  }
  for (const name of names) {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "forme-cell";
    cell.title = name.replace(/-/g, " ");
    const img = document.createElement("img");
    img.src = "/api/formes/svg/" + encodeURIComponent(name) +
              "?color=" + encodeURIComponent(C.text);
    img.alt = name;
    cell.appendChild(img);
    cell.addEventListener("click", () => {
      pendingIcon = name;
      $("#formes-menu").hidden = true;
      setAnnotTool("icone");
    });
    grid.appendChild(cell);
  }
}

$("#btn-formes").addEventListener("click", openFormesMenu);
$("#formes-filter").addEventListener("input",
  (e) => renderFormesGrid(e.target.value));

/* ---- Dessin libre (Texte / Zone / Flèche) — esprit draw.io ---------- */
let annotTool = null; // null | "texte" | "zone" | "fleche"

function setAnnotTool(tool) {
  annotTool = annotTool === tool ? null : tool;
  document.querySelectorAll("[data-annot]").forEach((b) =>
    b.classList.toggle("active", b.dataset.annot === annotTool));
  const hints = {
    texte: "Cliquez l'endroit du schéma où poser le texte",
    zone: "Cliquez-glissez pour encadrer la zone",
    fleche: "Cliquez-glissez du départ vers l'arrivée",
    ligne: "Cliquez-glissez pour tracer la ligne (diagonale libre)",
    ellipse: "Cliquez-glissez pour entourer en ellipse",
    icone: "Cliquez l'endroit du schéma où poser la forme",
  };
  renderStatus(annotTool ? hints[annotTool] + " — Échap pour annuler" : "");
}
document.querySelectorAll("[data-annot]").forEach((b) =>
  b.addEventListener("click", () => setAnnotTool(b.dataset.annot)));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && annotTool) setAnnotTool(annotTool);
});

function svgPoint(svg, e) {
  /* Rect + division par le zoom (le SVG logique est 1:1 avec son viewBox
     — plus fiable que getScreenCTM sous CSS zoom). */
  const r = svg.getBoundingClientRect();
  return {
    x: Math.max(0, (e.clientX - r.left) / canvasZoom),
    y: Math.max(0, (e.clientY - r.top) / canvasZoom),
  };
}

/* Le dessin libre vit dans la vue logique OU dans l'onglet Diagramme :
   même moteur, deux collections. */
function annotList() {
  if (viewMode === "diagram") {
    project.diagram = project.diagram || { annotations: [] };
    project.diagram.annotations = project.diagram.annotations || [];
    return project.diagram.annotations;
  }
  project.logical.annotations = project.logical.annotations || [];
  return project.logical.annotations;
}

function renderAnnotView() {
  if (viewMode === "diagram") renderDiagram();
  else renderLogical();
}

function addAnnotation(a) {
  annotList().push({
    id: "an-" + Date.now().toString(36), x2: 0, y2: 0, text: "", color: "", ...a,
  });
  renderAnnotView();
}

function wireAnnotTools(svg) {
  svg.addEventListener("pointerdown", (e) => {
    if (!annotTool) return;
    e.preventDefault();
    e.stopPropagation();
    const start = svgPoint(svg, e);
    if (annotTool === "texte") {
      setAnnotTool(annotTool);
      askText("Texte à poser").then((text) => {
        if (text) addAnnotation({ kind: "texte", x: start.x, y: start.y, text });
      });
      return;
    }
    if (annotTool === "icone") {
      setAnnotTool(annotTool);
      if (pendingIcon)
        addAnnotation({ kind: "icone", icon: pendingIcon,
                        x: start.x, y: start.y, x2: 64 });
      return;
    }
    /* zone / ellipse / flèche / ligne : glisser avec aperçu en direct. */
    const kind = annotTool;
    const ns = "http://www.w3.org/2000/svg";
    const tag = { zone: "rect", ellipse: "ellipse",
                  fleche: "line", ligne: "line" }[kind];
    const ghost = document.createElementNS(ns, tag);
    ghost.setAttribute("stroke", "#f97316");
    ghost.setAttribute("stroke-width", "1.6");
    ghost.setAttribute("stroke-dasharray", "6,4");
    ghost.setAttribute("fill", "none");
    svg.appendChild(ghost);
    let cur = start;
    const move = (ev) => {
      cur = svgPoint(svg, ev);
      if (kind === "zone") {
        ghost.setAttribute("x", Math.min(start.x, cur.x));
        ghost.setAttribute("y", Math.min(start.y, cur.y));
        ghost.setAttribute("width", Math.abs(cur.x - start.x));
        ghost.setAttribute("height", Math.abs(cur.y - start.y));
      } else if (kind === "ellipse") {
        ghost.setAttribute("cx", (start.x + cur.x) / 2);
        ghost.setAttribute("cy", (start.y + cur.y) / 2);
        ghost.setAttribute("rx", Math.abs(cur.x - start.x) / 2);
        ghost.setAttribute("ry", Math.abs(cur.y - start.y) / 2);
      } else {
        ghost.setAttribute("x1", start.x); ghost.setAttribute("y1", start.y);
        ghost.setAttribute("x2", cur.x); ghost.setAttribute("y2", cur.y);
      }
    };
    const up = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      ghost.remove();
      setAnnotTool(kind);
      if (Math.abs(cur.x - start.x) + Math.abs(cur.y - start.y) < 8) return;
      const q = (kind === "zone" || kind === "ellipse")
        ? "Titre (optionnel)" : "Étiquette (optionnel)";
      askText(q).then((text) => {
        if (text === null) return;  // Annuler = pas de forme
        addAnnotation({ kind, x: start.x, y: start.y,
                        x2: cur.x, y2: cur.y, text: text || "" });
      });
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  }, true);
}

function wireAnnotationMenus(svg) {
  /* Clic droit / édition du dessin libre (vue logique ET diagramme). */
  svg.querySelectorAll('g[id^="annot-"]').forEach((g) => {
    const anId = g.id.slice("annot-".length);
    g.addEventListener("contextmenu", (e) => {
      const list = annotList();
      const a = list.find((x) => x.id === anId);
      if (!a) return;
      _logicalMenu(e, a.text || { texte: "Texte", zone: "Zone", fleche: "Flèche",
                                  ligne: "Ligne", ellipse: "Ellipse",
                                  icone: a.icon || "Forme" }[a.kind], [
        ["Modifier le texte", async () => {
          const t = await askText("Texte", "", a.text);
          if (t !== null) { a.text = t; renderAnnotView(); }
        }],
        ["Supprimer", () => {
          const kept = list.filter((x) => x.id !== anId);
          if (viewMode === "diagram") project.diagram.annotations = kept;
          else project.logical.annotations = kept;
          renderAnnotView();
        }, "danger"],
      ]);
    });
  });
}

/* Onglet Diagramme — page de dessin libre (esprit Visio/draw.io). */
async function renderDiagram() {
  const res = await fetch("/api/export/svg?view=diagram&theme=" + theme, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  const canvas = $("#canvas");
  if (!res.ok) {
    canvas.innerHTML = "";
    renderStatus('<span class="stat-err">Projet invalide — diagramme indisponible</span>');
    return;
  }
  canvas.innerHTML = await res.text();
  const svg = canvas.querySelector("svg");
  if (svg) {
    wireAnnotTools(svg);
    wireAnnotationMenus(svg);
  }
  renderStatus();
  saveLocal();
  requestAnimationFrame(updateMinimap);
}

function wireLogical(svg) {
  if (!svg) return;
  wireAnnotTools(svg);
  wireAnnotationMenus(svg);
  /* Drag des nœuds : delta appliqué en transform pendant le geste,
     position persistée dans project.logical.positions au relâcher. */
  svg.querySelectorAll('g[id^="lnode-"]').forEach((g) => {
    const eqId = g.id.slice("lnode-".length);
    const rect = g.querySelector("rect");
    const ox = parseFloat(rect.getAttribute("x"));
    const oy = parseFloat(rect.getAttribute("y"));
    g.addEventListener("pointerdown", (e) => {
      if (annotTool) return;
      e.preventDefault();
      const sx = e.clientX, sy = e.clientY;
      let dx = 0, dy = 0;
      const move = (ev) => {
        dx = (ev.clientX - sx) / canvasZoom;
        dy = (ev.clientY - sy) / canvasZoom;
        g.setAttribute("transform", `translate(${dx},${dy})`);
      };
      const up = () => {
        document.removeEventListener("pointermove", move);
        document.removeEventListener("pointerup", up);
        if (Math.abs(dx) + Math.abs(dy) > 3) {
          if (!project.logical.positions) project.logical.positions = {};
          project.logical.positions[eqId] =
            { x: Math.max(0, ox + dx), y: Math.max(30, oy + dy) };
          renderLogical();
        }
      };
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", up);
    });
  });
  /* Clic sur un lien : édition / suppression. Clic droit : menu. */
  svg.querySelectorAll('g[id^="link-"]').forEach((g) => {
    const linkId = g.id.replace(/^link-(label-)?/, "");
    g.addEventListener("click", () => {
      const link = project.logical.links.find((l) => l.id === linkId);
      if (link) openLinkDialog(link);
    });
    g.addEventListener("contextmenu", (e) => openLogicalLinkMenu(e, linkId));
  });
  /* Clic droit sur un nœud : menu contextuel (comme la vue physique). */
  svg.querySelectorAll('g[id^="lnode-"]').forEach((g) => {
    const eqId = g.id.slice("lnode-".length);
    g.addEventListener("contextmenu", (e) => openLogicalNodeMenu(e, eqId));
  });
  /* Double-clic sur un nœud : fiche de l'équipement. */
  svg.querySelectorAll('g[id^="lnode-"]').forEach((g) => {
    g.addEventListener("dblclick", () =>
      openDeviceSheet(g.id.slice("lnode-".length)));
  });
}

/* Menus contextuels de la vue logique — même moule que la vue physique
   (id #item-menu réutilisé : fermeture et style déjà branchés). */
function _logicalMenu(e, title, actions) {
  e.preventDefault();
  e.stopPropagation();
  closeItemMenu();
  const menu = document.createElement("div");
  menu.id = "item-menu";
  menu.style.position = "fixed";
  menu.style.zIndex = "70";
  menu.innerHTML = `<div class="menu-title">${esc(title)}</div>`;
  for (const [label, fn, cls] of actions) {
    const row = document.createElement("div");
    row.className = "menu-item" + (cls ? " menu-" + cls : "");
    row.textContent = label;
    row.addEventListener("click", () => { closeItemMenu(); fn(); });
    menu.appendChild(row);
  }
  document.body.appendChild(menu);
  const pad = 6;
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.max(pad, Math.min(e.clientX,
    window.innerWidth - r.width - pad)) + "px";
  menu.style.top = Math.max(pad, Math.min(e.clientY,
    window.innerHeight - r.height - pad)) + "px";
}

function openLogicalNodeMenu(e, eqId) {
  let found = null;
  for (const rack of project.racks) {
    const item = rack.items.find((i) => i.id === eqId);
    if (item) { found = { rack, item }; break; }
  }
  if (!found) return;
  const t = typesById[found.item.type_id];
  const name = found.item.meta.hostname || `${t.vendor} ${t.model}`;
  const nLinks = project.logical.links.filter((l) =>
    l.from.equipment_id === eqId || l.to.equipment_id === eqId).length;
  _logicalMenu(e, name, [
    ["Fiche de l'équipement", () => openDeviceSheet(eqId)],
    ["Voir dans la baie", () => { setView("physical"); selectItem(eqId); }],
    ["Nouveau lien depuis ce nœud", () => openLinkDialog(null, { from: eqId })],
    ["Réinitialiser la position", () => {
      if (project.logical.positions) delete project.logical.positions[eqId];
      renderLogical();
    }],
    [`Supprimer ses liens (${nLinks})`, () => {
      project.logical.links = project.logical.links.filter((l) =>
        l.from.equipment_id !== eqId && l.to.equipment_id !== eqId);
      renderLogical();
    }, "danger"],
  ]);
}

function openLogicalLinkMenu(e, linkId) {
  const link = project.logical.links.find((l) => l.id === linkId);
  if (!link) return;
  _logicalMenu(e, link.label || link.kind, [
    ["Modifier le lien", () => openLinkDialog(link)],
    ["Supprimer le lien", () => {
      project.logical.links = project.logical.links.filter((l) => l !== link);
      renderLogical();
    }, "danger"],
  ]);
}

/* ---- Modale lien ---- */

let editingLink = null; // null = création

function equipmentOptions() {
  const opts = [];
  for (const rack of project.racks)
    for (const item of rack.items) {
      const t = typesById[item.type_id];
      if (!t || t.category === "blank" || t.category === "cable-mgmt") continue;
      const label = item.meta.hostname || `${t.vendor} ${t.model}`;
      opts.push({ id: item.id, label: `${label} (${rack.name} U${item.position_u})` });
    }
  return opts;
}

function openLinkDialog(link, prefill) {
  editingLink = link || null;
  const f = $("#link-form");
  const opts = equipmentOptions();
  if (opts.length < 2 && !link) {
    renderStatus('<span class="stat-err">Posez au moins deux équipements avant de créer un lien</span>');
    return;
  }
  for (const name of ["from_eq", "to_eq"]) {
    f.elements[name].innerHTML = opts
      .map((o) => `<option value="${o.id}">${o.label}</option>`).join("");
  }
  $("#link-dialog-title").textContent = link ? "Modifier le lien" : "Nouveau lien";
  $("#btn-link-delete").hidden = !link;
  f.elements.from_eq.value = link ? link.from.equipment_id
    : (prefill?.from || opts[0].id);
  f.elements.from_port.value = link ? link.from.port : "";
  f.elements.to_eq.value = link ? link.to.equipment_id
    : (prefill?.to || (opts[1] || opts[0]).id);
  f.elements.to_port.value = link ? link.to.port : "";
  f.elements.kind.value = link ? link.kind : "trunk";
  f.elements.vlans.value = link ? (link.vlans || []).join(", ") : "";
  f.elements.label.value = link ? link.label : "";
  f.elements.media.value = link ? link.media : "";
  $("#link-dialog").showModal();
}

$("#link-form").addEventListener("submit", (e) => {
  const action = e.submitter && e.submitter.value;
  if (action === "cancel") { editingLink = null; return; }
  if (action === "delete") {
    project.logical.links = project.logical.links.filter((l) => l !== editingLink);
    editingLink = null;
    renderAll();
    return;
  }
  const f = e.target;
  const vlans = f.elements.vlans.value.split(",")
    .map((s) => parseInt(s.trim(), 10)).filter((n) => n >= 1 && n <= 4094);
  const data = {
    from: { equipment_id: f.elements.from_eq.value, port: f.elements.from_port.value.trim() },
    to: { equipment_id: f.elements.to_eq.value, port: f.elements.to_port.value.trim() },
    kind: f.elements.kind.value, vlans,
    label: f.elements.label.value.trim(), media: f.elements.media.value.trim(),
  };
  if (editingLink) Object.assign(editingLink, data);
  else project.logical.links.push({
    id: "lnk-" + Math.random().toString(36).slice(2, 8), ...data });
  editingLink = null;
  renderAll();
});

$("#btn-add-link").addEventListener("click", () => openLinkDialog(null));

/* ---- Câblage en 2 clics (esprit PATCHBOX : départ → arrivée) ---- */

let connectFrom = null; // id de l'équipement de départ, null = mode inactif

$("#btn-start-connection").addEventListener("click", () => {
  if (!selectedItemId) return;
  connectFrom = selectedItemId;
  const found = findItem(connectFrom);
  const name = found?.item.meta.hostname
    || typesById[found?.item.type_id]?.model || connectFrom;
  renderStatus(`<span class="stat-accent">Connexion depuis ${name} — ` +
               `cliquez l'équipement d'arrivée (Échap pour annuler)</span>`);
  document.body.classList.add("connecting");
});

function cancelConnection() {
  if (!connectFrom) return;
  connectFrom = null;
  document.body.classList.remove("connecting");
  renderStatus();
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") cancelConnection();
});

/* ---- Surlignage des connexions au survol (vue physique) ---- */

function linkedIds(itemId) {
  const ids = new Set();
  for (const l of (project?.logical?.links || [])) {
    if (l.from.equipment_id === itemId) ids.add(l.to.equipment_id);
    if (l.to.equipment_id === itemId) ids.add(l.from.equipment_id);
  }
  return ids;
}

function highlightConnections(itemId) {
  const peers = linkedIds(itemId);
  if (!peers.size) return; // pas de lien : ne rien atténuer
  for (const g of document.querySelectorAll("g.rack-item")) {
    const id = g.dataset.itemId;
    if (id !== itemId && !peers.has(id)) g.classList.add("conn-dim");
    else g.classList.add("conn-lit");
  }
}

function clearHighlight() {
  for (const g of document.querySelectorAll("g.rack-item"))
    g.classList.remove("conn-dim", "conn-lit");
}

/* ---- Modale VLANs ---- */

function renderVlanList() {
  const wrap = $("#vlan-list");
  wrap.innerHTML = project.logical.vlans.length ? "" :
    '<span style="color:var(--text-dim)">Aucun VLAN déclaré.</span>';
  for (const v of project.logical.vlans) {
    const row = document.createElement("div");
    row.className = "vlan-row";
    row.innerHTML = `<span class="role-dot" style="background:${v.color}"></span>` +
      `<span>${v.vid} — ${v.name}</span><button title="Supprimer">×</button>`;
    row.querySelector("button").addEventListener("click", () => {
      project.logical.vlans = project.logical.vlans.filter((x) => x !== v);
      renderVlanList();
      saveLocal();
    });
    wrap.appendChild(row);
  }
}

$("#btn-add-vlan").addEventListener("click", () => {
  renderVlanList();
  $("#vlan-dialog").showModal();
});

$("#vlan-form").addEventListener("submit", (e) => {
  if (e.submitter && e.submitter.value === "cancel") { renderAll(); return; }
  e.preventDefault(); // la modale reste ouverte pour enchaîner les ajouts
  const f = e.target;
  project.logical.vlans.push({
    vid: parseInt(f.elements.vid.value, 10),
    name: f.elements.name.value.trim(),
    color: f.elements.color.value,
  });
  f.elements.vid.value = ""; f.elements.name.value = "";
  renderVlanList();
  saveLocal();
});

/* ---- Bascule de vue ---- */

function setView(mode) {
  if (mode === "logical" && viewMode === "physical" && focusRackId &&
      project.racks.some((r) => r.id === focusRackId))
    logicalRack = focusRackId;
  if (mode === "logical") syncLogicalRackSelect();
  viewMode = mode;
  document.body.dataset.view = mode;
  $("#btn-view-physical").classList.toggle("active", mode === "physical");
  $("#btn-view-logical").classList.toggle("active", mode === "logical");
  $("#btn-view-diagram").classList.toggle("active", mode === "diagram");
  $("#btn-view-plan").classList.toggle("active", mode === "plan");
  closeInspector();
  renderAll();
}
$("#btn-view-physical").addEventListener("click", () => setView("physical"));
$("#btn-view-logical").addEventListener("click", () => setView("logical"));
$("#btn-view-diagram").addEventListener("click", () => setView("diagram"));
$("#btn-view-plan").addEventListener("click", () => setView("plan"));

/* =====================================================================
 * Imports de modèles — YAML NetBox, PDF datasheet, image/SVG custom.
 * Tout passe par la modale de validation : rien n'entre en silence.
 * =================================================================== */

let pendingProposal = null; // { type: {...}, source: "yaml"|"pdf"|"image" }

function openProposal(type, source, confidence) {
  pendingProposal = { type, source };
  const dlg = $("#proposal-dialog");
  const f = $("#proposal-form");
  f.elements.vendor.value = type.vendor || "";
  f.elements.model.value = type.model || "";
  f.elements.category.value = type.category || "other";
  f.elements.u_height.value = type.u_height || 1;
  f.elements.power_w.value = type.power_w || 0;
  f.elements.ports_count.value = (type.ports || []).length;
  const hints = {
    yaml: "Importé depuis un devicetype NetBox — vérifiez puis validez.",
    pdf: "Extrait de la datasheet PDF. Les champs ambrés sont devinés : vérifiez-les.",
    image: "Faceplate custom — complétez les caractéristiques réelles.",
  };
  $("#proposal-hint").textContent = hints[source];
  /* Champs devinés (heuristique PDF) marqués visuellement. */
  for (const name of ["vendor", "model", "u_height", "power_w", "ports_count"]) {
    const key = name === "ports_count" ? "ports" : name;
    f.elements[name].classList.toggle(
      "guessed", source === "pdf" && confidence && !confidence[key]);
  }
  dlg.showModal();
}

$("#proposal-form").addEventListener("submit", (e) => {
  if (e.submitter && e.submitter.value === "cancel") { pendingProposal = null; return; }
  const f = e.target;
  const n = parseInt(f.elements.ports_count.value || "0", 10);
  const t = pendingProposal.type;
  /* Id unique dans la palette courante. */
  let id = t.id || "type-importe";
  while (typesById[id]) id += "-2";
  project.equipment_types.push({
    id, vendor: f.elements.vendor.value.trim(),
    model: f.elements.model.value.trim(),
    category: f.elements.category.value,
    u_height: Math.max(1, parseInt(f.elements.u_height.value, 10) || 1),
    power_w: parseFloat(f.elements.power_w.value) || 0,
    ports: Array.from({ length: n }, (_, i) => ({ name: "port" + (i + 1), type: "other" })),
    color: catalog.role_colors[f.elements.category.value] || "#94a3b8",
    faceplate_svg: null,
    faceplate_image: t.faceplate_image || null,
  });
  pendingProposal = null;
  refreshTypes();
  renderPalette($("#palette-filter").value);
  renderStatus("Modèle ajouté à la palette");
  saveLocal();
});

/* Lecture d'un fichier image/SVG en data URI (stocké dans le JSON projet :
 * le projet reste auto-suffisant, régénérable sans fichiers externes). */
function fileToDataURI(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

document.querySelectorAll("[data-import]").forEach((input) =>
  input.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    const kind = e.target.dataset.import;
    try {
      if (kind === "image") {
        openProposal({
          id: file.name.replace(/\.[^.]+$/, "").toLowerCase().replace(/[^a-z0-9]+/g, "-"),
          vendor: "", model: file.name.replace(/\.[^.]+$/, ""),
          category: "other", u_height: 1,
          faceplate_image: await fileToDataURI(file),
        }, "image");
        return;
      }
      const url = kind === "yaml" ? "/api/import/devicetype-yaml"
                                  : "/api/import/datasheet";
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        renderStatus(`<span class="stat-err">Import refusé : ${data.detail}</span>`);
        return;
      }
      if (kind === "yaml") openProposal(data.type, "yaml");
      else openProposal(data.proposal, "pdf", data.confidence);
    } catch (err) {
      renderStatus(`<span class="stat-err">Import impossible : ${err}</span>`);
    }
  }));

/* « Remplacer par image officielle » : clone le type de l'item sélectionné
 * dans les types du projet (même id => il remplace le type intégré). */
$("#replace-image-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  const found = findItem(selectedItemId);
  if (!file || !found) return;
  const dataUri = await fileToDataURI(file);
  const t = typesById[found.item.type_id];
  const existing = project.equipment_types.find((x) => x.id === t.id);
  if (existing) existing.faceplate_image = dataUri;
  else project.equipment_types.push({ ...t, faceplate_image: dataUri });
  refreshTypes();
  renderAll();
  renderStatus("Image officielle appliquée au modèle");
});

/* ---- Baies ---- */
/* Bascule de design sombre / clair (l'icône soleil du topbar). */
function applyTheme() {
  document.body.dataset.theme = theme;
  C = THEMES[theme];
  renderAll();
}
$("#btn-undo").addEventListener("click", () => restoreHistory(history.index - 1));
$("#btn-redo").addEventListener("click", () => restoreHistory(history.index + 1));

/* Menu Exporter : SVG / PDF / JSON regroupés. */
$("#btn-export-menu").addEventListener("click", (e) => {
  e.stopPropagation();
  $("#export-menu").hidden = !$("#export-menu").hidden;
});
$("#export-menu").addEventListener("click", () => { $("#export-menu").hidden = true; });
document.addEventListener("pointerdown", (e) => {
  if (!$("#export-menu").hidden && !e.target.closest(".dropdown"))
    $("#export-menu").hidden = true;
}, true);

$("#btn-search").addEventListener("click", openSearch);

$("#btn-theme").addEventListener("click", () => {
  const i = THEME_ORDER.indexOf(theme);
  theme = THEME_ORDER[(i + 1) % THEME_ORDER.length];
  localStorage.setItem("rfp-theme", theme);
  $("#btn-theme").title = `Design : ${THEME_LABELS[theme]} — cliquez pour changer`;
  renderStatus(`Design : ${THEME_LABELS[theme]}`);
  applyTheme();
});

function syncRenderButton() {
  const lbl = $("#btn-render-label");
  if (lbl) lbl.textContent = renderMode === "dessin" ? "Dessin" : "Photos";
}
$("#btn-render").addEventListener("click", () => {
  renderMode = renderMode === "dessin" ? "photos" : "dessin";
  localStorage.setItem("rfp-render", renderMode);
  syncRenderButton();
  renderAll();
});
syncRenderButton();

$("#btn-toggle-u").addEventListener("click", () => {
  showUNumbers = !showUNumbers;
  localStorage.setItem("rfp-show-u", showUNumbers ? "1" : "0");
  renderAll();
});

/* Ajouter une baie — TOUJOURS dit où elle va : « à droite de X » (après
   la baie donnée) ou tout à droite (bouton du bandeau / tuile « + Baie »).
   La lettre suivante est la première libre (A, B, C… sans doublon). */
/* Lettre de baie libre : A…Z puis AA, AB… (style colonnes Excel) — jamais
   de « Baie [ » ni de doublon « Baie Z ». */
function nextRackLetter() {
  const used = new Set(project.racks.map((r) => r.id));
  const names = new Set(project.racks.map((r) => r.name));
  for (let n = 0; n < 702; n++) {
    let k = n, s = "";
    do { s = String.fromCharCode(65 + (k % 26)) + s; k = Math.floor(k / 26) - 1; } while (k >= 0);
    if (!used.has("rack-" + s.toLowerCase()) && !names.has("Baie " + s)) return s;
  }
  return "X" + Date.now().toString(36);
}
function addRack(afterRack) {
  const used = new Set(project.racks.map((r) => r.id));
  const letter = nextRackLetter();
  const rack = newRack(letter);
  if (used.has(rack.id)) rack.id = "rack-" + Date.now().toString(36);
  const idx = afterRack ? project.racks.indexOf(afterRack) + 1 : project.racks.length;
  project.racks.splice(idx, 0, rack);
  focusRackId = rack.id;
  if (viewMode !== "physical") setView("physical"); else renderAll();
  scrollToRack(rack.id);
  const where = afterRack ? `à droite de ${afterRack.name}` : "tout à droite du plan";
  renderStatus(`Baie ${esc(rack.name)} ajoutée ${where} — glissez-y des équipements, ` +
    "clic sur son nom pour la renommer, clic droit pour la supprimer");
  return rack;
}
$("#btn-add-rack").addEventListener("click", () => addRack(null));

/* ---- Tableau de brassage ---- */
$("#btn-patch-table").addEventListener("click", async () => {
  const res = await fetch("/api/patch-table", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  const wrap = $("#patch-table-wrap");
  if (!res.ok) { wrap.textContent = "Projet invalide."; }
  else {
    const { rows } = await res.json();
    const head = ["Baie", "U", "Équipement", "Port", "Prise", "VLAN",
                  "Usage", "État"];
    wrap.innerHTML = "<table><thead><tr>" +
      head.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>" +
      (rows.length ? rows.map((r) =>
        `<tr><td>${r.rack}</td><td>U${r.u}</td><td>${r.equipment}</td>` +
        `<td>${r.port}</td><td>${r.outlet}</td><td>${r.vlan}</td>` +
        `<td>${r.usage}</td><td>${ETAT_LABELS[r.etat] || ""}</td></tr>`
      ).join("") : '<tr><td colspan="8">Aucun équipement.</td></tr>') +
      "</tbody></table>";
  }
  $("#patch-dialog").showModal();
});
$("#btn-close-patch").addEventListener("click", () => $("#patch-dialog").close());

/* ---- Import CSV de brassage (le retour d'Excel, là où vivent les
 * équipes câblage — plainte n°1 du terrain : la saisie de masse). ---- */

/* Parse CSV « ; » avec guillemets doubles (le format de notre export). */
function parseCSV(text) {
  const rows = [];
  for (const line of text.replace(/^﻿/, "").split(/\r?\n/)) {
    if (!line.trim()) continue;
    const cells = [];
    let cur = "", inQ = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQ) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (ch === '"') inQ = false;
        else cur += ch;
      } else if (ch === '"') inQ = true;
      else if (ch === ";") { cells.push(cur); cur = ""; }
      else cur += ch;
    }
    cells.push(cur);
    rows.push(cells);
  }
  return rows;
}

const ETAT_FROM_LABEL = { "up": "up", "down": "down", "réservé": "reserve",
                          "reserve": "reserve", "": "" };

function importPatchCSV(text) {
  const rows = parseCSV(text);
  if (!rows.length) return { ok: 0, ko: 0, motifs: ["fichier vide"] };
  /* En-tête : on repère les colonnes par leur nom (ordre libre). */
  const head = rows[0].map((h) => h.trim().toLowerCase());
  const col = (names) => head.findIndex((h) => names.some((n) => h.includes(n)));
  const ci = {
    rack: col(["baie"]), u: col(["u"]), eq: col(["équipement", "equipement"]),
    port: col(["port"]), outlet: col(["prise"]), vlan: col(["vlan"]),
    usage: col(["usage"]), etat: col(["état", "etat"]),
  };
  if (ci.eq < 0 || ci.port < 0)
    return { ok: 0, ko: rows.length - 1,
             motifs: ["colonnes Équipement et Port introuvables dans l'en-tête"] };
  let ok = 0, ko = 0;
  const motifs = new Set();
  for (const r of rows.slice(1)) {
    const eqName = (r[ci.eq] || "").trim();
    const portName = (r[ci.port] || "").trim();
    if (!eqName || !portName || portName === "—") { ko++; continue; }
    /* Cible : hostname exact d'abord, sinon libellé constructeur+modèle,
       restreint à la baie si la colonne existe. */
    let target = null;
    for (const rack of project.racks) {
      if (ci.rack >= 0 && (r[ci.rack] || "").trim() &&
          rack.name !== (r[ci.rack] || "").trim()) continue;
      for (const item of rack.items) {
        const t = typesById[item.type_id];
        if (item.meta.hostname === eqName ||
            (t && `${t.vendor} ${t.model}` === eqName)) { target = item; break; }
      }
      if (target) break;
    }
    if (!target) { ko++; motifs.add(`équipement introuvable : ${eqName}`); continue; }
    target.meta.port_usage = target.meta.port_usage || [];
    let pu = target.meta.port_usage.find((p) => p.port === portName);
    if (!pu) {
      pu = { port: portName, outlet: "", vlan: "", usage: "", etat: "" };
      target.meta.port_usage.push(pu);
    }
    if (ci.outlet >= 0) pu.outlet = (r[ci.outlet] || "").trim();
    if (ci.vlan >= 0) pu.vlan = (r[ci.vlan] || "").trim();
    if (ci.usage >= 0) pu.usage = (r[ci.usage] || "").trim();
    if (ci.etat >= 0)
      pu.etat = ETAT_FROM_LABEL[(r[ci.etat] || "").trim().toLowerCase()] || "";
    ok++;
  }
  return { ok, ko, motifs: [...motifs].slice(0, 3) };
}

$("#patch-csv-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const res = importPatchCSV(await file.text());
  $("#patch-import-msg").textContent =
    `${res.ok} ligne(s) appliquée(s), ${res.ko} ignorée(s)` +
    (res.motifs.length ? ` — ${res.motifs.join(" · ")}` : "");
  renderAll();
  $("#patch-dialog").close();     // showModal refuse un dialog déjà ouvert
  $("#btn-patch-table").click();  // recharge le tableau affiché
  e.target.value = "";
});
$("#btn-export-csv").addEventListener("click", () =>
  postForBlob("/api/patch-table.csv", currentProject().id + "-brassage.csv"));

/* ---- Sauvegarde de secours (localStorage) ---- */
function saveLocal() {
  /* Les modes ?demo=1 et ?projet=... n'écrasent jamais le projet local. */
  const qs = new URLSearchParams(location.search);
  if (!qs.has("demo") && !qs.get("projet")) {
    try { localStorage.setItem("rackforgeprime.project", JSON.stringify(project)); }
    catch { /* stockage plein ou bloqué : non bloquant */ }
  }
  pushHistory();
  /* Projet de l'espace de travail : enregistré en différé (1,5 s après
     le dernier geste) — basculer de projet en projet ne perd rien. */
  if (workspaceName && !qs.has("demo")) scheduleWorkspaceSave();
}

/* =====================================================================
 * Projets de l'espace de travail — basculer de l'un à l'autre, fluide :
 * le courant est enregistré, l'autre est chargé, aucun rechargement.
 * =================================================================== */
let _wsTimer = null;
let _wsLastSaved = "";   // dernier JSON enregistré : inchangé = pas de PUT
function scheduleWorkspaceSave() {
  clearTimeout(_wsTimer);
  _wsTimer = setTimeout(() => saveToWorkspace(), 1500);
}
function slugName(name) {
  const s = (name || "projet").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\- ]+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "").trim();
  return (s || "projet").slice(0, 60);
}
async function saveToWorkspace(name) {
  const target = name || workspaceName;
  if (!target) return false;
  clearTimeout(_wsTimer);
  const body = JSON.stringify(currentProject());
  if (target === workspaceName && body === _wsLastSaved) return true;  // rien n'a bougé
  const res = await fetch("/api/projects/" + encodeURIComponent(target), {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    renderStatus(`<span class="stat-err">Non enregistré (${esc(target)}) : ${esc(JSON.stringify(err.detail))}</span>`);
    return false;
  }
  workspaceName = target;
  _wsLastSaved = body;
  localStorage.setItem("rfp-ws-name", target);
  return true;
}
async function listWorkspaceProjects() {
  try {
    const res = await fetch("/api/projects");
    return res.ok ? (await res.json()).projects : [];
  } catch { return []; }
}
function _installProject(data, name) {
  project = data;
  if (!project.equipment_types) project.equipment_types = [];
  if (!project.logical) project.logical = { vlans: [], links: [], positions: {} };
  if (!project.diagram) project.diagram = { annotations: [] };
  if (!project.sites) project.sites = [];
  if (!project.flows) project.flows = [];
  workspaceName = name;
  if (name) localStorage.setItem("rfp-ws-name", name);
  else localStorage.removeItem("rfp-ws-name");
  selectedItemId = null; focusRackId = null; logicalRack = null; _logicalFitted = false;
  _wsLastSaved = name ? JSON.stringify(project) : "";
  planNav = { siteId: null, buildingId: null, roomId: null };
  history.stack = []; history.index = -1;
  refreshTypes();
  renderPalette($("#palette-filter").value);
  $("#project-name").value = project.name || "Sans nom";
  closeInspector();
  /* L'URL suit le projet ouvert (F5 rouvre le même). NB : `history` est
     l'undo de l'app — l'historique du navigateur est window.history. */
  const url = new URL(location.href);
  if (name) url.searchParams.set("projet", name); else url.searchParams.delete("projet");
  url.searchParams.delete("demo");
  window.history.replaceState(null, "", url);
  renderAll();
  updateUndoButtons();
}
async function switchProject(name) {
  if (name === workspaceName) return;
  /* 1. le projet courant est enregistré (sous son nom, ou un nom dérivé
     s'il n'en a pas encore et qu'il n'est pas vide). */
  if (workspaceName) await saveToWorkspace();
  else if (project.racks.some((r) => r.items.length))
    await saveToWorkspace(slugName(currentProject().name));
  /* 2. l'autre est chargé. */
  const res = await fetch("/api/projects/" + encodeURIComponent(name));
  if (!res.ok) {
    renderStatus(`<span class="stat-err">Projet « ${esc(name)} » illisible</span>`);
    return;
  }
  _installProject(await res.json(), name);
  renderStatus(`Projet « ${esc(name)} » ouvert — enregistré automatiquement dans l'espace de travail`);
}
async function openProjectsMenu(e) {
  const names = await listWorkspaceProjects();
  $("#projects-count").textContent = names.length ? String(names.length) : "";
  const actions = names.map((n) => [
    (n === workspaceName ? "● " : "") + n, () => switchProject(n),
    n === workspaceName ? "current" : ""]);
  actions.push(["＋ Nouveau projet", async () => {
    if (workspaceName) await saveToWorkspace();
    else if (project.racks.some((r) => r.items.length))
      await saveToWorkspace(slugName(currentProject().name));
    _installProject(newProject(), null);
    renderStatus("Nouveau projet — « Projets › Enregistrer » lui donne un nom dans l'espace de travail");
  }, "sep"]);
  actions.push([workspaceName ? `Enregistrer maintenant (${workspaceName})`
                              : "Enregistrer dans l'espace de travail…", async () => {
    let name = workspaceName;
    if (!name) {
      name = await askText("Nom du projet dans l'espace de travail",
        "Lettres, chiffres, tirets, espaces — devient projets/<nom>.json",
        slugName(currentProject().name));
      if (!name) return;
      name = slugName(name);
    }
    if (await saveToWorkspace(name)) {
      renderStatus(`Enregistré : ${esc(name)}.json — puis à chaque geste, automatiquement`);
      const url = new URL(location.href); url.searchParams.set("projet", name);
      window.history.replaceState(null, "", url);
    }
  }]);
  if (workspaceName)
    actions.push(["Détacher (ne plus enregistrer automatiquement)", () => {
      workspaceName = null; localStorage.removeItem("rfp-ws-name");
      const url = new URL(location.href); url.searchParams.delete("projet");
      window.history.replaceState(null, "", url);
      renderStatus("Projet détaché de l'espace de travail (localStorage seulement)");
    }]);
  _logicalMenu(e, "Projets de l'espace de travail", actions);
}
$("#btn-projects").addEventListener("click", openProjectsMenu);
listWorkspaceProjects().then((names) => {
  $("#projects-count").textContent = names.length ? String(names.length) : "";
});

/* =====================================================================
 * Undo / redo — instantanés du projet (la source de vérité est un JSON,
 * l'historique est donc trivial et fiable). Ctrl+Z / Ctrl+Y.
 * =================================================================== */

const history = { stack: [], index: -1, muted: false, MAX: 100 };

function pushHistory() {
  if (history.muted || !project) return;
  const snap = JSON.stringify(project);
  if (history.stack[history.index] === snap) return;
  history.stack.length = history.index + 1;
  history.stack.push(snap);
  if (history.stack.length > history.MAX) history.stack.shift();
  history.index = history.stack.length - 1;
  updateUndoButtons();
}

function restoreHistory(index) {
  if (index < 0 || index >= history.stack.length) return;
  history.index = index;
  history.muted = true;
  project = JSON.parse(history.stack[index]);
  $("#project-name").value = project.name || "";
  refreshTypes();
  renderAll();
  history.muted = false;
  updateUndoButtons();
}

function updateUndoButtons() {
  const u = $("#btn-undo"), r = $("#btn-redo");
  if (u) u.disabled = history.index <= 0;
  if (r) r.disabled = history.index >= history.stack.length - 1;
}

document.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey)) return;
  const k = e.key.toLowerCase();
  /* Pas d'interception dans un champ de saisie (undo natif du champ). */
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  if (k === "z" && !e.shiftKey) { e.preventDefault(); restoreHistory(history.index - 1); }
  else if (k === "y" || (k === "z" && e.shiftKey)) { e.preventDefault(); restoreHistory(history.index + 1); }
});
function loadLocal() {
  try {
    const raw = localStorage.getItem("rackforgeprime.project");
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

/* =====================================================================
 * Démarrage
 * =================================================================== */

/* Projet de démonstration (?demo=1) : une baie remplie et câblée,
 * utile pour découvrir l'application et pour les captures. */
function demoProject() {
  const p = newProject();
  p.name = "Démo — Baie LT1";
  p.racks[0].u_height = 24;
  p.racks[0].location = "Salle technique";
  p.racks[0].items = [
    { id: "eq-01", type_id: "fortinet-fortigate-100f", position_u: 22, face: "front",
      meta: { hostname: "FWL-01", role: "firewall", vlan: "", wall_outlet: "",
              port_usage: [{ port: "port1", outlet: "PM-R12", vlan: "99", usage: "Mgmt" }],
              serial: "", notes: "" } },
    { id: "eq-02", type_id: "fortinet-fortigate-600e", position_u: 20, face: "front",
      meta: { hostname: "FWL-02", role: "firewall", vlan: "", wall_outlet: "",
              port_usage: [], serial: "", notes: "" } },
    { id: "eq-03", type_id: "aruba-6300m-48g", position_u: 16, face: "front",
      meta: { hostname: "SW-CORE-01", role: "switch", vlan: "10", wall_outlet: "",
              port_usage: [], serial: "", notes: "" } },
    { id: "eq-04", type_id: "generic-patch-panel-24", position_u: 14, face: "front",
      meta: { hostname: "", role: "patch-panel", vlan: "", wall_outlet: "",
              port_usage: [], serial: "", notes: "" } },
    { id: "eq-05", type_id: "dell-poweredge-r650", position_u: 8, face: "front",
      meta: { hostname: "SRV-HYP-01", role: "server", vlan: "20", wall_outlet: "",
              port_usage: [], serial: "", notes: "" } },
    { id: "eq-06", type_id: "apc-smart-ups-3000-2u", position_u: 2, face: "front",
      meta: { hostname: "", role: "ups", vlan: "", wall_outlet: "",
              port_usage: [], serial: "", notes: "" } },
  ];
  p.logical = {
    vlans: [{ vid: 10, name: "USERS", color: "#22d3ee" },
            { vid: 99, name: "MGMT-AP", color: "#f59e0b" }],
    links: [
      { id: "lk-1", from: { equipment_id: "eq-01", port: "port16" },
        to: { equipment_id: "eq-02", port: "port16" }, kind: "ha",
        vlans: [], label: "HA", media: "" },
      { id: "lk-2", from: { equipment_id: "eq-01", port: "port1" },
        to: { equipment_id: "eq-03", port: "1/1/47" }, kind: "trunk",
        vlans: [10, 99], label: "Uplink FW", media: "fibre" },
      { id: "lk-3", from: { equipment_id: "eq-03", port: "1/1/1" },
        to: { equipment_id: "eq-05", port: "eno1" }, kind: "access",
        vlans: [10], label: "", media: "" },
    ],
    positions: {},
  };
  return p;
}

(async function init() {
  const res = await fetch("/api/catalog");
  catalog = await res.json();
  /* Paramètres d'URL : ?theme=clair|sombre force le thème,
     ?demo=1 charge le projet de démonstration. */
  const qs = new URLSearchParams(location.search);
  if (THEMES[qs.get("theme")]) {
    theme = qs.get("theme");
    C = THEMES[theme];
    document.body.dataset.theme = theme;
  }
  /* ?projet=<nom> charge un projet sauvegardé (captures, liens directs). */
  if (qs.get("projet")) {
    try {
      const res = await fetch("/api/projects/" +
                              encodeURIComponent(qs.get("projet")));
      project = res.ok ? await res.json() : null;
    } catch { project = null; }
    workspaceName = project ? qs.get("projet") : null;
  } else if (workspaceName && !qs.has("demo")) {
    /* Dernier projet de l'espace de travail ouvert : on le rouvre.
       (Un exe fraîchement lancé arrive ici sans ?projet=.) */
    try {
      const res = await fetch("/api/projects/" + encodeURIComponent(workspaceName));
      project = res.ok ? await res.json() : null;
    } catch { project = null; }
    if (!project) { workspaceName = null; localStorage.removeItem("rfp-ws-name"); }
  }
  if (qs.has("demo")) workspaceName = null;
  if (!project)
    project = qs.has("demo") ? demoProject() : (loadLocal() || newProject());
  if (!project.equipment_types) project.equipment_types = [];
  if (!project.logical) project.logical = { vlans: [], links: [], positions: {} };
  if (!project.diagram) project.diagram = { annotations: [] };
  if (!project.sites) project.sites = [];
  if (!project.flows) project.flows = [];
  document.body.dataset.view = viewMode;
  refreshTypes();
  renderPalette("");
  $("#palette-filter").addEventListener("input",
    (e) => renderPalette(e.target.value));
  $("#project-name").value = project.name;
  /* ?view=logical|diagram ouvre directement la vue voulue. */
  if (["logical", "diagram", "plan"].includes(qs.get("view"))) setView(qs.get("view"));
  else renderAll();
  renderStatus("Prêt");
})();

/* =====================================================================
 * Vue PLAN D'ÉTAGE — le parcours voulu : ville → bâtiment → salle → baies.
 * Le SVG de la salle est rendu par le BACKEND (svg_plan.py : ce qu'on
 * voit est ce qu'on exporte) ; le frontend pose la navigation et
 * l'interactivité : glisser les baies et les points, menus contextuels,
 * image de plan, opacité, échelle.
 * =================================================================== */

const PLAN_OX = 20, PLAN_OY = 64;   // translate() du groupe plan (miroir svg_plan)
let planNav = { siteId: null, buildingId: null, roomId: null };
try { planNav = Object.assign(planNav, JSON.parse(localStorage.getItem("rfp-plan-nav") || "{}")); }
catch { /* défaut */ }

const uid = (prefix) => prefix + "-" + Math.random().toString(36).slice(2, 8);
function planSite() { return (project.sites || []).find((s) => s.id === planNav.siteId) || null; }
function planBuilding() {
  const s = planSite();
  return s ? (s.buildings || []).find((b) => b.id === planNav.buildingId) || null : null;
}
function planRoom() {
  const b = planBuilding();
  return b ? (b.rooms || []).find((r) => r.id === planNav.roomId) || null : null;
}
function savePlanNav() { localStorage.setItem("rfp-plan-nav", JSON.stringify(planNav)); }
function allRooms() {
  const out = [];
  for (const s of project.sites || [])
    for (const b of s.buildings || [])
      for (const r of b.rooms || []) out.push({ site: s, building: b, room: r });
  return out;
}
/* Baies du projet non encore posées sur un plan (une baie = un seul plan). */
function unplacedRacks() {
  const placed = new Set();
  for (const { room } of allRooms()) for (const pr of room.racks || []) placed.add(pr.rack_id);
  return project.racks.filter((r) => !placed.has(r.id));
}

function renderPlanCrumb() {
  const el = $("#plan-crumb");
  const parts = ['<span class="crumb" data-lvl="0">Villes</span>'];
  const s = planSite(), b = planBuilding(), r = planRoom();
  if (s) parts.push(`<span class="crumb" data-lvl="1">${esc(s.name)}</span>`);
  if (b) parts.push(`<span class="crumb" data-lvl="2">${esc(b.name)}</span>`);
  if (r) parts.push(`<span class="crumb current" data-lvl="3">${esc(r.name)}</span>`);
  el.innerHTML = parts.join('<span class="sep">›</span>');
  el.querySelectorAll(".crumb").forEach((c) => c.addEventListener("click", () => {
    const lvl = +c.dataset.lvl;
    if (lvl < 3) planNav.roomId = null;
    if (lvl < 2) planNav.buildingId = null;
    if (lvl < 1) planNav.siteId = null;
    savePlanNav();
    renderAll();
  }));
  const add = $("#btn-plan-add");
  add.textContent = !s ? "+ Ville" : !b ? "+ Bâtiment" : "+ Salle";
  /* Les outils de salle n'ont de sens que dans une salle. */
  for (const id of ["#btn-plan-rack", "#btn-plan-point", "#btn-plan-image",
                    "#plan-opacity-wrap", "#btn-plan-settings"])
    $(id).style.display = r ? "" : "none";
  if (r) $("#plan-opacity").value = Math.round((r.plan_opacity ?? 0.6) * 100);
}

async function planAddLevel() {
  const s = planSite(), b = planBuilding();
  if (!s) {
    const name = await askText("Nouvelle ville / site", "ex : Paris, Lyon, Siège…", "");
    if (!name) return;
    project.sites.push({ id: uid("site"), name: name.trim(), address: "", buildings: [] });
  } else if (!b) {
    const name = await askText(`Nouveau bâtiment à ${s.name}`, "ex : Bâtiment A, Entrepôt…", "");
    if (!name) return;
    s.buildings.push({ id: uid("bat"), name: name.trim(), rooms: [] });
  } else {
    const name = await askText(`Nouvelle salle dans ${b.name}`, "ex : OLYMPE, Local technique RDC…", "");
    if (!name) return;
    const room = { id: uid("salle"), name: name.trim(), plan_image: null,
                   plan_opacity: 0.6, plan_w: 1200, plan_h: 800, mm_per_px: 10,
                   racks: [], points: [] };
    b.rooms.push(room);
    planNav.roomId = room.id;
    savePlanNav();
  }
  pushHistory();
  renderAll();
}
$("#btn-plan-add").addEventListener("click", planAddLevel);

/* Cartes de navigation (niveau ville / bâtiment / salle). */
function renderPlanNav(canvas) {
  const s = planSite(), b = planBuilding();
  let items, title, hint, sub, onOpen, addLabel;
  if (!s) {
    items = project.sites; title = "Villes / sites";
    hint = "Cliquez une ville pour descendre vers ses bâtiments, puis ses salles. Clic droit : renommer, supprimer.";
    sub = (x) => `${(x.buildings || []).length} bâtiment(s)`;
    onOpen = (x) => { planNav.siteId = x.id; }; addLabel = "Ville";
  } else if (!b) {
    items = s.buildings; title = `${s.name} — bâtiments`;
    hint = "Un bâtiment regroupe des salles (locaux techniques, salles serveurs).";
    sub = (x) => `${(x.rooms || []).length} salle(s)`;
    onOpen = (x) => { planNav.buildingId = x.id; }; addLabel = "Bâtiment";
  } else {
    items = b.rooms; title = `${s.name} › ${b.name} — salles`;
    hint = "Ouvrez une salle pour poser ses baies sur le plan d'étage.";
    sub = (x) => `${(x.racks || []).length} baie(s) · ${(x.points || []).length} point(s)` +
                 (x.plan_image ? " · plan chargé" : "");
    onOpen = (x) => { planNav.roomId = x.id; }; addLabel = "Salle";
  }
  const wrap = document.createElement("div");
  wrap.className = "plan-nav";
  wrap.innerHTML = `<h3>${esc(title)}</h3><div class="plan-hint">${esc(hint)}</div>`;
  for (const x of items) {
    const card = document.createElement("div");
    card.className = "plan-card";
    card.innerHTML = `<div class="pc-name">${esc(x.name)}</div><div class="pc-sub">${esc(sub(x))}</div>`;
    card.addEventListener("click", () => { onOpen(x); savePlanNav(); renderAll(); });
    card.addEventListener("contextmenu", (e) => _logicalMenu(e, x.name, [
      ["Ouvrir", () => { onOpen(x); savePlanNav(); renderAll(); }],
      ["Renommer…", async () => {
        const n = await askText("Renommer", "", x.name);
        if (n && n.trim()) { x.name = n.trim(); pushHistory(); renderAll(); }
      }],
      ["Supprimer…", async () => {
        const n = countUnder(x);
        if (!await askConfirm(`Supprimer « ${x.name} » ?`,
          n ? `${n} élément(s) posé(s) dessous seront retirés des plans — les baies restent dans le projet (Ctrl+Z pour annuler).`
            : "Rien n'est posé dessous (Ctrl+Z pour annuler).")) return;
        const idx = items.indexOf(x);
        if (idx >= 0) items.splice(idx, 1);
        pushHistory();
        renderAll();
      }, "danger"],
    ]));
    wrap.appendChild(card);
  }
  const add = document.createElement("div");
  add.className = "plan-card pc-add";
  add.title = "Ajouter";
  add.innerHTML = `+ <small style="font-size:12px;margin-left:6px">${addLabel}</small>`;
  add.addEventListener("click", planAddLevel);
  wrap.appendChild(add);
  canvas.appendChild(wrap);
}
function countUnder(x) {
  if (x.buildings) return x.buildings.reduce((a, b) => a + countUnder(b), 0);
  if (x.rooms) return x.rooms.reduce((a, r) => a + countUnder(r), 0);
  return (x.racks || []).length + (x.points || []).length;
}

async function renderPlan() {
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  if (!planSite()) planNav.siteId = null;
  if (!planBuilding()) planNav.buildingId = null;
  if (!planRoom()) planNav.roomId = null;
  renderPlanCrumb();
  const room = planRoom();
  if (!room) { renderPlanNav(canvas); renderStatus(); saveLocal(); return; }
  const res = await fetch("/api/export/svg?view=plan&theme=" + theme +
                          "&room=" + encodeURIComponent(room.id), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    renderStatus(`<span class="stat-err">Plan indisponible : ${esc(JSON.stringify(err.detail))}</span>`);
    return;
  }
  canvas.innerHTML = await res.text();
  wirePlan(canvas.querySelector("svg"), room);
  renderStatus(`${room.name} : ${room.racks.length} baie(s) posée(s), ` +
    `${unplacedRacks().length} à poser — glissez, clic droit pour les options`);
  saveLocal();
  requestAnimationFrame(updateMinimap);
}

/* Interactivité sur le SVG rendu par le backend. */
function wirePlan(svg, room) {
  if (!svg) return;
  const planPt = (e) => {
    const p = svgPoint(svg, e);
    return { x: p.x - PLAN_OX, y: p.y - PLAN_OY };
  };
  const clamp = (v, max) => Math.max(0, Math.min(max, v));
  /* Glisser une baie ou un point : transform mis à jour en direct,
     modèle mis à jour au relâchement, puis re-rendu (un seul moteur). */
  const startDrag = (g, e, getXY, setXY) => {
    e.preventDefault();
    e.stopPropagation();
    const start = planPt(e), from = getXY();
    const base = g.getAttribute("transform") || "";
    let moved = false;
    g.classList.add("plan-dragging");
    const onMove = (ev) => {
      const p = planPt(ev);
      const dx = p.x - start.x, dy = p.y - start.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      g.setAttribute("transform", `translate(${dx},${dy}) ${base}`);
    };
    const onUp = (ev) => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      g.classList.remove("plan-dragging");
      if (!moved) { g.setAttribute("transform", base); return; }
      const p = planPt(ev);
      setXY(clamp(from.x + p.x - start.x, room.plan_w),
            clamp(from.y + p.y - start.y, room.plan_h));
      pushHistory();
      renderPlan();
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
  };
  for (const pr of room.racks) {
    const g = svg.querySelector(`[id="planrack-${CSS.escape(pr.rack_id)}"]`);
    const rack = project.racks.find((r) => r.id === pr.rack_id);
    if (!g || !rack) continue;
    g.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      startDrag(g, e, () => ({ x: pr.x, y: pr.y }),
                (x, y) => { pr.x = Math.round(x); pr.y = Math.round(y); });
    });
    g.addEventListener("dblclick", () => { setView("physical"); scrollToRack(rack.id); });
    g.addEventListener("contextmenu", (e) => _logicalMenu(e, rack.name, [
      ["Tourner de 90°", () => { pr.rotation = ((pr.rotation || 0) + 90) % 360; pushHistory(); renderPlan(); }],
      ["Voir la baie (vue physique)", () => { setView("physical"); scrollToRack(rack.id); }],
      ["Retirer du plan", () => {
        room.racks = room.racks.filter((x) => x !== pr);
        pushHistory(); renderPlan();
      }, "danger"],
    ]));
  }
  for (const pt of room.points) {
    const g = svg.querySelector(`[id="planpoint-${CSS.escape(pt.id)}"]`);
    if (!g) continue;
    g.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      startDrag(g, e, () => ({ x: pt.x, y: pt.y }),
                (x, y) => { pt.x = Math.round(x); pt.y = Math.round(y); });
    });
    g.addEventListener("dblclick", () => openPointDialog(room, pt));
    g.addEventListener("contextmenu", (e) => _logicalMenu(e, pt.label || pt.kind, [
      ["Modifier…", () => openPointDialog(room, pt)],
      ["Supprimer", () => { room.points = room.points.filter((x) => x !== pt); pushHistory(); renderPlan(); }, "danger"],
    ]));
  }
  /* Fond du plan : clic droit = tout ce qu'on peut poser ICI. */
  svg.addEventListener("contextmenu", (e) => {
    if (e.target.closest('[id^="planrack-"], [id^="planpoint-"]')) return;
    const p = planPt(e);
    const actions = [];
    for (const r of unplacedRacks().slice(0, 8))
      actions.push([`Poser la baie ${r.name} ici`, () => placeRack(room, r, p.x, p.y)]);
    actions.push(["＋ Nouvelle baie ici (créée dans le projet)", () => {
      const rack = addRackSilently();
      placeRack(room, rack, p.x, p.y);
      renderStatus(`Baie ${esc(rack.name)} créée et posée ici — double-clic dessus pour la remplir en vue physique`);
    }]);
    actions.push(["Borne Wi-Fi ici", () => addPoint(room, "ap", p)]);
    actions.push(["Prise murale ici", () => addPoint(room, "prise", p)]);
    actions.push(["Caméra ici", () => addPoint(room, "camera", p)]);
    actions.push(["Note ici", () => addPoint(room, "note", p)]);
    actions.push(["Image du plan…", () => $("#btn-plan-image input").click()]);
    actions.push(["Réglages de la salle…", () => openRoomDialog(room)]);
    _logicalMenu(e, `${room.name} — ${Math.round(p.x)}, ${Math.round(p.y)} px`, actions);
  });
}
function addRackSilently() {
  const used = new Set(project.racks.map((r) => r.id));
  const rack = newRack(nextRackLetter());
  if (used.has(rack.id)) rack.id = "rack-" + Date.now().toString(36);
  project.racks.push(rack);
  return rack;
}
function scrollToRack(rackId) {
  requestAnimationFrame(() =>
    document.querySelector(`svg[data-rack-id="${CSS.escape(rackId)}"]`)
      ?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" }));
}
function placeRack(room, rack, x, y) {
  const fw = 600 / room.mm_per_px, fd = 1000 / room.mm_per_px;
  room.racks.push({ rack_id: rack.id, x: Math.round(Math.max(0, x - fw / 2)),
                    y: Math.round(Math.max(0, y - fd / 2)), rotation: 0 });
  pushHistory();
  renderPlan();
}
function addPoint(room, kind, p) {
  const pt = { id: uid("pt"), kind, label: "", x: Math.round(p.x), y: Math.round(p.y),
               radius: kind === "ap" ? Math.round(10000 / room.mm_per_px) : 0,
               equipment_id: "", color: "" };
  room.points.push(pt);
  pushHistory();
  openPointDialog(room, pt, true);
}

/* Bandeau : poser une baie / ajouter un point (au centre du plan). */
$("#btn-plan-rack").addEventListener("click", (e) => {
  const room = planRoom();
  if (!room) return;
  const free = unplacedRacks();
  const actions = free.map((r) =>
    [r.name, () => placeRack(room, r, room.plan_w / 2, room.plan_h / 2)]);
  actions.push(["＋ Nouvelle baie (créée dans le projet, posée au centre)", () => {
    const rack = addRackSilently();
    placeRack(room, rack, room.plan_w / 2, room.plan_h / 2);
    renderStatus(`Baie ${esc(rack.name)} créée et posée au centre — glissez-la, double-clic pour la remplir`);
  }, "sep"]);
  _logicalMenu(e, free.length ? "Poser une baie" : "Toutes les baies sont posées", actions);
});
$("#btn-plan-point").addEventListener("click", (e) => {
  const room = planRoom();
  if (!room) return;
  const c = { x: room.plan_w / 2, y: room.plan_h / 2 };
  _logicalMenu(e, "Ajouter un point", [
    ["Borne Wi-Fi (couverture)", () => addPoint(room, "ap", c)],
    ["Prise murale", () => addPoint(room, "prise", c)],
    ["Caméra", () => addPoint(room, "camera", c)],
    ["Équipement", () => addPoint(room, "equipement", c)],
    ["Note", () => addPoint(room, "note", c)],
  ]);
});
$("#plan-opacity").addEventListener("input", (e) => {
  const room = planRoom();
  if (!room) return;
  room.plan_opacity = (+e.target.value) / 100;
  const img = $("#canvas svg image");
  if (img) img.setAttribute("opacity", room.plan_opacity);
});
$("#plan-opacity").addEventListener("change", () => { saveLocal(); });
$("#btn-plan-settings").addEventListener("click", () => {
  const room = planRoom();
  if (room) openRoomDialog(room);
});

/* Image du plan : réduite à 1600 px de large (JPEG) pour rester légère
   dans le JSON du projet ; la salle prend la taille de l'image. */
$("#btn-plan-image input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  const room = planRoom();
  e.target.value = "";
  if (!file || !room) return;
  const uri = await fileToDataURI(file);
  const img = new Image();
  img.onload = () => {
    const maxW = 1600;
    const k = Math.min(1, maxW / img.width);
    const cv = document.createElement("canvas");
    cv.width = Math.round(img.width * k);
    cv.height = Math.round(img.height * k);
    cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
    room.plan_image = cv.toDataURL("image/jpeg", 0.85);
    room.plan_w = cv.width;
    room.plan_h = cv.height;
    pushHistory();
    renderPlan();
    renderStatus(`Plan chargé : ${cv.width} × ${cv.height} px — réglez l'échelle (mm/px) dans Réglages`);
  };
  img.onerror = () => renderStatus('<span class="stat-err">Image illisible</span>');
  img.src = uri;
});

/* Dialogue point (borne, prise, caméra, note). */
let editingPoint = null;
const POINT_COLORS = { ap: "#22d3ee", prise: "#3b82f6", camera: "#a78bfa",
                       equipement: "#34d399", note: "#94a3b8" };
function openPointDialog(room, pt, isNew) {
  editingPoint = { room, pt, isNew: !!isNew };
  const f = $("#point-form");
  $("#point-dialog-title").textContent = isNew ? "Nouveau point" : (pt.label || "Point");
  const sel = f.elements.equipment_id;
  sel.innerHTML = '<option value="">—</option>' + project.racks.map((r) =>
    r.items.map((it) => {
      const t = typesById[it.type_id];
      const lbl = it.meta.hostname || (t ? `${t.vendor} ${t.model}` : it.id);
      return `<option value="${esc(it.id)}">${esc(r.name)} · U${it.position_u} · ${esc(lbl)}</option>`;
    }).join("")).join("");
  f.elements.kind.value = pt.kind;
  f.elements.label.value = pt.label || "";
  f.elements.radius_m.value = pt.radius ? +(pt.radius * room.mm_per_px / 1000).toFixed(1) : "";
  f.elements.equipment_id.value = pt.equipment_id || "";
  f.elements.color.value = pt.color || POINT_COLORS[pt.kind] || "#94a3b8";
  $("#btn-point-delete").hidden = !!isNew;
  $("#point-dialog").showModal();
}
$("#point-dialog").addEventListener("close", () => {
  const ep = editingPoint;
  editingPoint = null;
  if (!ep) return;
  const f = $("#point-form"), v = $("#point-dialog").returnValue;
  const { room, pt, isNew } = ep;
  if (v === "delete" || (v !== "ok" && isNew)) {
    room.points = room.points.filter((x) => x !== pt);
    pushHistory(); renderPlan(); return;
  }
  if (v !== "ok") return;
  pt.kind = f.elements.kind.value;
  pt.label = f.elements.label.value.trim();
  const m = parseFloat(String(f.elements.radius_m.value).replace(",", "."));
  pt.radius = Number.isFinite(m) && m > 0 ? Math.round(m * 1000 / room.mm_per_px) : 0;
  pt.equipment_id = f.elements.equipment_id.value;
  pt.color = f.elements.color.value;
  pushHistory();
  renderPlan();
});

/* Réglages de la salle. */
let editingRoom = null;
function openRoomDialog(room) {
  editingRoom = room;
  const f = $("#room-form");
  f.elements.name.value = room.name;
  f.elements.plan_w.value = room.plan_w;
  f.elements.plan_h.value = room.plan_h;
  f.elements.mm_per_px.value = room.mm_per_px;
  $("#btn-room-noimage").hidden = !room.plan_image;
  $("#room-dialog").showModal();
}
$("#room-dialog").addEventListener("close", () => {
  const room = editingRoom;
  editingRoom = null;
  if (!room) return;
  const f = $("#room-form"), v = $("#room-dialog").returnValue;
  if (v === "noimage") { room.plan_image = null; pushHistory(); renderPlan(); return; }
  if (v !== "ok") return;
  room.name = f.elements.name.value.trim() || room.name;
  room.plan_w = Math.max(200, +f.elements.plan_w.value || room.plan_w);
  room.plan_h = Math.max(200, +f.elements.plan_h.value || room.plan_h);
  room.mm_per_px = Math.max(0.1, +f.elements.mm_per_px.value || room.mm_per_px);
  pushHistory();
  renderPlan();
});

/* =====================================================================
 * MATRICE DE FLUX — lignes éditables + vue croisée zones × zones.
 * =================================================================== */
const FLOW_ACTIONS = [["", "à définir"], ["allow", "Autorisé"], ["deny", "Refusé"], ["nat", "NAT"]];

function renderFlowsTable() {
  const tb = $("#flows-table tbody");
  tb.innerHTML = "";
  if (!project.flows.length) {
    tb.innerHTML = '<tr><td colspan="8" class="dialog-hint">Aucun flux — « + Ligne » ou « Proposer depuis le projet ».</td></tr>';
    return;
  }
  for (const fl of project.flows) {
    const tr = document.createElement("tr");
    const cell = (name, ph) => {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.value = fl[name] || "";
      inp.placeholder = ph || "";
      inp.addEventListener("input", () => { fl[name] = inp.value; saveLocal(); });
      td.appendChild(inp);
      return td;
    };
    tr.appendChild(cell("src", "VLAN 20 — USERS"));
    tr.appendChild(cell("dst", "Internet"));
    tr.appendChild(cell("proto", "tcp"));
    tr.appendChild(cell("ports", "443, 8443"));
    const tdA = document.createElement("td");
    const sel = document.createElement("select");
    sel.innerHTML = FLOW_ACTIONS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
    sel.value = fl.action || "";
    sel.className = "act-" + (fl.action || "none");
    sel.addEventListener("change", () => {
      fl.action = sel.value; sel.className = "act-" + (fl.action || "none"); saveLocal();
    });
    tdA.appendChild(sel);
    tr.appendChild(tdA);
    tr.appendChild(cell("via", "FW-01"));
    tr.appendChild(cell("comment", ""));
    const tdD = document.createElement("td");
    const del = document.createElement("button");
    del.className = "fl-del"; del.textContent = "✕"; del.title = "Supprimer la ligne";
    del.addEventListener("click", () => {
      project.flows = project.flows.filter((x) => x !== fl);
      pushHistory(); renderFlowsTable();
    });
    tdD.appendChild(del);
    tr.appendChild(tdD);
    tb.appendChild(tr);
  }
}
function renderFlowsMatrix() {
  const zones = [];
  const cells = {};
  const rank = { "": 0, allow: 1, nat: 2, deny: 3 };
  for (const f of project.flows) {
    for (const z of [f.src, f.dst]) if (z && !zones.includes(z)) zones.push(z);
    if (!f.src || !f.dst) continue;
    const cur = (cells[f.src] || {})[f.dst] || "";
    if (rank[f.action || ""] >= rank[cur]) (cells[f.src] = cells[f.src] || {})[f.dst] = f.action || "";
  }
  const lbl = Object.fromEntries(FLOW_ACTIONS);
  const box = $("#flows-matrix");
  if (!zones.length) { box.innerHTML = '<div class="dialog-hint">Aucune zone : ajoutez des lignes de flux.</div>'; return; }
  box.innerHTML = "<table><thead><tr><th>source ↓ / destination →</th>" +
    zones.map((z) => `<th>${esc(z)}</th>`).join("") + "</tr></thead><tbody>" +
    zones.map((a) => `<tr><th class="rowhead">${esc(a)}</th>` + zones.map((b) => {
      if (a === b) return '<td class="fm-self">—</td>';
      const act = (cells[a] || {})[b];
      if (act === undefined) return '<td class="fm-none">·</td>';
      return `<td class="fm-${act || "none"}">${esc(lbl[act] || "à définir")}</td>`;
    }).join("") + "</tr>").join("") + "</tbody></table>";
}
let flowsMatrixMode = false;
function syncFlowsMode() {
  $("#flows-table-wrap").hidden = flowsMatrixMode;
  $("#flows-matrix").hidden = !flowsMatrixMode;
  $("#btn-flows-matrix").textContent = flowsMatrixMode ? "Vue lignes" : "Vue matrice";
  if (flowsMatrixMode) renderFlowsMatrix(); else renderFlowsTable();
}
$("#btn-flows").addEventListener("click", () => {
  $("#flows-msg").textContent = "";
  syncFlowsMode();
  $("#flows-dialog").showModal();
});
$("#btn-close-flows").addEventListener("click", () => { $("#flows-dialog").close(); renderAll(); });
$("#btn-flows-matrix").addEventListener("click", () => { flowsMatrixMode = !flowsMatrixMode; syncFlowsMode(); });
$("#btn-flows-add").addEventListener("click", () => {
  project.flows.push({ id: uid("fl"), src: "", dst: "", proto: "", ports: "", action: "", via: "", comment: "" });
  flowsMatrixMode = false; syncFlowsMode();
  $("#flows-table tbody tr:last-child input")?.focus();
});
$("#btn-flows-propose").addEventListener("click", async () => {
  const res = await fetch("/api/flows/propose", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) { $("#flows-msg").textContent = "Projet invalide — proposition impossible"; return; }
  const { flows } = await res.json();
  if (!flows.length) {
    $("#flows-msg").textContent = "Rien à proposer : déclarez des VLANs (vue Logique) ou un port WAN.";
    return;
  }
  project.flows.push(...flows);
  pushHistory();
  $("#flows-msg").textContent = `${flows.length} ligne(s) proposée(s) — action « à définir » : à vous de trancher.`;
  flowsMatrixMode = false; syncFlowsMode();
});
$("#btn-flows-csv").addEventListener("click", () =>
  postForBlob("/api/flows.csv", currentProject().id + "-flux.csv"));


/* =====================================================================
 * Application de bureau : la fenêtre dit « je suis là » toutes les 5 s,
 * et « au revoir » quand elle se ferme — le serveur s'arrête alors
 * (plus jamais de processus fantôme qui bloque le port au lancement
 * suivant). Un rechargement (F5) renvoie un ping tout de suite.
 * =================================================================== */
(function heartbeat() {
  /* Chaque fenêtre/onglet a son identifiant : fermer l'un n'éteint pas
     l'app tant qu'un autre vit encore. */
  const cid = "w-" + Math.random().toString(36).slice(2, 10);
  const ping = () => fetch("/api/ping?c=" + cid, { cache: "no-store" }).catch(() => {});
  ping();
  setInterval(ping, 5000);
  window.addEventListener("pagehide", () => {
    try {
      if (navigator.sendBeacon) navigator.sendBeacon("/api/bye", cid);
      else fetch("/api/bye", { method: "POST", body: cid, keepalive: true }).catch(() => {});
    } catch { /* rien : le silence de 3 min fera le reste */ }
  });
})();
