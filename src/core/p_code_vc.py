import math

# ============================================================
# COEFFICIENTS VC (différenciés selon le genre)
# ============================================================
COEFF_VC_DISTANCE = {
    # Hommes (M) / Femmes (F)
    200: {'M': 1.2000, 'F': 1.1640},
    300: {'M': 1.1800, 'F': 1.1446},
    400: {'M': 1.1400, 'F': 1.1058},
    500: {'M': 1.1200, 'F': 1.0864},
    600: {'M': 1.1000, 'F': 1.0670},
    700: {'M': 1.0800, 'F': 1.0476},
    800: {'M': 1.0500, 'F': 1.0185},
    1000: {'M': 1.0200, 'F': 0.9894},
    1600: {'M': 1.0000, 'F': 0.9700},
    2000: {'M': 0.9800, 'F': 0.9506},
    2400: {'M': 0.9700, 'F': 0.9409},
    2800: {'M': 0.9600, 'F': 0.9312}
}

VITESSE_RECUP_VC = 0.5   # 50% de la VC
RAPPORT_RECUP_VC = 0.25  # 25% de la distance d'effort

def generer_seances_vc(vc: float, sexe: str, temps_min: int = 15, temps_max: int = 30):
    """
    Génère les séances VC selon le P-code.
    vc : km/h
    sexe : "M" ou "F"
    temps_min, temps_max : minutes
    """
    if not vc or math.isnan(vc):
        return []
    
    resultats = []
    
    for distance, coeffs in COEFF_VC_DISTANCE.items():
        coeff = coeffs.get(sexe, 1.0)
        pourcentage = coeff * 100
        
        vitesse_effort = vc * coeff
        distance_recup = distance * RAPPORT_RECUP_VC
        vitesse_recup = vc * VITESSE_RECUP_VC
        
        temps_effort_s = distance / (vitesse_effort / 3.6)
        temps_recup_s = distance_recup / (vitesse_recup / 3.6)
        temps_total_rep_s = temps_effort_s + temps_recup_s
        
        if distance <= 400:
            temps_cible_s = temps_min * 60
        elif distance >= 2000:
            temps_cible_s = temps_max * 60
        else:
            pente = (temps_max - temps_min) / (2000 - 400)
            temps_min_calc = temps_min + pente * (distance - 400)
            temps_cible_s = temps_min_calc * 60
        
        nb_rep = math.ceil(temps_cible_s / temps_total_rep_s)
        temps_total_seance_s = nb_rep * temps_total_rep_s
        
        resultats.append({
            "distance": distance,
            "pourcentage": round(pourcentage, 1),
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
    print("=== TEST VC (Homme, 14.0 km/h) ===")
    seances = generer_seances_vc(14.0, "M")
    for s in seances:
        print(f"{s['distance']}m : {s['pourcentage']}% VC → {s['vitesse_effort']} km/h")
        print(f"  Effort {s['temps_effort']}, recup {s['temps_recup']}, {s['nb_rep']} rep")
        print(f"  Total : {s['temps_total_seance']}")
        print()
    
    print("=== TEST VC (Femme, 14.0 km/h) ===")
    seances = generer_seances_vc(14.0, "F")
    for s in seances:
        print(f"{s['distance']}m : {s['pourcentage']}% VC → {s['vitesse_effort']} km/h")
        print(f"  Effort {s['temps_effort']}, recup {s['temps_recup']}, {s['nb_rep']} rep")
        print(f"  Total : {s['temps_total_seance']}")
        print()