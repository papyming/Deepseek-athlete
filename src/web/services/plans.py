# ============================================================
# FICHIER: src/web/services/plans.py
# RÔLE: Services Web de consultation des plans.
#       Accès aux plans EXCLUSIVEMENT via PlanRepository.
#       Aucun accès direct au système de fichiers ici.
# ============================================================

import hashlib
import re
from typing import Dict, List, Optional

from stockage import PlanRepository, get_plan_repository
from planificateur.validateur_plan import valider_plan_csv

# Timestamp du nommage existant : <Athlete>_plan_<AAAAmmjj_HHMMSS>.csv
_MOTIF_TIMESTAMP = re.compile(r'_plan_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})')


def identifiant_plan(chemin: str) -> str:
    """Identifiant opaque et stable d'un plan (dérivé de son emplacement).

    Le nom de l'athlète n'est jamais utilisé comme identifiant : deux plans
    distincts gardent des identifiants distincts.
    """
    return hashlib.sha1(str(chemin).encode('utf-8')).hexdigest()[:16]


def date_nommage(fichier: str) -> str:
    """Date de modification lue dans le nommage du fichier (si présente)."""
    correspondance = _MOTIF_TIMESTAMP.search(str(fichier))
    if not correspondance:
        return ''
    annee, mois, jour, heure, minute, _ = correspondance.groups()
    return f"{jour}/{mois}/{annee} {heure}:{minute}"


def _depot(repository: Optional[PlanRepository] = None) -> PlanRepository:
    return repository or get_plan_repository()


def lister_plans(repository: Optional[PlanRepository] = None) -> List[Dict]:
    """Liste les plans disponibles, enrichis d'un identifiant."""
    entrees = []
    for plan in _depot(repository).lister_plans():
        entree = dict(plan)
        entree['identifiant'] = identifiant_plan(plan['chemin'])
        entree['modifie'] = date_nommage(plan['fichier'])
        entrees.append(entree)
    return entrees


def obtenir_plan(identifiant: str,
                 repository: Optional[PlanRepository] = None) -> Optional[Dict]:
    """Résout un identifiant UNIQUEMENT via la liste connue du repository."""
    for entree in lister_plans(repository):
        if entree['identifiant'] == identifiant:
            return entree
    return None


def lire_plan(entree: Dict, repository: Optional[PlanRepository] = None):
    """Lit le contenu d'un plan via le repository (DataFrame brut)."""
    return _depot(repository).lire_plan(entree['chemin'])


def valider_plan(entree: Dict, repository: Optional[PlanRepository] = None) -> Dict:
    """Valide le CSV courant avec le validateur existant (sans modification)."""
    _depot(repository)  # le validateur lit via le repository
    return valider_plan_csv(entree['chemin'])
