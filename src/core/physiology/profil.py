def analyser_profil(vitesses_performances: dict, vma: float = None, vc: float = None) -> dict:
    """
    Analyse le profil de l'athlète (Endurant/Explosif/Moyen).
    Retourne : {'profil': str, 'nb_distances': int, 'alertes': list}
    """
    alertes = []
    nb_distances = len(vitesses_performances)
    
    if nb_distances >= 3:
        v10 = vitesses_performances.get('10km')
        vsemi = vitesses_performances.get('semi')
        vmar = vitesses_performances.get('marathon')
        
        if v10 and vsemi and vmar:
            if vsemi > (v10 - 1) and vmar > (vsemi - 1):
                profil = "Endurant"
            elif vsemi < (v10 - 1) and vmar < (vsemi - 1):
                profil = "Explosif"
            else:
                profil = "Moyen"
        else:
            profil = "Non déterminé (données incomplètes)"
    elif nb_distances == 2:
        v10 = vitesses_performances.get('10km')
        vsemi = vitesses_performances.get('semi')
        vmar = vitesses_performances.get('marathon')
        
        if v10 and vsemi:
            if vsemi > (v10 - 1):
                profil = "Endurant (tendance)"
            elif vsemi < (v10 - 1):
                profil = "Explosif (tendance)"
            else:
                profil = "Moyen"
        elif vsemi and vmar:
            if vmar > (vsemi - 1):
                profil = "Endurant"
            elif vmar < (vsemi - 1):
                profil = "Explosif (tendance)"
            else:
                profil = "Moyen"
        else:
            profil = "Non déterminé (2 distances)"
    elif nb_distances == 1:
        profil = "Non déterminé (1 seule distance)"
    else:
        profil = "Non déterminé (aucune distance)"
    
    # Vérification cohérence VMA/VC
    if vma and vc:
        ratio = vc / vma
        if ratio < 0.75 or ratio > 0.95:
            alertes.append(f"Incohérence VMA/VC : VMA={vma} km/h, VC={vc} km/h (ratio {ratio:.2f})")
    
    return {
        'profil': profil,
        'nb_distances': nb_distances,
        'alertes': alertes
    }