import math

# ============================================================
# COEFFICIENTS VMA (extraits de ta feuille "VMA/Piste")
# ============================================================
COEFF_VMA_DISTANCE = {
    200: {'M': 105, 'F': 102},
    300: {'M': 99, 'F': 97},
    400: {'M': 98, 'F': 96},
    500: {'M': 97, 'F': 95},
    600: {'M': 96, 'F': 94},
    700: {'M': 95, 'F': 93},
    800: {'M': 94, 'F': 92},
    1000: {'M': 92, 'F': 90},
    2000: {'M': 89, 'F': 87},
    3000: {'M': 85, 'F': 82}
}

VITESSE_RECUP_VMA = 0.5   # 50% de la VMA
RAPPORT_RECUP_VMA = 0.25  # 25% de la distance d'effort

def generer_seances_vma(vma: float, sexe: str, temps_min: int = 15, temps_max: int = 30):
    """
    Génère les séances VMA selon le P-code
    vma : km/h
    sexe : "M" ou "F"
    temps_min, temps_max : minutes
    """
    # 🔥 Vérifier que vma est valide
    if not vma or math.isnan(vma):
        return []
    
    resultats = []
    
    for distance, coeffs in COEFF_VMA_DISTANCE.items():
        coeff = coeffs.get(sexe, 105) if sexe == "M" else coeffs.get(sexe, 102)
        pourcentage = coeff
        
        # Vitesse d'effort (km/h)
        vitesse_effort = vma * (pourcentage / 100)
        
        # Récupération : 25% de la distance, à 50% de la VMA
        distance_recup = distance * RAPPORT_RECUP_VMA
        vitesse_recup = vma * VITESSE_RECUP_VMA
        
        # Temps (secondes)
        temps_effort_s = distance / (vitesse_effort / 3.6)
        temps_recup_s = distance_recup / (vitesse_recup / 3.6)
        temps_total_rep_s = temps_effort_s + temps_recup_s
        
        # Temps cible
        if distance <= 400:
            temps_cible_s = temps_min * 60
        elif distance >= 2000:
            temps_cible_s = temps_max * 60
        else:
            pente = (temps_max - temps_min) / (2000 - 400)
            temps_min_calc = temps_min + pente * (distance - 400)
            temps_cible_s = temps_min_calc * 60
        
        # Nombre de répétitions
        nb_rep = math.ceil(temps_cible_s / temps_total_rep_s)
        temps_total_seance_s = nb_rep * temps_total_rep_s
        
        resultats.append({
            "distance": distance,
            "pourcentage": pourcentage,
            "vitesse_effort": round(vitesse_effort, 1),
            "temps_effort": formater_temps(temps_effort_s),
            "temps_effort_sec": round(temps_effort_s, 2),
            "distance_recup": round(distance_recup, 1),
            "vitesse_recup": round(vitesse_recup, 1),
            "temps_recup": formater_temps(temps_recup_s),
            "temps_recup_sec": round(temps_recup_s, 2),
            "temps_total_rep": formater_temps(temps_total_rep_s),
            "nb_rep": nb_rep,
            "temps_cible": formater_temps(temps_cible_s),
            "temps_total_seance": formater_temps(temps_total_seance_s)
        })
    
    return resultats


def formater_temps(secondes: float) -> str:
    minutes = int(secondes // 60)
    sec = int(secondes % 60)
    return f"{minutes:02d}:{sec:02d}"


if __name__ == "__main__":
    print("=== TEST VMA (Homme, 16.5 km/h) ===")
    seances = generer_seances_vma(16.5, "M")
    for s in seances:
        print(f"{s['distance']}m : {s['pourcentage']}% VMA → {s['vitesse_effort']} km/h")
        print(f"  Effort {s['temps_effort']}, recup {s['temps_recup']}, {s['nb_rep']} rep")
        print(f"  Total : {s['temps_total_seance']}")
        print()