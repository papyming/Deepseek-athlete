# ============================================================
# FICHIER: src/utils/validators.py
# RÔLE: Validation et analyse des jours disponibles
#       CORRIGÉ: Suppression des imports inutiles
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
    
    # ---- 1. CAP ----
    col_cap = None
    for nom_colonne in [
        'Quels jours ? (CAP) [Course à pieds]',
        'Quels jours ? (CAP)',
        'Quels jours ? (Course à pieds)',
        'CAP',
        'Course à pieds'
    ]:
        if nom_colonne in row:
            col_cap = nom_colonne
            break
    
    if col_cap:
        valeur = str(row.get(col_cap, '')).strip()
        if valeur and valeur != '' and valeur != 'nan' and valeur != 'None':
            valeur = valeur.replace(';', ',').replace(' et ', ',').replace(' et', ',')
            valeur = valeur.replace(' ', ',')
            while ',,' in valeur:
                valeur = valeur.replace(',,', ',')
            jours = []
            for j in valeur.split(','):
                j = j.strip().capitalize()
                if j in jours_semaine:
                    jours.append(j)
            resultat['CAP'] = jours
    
    # ---- 2. Vélo ----
    col_velo = None
    for nom_colonne in [
        'Quels jours ? (Nat/vélo) [Vélo]',
        'Quels jours ? (Vélo)',
        'Quels jours ? (Nat/vélo) [Velo]',
        'Quels jours ? (Velo)',
        'Vélo',
        'Velo'
    ]:
        if nom_colonne in row:
            col_velo = nom_colonne
            break
    
    if col_velo:
        valeur = str(row.get(col_velo, '')).strip()
        if valeur and valeur != '' and valeur != 'nan' and valeur != 'None':
            if valeur.lower() not in ['non pratiquant', '0', 'aucun', '']:
                valeur = valeur.replace(';', ',').replace(' et ', ',').replace(' et', ',')
                valeur = valeur.replace(' ', ',')
                while ',,' in valeur:
                    valeur = valeur.replace(',,', ',')
                jours = []
                for j in valeur.split(','):
                    j = j.strip().capitalize()
                    if j in jours_semaine:
                        jours.append(j)
                resultat['Velo'] = jours
    
    # ---- 3. Natation ----
    col_natation = None
    for nom_colonne in [
        'Quels jours ? (Nat/vélo) [Natation,]',
        'Quels jours ? (Natation)',
        'Quels jours ? (Nat/vélo) [Natation]',
        'Natation',
        'Nat'
    ]:
        if nom_colonne in row:
            col_natation = nom_colonne
            break
    
    if col_natation:
        valeur = str(row.get(col_natation, '')).strip()
        if valeur and valeur != '' and valeur != 'nan' and valeur != 'None':
            if valeur.lower() not in ['non pratiquant', '0', 'aucun', '']:
                valeur = valeur.replace(';', ',').replace(' et ', ',').replace(' et', ',')
                valeur = valeur.replace(' ', ',')
                while ',,' in valeur:
                    valeur = valeur.replace(',,', ',')
                jours = []
                for j in valeur.split(','):
                    j = j.strip().capitalize()
                    if j in jours_semaine:
                        jours.append(j)
                resultat['Natation'] = jours
    
    # ---- 4. Bi-quotidien ----
    col_bi = None
    for nom_colonne in [
        'Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)',
        'Bi-quotidien',
        'bi_quotidien'
    ]:
        if nom_colonne in row:
            col_bi = nom_colonne
            break
    
    if col_bi:
        valeur = str(row.get(col_bi, '')).strip()
        if valeur and valeur != '' and valeur != 'nan' and valeur != 'None':
            if valeur.lower() not in ['non', '0', 'aucun', '']:
                bi_parsed = parser_jours_disciplines(valeur)
                for discipline, jours in bi_parsed.items():
                    if discipline in resultat['bi_quotidien']:
                        jours_normaux = resultat.get(discipline, [])
                        resultat['bi_quotidien'][discipline] = [j for j in jours if j in jours_normaux]
    
    return resultat