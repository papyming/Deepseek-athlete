import math
from .constants import ZONES_FTP

def extraire_ftp(athlete_data: dict) -> dict:
    """
    Extrait la FTP en Watts.
    Retourne : {'ftp': int, 'origine': str}
    """
    ftp_str = athlete_data.get('FTP vélo en watt (laisser vide sinon)', '')
    if ftp_str is None or ftp_str == '':
        return {'ftp': None, 'origine': None}
    
    ftp_str = str(ftp_str).strip()
    if not ftp_str or ftp_str == '' or ftp_str == 'nan' or ftp_str == 'None':
        return {'ftp': None, 'origine': None}
    
    try:
        return {
            'ftp': int(float(ftp_str)),
            'origine': 'Déclarée (colonne FTP)'
        }
    except:
        return {'ftp': None, 'origine': None}

def generer_zones_velo(ftp: int) -> dict:
    """
    Génère les 6 zones vélo basées sur la FTP (modèle Coggan).
    Retourne un dict avec les zones Z1 à Z6 en Watts.
    """
    if not ftp:
        return {}
    
    zones = {}
    for zone, (bas, haut) in ZONES_FTP.items():
        zones[zone] = {
            'min': int(ftp * bas),
            'max': int(ftp * haut)
        }
    return zones

def generer_tableau_velo(ftp: int) -> list:
    """
    Génère un tableau des zones vélo pour affichage.
    """
    if not ftp:
        return []
    
    zones = generer_zones_velo(ftp)
    tableau = []
    for zone, valeurs in zones.items():
        tableau.append({
            'zone': zone,
            'min_watts': valeurs['min'],
            'max_watts': valeurs['max']
        })
    return tableau