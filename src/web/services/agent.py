# ============================================================
# FICHIER: src/web/services/agent.py
# RÔLE: Service Web de l'agent IA (APERÇU puis CONFIRMATION).
#
#       Chaîne :
#           demande → fournisseur IA (injecté)
#                   → contrat existant
#                   → traiter_demande_ia → moteur existant
#                   → validation existante
#                   → aperçu serveur (empreinte du CSV)
#           [CONFIRMER] → réécriture via PlanRepository
#
#       L'IA n'écrit JAMAIS : seul le moteur (via PlanRepository) écrit,
#       et uniquement après confirmation explicite. Le navigateur ne
#       fournit jamais de chemin : l'aperçu est identifié par un jeton
#       opaque conservé côté serveur.
# ============================================================

import hashlib
import secrets
import threading
import time
from typing import Dict, Optional

from planificateur.fournisseur_ia import traiter_demande_ia
from planificateur.validateur_plan import valider_plan_csv

from . import plans as plans_service

# Durée de vie d'une prévisualisation (secondes).
DUREE_APERCU_SECONDES = 900

_VERROU = threading.Lock()
_APERCUS: Dict[str, Dict] = {}


class FournisseurStructure:
    """Fournisseur INTERNE qui rejoue une structure déjà produite.

    Utilisé uniquement à la confirmation, pour réappliquer la
    modification validée sans rappeler l'IA. Il respecte le même
    contrat que les autres fournisseurs (``proposer_modifications``).
    """

    def __init__(self, structure):
        self._structure = structure

    def proposer_modifications(self, demande: str, contexte: Dict):
        return self._structure


def traiter_demande_ia_plan(entree: Dict,
                            demande: str,
                            fournisseur,
                            donnees_athlete: Optional[Dict] = None,
                            disponibilites: Optional[Dict] = None,
                            date_reference=None,
                            ecrire: bool = False,
                            chemin_sortie: Optional[str] = None) -> Dict:
    """Traite une demande IA pour une entrée de plan (via son chemin)."""
    return traiter_demande_ia(
        entree['chemin'],
        demande,
        fournisseur,
        donnees_athlete=donnees_athlete,
        disponibilites=disponibilites,
        date_reference=date_reference,
        ecrire=ecrire,
        chemin_sortie=chemin_sortie,
    )


def _empreinte(entree: Dict, repository=None) -> str:
    """Empreinte du contenu courant du plan (jamais un chemin exposé)."""
    df = plans_service.lire_plan(entree, repository)
    contenu = df.to_csv(index=False, sep=';')
    return hashlib.sha256(contenu.encode('utf-8')).hexdigest()


def _liste_modifications(interpretation) -> list:
    if interpretation is None:
        return []
    if isinstance(interpretation, dict) and 'modifications' in interpretation:
        return list(interpretation.get('modifications') or [])
    if isinstance(interpretation, dict):
        return [interpretation]
    if isinstance(interpretation, list):
        return list(interpretation)
    return []


def _refus(resultat: str, message: str) -> Dict:
    return {
        'resultat': resultat,
        'erreurs': [message],
        'confirmation_requise': False,
    }


def _apercu_expire(apercu: Dict) -> bool:
    return (time.monotonic() - apercu.get('cree', 0)) > DUREE_APERCU_SECONDES


def generer_apercu(entree: Dict,
                   demande: str,
                   fournisseur,
                   repository=None,
                   donnees_athlete: Optional[Dict] = None,
                   disponibilites: Optional[Dict] = None,
                   date_reference=None) -> Dict:
    """Génère un aperçu AVANT/APRÈS sans JAMAIS écrire le CSV courant."""
    empreinte = _empreinte(entree, repository)

    resultat = traiter_demande_ia_plan(
        entree, demande, fournisseur,
        donnees_athlete=donnees_athlete,
        disponibilites=disponibilites,
        date_reference=date_reference,
        ecrire=False,
    )
    statut = resultat.get('resultat')

    if statut == 'CLARIFICATION_REQUISE':
        return {
            'resultat': 'CLARIFICATION_REQUISE',
            'question': resultat.get('question'),
            'questions': resultat.get('questions', []),
            'confirmation_requise': False,
        }
    if statut == 'ERREUR_IA':
        return {
            'resultat': 'ERREUR_IA',
            'erreurs': resultat.get('erreurs', []),
            'confirmation_requise': False,
        }
    if statut == 'AMBIGU':
        return {
            'resultat': 'AMBIGU',
            'question': resultat.get('question'),
            'ambiguites': resultat.get('ambiguites', []),
            'confirmation_requise': False,
        }
    if statut == 'CONFLIT':
        return {
            'resultat': 'CONFLIT',
            'conflits': resultat.get('conflits', []),
            'erreurs': resultat.get('erreurs', []),
            'confirmation_requise': False,
        }
    if statut == 'INVALIDE':
        return {
            'resultat': 'INVALIDE',
            'erreurs': resultat.get('erreurs', []),
            'validation': resultat.get('validation'),
            'confirmation_requise': False,
        }
    if statut == 'ERREUR_SCHEMA':
        return {
            'resultat': 'ERREUR_SCHEMA',
            'erreurs': resultat.get('erreurs', []),
            'confirmation_requise': False,
        }

    if resultat.get('modifications_appliquees', 0) == 0:
        return {
            'resultat': 'AUCUNE_MODIFICATION',
            'erreurs': ['Aucune modification applicable pour cette demande.'],
            'confirmation_requise': False,
        }

    apercu = resultat.get('apercu', [])
    interpretation = resultat.get('interpretation')
    preview_id = secrets.token_urlsafe(32)
    with _VERROU:
        _APERCUS[preview_id] = {
            'identifiant': entree.get('identifiant'),
            'empreinte': empreinte,
            'structure': interpretation,
            'demande': demande,
            'date_reference': date_reference,
            'cree': time.monotonic(),
        }

    return {
        'resultat': 'APERCU',
        'demande': demande,
        'modifications': _liste_modifications(interpretation),
        'avant': [element.get('avant') for element in apercu],
        'apres': [element.get('apres') for element in apercu],
        'validation': resultat.get('validation'),
        'confirmation_requise': True,
        'preview_id': preview_id,
    }


def confirmer_apercu(entree: Dict,
                     preview_id: str,
                     repository=None) -> Dict:
    """Écrit le CSV courant si (et seulement si) l'aperçu est cohérent."""
    with _VERROU:
        apercu = _APERCUS.get(preview_id)

    if apercu is None:
        return _refus('PREVIEW_INCONNUE',
                      "Prévisualisation inconnue ou expirée. Refaites un aperçu.")
    if apercu.get('identifiant') != entree.get('identifiant'):
        with _VERROU:
            _APERCUS.pop(preview_id, None)
        return _refus('PREVIEW_INVALIDE',
                      "Cette prévisualisation ne correspond pas à ce plan.")
    if _apercu_expire(apercu):
        with _VERROU:
            _APERCUS.pop(preview_id, None)
        return _refus('PREVIEW_INCONNUE',
                      "Prévisualisation expirée. Refaites un aperçu.")

    # Contrôle de concurrence : le plan ne doit pas avoir changé.
    if _empreinte(entree, repository) != apercu.get('empreinte'):
        with _VERROU:
            _APERCUS.pop(preview_id, None)
        return _refus('PLAN_MODIFIE',
                      "Le plan a changé depuis l'aperçu. Refaites un aperçu.")

    fournisseur = FournisseurStructure(apercu.get('structure'))
    resultat = traiter_demande_ia_plan(
        entree, apercu.get('demande', ''), fournisseur,
        date_reference=apercu.get('date_reference'),
        ecrire=True, chemin_sortie=entree['chemin'],
    )

    # Prévisualisation à usage unique.
    with _VERROU:
        _APERCUS.pop(preview_id, None)

    validation = valider_plan_csv(entree['chemin'])
    resultat_moteur = resultat.get('resultat')
    return {
        'resultat': 'CONFIRME' if resultat_moteur == 'OK' else resultat_moteur,
        'modifications_appliquees': resultat.get('modifications_appliquees', 0),
        'validation': validation,
        'erreurs': resultat.get('erreurs', []),
        'confirmation_requise': False,
    }


def reinitialiser_apercus() -> None:
    """Vide le registre d'aperçus (isolation des tests)."""
    with _VERROU:
        _APERCUS.clear()
