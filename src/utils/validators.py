from .parsers import parser_jours_disciplines

def analyser_jours_disponibles(row):
    resultat = {
        'CAP': [],
        'Velo': [],
        'Natation': [],
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    
    jours_cap = row.get('Quels jours ? (CAP)', '')
    if jours_cap:
        resultat['CAP'] = [j.strip().capitalize() for j in str(jours_cap).replace(';', ',').split(',') if j.strip()]
    
    jours_velo = row.get('Quels jours ? (Vélo)', '')
    if jours_velo:
        resultat['Velo'] = [j.strip().capitalize() for j in str(jours_velo).replace(';', ',').split(',') if j.strip()]
    
    jours_natation = row.get('Quels jours ? (Natation)', '')
    if jours_natation:
        resultat['Natation'] = [j.strip().capitalize() for j in str(jours_natation).replace(';', ',').split(',') if j.strip()]
    
    bi_str = row.get('Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)', '')
    if bi_str:
        bi_parsed = parser_jours_disciplines(bi_str)
        for discipline, jours in bi_parsed.items():
            if discipline in resultat['bi_quotidien']:
                jours_normaux = resultat.get(discipline, [])
                resultat['bi_quotidien'][discipline] = [j for j in jours if j in jours_normaux]
    
    return resultat