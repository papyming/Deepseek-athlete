import math
from .constants import COEFF_VMA_DISTANCE, POURCENTAGE_VMA

def formater_temps(secondes: float) -> str:
    if math.isnan(secondes) or math.isinf(secondes):
        return "00:00"
    minutes = int(secondes // 60)
    sec = int(secondes % 60)
    return f"{minutes:02d}:{sec:02d}"

def extraire_vma(athlete_data: dict) -> dict:
    """
    Extrait la VMA déclarée ou l'estime depuis la VC.
    Retourne : {'vma': float, 'origine': str, 'alerte': str or None}
    """
    champ = athlete_data.get('Avez vous fait un test VMA (Vitesse Maximale Aérobie) ou de VC (Vitesse Critique) ? Sinon avez vous une idée de votre VMA ou de votre VC ?', '')
    result = {'vma': None, 'origine': None, 'alerte': None}
    
    if not champ or champ == '':
        return result
    
    champ = str(champ).upper().replace(' ', '')
    
    # VMA déclarée
    import re
    match = re.search(r'VMA[=:]*([0-9.]+)', champ)
    if match:
        result['vma'] = float(match.group(1))
        result['origine'] = "Déclarée (colonne VMA)"
        return result
    
    # VC déclarée → VMA estimée
    match_vc = re.search(r'VC[=:]*([0-9.]+)', champ)
    if match_vc:
        vc = float(match_vc.group(1))
        result['vma'] = round(vc / 0.85, 1)
        result['origine'] = f"Estimée depuis la VC ({vc} km/h)"
        result['alerte'] = f"VMA estimée depuis la VC ({vc} km/h) → à valider par un test VMA."
        return result
    
    try:
        result['vma'] = float(champ)
        result['origine'] = "Déclarée (valeur numérique)"
        return result
    except:
        return result

def estimer_vma(vitesses_performances: dict) -> float:
    """
    Estime la VMA à partir des performances en course.
    Utilise les pourcentages de soutien moyens.
    """
    estimations = []
    if '10km' in vitesses_performances:
        estimations.append(vitesses_performances['10km'] / POURCENTAGE_VMA['10km'])
    if 'semi' in vitesses_performances:
        estimations.append(vitesses_performances['semi'] / POURCENTAGE_VMA['semi'])
    if 'marathon' in vitesses_performances:
        estimations.append(vitesses_performances['marathon'] / POURCENTAGE_VMA['marathon'])
    
    if len(estimations) >= 2:
        return round(sum(estimations) / len(estimations), 1)
    return None

def generer_tableau_vma(vma: float, genre: str) -> list:
    """
    Génère le tableau des zones VMA.
    """
    if not vma or math.isnan(vma):
        return []
    
    tableau = []
    for distance, coeffs in COEFF_VMA_DISTANCE.items():
        coeff = coeffs.get(genre, 105 if genre == "M" else 102)
        vitesse = vma * (coeff / 100)
        temps_sec = distance / (vitesse / 3.6)
        
        if math.isnan(temps_sec) or math.isinf(temps_sec):
            continue
        
        distance_recup = distance * 0.25
        vitesse_recup = vma * 0.5
        temps_recup_sec = distance_recup / (vitesse_recup / 3.6)
        
        tableau.append({
            'distance': distance,
            'vitesse': round(vitesse, 1),
            'coeff': coeff,
            'temps': formater_temps(temps_sec),
            'temps_sec': round(temps_sec, 2),
            'distance_recup': round(distance_recup, 1),
            'vitesse_recup': round(vitesse_recup, 1),
            'temps_recup': formater_temps(temps_recup_sec),
            'temps_recup_sec': round(temps_recup_sec, 2)
        })
    return tableau