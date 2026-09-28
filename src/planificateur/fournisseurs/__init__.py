# ============================================================
# FICHIER: src/planificateur/fournisseurs/__init__.py
# RÔLE: Fournisseurs IA interchangeables (socle + adaptateurs HTTP).
#
#       Aucun appel réseau n'est déclenché à l'import : les clés API
#       ne sont lues qu'au moment d'une demande.
# ============================================================

from .base_http import (
    ConfigurationManquante,
    ErreurFournisseurIA,
    ErreurHTTPFournisseur,
    FournisseurHTTPAbstrait,
    FournisseurOpenAICompatible,
    ReponseInvalide,
    parser_reponse_ia,
    valider_structure_ia,
)
from .gemini import GeminiFournisseurIA
from .mistral import MistralFournisseurIA
from .openrouter import OpenRouterFournisseurIA

# Adaptateurs HTTP prêts à brancher (Gemini, Mistral, OpenRouter).
FOURNISSEURS_DISPONIBLES = {
    'mistral': MistralFournisseurIA,
    'gemini': GeminiFournisseurIA,
    'openrouter': OpenRouterFournisseurIA,
}

__all__ = [
    'ErreurFournisseurIA',
    'ConfigurationManquante',
    'ReponseInvalide',
    'ErreurHTTPFournisseur',
    'FournisseurHTTPAbstrait',
    'FournisseurOpenAICompatible',
    'MistralFournisseurIA',
    'GeminiFournisseurIA',
    'OpenRouterFournisseurIA',
    'FOURNISSEURS_DISPONIBLES',
    'parser_reponse_ia',
    'valider_structure_ia',
]
