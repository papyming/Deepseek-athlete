# ============================================================
# FICHIER: src/planificateur/fournisseur_ia.py
# RÔLE: Socle d'abstraction pour brancher n'importe quel fournisseur
#       IA (Gemini, DeepSeek, Ollama, …) SANS modifier le moteur de
#       modification des CSV.
#
#       Architecture :
#
#         Navigateur
#             ↓
#         FastAPI
#             ↓
#         traiter_demande_ia(...)      <- ce module
#             ↓
#         FournisseurIAAbstrait         <- interface (ce module)
#             ↓
#         structure JSON (contrat_modifications)
#             ↓
#         moteur_modifications.py       <- DÉTERMINISTE (écrit/valide)
#             ↓
#         validateur_plan.py
#             ↓
#         PlanRepository
#             ↓
#         CSV
#
#       PRINCIPE : l'IA INTERPRÈTE. Python DÉCIDE, CALCULE, MODIFIE et
#       VALIDE. Un fournisseur ne reçoit JAMAIS de chemin de fichier et
#       ne retourne QUE des données (jamais de CSV, PDF, code Python).
#
#       AUCUNE connexion IA n'est réalisée ici : aucun fournisseur
#       réseau n'est fourni (le Mock sert aux tests).
# ============================================================

from abc import abstractmethod
from typing import Dict, List, Optional, Union

from .agent_plan_csv import FournisseurModifications
from .contexte_plan import construire_contexte_plan
from .moteur_modifications import (
    appliquer_modifications_structurees,
    previsualiser_modifications,
)

__all__ = [
    'FournisseurIAAbstrait',
    'MockFournisseurModifications',
    'FournisseurIAFictif',
    'ClarificationRequise',
    'traiter_demande_ia',
]

# Structure renvoyée par un fournisseur : dict unique, liste de dicts,
# ou {'modifications': [...]}. Elle respecte le contrat existant
# (src/planificateur/contrat_modifications.py).
StructureIA = Union[Dict, List[Dict]]


class ClarificationRequise(Exception):
    """Signal explicite : le fournisseur ne peut pas interpréter la demande.

    Lever cette exception n'écrit jamais le CSV : l'orchestrateur
    court-circuite le moteur et renvoie une clarification.
    """

    def __init__(self, question: str, categorie: str = 'INCOMPRIS'):
        super().__init__(question)
        self.question = question
        self.categorie = categorie


class FournisseurIAAbstrait(FournisseurModifications):
    """Contrat d'un fournisseur IA d'interprétation de demandes.

    Différence avec ``FournisseurModifications`` (contrat historique) :
    le fournisseur reçoit ici la DEMANDE LIBRE du coach et un CONTEXTE
    STRUCTURÉ construit par Python. Il ne reçoit AUCUN chemin de fichier.

    Il retourne UNIQUEMENT une structure conforme au contrat de
    modifications (action, discipline, type_seance, jour_cible, période…),
    ou lève ``ClarificationRequise``.
    """

    @abstractmethod
    def proposer_modifications(self, demande: str, contexte: Dict) -> StructureIA:
        raise NotImplementedError


class MockFournisseurModifications(FournisseurIAAbstrait):
    """Fournisseur fictif pour les tests : AUCUN appel réseau.

    - ``structure`` : structure fixe (dict/list) ou callable
      ``(demande, contexte) -> structure``.
    - ``reponses`` : file de structures à renvoyer successivement.
    - ``erreur`` : exception à lever (ex. ``ClarificationRequise``).
    - ``appels`` : historique des ``(demande, contexte)`` reçus.
    """

    def __init__(self, structure: Optional[StructureIA] = None,
                 reponses: Optional[List[StructureIA]] = None,
                 erreur: Optional[Exception] = None):
        self._structure = structure
        self._reponses = list(reponses or [])
        self._erreur = erreur
        self.appels: List[Dict] = []

    def proposer_modifications(self, demande: str, contexte: Dict) -> StructureIA:
        self.appels.append({'demande': demande, 'contexte': contexte})
        if self._erreur is not None:
            raise self._erreur
        if self._reponses:
            return self._reponses.pop(0)
        if callable(self._structure):
            return self._structure(demande, contexte)
        return self._structure


# Alias sémantique.
FournisseurIAFictif = MockFournisseurModifications


def _resultat_erreur(message: str, chemin_csv: Optional[str] = None) -> Dict:
    return {
        'resultat': 'ERREUR_IA',
        'categorie': None,
        'question': None,
        'questions': [],
        'apercu': [],
        'ambiguites': [],
        'conflits': [],
        'erreurs': [message],
        'validation': None,
        'modifications_appliquees': 0,
        'chemin': chemin_csv,
        'interpretation': None,
    }


def traiter_demande_ia(chemin_csv: str,
                       demande: str,
                       fournisseur: Optional[FournisseurIAAbstrait],
                       contexte: Optional[Dict] = None,
                       donnees_athlete: Optional[Dict] = None,
                       disponibilites: Optional[Dict] = None,
                       date_reference=None,
                       ecrire: bool = False,
                       chemin_sortie: Optional[str] = None) -> Dict:
    """Chaîne complète : demande -> interprétation IA -> moteur -> validation.

    Cette fonction N'ÉCRIT JAMAIS le CSV elle-même. Elle délègue au
    moteur existant (``previsualiser_modifications`` en mode aperçu, ou
    ``appliquer_modifications_structurees`` en mode application), qui
    reste l'unique mécanisme d'application et de validation.

    Retour : résultat du moteur enrichi de la clé ``interpretation``
    (structure produite par le fournisseur), ou un résultat
    ``ERREUR_IA`` / ``CLARIFICATION_REQUISE`` sans écriture.
    """
    if fournisseur is None:
        return _resultat_erreur('Aucun fournisseur IA fourni.', chemin_csv)

    if contexte is None:
        try:
            contexte = construire_contexte_plan(
                chemin_csv,
                donnees_athlete=donnees_athlete,
                disponibilites=disponibilites,
            )
        except Exception as erreur:  # CSV illisible, etc.
            return _resultat_erreur(f'Contexte plan illisible : {erreur}', chemin_csv)

    try:
        structure = fournisseur.proposer_modifications(demande, contexte)
    except ClarificationRequise as clarification:
        return {
            'resultat': 'CLARIFICATION_REQUISE',
            'categorie': clarification.categorie,
            'question': clarification.question,
            'questions': [clarification.question],
            'apercu': [],
            'ambiguites': [],
            'conflits': [],
            'erreurs': [],
            'validation': None,
            'modifications_appliquees': 0,
            'chemin': chemin_csv,
            'interpretation': None,
        }
    except Exception as erreur:
        return _resultat_erreur(f'Fournisseur IA en échec : {erreur}', chemin_csv)

    if structure is None:
        question = "La demande n'a pas pu être interprétée."
        return {
            'resultat': 'CLARIFICATION_REQUISE',
            'categorie': 'INCOMPRIS',
            'question': question,
            'questions': [question],
            'apercu': [],
            'ambiguites': [],
            'conflits': [],
            'erreurs': [],
            'validation': None,
            'modifications_appliquees': 0,
            'chemin': chemin_csv,
            'interpretation': None,
        }

    # Délégation au moteur déterministe existant : unique application.
    if ecrire:
        resultat = appliquer_modifications_structurees(
            chemin_csv, structure,
            disponibilites=disponibilites,
            date_reference=date_reference,
            chemin_sortie=chemin_sortie,
        )
    else:
        resultat = previsualiser_modifications(
            chemin_csv, structure,
            disponibilites=disponibilites,
            date_reference=date_reference,
        )

    resultat = dict(resultat)
    resultat['interpretation'] = structure
    return resultat
