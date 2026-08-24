# ============================================================
# FICHIER: src/planificateur/generateur/journee.py
# RÔLE: Construction d'une journée d'entraînement
#       CORRIGÉ: Natation max 90 min (fix bug 180 min)
# ============================================================

from datetime import datetime
from typing import Dict, List

from ..constants_plan import get_emoji_journee, VOLUME_MAX_PAR_SEANCE
from .dates import est_date_passee, jours_avant_objectif, est_affutage
from .seances import (
    generer_seance_endurance, generer_seance_renforcement,
    generer_seance_qualite, choisir_seance_qualite
)


def construire_journee(
    nom_jour: str,
    date_str: str,
    date_objectif: datetime,
    type_semaine: str,
    jours_cap: List[str],
    jours_velo: List[str],
    jours_natation: List[str],
    volumes: Dict[str, int],
    coeff_volume: float,
    coeff_intensite: float,
    natation_km: int,
    nb_intenses_requis: int,
    seances_intenses_placees: int,
    dernier_jour_intense: int,
    renforcement_place: bool,
    a_vma: bool,
    a_vc: bool,
    a_les_deux: bool,
    seances_vma: List[Dict],
    seances_vc: List[Dict],
    semaine_num: int,
    nb_cap: int,
    objectif: str,
    vma: float,
    vc: float,
    jours_dispo_renforcement: List[int],
    date_semaine: datetime,
    i: int,
    nb_semaines_total: int = 0
) -> Dict:
    # Date passée → Repos
    if est_date_passee(date_str):
        return {
            'jour': nom_jour,
            'date': date_str,
            'seances': [{'discipline': 'Repos', 'type': 'Repos', 'details': 'Repos', 'duree': 0, 'difficulte': 'repos'}],
            'difficulte': 'repos',
            'emoji': '⬜'
        }
    
    # Objectif
    if date_str == date_objectif.strftime('%Y-%m-%d'):
        return {
            'jour': nom_jour,
            'date': date_str,
            'seances': [{'discipline': 'Course', 'type': 'Objectif', 'details': objectif or 'Compétition', 'duree': 0, 'difficulte': 'course'}],
            'difficulte': 'course',
            'emoji': '⭐'
        }
    
    # Affûtage
    jours_avant = jours_avant_objectif(date_semaine, date_objectif, i)
    if est_affutage(jours_avant) or type_semaine == 'affutage':
        seances = []
        if nom_jour in jours_cap:
            seances.append(generer_seance_endurance('CAP', int(volumes.get('CAP', 45) * 0.65), 'Z1', 'endurance_recuperative'))
        if nom_jour in jours_velo:
            duree_velo = max(45, int(volumes.get('Velo', 90) * 0.65))
            seances.append(generer_seance_endurance('Vélo', duree_velo, 'Z1', 'recup'))
        if nom_jour in jours_natation:
            duree_natation = min(60, int(volumes.get('Natation', 45) * 0.65))
            seances.append(generer_seance_endurance('Natation', duree_natation, 'Z1', 'recup'))
        if not seances:
            seances.append({'discipline': 'Repos', 'type': 'Repos', 'details': 'Repos actif', 'duree': 0, 'difficulte': 'repos'})
        
        difficulte_journee = 'recuperation'
        for s in seances:
            if s.get('difficulte') in ['intense', 'seuil']:
                difficulte_journee = s.get('difficulte')
                break
        
        return {
            'jour': nom_jour,
            'date': date_str,
            'seances': seances,
            'difficulte': difficulte_journee,
            'emoji': get_emoji_journee(difficulte_journee)
        }
    
    seances = []
    cap_dispo = nom_jour in jours_cap
    velo_dispo = nom_jour in jours_velo
    natation_dispo = nom_jour in jours_natation
    
    # CAP
    if cap_dispo:
        peut_avoir_intense = (seances_intenses_placees < nb_intenses_requis) and (i - dernier_jour_intense) >= 2
        
        if nb_cap <= 2 and semaine_num % 3 == 0 and seances_intenses_placees == 0:
            peut_avoir_intense = True
        
        if a_les_deux and seances_intenses_placees < nb_intenses_requis:
            type_force = 'VMA' if semaine_num % 2 == 0 else 'VC'
            seance_data = None
            if type_force == 'VMA' and seances_vma:
                seance_data = seances_vma[(semaine_num + seances_intenses_placees) % len(seances_vma)]
                type_seance = 'VMA'
            elif type_force == 'VC' and seances_vc:
                seance_data = seances_vc[(semaine_num + seances_intenses_placees) % len(seances_vc)]
                type_seance = 'VC'
            if seance_data:
                seance = generer_seance_qualite(
                    seance_data, 'CAP', type_seance,
                    semaine_num, nb_semaines_total
                )
                seance['duree'] = int(seance['duree'] * coeff_intensite)
                seances.append(seance)
                cap_dispo = False
        
        if cap_dispo and peut_avoir_intense and seances_intenses_placees < nb_intenses_requis:
            seance_data, type_seance = choisir_seance_qualite(
                seances_vma, seances_vc, semaine_num, vma, vc, nb_cap, 
                seances_intenses_placees, nb_semaines_total
            )
            if seance_data:
                seance = generer_seance_qualite(
                    seance_data, 'CAP', type_seance,
                    semaine_num, nb_semaines_total
                )
                if type_seance != 'Test 3\'/6\'/12\'':
                    seance['duree'] = int(seance['duree'] * coeff_intensite)
                seances.append(seance)
            else:
                duree = int(volumes.get('CAP', 45) * coeff_volume)
                duree = min(duree, VOLUME_MAX_PAR_SEANCE['CAP'])
                seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale'))
        elif cap_dispo:
            if i == 5:  # Samedi
                duree = int(volumes.get('CAP', 45) * 1.5 * coeff_volume)
                duree = min(duree, VOLUME_MAX_PAR_SEANCE['CAP'])
                seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'sortie_longue'))
            elif i in [0, 3]:  # Lundi ou Jeudi
                duree = int(volumes.get('CAP', 45) * coeff_volume)
                duree = min(duree, VOLUME_MAX_PAR_SEANCE['CAP'])
                seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale'))
            else:
                duree = int(volumes.get('CAP', 45) * 0.7 * coeff_volume)
                duree = min(duree, VOLUME_MAX_PAR_SEANCE['CAP'])
                seances.append(generer_seance_endurance('CAP', duree, 'Z1', 'endurance_recuperative'))
    
    # Vélo
    if velo_dispo:
        duree = max(80, int(volumes.get('Velo', 90) * coeff_volume))
        duree = min(duree, VOLUME_MAX_PAR_SEANCE['Velo'])
        if i == 5:
            duree = max(120, int(duree * 1.3))
            duree = min(duree, VOLUME_MAX_PAR_SEANCE['Velo'])
            seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'sortie_longue'))
        elif i in [2, 4]:
            duree = max(80, int(duree * coeff_intensite))
            duree = min(duree, VOLUME_MAX_PAR_SEANCE['Velo'])
            seances.append({'discipline': 'Vélo', 'type': 'Seuil Z4', 'details': f'Seuil Z4 ({duree} min)', 'duree': duree, 'difficulte': 'seuil'})
        else:
            seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'endurance'))
    
    # Natation - CORRIGÉ: MAX 90 min ABSOLU
    if natation_dispo:
        # CORRIGÉ: Application stricte de la limite 90 min
        duree = min(int(volumes.get('Natation', 45) * coeff_volume), 90)
        
        if i in [1, 4]:
            duree = min(int(duree * coeff_intensite), 90)
            seances.append({'discipline': 'Natation', 'type': 'Technique + Seuil', 'details': f'Technique + seuil Z4 ({duree} min, {natation_km}km)', 'duree': duree, 'difficulte': 'seuil'})
        elif i == 2:
            duree = min(duree, 90)
            seances.append(generer_seance_endurance('Natation', duree, 'Z2', 'endurance'))
        else:
            duree = min(int(duree * 0.8), 90)
            seances.append(generer_seance_endurance('Natation', duree, 'Z1', 'recup'))
    
    # Renforcement - une seule séance par semaine MAX
    if not renforcement_place:
        est_jour_intense = any(s.get('difficulte') in ['intense', 'seuil'] for s in seances)
        if not est_jour_intense and i in jours_dispo_renforcement:
            seances.append(generer_seance_renforcement('Renforcement', 30))
            renforcement_place = True
    
    # Repos
    if not seances:
        seances.append({'discipline': 'Repos', 'type': 'Repos', 'details': 'Repos', 'duree': 0, 'difficulte': 'repos'})
    
    # Déterminer la difficulté de la journée
    difficulte_journee = 'endurance'
    for s in seances:
        if s.get('difficulte') == 'intense':
            difficulte_journee = 'intense'
            break
        elif s.get('difficulte') == 'seuil' and difficulte_journee != 'intense':
            difficulte_journee = 'seuil'
    
    return {
        'jour': nom_jour,
        'date': date_str,
        'seances': seances,
        'difficulte': difficulte_journee,
        'emoji': get_emoji_journee(difficulte_journee)
    }