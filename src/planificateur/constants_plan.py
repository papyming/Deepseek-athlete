# ============================================================
# FICHIER: src/planificateur/constants_plan.py
# RÔLE: Définit les constantes utilisées dans la planification
#       (émojis, types de séances, difficultés)
# ============================================================

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