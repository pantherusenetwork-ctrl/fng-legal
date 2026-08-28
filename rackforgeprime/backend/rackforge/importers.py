"""Importeurs de types d'équipements.

Deux sources externes deviennent des ``EquipmentType`` :

1. **YAML NetBox devicetype-library** (netbox-community/devicetype-library) :
   format communautaire éprouvé — manufacturer, model, slug, u_height,
   interfaces nommées. Import direct et fiable.

2. **PDF datasheet constructeur** : extraction *heuristique* du texte
   (modèle, hauteur U, conso, nombre de ports). Le résultat est une
   **proposition** que l'utilisateur valide/corrige dans l'UI avant l'ajout
   à la palette — jamais un ajout silencieux.
"""

from __future__ import annotations

import io
import math
import re

import yaml
from pypdf import PdfReader

from .models import EquipmentType, Port

# Catégorie devinée d'après des mots-clés (YAML slug/model ou texte du PDF).
_CATEGORY_HINTS: list[tuple[str, str]] = [
    (r"firewall|fortigate|palo\s*alto|asa\b|srx\b", "firewall"),
    (r"switch|catalyst|nexus|aruba\s*(cx|6\d{3}|2\d{3})|ex\d{4}|fortiswitch", "switch"),
    (r"router|isr\b|asr\b|mx\d+", "router"),
    (r"patch\s*panel|brassage", "patch-panel"),
    (r"ups|onduleur|smart-ups|battery", "ups"),
    (r"server|serveur|poweredge|proliant|thinksystem", "server"),
    (r"blank|obturateur", "blank"),
    (r"cable\s*(management|manager)|passe-c[âa]bles", "cable-mgmt"),
]


def guess_category(text: str) -> str:
    low = text.lower()
    for pattern, cat in _CATEGORY_HINTS:
        if re.search(pattern, low):
            return cat
    return "other"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "type-importe"


# ---------------------------------------------------------------------------
# 1. YAML NetBox devicetype-library
# ---------------------------------------------------------------------------

def import_netbox_yaml(text: str) -> EquipmentType:
    """Un fichier YAML devicetype -> EquipmentType.

    Lève ValueError avec un message en français si le YAML n'est pas un
    devicetype exploitable.
    """
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML illisible : {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("YAML illisible : le document n'est pas un objet")

    vendor = str(data.get("manufacturer") or "").strip()
    model = str(data.get("model") or "").strip()
    if not vendor or not model:
        raise ValueError(
            "Devicetype incomplet : « manufacturer » et « model » sont requis"
        )

    # NetBox autorise 0.5U (demi-U) ; notre snap est entier : on arrondit
    # au U supérieur (jamais en dessous de la réalité physique).
    raw_u = data.get("u_height", 1)
    try:
        u_height = max(1, math.ceil(float(raw_u)))
    except (TypeError, ValueError):
        raise ValueError(f"u_height invalide : {raw_u!r}")

    ports = [
        Port(name=str(itf.get("name", f"port{i}")),
             type=str(itf.get("type", "other")))
        for i, itf in enumerate(data.get("interfaces") or [], start=1)
        if isinstance(itf, dict)
    ]

    from .catalog import ROLE_COLORS
    category = guess_category(f"{data.get('slug', '')} {vendor} {model}")
    return EquipmentType(
        id=str(data.get("slug") or _slugify(f"{vendor}-{model}")),
        vendor=vendor, model=model, category=category,  # type: ignore[arg-type]
        u_height=u_height, ports=ports,
        color=ROLE_COLORS.get(category, "#94a3b8"),
    )


# ---------------------------------------------------------------------------
# 2. PDF datasheet — extraction heuristique, résultat = proposition
# ---------------------------------------------------------------------------

_U_PATTERNS = [
    # « 1RU », « 2 RU », « 1U rack », « hauteur : 2U »…
    re.compile(r"\b([1-9]|1[0-2])\s*R?U\b(?!\s*plink)", re.IGNORECASE),
    # « rack unit(s): 2 », « 2 rack units »
    re.compile(r"\b([1-9]|1[0-2])\s*rack\s*units?\b", re.IGNORECASE),
]
_POWER_PATTERN = re.compile(
    r"(?:max(?:imum)?|typical|typique|consommation|power\s*(?:draw|consumption))"
    r"[^\n]{0,40}?(\d{1,4}(?:[.,]\d{1,2})?)\s*W(?:att)?s?\b",
    re.IGNORECASE)
_PORTS_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(?:x\s*)?(?:RJ-?45|GE|GbE|10/100/1000|SFP\+?|ports?)\b",
    re.IGNORECASE)


def parse_datasheet_pdf(pdf_bytes: bytes, filename: str = "") -> dict:
    """PDF -> proposition de type (dict), à valider par l'utilisateur.

    Retourne ``{proposal: EquipmentType-dict, confidence: {...}}`` où
    ``confidence`` dit champ par champ si la valeur a été trouvée dans le
    texte ou seulement devinée.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        # Les infos utiles (modèle, U, conso) sont presque toujours dans les
        # premières pages ; on borne pour rester instantané sur un gros PDF.
        text = "\n".join((page.extract_text() or "")
                         for page in reader.pages[:8])
    except Exception as exc:
        raise ValueError(f"PDF illisible : {exc}") from exc
    if not text.strip():
        raise ValueError(
            "Aucun texte extractible (PDF scanné ? OCR non pris en charge "
            "pour l'instant)"
        )

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Modèle : la première ligne « titre » plausible, sinon le nom de fichier.
    model = ""
    for ln in lines[:15]:
        if 3 <= len(ln) <= 60 and re.search(r"[A-Za-z]", ln) \
                and not re.search(r"datasheet|fiche|www\.|http", ln, re.I):
            model = ln
            break
    if not model:
        model = re.sub(r"\.pdf$", "", filename, flags=re.I) or "Modèle inconnu"

    # Constructeur : premier nom connu rencontré dans le texte.
    vendors = ["Cisco", "Fortinet", "HPE", "Aruba", "Juniper", "Dell",
               "Ubiquiti", "MikroTik", "APC", "Eaton", "Netgear", "TP-Link",
               "Huawei", "Arista", "Palo Alto"]
    vendor = next((v for v in vendors
                   if re.search(rf"\b{re.escape(v)}\b", text, re.I)), "")

    u_height, u_found = 1, False
    for pat in _U_PATTERNS:
        m = pat.search(text)
        if m:
            u_height, u_found = int(m.group(1)), True
            break

    power_w, power_found = 0.0, False
    m = _POWER_PATTERN.search(text)
    if m:
        power_w, power_found = float(m.group(1).replace(",", ".")), True

    ports_count, ports_found = 0, False
    m = _PORTS_PATTERN.search(text)
    if m:
        ports_count, ports_found = min(int(m.group(1)), 96), True

    from .catalog import ROLE_COLORS
    category = guess_category(f"{filename} {text[:4000]}")
    proposal = EquipmentType(
        id=_slugify(f"{vendor}-{model}") + "-importe",
        vendor=vendor or "Inconnu", model=model,
        category=category,  # type: ignore[arg-type]
        u_height=u_height, power_w=power_w,
        ports=[Port(name=f"port{i}") for i in range(1, ports_count + 1)],
        color=ROLE_COLORS.get(category, "#94a3b8"),
    )
    return {
        "proposal": proposal.model_dump(),
        "confidence": {
            "vendor": bool(vendor), "model": bool(lines),
            "u_height": u_found, "power_w": power_found,
            "ports": ports_found, "category": category != "other",
        },
    }
