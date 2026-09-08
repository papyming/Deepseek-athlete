# ============================================================
# FICHIER: src/planificateur/periodisation.py
# RÔLE: Gestion de la périodisation
#       SOURCES: Matveev (1981), Billat (2001), Issurin (2010)
# ============================================================

from typing import Dict, List, Optional


def determiner_phase(semaine_num: int, nb_semaines: int) -> str:
    """
    Détermine la phase d'entraînement selon Matveev (1981).
    
    Source: Matveev, L. (1981). Fundamentals of Sports Training.
    - Préparation générale: 0-25%
    - Préparation spécifique: 25-60%
    - Compétition: 60-85%
    - Affûtage: 85-100%
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
    Détermine le type de semaine selon les critères de charge.
    
    SOURCES:
    - Billat, V. (2001). Physiologie et méthodologie de l'entraînement.
      Une séance est "dure" quand elle dépasse 70% de VMA ou VC.
    
    - Seiler, S. (2010). What is best practice for training intensity
      and duration distribution in endurance athletes?
      80% du volume en Z1-Z2, 20% en Z3+.
    
    - Norris, M. (2019). Monitoring training load in endurance athletes.
      Seuil de surentraînement: TSB < -25.
    """
    if semaines_anterieures is None:
        semaines_anterieures = []
    
    # Règle 1: Affûtage les 2 dernières semaines (Matveev)
    if semaine_num >= nb_semaines - 2:
        return 'affutage'
    
    # Règle 2: Récupération toutes les 4 semaines (Issurin, 2010)
    if semaine_num % 4 == 0 and semaine_num > 0:
        return 'recuperation'
    
    # ---- SEUILS ADAPTÉS AU NOMBRE DE SÉANCES ----
    # Règle 3: Semaine "dure" basée sur le ratio intensité/volume
    # Plus l'athlète s'entraîne, plus le seuil de volume est élevé
    # pour déclencher une semaine rouge.
    
    # Nombre total de séances dans la semaine
    nb_seances_total = seances_intenses * 2 + (volume_total // 60)
    
    # Seuil de volume adapté au nombre de séances
    # Source: Norris (2019) - Le volume total doit représenter
    # environ 60-90 min par séance en moyenne
    nb_seances_estime = max(1, int(volume_total / 60))
    
    # Seuil de volume pour une semaine "dure"
    # Plus l'athlète a de séances, plus le seuil est élevé
    if nb_seances_estime <= 3:
        seuil_volume_dure = 300   # 3 séances × 60 min
    elif nb_seances_estime <= 5:
        seuil_volume_dure = 450   # 5 séances × 60 min
    elif nb_seances_estime <= 8:
        seuil_volume_dure = 600   # 8 séances × 60 min
    else:
        seuil_volume_dure = 750   # 10+ séances × 60 min
    
    # Règle 4: Semaine "dure" si volume > seuil adapté
    if volume_total > seuil_volume_dure and phase != 'affutage':
        return 'dure'
    
    # Règle 5: Semaine "dure" si intensité > seuil adapté
    # Source: Billat (2001) - Plus de 2 séances intenses par semaine
    # pour un volume faible, plus pour un volume élevé
    if nb_seances_estime <= 3 and seances_intenses >= 2:
        return 'dure'
    elif nb_seances_estime <= 5 and seances_intenses >= 3:
        return 'dure'
    elif nb_seances_estime <= 8 and seances_intenses >= 4:
        return 'dure'
    elif nb_seances_estime > 8 and seances_intenses >= 5:
        return 'dure'
    
    # Règle 6: Alternance stricte (Matveev)
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
    """
    Coefficient de volume avec inversion volume/intensité (Matveev).
    """
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
    """
    Coefficient d'intensité avec inversion volume/intensité (Matveev).
    """
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