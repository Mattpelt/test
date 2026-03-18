import logging
import re
from collections import defaultdict
from datetime import date, time

import pdfplumber

logger = logging.getLogger(__name__)

# --- Regex ---
RE_ROT    = re.compile(r'Rot\s+n[°o](\d+)\s*\((\d+)\s+du\s+jour\)', re.IGNORECASE)
RE_DATE   = re.compile(r'Date\s*:\s*(\d{2})-(\d{2})-(\d{4})')
RE_TIME   = re.compile(r'Heure\s*:\s*(\d{2}):(\d{2})')
RE_WEIGHT = re.compile(r'\b(\d{2,3})\s*kg\b', re.IGNORECASE)
RE_LEVEL  = re.compile(r'\(([A-Z]{1,3})\)\s*$')
RE_UPPER  = re.compile(r'^[A-ZÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ][A-ZÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ\-]*$')

# Limites des colonnes du tableau participants (points PDF, mesurées sur les edges)
COL_HAUT_MAX  = 57    # Haut.      : x < 57
COL_TYPE_MAX  = 165   # Type saut  : 57 ≤ x < 165
COL_SAUT_MIN  = 207   # Sautant    : 207 ≤ x < 315
COL_SAUT_MAX  = 315
COL_COUL_MAX  = 395   # Couleur    : 315 ≤ x < 395
COL_POIDS_MAX = 423   # Poids      : 395 ≤ x < 423


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def parse_afifly_pdf(pdf_path: str) -> dict:
    """
    Parse un PDF Afifly et retourne un dict structuré :
    {
        rot_number, day_number, rot_date, rot_time,
        plane_registration, pilot, chef_avion,
        source_pdf_path,
        participants: [
            { last_name, first_name, afifly_name, level, weight, jump_type, group_id },
            ...
        ]
    }
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""

        result = _parse_header(text)
        result.update(_parse_crew(page))
        result["participants"]    = _parse_participants(page)
        result["source_pdf_path"] = pdf_path

        return result


# ---------------------------------------------------------------------------
# En-tête (rot_number, day_number, date, heure)
# ---------------------------------------------------------------------------

def _parse_header(text: str) -> dict:
    result = {}

    m = RE_ROT.search(text)
    if not m:
        raise ValueError("Numéro de rot introuvable dans le PDF.")
    result["rot_number"] = int(m.group(1))
    result["day_number"] = int(m.group(2))

    m = RE_DATE.search(text)
    if m:
        result["rot_date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    m = RE_TIME.search(text)
    if m:
        result["rot_time"] = time(int(m.group(1)), int(m.group(2)))

    return result


# ---------------------------------------------------------------------------
# Tableau d'équipage (avion, pilote, chef avion)
# ---------------------------------------------------------------------------

def _parse_crew(page) -> dict:
    """
    Cherche le tableau contenant 'AVION' et 'PILOTE' dans son en-tête.
    Utilise les noms de colonnes (pas les indices) pour être robuste.
    """
    for table in page.extract_tables():
        for i, row in enumerate(table):
            cells = [str(c or "").strip() for c in row]
            if any("AVION" in c for c in cells) and any("PILOTE" in c for c in cells):
                avion_idx  = next((j for j, c in enumerate(cells) if c == "AVION"), None)
                pilote_idx = next((j for j, c in enumerate(cells) if c == "PILOTE"), None)
                chef_idx   = next((j for j, c in enumerate(cells) if "CHEF" in c), None)

                if i + 1 < len(table):
                    data = [str(c or "").strip() for c in table[i + 1]]
                    return {
                        "plane_registration": data[avion_idx]  if avion_idx  is not None and avion_idx  < len(data) else None,
                        "pilot":              data[pilote_idx] if pilote_idx is not None and pilote_idx < len(data) else None,
                        "chef_avion":         data[chef_idx]   if chef_idx   is not None and chef_idx   < len(data) else None,
                    }

    return {"plane_registration": None, "pilot": None, "chef_avion": None}


# ---------------------------------------------------------------------------
# Tableau des participants — extraction par positions de mots
# ---------------------------------------------------------------------------

def _parse_participants(page) -> list:
    """
    Extrait les participants via extract_words() + positions x/y.

    Stratégie :
      1. Localiser l'en-tête "Haut." pour connaître le début du tableau.
      2. Détecter les séparateurs de groupes (doubles-lignes horizontales).
      3. Grouper les mots par ligne (tolérance 3pt sur y).
      4. Pour chaque ligne avec une altitude en col[0], extraire les champs.
    """
    all_words = page.extract_words()

    # --- 1. Trouver le début et la fin du tableau participants ---
    header_top   = None
    table_bottom = page.height - 30   # fallback

    for w in all_words:
        if "Haut" in w["text"] and w["x0"] < COL_HAUT_MAX + 5:
            header_top = w["top"]
        if header_top and w["text"] in ("Afifly", "TCPDF", "Powered") and w["top"] > header_top + 50:
            table_bottom = w["top"] - 5
            break

    if header_top is None:
        logger.warning("En-tête 'Haut.' introuvable dans le PDF.")
        return []

    logger.debug(f"Tableau participants : top={header_top:.1f}, bottom={table_bottom:.1f}")

    # --- 2. Détecter les séparateurs de groupes (doubles-lignes) ---
    separator_bottoms = _find_group_separator_bottoms(page, header_top, table_bottom)
    logger.debug(f"Séparateurs de groupes : {separator_bottoms}")

    def get_group_id(row_top: float) -> int:
        gid = 1
        for sb in separator_bottoms:
            if row_top > sb:
                gid += 1
        return gid

    # --- 3. Grouper les mots en lignes ---
    rows_dict: dict[int, list] = defaultdict(list)
    for w in all_words:
        if w["top"] <= header_top:
            continue
        if w["top"] >= table_bottom:
            continue
        row_key = round(w["top"] / 3) * 3   # tolérance 3pt
        rows_dict[row_key].append(w)

    # --- 4. Parser chaque ligne participant ---
    participants = []

    for row_key in sorted(rows_dict.keys()):
        words = rows_dict[row_key]

        # La colonne Haut. doit contenir un entier (altitude ex: 4000)
        altitude_words = [w for w in words if w["text"].isdigit() and w["x0"] < COL_HAUT_MAX]
        if not altitude_words:
            continue

        # Type de saut : COL_HAUT_MAX < x < COL_TYPE_MAX
        type_words = sorted(
            [w for w in words if COL_HAUT_MAX < w["x0"] < COL_TYPE_MAX],
            key=lambda w: w["x0"],
        )
        jump_type = " ".join(w["text"] for w in type_words)

        # Sautant : COL_SAUT_MIN ≤ x < COL_SAUT_MAX
        name_words = sorted(
            [w for w in words if COL_SAUT_MIN <= w["x0"] < COL_SAUT_MAX],
            key=lambda w: w["x0"],
        )
        name_raw = " ".join(w["text"] for w in name_words)
        if not name_raw:
            continue

        # Poids : COL_COUL_MAX < x < COL_POIDS_MAX
        weight = None
        for w in words:
            if COL_COUL_MAX < w["x0"] < COL_POIDS_MAX:
                m = RE_WEIGHT.search(w["text"])
                if m:
                    v = int(m.group(1))
                    if 30 <= v <= 200:
                        weight = v
                        break

        last_name, first_name, level = _parse_name_level(name_raw)
        if not last_name:
            continue

        row_top  = min(w["top"] for w in words)
        group_id = get_group_id(row_top)

        participants.append({
            "last_name":   last_name,
            "first_name":  first_name,
            "afifly_name": f"{last_name} {first_name}".strip(),
            "level":       level,
            "weight":      weight,
            "jump_type":   jump_type,
            "group_id":    group_id,
        })

    return participants


# ---------------------------------------------------------------------------
# Détection des groupes par doubles-lignes horizontales
# ---------------------------------------------------------------------------

def _find_group_separator_bottoms(page, table_top: float, table_bottom: float) -> list:
    """
    Dans les PDFs Afifly, chaque groupe est séparé par une PAIRE de lignes
    horizontales très proches (~5.7pt d'écart).
    Une ligne seule = en-tête ou pied de tableau.

    Retourne les y-positions du bas de chaque paire (= frontière basse du séparateur).
    Un participant est dans le groupe N si son top est supérieur à N-1 de ces y-positions.
    """
    h_edges = [
        e for e in page.edges
        if (e.get("orientation") == "h"
            and e.get("linewidth", 0) > 0
            and table_top < e.get("top", 0) < table_bottom)
    ]

    # Dédupliquer les positions quasi-identiques (même ligne vue plusieurs fois)
    unique_tops = []
    for e in sorted(h_edges, key=lambda e: e["top"]):
        t = round(e["top"], 1)
        if not unique_tops or t - unique_tops[-1] > 0.5:
            unique_tops.append(t)

    # Repérer les paires (gap ≤ 6.5pt entre deux lignes consécutives = double-ligne)
    separator_bottoms = []
    i = 0
    while i < len(unique_tops) - 1:
        gap = unique_tops[i + 1] - unique_tops[i]
        if gap <= 6.5:
            separator_bottoms.append(unique_tops[i + 1])  # y du bas de la paire
            i += 2
        else:
            i += 1  # ligne seule : en-tête ou pied
    return separator_bottoms


# ---------------------------------------------------------------------------
# Parsing du nom / niveau
# ---------------------------------------------------------------------------

def _parse_name_level(raw: str) -> tuple:
    """
    Parse 'NOM Prenom (NIVEAU)' → (nom, prenom, niveau).

    Exemples :
        "SASSI Arifa"                → ("SASSI",    "Arifa",           None)
        "ALZIARY Benoit (C)"         → ("ALZIARY",  "Benoit",          "C")
        "DE ROY Hubert-arnaud (BPA)" → ("DE ROY",   "Hubert-arnaud",   "BPA")
    """
    raw = re.sub(r'[◆♦●◉]', '', raw).strip()

    level = None
    m = RE_LEVEL.search(raw)
    if m:
        level = m.group(1)
        raw   = raw[:m.start()].strip()

    words       = raw.split()
    last_parts  = []
    first_parts = []
    in_last     = True

    for word in words:
        if in_last and RE_UPPER.match(word):
            last_parts.append(word)
        else:
            in_last = False
            first_parts.append(word)

    return " ".join(last_parts), " ".join(first_parts), level
