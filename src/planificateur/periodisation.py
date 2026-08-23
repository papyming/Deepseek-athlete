# ============================================================
# FICHIER: src/planificateur/periodisation.py
# RÔLE: Gestion de la périodisation (phases, types de semaine)
#       Détermine les phases d'entraînement et les types de semaines
#       selon les modèles de Matveev, Billat et le modèle norvégien
# ============================================================

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
    Détermine le type de semaine selon les 6 types possibles.
    
    ⚪ = récupération (baisse de 25-35%)
    🔵 = affûtage (2 dernières semaines)
    🟢 = normale
    🟡 = légèrement chargée
    🔴 = dure
    🟤 = exceptionnelle
    """
    if semaines_anterieures is None:
        semaines_anterieures = []
    
    # Règle 1: Affûtage les 2 dernières semaines → S-01 et S-00
    if semaine_num >= nb_semaines - 2:
        return 'affutage'
    
    # Règle 2: Récupération toutes les 4 semaines (réduction 25-35%)
    # Le modèle norvégien: réduction toutes les 3-4 semaines
    if semaine_num % 4 == 0:
        return 'recuperation'
    
    # Règle 3: Semaine exceptionnelle si très chargée (phase spécifique)
    if phase == 'preparation_specifique' and seances_intenses > 4 and volume_total > 700:
        return 'exceptionnelle'
    
    # Règle 4: Semaine dure (phase spécifique)
    if phase == 'preparation_specifique' and seances_intenses > 3:
        return 'dure'
    
    # Règle 5: Semaine légèrement chargée
    if seances_intenses > 2 and volume_total > 450:
        return 'chargee'
    
    # Règle 6: S'assurer qu'on n'a pas 2 semaines identiques
    # Utiliser un motif ondulatoire (Matveev)
    if semaines_anterieures and semaine_num > 1:
        dernier_type = semaines_anterieures[-1].get('semaine_type', 'normale')
        phase_prec = semaines_anterieures[-1].get('phase', '')
        
        # Éviter les répétitions
        if dernier_type == 'normale' and phase == 'preparation_specifique':
            return 'chargee'
        if dernier_type == 'chargee' and phase == 'preparation_specifique':
            return 'dure'
        if dernier_type == 'dure':
            return 'chargee'  # Après une semaine dure, on réduit
        if dernier_type == 'recuperation' and semaine_num % 4 != 0:
            return 'chargee'  # Après récup, on charge
    
    return 'normale'


def get_volume_coeff(semaine_type: str, phase: Optional[str] = None, semaine_num: int = 0) -> float:
    """
    Coefficient de volume selon le type de semaine et la phase.
    Applique la variation ondulatoire de Matveev.
    """
    # Coefficients de base par type de semaine
    coeffs = {
        'affutage': 0.65,      # Réduction de 35%
        'recuperation': 0.75,  # Réduction de 25% (modèle norvégien)
        'normale': 1.0,
        'chargee': 1.15,
        'dure': 1.25,
        'exceptionnelle': 1.35
    }
    
    # Coefficients par phase (Matveev)
    phase_coeff = {
        'preparation_generale': 0.9,
        'preparation_specifique': 1.1,
        'competition': 1.0,
        'affutage': 0.7
    }
    
    # Variation ondulatoire toutes les 2 semaines (Matveev)
    # Évite les semaines identiques
    ondulation = 1.0
    if semaine_num > 0:
        if semaine_num % 2 == 0:
            ondulation = 1.05  # Semaine paire: +5%
        else:
            ondulation = 0.95  # Semaine impaire: -5%
    
    base = coeffs.get(semaine_type, 1.0)
    
    # Appliquer le coefficient de phase si fourni
    if phase and phase in phase_coeff:
        base = base * phase_coeff[phase]
    
    # Appliquer l'ondulation (Matveev)
    if semaine_type not in ['affutage', 'recuperation']:
        base = base * ondulation
    
    return round(base, 2)


def get_intensite_coeff(semaine_type: str) -> float:
    """
    Coefficient d'intensité selon le type de semaine (inversion volume/intensité).
    Quand le volume augmente, l'intensité diminue, et inversement.
    """
    coeffs = {
        'affutage': 1.3,       # Intensité maximale
        'recuperation': 0.6,   # Intensité minimale
        'normale': 1.0,
        'chargee': 1.1,
        'dure': 1.2,
        'exceptionnelle': 0.9  # Volume élevé, intensité réduite
    }
    return coeffs.get(semaine_type, 1.0)


def get_volume_semaine_affichage(semaine_num: int, nb_semaines: int) -> int:
    """
    Calcule le numéro de semaine affiché (S-XX).
    La dernière semaine est S-00.
    """
    return nb_semaines - semaine_num