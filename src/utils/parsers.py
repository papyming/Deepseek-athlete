# ============================================================
# FICHIER: src/utils/parsers.py
# RÔLE: Fonctions de parsing des données du CSV
#       CORRIGÉ: Support de multiples formats
# ============================================================

import math
from datetime import datetime


def parser_date_debut(saisie):
    """Convertit une saisie utilisateur de date de début en date Python.

    - vide / None -> None (comportement actuel : aujourd'hui)
    - format utilisateur JJ/MM/AAAA -> datetime
    - format ISO AAAA-MM-JJ accepté pour compatibilité interne
    - tout autre format -> ValueError
    """
    if saisie is None:
        return None
    if isinstance(saisie, datetime):
        return saisie
    texte = str(saisie).strip()
    if not texte:
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(texte, fmt)
        except ValueError:
            continue
    raise ValueError(
        f"Date invalide : '{texte}'. Format attendu : JJ/MM/AAAA (ex: 01/08/2026)."
    )


def est_reponse_tri_quadri(valeur):
    """Indique si la réponse demande une sélection de jours tri/quadri."""
    if valeur is None:
        return False
    return 'tri' in str(valeur).lower() or 'quadri' in str(valeur).lower()


def parser_bi_quotidien(valeur):
    """
    Convertit la réponse 'Possibilité de faire du bi-quotidien ?'
    en nombre de jours où l'athlète peut faire plusieurs séances.
    """
    if valeur is None:
        return None
    if isinstance(valeur, float) and math.isnan(valeur):
        return None
    if not valeur:
        return None
    
    valeur = str(valeur).lower()
    
    if 'non' in valeur:
        return 0
    elif '1 fois' in valeur:
        return 1
    elif '2 fois' in valeur:
        return 2
    elif '3 fois' in valeur:
        return 3
    elif est_reponse_tri_quadri(valeur):
        return None
    elif valeur == 'autre' or 'à voir' in valeur or 'a voir' in valeur:
        return None
    else:
        return 0


def selectionner_jours_tri_quadri(jours_par_discipline):
    """Propose les jours source et retourne les jours sélectionnés par l'athlète."""
    jours_par_discipline = jours_par_discipline or {}
    ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    jours = sorted({
        jour
        for jours_discipline in jours_par_discipline.values()
        for jour in jours_discipline
        if jour in ordre
    }, key=ordre.index)
    if not jours:
        print("ERREUR : aucun jour bi-quotidien n'est renseigné dans les données de l'athlète.")
        print("Veuillez renseigner d'abord les jours bi-quotidiens avant la planification.")
        return {}

    print("\nL'athlète a indiqué qu'il peut faire du tri/quadri.")
    print("Quels jours peut-il réaliser ces journées ?")
    print("Sélectionnez parmi les jours renseignés en bi-quotidien :")
    for index, jour in enumerate(jours, start=1):
        print(f"   {index}. {jour}")

    while True:
        saisie = input("Sélectionnez un ou plusieurs numéros (ex: 1 ou 1,2) : ").strip()
        if not saisie:
            print("ERREUR : aucun jour sélectionné. La planification sera bloquée.")
            continue
        try:
            indices = sorted({int(element.strip()) for element in saisie.split(',')})
        except ValueError:
            print("Saisie invalide : utilisez les numéros affichés, séparés par des virgules.")
            continue
        if not indices or any(index < 1 or index > len(jours) for index in indices):
            print("Saisie invalide : sélectionnez uniquement les numéros affichés.")
            continue
        selection = set(jours[index - 1] for index in indices)
        return {
            discipline: [jour for jour in jours_discipline if jour in selection]
            for discipline, jours_discipline in jours_par_discipline.items()
        }


def _lire_nombre_jours_tri_quadri():
    """Compatibilité interne : le nombre tri/quadri provient désormais de la sélection."""
    return None
    while True:
        try:
            saisie = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ Saisie interrompue : valeur non renseignée.\n")
            return None

        if saisie == '':
            print("ℹ️ Aucune valeur enregistrée : nombre de jours non renseigné.\n")
            return None

        if not saisie.isdigit():
            print("⚠️ Saisie invalide : veuillez entrer un entier compris entre 1 et 7.")
            continue

        nb = int(saisie)
        if 1 <= nb <= 7:
            print(f"✅ {nb} jour(s) enregistré(s)\n")
            return nb

        print("⚠️ Valeur hors plage : veuillez entrer un entier compris entre 1 et 7.")


def parser_jours_disciplines(valeur):
    """
    Parse la colonne 'Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)'
    CORRIGÉ: Supporte plusieurs formats.
    """
    resultat = {'CAP': [], 'Velo': [], 'Natation': []}
    
    if valeur is None:
        return resultat
    if isinstance(valeur, float) and math.isnan(valeur):
        return resultat
    if not valeur:
        return resultat
    
    valeur = str(valeur).strip()
    if not valeur or valeur == '' or valeur == 'nan' or valeur == 'None':
        return resultat
    
    # Essayer de parser différents formats
    
    # Format 1: CAP=Lundi,Mardi,Jeudi Velo=Mercredi
    if '=' in valeur and any(discipline in valeur for discipline in ['CAP', 'Velo', 'Nat']):
        parties = valeur.split()
        for partie in parties:
            if '=' not in partie:
                continue
            discipline, jours_str = partie.split('=', 1)
            discipline = discipline.strip().capitalize()
            jours = [j.strip().capitalize() for j in jours_str.split(',') if j.strip()]
            
            if discipline in ['Cap', 'Course', 'Running', 'CAP']:
                resultat['CAP'].extend(jours)
            elif discipline in ['Velo', 'Cyclisme', 'Bike', 'Vélo']:
                resultat['Velo'].extend(jours)
            elif discipline in ['Nat', 'Natation', 'Swim']:
                resultat['Natation'].extend(jours)
        
        return resultat
    
    # Format 2: "Mardi CAP" (un jour et une discipline sans '=')
    jours_semaine = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    mots = valeur.replace(';', ' ').replace(',', ' ').split()
    disciplines = {
        'cap': 'CAP', 'course': 'CAP', 'running': 'CAP',
        'velo': 'Velo', 'vélo': 'Velo', 'cyclisme': 'Velo',
        'nat': 'Natation', 'natation': 'Natation', 'swim': 'Natation'
    }
    for mot in mots:
        discipline = disciplines.get(mot.lower())
        if discipline:
            for jour in mots:
                jour_normalise = jour.strip().capitalize()
                if jour_normalise in jours_semaine:
                    resultat[discipline].append(jour_normalise)
            return resultat

    # Format 3: "Lundi, Mardi, Jeudi" (CAP uniquement)
    # ou "Lundi=Mardi=Jeudi"
    # Remplacer les séparateurs
    valeur = valeur.replace('=', ',').replace(';', ',').replace(' et ', ',')
    jours = [j.strip().capitalize() for j in valeur.split(',') if j.strip()]
    
    # Filtrer les jours valides
    jours_valides = [j for j in jours if j in jours_semaine]
    
    if jours_valides:
        # Si c'est CAP=Lundi,Mardi,Jeudi, la discipline est déjà définie
        # Sinon, on suppose que c'est du CAP par défaut
        if 'CAP' not in valeur and 'Velo' not in valeur and 'Nat' not in valeur:
            resultat['CAP'] = jours_valides
    
    return resultat