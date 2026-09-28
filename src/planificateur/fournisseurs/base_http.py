# ============================================================
# FICHIER: src/planificateur/fournisseurs/base_http.py
# RÔLE: Code RÉELLEMENT COMMUN aux fournisseurs IA HTTP.
#
#       - lecture des clés API par variables d'environnement ;
#       - appel HTTP JSON minimal (httpx, déjà présent) ;
#       - prompt structuré commun (contrat de modifications) ;
#       - parsing STRICT : aucun texte avant/après le JSON, aucune
#         réparation silencieuse, aucun champ inconnu toléré ;
#       - validation de structure contre contrat_modifications.py.
#
#       Un fournisseur ne reçoit JAMAIS de chemin de fichier et
#       n'écrit JAMAIS de fichier. Il ne retourne que des données.
#
#       AUCUN appel réseau n'est effectué à l'import de ce module.
# ============================================================

import json
import os
from typing import Dict, List, Optional

import httpx

from ..contrat_modifications import (
    ACTIONS,
    DETAILS_MODES,
    FREQUENCES,
    PERIODES,
    TYPES_SEANCE,
    normaliser_action,
    normaliser_discipline,
    normaliser_frequence,
    normaliser_modification,
    normaliser_periode,
    normaliser_type_seance,
    valider_contrat,
)
from ..fournisseur_ia import FournisseurIAAbstrait

__all__ = [
    'ErreurFournisseurIA',
    'ConfigurationManquante',
    'ReponseInvalide',
    'ErreurHTTPFournisseur',
    'FournisseurHTTPAbstrait',
    'FournisseurOpenAICompatible',
    'PROMPT_SYSTEME',
    'construire_message_utilisateur',
    'parser_reponse_ia',
    'valider_structure_ia',
]

# ---- Disciplines acceptées par le contrat de modifications ----
DISCIPLINES_VALIDES = {'CAP', 'Vélo', 'Natation', 'Renforcement', 'Course'}

# Champs autorisés dans une modification (contrat existant).
CHAMPS_MODIFICATION = {
    'action', 'discipline', 'type_seance', 'cible', 'date_cible', 'jour_cible',
    'jour', 'periode', 'periode_ambigue', 'ambigu_periode', 'ambigu', 'compris',
    'question', 'duree', 'duree_delta', 'frequence', 'details', 'details_mode',
    'ressources', 'raison', 'commentaire', 'contraintes',
}
# Champs autorisés dans une cible de séance.
CHAMPS_CIBLE = {'discipline', 'type_seance', 'jour', 'date', 'difficulte'}


# ============================================================
# ERREURS EXPLICITES (jamais de clé API dans les messages)
# ============================================================
class ErreurFournisseurIA(Exception):
    """Erreur d'un fournisseur IA (configuration, réseau, réponse)."""


class ConfigurationManquante(ErreurFournisseurIA):
    """Clé API absente : le fournisseur ne doit pas être contacté."""

    def __init__(self, nom_variable: str):
        self.nom_variable = nom_variable
        super().__init__(
            f"Clé API absente : la variable d'environnement {nom_variable} "
            "n'est pas définie. Aucune requête n'a été envoyée."
        )


class ReponseInvalide(ErreurFournisseurIA):
    """Réponse IA invalide (JSON incorrect, champ inconnu, valeur invalide)."""


class ErreurHTTPFournisseur(ErreurFournisseurIA):
    """Erreur HTTP ou réseau lors de l'appel au fournisseur."""

    def __init__(self, statut, message: str = ''):
        self.statut = statut
        super().__init__(f"Erreur fournisseur ({statut}){': ' + message if message else ''}.")


# ============================================================
# PROMPT STRUCTURÉ COMMUN
# ============================================================
PROMPT_SYSTEME = (
    "Tu es un interpréteur de demandes d'entraînement pour un coach.\n"
    "Tu ne calcules rien et tu ne modifies aucun fichier : tu produis "
    "UNIQUEMENT une structure JSON conforme au contrat de modifications.\n\n"
    "RÈGLES DE SORTIE (STRICTES) :\n"
    "- Réponds EXCLUSIVEMENT par un objet JSON valide.\n"
    "- Aucun texte avant, aucun texte après, aucune balise Markdown, "
    "aucun commentaire.\n"
    "- N'invente aucun champ. Utilise uniquement les champs listés.\n"
    "- N'utilise ni chemin de fichier, ni CSV, ni code Python.\n\n"
    "ACTIONS POSSIBLES : " + ', '.join(sorted(ACTIONS)) + "\n"
    "DISCIPLINES : CAP, Vélo, Natation, Renforcement, Course\n"
    "TYPES DE SÉANCE : " + ', '.join(sorted(TYPES_SEANCE)) + "\n"
    "PÉRIODES : " + ', '.join(sorted(PERIODES)) + "\n"
    "FRÉQUENCES : " + ', '.join(sorted(FREQUENCES)) + "\n"
    "MODES DE DÉTAILS : " + ', '.join(sorted(DETAILS_MODES)) + "\n\n"
    "CHAMPS UTILISABLES DANS UNE MODIFICATION : action, discipline, "
    "type_seance, cible (discipline, type_seance, jour, date, difficulte), "
    "date_cible, jour_cible, periode, frequence, duree, duree_delta, "
    "details, details_mode, ressources, raison, question.\n\n"
    "RÈGLES MÉTIER :\n"
    "- Création récurrente sans période explicite : période = FIN_DU_PLAN.\n"
    "- Si la demande est ambiguë ou incomprise : utilise "
    "{\"action\": \"INCOMPRIS\", \"question\": \"...\"} avec UNIQUEMENT "
    "l'information réellement bloquante.\n"
    "- Ne devine jamais une information manquante indispensable.\n"
    "- Un déplacement ambigu (plusieurs séances possibles) : ajoute "
    "\"ambigu\": true et une \"question\".\n\n"
    "EXEMPLE :\n"
    "{\"action\": \"AJOUTER\", \"discipline\": \"Vélo\", "
    "\"type_seance\": \"ENDURANCE\", \"jour_cible\": \"Lundi\", "
    "\"duree\": 180, \"frequence\": {\"type\": \"UNE_SEMAINE_SUR_DEUX\"}, "
    "\"periode\": {\"type\": \"FIN_DU_PLAN\"}}\n"
)


def construire_message_utilisateur(demande: str, contexte: Dict) -> str:
    """Message utilisateur commun : contexte Python + demande libre."""
    contexte_json = json.dumps(contexte or {}, ensure_ascii=False, indent=2,
                               default=str)
    return (
        "CONTEXTE DU PLAN (fourni par Python, JSON) :\n"
        f"{contexte_json}\n\n"
        "DEMANDE DU COACH :\n"
        f"{demande}\n\n"
        "Réponds uniquement par l'objet JSON."
    )


# ============================================================
# PARSING STRICT
# ============================================================
def _sans_texte_autour(contenu: str):
    """Vérifie qu'il n'y a ni texte avant ni après le JSON."""
    if not (contenu.startswith('{') or contenu.startswith('[')):
        raise ReponseInvalide(
            "La réponse ne commence pas par un JSON (texte avant détecté)."
        )
    if not (contenu.endswith('}') or contenu.endswith(']')):
        raise ReponseInvalide(
            "La réponse ne se termine pas par un JSON (texte après détecté)."
        )


def parser_reponse_ia(texte) -> object:
    """Transforme une réponse brute en structure, ou lève ``ReponseInvalide``.

    Aucune réparation : le JSON doit être pur et conforme au contrat.
    """
    if not isinstance(texte, str) or not texte.strip():
        raise ReponseInvalide("Réponse vide ou non textuelle.")
    contenu = texte.strip()
    _sans_texte_autour(contenu)
    try:
        structure = json.loads(contenu)
    except json.JSONDecodeError as erreur:
        raise ReponseInvalide(
            f"JSON invalide ({erreur.msg}, position {erreur.pos})."
        )
    erreurs = valider_structure_ia(structure)
    if erreurs:
        raise ReponseInvalide(' ; '.join(erreurs))
    return structure


def valider_structure_ia(structure) -> List[str]:
    """Valide STRICTEMENT une structure IA contre le contrat existant.

    Retourne une liste d'erreurs explicites (vide si conforme).
    """
    if structure is None:
        return ["Réponse vide."]

    erreurs: List[str] = []
    if isinstance(structure, dict) and 'modifications' in structure:
        inconnus = set(structure) - {'modifications'}
        if inconnus:
            erreurs.append(
                "Champ(s) inconnu(s) au niveau racine : "
                + ', '.join(sorted(inconnus))
            )
        liste = structure.get('modifications')
    elif isinstance(structure, dict):
        liste = [structure]
    elif isinstance(structure, list):
        liste = structure
    else:
        return ["Structure IA non supportée (objet ou liste JSON attendu)."]

    if not isinstance(liste, list):
        return ["Le champ 'modifications' doit être une liste."]
    if not liste:
        return ["Aucune modification fournie."]

    for index, item in enumerate(liste):
        prefixe = f"Modification {index} : "
        if not isinstance(item, dict):
            erreurs.append(prefixe + "objet JSON attendu.")
            continue

        inconnus = set(item) - CHAMPS_MODIFICATION
        if inconnus:
            erreurs.append(
                prefixe + "champ(s) inconnu(s) : " + ', '.join(sorted(inconnus))
            )

        cible = item.get('cible')
        if cible is not None:
            if not isinstance(cible, dict):
                erreurs.append(prefixe + "'cible' doit être un objet.")
            else:
                inconnus_cible = set(cible) - CHAMPS_CIBLE
                if inconnus_cible:
                    erreurs.append(
                        prefixe + "champ(s) de cible inconnu(s) : "
                        + ', '.join(sorted(inconnus_cible))
                    )

        for erreur_contrat in valider_contrat(normaliser_modification(item)):
            erreurs.append(prefixe + erreur_contrat)

        action = normaliser_action(item.get('action'))
        if action and action not in ACTIONS:
            erreurs.append(prefixe + f"action invalide : {action!r}.")

        discipline = normaliser_discipline(item.get('discipline'))
        if discipline and discipline not in DISCIPLINES_VALIDES:
            erreurs.append(prefixe + f"discipline invalide : {discipline!r}.")

        type_seance = normaliser_type_seance(item.get('type_seance'))
        if type_seance and type_seance not in TYPES_SEANCE:
            erreurs.append(prefixe + f"type_seance invalide : {type_seance!r}.")

        periode = item.get('periode')
        if periode is not None:
            periode_norm = normaliser_periode(periode)
            if not isinstance(periode_norm, dict) or periode_norm.get('type') not in PERIODES:
                erreurs.append(prefixe + "période invalide.")

        frequence = item.get('frequence')
        if frequence is not None:
            frequence_norm = normaliser_frequence(frequence)
            if 'intervalle' in frequence_norm:
                if not isinstance(frequence_norm['intervalle'], int):
                    erreurs.append(prefixe + "intervalle de fréquence invalide.")
            elif frequence_norm.get('type') not in FREQUENCES:
                erreurs.append(prefixe + "fréquence invalide.")

        details_mode = item.get('details_mode')
        if details_mode is not None and normaliser_action(details_mode) not in DETAILS_MODES:
            erreurs.append(prefixe + f"details_mode invalide : {details_mode!r}.")

        ressources = item.get('ressources')
        if ressources is not None and not isinstance(ressources, list):
            erreurs.append(prefixe + "'ressources' doit être une liste.")

    return erreurs


# ============================================================
# BASE HTTP
# ============================================================
class FournisseurHTTPAbstrait(FournisseurIAAbstrait):
    """Base des fournisseurs IA HTTP (Mistral, Gemini, OpenRouter)."""

    nom = 'http'
    nom_variable_cle = ''
    nom_variable_modele = ''
    modele_par_defaut = ''
    url_api = ''

    def __init__(self, api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: float = 30.0,
                 transport=None):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        # ``transport`` permet d'injecter un httpx.MockTransport en test.
        self._transport = transport

    # ---- configuration ----
    @property
    def modele(self) -> str:
        return (
            self._model
            or os.environ.get(self.nom_variable_modele)
            or self.modele_par_defaut
        )

    @property
    def cle_api_disponible(self) -> bool:
        """Indique si une clé est présente, sans jamais la révéler."""
        cle = self._api_key
        if cle is None:
            cle = os.environ.get(self.nom_variable_cle)
        return bool(str(cle or '').strip())

    def _obtenir_cle_api(self) -> str:
        cle = self._api_key
        if cle is None:
            cle = os.environ.get(self.nom_variable_cle)
        if not str(cle or '').strip():
            raise ConfigurationManquante(self.nom_variable_cle)
        return str(cle)

    # ---- orchestration ----
    def proposer_modifications(self, demande: str, contexte: Dict):
        cle = self._obtenir_cle_api()
        modele = self.modele
        systeme = PROMPT_SYSTEME
        utilisateur = construire_message_utilisateur(demande, contexte)
        requete = self._construire_requete(cle, modele, systeme, utilisateur)
        reponse = self._poster_json(
            requete['url'], requete['headers'], requete['payload']
        )
        texte = self._extraire_texte(reponse)
        return parser_reponse_ia(texte)

    def _poster_json(self, url: str, headers: Dict, payload: Dict) -> httpx.Response:
        try:
            with httpx.Client(timeout=self._timeout,
                              transport=self._transport) as client:
                reponse = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise ErreurHTTPFournisseur('TIMEOUT', 'délai dépassé')
        except httpx.HTTPError as erreur:
            raise ErreurHTTPFournisseur(
                'RESEAU', type(erreur).__name__
            )
        if reponse.status_code >= 400:
            raise ErreurHTTPFournisseur(
                reponse.status_code,
                reponse.reason_phrase or 'requête refusée',
            )
        return reponse

    # ---- à implémenter par les fournisseurs ----
    def _construire_requete(self, cle: str, modele: str, systeme: str,
                            utilisateur: str) -> Dict:
        raise NotImplementedError

    def _extraire_texte(self, reponse: httpx.Response) -> str:
        raise NotImplementedError

    # ---- utilitaire commun de décodage ----
    @staticmethod
    def _json_reponse(reponse: httpx.Response) -> Dict:
        try:
            donnees = reponse.json()
        except Exception:
            raise ReponseInvalide("Réponse fournisseur illisible (JSON attendu).")
        if not isinstance(donnees, dict):
            raise ReponseInvalide("Réponse fournisseur invalide (objet attendu).")
        return donnees


class FournisseurOpenAICompatible(FournisseurHTTPAbstrait):
    """Base des API compatibles OpenAI (Mistral, OpenRouter)."""

    def _construire_requete(self, cle: str, modele: str, systeme: str,
                            utilisateur: str) -> Dict:
        return {
            'url': self.url_api,
            'headers': {
                'Authorization': f'Bearer {cle}',
                'Content-Type': 'application/json',
            },
            'payload': {
                'model': modele,
                'messages': [
                    {'role': 'system', 'content': systeme},
                    {'role': 'user', 'content': utilisateur},
                ],
                'temperature': 0,
                'response_format': {'type': 'json_object'},
            },
        }

    def _extraire_texte(self, reponse: httpx.Response) -> str:
        donnees = self._json_reponse(reponse)
        choix = donnees.get('choices')
        if not isinstance(choix, list) or not choix:
            raise ReponseInvalide("Réponse fournisseur sans résultat exploitable.")
        message = choix[0].get('message') if isinstance(choix[0], dict) else None
        contenu = message.get('content') if isinstance(message, dict) else None
        if not isinstance(contenu, str) or not contenu.strip():
            raise ReponseInvalide("Réponse fournisseur vide.")
        return contenu
