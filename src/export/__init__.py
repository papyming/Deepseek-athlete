# Fichier vide pour que Python reconnaisse le dossier comme un module# ============================================================
# FICHIER: src/export/__init__.py
# RÔLE: Point d'entrée du module export
#       Exporte les fonctions principales de génération PDF
# ============================================================

from .generateur_pdf import generer_pdf_athlete

__all__ = ['generer_pdf_athlete']