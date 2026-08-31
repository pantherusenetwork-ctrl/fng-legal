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

/* ---- Palette de la DA (miroir de svg_export.py) ---- */
const C = {
  frame: "#1b2230", rail: "#2a3446", hole: "#0e1420", slot: "#0e131d",
  slotLine: "#1a2130", text: "#cbd5e1", dim: "#64748b", face: "#1a1f2b",
  accent: "#22d3ee", danger: "#f87171",
};

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
    ["VLAN", m.vlan],
    ["Prise murale", m.wall_outlet],
    ["N° série", m.serial],
    ["Ports brassés", (m.port_usage || []).length || ""],
  ].filter(([, v]) => v);
  return `<div class="tip-title">${esc(m.hostname || t.model)}</div>` +
    rows.map(([k, v]) => `<div class="tip-row"><span>${k}</span>${esc(v)}</div>`).join("");
}

/* Faceplate placeholder — même dessin que _faceplate_placeholder() côté Python. */
function drawFaceplate(g, t, x, y, label, selected, item) {
  const h = t.u_height * U_PX;
  if (t.faceplate_image) {
    /* Image officielle : étirée sur le slot U exact (convention TSS/NetBox),
       cadre de sélection par-dessus. */
    g.appendChild(svgEl("rect", { x, y: y + 1, width: RACK_W, height: h - 2, fill: C.face }));
    const img = svgEl("image", {
      x, y: y + 1, width: RACK_W, height: h - 2,
      preserveAspectRatio: "none", href: t.faceplate_image,
    });
    g.appendChild(img);
    /* Sur une photo officielle les ports ne sont pas localisables :
       le survol montre la fiche de l'équipement. */
    if (item) {
      img.addEventListener("mousemove", (e) => showTip(itemTipHTML(t, item), e));
      img.addEventListener("mouseleave", hideTip);
    }
    if (selected)
      g.appendChild(svgEl("rect", { x, y: y + 1, width: RACK_W, height: h - 2,
        fill: "none", stroke: C.accent, "stroke-width": 1.6 }));
    return;
  }
  const yc = y + h / 2;
  /* Corps plat teinté par rôle — style PATCHBOX/Lucid (miroir Python). */
  g.appendChild(svgEl("rect", {
    x, y: y + 1, width: RACK_W, height: h - 2, rx: 3, fill: C.face,
    stroke: selected ? C.accent : "#2c3547", "stroke-width": selected ? 1.6 : 1,
  }));
  g.appendChild(svgEl("rect", {
    x, y: y + 1, width: RACK_W, height: h - 2, rx: 3,
    fill: t.color, "fill-opacity": 0.07,
  }));
  g.appendChild(svgEl("rect", { x, y: y + 1, width: 4, height: h - 2, fill: t.color }));
  g.appendChild(svgEl("text", {
    x: x + 14, y: yc + 4, "font-size": 11, fill: C.text,
    "font-family": "system-ui, sans-serif",
  }, label));
  /* Pastille de hauteur U. */
  g.appendChild(svgEl("rect", {
    x: x + RACK_W - 34, y: yc - 7, width: 26, height: 14, rx: 7,
    fill: "none", stroke: "#33405a", "stroke-width": 1,
  }));
  g.appendChild(svgEl("text", {
    x: x + RACK_W - 21, y: yc + 3, "text-anchor": "middle",
    "font-size": 8.5, fill: C.dim, "font-family": "monospace",
  }, t.u_height + "U"));
  /* Serveur / onduleur / passe-câbles : la silhouette prime sur les
     quelques ports de management (miroir Python). */
  if (["server", "ups", "cable-mgmt"].includes(t.category))
    drawCategoryDecor(g, t, x, y, RACK_W, h);
  else if ((t.ports || []).length)
    drawPortBanks(g, t, item, x, y, RACK_W, h);
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
    g.appendChild(svgEl("rect", {
      x: px, y: py, width: pw, height: ph, rx: 1,
      fill: "#0a0e16", stroke: color, "stroke-width": 0.7,
    }));
    g.appendChild(svgEl("rect", {
      x: px + 2, y: py + ph - 1.6, width: 3, height: 1.6,
      fill: color, "fill-opacity": 0.85,
    }));
    /* Zone de survol invisible, plus large que le port dessiné. */
    const port = t.ports[i];
    const hit = svgEl("rect", {
      x: px - 1, y: py - 2, width: pw + 3, height: ph + 5,
      fill: "transparent", class: "port-hit",
    });
    hit.addEventListener("mousemove", (e) => showTip(portTipHTML(t, item, port), e));
    hit.addEventListener("mouseleave", hideTip);
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
        fill: "#10151f", stroke: "#2c3547", "stroke-width": 0.7,
      }));
      g.appendChild(svgEl("circle", {
        cx: bx + bw / 2, cy: y + 7, r: 1.3, fill: t.color,
      }));
    }
  } else if (t.category === "ups") {
    g.appendChild(svgEl("rect", {
      x: x + w - 200, y: y + h / 2 - 8, width: 30, height: 16, rx: 2,
      fill: "#0a2027", stroke: t.color, "stroke-width": 0.8,
    }));
    for (let i = 0; i < 24; i++)
      g.appendChild(svgEl("rect", {
        x: x + w - 155 + i * 5, y: y + h / 2 - 6, width: 2, height: 12,
        rx: 1, fill: "#10151f",
      }));
  } else if (t.category === "cable-mgmt") {
    for (let i = 0; i < 4; i++)
      g.appendChild(svgEl("rect", {
        x: x + 200 + i * 50, y: y + 3, width: 30, height: h - 6, rx: 4,
        fill: "none", stroke: "#3a465c", "stroke-width": 2,
      }));
  }
}

function renderRackSVG(rack) {
  const { w, h } = rackSize(rack);
  const innerX = FRAME_PAD + RAIL_W;
  const svg = svgEl("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}` });
  svg.dataset.rackId = rack.id;

  svg.appendChild(svgEl("rect", { x: 0, y: 0, width: w, height: h, rx: 6,
    fill: C.frame, stroke: "#2c3547", "stroke-width": 1.5 }));
  svg.appendChild(svgEl("text", { x: w / 2, y: 24, "text-anchor": "middle",
    "font-size": 15, "font-weight": "bold", fill: C.text }, rack.name));

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
          "text-anchor": "middle", "font-size": 8, fill: C.dim,
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
      rx: 2, class: "slot-free", fill: "transparent",
    });
    slot.addEventListener("click", (e) => openSlotPopover(e, rack, u));
    svg.appendChild(slot);
  }

  /* Stats de la baie. */
  const st = rackStats(rack);
  svg.appendChild(svgEl("text", { x: w / 2, y: h - FOOTER_H / 2, "text-anchor": "middle",
    "font-size": 10, fill: C.accent, "font-family": "monospace" },
    `${st.used}U occupés · ${st.free}U libres · ${st.power} W`));

  return svg;
}

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
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  for (const rack of project.racks) canvas.appendChild(renderRackSVG(rack));
  renderStatus();
  saveLocal();
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

function renderPalette(filter) {
  const wrap = $("#palette-groups");
  wrap.innerHTML = "";
  const f = (filter || "").toLowerCase();
  for (const [cat, label] of Object.entries(CATEGORY_LABELS)) {
    const types = allTypes().filter((t) =>
      t.category === cat &&
      (!f || `${t.vendor} ${t.model}`.toLowerCase().includes(f)));
    if (!types.length) continue;
    const title = document.createElement("div");
    title.className = "palette-group-title";
    title.innerHTML = `<span class="role-dot" style="background:${catalog.role_colors[cat] || "#666"}"></span>${label}`;
    wrap.appendChild(title);
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
    const y = e.clientY - r.top;
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
    fill: ok ? "rgba(34,211,238,.12)" : "rgba(248,113,113,.15)",
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

  /* Simple clic sur un item posé (pas de mouvement) = ouverture inspecteur. */
  if (d.itemId && !d.moved) { selectItem(d.itemId); return; }

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
  for (const k of ["hostname", "role", "vlan", "wall_outlet", "serial", "notes"])
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

/* Les exports suivent la vue active : baies en physique, VLANs/liens en logique. */
function viewSuffix() { return viewMode === "logical" ? "-logique" : ""; }
function viewQuery() { return viewMode === "logical" ? "?view=logical" : ""; }

$("#btn-export-svg").addEventListener("click", () =>
  postForBlob("/api/export/svg" + viewQuery(),
              currentProject().id + viewSuffix() + ".svg"));
$("#btn-export-pdf").addEventListener("click", () =>
  postForBlob("/api/export/pdf" + viewQuery(),
              currentProject().id + viewSuffix() + ".pdf"));
$("#btn-export-dossier").addEventListener("click", () =>
  postForBlob("/api/export/pdf?view=dossier",
              currentProject().id + "-dossier.pdf"));
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
  const res = await fetch("/api/export/svg?view=logical", {
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

function wireLogical(svg) {
  if (!svg) return;
  /* Drag des nœuds : delta appliqué en transform pendant le geste,
     position persistée dans project.logical.positions au relâcher. */
  svg.querySelectorAll('g[id^="lnode-"]').forEach((g) => {
    const eqId = g.id.slice("lnode-".length);
    const rect = g.querySelector("rect");
    const ox = parseFloat(rect.getAttribute("x"));
    const oy = parseFloat(rect.getAttribute("y"));
    g.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      const sx = e.clientX, sy = e.clientY;
      let dx = 0, dy = 0;
      const move = (ev) => {
        dx = ev.clientX - sx; dy = ev.clientY - sy;
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
  /* Clic sur un lien : édition / suppression. */
  svg.querySelectorAll('g[id^="link-"]').forEach((g) => {
    const linkId = g.id.slice("link-".length);
    g.addEventListener("click", () => {
      const link = project.logical.links.find((l) => l.id === linkId);
      if (link) openLinkDialog(link);
    });
  });
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
  closeInspector();
  renderAll();
}
$("#btn-view-physical").addEventListener("click", () => setView("physical"));
$("#btn-view-logical").addEventListener("click", () => setView("logical"));

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
    const head = ["Baie", "U", "Équipement", "Port", "Prise", "VLAN", "Usage"];
    wrap.innerHTML = "<table><thead><tr>" +
      head.map((h) => `<th>${h}</th>`).join("") + "</tr></thead><tbody>" +
      (rows.length ? rows.map((r) =>
        `<tr><td>${r.rack}</td><td>U${r.u}</td><td>${r.equipment}</td>` +
        `<td>${r.port}</td><td>${r.outlet}</td><td>${r.vlan}</td><td>${r.usage}</td></tr>`
      ).join("") : '<tr><td colspan="7">Aucun équipement.</td></tr>') +
      "</tbody></table>";
  }
  $("#patch-dialog").showModal();
});
$("#btn-close-patch").addEventListener("click", () => $("#patch-dialog").close());
$("#btn-export-csv").addEventListener("click", () =>
  postForBlob("/api/patch-table.csv", currentProject().id + "-brassage.csv"));

/* ---- Sauvegarde de secours (localStorage) ---- */
function saveLocal() {
  try { localStorage.setItem("rackforgeprime.project", JSON.stringify(project)); }
  catch { /* stockage plein ou bloqué : non bloquant */ }
}
function loadLocal() {
  try {
    const raw = localStorage.getItem("rackforgeprime.project");
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

/* =====================================================================
 * Démarrage
 * =================================================================== */

(async function init() {
  const res = await fetch("/api/catalog");
  catalog = await res.json();
  project = loadLocal() || newProject();
  if (!project.equipment_types) project.equipment_types = [];
  if (!project.logical) project.logical = { vlans: [], links: [], positions: {} };
  document.body.dataset.view = viewMode;
  refreshTypes();
  renderPalette("");
  $("#palette-filter").addEventListener("input",
    (e) => renderPalette(e.target.value));
  $("#project-name").value = project.name;
  renderAll();
  renderStatus("Prêt");
})();
