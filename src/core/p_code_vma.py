import math

def generer_seances_vma(vma: float, sexe: str, temps_min: int = 15, temps_max: int = 30):
    """
    Génère les séances VMA selon le P-code
    vma : km/h
    sexe : "M" ou "F"
    temps_min, temps_max : minutes
    """
    
    # Table de correspondance VMA
    table_vma = [
        {"distance": 200,  "%H": 105, "%F": 102},
        {"distance": 300,  "%H": 99,  "%F": 97},
        {"distance": 400,  "%H": 98,  "%F": 96},
        {"distance": 500,  "%H": 97,  "%F": 95},
        {"distance": 600,  "%H": 96,  "%F": 94},
        {"distance": 700,  "%H": 95,  "%F": 93},
        {"distance": 800,  "%H": 94,  "%F": 92},
        {"distance": 1000, "%H": 92,  "%F": 90},
        {"distance": 2000, "%H": 89,  "%F": 87},
        {"distance": 3000, "%H": 85,  "%F": 82}
    ]
    
    resultats = []
    
    for row in table_vma:
        distance = row["distance"]
        pourcentage = row["%H"] if sexe == "M" else row["%F"]
        
        # Vitesse d'effort
        vitesse_effort = vma * (pourcentage / 100)
        
        # Récupération
        distance_recup = distance * 0.25
        vitesse_recup = vma * 0.5
        
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
            "pourcentage": pourcentage,
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
    """Convertit des secondes en MM:SS"""
    minutes = int(secondes // 60)
    sec = int(secondes % 60)
    return f"{minutes:02d}:{sec:02d}"


# Test
if __name__ == "__main__":
    print("=== TEST VMA (Homme, 16.5 km/h) ===")
    seances = generer_seances_vma(16.5, "M")
    for s in seances:
        print(f"{s['distance']}m : {s['pourcentage']}% VMA → {s['vitesse_effort']} km/h")
        print(f"  Effort {s['temps_effort']}, recup {s['temps_recup']}, {s['nb_rep']} rep")
        print(f"  Total : {s['temps_total_seance']}")