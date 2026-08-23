# ============================================================
# FICHIER: src/planificateur/volume.py
# RÔLE: Calculs de volume hebdomadaire par discipline
#       Basé sur le niveau, l'objectif et le type de semaine
#       Respecte les règles du cahier des charges
# ============================================================

from typing import Dict, List

from .periodisation import get_volume_coeff


# Volume maximal par séance (en minutes)
VOLUME_MAX_PAR_SEANCE = {
    'CAP': 180,      # 3h max par séance
    'Velo': 240,     # 4h max par séance (sortie longue)
    'Natation': 120  # 2h max par séance
}


def calculer_volume_hebdo(
    jours_dispos: Dict[str, List[str]],
    niveau: str,
    objectif: str,
    semaine_type: str,
    phase: str,
    semaine_num: int = 0
) -> Dict[str, int]:
    """
    Calcule le volume hebdomadaire cible par discipline.
    """
    # Volume de base par séance
    duree_base = {
        'CAP': 45,
        'Velo': 90,  # Minimum 80 min selon règle
        'Natation': 45
    }
    
    # Coefficient de niveau
    coeff_niveau = {
        'Débutant': 0.8,
        'Intermédiaire': 1.0,
        'Avancé': 1.2
    }.get(niveau, 1.0)
    
    # Coefficient d'objectif (priorité selon discipline)
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
    
    # Déterminer le type d'objectif
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
    
    # Coefficient de semaine (avec numéro pour l'ondulation)
    coeff_semaine = get_volume_coeff(semaine_type, phase, semaine_num)
    
    volumes = {}
    for discipline in ['CAP', 'Velo', 'Natation']:
        nb_jours = len(jours_dispos.get(discipline, []))
        duree = duree_base.get(discipline, 45)
        
        # Règle vélo: jamais < 80 min
        if discipline == 'Velo' and duree * coeff_semaine * coeff_niveau < 80:
            duree = 80
        
        # Calcul du volume total
        volume_calc = nb_jours * duree * coeff_niveau * coeff_obj.get(discipline, 1.0) * coeff_semaine
        
        # Règle: volume max par séance
        if nb_jours > 0:
            volume_max = nb_jours * VOLUME_MAX_PAR_SEANCE.get(discipline, 120)
            volume_calc = min(volume_calc, volume_max)
        
        # Règle natation: entre 2 et 6 km par séance
        if discipline == 'Natation' and nb_jours > 0:
            km_par_seance = get_natation_km(niveau)
            volume_min_km = km_par_seance * 60 * nb_jours
            volume_calc = max(volume_calc, volume_min_km * 0.7)
        
        volumes[discipline] = int(volume_calc)
        
        # Règle vélo: jamais < 80 min pour une séance
        if discipline == 'Velo' and nb_jours > 0:
            volumes[discipline] = max(volumes[discipline], nb_jours * 80)
    
    return volumes


def get_nb_intenses_requis(nb_seances_cap: int) -> int:
    """
    Règle 3.2: Détermine le nombre de séances intenses CAP requises.
    
    - 1 ou 2 séances: 1 séance intense toutes les 3 séances
    - 3 séances: 1 intense
    - 5 séances: 2 intenses
    - 7 séances: 3 intenses
    - 10 séances: 4 intenses
    """
    if nb_seances_cap >= 10:
        return 4
    elif nb_seances_cap >= 7:
        return 3
    elif nb_seances_cap >= 5:
        return 2
    elif nb_seances_cap >= 3:
        return 1
    elif nb_seances_cap >= 2:
        return 1  # 1 intense sur 2 jours (règle: une toutes les 3 séances)
    return 0


def get_natation_km(niveau: str) -> int:
    """
    Règle natation: entre 2 et 6 km par séance.
    """
    volumes = {
        'Débutant': 2,
        'Intermédiaire': 3,
        'Avancé': 4
    }
    return volumes.get(niveau, 3)


def get_duree_intensite_min(nb_rep: int, temps_effort_sec: float) -> int:
    """
    Règle 3.2: L'intensité doit durer entre 15' et 30'.
    Calcule la durée totale d'intensité (effort × nb_rep).
    """
    duree_intense_sec = nb_rep * temps_effort_sec
    duree_intense_min = duree_intense_sec / 60
    return int(duree_intense_min)


def ajuster_nb_rep_pour_intensite(
    nb_rep: int,
    temps_effort_sec: float,
    temps_recup_sec: float,
    duree_cible_min: int = 20
) -> int:
    """
    Ajuste le nombre de répétitions pour que l'intensité dure entre 15' et 30'.
    """
    duree_intense_min = get_duree_intensite_min(nb_rep, temps_effort_sec)
    
    if duree_intense_min < 15:
        # Pas assez d'intensité: augmenter les répétitions
        nb_min = int(15 * 60 / temps_effort_sec) + 1
        return max(nb_rep, nb_min)
    elif duree_intense_min > 30:
        # Trop d'intensité: réduire les répétitions
        nb_max = int(30 * 60 / temps_effort_sec)
        return min(nb_rep, max(1, nb_max))
    
    return nb_rep