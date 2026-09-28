# ============================================================
# FICHIER: src/planificateur/agent_plan_csv.py
# RÔLE: Interface de modification du CSV par un agent (IA).
#       AUCUNE connexion IA ici : uniquement le contrat et le
#       moteur déterministe d'application + validation.
#
#       Flux futur :
#         CSV courant + consigne langage naturel + CDC
#              ↓ (FournisseurModifications — DeepSeek/OpenAI/…)
#         liste de modifications CSV
#              ↓ (appliqu_ modifications_csv — déterministe)
#         validation
#              ↓
#         CSV courant mis à jour, ou aucune modification
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd

from stockage import get_plan_repository
from .plan_csv import LIGNES_ENTETE
from .validateur_plan import valider_plan_csv
from .moteur_modifications import (
    executer_demande,
    previsualiser_modifications,
    appliquer_modifications_structurees,
)

__all__ = [
    'FournisseurModifications',
    'appliquer_modifications_csv',
    'executer_demande',
    'previsualiser_modifications',
    'appliquer_modifications_structurees',
]


class FournisseurModifications(ABC):
    """Contrat d'un fournisseur de modifications (indépendant du modèle).

    Une implémentation future (DeepSeek, OpenAI, …) devra renvoyer une liste
    de modifications de la forme ::

        {'ligne': 12, 'colonne': 'Type de séance', 'valeur': 'Endurance'}
        {'ligne': 12, 'colonne': 'Durée (min)', 'valeur': '60'}

    ``ligne`` est l'index dans les lignes de données du CSV (hors en-têtes
    OBJECTIF / COURSES / ---). Le fournisseur ne doit jamais régénérer le plan
    ni écrire lui-même dans le CSV.
    """

    @abstractmethod
    def proposer_modifications(self, chemin_csv: str, consigne: str,
                               contexte: Optional[Dict] = None) -> List[Dict]:
        raise NotImplementedError


def _lire_dataframe(chemin_csv: str) -> pd.DataFrame:
    return get_plan_repository().lire_plan(chemin_csv)


def appliquer_modifications_csv(chemin_csv: str,
                                modifications: List[Dict],
                                chemin_sortie: Optional[str] = None) -> Dict:
    """Applique des modifications de façon déterministe puis valide.

    Le fichier n'est mis à jour QUE si la validation passe. Sinon, aucune
    modification n'est écrite et les erreurs sont retournées.
    """
    try:
        df = _lire_dataframe(chemin_csv)
    except Exception as erreur:
        return {'applique': False, 'erreurs': [f'CSV illisible : {erreur}'],
                'validation': None, 'chemin': chemin_csv}

    masque_entete = df['N° semaine'].isin(LIGNES_ENTETE)
    entetes = df[masque_entete]
    data = df[~masque_entete].reset_index(drop=True)

    erreurs = []
    for modification in modifications or []:
        ligne = modification.get('ligne')
        colonne = modification.get('colonne')
        if not isinstance(ligne, int) or ligne < 0 or ligne >= len(data):
            erreurs.append(f"Ligne hors limites : {ligne!r}")
            continue
        if colonne not in df.columns:
            erreurs.append(f"Colonne inconnue : {colonne!r}")
            continue
        data.at[ligne, colonne] = str(modification.get('valeur', ''))

    if erreurs:
        return {'applique': False, 'erreurs': erreurs, 'validation': None,
                'chemin': chemin_csv}

    df_modifie = pd.concat([entetes, data], ignore_index=True)

    depot = get_plan_repository()
    chemin_temporaire = depot.chemin_temporaire(chemin_csv)
    depot.ecrire_plan(df_modifie, chemin_temporaire)

    validation = valider_plan_csv(chemin_temporaire)
    if not validation['valide']:
        depot.supprimer_plan(chemin_temporaire)
        return {'applique': False, 'erreurs': validation['erreurs'],
                'validation': validation, 'chemin': chemin_csv}

    destination = chemin_sortie or chemin_csv
    depot.remplacer_plan(chemin_temporaire, destination)
    return {'applique': True, 'erreurs': [], 'validation': validation,
            'chemin': destination}
