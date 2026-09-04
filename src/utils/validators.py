# ============================================================
# FICHIER: src/utils/validators.py
# RÔLE: Validation et analyse des jours disponibles
# ============================================================

from .parsers import parser_jours_disciplines


def analyser_jours_disponibles(row):
    """
    Analyse les jours d'entraînement depuis le CSV.
    """
    resultat = {
        'CAP': [],
        'Velo': [],
        'Natation': [],
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    
    jours_semaine = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # ---- CAP ----
    jours_cap = row.get('Quels jours ? (CAP)', '')
    if jours_cap and jours_cap != '':
        jours_cap = str(jours_cap).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_cap.replace(',', ' ').split() if j.strip()]
        resultat['CAP'] = [j for j in jours_list if j in jours_semaine]
    
    # ---- Vélo ----
    jours_velo = row.get('Quels jours ? (Vélo)', '')
    if jours_velo and jours_velo != '':
        jours_velo = str(jours_velo).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_velo.replace(',', ' ').split() if j.strip()]
        resultat['Velo'] = [j for j in jours_list if j in jours_semaine]
    
    # ---- Natation ----
    jours_natation = row.get('Quels jours ? (Natation)', '')
    if jours_natation and jours_natation != '':
        jours_natation = str(jours_natation).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_natation.replace(',', ' ').split() if j.strip()]
        resultat['Natation'] = [j for j in jours_list if j in jours_semaine]
    
    # ---- Bi-quotidien ----
    bi_str = row.get('Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)', '')
    if bi_str and bi_str != '':
        bi_parsed = parser_jours_disciplines(bi_str)
        for discipline, jours in bi_parsed.items():
            if discipline in resultat['bi_quotidien']:
                jours_normaux = resultat.get(discipline, [])
                resultat['bi_quotidien'][discipline] = [j for j in jours if j in jours_normaux]
    
    return resultat