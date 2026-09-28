# ============================================================
# FICHIER: src/planificateur/fournisseurs/gemini.py
# RÔLE: Adaptateur Google Gemini (API generateContent).
#
#       - clé : variable d'environnement GEMINI_API_KEY (transmise par
#         en-tête x-goog-api-key, jamais dans l'URL pour éviter toute fuite) ;
#       - modèle : GEMINI_MODEL (défaut configurable) ;
#       - sortie : structure conforme à contrat_modifications.py.
#
#       Aucun appel réseau à l'import. Aucun accès disque.
# ============================================================

import httpx

from .base_http import FournisseurHTTPAbstrait, ReponseInvalide

__all__ = ['GeminiFournisseurIA']

_URL_MODELE = 'https://generativelanguage.googleapis.com/v1beta/models'


class GeminiFournisseurIA(FournisseurHTTPAbstrait):
    """Fournisseur IA Google Gemini."""

    nom = 'gemini'
    nom_variable_cle = 'GEMINI_API_KEY'
    nom_variable_modele = 'GEMINI_MODEL'
    # Alias stable aligné sur la documentation Google, surchargeable.
    modele_par_defaut = 'gemini-flash-latest'

    def _construire_requete(self, cle: str, modele: str, systeme: str,
                            utilisateur: str) -> dict:
        return {
            'url': f'{_URL_MODELE}/{modele}:generateContent',
            'headers': {
                'x-goog-api-key': cle,
                'Content-Type': 'application/json',
            },
            'payload': {
                'system_instruction': {'parts': [{'text': systeme}]},
                'contents': [
                    {'role': 'user', 'parts': [{'text': utilisateur}]},
                ],
                'generationConfig': {
                    'temperature': 0,
                    'responseMimeType': 'application/json',
                },
            },
        }

    def _extraire_texte(self, reponse: httpx.Response) -> str:
        donnees = self._json_reponse(reponse)
        candidats = donnees.get('candidates')
        if not isinstance(candidats, list) or not candidats:
            raise ReponseInvalide(
                "Réponse Gemini sans résultat exploitable (blocage ou vide)."
            )
        contenu = candidats[0].get('content') if isinstance(candidats[0], dict) else None
        parties = contenu.get('parts') if isinstance(contenu, dict) else None
        if not isinstance(parties, list) or not parties:
            raise ReponseInvalide("Réponse Gemini sans contenu textuel.")
        texte = parties[0].get('text') if isinstance(parties[0], dict) else None
        if not isinstance(texte, str) or not texte.strip():
            raise ReponseInvalide("Réponse Gemini vide.")
        return texte
