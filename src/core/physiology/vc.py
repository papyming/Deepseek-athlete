# ============================================================
# FICHIER: src/core/physiology/vc.py
# RÔLE: Calcul de la Vitesse Critique
#       CORRIGÉ: Récupération = 50% de la VC
# ============================================================

import math
import re
import numpy as np
from .constants import COEFF_VC_DISTANCE
from .vma import formater_temps


# CORRIGÉ: Constante définie en haut du fichier
VITESSE_RECUP_PCT = 0.50


def extraire_vc(athlete_data: dict, vma: float = None) -> dict:
    """
    Extrait la VC avec priorité :
    1. Test VC 3'/6'/12'
    2. Déclaration directe
    3. Régression sur performances (modèle puissance critique)
    4. Estimation depuis VMA
    """
    result = {'vc': None, 'origine': None, 'alerte': None, 'test_3_6_12': None}
    
    # ---- 1. Test VC 3'/6'/12' ----
    test_vc = athlete_data.get('Si vous avez fait le test de Vitesse Critique (VC) 3\'/6\'/12\' Veuillez saisir les 3 distances ci dessous avec la syntaxe suivante : 3=X/6=Y/12=Z', '')
    if test_vc and test_vc != '':
        test_vc = str(test_vc).strip().replace(' ', '')
        match = re.search(r'3=(\d+)/6=(\d+)/12=(\d+)', test_vc)
        if match:
            d3 = float(match.group(1))
            d6 = float(match.group(2))
            d12 = float(match.group(3))
            result['test_3_6_12'] = f"3={d3}m/6={d6}m/12={d12}m"
            
            temps = [3*60, 6*60, 12*60]
            distances = [d3/1000, d6/1000, d12/1000]
            try:
                vc = _calculer_vc_regression(distances, temps)
                if vc:
                    result['vc'] = vc
                    result['origine'] = f"Calculée depuis le test VC 3'/6'/12' (3={d3}m, 6={d6}m, 12={d12}m)"
                    result['alerte'] = f"VC calculée depuis le test VC 3'/6'/12' → Valeur fiable (3 points)"
                    return result
            except:
                pass
    
    # ---- 2. Déclaration directe ----
    champ = athlete_data.get('Avez vous fait un test VMA (Vitesse Maximale Aérobie) ou de VC (Vitesse Critique) ? Sinon avez vous une idée de votre VMA ou de votre VC ?', '')
    if champ and champ != '':
        champ = str(champ).upper().replace(' ', '')
        match = re.search(r'VC[=:]*([0-9.]+)', champ)
        if match:
            result['vc'] = float(match.group(1))
            result['origine'] = "Déclarée (colonne VC)"
            return result
    
    # ---- 3. Régression sur performances ----
    vitesses = []
    distances = []  # en km
    origines = []
    
    if athlete_data.get('Quel est votre temps sur 10kms ?'):
        t = _temps_vers_secondes(athlete_data['Quel est votre temps sur 10kms ?'])
        if t and t > 0:
            vitesses.append(10 / (t / 3600))
            distances.append(10)
            origines.append("10km")
    
    if athlete_data.get('Quel est votre temps sur semi marathon ?'):
        t = _temps_vers_secondes(athlete_data['Quel est votre temps sur semi marathon ?'])
        if t and t > 0:
            vitesses.append(21.1 / (t / 3600))
            distances.append(21.1)
            origines.append("semi-marathon")
    
    if athlete_data.get('Quel est votre temps sur marathon ?'):
        t = _temps_vers_secondes(athlete_data['Quel est votre temps sur marathon ?'])
        if t and t > 0:
            vitesses.append(42.195 / (t / 3600))
            distances.append(42.195)
            origines.append("marathon")
    
    if len(vitesses) >= 2:
        try:
            temps = [d / v * 3600 for d, v in zip(distances, vitesses)]
            vc = _calculer_vc_regression(distances, temps, vitesses)
            if vc:
                result['vc'] = vc
                result['origine'] = f"Calculée par régression sur {len(vitesses)} distances ({', '.join(origines)})"
                if len(vitesses) < 3:
                    result['alerte'] = f"VC calculée avec seulement {len(vitesses)} distances → précision limitée."
                return result
        except:
            pass
    
    # ---- 4. Estimation depuis VMA ----
    if vma:
        result['vc'] = round(vma * 0.85, 1)
        result['origine'] = f"Estimée depuis la VMA ({vma} km/h, 85%)"
        result['alerte'] = f"VC estimée depuis la VMA ({vma} km/h, 85%) → à valider par un test VC."
        return result
    
    return result


def _calculer_vc_regression(distances: list, temps: list, vitesses: list = None) -> float:
    """
    Calcule la VC par régression linéaire.
    """
    if len(distances) < 2:
        return None
    
    import numpy as np
    distances = np.array(distances)
    temps = np.array(temps)
    
    # Détection du profil endurant
    if vitesses and len(vitesses) >= 3:
        v10 = vitesses[0] if len(vitesses) > 0 else None
        vsemi = vitesses[1] if len(vitesses) > 1 else None
        vmar = vitesses[2] if len(vitesses) > 2 else None
        
        if v10 and vsemi and vmar:
            perte_10_semi = v10 - vsemi
            perte_semi_mar = vsemi - vmar
            
            # Si très endurant (faible perte de vitesse)
            if perte_10_semi < 0.6 and perte_semi_mar < 1.2:
                vc_kmh = vmar * 1.03
                return round(vc_kmh, 1)
    
    # Régression linéaire classique
    coeffs = np.polyfit(temps, distances, 1)
    a = coeffs[0]  # km/s
    vc_kmh = a * 3600  # km/h
    
    # Vérification: VC doit être < vitesse sur la plus longue distance
    v_min = min([d / t * 3600 for d, t in zip(distances, temps)])
    
    if vc_kmh > v_min and len(distances) >= 3:
        coeffs2 = np.polyfit(temps[1:], distances[1:], 1)
        vc_kmh = coeffs2[0] * 3600
    
    if vc_kmh > v_min:
        vc_kmh = v_min * 0.95
    
    if vc_kmh < 8 or vc_kmh > 30:
        return None
    
    return round(vc_kmh, 1)


def _temps_vers_secondes(temps_str: str) -> int:
    """Convertit un temps (HH:MM:SS ou MM:SS) en secondes."""
    if not temps_str or temps_str == '':
        return None
    temps_str = str(temps_str).strip()
    if not temps_str or temps_str == 'nan' or temps_str == 'None':
        return None
    parties = temps_str.split(':')
    try:
        if len(parties) == 2:
            return int(parties[0]) * 60 + int(parties[1])
        elif len(parties) == 3:
            return int(parties[0]) * 3600 + int(parties[1]) * 60 + int(parties[2])
    except:
        return None
    return None


def generer_tableau_vc(vc: float, genre: str) -> list:
    """
    Génère le tableau des zones VC.
    CORRIGÉ: Récupération = 50% de la VC
    """
    if not vc or math.isnan(vc):
        return []
    
    # CORRIGÉ: Utiliser la constante définie en haut du fichier
    VITESSE_RECUP_PCT = 0.50
    
    tableau = []
    for distance, coeffs in COEFF_VC_DISTANCE.items():
        coeff = coeffs.get(genre, 1.0)
        vitesse_effort = vc * coeff
        temps_effort_sec = distance / (vitesse_effort / 3.6)
        
        if math.isnan(temps_effort_sec) or math.isinf(temps_effort_sec):
            continue
        
        distance_recup = int(distance * 0.25)
        # CORRIGÉ: Calcul correct de la vitesse de récupération
        vitesse_recup = round(vc * VITESSE_RECUP_PCT, 1)
        temps_recup_sec = distance_recup / (vitesse_recup / 3.6) if vitesse_recup > 0 else 0
        
        tableau.append({
            'distance_effort': distance,
            'vitesse_effort': round(vitesse_effort, 1),
            'temps_effort': formater_temps(temps_effort_sec),
            'temps_effort_sec': round(temps_effort_sec, 2),
            'distance_recup': distance_recup,
            'vitesse_recup': vitesse_recup,
            'temps_recup': formater_temps(temps_recup_sec),
            'temps_recup_sec': round(temps_recup_sec, 2),
            'coeff': coeff
        })
    return tableau