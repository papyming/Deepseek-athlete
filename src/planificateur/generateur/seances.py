# ============================================================
# FICHIER: src/planificateur/generateur/seances.py
# RÔLE: Création des séances d'entraînement
#       CORRIGÉ: Force séance qualité même avec 1-2 CAP/semaine
# ============================================================

import math
import random
from typing import Dict, List, Optional, Tuple

from ..constants_plan import (
    TYPES_SEANCES_CAP, TYPES_SEANCES_VELO, TYPES_SEANCES_NATATION,
    TYPES_RENFORCEMENT, VOLUME_MAX_PAR_SEANCE, get_difficulte
)
from ..volume import get_duree_intensite_min, ajuster_nb_rep_pour_intensite


def generer_seance_endurance(discipline: str, duree: int, zone: str = "Z2", type_seance: str = 'endurance') -> Dict:
    if discipline == 'CAP':
        type_label = TYPES_SEANCES_CAP.get(type_seance, f'Endurance {zone}')
    elif discipline == 'Vélo':
        type_label = TYPES_SEANCES_VELO.get(type_seance, f'Endurance {zone}')
    elif discipline == 'Natation':
        type_label = TYPES_SEANCES_NATATION.get(type_seance, f'Endurance {zone}')
    else:
        type_label = f'Endurance {zone}'
    
    return {
        'discipline': discipline,
        'type': type_label,
        'details': f'{type_label} ({duree} min)',
        'duree': duree,
        'difficulte': get_difficulte(type_seance)
    }


def generer_seance_renforcement(discipline: str, duree: int = 30) -> Dict:
    type_choisi = random.choice(TYPES_RENFORCEMENT)
    difficulte = get_difficulte(type_choisi.lower().replace(' ', '_'))
    return {
        'discipline': discipline,
        'type': type_choisi,
        'details': f'{type_choisi} ({duree} min)',
        'duree': duree,
        'difficulte': difficulte
    }


def generer_seance_qualite(
    seance_data: Dict,
    discipline: str,
    type_seance: str,
    semaine_num: int = 0,
    nb_semaines_total: int = 0
) -> Dict:
    distance = seance_data.get('distance_effort', seance_data.get('distance', '?'))
    vitesse_effort = seance_data.get('vitesse_effort', 0)
    temps_effort = seance_data.get('temps_effort', '00:00')
    temps_effort_sec = seance_data.get('temps_effort_sec', 0)
    nb_rep = seance_data.get('nb_rep', 4)
    distance_recup = seance_data.get('distance_recup', 0)
    temps_recup = seance_data.get('temps_recup', '00:00')
    
    # Progression sur le long terme
    if nb_semaines_total > 20 and semaine_num > 0 and type_seance != 'Test 3\'/6\'/12\'':
        progression = 1.0 + (semaine_num / nb_semaines_total) * 0.08
        vitesse_effort = vitesse_effort * progression
        if semaine_num % 4 == 0 and nb_rep < 12:
            nb_rep = nb_rep + 1
    
    nb_rep = ajuster_nb_rep_pour_intensite(
        nb_rep=nb_rep,
        temps_effort_sec=temps_effort_sec,
        temps_recup_sec=0,
        duree_cible_min=20
    )
    
    duree_intense_min = get_duree_intensite_min(nb_rep, temps_effort_sec)
    
    details = f"{type_seance} {distance}m x {nb_rep} @ {vitesse_effort:.1f} km/h"
    details += f" (effort {temps_effort}"
    if distance_recup > 0 and temps_recup != '00:00':
        details += f" / recup {distance_recup}m x {temps_recup}"
    details += ")"
    details += f" - {duree_intense_min}min d'intensité"
    
    duree_seance = int(nb_rep * (temps_effort_sec + seance_data.get('temps_recup_sec', 0)) / 60) + 15
    duree_seance = min(duree_seance, VOLUME_MAX_PAR_SEANCE.get(discipline, 120))
    
    return {
        'discipline': discipline,
        'type': type_seance,
        'details': details,
        'duree': duree_seance,
        'difficulte': get_difficulte(type_seance.lower())
    }


def generer_seance_test_3_6_12() -> Dict:
    return {
        'type': 'Test 3\'/6\'/12\'',
        'details': 'Test de Vitesse Critique: 3\'/6\'/12\' (espacer de 48h)',
        'distance': 'Test',
        'pourcentage': 0,
        'vitesse_effort': 0,
        'temps_effort': '03:00',
        'temps_effort_sec': 180,
        'nb_rep': 1,
        'distance_effort': 'Test',
        'distance_recup': 0,
        'temps_recup': '00:00',
        'temps_recup_sec': 0
    }


def choisir_seance_qualite(
    seances_vma: List[Dict],
    seances_vc: List[Dict],
    semaine_num: int,
    vma: float,
    vc: float,
    nb_seances_cap: int,
    seance_index: int,
    nb_semaines_total: int = 0
) -> Tuple[Optional[Dict], str]:
    a_vma = vma is not None and not math.isnan(vma) and vma > 0
    a_vc = vc is not None and not math.isnan(vc) and vc > 0
    
    # CORRIGÉ: Force séance qualité même avec 1-2 CAP/semaine
    # Règle: 1 séance intense toutes les 3 séances CAP
    if nb_seances_cap <= 2:
        # Une séance intense toutes les 3 semaines
        if semaine_num % 3 != 0:
            return None, 'Endurance'
    
    if not a_vma and not a_vc:
        return generer_seance_test_3_6_12(), 'Test 3\'/6\'/12\''
    
    if a_vma and a_vc:
        if semaine_num % 2 == 0:
            if seances_vma:
                idx = (semaine_num + seance_index) % len(seances_vma)
                return seances_vma[idx], 'VMA'
        else:
            if seances_vc:
                idx = (semaine_num + seance_index) % len(seances_vc)
                return seances_vc[idx], 'VC'
    
    if a_vma and seances_vma:
        idx = (semaine_num + seance_index) % len(seances_vma)
        return seances_vma[idx], 'VMA'
    
    if a_vc and seances_vc:
        idx = (semaine_num + seance_index) % len(seances_vc)
        return seances_vc[idx], 'VC'
    
    return generer_seance_test_3_6_12(), 'Test 3\'/6\'/12\''