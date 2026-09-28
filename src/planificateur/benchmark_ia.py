# ============================================================
# FICHIER: src/planificateur/benchmark_ia.py
# RÔLE: Benchmark RÉEL de Phase 2B.
#
#       Envoie les 10 demandes représentatives de référence à un
#       fournisseur IA réel (par défaut OpenRouterFournisseurIA) et
#       classe chaque réponse :
#
#           OK / CLARIFICATION_REQUISE / ERREUR / NON_CONFORME
#
#       Conformité vérifiée avec le contrat EXISTANT
#       (src/planificateur/contrat_modifications.py) via
#       ``valider_structure_ia`` : ce module ne redéfinit rien.
#
#       Ce module NE MODIFIE AUCUN CSV et NE TOUCHE AUCUN fichier de
#       production : il LIT le plan pour construire le contexte, appelle
#       le fournisseur, puis se contente d'afficher/agréger.
#       Il n'invoque JAMAIS le moteur de modifications.
#
#       Aucun appel réseau n'est effectué à l'import : le fournisseur
#       par défaut n'est instancié que dans ``lancer_benchmark``/``main``.
# ============================================================

import argparse
import json
import sys
import time
from typing import Dict, Iterable, List, Optional

from .banc_essai_ia import (
    DEMANDES_REFERENCE,
    est_clarification,
    evaluer_criteres,
)
from .contexte_plan import construire_contexte_plan
from .fournisseurs.base_http import valider_structure_ia
from .fournisseurs.openrouter import OpenRouterFournisseurIA

__all__ = [
    'STATUT_OK',
    'STATUT_CLARIFICATION',
    'STATUT_ERREUR',
    'STATUT_NON_CONFORME',
    'MODELE_PAR_DEFAUT',
    'demandes_benchmark',
    'fournisseur_par_defaut',
    'classer_reponse',
    'lancer_benchmark',
    'formater_rapport',
    'afficher_rapport',
    'main',
]

# ---- STATUTS DE CLASSIFICATION FACTUELLE ----
STATUT_OK = 'OK'
STATUT_CLARIFICATION = 'CLARIFICATION_REQUISE'
STATUT_ERREUR = 'ERREUR'
# Correspond à une « réponse non conforme » (échoue au contrat existant).
STATUT_NON_CONFORME = 'NON_CONFORME'

# Modèle gratuit par défaut, surchargeable via OPENROUTER_MODEL.
# La valeur provient du fournisseur réel : aucune duplication de code.
MODELE_PAR_DEFAUT = OpenRouterFournisseurIA.modele_par_defaut


def demandes_benchmark() -> List[Dict]:
    """Les 10 demandes représentatives de référence (copie défensive)."""
    return [dict(entree) for entree in DEMANDES_REFERENCE]


def fournisseur_par_defaut(*, modele: Optional[str] = None,
                           api_key: Optional[str] = None,
                           timeout: float = 60.0) -> OpenRouterFournisseurIA:
    """Construit le fournisseur OpenRouter réel (aucun appel réseau ici).

    Clé : ``OPENROUTER_API_KEY`` ; modèle : ``OPENROUTER_MODEL`` puis
    ``openrouter/free`` par défaut (géré par le fournisseur existant).
    """
    return OpenRouterFournisseurIA(
        api_key=api_key, model=modele, timeout=timeout
    )


def _nom_fournisseur(fournisseur) -> str:
    return getattr(fournisseur, 'nom', None) or type(fournisseur).__name__


def _modele_fournisseur(fournisseur) -> Optional[str]:
    try:
        return getattr(fournisseur, 'modele', None)
    except Exception:
        return None


def classer_reponse(structure, erreur=None,
                    erreurs_contrat=None) -> str:
    """Classe une réponse de façon FACTUELLE (sans juger de l'à-propos).

    - ``erreur`` non nul : ERREUR (fournisseur/réseau/config) ;
    - structure absente ou non conforme : NON_CONFORME ;
    - clarification (INCOMPRIS/ambigu) : CLARIFICATION_REQUISE ;
    - sinon : OK.
    """
    if erreur is not None:
        return STATUT_ERREUR
    if structure is None or erreurs_contrat:
        return STATUT_NON_CONFORME
    if est_clarification(structure):
        return STATUT_CLARIFICATION
    return STATUT_OK


def _entree(entree):
    if isinstance(entree, dict):
        return (
            entree.get('id'),
            entree.get('demande', ''),
            entree.get('criteres') or {},
        )
    return None, str(entree), {}


def lancer_benchmark(fournisseur=None,
                     chemin_csv: Optional[str] = None,
                     demandes: Optional[Iterable] = None,
                     contexte: Optional[Dict] = None,
                     donnees_athlete: Optional[Dict] = None,
                     disponibilites: Optional[Dict] = None,
                     horloge=None,
                     modele: Optional[str] = None,
                     api_key: Optional[str] = None,
                     timeout: float = 60.0) -> Dict:
    """Exécute le benchmark sur les demandes et retourne un rapport.

    ``fournisseur`` : tout objet exposant ``proposer_modifications``
    (par défaut : ``OpenRouterFournisseurIA``).
    ``chemin_csv`` : chemin LECTURE seule pour construire le contexte.
    Aucune écriture CSV n'est jamais réalisée.
    """
    if fournisseur is None:
        fournisseur = fournisseur_par_defaut(
            modele=modele, api_key=api_key, timeout=timeout
        )

    contexte_erreur = None
    if contexte is None:
        if chemin_csv is not None:
            try:
                contexte = construire_contexte_plan(
                    chemin_csv,
                    donnees_athlete=donnees_athlete,
                    disponibilites=disponibilites,
                )
            except Exception as exception:  # CSV illisible, etc.
                contexte = {}
                contexte_erreur = str(exception)
        else:
            contexte = {}

    entrees = list(demandes) if demandes is not None else demandes_benchmark()
    horloge = horloge or time.perf_counter
    resultats: List[Dict] = []

    for entree in entrees:
        identifiant, demande, criteres = _entree(entree)

        debut = horloge()
        structure = None
        erreur = None
        try:
            structure = fournisseur.proposer_modifications(demande, contexte)
        except Exception as exception:  # fournisseur/parse/config/réseau
            erreur = f'{type(exception).__name__}: {exception}'
        temps = horloge() - debut

        erreurs_contrat = [] if erreur is not None else valider_structure_ia(structure)
        statut = classer_reponse(
            structure, erreur=erreur, erreurs_contrat=erreurs_contrat
        )

        resultat = {
            'id': identifiant,
            'demande': demande,
            'fournisseur': _nom_fournisseur(fournisseur),
            'statut': statut,
            'succes': erreur is None,
            'structure': structure,
            'erreur': erreur,
            'temps_secondes': temps,
            'conforme_contrat': (
                erreur is None and structure is not None and not erreurs_contrat
            ),
            'erreurs_contrat': erreurs_contrat,
            'clarification': (
                est_clarification(structure) if structure is not None else False
            ),
        }
        if criteres:
            resultat['criteres'] = evaluer_criteres(structure, criteres)
            resultat['criteres_ok'] = bool(resultat['criteres']) and all(
                resultat['criteres'].values()
            )
        resultats.append(resultat)

    total = len(resultats)
    temps_total = sum(r['temps_secondes'] for r in resultats)
    resume = {
        'total': total,
        'ok': sum(1 for r in resultats if r['statut'] == STATUT_OK),
        'clarifications': sum(
            1 for r in resultats if r['statut'] == STATUT_CLARIFICATION
        ),
        'erreurs': sum(1 for r in resultats if r['statut'] == STATUT_ERREUR),
        'non_conformes': sum(
            1 for r in resultats if r['statut'] == STATUT_NON_CONFORME
        ),
        'conformes_contrat': sum(1 for r in resultats if r['conforme_contrat']),
        'temps_total_secondes': temps_total,
        'temps_moyen_secondes': (temps_total / total) if total else 0.0,
    }

    return {
        'fournisseur': _nom_fournisseur(fournisseur),
        'modele': _modele_fournisseur(fournisseur),
        'contexte_erreur': contexte_erreur,
        'resultats': resultats,
        'resume': resume,
    }


def formater_rapport(rapport: Dict) -> str:
    """Rend un rapport lisible : statut + réponse structurée par demande."""
    lignes: List[str] = []
    lignes.append(
        f"Benchmark IA — fournisseur={rapport.get('fournisseur')} "
        f"modèle={rapport.get('modele')}"
    )
    if rapport.get('contexte_erreur'):
        lignes.append(f"Contexte incomplet : {rapport['contexte_erreur']}")

    for resultat in rapport.get('resultats', []):
        lignes.append('-' * 60)
        lignes.append(
            f"[{resultat.get('statut')}] Demande {resultat.get('id')} : "
            f"{resultat.get('demande')}"
        )
        lignes.append(
            "Conforme au contrat : "
            + ('oui' if resultat.get('conforme_contrat') else 'non')
        )
        if resultat.get('erreurs_contrat'):
            lignes.append(
                'Erreurs de contrat : ' + ' ; '.join(resultat['erreurs_contrat'])
            )
        if resultat.get('erreur'):
            lignes.append('Erreur : ' + str(resultat['erreur']))
        lignes.append('Réponse structurée reçue :')
        lignes.append(
            json.dumps(resultat.get('structure'), ensure_ascii=False,
                       indent=2, default=str)
        )

    lignes.append('=' * 60)
    lignes.append(
        'Résumé : '
        + json.dumps(rapport.get('resume') or {}, ensure_ascii=False,
                     default=str)
    )
    return '\n'.join(lignes)


def afficher_rapport(rapport: Dict, sortie=print) -> None:
    """Affiche le rapport (``print`` par défaut, injectable en test)."""
    sortie(formater_rapport(rapport))


def main(argv=None) -> int:
    """Point d'entrée CLI (seul endroit qui peut déclencher le réseau)."""
    parseur = argparse.ArgumentParser(
        description="Benchmark IA des 10 demandes représentatives (Phase 2B)."
    )
    parseur.add_argument(
        'chemin_csv', nargs='?', default=None,
        help='Plan CSV en LECTURE seule pour construire le contexte.',
    )
    parseur.add_argument(
        '--modele', default=None,
        help='Modèle OpenRouter (défaut : OPENROUTER_MODEL puis openrouter/free).',
    )
    parseur.add_argument('--timeout', type=float, default=60.0)
    args = parseur.parse_args(argv)

    rapport = lancer_benchmark(
        chemin_csv=args.chemin_csv, modele=args.modele, timeout=args.timeout
    )
    afficher_rapport(rapport)

    resume = rapport['resume']
    return 1 if (resume['erreurs'] or resume['non_conformes']) else 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
