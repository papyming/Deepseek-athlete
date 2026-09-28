# ============================================================
# FICHIER: src/planificateur/contrat_modifications.py
# RÔLE: Contrat STRUCTURÉ et déterministe d'une demande de
#       modification du CSV.
#
#       Ce contrat est le point d'échange avec un futur agent IA :
#       l'IA produit une (liste de) modification(s) sous cette forme,
#       Python se charge de la recherche, de l'application, du respect
#       des règles et de la validation.
#
#       AUCUNE connexion IA, AUCUN calcul de plan ici.
# ============================================================

from typing import Dict, List, Optional

# ---- ACTIONS SUPPORTÉES ----
ACTION_AJOUTER = 'AJOUTER'
ACTION_DEPLACER = 'DEPLACER'
ACTION_REMPLACER = 'REMPLACER'
ACTION_SUPPRIMER = 'SUPPRIMER'
ACTION_MODIFIER_DUREE = 'MODIFIER_DUREE'
ACTION_MODIFIER_DETAILS = 'MODIFIER_DETAILS'
ACTION_MODIFIER_FREQUENCE = 'MODIFIER_FREQUENCE'
ACTION_AJOUTER_RESSOURCE = 'AJOUTER_RESSOURCE'
ACTION_INCOMPRIS = 'INCOMPRIS'

ACTIONS = {
    ACTION_AJOUTER, ACTION_DEPLACER, ACTION_REMPLACER, ACTION_SUPPRIMER,
    ACTION_MODIFIER_DUREE, ACTION_MODIFIER_DETAILS, ACTION_MODIFIER_FREQUENCE,
    ACTION_AJOUTER_RESSOURCE, ACTION_INCOMPRIS,
}

# Actions qui créent des séances (période par défaut = fin du plan si récurrence).
ACTIONS_CREATION = {ACTION_AJOUTER, ACTION_AJOUTER_RESSOURCE}

# ---- PÉRIODES ----
PERIODE_SEMAINE_COURANTE = 'SEMAINE_COURANTE'
PERIODE_SEMAINE_PROCHAINE = 'SEMAINE_PROCHAINE'
PERIODE_SEMAINES = 'SEMAINES'
PERIODE_DATES = 'DATES'
PERIODE_DATE_FIN = 'DATE_DE_FIN'
PERIODE_JUSQU_OBJECTIF = 'JUSQU_OBJECTIF'
PERIODE_FIN_DU_PLAN = 'FIN_DU_PLAN'
PERIODE_TOUT = 'TOUT'

PERIODES = {
    PERIODE_SEMAINE_COURANTE, PERIODE_SEMAINE_PROCHAINE, PERIODE_SEMAINES,
    PERIODE_DATES, PERIODE_DATE_FIN, PERIODE_JUSQU_OBJECTIF,
    PERIODE_FIN_DU_PLAN, PERIODE_TOUT,
}

# Période appliquée quand le coach ne précise ni durée ni période.
PERIODE_PAR_DEFAUT = PERIODE_FIN_DU_PLAN
# Période appliquée par défaut aux opérations ponctuelles sur séances existantes.
PERIODE_PAR_DEFAUT_PONCTUELLE = PERIODE_SEMAINE_COURANTE

# ---- FRÉQUENCES ----
FREQUENCE_HEBDOMADAIRE = 'HEBDOMADAIRE'
FREQUENCE_UNE_SEMAINE_SUR_DEUX = 'UNE_SEMAINE_SUR_DEUX'
FREQUENCE_UNE_SEMAINE_SUR_TROIS = 'UNE_SEMAINE_SUR_TROIS'

FREQUENCES = {
    FREQUENCE_HEBDOMADAIRE, FREQUENCE_UNE_SEMAINE_SUR_DEUX,
    FREQUENCE_UNE_SEMAINE_SUR_TROIS,
}

# ---- MODES DE DÉTAILS ----
DETAILS_REMPLACER = 'REMPLACER'
DETAILS_AJOUTER = 'AJOUTER'
DETAILS_MODES = {DETAILS_REMPLACER, DETAILS_AJOUTER}

# ---- TYPES DE SÉANCE (canoniques) ----
TYPE_ENDURANCE = 'ENDURANCE'
TYPE_INTENSITE = 'INTENSITE'
TYPE_SEUIL = 'SEUIL'
TYPE_FARTLEK = 'FARTLEK'
TYPE_SORTIE_LONGUE = 'SORTIE_LONGUE'
TYPE_RECUPERATION = 'RECUPERATION'
TYPE_RENFORCEMENT = 'RENFORCEMENT'
TYPE_COMPETITION = 'COMPETITION'

TYPES_SEANCE = {
    TYPE_ENDURANCE, TYPE_INTENSITE, TYPE_SEUIL, TYPE_FARTLEK,
    TYPE_SORTIE_LONGUE, TYPE_RECUPERATION, TYPE_RENFORCEMENT, TYPE_COMPETITION,
}

_ALIAS_DISCIPLINES = {
    'cap': 'CAP', 'course': 'CAP', 'course_a_pied': 'CAP', 'course à pied': 'CAP',
    'running': 'CAP', 'run': 'CAP',
    'velo': 'Vélo', 'vélo': 'Vélo', 'bike': 'Vélo', 'cyclisme': 'Vélo',
    'natation': 'Natation', 'nat': 'Natation', 'swim': 'Natation',
    'renforcement': 'Renforcement', 'renfo': 'Renforcement',
    'musculation': 'Renforcement', 'ppg': 'Renforcement',
    'competition': 'Course', 'compétition': 'Course', 'course_competition': 'Course',
}

_ALIAS_TYPES = {
    'endurance': TYPE_ENDURANCE, 'endurance_fondamentale': TYPE_ENDURANCE,
    'intensite': TYPE_INTENSITE, 'intensité': TYPE_INTENSITE, 'vma': TYPE_INTENSITE,
    'seuil': TYPE_SEUIL, 'vc': TYPE_SEUIL,
    'fartlek': TYPE_FARTLEK,
    'sortie_longue': TYPE_SORTIE_LONGUE, 'sortie longue': TYPE_SORTIE_LONGUE,
    'recuperation': TYPE_RECUPERATION, 'récupération': TYPE_RECUPERATION,
    'recup': TYPE_RECUPERATION,
    'renforcement': TYPE_RENFORCEMENT, 'renfo': TYPE_RENFORCEMENT,
    'competition': TYPE_COMPETITION, 'compétition': TYPE_COMPETITION,
}

JOURS_SEMAINE = [
    'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche',
]
_ALIAS_JOURS = {jour.lower(): jour for jour in JOURS_SEMAINE}


def normaliser_action(valeur) -> str:
    if valeur is None:
        return ''
    return str(valeur).strip().upper()


def normaliser_discipline(valeur) -> Optional[str]:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    if not texte:
        return None
    if texte in ('CAP', 'Vélo', 'Velo', 'Natation', 'Renforcement', 'Course'):
        return 'Vélo' if texte == 'Velo' else texte
    return _ALIAS_DISCIPLINES.get(texte.lower(), texte)


def normaliser_type_seance(valeur) -> Optional[str]:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    if not texte:
        return None
    if texte in TYPES_SEANCE:
        return texte
    return _ALIAS_TYPES.get(texte.lower(), texte.upper())


def normaliser_jour(valeur) -> Optional[str]:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    if not texte:
        return None
    return _ALIAS_JOURS.get(texte.lower(), texte.capitalize())


def normaliser_periode(periode) -> Optional[Dict]:
    if periode is None:
        return None
    if isinstance(periode, str):
        texte = periode.strip().upper()
        if texte in PERIODES:
            return {'type': texte}
        # "2026-08-01" -> DATE_DE_FIN
        return {'type': PERIODE_DATE_FIN, 'fin': periode}
    return dict(periode)


def normaliser_frequence(frequence):
    if frequence is None:
        return None
    if isinstance(frequence, int):
        return {'intervalle': frequence}
    if isinstance(frequence, dict):
        return dict(frequence)
    texte = str(frequence).strip().upper()
    if texte in FREQUENCES:
        return {'type': texte}
    if texte.startswith('TOUS_LES_'):
        return {'type': FREQUENCE_HEBDOMADAIRE, 'jour': texte.replace('TOUS_LES_', '')}
    return {'type': texte}


def normaliser_modification(modification: Dict) -> Dict:
    """Normalise une modification (sans la valider)."""
    modification = dict(modification or {})
    periode = normaliser_periode(modification.get('periode'))
    action = normaliser_action(modification.get('action'))
    frequence = normaliser_frequence(modification.get('frequence'))
    compris = modification.get('compris', True)
    if action == ACTION_INCOMPRIS:
        compris = False

    # Période effective : explicite, sinon par défaut (fin du plan pour une
    # création récurrente, semaine courante pour une opération ponctuelle).
    periode_explicite = periode is not None
    if periode_explicite:
        periode_par_defaut = None
    elif action in ACTIONS_CREATION and frequence:
        periode_par_defaut = PERIODE_PAR_DEFAUT
    else:
        periode_par_defaut = PERIODE_PAR_DEFAUT_PONCTUELLE

    normalisee = {
        'action': action,
        'discipline': normaliser_discipline(modification.get('discipline')),
        'type_seance': normaliser_type_seance(modification.get('type_seance')),
        'cible': dict(modification.get('cible') or {}),
        'date_cible': modification.get('date_cible'),
        'jour_cible': normaliser_jour(modification.get('jour_cible') or modification.get('jour')),
        'periode': periode,
        'periode_explicite': periode_explicite,
        'periode_par_defaut': periode_par_defaut,
        'periode_ambigue': bool(
            modification.get('periode_ambigue') or modification.get('ambigu_periode')
        ),
        'ambigu': bool(modification.get('ambigu')),
        'compris': bool(compris),
        'question': modification.get('question'),
        'duree': modification.get('duree'),
        'duree_delta': modification.get('duree_delta'),
        'frequence': frequence,
        'details': modification.get('details'),
        'details_mode': normaliser_action(
            modification.get('details_mode') or DETAILS_REMPLACER
        ),
        'ressources': list(modification.get('ressources') or []),
        'raison': modification.get('raison') or modification.get('commentaire'),
        'contraintes': dict(modification.get('contraintes') or {}),
    }
    cible = normalisee['cible']
    if cible:
        if 'discipline' in cible:
            cible['discipline'] = normaliser_discipline(cible['discipline'])
        if 'type_seance' in cible:
            cible['type_seance'] = normaliser_type_seance(cible['type_seance'])
        if 'jour' in cible:
            cible['jour'] = normaliser_jour(cible['jour'])
    return normalisee


def valider_contrat(modification: Dict) -> List[str]:
    """Vérifie la STRUCTURE d'une modification normalisée (pas les manques)."""
    erreurs = []
    action = modification.get('action')
    if action not in ACTIONS:
        erreurs.append(
            f"Action inconnue : {action!r} (attendu parmi {sorted(ACTIONS)})."
        )
        return erreurs

    if modification.get('duree') is not None:
        try:
            int(modification['duree'])
        except (TypeError, ValueError):
            erreurs.append(f"Durée invalide : {modification['duree']!r}.")
    if modification.get('duree_delta') is not None:
        try:
            int(modification['duree_delta'])
        except (TypeError, ValueError):
            erreurs.append(f"Delta de durée invalide : {modification['duree_delta']!r}.")
    return erreurs


def questions_manquantes(modification: Dict) -> List[str]:
    """Retourne les questions ciblées pour une information indispensable absente.

    Aucune valeur n'est inventée : on demande uniquement l'élément manquant.
    """
    questions = []
    action = modification.get('action')
    cible = modification.get('cible') or {}
    a_discipline = bool(modification.get('discipline') or cible.get('discipline'))
    a_cible = bool(cible or modification.get('discipline'))
    a_jour = bool(modification.get('jour_cible'))
    a_date = bool(modification.get('date_cible'))

    if action == ACTION_AJOUTER:
        if not modification.get('discipline'):
            questions.append('Quelle discipline souhaitez-vous ajouter ?')
        if not a_jour and not a_date:
            questions.append('Quel jour souhaitez-vous ajouter cette séance ?')
    elif action == ACTION_DEPLACER:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous déplacer ?')
        if not a_jour and not a_date:
            questions.append('Vers quel jour souhaitez-vous déplacer cette séance ?')
    elif action == ACTION_REMPLACER:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous remplacer ?')
    elif action == ACTION_SUPPRIMER:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous supprimer ?')
    elif action == ACTION_MODIFIER_DUREE:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous modifier ?')
        if modification.get('duree') is None and modification.get('duree_delta') is None:
            questions.append('Quelle durée souhaitez-vous appliquer ?')
    elif action == ACTION_MODIFIER_DETAILS:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous modifier ?')
        if not modification.get('details'):
            questions.append('Quel contenu souhaitez-vous appliquer ?')
    elif action == ACTION_MODIFIER_FREQUENCE:
        if not a_cible:
            questions.append('Quelle séance souhaitez-vous modifier ?')
    elif action == ACTION_AJOUTER_RESSOURCE:
        if not modification.get('ressources'):
            questions.append('Quelles ressources souhaitez-vous ajouter ?')
        if not a_jour and not a_cible:
            questions.append('À quel jour souhaitez-vous associer ces ressources ?')
    return questions


def normaliser_demande(demande) -> Dict:
    """Normalise une demande : dict unique, liste, ou {'modifications': [...]}.

    Retourne {'modifications': [...], 'erreurs': [...], 'questions': [...]}.
    - 'erreurs' : problème de structure (INVALIDE).
    - 'questions' : information indispensable manquante (CLARIFICATION).
    """
    if demande is None:
        return {'modifications': [], 'erreurs': ['Demande vide.'], 'questions': []}
    if isinstance(demande, dict) and 'modifications' in demande:
        brut = demande.get('modifications') or []
    elif isinstance(demande, dict):
        brut = [demande]
    elif isinstance(demande, (list, tuple)):
        brut = list(demande)
    else:
        return {'modifications': [], 'erreurs': ['Format de demande non supporté.'],
                'questions': []}

    modifications = []
    erreurs = []
    questions = []
    for index, item in enumerate(brut):
        normalisee = normaliser_modification(item)
        erreurs_item = valider_contrat(normalisee)
        if erreurs_item:
            erreurs.extend(f"Modification {index}: {e}" for e in erreurs_item)
            continue
        modifications.append(normalisee)
        for question in questions_manquantes(normalisee):
            questions.append({'modification': index, 'question': question})
    return {'modifications': modifications, 'erreurs': erreurs, 'questions': questions}
