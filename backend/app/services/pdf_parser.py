import logging
import re
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
    Cherche le tableau qui contient 'AVION' et 'PILOTE' dans son en-tête,
    puis lit la ligne de données suivante.
    """
    for table in page.extract_tables():
        for i, row in enumerate(table):
            cells = [str(c or "").strip() for c in row]
            if any("AVION" in c for c in cells) and any("PILOTE" in c for c in cells):
                if i + 1 < len(table):
                    data = [str(c or "").strip() for c in table[i + 1]]
                    while len(data) < 4:
                        data.append("")
                    return {
                        "plane_registration": data[1] or None,
                        "pilot":              data[2] or None,
                        "chef_avion":         data[3] or None,
                    }
    return {"plane_registration": None, "pilot": None, "chef_avion": None}


# ---------------------------------------------------------------------------
# Tableau des participants
# ---------------------------------------------------------------------------

def _parse_participants(page) -> list:
    """
    Trouve le tableau des participants (celui avec l'en-tête 'Haut.'),
    extrait chaque ligne et assigne les groupes via détection des bordures épaisses.
    """
    # Trouver le bon tableau
    participant_table_obj = None
    header_idx = 0

    for t_obj in page.find_tables():
        rows = t_obj.extract()
        for i, row in enumerate(rows[:3]):
            cells = [str(c or "").strip() for c in row]
            if any("Haut" in c for c in cells):
                participant_table_obj = t_obj
                header_idx = i
                break
        if participant_table_obj:
            break

    if not participant_table_obj:
        logger.warning("Tableau des participants introuvable.")
        return []

    all_rows   = participant_table_obj.extract()
    data_rows  = all_rows[header_idx + 1:]
    groups     = _assign_groups(participant_table_obj, page, header_idx)

    participants = []

    for i, row in enumerate(data_rows):
        cells = [str(c or "").strip() for c in row]

        if not any(cells):
            continue

        # col[0]=Haut  col[1]=Type saut  col[2]=Sautant  col[3]=Couleur  col[4]=Poids ...
        if len(cells) < 3:
            continue

        altitude_str = cells[0]
        if not altitude_str.isdigit():
            continue                            # ignore les lignes non-participant

        jump_type = cells[1] if len(cells) > 1 else ""
        name_raw  = cells[2] if len(cells) > 2 else ""

        if not name_raw:
            continue

        # Chercher le poids dans les cellules suivantes
        weight = None
        for cell in cells[3:]:
            m = RE_WEIGHT.search(cell)
            if m:
                w = int(m.group(1))
                if 30 <= w <= 200:
                    weight = w
                    break

        last_name, first_name, level = _parse_name_level(name_raw)

        if not last_name:
            continue

        participants.append({
            "last_name":   last_name,
            "first_name":  first_name,
            "afifly_name": f"{last_name} {first_name}".strip(),
            "level":       level,
            "weight":      weight,
            "jump_type":   jump_type,
            "group_id":    groups[i] if i < len(groups) else 1,
        })

    return participants


# ---------------------------------------------------------------------------
# Parsing du nom / niveau
# ---------------------------------------------------------------------------

def _parse_name_level(raw: str) -> tuple:
    """
    Parse 'NOM Prenom (NIVEAU)' → (nom, prenom, niveau).

    Exemples :
        "SASSI Arifa"              → ("SASSI",    "Arifa",           None)
        "ALZIARY Benoit (C)"       → ("ALZIARY",  "Benoit",          "C")
        "DE ROY Hubert-arnaud (BPA)" → ("DE ROY", "Hubert-arnaud",   "BPA")
    """
    # Supprimer les symboles de chef avion (◆ ♦ ● ◉)
    raw = re.sub(r'[◆♦●◉]', '', raw).strip()

    level = None
    m = RE_LEVEL.search(raw)
    if m:
        level = m.group(1)
        raw = raw[:m.start()].strip()

    words      = raw.split()
    last_parts = []
    first_parts= []
    in_last    = True

    for word in words:
        if in_last and RE_UPPER.match(word):
            last_parts.append(word)
        else:
            in_last = False
            first_parts.append(word)

    return " ".join(last_parts), " ".join(first_parts), level


# ---------------------------------------------------------------------------
# Détection des groupes par encadrements (rectangles visuels du PDF)
# ---------------------------------------------------------------------------

def _assign_groups(table_obj, page, header_idx: int) -> list:
    """
    Retourne une liste de group_id (int) pour chaque ligne de données.

    Stratégie (3 niveaux de fallback) :
      1. Rectangles (page.rects) : chaque encadrement visuel = un groupe.
         C'est la méthode la plus fidèle au PDF Afifly.
      2. Bordures épaisses (page.edges) : si les groupes ne sont pas des
         rectangles distincts mais une table continue avec lignes épaisses.
      3. Aucun groupe détecté → group_id = 1 pour tous.
    """
    data_rows = table_obj.rows[header_idx + 1:]
    n = len(data_rows)

    if n == 0:
        return []

    t_bbox       = table_obj.bbox
    table_top    = t_bbox[1]
    table_bottom = t_bbox[3]

    # --- Méthode 1 : rectangles ---
    groups = _assign_groups_by_rects(data_rows, page, table_top, table_bottom)
    if groups and len(set(groups)) > 1:
        logger.debug(f"Groupes via rectangles : {groups}")
        return groups

    # --- Méthode 2 : bordures épaisses ---
    groups = _assign_groups_by_thick_edges(data_rows, page, table_top, table_bottom)
    if groups and len(set(groups)) > 1:
        logger.debug(f"Groupes via bordures épaisses : {groups}")
        return groups

    # --- Fallback : un seul groupe ---
    logger.warning("Impossible de détecter les groupes — tous assignés au groupe 1.")
    return [1] * n


def _assign_groups_by_rects(data_rows, page, table_top: float, table_bottom: float) -> list:
    """
    Méthode 1 : chaque encadrement visible dans la zone du tableau = un groupe.

    Dans le PDF Afifly, chaque groupe de formation est délimité par un
    rectangle visuel (encadrement). On trouve ces rectangles via page.rects,
    on les trie par position verticale, et on assigne chaque ligne au
    rectangle qui la contient.
    """
    # Rectangles dans la zone du tableau, suffisamment larges pour être des encadrements
    rects = [
        r for r in page.rects
        if (table_top - 2 <= r["top"] <= table_bottom + 2
            and r["width"] > 100)           # ignorer les petits rectangles décoratifs
    ]

    if not rects:
        return []

    # Trier par position verticale (du haut vers le bas)
    rects_sorted = sorted(rects, key=lambda r: r["top"])

    groups = []
    for row in data_rows:
        row_center = (row.bbox[1] + row.bbox[3]) / 2
        group_id = 1
        for i, rect in enumerate(rects_sorted):
            if rect["top"] - 1 <= row_center <= rect["bottom"] + 1:
                group_id = i + 1
                break
        groups.append(group_id)

    return groups


def _assign_groups_by_thick_edges(data_rows, page, table_top: float, table_bottom: float) -> list:
    """
    Méthode 2 : dans une table continue, les lignes épaisses marquent
    les séparations entre groupes.
    """
    h_edges = [
        e for e in page.edges
        if (e.get("orientation") == "h"
            and table_top + 2 < e.get("top", 0) < table_bottom - 2)
    ]

    if not h_edges:
        return []

    linewidths = [e.get("linewidth", 0.5) for e in h_edges]
    if len(set(linewidths)) < 2:
        return []

    max_lw    = max(linewidths)
    threshold = max_lw * 0.6

    thick_tops = sorted(set(
        round(e.get("top", 0), 1)
        for e in h_edges
        if e.get("linewidth", 0.5) >= threshold
    ))

    group_id    = 1
    groups      = []
    prev_bottom = table_top

    for row in data_rows:
        row_top = row.bbox[1]
        for ty in thick_tops:
            if prev_bottom + 0.5 < ty < row_top + 0.5:
                group_id += 1
                break
        groups.append(group_id)
        prev_bottom = row.bbox[3]

    return groups
