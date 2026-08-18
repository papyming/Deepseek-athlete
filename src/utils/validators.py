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
    print(f"   🔍 Jours CAP bruts : {jours_cap} (type: {type(jours_cap)})")
    if jours_cap and jours_cap != '':
        jours_cap = str(jours_cap).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_cap.replace(',', ' ').split() if j.strip()]
        resultat['CAP'] = [j for j in jours_list if j in jours_semaine]
        print(f"   🔍 Jours CAP parsés : {resultat['CAP']}")
    
    # ---- Vélo ----
    jours_velo = row.get('Quels jours ? (Vélo)', '')
    print(f"   🔍 Jours Vélo bruts : {jours_velo} (type: {type(jours_velo)})")
    if jours_velo and jours_velo != '':
        jours_velo = str(jours_velo).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_velo.replace(',', ' ').split() if j.strip()]
        resultat['Velo'] = [j for j in jours_list if j in jours_semaine]
        print(f"   🔍 Jours Vélo parsés : {resultat['Velo']}")
    
    # ---- Natation ----
    jours_natation = row.get('Quels jours ? (Natation)', '')
    print(f"   🔍 Jours Natation bruts : {jours_natation} (type: {type(jours_natation)})")
    if jours_natation and jours_natation != '':
        jours_natation = str(jours_natation).replace(';', ',').replace(' et ', ',')
        jours_list = [j.strip().capitalize() for j in jours_natation.replace(',', ' ').split() if j.strip()]
        resultat['Natation'] = [j for j in jours_list if j in jours_semaine]
        print(f"   🔍 Jours Natation parsés : {resultat['Natation']}")
    
    # ---- Bi-quotidien ----
    bi_str = row.get('Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)', '')
    print(f"   🔍 Bi-quotidien brut : {bi_str} (type: {type(bi_str)})")
    if bi_str and bi_str != '':
        bi_parsed = parser_jours_disciplines(bi_str)
        for discipline, jours in bi_parsed.items():
            if discipline in resultat['bi_quotidien']:
                jours_normaux = resultat.get(discipline, [])
                resultat['bi_quotidien'][discipline] = [j for j in jours if j in jours_normaux]
        print(f"   🔍 Bi-quotidien parsé : {resultat['bi_quotidien']}")
    
    return resultat