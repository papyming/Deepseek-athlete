import math

def generer_seances_vc(vc: float, sexe: str, temps_min: int = 15, temps_max: int = 30):
    """
    Génère les séances VC selon le P-code
    vc : km/h
    sexe : "M" ou "F"
    temps_min, temps_max : minutes
    """
    
    # Coefficient Femme
    coeff_femme = 0.97 if sexe == "F" else 1.0
    
    # Table de correspondance VC
    table_vc = [
        {"distance": 200,  "%H": 120, "%F": 120 * coeff_femme},
        {"distance": 300,  "%H": 118, "%F": 118 * coeff_femme},
        {"distance": 400,  "%H": 114, "%F": 114 * coeff_femme},
        {"distance": 500,  "%H": 112, "%F": 112 * coeff_femme},
        {"distance": 600,  "%H": 110, "%F": 110 * coeff_femme},
        {"distance": 700,  "%H": 108, "%F": 108 * coeff_femme},
        {"distance": 800,  "%H": 105, "%F": 105 * coeff_femme},
        {"distance": 1000, "%H": 102, "%F": 102 * coeff_femme},
        {"distance": 1600, "%H": 100, "%F": 100 * coeff_femme},
        {"distance": 2000, "%H": 98,  "%F": 98  * coeff_femme},
        {"distance": 2400, "%H": 97,  "%F": 97  * coeff_femme},
        {"distance": 2800, "%H": 96,  "%F": 96  * coeff_femme}
    ]
    
    resultats = []
    
    for row in table_vc:
        distance = row["distance"]
        pourcentage = row["%H"] if sexe == "M" else row["%F"]
        
        # Vitesse d'effort
        vitesse_effort = vc * (pourcentage / 100)
        
        # Récupération
        distance_recup = distance * 0.25
        vitesse_recup = vc * 0.5
        
        # Temps
        temps_effort_s = distance / (vitesse_effort / 3.6)
        temps_recup_s = distance_recup / (vitesse_recup / 3.6)
        temps_total_rep_s = temps_effort_s + temps_recup_s
        
        # Temps cible selon la distance
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
        
        # Stockage
        resultats.append({
            "distance": distance,
            "pourcentage": round(pourcentage, 1),
            "vitesse_effort": round(vitesse_effort, 1),
            "temps_effort": formater_temps(temps_effort_s),
            "distance_recup": distance_recup,
            "vitesse_recup": round(vitesse_recup, 1),
            "temps_recup": formater_temps(temps_recup_s),
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


# Test
if __name__ == "__main__":
    print("=== TEST VC (Femme, 12.47 km/h) ===")
    seances = generer_seances_vc(12.47, "F")
    for s in seances:
        print(f"{s['distance']}m : {s['pourcentage']}% VC → {s['vitesse_effort']} km/h")
        print(f"  Effort {s['temps_effort']}, recup {s['temps_recup']}, {s['nb_rep']} rep")
        print(f"  Total : {s['temps_total_seance']}")
        print()