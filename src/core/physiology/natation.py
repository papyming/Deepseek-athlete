import math
from .constants import ZONES_NATATION, DISTANCES_NATATION, RAPPORT_RECUP_NATATION

def extraire_temps_400m(athlete_data: dict) -> dict:
    """
    Extrait le temps sur 400m nage libre.
    Retourne : {'temps_sec': int, 'vitesse_ms': float, 'allure_100m': str}
    """
    temps_str = athlete_data.get('Temps actuel sur 400m nage libre (laisser vide sinon)', '')
    if temps_str is None or temps_str == '':
        return {'temps_sec': None, 'vitesse_ms': None, 'allure_100m': None}
    
    temps_str = str(temps_str).strip()
    if not temps_str or temps_str == '' or temps_str == 'nan' or temps_str == 'None':
        return {'temps_sec': None, 'vitesse_ms': None, 'allure_100m': None}
    
    # Convertir le temps en secondes
    parties = temps_str.split(':')
    try:
        if len(parties) == 2:
            temps_sec = int(parties[0]) * 60 + int(parties[1])
        elif len(parties) == 3:
            temps_sec = int(parties[0]) * 3600 + int(parties[1]) * 60 + int(parties[2])
        else:
            return {'temps_sec': None, 'vitesse_ms': None, 'allure_100m': None}
    except:
        return {'temps_sec': None, 'vitesse_ms': None, 'allure_100m': None}
    
    if temps_sec <= 0:
        return {'temps_sec': None, 'vitesse_ms': None, 'allure_100m': None}
    
    vitesse_ms = 400 / temps_sec
    allure_100m = temps_sec / 4  # secondes pour 100m
    
    return {
        'temps_sec': temps_sec,
        'vitesse_ms': round(vitesse_ms, 2),
        'allure_100m': _formater_temps(allure_100m)
    }

def generer_zones_natation(vitesse_ms: float) -> dict:
    """
    Génère les 6 zones natation basées sur la vitesse 400m.
    Retourne un dict avec les zones Z1 à Z6 en min/100m.
    """
    if not vitesse_ms:
        return {}
    
    zones = {}
    for zone, (bas, haut) in ZONES_NATATION.items():
        vitesse_min = vitesse_ms * bas
        vitesse_max = vitesse_ms * haut
        # Conversion en min/100m : (100 / vitesse) / 60
        allure_min = (100 / vitesse_max) / 60 if vitesse_max > 0 else None
        allure_max = (100 / vitesse_min) / 60 if vitesse_min > 0 else None
        
        zones[zone] = {
            'vitesse_min': round(vitesse_min, 2),
            'vitesse_max': round(vitesse_max, 2),
            'allure_min': _formater_temps(allure_min * 60) if allure_min else None,
            'allure_max': _formater_temps(allure_max * 60) if allure_max else None
        }
    return zones

def generer_tableau_natation(vitesse_ms: float) -> list:
    """
    Génère un tableau des zones natation avec :
    - Zone
    - Vitesse (m/s)
    - Allure (min/100m)
    - Temps d'intensité pour 25m/50m/75m/100m
    - Temps de repos correspondant (50% de l'effort)
    """
    if not vitesse_ms:
        return []
    
    zones = generer_zones_natation(vitesse_ms)
    tableau = []
    
    for zone, valeurs in zones.items():
        if valeurs['vitesse_max'] is None:
            continue
        
        # Calculer les temps pour chaque distance
        temps_intensite = {}
        temps_repos = {}
        for distance in DISTANCES_NATATION:
            temps_sec = distance / valeurs['vitesse_max']  # en secondes
            temps_intensite[distance] = _formater_temps(temps_sec)
            temps_repos[distance] = _formater_temps(temps_sec * RAPPORT_RECUP_NATATION)
        
        tableau.append({
            'zone': zone,
            'vitesse_max': valeurs['vitesse_max'],
            'allure_max': valeurs['allure_max'],
            'temps_intensite': temps_intensite,
            'temps_repos': temps_repos,
            'distances': DISTANCES_NATATION
        })
    
    return tableau

def _formater_temps(secondes: float) -> str:
    """Formate un temps en MM:SS"""
    if secondes is None or math.isnan(secondes) or math.isinf(secondes):
        return "00:00"
    minutes = int(secondes // 60)
    sec = int(secondes % 60)
    return f"{minutes:02d}:{sec:02d}"