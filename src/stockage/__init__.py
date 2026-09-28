# ============================================================
# FICHIER: src/stockage/__init__.py
# RÔLE: Point d'entrée de la couche de stockage des plans.
#
#       Fournit le dépôt de plans courant (configurable) utilisé par
#       le code métier. Le remplacement futur de l'implémentation
#       (MEGA, Web, base de données) se fera via definir_plan_repository
#       sans modifier le moteur ni les règles métier.
# ============================================================

from .plan_repository import PlanRepository, LocalPlanRepository

_DEPOT_COURANT = LocalPlanRepository()


def get_plan_repository() -> PlanRepository:
    """Retourne le dépôt de plans courant."""
    return _DEPOT_COURANT


def definir_plan_repository(repository: PlanRepository) -> None:
    """Remplace le dépôt de plans courant (tests, web, autre stockage)."""
    global _DEPOT_COURANT
    _DEPOT_COURANT = repository


__all__ = [
    'PlanRepository',
    'LocalPlanRepository',
    'get_plan_repository',
    'definir_plan_repository',
]
