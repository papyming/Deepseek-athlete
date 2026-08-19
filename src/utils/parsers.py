import math

def parser_bi_quotidien(valeur):
    """
    Convertit la réponse 'Possibilité de faire du bi-quotidien ?' en nombre de jours
    où l'athlète peut faire plusieurs séances dans la même journée.
    """
    if valeur is None:
        return 0
    if isinstance(valeur, float) and math.isnan(valeur):
        return 0
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
        print("\n")
        print("="*60)
        print("L'ATHLETE A INDIQUE QU'IL PEUT FAIRE DU TRI/QUADRI.")
        print("CECI SIGNIFIE QU'IL PEUT EFFECTUER PLUSIEURS SEANCES DANS LA MEME JOURNEE.")
        print("VEUILLEZ SAISIR LE NOMBRE DE JOURS PAR SEMAINE OU IL PEUT FAIRE 2 SEANCES (OU PLUS) :")
        print("(ex: 1, 2, 3 ou 4)")
        print("="*60)
        try:
            saisie = input("> ").strip()
            if saisie and saisie.isdigit():
                nb = int(saisie)
                print(f"✅ {nb} jour(s) par semaine avec séance(s) supplémentaire(s) enregistré(s)\n")
                return nb
            else:
                print("⚠️ Saisie invalide. Valeur par défaut : 2\n")
                return 2
        except:
            print("⚠️ Saisie invalide. Valeur par défaut : 2\n")
            return 2
    elif valeur == 'autre':
        print("\n")
        print("="*60)
        print("L'ATHLETE A INDIQUE 'AUTRE' POUR LE BI-QUOTIDIEN.")
        print("VEUILLEZ SAISIR LE NOMBRE DE JOURS PAR SEMAINE OU IL PEUT FAIRE 2 SEANCES (OU PLUS) :")
        print("(ex: 1, 2, 3 ou 4)")
        print("="*60)
        try:
            saisie = input("> ").strip()
            if saisie and saisie.isdigit():
                nb = int(saisie)
                print(f"✅ {nb} jour(s) par semaine avec séance(s) supplémentaire(s) enregistré(s)\n")
                return nb
            else:
                print("⚠️ Saisie invalide. Valeur par défaut : 1\n")
                return 1
        except:
            print("⚠️ Saisie invalide. Valeur par défaut : 1\n")
            return 1
    else:
        return 0


def parser_jours_disciplines(valeur):
    """
    Parse la colonne 'Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)'
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