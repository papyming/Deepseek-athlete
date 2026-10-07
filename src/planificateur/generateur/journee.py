# ============================================================
# FICHIER: src/planificateur/generateur/journee.py
# RÔLE: Construction d'une journée d'entraînement
#       CORRIGÉ: Espacement 48h, limitation volume week-end
# ============================================================

from datetime import datetime
from typing import Dict, List

from ..constants_plan import (
    get_emoji_journee,
    VELO_DUREE_MIN,
    VELO_DUREE_MAX_TECHNIQUE,
    VOLUME_MAX_PAR_SEANCE,
)
from .dates import jours_avant_objectif, est_affutage
from .seances import (
    generer_seance_endurance, generer_seance_renforcement,
    generer_seance_qualite, choisir_seance_qualite
)


def _est_biquotidien_reel(seances: List[Dict], biquotidien_actif: bool) -> bool:
    """Une journée n'est bi-quotidienne que si au moins deux séances réelles y sont générées."""
    if not biquotidien_actif:
        return False
    return len([s for s in seances if s.get('discipline') != 'Repos']) >= 2


_SPORT_DISCIPLINES = ('CAP', 'Vélo', 'Velo', 'Natation')
_MAX_SPORT_PAR_STATUT = {'normal': 1, 'biquotidien': 2, 'tri': 3, 'quadri': 4}


def _nb_seances_sport(seances: List[Dict]) -> int:
    """Compte les séances CAP/Vélo/Natation (hors Renforcement, Repos, Course)."""
    return len([s for s in seances if s.get('discipline') in _SPORT_DISCIPLINES])


def _seance_cap_endurance(jour_semaine: int, volumes: Dict[str, int], coeff_volume: float) -> Dict:
    """Séance CAP d'endurance selon le jour, hors rôles longue et intensité."""
    if jour_semaine == 6:  # Dimanche
        duree = int(volumes.get('CAP', 45) * 0.5 * coeff_volume)
        duree = min(duree, 45)
        if duree > 30:
            return generer_seance_endurance('CAP', duree, 'Z1', 'endurance_recuperative')
        return {'discipline': 'Repos', 'type': 'Repos', 'details': 'Repos actif', 'duree': 0, 'difficulte': 'repos'}
    elif jour_semaine in [0, 3]:  # Lundi ou Jeudi
        duree = min(int(volumes.get('CAP', 45) * coeff_volume), 60)
        return generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale')
    else:
        duree = min(int(volumes.get('CAP', 45) * 0.6 * coeff_volume), 45)
        return generer_seance_endurance('CAP', duree, 'Z1', 'endurance_recuperative')


def _seance_cap_longue(volumes: Dict[str, int], coeff_volume: float) -> Dict:
    """Séance CAP de sortie longue portée par un rôle longue explicite."""
    duree = int(volumes.get('CAP', 45) * 1.3 * coeff_volume)
    duree = min(duree, 90)
    if duree > 60:
        return generer_seance_endurance('CAP', duree, 'Z2', 'sortie_longue')
    return generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale')


def _duree_velo_qualite(duree: int) -> int:
    """Plafonne une séance Vélo de qualité à [80, 180] min.

    Seules les séances de qualité (Seuil/Intensité) sont bornées à 180 min
    (``VOLUME_MAX_PAR_SEANCE['Velo']``). Les séances Endurance et Sortie longue
    ne passent pas par ce plafond et peuvent donc dépasser 180 min.
    """
    plafond = VOLUME_MAX_PAR_SEANCE.get('Velo', 180)
    return max(VELO_DUREE_MIN, min(int(plafond), int(duree)))


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
    nb_semaines_total: int = 0,
    sport_principal: str = 'Triathlon',
    biquotidien_actif: bool = False,
    statut_jour: str = 'normal',
    roles_jour: Dict[str, str] = None,
    derniere_categorie_cap: str = None,
    durees_velo_par_jour: Dict[str, int] = None
) -> Dict:
    jour_semaine = datetime.strptime(date_str, '%Y-%m-%d').weekday()

    # Objectif
    if date_str == date_objectif.strftime('%Y-%m-%d'):
        seances = [{'discipline': 'Course', 'type': 'Objectif', 'details': objectif or 'Compétition', 'duree': 0, 'difficulte': 'course'}]
        return {
            'jour': nom_jour,
            'date': date_str,
            'seances': seances,
            'difficulte': 'course',
            'emoji': '⭐',
            'biquotidien': _est_biquotidien_reel(seances, biquotidien_actif)
        }
    
    # Affûtage
    jours_avant = jours_avant_objectif(date_semaine, date_objectif, i)
    if est_affutage(jours_avant) or type_semaine == 'affutage':
        seances = []
        if nom_jour in jours_cap:
            seances.append(generer_seance_endurance('CAP', int(volumes.get('CAP', 45) * 0.65), 'Z1', 'endurance_recuperative'))
        if nom_jour in jours_velo:
            duree_velo = None
            if durees_velo_par_jour:
                duree_velo = durees_velo_par_jour.get(nom_jour)
            if duree_velo is None:
                duree_velo = int(volumes.get('Velo', VELO_DUREE_MIN) or VELO_DUREE_MIN)
            duree_velo = max(VELO_DUREE_MIN, min(VELO_DUREE_MAX_TECHNIQUE, int(duree_velo)))
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
            'emoji': get_emoji_journee(difficulte_journee),
            'biquotidien': _est_biquotidien_reel(seances, biquotidien_actif)
        }
    
    seances = []
    cap_dispo = nom_jour in jours_cap
    velo_dispo = nom_jour in jours_velo
    natation_dispo = nom_jour in jours_natation
    
    # Espacement des séances intenses (48h = 2 jours d'écart) - chemin historique
    peut_avoir_intense = (
        seances_intenses_placees < nb_intenses_requis and
        (i - dernier_jour_intense) >= 2
    )

    # Rôles de placement décidés par construire_semaine. Sans rôle explicite,
    # on reconstruit l'ancien comportement jour par jour pour compatibilité.
    if roles_jour is None:
        role_cap = 'intensite' if (cap_dispo and peut_avoir_intense) else (
            'longue' if (cap_dispo and jour_semaine == 5) else 'endurance'
        )
        role_velo = 'intensite' if jour_semaine in [2, 4] else (
            'longue' if jour_semaine == 5 else 'endurance'
        )
        role_natation = 'intensite' if jour_semaine in [1, 4] else 'endurance'
        roles_jour = {'CAP': role_cap, 'Velo': role_velo, 'Natation': role_natation}

    role_cap = roles_jour.get('CAP')
    role_velo = roles_jour.get('Velo')
    role_natation = roles_jour.get('Natation')

    # ---- CAP ----
    if cap_dispo:
        if role_cap == 'intensite':
            seance_data, type_seance = choisir_seance_qualite(
                seances_vma, seances_vc, semaine_num, vma, vc, nb_cap,
                seances_intenses_placees, nb_semaines_total,
                derniere_categorie=derniere_categorie_cap
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
                duree = min(duree, 60)
                seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale'))
        elif role_cap == 'longue':
            seances.append(_seance_cap_longue(volumes, coeff_volume))
        else:
            seances.append(_seance_cap_endurance(jour_semaine, volumes, coeff_volume))
    
    # ---- Vélo ----
    # Durée imposée par la répartition du budget hebdomadaire (>= 80 min).
    # Endurance et Sortie longue peuvent dépasser 180 min (borne technique
    # absolue uniquement) ; la qualité, elle, est plafonnée à 180 min.
    # Aucune réapplication du coefficient de période : le budget le contient
    # déjà une seule fois.
    if velo_dispo and not (jour_semaine == 6 and cap_dispo):
        duree_velo = None
        if durees_velo_par_jour:
            duree_velo = durees_velo_par_jour.get(nom_jour)
        if duree_velo is None:
            duree_velo = int(volumes.get('Velo', VELO_DUREE_MIN) or VELO_DUREE_MIN)
        duree = max(VELO_DUREE_MIN, min(VELO_DUREE_MAX_TECHNIQUE, int(duree_velo)))
        if role_velo == 'intensite':
            # Qualité vélo : plafonnée à 180 min (VOLUME_MAX_PAR_SEANCE['Velo']).
            duree_qualite = _duree_velo_qualite(duree)
            seances.append({'discipline': 'Vélo', 'type': 'Seuil Z4', 'details': f'Seuil Z4 ({duree_qualite} min)', 'duree': duree_qualite, 'difficulte': 'seuil'})
        elif role_velo == 'longue':
            seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'sortie_longue'))
        else:
            seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'endurance'))
    
    # ---- Natation ----
    if natation_dispo:
        # Pas de Natation le dimanche si déjà CAP ou Vélo
        if jour_semaine == 6 and (cap_dispo or velo_dispo):
            pass
        else:
            duree = min(int(volumes.get('Natation', 45) * coeff_volume), 90)
            
            if role_natation == 'intensite':
                duree = min(int(duree * coeff_intensite), 90)
                seances.append({'discipline': 'Natation', 'type': 'Technique + Seuil', 'details': f'Technique + seuil Z4 ({duree} min, {natation_km}km)', 'duree': duree, 'difficulte': 'seuil'})
            elif jour_semaine == 2:  # Mercredi
                duree = min(duree, 90)
                seances.append(generer_seance_endurance('Natation', duree, 'Z2', 'endurance'))
            else:
                duree = min(int(duree * 0.8), 90)
                seances.append(generer_seance_endurance('Natation', duree, 'Z1', 'recup'))
    
    # ---- Renforcement ----
    if not renforcement_place and len(jours_cap) > 0:
        est_jour_intense = any(s.get('difficulte') in ['intense', 'seuil'] for s in seances)
        if not est_jour_intense and jour_semaine in jours_dispo_renforcement:
            seances.append(generer_seance_renforcement('Renforcement', 30))
            renforcement_place = True
    
    # ---- Repos ----
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
        'emoji': get_emoji_journee(difficulte_journee),
        'biquotidien': _est_biquotidien_reel(seances, biquotidien_actif)
    }