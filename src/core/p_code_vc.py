# ============================================================
# FICHIER: src/core/p_code_vc.py
# RÔLE: Génération des séances VC selon le P-code
#       CORRIGÉ: Calcul du temps d'intensité total (effort × nb_rep)
# ============================================================

import math
from .physiology.vma import formater_temps
from .physiology.constants import COEFF_VC_DISTANCE


VITESSE_RECUP_PCT = 0.50
RAPPORT_RECUP = 0.25


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
        distance_recup = distance * RAPPORT_RECUP
        vitesse_recup = vc * VITESSE_RECUP_PCT
        
        temps_effort_s = distance / (vitesse_effort / 3.6)
        temps_recup_s = distance_recup / (vitesse_recup / 3.6)
        temps_total_rep_s = temps_effort_s + temps_recup_s
        
        # Temps cible de 15 à 30 minutes selon la distance
        if distance <= 400:
            temps_cible_s = temps_min * 60
        elif distance >= 2000:
            temps_cible_s = temps_max * 60
        else:
            pente = (temps_max - temps_min) / (2000 - 400)
            temps_min_calc = temps_min + pente * (distance - 400)
            temps_cible_s = temps_min_calc * 60
        
        nb_rep = math.ceil(temps_cible_s / temps_total_rep_s)
        
        # CORRIGÉ: Calcul du temps d'intensité total (effort × nb_rep)
        temps_intensite_total_s = nb_rep * temps_effort_s
        temps_intensite_total_min = round(temps_intensite_total_s / 60, 1)
        
        # On enlève la dernière récupération
        temps_total_seance_s = nb_rep * temps_effort_s + (nb_rep - 1) * temps_recup_s
        
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
            "temps_total_seance": formater_temps(temps_total_seance_s),
            "temps_intensite_total_min": temps_intensite_total_min,
            "temps_intensite_total": formater_temps(temps_intensite_total_s)
        })
    
    return resultats