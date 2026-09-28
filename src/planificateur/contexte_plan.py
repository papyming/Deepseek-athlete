# ============================================================
# FICHIER: src/planificateur/contexte_plan.py
# RÔLE: Construction EXPLICITE du contexte transmis à un futur
#       fournisseur IA.
#
#       Python décide de ce qui est envoyé. Le contexte ne contient
#       AUCUN chemin de fichier brut, aucun CSV, aucun projet
#       complet : uniquement l'identité LOGIQUE du plan, sa période,
#       ses disciplines et ses séances pertinentes.
#
#       Les données athlète (base athlète) ne sont PAS lues ici :
#       elles sont fournies explicitement par l'appelant lorsqu'elles
#       sont disponibles.
#
#       AUCUNE connexion IA, AUCUN calcul de plan ici.
# ============================================================

import hashlib
import os
from typing import Dict, List, Optional, Set

from .plan_csv import construire_plan_depuis_csv

# Disciplines non sportives : jamais transmises comme séances.
_DISCIPLINES_IGNOREES = {'', 'Repos', 'Course'}


def identifiant_logique(chemin_csv: str) -> str:
    """Identifiant LOGIQUE et stable d'un plan (jamais un chemin lisible).

    Le chemin réel n'est pas exposé au fournisseur IA : seul ce condensat
    permet de distinguer deux plans.
    """
    graine = os.path.abspath(str(chemin_csv))
    return hashlib.sha1(graine.encode('utf-8')).hexdigest()[:16]


def _seance_compacte(semaine: Dict, jour: Dict, seance: Dict) -> Dict:
    return {
        'semaine': semaine.get('num_affichage') or semaine.get('emoji', ''),
        'date': jour.get('date', ''),
        'jour': jour.get('jour', ''),
        'discipline': seance.get('discipline', ''),
        'type': seance.get('type', ''),
        'duree': seance.get('duree', 0),
    }


def _normaliser_disponibilites(disponibilites: Dict) -> Dict:
    return {
        'CAP': list(disponibilites.get('CAP', []) or []),
        'Velo': list(
            disponibilites.get('Velo', disponibilites.get('Vélo', [])) or []
        ),
        'Natation': list(disponibilites.get('Natation', []) or []),
    }


def construire_contexte_plan(chemin_csv: str,
                             athlete: Optional[str] = None,
                             donnees_athlete: Optional[Dict] = None,
                             disponibilites: Optional[Dict] = None,
                             filtrer_discipline: Optional[str] = None,
                             inclure_seances: bool = True) -> Dict:
    """Construit le contexte structuré d'un plan pour le fournisseur IA.

    - ``donnees_athlete`` : informations de la base athlète, fournies
      explicitement par Python (jamais lues ici).
    - ``disponibilites`` : disponibilités connues (CAP/Velo/Natation).
    - ``filtrer_discipline`` : ne transmet que les séances d'une discipline.
    """
    plan = construire_plan_depuis_csv(chemin_csv, athlete=athlete)

    seances: List[Dict] = []
    disciplines: Set[str] = set()
    if inclure_seances:
        for semaine in plan.get('semaines', []):
            for jour in semaine.get('jours', []):
                for seance in jour.get('seances', []):
                    discipline = seance.get('discipline', '')
                    if discipline in _DISCIPLINES_IGNOREES:
                        continue
                    if filtrer_discipline and discipline != filtrer_discipline:
                        continue
                    disciplines.add(discipline)
                    seances.append(_seance_compacte(semaine, jour, seance))

    if disponibilites:
        disciplines.update(_normaliser_disponibilites(disponibilites).keys())

    contexte: Dict = {
        'identite_plan': {
            'identifiant': identifiant_logique(chemin_csv),
            'athlete': plan.get('athlete', ''),
        },
        'periode': {
            'debut': plan.get('date_debut', ''),
            'fin': plan.get('date_objectif', ''),
            'date_objectif': plan.get('date_objectif', ''),
            'nb_semaines': plan.get('nb_semaines', 0),
        },
        'disciplines_disponibles': sorted(disciplines),
        'seances': seances,
    }

    if disponibilites:
        contexte['disponibilites'] = _normaliser_disponibilites(disponibilites)
    if donnees_athlete:
        contexte['athlete'] = dict(donnees_athlete)
    return contexte
