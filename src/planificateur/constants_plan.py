# ============================================================
# FICHIER: src/planificateur/constants_plan.py
# RÔLE: Définit les constantes utilisées dans la planification
#       (émojis, types de séances, difficultés, volumes max)
# ============================================================

# ============================================================
# JOURS DE LA SEMAINE
# ============================================================

JOURS_SEMAINE = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

# ============================================================
# ÉMOJIS
# ============================================================

EMOJI_JOURNEE = {
    'endurance': '🟩',
    'seuil': '🟨',
    'intense': '🟥',
    'recuperation': '🟦',
    'course': '⭐',
    'repos': '⬜',
    'technique': '🟩',
    'renforcement': '🏋️'
}

EMOJI_SEMAINE = {
    'recuperation': '⚪',
    'affutage': '🔵',
    'normale': '🟢',
    'chargee': '🟡',
    'dure': '🔴',
    'exceptionnelle': '🟤'
}

# ============================================================
# TYPES DE SÉANCES CAP (complets)
# ============================================================

TYPES_SEANCES_CAP = {
    'endurance_fondamentale': 'Endurance fondamentale Z2',
    'endurance_recuperative': 'Footing de récupération Z1',
    'sortie_longue': 'Sortie longue Z2',
    'vma': 'VMA Z5',
    'vc': 'VC Z4',
    'seuil': 'Seuil Z3',
    'fartlek': 'Fartlek',
    'recup': 'Récupération active',
    'test_3_6_12': 'Test VC 3\'/6\'/12\''
}

# ============================================================
# TYPES DE SÉANCES VÉLO (complets)
# ============================================================

TYPES_SEANCES_VELO = {
    'endurance': 'Endurance Z2',
    'seuil': 'Seuil Z4',
    'ftp_travail': 'Travail FTP Z3/Z4',
    'sortie_longue': 'Sortie longue Z2',
    'recup': 'Récupération active'
}

# ============================================================
# TYPES DE SÉANCES NATATION (complets)
# ============================================================

TYPES_SEANCES_NATATION = {
    'technique': 'Technique',
    'endurance': 'Endurance Z2',
    'seuil': 'Seuil Z4',
    'sprint': 'Sprint Z5',
    'recup': 'Récupération active'
}

# ============================================================
# TYPES DE RENFORCEMENT
# ============================================================

TYPES_RENFORCEMENT = [
    'Renforcement général',
    'Renforcement spécifique',
    'Pliométrie',
    'Gainage',
    'Renforcement excentrique'
]

# ============================================================
# DIFFICULTÉS
# ============================================================

DIFFICULTE = {
    'endurance_fondamentale': 'endurance',
    'endurance_recuperative': 'recuperation',
    'sortie_longue': 'endurance',
    'vma': 'intense',
    'vc': 'seuil',
    'seuil': 'seuil',
    'fartlek': 'intense',
    'recup': 'recuperation',
    'technique': 'endurance',
    'sprint': 'intense',
    'ftp_travail': 'seuil',
    'endurance': 'endurance',
    'test_3_6_12': 'intense',
    'renforcement_general': 'endurance',
    'renforcement_specifique': 'endurance',
    'pliometrie': 'intense',
    'gainage': 'endurance',
    'renforcement_excentrique': 'endurance'
}

# ============================================================
# VOLUME MAXIMAL PAR SÉANCE
# ============================================================

VOLUME_MAX_PAR_SEANCE = {
    'CAP': 120,      # 2h max par séance
    'Velo': 180,     # borne des seances de qualite uniquement
    'Natation': 90   # 1h30 max par séance
}

# Bornes metier des seances Velo :
# - une seance velo n'est jamais < 80 min ;
# - il n'existe AUCUN plafond metier a 180 min : une sortie longue peut
#   depasser 180 min (210, 240, 270, 300 min ou davantage) selon le budget
#   hebdomadaire et la periode. La constante ci-dessous n'est qu'une borne
#   TECHNIQUE de securite (duree maximale absolue), pas un plafond metier.
VELO_DUREE_MIN = 80
VELO_DUREE_MAX_TECHNIQUE = 480  # 8 h : borne technique, PAS un plafond metier

# Cible de base (duree visee) de la seance longue Velo selon l'objectif.
# C'est un objectif prefere, jamais un plafond : si le budget hebdomadaire le
# permet, la sortie longue peut le depasser.
VELO_DUREE_LONGUE_CIBLE_IRONMAN = 180   # longue distance / Ironman
VELO_DUREE_LONGUE_CIBLE_VOLUME = 150    # triathlon / cyclisme a volume important
VELO_DUREE_LONGUE_CIBLE_DEFAUT = 90     # sinon

# ============================================================
# ÉQUIVALENCE DE TEMPS D'ENTRAÎNEMENT (unités par heure)
# 1 h CAP = 1 h Natation = 2 h Vélo = 1 unité
# ============================================================

UNITE_DUREE_PAR_HEURE = {
    'CAP': 1.0,
    'Natation': 1.0,
    'Velo': 0.5
}

# ============================================================
# MATRICE SPORT PRINCIPAL -> PRIORITÉ DISCIPLINES + PONDÉRATION
# ============================================================

DEFAULT_SPORT_PRINCIPAL = 'Triathlon'

SPORT_PRINCIPAL_MATRIX = {
    'Triathlon': {
        'disciplines_priorite': ['CAP', 'Velo', 'Natation'],
        'priority': {'CAP': 1, 'Velo': 1, 'Natation': 1},
        'ponderation': {'CAP': 1.0, 'Velo': 1.0, 'Natation': 1.0}
    },
    'Course à pied': {
        'disciplines_priorite': ['CAP', 'Velo', 'Natation'],
        'priority': {'CAP': 3, 'Velo': 2, 'Natation': 1},
        'ponderation': {'CAP': 1.3, 'Velo': 0.5, 'Natation': 0.5}
    },
    'Cyclisme': {
        'disciplines_priorite': ['Velo', 'CAP', 'Natation'],
        'priority': {'Velo': 3, 'CAP': 2, 'Natation': 1},
        'ponderation': {'CAP': 0.5, 'Velo': 1.3, 'Natation': 0.5}
    },
    'Natation': {
        'disciplines_priorite': ['Natation', 'CAP', 'Velo'],
        'priority': {'Natation': 3, 'CAP': 2, 'Velo': 1},
        'ponderation': {'CAP': 0.5, 'Velo': 0.5, 'Natation': 1.3}
    },
    'Swimrun': {
        'disciplines_priorite': ['CAP', 'Natation', 'Velo'],
        'priority': {'CAP': 3, 'Natation': 3, 'Velo': 1},
        'ponderation': {'CAP': 1.1, 'Velo': 0.0, 'Natation': 1.1}
    },
    'Aquathlon': {
        'disciplines_priorite': ['CAP', 'Natation', 'Velo'],
        'priority': {'CAP': 3, 'Natation': 3, 'Velo': 1},
        'ponderation': {'CAP': 1.1, 'Velo': 0.0, 'Natation': 1.1}
    },
    'Raid aventure / multisport': {
        'disciplines_priorite': ['CAP', 'Velo', 'Natation'],
        'priority': {'CAP': 3, 'Velo': 2, 'Natation': 1},
        'ponderation': {'CAP': 1.0, 'Velo': 0.8, 'Natation': 0.8}
    }
}


def get_sport_discipline_priority_order(sport_principal: str = '') -> list:
    """Retourne l’ordre de priorité des disciplines pour un sport principal donné.

    Aucune correction silencieuse vers Triathlon n’est appliquée : les règles
    métier ne déduisent pas un sport principal absent depuis le profil.
    """
    sport_principal = str(sport_principal or '').strip()
    sport_rules = SPORT_PRINCIPAL_MATRIX.get(sport_principal)
    if sport_rules is None:
        return ['CAP', 'Velo', 'Natation']
    priority = sport_rules.get('priority', {'CAP': 1, 'Velo': 1, 'Natation': 1})
    return sorted(['CAP', 'Velo', 'Natation'], key=lambda d: (-priority.get(d, 1), d))


def get_sport_ponderation(sport_principal: str = '') -> dict:
    """Retourne la pondération de volume par discipline pour un sport principal donné."""
    sport_principal = str(sport_principal or '').strip()
    sport_rules = SPORT_PRINCIPAL_MATRIX.get(sport_principal)
    if sport_rules is None:
        return {'CAP': 1.0, 'Velo': 1.0, 'Natation': 1.0}
    return dict(sport_rules.get('ponderation', {'CAP': 1.0, 'Velo': 1.0, 'Natation': 1.0}))


def get_sport_priority_map(sport_principal: str = '') -> dict:
    """Retourne la carte de priorité numérique par discipline pour le sport demandé."""
    sport_principal = str(sport_principal or '').strip()
    sport_rules = SPORT_PRINCIPAL_MATRIX.get(sport_principal)
    if sport_rules is None:
        return {'CAP': 1, 'Velo': 1, 'Natation': 1}
    return dict(sport_rules.get('priority', {'CAP': 1, 'Velo': 1, 'Natation': 1}))

# ============================================================
# NORMALISATION DES DISCIPLINES
# ============================================================

def normalize_discipline_name(discipline: str) -> str:
    """Normalise les libellés métier des disciplines sur le libellé canonique.
    Conserve CAP et Natation, normalise Velo -> Vélo.
    """
    if discipline is None:
        return discipline
    key = str(discipline).strip()
    if key == 'Velo':
        return 'Vélo'
    return key

# ============================================================
# FONCTIONS D'ACCÈS AUX CONSTANTES
# ============================================================

def get_emoji_semaine(type_semaine: str) -> str:
    """Retourne l'émoji correspondant au type de semaine."""
    return EMOJI_SEMAINE.get(type_semaine, '🟢')


def get_emoji_journee(difficulte: str) -> str:
    """Retourne l'émoji correspondant à la difficulté de la journée."""
    return EMOJI_JOURNEE.get(difficulte, '🟩')


def get_difficulte(type_seance: str) -> str:
    """Retourne la difficulté d'un type de séance."""
    for key, value in DIFFICULTE.items():
        if key in type_seance.lower().replace(' ', '_'):
            return value
    return 'endurance'