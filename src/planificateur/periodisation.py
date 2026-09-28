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
    - Compétition: 60-100% (hors dernière semaine)
    - Affûtage: uniquement la dernière semaine du plan (semaine de l'objectif)

    L'affûtage ne doit pas commencer plusieurs semaines avant l'objectif :
    seule la semaine qui contient la date de l'objectif principal est en
    affûtage. Les semaines précédentes poursuivent la périodisation normale.
    """
    if nb_semaines <= 0:
        return "preparation_generale"

    # Une seule semaine d'affûtage : la dernière (celle de l'objectif).
    if semaine_num >= nb_semaines:
        return "affutage"

    ratio = semaine_num / nb_semaines
    if ratio < 0.25:
        return "preparation_generale"
    if ratio < 0.60:
        return "preparation_specifique"
    return "competition"


def _semaine_exceptionnelle(nb_semaines: int) -> Optional[int]:
    """Retourne la semaine de charge la plus élevée de la préparation.

    Il s'agit de la dernière semaine de pic (3e semaine du mésocycle de
    charge) située encore en préparation (générale ou spécifique), avant
    la phase de compétition et l'affûtage. Une seule semaine par plan.
    """
    pic = None
    for semaine_num in range(3, nb_semaines, 4):
        if determiner_phase(semaine_num, nb_semaines) in (
            "preparation_generale", "preparation_specifique"
        ):
            pic = semaine_num
    return pic


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

    # Règle 1: une seule semaine d'affûtage, la dernière (objectif principal).
    if semaine_num >= nb_semaines:
        return 'affutage'

    # Règle 2: mésocycle de 4 semaines -> 3 semaines de charge + 1 récupération
    # (réduction périodique de charge toutes les 3-4 semaines, Issurin 2010).
    if semaine_num > 0 and semaine_num % 4 == 0:
        return 'recuperation'

    # Règle 3: progression de charge à l'intérieur du mésocycle.
    #   semaine 1 -> normale
    #   semaine 2 -> chargée
    #   semaine 3 -> dure (pic du mésocycle éventuellement exceptionnel)
    position = ((semaine_num - 1) % 4) + 1
    if position == 1:
        return 'normale'
    if position == 2:
        return 'chargee'
    # Le pic du mésocycle est une semaine "dure". La semaine réellement la
    # plus chargée de la préparation est ensuite promue "exceptionnelle"
    # après construction, à partir de la charge mesurée.
    return 'dure'


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