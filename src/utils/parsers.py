def parser_bi_quotidien(valeur):
    if not valeur:
        return 0
    valeur = str(valeur).lower()
    if 'non' in valeur:
        return 0
    elif '1 fois' in valeur:
        return 1
    elif '2 fois' in valeur:
        return 2
    elif '3 fois' in valeur:
        return 3
    elif 'tri' in valeur or 'quadri' in valeur:
        return 4
    return 0

def parser_jours_disciplines(valeur):
    resultat = {'CAP': [], 'Velo': [], 'Natation': []}
    if not valeur:
        return resultat
    valeur = str(valeur)
    parties = valeur.split()
    for partie in parties:
        if '=' not in partie:
            continue
        discipline, jours_str = partie.split('=', 1)
        discipline = discipline.strip().capitalize()
        jours = [j.strip().capitalize() for j in jours_str.split(',') if j.strip()]
        if discipline in ['Cap', 'Course', 'Running']:
            resultat['CAP'].extend(jours)
        elif discipline in ['Velo', 'Cyclisme', 'Bike']:
            resultat['Velo'].extend(jours)
        elif discipline in ['Nat', 'Natation', 'Swim']:
            resultat['Natation'].extend(jours)
    return resultat