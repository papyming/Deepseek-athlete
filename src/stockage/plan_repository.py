# ============================================================
# FICHIER: src/stockage/plan_repository.py
# RÔLE: Frontière entre la LOGIQUE MÉTIER et le STOCKAGE PHYSIQUE
#       des plans (CSV).
#
#       L'interface PlanRepository ne connaît AUCUN détail physique
#       (ni Windows, ni disque, ni MEGAsync, ni chemin utilisateur).
#       L'implémentation LocalPlanRepository travaille sur le dossier
#       local (actuellement synchronisé par MEGAsync).
#
#       Le CSV reste la donnée opérationnelle : cette couche ne
#       change ni le format, ni les règles, ni le workflow.
# ============================================================

import os
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd

# Un fichier CSV de plan (hors exports) suit la convention
# <Athlete>_plan_<AAAAmmjj_HHMMSS>.csv.
FRAGMENT_PLAN = '_plan_'
FRAGMENT_EXPORT_APERCU = '_plan_apercu_'


class PlanRepository(ABC):
    """Interface de stockage des plans de l'application.

    Aucune notion de système de fichiers dans cette interface : les
    implémentations décident de la localisation physique (local, MEGA,
    stockage serveur, base de données, …).
    """

    @abstractmethod
    def creer_stockage(self) -> None:
        """Crée le stockage s'il n'existe pas (idempotent)."""

    @abstractmethod
    def dossier_plan(self, identifiant: str) -> str:
        """Retourne la localisation du dossier d'un athlète/plan."""

    @abstractmethod
    def lister_plans(self, racine: Optional[str] = None) -> List[Dict]:
        """Liste les plans CSV disponibles (un fichier = une entrée)."""

    @abstractmethod
    def trouver_plan_courant(self, plan_dir: str) -> Optional[str]:
        """Retourne le plan CSV courant d'un dossier (le plus récent)."""

    @abstractmethod
    def lire_plan(self, chemin: str) -> pd.DataFrame:
        """Lit le contenu d'un plan CSV."""

    @abstractmethod
    def existe(self, chemin: str) -> bool:
        """Indique si un plan (ou fichier) existe."""

    @abstractmethod
    def ecrire_plan(self, contenu: pd.DataFrame, chemin: str,
                    separateur: str = ';') -> str:
        """Écrit (ou remplace) un plan CSV et retourne son emplacement."""

    @abstractmethod
    def remplacer_plan(self, source: str, cible: str) -> str:
        """Remplace atomiquement ``cible`` par ``source``."""

    @abstractmethod
    def supprimer_plan(self, chemin: str) -> None:
        """Supprime un plan CSV."""

    @abstractmethod
    def chemin_temporaire(self, chemin_reference: str) -> str:
        """Retourne un emplacement temporaire utilisable près de la référence."""


class LocalPlanRepository(PlanRepository):
    """Implémentation locale (dossier synchronisé par MEGAsync).

    Le chemin racine est configurable ; il ne doit jamais être codé en dur
    dans les modules métier.
    """

    def __init__(self, racine_plans: Optional[str] = None):
        self.racine_plans = racine_plans or os.path.join('outputs', 'plans')

    # ----------------------------------------------------------
    def creer_stockage(self) -> None:
        os.makedirs(self.racine_plans, exist_ok=True)

    def dossier_plan(self, identifiant: str) -> str:
        nom = str(identifiant).replace(' ', '_')
        return os.path.join(self.racine_plans, nom)

    # ----------------------------------------------------------
    def lister_plans(self, racine: Optional[str] = None) -> List[Dict]:
        racine = racine or self.racine_plans
        if not os.path.isdir(racine):
            return []
        entrees = []
        for dossier, _, fichiers in os.walk(racine):
            for nom in fichiers:
                if not self._est_plan(nom):
                    continue
                entrees.append({
                    'athlete': os.path.basename(dossier),
                    'dossier': dossier,
                    'fichier': nom,
                    'chemin': os.path.join(dossier, nom),
                })
        entrees.sort(key=lambda entree: (entree['athlete'].lower(), entree['fichier']))
        return entrees

    def trouver_plan_courant(self, plan_dir: str) -> Optional[str]:
        if not os.path.isdir(plan_dir):
            return None
        candidats = []
        for nom in os.listdir(plan_dir):
            if self._est_plan(nom):
                candidats.append(os.path.join(plan_dir, nom))
        if not candidats:
            return None
        candidats.sort(key=lambda chemin: os.path.getmtime(chemin), reverse=True)
        return candidats[0]

    # ----------------------------------------------------------
    def lire_plan(self, chemin: str) -> pd.DataFrame:
        return pd.read_csv(
            chemin, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False
        )

    def existe(self, chemin: str) -> bool:
        return bool(chemin) and os.path.exists(chemin)

    def ecrire_plan(self, contenu: pd.DataFrame, chemin: str,
                    separateur: str = ';') -> str:
        dossier = os.path.dirname(os.path.abspath(chemin))
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        contenu.to_csv(chemin, sep=separateur, index=False, encoding='utf-8-sig')
        return chemin

    def remplacer_plan(self, source: str, cible: str) -> str:
        os.replace(source, cible)
        return cible

    def supprimer_plan(self, chemin: str) -> None:
        try:
            os.remove(chemin)
        except OSError:
            pass

    def chemin_temporaire(self, chemin_reference: str) -> str:
        dossier = os.path.dirname(os.path.abspath(chemin_reference)) or '.'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', prefix='plan_', delete=False,
            dir=dossier, encoding='utf-8-sig', newline='',
        ) as temporaire:
            return temporaire.name

    # ----------------------------------------------------------
    @staticmethod
    def _est_plan(nom_fichier: str) -> bool:
        nom = str(nom_fichier).lower()
        if not nom.endswith('.csv'):
            return False
        if FRAGMENT_PLAN not in nom:
            return False
        if FRAGMENT_EXPORT_APERCU in nom:
            return False
        return True
