# ============================================================
# FICHIER: src/planificateur/fournisseurs/mistral.py
# RÔLE: Adaptateur Mistral (API HTTP JSON OpenAI-compatible).
#
#       - clé : variable d'environnement MISTRAL_API_KEY ;
#       - modèle : MISTRAL_MODEL (défaut configurable) ;
#       - sortie : structure conforme à contrat_modifications.py.
#
#       Aucun appel réseau à l'import. Aucun accès disque.
# ============================================================

from .base_http import FournisseurOpenAICompatible

__all__ = ['MistralFournisseurIA']


class MistralFournisseurIA(FournisseurOpenAICompatible):
    """Fournisseur IA Mistral."""

    nom = 'mistral'
    nom_variable_cle = 'MISTRAL_API_KEY'
    nom_variable_modele = 'MISTRAL_MODEL'
    # Valeur par défaut alignée sur la documentation Mistral (modèles
    # « -latest » stables), surchargeable via MISTRAL_MODEL.
    modele_par_defaut = 'mistral-small-latest'
    url_api = 'https://api.mistral.ai/v1/chat/completions'
