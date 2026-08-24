# ============================================================
# FICHIER: src/planificateur/generateur/__init__.py
# RÔLE: Point d'entrée du sous-module generateur
# ============================================================

from .generateur_semaine import generer_semaine, generer_plan_complet

__all__ = ['generer_semaine', 'generer_plan_complet']