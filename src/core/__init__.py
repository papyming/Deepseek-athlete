# Fichier vide pour que Python reconnaisse le dossier comme un module# ============================================================
# FICHIER: src/core/__init__.py
# RÔLE: Point d'entrée du module core
# ============================================================

from .physiologie import Physiologie
from .physiologie_simple import PhysiologieSimple
from .p_code_vma import generer_seances_vma
from .p_code_vc import generer_seances_vc

__all__ = [
    'Physiologie',
    'PhysiologieSimple',
    'generer_seances_vma',
    'generer_seances_vc'
]