# ============================================================
# FICHIER: src/planificateur/__init__.py
# RÔLE: Point d'entrée du module planificateur
#       Exporte la fonction principale de planification
# ============================================================

from .main_plan import planifier_athlete

__all__ = ['planifier_athlete']