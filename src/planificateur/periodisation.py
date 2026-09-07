# ============================================================
# FICHIER: src/planificateur/periodisation.py
# RÔLE: Gestion de la périodisation (phases, types de semaine)
#       CORRIGÉ: Ajout des semaines rouges (dure)
# ============================================================

import random
import math
from typing import Dict, List, Optional


def determiner_phase(semaine_num: int, nb_semaines: int) -> str:
    """
    Détermine la phase d'entraînement selon les 4 phases classiques de Matveev.
    """
    ratio = semaine_num / nb_semaines if nb_semaines > 0 else 0
    
    if ratio < 0.25:
        return "preparation_generale"
    elif ratio < 0.60:
        return "preparation_specifique"
    elif ratio < 0.85:
        return "competition"
    else:
        return "affutage"


def determiner_type_semaine(
    semaine_num: int,
    nb_semaines: int,
    volume_total: float,
    seances_intenses: int,
    phase: str,
    semaines_anterieures: Optional[List[Dict]] = None
) -> str:
    """
    Détermine le type de semaine.
    CORRIGÉ: Plus de semaines rouges (dure).
    """
    if semaines_anterieures is None:
        semaines_anterieures = []
    
    # Règle 1: Affûtage les 2 dernières semaines
    if semaine_num >= nb_semaines - 2:
        return 'affutage'
    
    # Règle 2: Récupération toutes les 4 semaines
    if semaine_num % 4 == 0 and semaine_num > 0:
        return 'recuperation'
    
    # CORRIGÉ: Semaine rouge (dure) en phase spécifique avec volume ou intensité élevés
    if phase == 'preparation_specifique' and seances_intenses > 3:
        return 'dure'
    
    if volume_total > 600 and phase != 'affutage':
        return 'dure'
    
    # CORRIGÉ: Alternance stricte pour éviter les semaines identiques
    if semaines_anterieures:
        derniers_types = [s.get('semaine_type', 'normale') for s in semaines_anterieures[-3:]]
        
        if len(derniers_types) >= 2 and derniers_types[-1] == derniers_types[-2]:
            if derniers_types[-1] == 'normale':
                return 'chargee'
            elif derniers_types[-1] == 'chargee':
                return 'dure'
            elif derniers_types[-1] == 'dure':
                return 'recuperation'
    
    return 'normale'


def get_volume_coeff(semaine_type: str, phase: Optional[str] = None, semaine_num: int = 0) -> float:
    """Coefficient de volume avec inversion volume/intensité (Matveev)."""
    coeffs = {
        'affutage': 0.65,
        'recuperation': 0.75,
        'normale': 1.0,
        'chargee': 1.15,
        'dure': 1.25,
        'exceptionnelle': 1.35
    }
    
    phase_volume = {
        'preparation_generale': 1.2,
        'preparation_specifique': 1.0,
        'competition': 0.85,
        'affutage': 0.65
    }
    
    base = coeffs.get(semaine_type, 1.0) * phase_volume.get(phase, 1.0)
    
    if semaine_num > 0 and semaine_num % 4 == 0:
        base = base * 0.75
    
    return round(base, 2)


def get_intensite_coeff(semaine_type: str, phase: Optional[str] = None) -> float:
    """Coefficient d'intensité avec inversion volume/intensité (Matveev)."""
    coeffs = {
        'affutage': 1.3,
        'recuperation': 0.6,
        'normale': 1.0,
        'chargee': 1.1,
        'dure': 1.2,
        'exceptionnelle': 0.9
    }
    
    phase_intensite = {
        'preparation_generale': 0.7,
        'preparation_specifique': 1.2,
        'competition': 1.3,
        'affutage': 1.0
    }
    
    base = coeffs.get(semaine_type, 1.0) * phase_intensite.get(phase, 1.0)
    
    return round(base, 2)


def get_volume_semaine_affichage(semaine_num: int, nb_semaines: int) -> int:
    """Calcule le numéro de semaine affiché (S-XX)."""
    return nb_semaines - semaine_num