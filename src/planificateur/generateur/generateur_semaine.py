# ============================================================
# FICHIER: src/planificateur/generateur/generateur_semaine.py
# RÔLE: Orchestrateur - réexporte les fonctions principales
# ============================================================

from .semaine import generer_plan_complet

# Réexport pour compatibilité
generer_semaine = generer_plan_complet

__all__ = ['generer_semaine', 'generer_plan_complet']