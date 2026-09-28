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
    TYPES_RENFORCEMENT, VOLUME_MAX_PAR_SEANCE, get_difficulte,
    normalize_discipline_name
)
from ..volume import get_duree_intensite_min, ajuster_nb_rep_pour_intensite

# Classification des intensités CAP pour l'alternance COURTE / LONGUE.
CATEGORIE_COURTE = 'COURTE'
CATEGORIE_LONGUE = 'LONGUE'
_SEUIL_DISTANCE_COURTE_M = 400
_SEUIL_DUREE_LONGUE_SEC = 180  # 3 minutes
_MARQUEURS_COURTS = ('sprint', '30"', "30''", '30/30', '30-30')


def classer_intensite_cap(seance_data: Dict) -> str:
    """Classe une séance d'intensité CAP en COURTE ou LONGUE.

    Règle métier (aucune équivalence durée <-> distance) :
    - distance <= 400 m (sprint, 30"/30", 200 m, 300 m, 400 m) -> COURTE ;
    - distance > 400 m -> LONGUE ;
    - sans distance chiffrée : effort > 3 min -> LONGUE, sinon COURTE.

    Le 400 m reste COURTE même si l'athlète met plus de 3 minutes.
    La récupération n'intervient jamais dans la classification.
    """
    distance = seance_data.get('distance_effort', seance_data.get('distance'))
    try:
        distance_num = float(distance)
    except (TypeError, ValueError):
        distance_num = None
    if distance_num is not None:
        return CATEGORIE_COURTE if distance_num <= _SEUIL_DISTANCE_COURTE_M else CATEGORIE_LONGUE

    texte = f"{seance_data.get('type', '')} {seance_data.get('details', '')}".lower()
    if any(marqueur in texte for marqueur in _MARQUEURS_COURTS):
        return CATEGORIE_COURTE

    temps_effort_sec = seance_data.get('temps_effort_sec')
    try:
        temps_effort_sec = float(temps_effort_sec)
    except (TypeError, ValueError):
        temps_effort_sec = None
    if temps_effort_sec is not None and temps_effort_sec > _SEUIL_DUREE_LONGUE_SEC:
        return CATEGORIE_LONGUE
    return CATEGORIE_COURTE


def generer_seance_endurance(discipline: str, duree: int, zone: str = "Z2", type_seance: str = 'endurance') -> Dict:
    discipline = normalize_discipline_name(discipline)
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
        'difficulte': get_difficulte(type_seance),
        'cle': False
    }


def generer_seance_renforcement(discipline: str, duree: int = 30) -> Dict:
    type_choisi = random.choice(TYPES_RENFORCEMENT)
    difficulte = get_difficulte(type_choisi.lower().replace(' ', '_'))
    return {
        'discipline': discipline,
        'type': type_choisi,
        'details': f'{type_choisi} ({duree} min)',
        'duree': duree,
        'difficulte': difficulte,
        'cle': False
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
        'difficulte': get_difficulte(type_seance.lower()),
        'cle': True,
        'categorie_intensite': seance_data.get('categorie_intensite'),
        'alternance_impossible': bool(seance_data.get('alternance_impossible', False)),
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


def _candidat_alterne(liste: List[Dict], index: int,
                      categorie_precedente: str) -> Optional[Dict]:
    """Cherche dans ``liste`` un candidat de catégorie différente (rotation)."""
    if not liste:
        return None
    for decalage in range(1, len(liste) + 1):
        candidat = liste[(index + decalage) % len(liste)]
        if classer_intensite_cap(candidat) != categorie_precedente:
            return candidat
    return None


def choisir_seance_qualite(
    seances_vma: List[Dict],
    seances_vc: List[Dict],
    semaine_num: int,
    vma: float,
    vc: float,
    nb_seances_cap: int,
    seance_index: int,
    nb_semaines_total: int = 0,
    derniere_categorie: Optional[str] = None
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

    # Choix de la référence (VMA/VC) selon la périodisation existante.
    type_seance = None
    liste = None
    if a_vma and a_vc:
        if semaine_num % 2 == 0 and seances_vma:
            type_seance, liste = 'VMA', seances_vma
        elif seances_vc:
            type_seance, liste = 'VC', seances_vc
    if liste is None and a_vma and seances_vma:
        type_seance, liste = 'VMA', seances_vma
    if liste is None and a_vc and seances_vc:
        type_seance, liste = 'VC', seances_vc
    if liste is None:
        return generer_seance_test_3_6_12(), 'Test 3\'/6\'/12\''

    index = (semaine_num + seance_index) % len(liste)
    candidat = liste[index]
    alternance_impossible = False

    # Alternance COURTE / LONGUE des intensités CAP successives.
    if derniere_categorie and classer_intensite_cap(candidat) == derniere_categorie:
        alternative = _candidat_alterne(liste, index, derniere_categorie)
        if alternative is not None:
            candidat = alternative
        else:
            # Aucune alternative dans la liste de référence : on tente l'autre.
            autre_liste = seances_vc if liste is seances_vma else seances_vma
            autre_type = 'VC' if liste is seances_vma else 'VMA'
            alternative = _candidat_alterne(autre_liste, 0, derniere_categorie)
            if alternative is not None:
                candidat, type_seance = alternative, autre_type
            else:
                alternance_impossible = True

    candidat = dict(candidat)
    candidat['categorie_intensite'] = classer_intensite_cap(candidat)
    candidat['alternance_impossible'] = alternance_impossible
    return candidat, type_seance