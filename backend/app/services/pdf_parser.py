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
# Détection des groupes par analyse des bordures épaisses
# ---------------------------------------------------------------------------

def _assign_groups(table_obj, page, header_idx: int) -> list:
    """
    Retourne une liste de group_id (int) pour chaque ligne de données.

    Principe :
      - Les cellules d'un même groupe sont séparées par des lignes FINES.
      - Les groupes sont séparés par des lignes ÉPAISSES.
      - On identifie les lignes épaisses via la propriété 'linewidth' des edges pdfplumber.
    """
    data_rows = table_obj.rows[header_idx + 1:]
    n = len(data_rows)

    if n == 0:
        return []

    t_bbox       = table_obj.bbox           # (x0, top, x1, bottom)
    table_top    = t_bbox[1]
    table_bottom = t_bbox[3]

    # Edges horizontaux strictement à l'intérieur du tableau (pas les bordures externes)
    h_edges = [
        e for e in page.edges
        if (e.get("orientation") == "h"
            and table_top + 2 < e.get("top", 0) < table_bottom - 2)
    ]

    if not h_edges:
        logger.debug("Aucun edge intérieur trouvé — tous les participants dans groupe 1.")
        return [1] * n

    linewidths = [e.get("linewidth", 0.5) for e in h_edges]

    if len(set(linewidths)) < 2:
        # Tous les edges ont la même épaisseur : impossible de distinguer les séparateurs.
        # Fallback : utiliser le changement de jump_type comme marqueur de groupe.
        logger.debug("Épaisseurs identiques — fallback sur changement de jump_type.")
        return _assign_groups_by_jump_type(table_obj, header_idx)

    max_lw    = max(linewidths)
    threshold = max_lw * 0.6          # lignes à ≥ 60 % de l'épaisseur max = séparateurs

    thick_tops = sorted(set(
        round(e.get("top", 0), 1)
        for e in h_edges
        if e.get("linewidth", 0.5) >= threshold
    ))

    # Assigner les groupes en parcourant les lignes du tableau
    group_id    = 1
    groups      = []
    prev_bottom = table_top

    for row in data_rows:
        row_top = row.bbox[1]
        # Une ligne épaisse entre prev_bottom et row_top → nouveau groupe
        for ty in thick_tops:
            if prev_bottom + 0.5 < ty < row_top + 0.5:
                group_id += 1
                break
        groups.append(group_id)
        prev_bottom = row.bbox[3]

    logger.debug(f"Groupes détectés : {groups}")
    return groups


def _assign_groups_by_jump_type(table_obj, header_idx: int) -> list:
    """
    Fallback : assigne les groupes en fonction des changements de 'Type saut'.
    Moins précis que la détection par bordures, mais robuste.
    """
    data_rows    = table_obj.extract()[header_idx + 1:]
    group_id     = 1
    groups       = []
    prev_jt      = None

    for row in data_rows:
        cells = [str(c or "").strip() for c in row]
        jump_type = cells[1] if len(cells) > 1 else ""
        if prev_jt is not None and jump_type != prev_jt:
            group_id += 1
        groups.append(group_id)
        prev_jt = jump_type

    return groups
