# ============================================================
# FICHIER: src/core/p_code_vma.py
# RÔLE: Génération des séances VMA selon le P-code
#       CORRIGÉ: Import depuis physiology/
# ============================================================

import math
from .physiology import COEFF_VMA_DISTANCE


VITESSE_RECUP_VMA = 0.5
RAPPORT_RECUP_VMA = 0.25


def generer_seances_vma(vma: float, sexe: str, temps_min: int = 15, temps_max: int = 30):
    """
    Génère les séances VMA selon le P-code.
    vma : km/h
    sexe : "M" ou "F"
    temps_min, temps_max : minutes
    """
    if not vma or math.isnan(vma):
        return []
    
    resultats = []
    
    for distance, coeffs in COEFF_VMA_DISTANCE.items():
        coeff = coeffs.get(sexe, 105 if sexe == "M" else 102)
        pourcentage = coeff
        
        vitesse_effort = vma * (pourcentage / 100)
        distance_recup = distance * RAPPORT_RECUP_VMA
        vitesse_recup = vma * VITESSE_RECUP_VMA
        
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