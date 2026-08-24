# ============================================================
# FICHIER: src/planificateur/periodisation.py
# RÔLE: Gestion de la périodisation (phases, types de semaine)
#       CORRIGÉ: Alternance renforcée et évitement des semaines identiques
# ============================================================

import random
import math
from typing import Dict, List, Optional


def determiner_phase(semaine_num: int, nb_semaines: int) -> str:
    """
    Détermine la phase d'entraînement selon les 4 phases classiques.
    
    Phase 1: Préparation générale (0-25%) - volume élevé, intensité faible
    Phase 2: Préparation spécifique (25-60%) - volume modéré, intensité élevée
    Phase 3: Compétition/pic de forme (60-85%) - volume réduit, intensité maximale
    Phase 4: Affûtage/transition (85-100%) - repos actif
    """
    ratio = semaine_num / nb_semaines
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
    CORRIGÉ: Détermine le type de semaine selon les 6 types possibles.
    Renforce l'alternance pour éviter les semaines identiques.
    
    ⚪ = récupération (baisse de 25-35%)
    🔵 = affûtage (2 dernières semaines)
    🟢 = normale
    🟡 = légèrement chargée
    🔴 = dure
    🟤 = exceptionnelle
    """
    if semaines_anterieures is None:
        semaines_anterieures = []
    
    # Règle 1: Affûtage les 2 dernières semaines
    if semaine_num >= nb_semaines - 2:
        return 'affutage'
    
    # Règle 2: Récupération toutes les 4 semaines (réduction 25-35%)
    if semaine_num % 4 == 0 and semaine_num > 0:
        return 'recuperation'
    
    # Règle 3: Semaine exceptionnelle si très chargée
    if phase == 'preparation_specifique' and seances_intenses > 4 and volume_total > 600:
        return 'exceptionnelle'
    
    # Règle 4: Semaine dure (phase spécifique)
    if phase == 'preparation_specifique' and seances_intenses > 3:
        return 'dure'
    
    # Règle 5: Semaine légèrement chargée
    if seances_intenses > 2 and volume_total > 400:
        return 'chargee'
    
    # Règle 6: CORRIGÉ - Éviter les semaines identiques de manière stricte
    if semaines_anterieures:
        derniers_types = [s.get('semaine_type', 'normale') for s in semaines_anterieures[-3:]]
        derniers_volumes = [s.get('volume_total', 0) for s in semaines_anterieures[-3:]]
        
        # 6a: Éviter 2 semaines consécutives identiques
        if len(derniers_types) >= 2 and derniers_types[-1] == derniers_types[-2]:
            # Forcer un changement
            if derniers_types[-1] == 'normale':
                return 'chargee'
            elif derniers_types[-1] == 'chargee':
                return 'dure' if phase in ['preparation_specifique', 'competition'] else 'normale'
            elif derniers_types[-1] == 'dure':
                return 'chargee' if semaine_num % 2 == 0 else 'normale'
            elif derniers_types[-1] == 'recuperation':
                return 'chargee' if phase in ['preparation_specifique', 'competition'] else 'normale'
            elif derniers_types[-1] == 'exceptionnelle':
                return 'recuperation'
            elif derniers_types[-1] == 'affutage':
                return 'normale'
        
        # 6b: Éviter les volumes trop proches sur 2 semaines consécutives
        if len(derniers_volumes) >= 2:
            diff_volume = abs(derniers_volumes[-1] - derniers_volumes[-2])
            # Si les volumes sont trop proches (moins de 5% de différence)
            if derniers_volumes[-1] > 0 and (diff_volume / derniers_volumes[-1]) < 0.05:
                if derniers_types[-1] == 'normale':
                    return 'chargee'
                elif derniers_types[-1] == 'chargee':
                    return 'dure' if phase in ['preparation_specifique', 'competition'] else 'normale'
                elif derniers_types[-1] == 'dure':
                    return 'recuperation' if semaine_num % 3 == 0 else 'chargee'
                else:
                    return 'normale'
        
        # 6c: Éviter 3 semaines avec le même type
        if len(derniers_types) >= 3:
            if derniers_types[-1] == derniers_types[-2] == derniers_types[-3]:
                if derniers_types[-1] == 'normale':
                    return 'chargee'
                elif derniers_types[-1] == 'chargee':
                    return 'dure'
                elif derniers_types[-1] == 'dure':
                    return 'chargee'
                else:
                    return 'normale'
    
    # Règle 7: Alternance charge/récupération (Selye) - motif ondulatoire
    if semaines_anterieures:
        dernier_type = semaines_anterieures[-1].get('semaine_type', 'normale')
        
        # Alternance stricte sur 2 semaines
        if dernier_type == 'recuperation' and semaine_num % 4 != 0:
            return 'chargee'
        if dernier_type == 'normale' and semaine_num % 2 == 0:
            return 'chargee' if phase in ['preparation_specifique', 'competition'] else 'normale'
        if dernier_type == 'chargee' and semaine_num % 2 == 1:
            return 'dure' if phase in ['preparation_specifique', 'competition'] else 'normale'
        if dernier_type == 'dure':
            return 'chargee'
        if dernier_type == 'exceptionnelle':
            return 'recuperation'
    
    return 'normale'


def get_volume_coeff(semaine_type: str, phase: Optional[str] = None, semaine_num: int = 0) -> float:
    """
    CORRIGÉ: Coefficient de volume avec ondulation plus marquée.
    Applique une variation ondulatoire de Matveev plus dynamique.
    """
    coeffs = {
        'affutage': 0.65,
        'recuperation': 0.75,
        'normale': 1.0,
        'chargee': 1.15,
        'dure': 1.25,
        'exceptionnelle': 1.35
    }
    
    phase_coeff = {
        'preparation_generale': 0.9,
        'preparation_specifique': 1.1,
        'competition': 1.0,
        'affutage': 0.7
    }
    
    # CORRIGÉ: Variation ondulatoire plus marquée pour éviter les semaines identiques
    # Motif plus long et varié: 1.0, 1.08, 0.92, 1.12, 0.88, 1.15, 0.85, 1.05, 0.95, 1.02, 0.98, 1.10
    ondulation = 1.0
    if semaine_num > 0:
        pattern = [1.0, 1.08, 0.92, 1.12, 0.88, 1.15, 0.85, 1.05, 0.95, 1.02, 0.98, 1.10]
        idx = (semaine_num - 1) % len(pattern)
        ondulation = pattern[idx]
    
    base = coeffs.get(semaine_type, 1.0)
    
    if phase and phase in phase_coeff:
        base = base * phase_coeff[phase]
    
    # L'ondulation s'applique à toutes les semaines sauf affûtage et récupération
    if semaine_type not in ['affutage', 'recuperation']:
        base = base * ondulation
    
    return round(base, 2)


def get_intensite_coeff(semaine_type: str) -> float:
    """
    Coefficient d'intensité selon le type de semaine (inversion volume/intensité).
    Quand le volume augmente, l'intensité diminue, et inversement.
    """
    coeffs = {
        'affutage': 1.3,
        'recuperation': 0.6,
        'normale': 1.0,
        'chargee': 1.1,
        'dure': 1.2,
        'exceptionnelle': 0.9
    }
    return coeffs.get(semaine_type, 1.0)


def get_volume_semaine_affichage(semaine_num: int, nb_semaines: int) -> int:
    """
    Calcule le numéro de semaine affiché (S-XX).
    La dernière semaine (semaine de l'objectif) est S-00.
    """
    return nb_semaines - semaine_num