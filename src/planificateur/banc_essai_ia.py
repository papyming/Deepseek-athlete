# ============================================================
# FICHIER: src/planificateur/banc_essai_ia.py
# RÔLE: Banc d'essai des fournisseurs IA.
#
#       Il teste UNIQUEMENT :
#
#           demande → IA → JSON → contrat
#
#       Il NE lance PAS le moteur de modification et NE TOUCHE
#       JAMAIS aux CSV. Il produit des résultats FACTUELS par
#       demande (succès, structure, erreur, temps, conformité,
#       clarification, critères attendus).
#
#       Aucun appel réseau n'est effectué par ce module lui-même :
#       il utilise le fournisseur qu'on lui injecte.
# ============================================================

import json
import time
from typing import Dict, Iterable, List, Optional, Union

from .contrat_modifications import (
    ACTION_INCOMPRIS,
    normaliser_action,
    normaliser_discipline,
    normaliser_demande,
    normaliser_type_seance,
)
from .fournisseurs.base_http import valider_structure_ia

__all__ = [
    'DEMANDES_REFERENCE',
    'tester_fournisseur',
    'evaluer_criteres',
    'est_clarification',
]

# Jeu de référence : 10 demandes + critères FACTUELS attendus.
# Les critères sont volontairement non exclusifs (plusieurs
# interprétations légitimes possibles).
DEMANDES_REFERENCE: List[Dict] = [
    {
        'id': 1,
        'demande': "Mets une intensité CAP en VMA de 500 m le jeudi 26/11/2026.",
        'criteres': {
            'discipline': {'CAP'},
            'type_seance': {'INTENSITE'},
            'contient': {'500'},
            'action': {'AJOUTER', 'REMPLACER', 'MODIFIER_DETAILS'},
        },
    },
    {
        'id': 2,
        'demande': "Rajoute 1 lundi sur 2 une séance d'endurance en vélo de 3h.",
        'criteres': {
            'action': {'AJOUTER'},
            'discipline': {'Vélo'},
            'jour_cible': {'Lundi'},
            'frequence': {'UNE_SEMAINE_SUR_DEUX'},
        },
    },
    {
        'id': 3,
        'demande': 'Mettre toutes les intensités de CAP le mercredi.',
        'criteres': {
            'action': {'DEPLACER'},
            'discipline': {'CAP'},
            'type_seance': {'INTENSITE'},
            'jour_cible': {'Mercredi'},
        },
    },
    {
        'id': 4,
        'demande': 'La natation sera impossible du 1er au 10 août.',
        'criteres': {
            'action': {'SUPPRIMER'},
            'discipline': {'Natation'},
            'periode': {'DATES', 'DATE_DE_FIN', 'SEMAINES'},
        },
    },
    {
        'id': 5,
        'demande': 'Place tous les vendredis les renforcements musculaires '
                   'suivants avec cette ressource : https://youtu.be/exemple',
        'criteres': {
            'action': {'AJOUTER_RESSOURCE'},
            'type_seance': {'RENFORCEMENT'},
            'jour_cible': {'Vendredi'},
            'contient': {'https://youtu.be/exemple'},
        },
    },
    {
        'id': 6,
        'demande': 'Déplace la séance.',
        'criteres': {'clarification': True},
    },
    {
        'id': 7,
        'demande': 'Fais quelque chose de plus dur mercredi.',
        'criteres': {'clarification': True},
    },
    {
        'id': 8,
        'demande': 'Ajoute une séance qui crée volontairement une contrainte '
                   'avec la séance existante.',
        'criteres': {'action': {'AJOUTER'}},
    },
    {
        'id': 9,
        'demande': 'Réduis la durée de la sortie longue CAP du dimanche de 20 minutes.',
        'criteres': {
            'action': {'MODIFIER_DUREE', 'MODIFIER_FREQUENCE'},
            'discipline': {'CAP'},
            'type_seance': {'SORTIE_LONGUE'},
            'duree_delta': {-20},
        },
    },
    {
        'id': 10,
        'demande': 'Intensité natation le jeudi.',
        'criteres': {
            'discipline': {'Natation'},
            'jour_cible': {'Jeudi'},
            'type_seance': {'INTENSITE'},
        },
    },
]


# ------------------------------------------------------------
# Utilitaires factuels
# ------------------------------------------------------------
def _liste_modifications(structure) -> List[Dict]:
    if isinstance(structure, dict) and 'modifications' in structure:
        brut = structure.get('modifications')
        return list(brut) if isinstance(brut, list) else []
    if isinstance(structure, dict):
        return [structure]
    if isinstance(structure, list):
        return list(structure)
    return []


def _normalisees(structure) -> List[Dict]:
    try:
        return normaliser_demande(structure).get('modifications', [])
    except Exception:
        return []


def est_clarification(structure) -> bool:
    """Vrai si la structure demande une clarification (aucune écriture)."""
    for modification in _liste_modifications(structure):
        if not isinstance(modification, dict):
            continue
        if normaliser_action(modification.get('action')) == ACTION_INCOMPRIS:
            return True
        if modification.get('compris') is False:
            return True
        if modification.get('ambigu') or modification.get('periode_ambigue'):
            return True
    return False


def _valeur_critere(valeur):
    if isinstance(valeur, (set, frozenset, list, tuple)):
        return set(valeur)
    return valeur


def evaluer_criteres(structure, criteres: Dict) -> Dict:
    """Évalue chaque critère de façon FACTUELLE (sans imposer de réponse).

    Retourne {'<critère>': bool, ..., 'tous': bool}.
    """
    resultats: Dict[str, bool] = {}
    if not criteres:
        return resultats

    modifications = _normalisees(structure)
    texte = json.dumps(structure, ensure_ascii=False, default=str)

    for critere, attendu in criteres.items():
        if critere == 'clarification':
            resultats[critere] = est_clarification(structure) is bool(attendu)
            continue

        if critere == 'contient':
            morceaux = [str(m) for m in _valeur_critere(attendu)]
            resultats[critere] = all(m in texte for m in morceaux)
            continue

        valeurs = _valeur_critere(attendu)
        resultats[critere] = _critere_satisfait(
            critere, valeurs, modifications, structure
        )

    resultats['tous'] = all(resultats.values())
    return resultats


def _critere_satisfait(critere, valeurs, modifications, structure) -> bool:
    def _dans(valeur):
        return valeur in valeurs

    for modification in modifications:
        if critere == 'action' and _dans(normaliser_action(modification.get('action'))):
            return True
        if critere == 'discipline':
            if _dans(normaliser_discipline(modification.get('discipline'))):
                return True
        elif critere == 'type_seance':
            if _dans(normaliser_type_seance(modification.get('type_seance'))):
                return True
        elif critere == 'jour_cible':
            if _dans(modification.get('jour_cible')):
                return True
        elif critere == 'date_cible':
            brute = modification.get('date_cible')
            if _dans(brute):
                return True
        elif critere == 'duree' and _dans(modification.get('duree')):
            return True
        elif critere == 'duree_delta' and _dans(modification.get('duree_delta')):
            return True
        elif critere == 'periode':
            periode = modification.get('periode')
            if periode is None and 'FIN_DU_PLAN' in valeurs:
                return True
            if isinstance(periode, dict) and _dans(periode.get('type')):
                return True
        elif critere == 'frequence':
            frequence = modification.get('frequence')
            if isinstance(frequence, dict) and _dans(frequence.get('type')):
                return True

    # Repli textuel pour certaines valeurs encodées dans les détails.
    if critere in ('type_seance', 'contient'):
        texte = json.dumps(structure, ensure_ascii=False, default=str)
        return any(str(v) in texte for v in valeurs)
    return False


def _nom_fournisseur(fournisseur) -> str:
    return getattr(fournisseur, 'nom', None) or type(fournisseur).__name__


# ------------------------------------------------------------
# Banc d'essai
# ------------------------------------------------------------
def tester_fournisseur(fournisseur,
                       demandes: Optional[Iterable] = None,
                       contexte: Optional[Dict] = None,
                       horloge=None) -> Dict:
    """Teste un fournisseur sur une liste de demandes (sans toucher au CSV).

    ``demandes`` : liste de chaînes ou d'entrées ``{'id','demande','criteres'}``
    (par défaut : ``DEMANDES_REFERENCE``).
    ``contexte`` : contexte construit par Python.
    """
    entrees = list(demandes) if demandes is not None else list(DEMANDES_REFERENCE)
    horloge = horloge or time.perf_counter
    resultats: List[Dict] = []

    for entree in entrees:
        if isinstance(entree, dict):
            identifiant = entree.get('id')
            demande = entree.get('demande', '')
            criteres = entree.get('criteres') or {}
        else:
            identifiant = None
            demande = str(entree)
            criteres = {}

        debut = horloge()
        structure = None
        erreur = None
        succes = True
        try:
            structure = fournisseur.proposer_modifications(demande, contexte)
        except Exception as exception:  # erreur fournisseur/parse/config
            succes = False
            erreur = str(exception)
        temps = horloge() - debut

        erreurs_contrat = [] if structure is None else valider_structure_ia(structure)
        resultat = {
            'id': identifiant,
            'demande': demande,
            'fournisseur': _nom_fournisseur(fournisseur),
            'succes': succes,
            'structure': structure,
            'erreur': erreur,
            'temps_secondes': temps,
            'conforme_contrat': succes and not erreurs_contrat,
            'erreurs_contrat': erreurs_contrat,
            'clarification': est_clarification(structure),
        }
        if criteres:
            resultat['criteres'] = evaluer_criteres(structure, criteres)
            resultat['criteres_ok'] = bool(resultat['criteres']) and all(
                resultat['criteres'].values()
            )
        resultats.append(resultat)

    total = len(resultats)
    reussis = sum(1 for r in resultats if r['succes'])
    conformes = sum(1 for r in resultats if r['conforme_contrat'])
    clarifications = sum(1 for r in resultats if r['clarification'])
    temps_total = sum(r['temps_secondes'] for r in resultats)

    return {
        'fournisseur': _nom_fournisseur(fournisseur),
        'resultats': resultats,
        'resume': {
            'total': total,
            'reussis': reussis,
            'echecs': total - reussis,
            'conformes': conformes,
            'clarifications': clarifications,
            'temps_total_secondes': temps_total,
            'temps_moyen_secondes': (temps_total / total) if total else 0.0,
        },
    }
