# ============================================================
# FICHIER: src/core/physiology/profil.py
# RÔLE: Analyse du profil de l'athlète
#       CORRIGÉ: Priorité à la perte de vitesse entre distances
# ============================================================

def analyser_profil(vitesses_performances: dict, vma: float = None, vc: float = None) -> dict:
    """
    Analyse le profil de l'athlète (Endurant/Explosif/Équilibré).
    CORRIGÉ: Priorité à la perte de vitesse entre distances.
    """
    alertes = []
    nb_distances = len(vitesses_performances)
    
    v10 = vitesses_performances.get('10km')
    vsemi = vitesses_performances.get('semi')
    vmar = vitesses_performances.get('marathon')
    
    # ---- 3 distances ----
    if nb_distances >= 3 and v10 and vsemi and vmar:
        perte_10_semi = v10 - vsemi
        perte_semi_mar = vsemi - vmar
        perte_totale = v10 - vmar
        
        # Seuils basés sur la littérature
        if perte_10_semi < 0.8 and perte_semi_mar < 1.2 and perte_totale < 2.0:
            profil = "Endurant"
            alertes.append(f"Profil endurant : faible perte de vitesse (10km→marathon : {perte_totale:.1f} km/h)")
        elif perte_10_semi > 1.5 and perte_semi_mar > 1.5 and perte_totale > 3.0:
            profil = "Explosif"
            alertes.append(f"Profil explosif : forte perte de vitesse (10km→marathon : {perte_totale:.1f} km/h)")
        else:
            profil = "Équilibré"
            alertes.append(f"Profil équilibré : perte de vitesse modérée (10km→marathon : {perte_totale:.1f} km/h)")
        
        # Alerte si ratio VC/VMA incohérent
        if vma and vc and vma > 0 and vc > 0:
            ratio = vc / vma
            if profil == "Endurant" and ratio < 0.78:
                alertes.append(f"⚠️ Ratio VC/VMA ({ratio*100:.0f}%) bas pour un profil endurant → vérifier la VC")
            elif profil == "Explosif" and ratio > 0.90:
                alertes.append(f"⚠️ Ratio VC/VMA ({ratio*100:.0f}%) élevé pour un profil explosif → vérifier la VC")
        
        return {
            'profil': profil,
            'nb_distances': nb_distances,
            'alertes': alertes,
            'ratio': (vc / vma) if (vma and vc and vma > 0 and vc > 0) else None
        }
    
    # ---- 2 distances (10km + semi) ----
    if nb_distances >= 2 and v10 and vsemi:
        perte = v10 - vsemi
        if perte < 0.8:
            profil = "Endurant (tendance)"
        elif perte > 1.5:
            profil = "Explosif (tendance)"
        else:
            profil = "Équilibré"
        
        if vma and vc and vma > 0 and vc > 0:
            ratio = vc / vma
            if ratio < 0.78:
                alertes.append(f"⚠️ Ratio VC/VMA ({ratio*100:.0f}%) bas → vérifier les données")
        
        return {
            'profil': profil,
            'nb_distances': nb_distances,
            'alertes': alertes,
            'ratio': (vc / vma) if (vma and vc and vma > 0 and vc > 0) else None
        }
    
    # ---- 2 distances (semi + marathon) ----
    if nb_distances >= 2 and vsemi and vmar:
        perte = vsemi - vmar
        if perte < 0.8:
            profil = "Endurant (tendance)"
        elif perte > 1.5:
            profil = "Explosif (tendance)"
        else:
            profil = "Équilibré"
        
        if vma and vc and vma > 0 and vc > 0:
            ratio = vc / vma
            if ratio < 0.78:
                alertes.append(f"⚠️ Ratio VC/VMA ({ratio*100:.0f}%) bas → vérifier les données")
        
        return {
            'profil': profil,
            'nb_distances': nb_distances,
            'alertes': alertes,
            'ratio': (vc / vma) if (vma and vc and vma > 0 and vc > 0) else None
        }
    
    # ---- 1 distance ----
    if nb_distances == 1:
        profil = "Non déterminé (1 seule distance)"
        return {
            'profil': profil,
            'nb_distances': nb_distances,
            'alertes': alertes
        }
    
    # ---- Aucune distance ----
    profil = "Non déterminé (aucune distance)"
    return {
        'profil': profil,
        'nb_distances': nb_distances,
        'alertes': alertes
    }