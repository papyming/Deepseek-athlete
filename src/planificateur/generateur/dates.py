# ============================================================
# FICHIER: src/planificateur/generateur/dates.py
# RÔLE: Gestion des dates pour la génération des semaines
# ============================================================

from datetime import datetime, timedelta
from typing import List

from ..constants_plan import JOURS_SEMAINE


def generer_jour_date(date_semaine: datetime, jour_index: int) -> str:
    jour_date = date_semaine + timedelta(days=jour_index)
    return jour_date.strftime('%Y-%m-%d')


def est_date_passee(date_str: str) -> bool:
    aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date < aujourd_hui


def jours_avant_objectif(date_semaine: datetime, date_objectif: datetime, jour_index: int) -> int:
    return (date_objectif - date_semaine - timedelta(days=jour_index)).days


def est_affutage(jours_avant: int) -> bool:
    return 0 <= jours_avant <= 3


def jours_disponibles_renforcement(jours_cap: List[str], jours_velo: List[str], jours_natation: List[str]) -> List[int]:
    jours_disponibles = []
    for i, nom_jour in enumerate(JOURS_SEMAINE):
        if nom_jour in jours_cap or nom_jour in jours_velo or nom_jour in jours_natation:
            jours_disponibles.append(i)
    return jours_disponibles


def get_volume_semaine_affichage(semaine_num: int, nb_semaines: int) -> int:
    return nb_semaines - semaine_num