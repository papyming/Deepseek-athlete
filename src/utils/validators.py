# ============================================================
# FICHIER: src/utils/validators.py
# RÔLE: Validation et analyse des jours disponibles
#       CORRIGÉ: Nouveaux noms de colonnes + sport principal
# ============================================================

from .parsers import parser_jours_disciplines


def valider_coherence_biquotidien(disponibilites, athlete_nom='', capacite_brute=None):
    """Valide la capacité et les jours bi-quotidiens avant planification."""
    capacite = disponibilites.get('bi_quotidien_nb')
    mode = disponibilites.get('bi_quotidien_mode', 'standard')
    jours_source_par_discipline = disponibilites.get(
        'bi_quotidien_source', disponibilites.get('bi_quotidien', {})
    )
    jours_par_discipline = disponibilites.get('bi_quotidien_tri_quadri', {}) if mode == 'tri_quadri' else jours_source_par_discipline
    jours = sorted({
        jour
        for jours_discipline in jours_par_discipline.values()
        for jour in jours_discipline
    })
    jours_source = sorted({
        jour
        for jours_discipline in jours_source_par_discipline.values()
        for jour in jours_discipline
    })
    jours_disponibles = sorted({
        jour
        for discipline in ['CAP', 'Velo', 'Natation']
        for jour in disponibilites.get(discipline, [])
    })
    nombre_jours = len(jours)

    resultat = {
        'valide': False,
        'statut': 'a_confirmer',
        'athlete': athlete_nom,
        'capacite': capacite,
        'capacite_brute': capacite_brute,
        'jours': jours,
        'jours_source': jours_source,
        'jours_disponibles': jours_disponibles,
        'jours_tri_quadri': jours if mode == 'tri_quadri' else [],
        'jours_biquotidien_restants': [jour for jour in jours_source if jour not in jours],
        'nombre_jours': nombre_jours,
        'message': ''
    }

    if mode == 'tri_quadri':
        if not jours_source:
            resultat['statut'] = 'insuffisant'
            resultat['message'] = f"ERREUR - DONNEES TRI/QUADRI INSUFFISANTES\n{athlete_nom}\nAucun jour bi-quotidien source n'est renseigne.\nVeuillez renseigner d'abord les jours bi-quotidiens avant la planification."
            return resultat
        jours_hors_source = sorted(set(jours) - set(jours_source))
        if jours_hors_source:
            resultat['statut'] = 'contradiction'
            resultat['message'] = f"ERREUR CONTRADICTOIRE - TRI/QUADRI\n{athlete_nom}\nJours TRI/QUADRI hors des jours bi-quotidiens possibles : {', '.join(jours_hors_source)}\nLa sélection doit être un sous-ensemble des jours renseignés.\nLa planification est bloquée."
            return resultat
        jours_hors_disponibilite = sorted(set(jours_source) - set(jours_disponibles))
        if jours_hors_disponibilite:
            resultat['statut'] = 'contradiction'
            resultat['message'] = f"ERREUR - JOURS BI-QUOTIDIEN HORS DISPONIBILITE\n{athlete_nom}\nJours bi-quotidiens déclarés absents des jours d'entraînement : {', '.join(jours_hors_disponibilite)}\nJours d'entraînement disponibles : {', '.join(jours_disponibles) or 'Aucun'}\nVeuillez corriger les informations de l'athlete avant planification."
            return resultat
        if not jours:
            resultat['message'] = f"CORRECTION NECESSAIRE - TRI/QUADRI\n{athlete_nom}\nAucun jour TRI/QUADRI n'est selectionne.\nVeuillez selectionner au moins un jour avant la planification."
            return resultat
        resultat['valide'] = True
        resultat['statut'] = 'coherent'
        resultat['message'] = f"VERIFICATION - TRI/QUADRI\n{athlete_nom}\nJours renseignes en bi-quotidien : {', '.join(jours_source)}\nJours selectionnes en TRI/QUADRI : {', '.join(jours)}\nJours restants en bi-quotidien : {', '.join(resultat['jours_biquotidien_restants']) or 'Aucun'}\nCapacite TRI/QUADRI correspondant a la selection : {len(jours)} jour(s)."
        return resultat

    jours_hors_disponibilite = sorted(set(jours) - set(jours_disponibles))
    if jours_hors_disponibilite:
        resultat['statut'] = 'contradiction'
        resultat['message'] = f"ERREUR - JOURS BI-QUOTIDIEN HORS DISPONIBILITE\n{athlete_nom}\nJours bi-quotidiens déclarés absents des jours d'entraînement : {', '.join(jours_hors_disponibilite)}\nJours d'entraînement disponibles : {', '.join(jours_disponibles) or 'Aucun'}\nVeuillez corriger les informations de l'athlete avant planification."
        return resultat

    if capacite is None:
        resultat['message'] = 'Capacité bi-quotidien indéterminée : confirmation nécessaire avant planification.'
        return resultat

    if capacite == 0 and nombre_jours > 0:
        resultat['statut'] = 'contradiction'
        resultat['message'] = f"ERREUR - DONNEES BI-QUOTIDIEN INCOHERENTES\n{athlete_nom}\nCapacite declaree : {capacite_brute or 'Non'}\nJour bi-quotidien renseigne : {', '.join(jours)}\nContradiction : l'athlete declare ne pas pouvoir faire de bi-quotidien mais un jour bi-quotidien est renseigne.\nCorrection de l'athlete necessaire avant planification."
        return resultat

    if capacite > 0 and nombre_jours == 0:
        resultat['statut'] = 'insuffisant'
        resultat['message'] = f'Jours bi-quotidiens manquants : {capacite} jour(s) à renseigner.'
        return resultat

    if capacite > 0 and capacite > nombre_jours:
        resultat['statut'] = 'contradiction'
        resultat['message'] = f"ERREUR - DONNEES BI-QUOTIDIEN INCOHERENTES\n{athlete_nom}\nCapacite annoncee : {capacite} jours/semaine\nJours bi-quotidiens renseignes : {', '.join(jours) or 'Aucun'}\nNombre de jours renseignes : {nombre_jours}\nNombre de jours annonce : {capacite}\nContradiction : la capacité de {capacite} supérieure au nombre de jours renseignés.\nVeuillez corriger les informations de l'athlete avant planification."
        return resultat

    resultat['valide'] = True
    resultat['statut'] = 'coherent'
    resultat['message'] = 'Données bi-quotidien cohérentes.'
    return resultat


def analyser_jours_disponibles(row):
    """
    Analyse les jours d'entraînement depuis le CSV.
    CORRIGÉ: Nouveaux noms de colonnes + sport principal + contraintes.
    """
    resultat = {
        'CAP': [],
        'Velo': [],
        'Natation': [],
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
        'sport_principal': '',
        'contraintes': {
            'velo_weekend': False,
            'pas_velo_dimanche': False,
            'pas_cap_samedi': False,
            'double_seance': False
        }
    }
    
    jours_semaine = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # ---- 0. Sport principal ----
    col_sport = None
    for nom_colonne in [
        "Quel sport est l'objectif principal de ce plan ?",
        "Quel sport est l'objectif principal de ce plan",
        "Sport objectif"
    ]:
        if nom_colonne in row:
            col_sport = nom_colonne
            break
    
    if col_sport:
        valeur = str(row.get(col_sport, '')).strip()
        if valeur and valeur != '' and valeur != 'nan':
            resultat['sport_principal'] = valeur
    
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
        'Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s) ex: Nat=Lundi,Mercredi Velo=Dimanche CAP=Mardi,Jeudi',
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
                        resultat['bi_quotidien'][discipline] = list(dict.fromkeys(jours))
    
    # ---- 5. Contraintes ----
    contraintes = ''
    for nom_colonne in [
        'A ne pas oublier  !!!',
        'A ne pas oublier !!!',
        'A ne pas oublier',
        'Compléments à rajouter pour améliorer le suivi, contraintes pro/perso, santé, emploi du temps, etc...'
    ]:
        if nom_colonne in row:
            contraintes = str(row.get(nom_colonne, '')).strip()
            break
    
    if contraintes and contraintes != '' and contraintes != 'nan':
        contraintes_lower = contraintes.lower()
        
        if 'vélo le week-end' in contraintes_lower or 'velo le week-end' in contraintes_lower:
            resultat['contraintes']['velo_weekend'] = True
        
        if 'pas de vélo le dimanche' in contraintes_lower or 'pas de velo le dimanche' in contraintes_lower:
            resultat['contraintes']['pas_velo_dimanche'] = True
        
        if 'pas de cap le samedi' in contraintes_lower or 'pas de course le samedi' in contraintes_lower:
            resultat['contraintes']['pas_cap_samedi'] = True
        
        if 'double séance' in contraintes_lower or 'double seance' in contraintes_lower:
            resultat['contraintes']['double_seance'] = True
        
        if '1 seule fois du vélo le dimanche' in contraintes_lower or '1 seule fois du velo le dimanche' in contraintes_lower:
            resultat['contraintes']['pas_velo_samedi'] = True
    
    return resultat