# ============================================================
# FICHIER: src/planificateur/volume.py
# RÔLE: Calculs de volume hebdomadaire par discipline
#       CORRIGÉ: Prise en compte du sport principal
# ============================================================

import math
from typing import Dict, List

from .constants_plan import VOLUME_MAX_PAR_SEANCE, UNITE_DUREE_PAR_HEURE, get_sport_ponderation
from .periodisation import get_volume_coeff


def unites_depuis_minutes(discipline: str, minutes: float) -> float:
    """Convertit une durée en minutes en unités de temps d'entraînement.

    Équivalence : 1 h CAP = 1 h Natation = 2 h Vélo = 1 unité.
    """
    if minutes is None:
        return 0.0
    cle = 'Velo' if discipline in ('Velo', 'Vélo') else discipline
    coefficient = UNITE_DUREE_PAR_HEURE.get(cle)
    if coefficient is None:
        return 0.0
    return (float(minutes) / 60.0) * coefficient


def calculer_unites_hebdo(volumes: Dict[str, int]) -> Dict[str, float]:
    """Convertit des volumes hebdomadaires (minutes par discipline) en unités de temps."""
    return {
        discipline: round(unites_depuis_minutes(discipline, minutes), 4)
        for discipline, minutes in volumes.items()
    }


def total_unites_hebdo(volumes: Dict[str, int]) -> float:
    """Somme des unités de temps d'une semaine, toutes disciplines confondues."""
    return round(sum(unites_depuis_minutes(discipline, minutes) for discipline, minutes in volumes.items()), 4)


def calculer_volume_hebdo(
    jours_dispos: Dict[str, List[str]],
    niveau: str,
    objectif: str,
    semaine_type: str,
    phase: str,
    semaine_num: int = 0,
    sport_principal: str = 'Triathlon'
) -> Dict[str, int]:
    """
    Calcule le volume hebdomadaire cible par discipline.
    CORRIGÉ: Pondération selon le sport principal.
    """
    # Volume de base par séance
    duree_base = {
        'CAP': 45,
        'Velo': 90,
        'Natation': 45
    }
    
    # Coefficient de niveau
    coeff_niveau = {
        'Débutant': 0.8,
        'Intermédiaire': 1.0,
        'Avancé': 1.2
    }.get(niveau, 1.0)
    
    # Coefficient d'objectif (basé sur le format de compétition)
    coeff_objectif = {
        'sprint': {'CAP': 1.2, 'Velo': 0.7, 'Natation': 0.9},
        'olympique': {'CAP': 1.0, 'Velo': 1.0, 'Natation': 1.0},
        'ironman': {'CAP': 1.0, 'Velo': 1.5, 'Natation': 1.0},
        'longue_distance': {'CAP': 1.0, 'Velo': 1.5, 'Natation': 1.0},
        'swimrun': {'CAP': 1.2, 'Velo': 0.0, 'Natation': 1.2},
        'triathlon': {'CAP': 1.0, 'Velo': 1.2, 'Natation': 1.0},
        'cap': {'CAP': 1.2, 'Velo': 0.0, 'Natation': 0.0},
        'velo': {'CAP': 0.0, 'Velo': 1.5, 'Natation': 0.0},
        'natation': {'CAP': 0.0, 'Velo': 0.0, 'Natation': 1.5}
    }
    
    obj_type = 'olympique'
    obj_lower = objectif.lower()
    if 'sprint' in obj_lower:
        obj_type = 'sprint'
    elif 'ironman' in obj_lower or 'longue' in obj_lower:
        obj_type = 'ironman'
    elif 'swimrun' in obj_lower:
        obj_type = 'swimrun'
    elif 'triathlon' in obj_lower:
        obj_type = 'triathlon'
    elif 'cap' in obj_lower or 'course' in obj_lower:
        obj_type = 'cap'
    elif 'velo' in obj_lower or 'cyclisme' in obj_lower:
        obj_type = 'velo'
    elif 'natation' in obj_lower or 'swim' in obj_lower:
        obj_type = 'natation'
    
    coeff_obj = coeff_objectif.get(obj_type, {'CAP': 1.0, 'Velo': 1.0, 'Natation': 1.0})
    coeff_semaine = get_volume_coeff(semaine_type, phase, semaine_num)
    
    # CORRIGÉ: Pondération selon le sport principal
    ponderation = get_sport_ponderation(sport_principal)
    
    volumes = {}
    for discipline in ['CAP', 'Velo', 'Natation']:
        nb_jours = len(jours_dispos.get(discipline, []))
        duree = duree_base.get(discipline, 45)
        
        if nb_jours == 0:
            volumes[discipline] = 0
            continue
        
        if discipline == 'Velo' and duree * coeff_semaine * coeff_niveau < 80:
            duree = 80
        
        volume_calc = nb_jours * duree * coeff_niveau * coeff_obj.get(discipline, 1.0) * coeff_semaine * ponderation.get(discipline, 1.0)
        
        volume_max = nb_jours * VOLUME_MAX_PAR_SEANCE.get(discipline, 120)
        volume_calc = min(volume_calc, volume_max)
        
        if discipline == 'Natation' and nb_jours > 0:
            km_par_seance = get_natation_km(niveau)
            volume_min_km = km_par_seance * 60 * nb_jours
            volume_calc = max(volume_calc, volume_min_km * 0.7)
        
        volumes[discipline] = int(volume_calc)
        
        if discipline == 'Velo' and nb_jours > 0:
            volumes[discipline] = max(volumes[discipline], nb_jours * 80)
    
    return volumes


def get_nb_intenses_requis(nb_seances_cap: int, semaine_num: int = 0, semaine_type: str = 'normale') -> int:
    """Détermine le nombre de séances intenses CAP requises."""
    if semaine_type in ['affutage', 'recuperation']:
        return 0
    
    if nb_seances_cap >= 10:
        return 4
    elif nb_seances_cap >= 7:
        return 3
    elif nb_seances_cap >= 5:
        return 2
    elif nb_seances_cap >= 3:
        return 1
    elif nb_seances_cap >= 1:
        if semaine_num % 3 == 0:
            return 1
        return 0
    return 0


def get_natation_km(niveau: str) -> int:
    """Règle natation: entre 2 et 6 km par séance."""
    volumes = {
        'Débutant': 2,
        'Intermédiaire': 3,
        'Avancé': 4
    }
    return volumes.get(niveau, 3)


def get_duree_intensite_min(nb_rep: int, temps_effort_sec: float) -> int:
    """Calcule la durée totale d'intensité."""
    duree_intense_sec = nb_rep * temps_effort_sec
    duree_intense_min = duree_intense_sec / 60
    return int(duree_intense_min)


def ajuster_nb_rep_pour_intensite(
    nb_rep: int,
    temps_effort_sec: float,
    temps_recup_sec: float = 0,
    duree_cible_min: int = 20
) -> int:
    """Ajuste le nombre de répétitions pour que l'intensité dure entre 15' et 30'."""
    if temps_effort_sec <= 0:
        return nb_rep
    
    duree_intense_min = get_duree_intensite_min(nb_rep, temps_effort_sec)
    
    if duree_intense_min < 15:
        nb_rep_min = math.ceil(15 * 60 / temps_effort_sec)
        return max(nb_rep, nb_rep_min)
    elif duree_intense_min > 30:
        nb_rep_max = math.floor(30 * 60 / temps_effort_sec)
        return max(1, min(nb_rep, nb_rep_max))
    
    return nb_rep