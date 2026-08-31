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

/* ---- Constantes d'échelle (miroir de svg_export.py) ---- */
const U_PX = 22, RACK_W = 440, RAIL_W = 26, FRAME_PAD = 14,
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
    frame: "#171a0c", rail: "#232816", hole: "#070903", slot: "#12150a",
    slotLine: "#1e2210", text: "#d4d9b8", dim: "#7f8663", face: "#1b1f0e",
    accent: "#eb9c14", danger: "#e06c5a",
    faceStroke: "#2c3118", pill: "#3d4423", portFill: "#0b0d05",
    decorFill: "#14180b", decorStroke: "#2c3118", ring: "#3f4725",
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

/* Faceplate placeholder — même dessin que _faceplate_placeholder() côté Python. */
function drawFaceplate(g, t, x, y, label, selected, item) {
  const h = t.u_height * U_PX;
  if (t.faceplate_image && renderMode !== "dessin") {
    /* Image officielle : proportions respectées (jamais étirée), centrée
       sur le fond de façade — même règle que l'export Python. */
    g.appendChild(svgEl("rect", { x, y: y + 1, width: RACK_W, height: h - 2, fill: C.face }));
    const img = svgEl("image", {
      x, y: y + 1, width: RACK_W, height: h - 2,
      preserveAspectRatio: "xMidYMid meet", href: t.faceplate_image,
    });
    g.appendChild(img);
    /* Sur une photo officielle les ports ne sont pas localisables :
       le survol montre la fiche de l'équipement. */
    if (item) {
      img.addEventListener("mousemove", (e) => showTip(itemTipHTML(t, item), e));
      img.addEventListener("mouseleave", hideTip);
    }
    /* Le MÊME cadre que les dessins : bordure, liseré de rôle, bandeau
       hostname, pastille U — un seul langage visuel (miroir Python). */
    g.appendChild(svgEl("rect", {
      x, y: y + 1, width: RACK_W, height: h - 2, rx: 2, fill: "none",
      stroke: C.faceStroke, "stroke-width": 1,
    }));
    g.appendChild(svgEl("rect", { x, y: y + 1, width: 4, height: h - 2, fill: t.color }));
    if (label) {
      const bw = Math.min(label.length * 6.2 + 14, RACK_W - 60);
      g.appendChild(svgEl("rect", {
        x: x + 6, y: y + h - 15, width: bw, height: 12, rx: 2,
        fill: C.band, "fill-opacity": 0.78,
      }));
      g.appendChild(svgEl("text", {
        x: x + 12, y: y + h - 6, "font-size": 9, fill: "#f1f5f9",
        "font-family": "system-ui, sans-serif",
      }, label));
    }
    g.appendChild(svgEl("rect", {
      x: x + RACK_W - 34, y: y + h / 2 - 7, width: 26, height: 14, rx: 7,
      fill: C.face, "fill-opacity": 0.85, stroke: C.pill, "stroke-width": 1,
    }));
    g.appendChild(svgEl("text", {
      x: x + RACK_W - 21, y: y + h / 2 + 3, "text-anchor": "middle",
      "font-size": 8.5, fill: C.dim, "font-family": "monospace",
    }, t.u_height + "U"));
    if (selected)
      g.appendChild(svgEl("rect", { x, y: y + 1, width: RACK_W, height: h - 2,
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
  /* Serveur / onduleur / passe-câbles : la silhouette prime sur les
     quelques ports de management (miroir Python). */
  if (["server", "ups", "cable-mgmt"].includes(t.category))
    drawCategoryDecor(g, t, x, y, RACK_W, h);
  else if ((t.ports || []).length)
    drawPortBanks(g, t, item, x, y, RACK_W, h);
  /* Libellé sur plaquette sombre en bas à gauche (même langage que les
     photos) : le texte ne se réécrit jamais sur le matériel. */
  if (label) {
    const bw = Math.min(label.length * 6.2 + 14, RACK_W - 60);
    g.appendChild(svgEl("rect", {
      x: x + 6, y: y + h - 15, width: bw, height: 12, rx: 2,
      fill: C.band, "fill-opacity": 0.85,
    }));
    g.appendChild(svgEl("text", {
      x: x + 12, y: y + h - 6, "font-size": 9, fill: "#f1f5f9",
      "font-family": "system-ui, sans-serif",
    }, label));
  }
  /* Pastille de hauteur U. */
  g.appendChild(svgEl("rect", {
    x: x + RACK_W - 34, y: yc - 7, width: 26, height: 14, rx: 7,
    fill: C.face, "fill-opacity": 0.85, stroke: C.pill, "stroke-width": 1,
  }));
  g.appendChild(svgEl("text", {
    x: x + RACK_W - 21, y: yc + 3, "text-anchor": "middle",
    "font-size": 8.5, fill: C.dim, "font-family": "monospace",
  }, t.u_height + "U"));
}

/* Ports groupés en banques de 6, 2 rangées au-delà de 12 (miroir Python).
 * Chaque port a une zone de survol élargie → info-bulle de config. */
function drawPortBanks(g, t, item, x, y, w, h) {
  const color = t.color;
  const n = Math.min((t.ports || []).length, 48);
  const rows = n > 12 ? 2 : 1;
  const cols = Math.ceil(n / rows);
  const pw = 7, gapx = 2, group = 6, ggap = 4;
  const ph = rows === 2 ? 6 : 8;
  const groups = Math.ceil(cols / group);
  const totalW = cols * (pw + gapx) - gapx + (groups - 1) * ggap;
  const x0 = x + w - 46 - totalW;
  const blockH = rows * ph + (rows - 1) * 3;
  const y0 = y + (h - blockH) / 2;
  for (let i = 0; i < n; i++) {
    const r = i % rows, c = Math.floor(i / rows);
    const px = x0 + c * (pw + gapx) + Math.floor(c / group) * ggap;
    const py = y0 + r * (ph + 3);
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
  if (t.category === "server") {
    const bw = 13, gap = 3, count = 10;
    const x0 = x + w - 46 - count * (bw + gap);
    for (let i = 0; i < count; i++) {
      const bx = x0 + i * (bw + gap);
      g.appendChild(svgEl("rect", {
        x: bx, y: y + 4, width: bw, height: h - 8, rx: 1,
        fill: C.decorFill, stroke: C.decorStroke, "stroke-width": 0.7,
      }));
      g.appendChild(svgEl("circle", {
        cx: bx + bw / 2, cy: y + 7, r: 1.3, fill: t.color,
      }));
    }
  } else if (t.category === "ups") {
    g.appendChild(svgEl("rect", {
      x: x + w - 200, y: y + h / 2 - 8, width: 30, height: 16, rx: 2,
      fill: C.lcd, stroke: t.color, "stroke-width": 0.8,
    }));
    for (let i = 0; i < 24; i++)
      g.appendChild(svgEl("rect", {
        x: x + w - 155 + i * 5, y: y + h / 2 - 6, width: 2, height: 12,
        rx: 1, fill: C.decorFill,
      }));
  } else if (t.category === "cable-mgmt") {
    for (let i = 0; i < 4; i++)
      g.appendChild(svgEl("rect", {
        x: x + 200 + i * 50, y: y + 3, width: 30, height: h - 6, rx: 4,
        fill: "none", stroke: C.ring, "stroke-width": 2,
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
  titleG.appendChild(svgEl("text", { x: w / 2, y: 24, "text-anchor": "middle",
    "font-size": 15, "font-weight": "bold", fill: C.text }, rack.name));
  const pencil = svgEl("g", { class: "rack-pencil",
    transform: `translate(${w / 2 + rack.name.length * 4.2 + 12}, 12)` });
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
  /* Localisation (salle, adresse) sous le nom — comme à l'export. */
  if (rack.location)
    svg.appendChild(svgEl("text", { x: w / 2, y: 37, "text-anchor": "middle",
      "font-size": 10.5, fill: C.dim }, rack.location));

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
        svg.appendChild(svgEl("text", { x: rx + RAIL_W / 2, y: y + U_PX / 2 + 3,
          "text-anchor": "middle", "font-size": 9.5, fill: C.dim,
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
    const label = item.meta.hostname || `${t.vendor} ${t.model}`;
    drawFaceplate(g, t, innerX, y, label, item.id === selectedItemId, item);
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
    "font-size": 11, fill: C.accent, "font-family": "monospace" },
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

  const ports = t.ports || [];
  const used = ports.filter((p) => portUsageOf(item, p.name)).length;
  const tiles = [
    ["Ports totaux", ports.length],
    ["Brassés", used],
    ["Libres", ports.length - used],
    ["Consommation", `${t.power_w} W`],
  ];
  $("#device-tiles").innerHTML = tiles.map(([k, v]) =>
    `<div class="tile"><div class="tile-k">${k}</div>` +
    `<div class="tile-v">${v}</div></div>`).join("");

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
  renderAll();
  openDeviceSheet(deviceItemId);
});
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
          id: nextItemId(), type_id: t.id, position_u: u, face: "front",
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
  renderOnboarding();
  renderStatus();
  saveLocal();
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
  if (!canPlace(rack, u, d.type.u_height, d.itemId)) {
    renderStatus('<span class="stat-err">Collision — dépôt refusé</span>');
    renderAll();
    return;
  }
  if (d.itemId) {
    /* Déplacement (y compris entre baies). */
    const fromRack = project.racks.find((r) => r.id === d.fromRackId);
    const idx = fromRack.items.findIndex((i) => i.id === d.itemId);
    const [item] = fromRack.items.splice(idx, 1);
    item.position_u = u;
    rack.items.push(item);
  } else {
    /* Nouveau depuis la palette. */
    rack.items.push({
      id: nextItemId(), type_id: d.type.id, position_u: u, face: "front",
      meta: { hostname: "", role: d.type.category, vlan: "", wall_outlet: "",
              port_usage: [], serial: "", notes: "" },
    });
  }
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

async function postForBlob(url, filename) {
  const res = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    renderStatus(`<span class="stat-err">Export refusé : ${JSON.stringify(err.detail)}</span>`);
    return;
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* Les exports suivent la vue active ET le thème affiché : ce que tu
 * vois est ce que tu livres. */
function viewSuffix() {
  return { logical: "-logique", diagram: "-diagramme" }[viewMode] || "";
}
function exportQuery(view) {
  const q = new URLSearchParams();
  q.set("view", view ||
    ({ logical: "logical", diagram: "diagram" }[viewMode] || "physical"));
  q.set("theme", theme);
  q.set("rendu", renderMode);
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

/* PNG : le SVG d'export rasterisé en local (à imprimer, scotcher sur la
 * baie — la demande NetBox n°1182 jamais servie). Échelle 2x. */
$("#btn-export-png").addEventListener("click", async () => {
  const res = await fetch("/api/export/svg" + exportQuery(), {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(currentProject()),
  });
  if (!res.ok) {
    renderStatus('<span class="stat-err">Export refusé — projet invalide</span>');
    return;
  }
  const svgText = await res.text();
  const size = /viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/.exec(svgText);
  const w = size ? parseFloat(size[1]) : 1200;
  const h = size ? parseFloat(size[2]) : 900;
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
    canvas.toBlob((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = currentProject().id + viewSuffix() + ".png";
      a.click();
      URL.revokeObjectURL(a.href);
    }, "image/png");
  };
  img.onerror = () => {
    URL.revokeObjectURL(url);
    renderStatus('<span class="stat-err">Rasterisation PNG impossible</span>');
  };
  img.src = url;
});
$("#btn-export-json").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(currentProject(), null, 2)],
                       { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = currentProject().id + ".json";
  a.click();
  URL.revokeObjectURL(a.href);
});

$("#btn-import-json input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    project = data;
    if (!project.equipment_types) project.equipment_types = [];
    if (!project.logical) project.logical = { vlans: [], links: [], positions: {} };
    refreshTypes();
    renderPalette($("#palette-filter").value);
    $("#project-name").value = project.name || "Sans nom";
    closeInspector();
    renderAll();
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

async function renderLogical() {
  const res = await fetch("/api/export/svg?view=logical&theme=" + theme, {
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
  renderStatus();
  saveLocal();
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
}
$("#btn-zoom-in").addEventListener("click", () => setCanvasZoom(canvasZoom * 1.2));
$("#btn-zoom-out").addEventListener("click", () => setCanvasZoom(canvasZoom / 1.2));
$("#btn-zoom-reset").addEventListener("click", () => setCanvasZoom(1));
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
                                  ligne: "Ligne", ellipse: "Ellipse" }[a.kind], [
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
  viewMode = mode;
  document.body.dataset.view = mode;
  $("#btn-view-physical").classList.toggle("active", mode === "physical");
  $("#btn-view-logical").classList.toggle("active", mode === "logical");
  $("#btn-view-diagram").classList.toggle("active", mode === "diagram");
  closeInspector();
  renderAll();
}
$("#btn-view-physical").addEventListener("click", () => setView("physical"));
$("#btn-view-logical").addEventListener("click", () => setView("logical"));
$("#btn-view-diagram").addEventListener("click", () => setView("diagram"));

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

$("#btn-add-rack").addEventListener("click", () => {
  const letter = String.fromCharCode(65 + project.racks.length); // A, B, C…
  project.racks.push(newRack(letter));
  renderAll();
});

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
}

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
  }
  if (!project)
    project = qs.has("demo") ? demoProject() : (loadLocal() || newProject());
  if (!project.equipment_types) project.equipment_types = [];
  if (!project.logical) project.logical = { vlans: [], links: [], positions: {} };
  if (!project.diagram) project.diagram = { annotations: [] };
  document.body.dataset.view = viewMode;
  refreshTypes();
  renderPalette("");
  $("#palette-filter").addEventListener("input",
    (e) => renderPalette(e.target.value));
  $("#project-name").value = project.name;
  /* ?view=logical|diagram ouvre directement la vue voulue. */
  if (["logical", "diagram"].includes(qs.get("view"))) setView(qs.get("view"));
  else renderAll();
  renderStatus("Prêt");
})();
