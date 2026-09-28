# ============================================================
# FICHIER: src/planificateur/fournisseurs/openrouter.py
# RÔLE: Adaptateur OpenRouter (API HTTP JSON OpenAI-compatible).
#
#       - clé : variable d'environnement OPENROUTER_API_KEY ;
#       - modèle : OPENROUTER_MODEL (défaut configurable, y compris
#         le routeur gratuit « openrouter/free »).
#
#       Spécificités OpenRouter (et uniquement elles) :
#       - prompt système renforcé (sortie JSON stricte, contrat) ;
#       - préparation de sortie robuste : vérifie la FORME avant de
#         laisser le contrat valider, puis reprise automatique si le
#         modèle renvoie un JSON invalide, vide ou mal formé.
#
#       Aucun appel réseau à l'import. Aucun accès disque.
#       Ne modifie jamais le contrat ni le moteur : il ne produit que
#       des données structurées.
# ============================================================

import json

from ..contrat_modifications import (
    ACTIONS,
    DETAILS_MODES,
    FREQUENCES,
    PERIODES,
    TYPES_SEANCE,
)
from .base_http import (
    FournisseurOpenAICompatible,
    ReponseInvalide,
    construire_message_utilisateur,
    parser_reponse_ia,
)

__all__ = ['OpenRouterFournisseurIA', 'PROMPT_SYSTEME_OPENROUTER']


# Prompt système renforcé : sortie strictement JSON et règles métier
# explicites pour ne pas transformer une demande claire en clarification.
PROMPT_SYSTEME_OPENROUTER = (
    "Tu es un interpréteur de demandes d'entraînement pour un coach.\n"
    "Tu ne calcules rien et tu ne modifies aucun fichier : tu produis "
    "UNIQUEMENT une structure JSON conforme au contrat de modifications.\n\n"
    "RÈGLES DE SORTIE (ABSOLUES) :\n"
    "- Réponds EXCLUSIVEMENT par UN SEUL objet JSON valide.\n"
    "- Jamais de texte avant, jamais de texte après.\n"
    "- Jamais de Markdown, jamais de commentaire, jamais de prose.\n"
    "- Jamais de réponse vide ni de tableau vide.\n"
    "- N'invente aucun champ et aucune valeur : respecte strictement le contrat.\n"
    "- N'utilise ni chemin de fichier, ni CSV, ni code.\n\n"
    "ACTIONS POSSIBLES : " + ', '.join(sorted(ACTIONS)) + "\n"
    "DISCIPLINES : CAP, Vélo, Natation, Renforcement, Course\n"
    "TYPES DE SÉANCE : " + ', '.join(sorted(TYPES_SEANCE)) + "\n"
    "PÉRIODES : " + ', '.join(sorted(PERIODES)) + "\n"
    "FRÉQUENCES : " + ', '.join(sorted(FREQUENCES)) + "\n"
    "MODES DE DÉTAILS : " + ', '.join(sorted(DETAILS_MODES)) + "\n\n"
    "CHAMPS D'UNE MODIFICATION : action, discipline, type_seance, "
    "cible (objet avec discipline, type_seance, jour, date, difficulte), "
    "date_cible, jour_cible, periode, frequence, duree, duree_delta, "
    "details, details_mode, ressources, raison, question.\n\n"
    "TYPES DE CHAMPS :\n"
    "- cible, periode et contraintes sont des OBJETS JSON {}, jamais des "
    "tableaux.\n"
    "- ressources est une LISTE de chaînes.\n"
    "- DURÉES : un ENTIER en MINUTES, jamais une chaîne. 3h = 180, "
    "1h30 = 90, 45 min = 45. Exemple : \"duree\": 180.\n"
    "- RESSOURCES / URL : chaîne brute (ex. \"https://exemple\"), jamais de "
    "lien Markdown de type [texte](url), jamais de balises.\n\n"
    "TYPES DE SÉANCE (STRICT) :\n"
    "- type_seance doit être EXACTEMENT l'une de ces valeurs : "
    + ', '.join(sorted(TYPES_SEANCE)) + ".\n"
    "- N'ajoute JAMAIS de zone ni d'intensité au type_seance : jamais "
    "\"SORTIE LONGUE Z2\", \"SEUIL Z4\", \"ENDURANCE Z2\", etc. Écris "
    "\"SORTIE_LONGUE\", \"SEUIL\", \"ENDURANCE\".\n"
    "- La zone / l'intensité (Z1, Z2, Z3, Z4, Z5, allure, %FC…) ne va JAMAIS "
    "dans type_seance ; si elle est explicitement demandée, elle va dans "
    "details.\n"
    "- Ne crée jamais un nouveau type_seance.\n\n"
    "RÈGLES MÉTIER :\n"
    "- AJOUT explicite (« Rajoute… », « Ajoute… », « Mets… », "
    "« Intensité natation le jeudi. ») : action AJOUTER. "
    "Ne demande PAS de confirmation ni si l'on veut ajouter ou modifier.\n"
    "- AJOUTER doit être EXPLOITABLE : au minimum discipline ET type_seance, "
    "plus tous les éléments explicitement fournis (jour_cible/date_cible, "
    "duree, details, frequence, periode). Si ces informations minimales ne "
    "sont pas déterminables, renvoie une clarification INCOMPRIS, jamais un "
    "AJOUT vide.\n"
    "- Création récurrente (frequence) sans période explicite : "
    "periode {\"type\": \"FIN_DU_PLAN\"}. N'invente jamais de durée "
    "(pas de 4 semaines ni d'autre durée arbitraire).\n"
    "- ANNÉE : ne l'invente JAMAIS. Utilise l'année si elle est donnée, ou "
    "si elle est déterminable sans ambiguïté à partir du contexte du plan "
    "(periode.debut / periode.fin). Sinon, action INCOMPRIS avec une "
    "question. N'utilise jamais l'année courante par défaut.\n"
    "- Indisponibilité sur une plage de dates (« impossible du 1er au 10 "
    "août ») : action SUPPRIMER, discipline concernée, periode "
    "{\"type\": \"DATES\", \"debut\": \"...\", \"fin\": \"...\"}. "
    "Ne pose AUCUNE question sur les séances concernées.\n"
    "- Renforcement musculaire : type_seance RENFORCEMENT. Une ressource "
    "(URL) : action AJOUTER_RESSOURCE avec ressources: [\"URL brute\"]. "
    "Ne demande JAMAIS de discipline CAP/Vélo/Natation pour un renforcement.\n"
    "- Modification de durée (« réduire … de 20 minutes ») : action "
    "MODIFIER_DUREE avec duree_delta = -20 et la cible "
    "(discipline, type_seance, jour). Ne demande pas de clarification inutile.\n"
    "- Contrainte de planification : ne tente JAMAIS de la résoudre. "
    "Propose l'AJOUT correspondant, le moteur Python détectera la contrainte.\n"
    "- Période fournie explicitement par le coach : la CONSERVER telle quelle.\n"
    "- Ne demande jamais une information non nécessaire à l'action demandée.\n\n"
    "CLARIFICATION (uniquement si une information indispensable manque) :\n"
    "- « Déplace la séance. » (aucune cible, aucune destination) : "
    "{\"action\": \"INCOMPRIS\", \"question\": \"...\"}.\n"
    "- « Fais quelque chose de plus dur mercredi. » (nature et cible "
    "indéterminées) : {\"action\": \"INCOMPRIS\", \"question\": \"...\"}.\n"
    "- Retourne toujours cet objet JSON de clarification, jamais de texte libre.\n"
)

# Message de reprise injecté avant la demande lors d'un second essai.
_RAPPEL_SORTIE = (
    "RAPPEL : ta réponse précédente n'était pas un objet JSON valide. "
    "Réponds MAINTENANT, sans aucune autre phrase, par UN SEUL objet JSON "
    "conforme au contrat, sans Markdown et sans commentaire."
)

# Champs qui doivent être des objets JSON dans le contrat existant.
_CHAMPS_OBJET = ('cible', 'periode', 'contraintes')


def _verifier_forme_sortie(structure):
    """Contrôle la FORME avant le contrat (évite un ValueError local).

    Le contrat appelle ``dict()`` sur ``cible``/``periode``/``contraintes`` :
    un tableau JSON à cet endroit provoque un ``ValueError`` qui ne doit PAS
    remonter comme erreur de programmation. On le classe proprement en
    ``ReponseInvalide`` (sortie IA non conforme).
    """
    erreurs = []
    if isinstance(structure, dict) and 'modifications' in structure:
        liste = structure.get('modifications')
        if not isinstance(liste, list):
            return ["Le champ 'modifications' doit être une liste."]
    elif isinstance(structure, dict):
        liste = [structure]
    elif isinstance(structure, list):
        liste = structure
    else:
        return ["Structure IA non supportée (objet ou liste JSON attendu)."]

    for index, item in enumerate(liste):
        if not isinstance(item, dict):
            continue  # signalé par le contrat, jamais de dict() dessus.
        for champ in _CHAMPS_OBJET:
            valeur = item.get(champ)
            if valeur is not None and not isinstance(valeur, dict):
                erreurs.append(
                    f"Modification {index} : le champ '{champ}' doit être un "
                    "objet JSON, pas un tableau."
                )
    return erreurs


def _parser_sortie_openrouter(texte):
    """Parse strict + contrôle de forme, puis validation du contrat."""
    if isinstance(texte, str) and texte.strip():
        try:
            structure = json.loads(texte.strip())
        except json.JSONDecodeError:
            structure = None
        if structure is not None:
            erreurs_forme = _verifier_forme_sortie(structure)
            if erreurs_forme:
                raise ReponseInvalide(' ; '.join(erreurs_forme))
    return parser_reponse_ia(texte)


class OpenRouterFournisseurIA(FournisseurOpenAICompatible):
    """Fournisseur IA OpenRouter (sortie structurée garantie par reprise)."""

    nom = 'openrouter'
    nom_variable_cle = 'OPENROUTER_API_KEY'
    nom_variable_modele = 'OPENROUTER_MODEL'
    # Modèle gratuit par défaut, surchargeable via OPENROUTER_MODEL
    # (aucun modèle n'est figé dans le code).
    modele_par_defaut = 'openrouter/free'
    url_api = 'https://openrouter.ai/api/v1/chat/completions'
    # Prompt renforcé propre à OpenRouter.
    prompt_systeme = PROMPT_SYSTEME_OPENROUTER
    # 1 essai + 1 reprise si la sortie n'est pas un JSON conforme.
    tentatives_max = 2

    def proposer_modifications(self, demande: str, contexte):
        """Interroge OpenRouter et ne retourne qu'une structure conforme.

        En cas de réponse vide, entourée de texte, mal formée ou non
        conforme au contrat, la demande est reformulée (max
        ``tentatives_max``). Les erreurs HTTP/réseau ne sont PAS rejouées,
        et aucune erreur de forme ne remonte comme exception Python.
        """
        cle = self._obtenir_cle_api()
        modele = self.modele
        derniere_erreur = None

        for tentative in range(1, self.tentatives_max + 1):
            utilisateur = construire_message_utilisateur(demande, contexte)
            if tentative > 1:
                utilisateur = _RAPPEL_SORTIE + '\n\n' + utilisateur
            requete = self._construire_requete(
                cle, modele, self.prompt_systeme, utilisateur
            )
            reponse = self._poster_json(
                requete['url'], requete['headers'], requete['payload']
            )
            try:
                texte = self._extraire_texte(reponse)
                return _parser_sortie_openrouter(texte)
            except ReponseInvalide as erreur:
                derniere_erreur = erreur

        raise derniere_erreur
