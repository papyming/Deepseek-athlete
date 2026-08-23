# ============================================================
# FICHIER: src/planificateur/generateur_semaine.py
# RÔLE: Génération des semaines d'entraînement
#       Construit chaque semaine avec ses séances
#       Respecte le cahier des charges (intensité 15-30min, S-00, etc.)
# ============================================================

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .constants_plan import (
    TYPES_SEANCES_CAP, TYPES_SEANCES_VELO, TYPES_SEANCES_NATATION,
    TYPES_RENFORCEMENT, get_emoji_semaine, get_emoji_journee,
    get_difficulte
)
from .periodisation import (
    determiner_phase, determiner_type_semaine,
    get_volume_coeff, get_intensite_coeff, get_volume_semaine_affichage
)
from .volume import (
    calculer_volume_hebdo, get_nb_intenses_requis,
    get_natation_km, ajuster_nb_rep_pour_intensite,
    get_duree_intensite_min, VOLUME_MAX_PAR_SEANCE
)

JOURS_SEMAINE = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def generer_jour_date(date_semaine: datetime, jour_index: int) -> str:
    """Génère la date au format YYYY-MM-DD pour un jour de la semaine."""
    jour_date = date_semaine + timedelta(days=jour_index)
    return jour_date.strftime('%Y-%m-%d')


def est_date_passee(date_str: str) -> bool:
    """Vérifie si une date est passée."""
    aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date < aujourd_hui


def choisir_seance_qualite(
    seances_vma: List[Dict],
    seances_vc: List[Dict],
    semaine_num: int,
    vma: float,
    vc: float,
    nb_seances_cap: int,
    seance_index: int
) -> Tuple[Optional[Dict], str]:
    """
    Choisit une séance de qualité selon les règles du cahier des charges.
    
    Règle 3.3:
    - Si ni VMA ni VC → tests 3'/6'/12'
    - Si VMA seule → priorité VMA
    - Si VC seule → priorité VC
    - Si les deux → alternance
    """
    a_vma = vma is not None and not math.isnan(vma) and vma > 0
    a_vc = vc is not None and not math.isnan(vc) and vc > 0
    
    # Si ni VMA ni VC → tests 3'/6'/12'
    if not a_vma and not a_vc:
        return {
            'type': 'Test 3\'/6\'/12\'',
            'details': 'Test de Vitesse Critique: 3\'/6\'/12\' (espacer de 48h)',
            'distance': 'Test',
            'pourcentage': 0,
            'vitesse_effort': 0,
            'temps_effort': '03:00',
            'temps_effort_sec': 180,
            'nb_rep': 1,
            'distance_effort': 'Test',
            'distance_recup': 0,
            'temps_recup': '00:00',
            'temps_recup_sec': 0
        }, 'Test 3\'/6\'/12\''
    
    # Alternance VMA/VC si les deux sont présentes
    if a_vma and a_vc:
        if semaine_num % 2 == 0:
            if seances_vma:
                idx = (semaine_num + seance_index) % len(seances_vma)
                return seances_vma[idx], 'VMA'
        else:
            if seances_vc:
                idx = (semaine_num + seance_index) % len(seances_vc)
                return seances_vc[idx], 'VC'
    
    # VMA seule
    if a_vma and seances_vma:
        idx = (semaine_num + seance_index) % len(seances_vma)
        return seances_vma[idx], 'VMA'
    
    # VC seule
    if a_vc and seances_vc:
        idx = (semaine_num + seance_index) % len(seances_vc)
        return seances_vc[idx], 'VC'
    
    return None, 'Endurance'


def generer_seance_endurance(
    discipline: str,
    duree: int,
    zone: str = "Z2",
    type_seance: str = 'endurance'
) -> Dict:
    """Génère une séance d'endurance."""
    if discipline == 'CAP':
        type_label = TYPES_SEANCES_CAP.get(type_seance, f'Endurance {zone}')
    elif discipline == 'Vélo':
        type_label = TYPES_SEANCES_VELO.get(type_seance, f'Endurance {zone}')
    elif discipline == 'Natation':
        type_label = TYPES_SEANCES_NATATION.get(type_seance, f'Endurance {zone}')
    else:
        type_label = f'Endurance {zone}'
    
    return {
        'discipline': discipline,
        'type': type_label,
        'details': f'{type_label} ({duree} min)',
        'duree': duree,
        'difficulte': get_difficulte(type_seance)
    }


def generer_seance_renforcement(discipline: str, duree: int = 30) -> Dict:
    """Génère une séance de renforcement musculaire."""
    type_choisi = random.choice(TYPES_RENFORCEMENT)
    difficulte = get_difficulte(type_choisi.lower().replace(' ', '_'))
    return {
        'discipline': discipline,
        'type': type_choisi,
        'details': f'{type_choisi} ({duree} min)',
        'duree': duree,
        'difficulte': difficulte
    }


def generer_seance_qualite(seance_data: Dict, discipline: str, type_seance: str) -> Dict:
    """
    Génère une séance de qualité avec les détails complets.
    
    Règle 3.2: L'intensité doit durer entre 15' et 30'.
    Détails: distance + temps effort + distance recup + temps recup
    """
    distance = seance_data.get('distance_effort', seance_data.get('distance', '?'))
    pourcentage = seance_data.get('pourcentage', 0)
    vitesse_effort = seance_data.get('vitesse_effort', 0)
    temps_effort = seance_data.get('temps_effort', '00:00')
    temps_effort_sec = seance_data.get('temps_effort_sec', 0)
    nb_rep = seance_data.get('nb_rep', 4)
    distance_recup = seance_data.get('distance_recup', 0)
    temps_recup = seance_data.get('temps_recup', '00:00')
    
    # Vérifier que l'intensité dure entre 15' et 30'
    duree_intense_min = get_duree_intensite_min(nb_rep, temps_effort_sec)
    
    # Ajuster le nombre de répétitions si nécessaire
    if duree_intense_min < 15:
        nb_rep_ajuste = ajuster_nb_rep_pour_intensite(nb_rep, temps_effort_sec, 0, 20)
        if nb_rep_ajuste != nb_rep:
            nb_rep = nb_rep_ajuste
            # Recalculer la durée totale
            duree_totale_sec = nb_rep * temps_effort_sec
            duree_totale_min = int(duree_totale_sec / 60)
    elif duree_intense_min > 30:
        nb_rep_ajuste = ajuster_nb_rep_pour_intensite(nb_rep, temps_effort_sec, 0, 20)
        if nb_rep_ajuste != nb_rep:
            nb_rep = nb_rep_ajuste
    
    # Construire les détails complets
    details = f"{type_seance} {distance}m x {nb_rep} @ {vitesse_effort} km/h"
    details += f" (effort {temps_effort}"
    if distance_recup > 0 and temps_recup != '00:00':
        details += f" / recup {distance_recup}m x {temps_recup}"
    details += ")"
    
    # Ajouter la durée totale d'intensité si > 15min
    duree_intense_min = get_duree_intensite_min(nb_rep, temps_effort_sec)
    if duree_intense_min >= 15:
        details += f" - {duree_intense_min}min d'intensité"
    
    # Calculer la durée de la séance
    duree_seance = int(nb_rep * (temps_effort_sec + seance_data.get('temps_recup_sec', 0)) / 60) + 15
    # Limiter la durée
    duree_seance = min(duree_seance, VOLUME_MAX_PAR_SEANCE.get(discipline, 120))
    
    return {
        'discipline': discipline,
        'type': type_seance,
        'details': details,
        'duree': duree_seance,
        'difficulte': get_difficulte(type_seance.lower())
    }


def generer_semaine(
    date_semaine: datetime,
    date_objectif: datetime,
    profil: Dict,
    disponibilites: Dict,
    semaine_num: int,
    nb_semaines: int,
    seances_vma: List[Dict] = None,
    seances_vc: List[Dict] = None,
    semaines_anterieures: List[Dict] = None
) -> Dict:
    """
    Génère une semaine d'entraînement complète selon le cahier des charges.
    """
    if seances_vma is None:
        seances_vma = []
    if seances_vc is None:
        seances_vc = []
    if semaines_anterieures is None:
        semaines_anterieures = []
    
    # 1. Déterminer la phase
    phase = determiner_phase(semaine_num, nb_semaines)
    
    # 2. Récupérer les données
    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    niveau = profil.get('niveau_estime', 'Intermédiaire')
    objectif = profil.get('objectif_principal', '')
    
    # 3. Jours disponibles
    jours_cap = disponibilites.get('CAP', [])
    jours_velo = disponibilites.get('Velo', [])
    jours_natation = disponibilites.get('Natation', [])
    bi_quotidien = disponibilites.get('bi_quotidien', {})
    
    # 4. Calcul du nombre de séances
    nb_cap = len(jours_cap)
    nb_velo = len(jours_velo)
    nb_natation = len(jours_natation)
    
    # 5. Déterminer le nombre de séances intenses requises
    nb_intenses_requis = get_nb_intenses_requis(nb_cap)
    
    # 6. Déterminer le type de semaine
    volume_approx = (nb_cap * 45 + nb_velo * 90 + nb_natation * 45)
    seances_intenses_approx = min(nb_intenses_requis, nb_cap)
    
    type_semaine = determiner_type_semaine(
        semaine_num, nb_semaines, volume_approx, seances_intenses_approx,
        phase, semaines_anterieures
    )
    emoji_semaine = get_emoji_semaine(type_semaine)
    
    # 7. Numéro de semaine affiché (S-XX)
    num_affichage = get_volume_semaine_affichage(semaine_num, nb_semaines)
    
    # 8. Calculer les volumes cibles
    volumes = calculer_volume_hebdo(
        {'CAP': jours_cap, 'Velo': jours_velo, 'Natation': jours_natation},
        niveau, objectif, type_semaine, phase, semaine_num
    )
    
    # 9. Coefficients
    coeff_volume = get_volume_coeff(type_semaine, phase, semaine_num)
    coeff_intensite = get_intensite_coeff(type_semaine)
    
    # 10. Volume natation
    natation_km = get_natation_km(niveau)
    
    # 11. Construire les jours
    jours = []
    seances_intenses_placees = 0
    dernier_jour_intense = -10
    jour_renforcement = None
    a_vma = vma is not None and not math.isnan(vma) and vma > 0
    a_vc = vc is not None and not math.isnan(vc) and vc > 0
    a_les_deux = a_vma and a_vc
    
    # Choisir un jour pour le renforcement (éviter les jours intenses)
    jours_disponibles_renforcement = []
    for i, nom_jour in enumerate(JOURS_SEMAINE):
        if nom_jour in jours_cap or nom_jour in jours_velo or nom_jour in jours_natation:
            jours_disponibles_renforcement.append(i)
    
    # Si l'athlète a les deux VMA et VC, forcer l'alternance
    if a_les_deux and nb_cap >= 2:
        # VMA les semaines paires, VC les semaines impaires
        pass  # Déjà géré par choisir_seance_qualite
    
    for i, nom_jour in enumerate(JOURS_SEMAINE):
        date_str = generer_jour_date(date_semaine, i)
        
        # Si date passée → pas de séance
        if est_date_passee(date_str):
            jours.append({
                'jour': nom_jour,
                'date': date_str,
                'seances': [],
                'difficulte': 'repos',
                'emoji': '⬜'
            })
            continue
        
        est_objectif = date_str == date_objectif.strftime('%Y-%m-%d')
        jours_avant_objectif = (date_objectif - date_semaine - timedelta(days=i)).days
        est_affutage = 0 <= jours_avant_objectif <= 3
        
        seances = []
        
        # Vérifier les disponibilités
        cap_dispo = nom_jour in jours_cap
        velo_dispo = nom_jour in jours_velo
        natation_dispo = nom_jour in jours_natation
        
        # ---- OBJECTIF ----
        if est_objectif:
            # On arrête le plan après cette séance
            seances.append({
                'discipline': 'Course',
                'type': 'Objectif',
                'details': objectif or 'Compétition',
                'duree': 0,
                'difficulte': 'course'
            })
            jours.append({
                'jour': nom_jour,
                'date': date_str,
                'seances': seances,
                'difficulte': 'course',
                'emoji': '⭐'
            })
            # IMPORTANT: On arrête la génération ici, le plan s'arrête à l'objectif
            continue
        
        # ---- AFFÛTAGE ----
        if est_affutage or type_semaine == 'affutage':
            # Réduction de volume de 35%
            if cap_dispo:
                duree = int(volumes.get('CAP', 45) * 0.65)
                # En affûtage, uniquement endurance Z1 ou footing récup
                seances.append(generer_seance_endurance('CAP', duree, 'Z1', 'endurance_recuperative'))
            if velo_dispo:
                duree = max(80, int(volumes.get('Velo', 90) * 0.65))
                seances.append(generer_seance_endurance('Vélo', duree, 'Z1', 'recup'))
            if natation_dispo:
                duree = int(volumes.get('Natation', 45) * 0.65)
                seances.append(generer_seance_endurance('Natation', duree, 'Z1', 'recup'))
            
            if not seances:
                seances.append({
                    'discipline': 'Repos',
                    'type': 'Repos',
                    'details': 'Repos actif',
                    'duree': 0,
                    'difficulte': 'repos'
                })
            
            difficulte_journee = 'recuperation'
            for s in seances:
                if s.get('difficulte') in ['intense', 'seuil']:
                    difficulte_journee = s.get('difficulte')
                    break
            
            jours.append({
                'jour': nom_jour,
                'date': date_str,
                'seances': seances,
                'difficulte': difficulte_journee,
                'emoji': get_emoji_journee(difficulte_journee)
            })
            continue
        
        # ---- SÉANCE CAP ----
        if cap_dispo:
            # Règle: espacer les séances intenses d'au moins 36h
            peut_avoir_intense = (seances_intenses_placees < nb_intenses_requis) and (i - dernier_jour_intense) >= 2
            
            # Si l'athlète a les deux VMA/VC, forcer alternance
            if a_les_deux and seances_intenses_placees < nb_intenses_requis:
                # VMA les semaines paires, VC les semaines impaires
                type_force = 'VMA' if semaine_num % 2 == 0 else 'VC'
                seance_data = None
                if type_force == 'VMA' and seances_vma:
                    idx = (semaine_num + seances_intenses_placees) % len(seances_vma)
                    seance_data = seances_vma[idx]
                    type_seance = 'VMA'
                elif type_force == 'VC' and seances_vc:
                    idx = (semaine_num + seances_intenses_placees) % len(seances_vc)
                    seance_data = seances_vc[idx]
                    type_seance = 'VC'
                
                if seance_data:
                    seance = generer_seance_qualite(seance_data, 'CAP', type_seance)
                    seance['duree'] = int(seance['duree'] * coeff_intensite)
                    seances.append(seance)
                    seances_intenses_placees += 1
                    dernier_jour_intense = i
                    # Passer à la suite
                    cap_dispo = False
            
            if cap_dispo and peut_avoir_intense and seances_intenses_placees < nb_intenses_requis:
                seance_data, type_seance = choisir_seance_qualite(
                    seances_vma, seances_vc, semaine_num, vma, vc, nb_cap, seances_intenses_placees
                )
                if seance_data:
                    seance = generer_seance_qualite(seance_data, 'CAP', type_seance)
                    # Si c'est un test ou une séance intense, garder la durée calculée
                    if type_seance != 'Test 3\'/6\'/12\'':
                        seance['duree'] = int(seance['duree'] * coeff_intensite)
                    seances.append(seance)
                    seances_intenses_placees += 1
                    dernier_jour_intense = i
                else:
                    duree = int(volumes.get('CAP', 45) * coeff_volume)
                    seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale'))
            elif cap_dispo:
                # Séance d'endurance ou récupération
                if i == 5:  # Samedi: sortie longue
                    duree = int(volumes.get('CAP', 45) * 1.5 * coeff_volume)
                    seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'sortie_longue'))
                elif i in [0, 3]:  # Lundi ou Jeudi: endurance fondamentale
                    duree = int(volumes.get('CAP', 45) * coeff_volume)
                    seances.append(generer_seance_endurance('CAP', duree, 'Z2', 'endurance_fondamentale'))
                else:
                    duree = int(volumes.get('CAP', 45) * 0.7 * coeff_volume)
                    seances.append(generer_seance_endurance('CAP', duree, 'Z1', 'endurance_recuperative'))
        
        # ---- SÉANCE VÉLO ----
        if velo_dispo:
            duree = max(80, int(volumes.get('Velo', 90) * coeff_volume))
            # Sorties longues le samedi
            if i == 5:
                duree = int(duree * 1.5)
                seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'sortie_longue'))
            # Séances de seuil le mercredi ou vendredi
            elif i in [2, 4]:
                duree = int(duree * coeff_intensite)
                seances.append({
                    'discipline': 'Vélo',
                    'type': 'Seuil Z4',
                    'details': f'Seuil Z4 ({duree} min)',
                    'duree': duree,
                    'difficulte': 'seuil'
                })
            else:
                seances.append(generer_seance_endurance('Vélo', duree, 'Z2', 'endurance'))
        
        # ---- SÉANCE NATATION ----
        if natation_dispo:
            duree = int(volumes.get('Natation', 45) * coeff_volume)
            
            if i in [1, 4]:  # Mardi ou Vendredi: technique + seuil
                duree = int(duree * coeff_intensite)
                seances.append({
                    'discipline': 'Natation',
                    'type': 'Technique + Seuil',
                    'details': f'Technique + seuil Z4 ({duree} min, {natation_km}km)',
                    'duree': duree,
                    'difficulte': 'seuil'
                })
            elif i == 2:  # Mercredi: endurance
                seances.append(generer_seance_endurance('Natation', duree, 'Z2', 'endurance'))
            else:
                seances.append(generer_seance_endurance('Natation', int(duree * 0.8), 'Z1', 'recup'))
        
        # ---- RENFORCEMENT ----
        # Une séance par semaine, pas le même jour qu'une séance intense
        est_jour_intense = any(s.get('difficulte') in ['intense', 'seuil'] for s in seances)
        # Vérifier aussi les jours déjà passés
        if not est_jour_intense and i in jours_disponibles_renforcement:
            if jour_renforcement is None or i == 2:  # Mercredi par défaut
                # Vérifier qu'on n'a pas déjà une séance intense ce jour-là
                if not any(s.get('difficulte') in ['intense', 'seuil'] for s in seances):
                    seances.append(generer_seance_renforcement('Renforcement', 30))
                    jour_renforcement = i
        
        # ---- REPOS ----
        if not seances:
            seances.append({
                'discipline': 'Repos',
                'type': 'Repos',
                'details': 'Repos',
                'duree': 0,
                'difficulte': 'repos'
            })
        
        # Déterminer la difficulté de la journée
        difficulte_journee = 'endurance'
        for s in seances:
            if s.get('difficulte') == 'intense':
                difficulte_journee = 'intense'
                break
            elif s.get('difficulte') == 'seuil' and difficulte_journee != 'intense':
                difficulte_journee = 'seuil'
        
        jours.append({
            'jour': nom_jour,
            'date': date_str,
            'seances': seances,
            'difficulte': difficulte_journee,
            'emoji': get_emoji_journee(difficulte_journee)
        })
    
    # 12. Calcul du volume total
    volume_total = sum(
        s.get('duree', 0)
        for jour in jours
        for s in jour['seances']
        if s.get('discipline') not in ['Repos', 'Course']
    )
    
    # 13. Nombre de séances intenses
    seances_intenses = sum(
        1 for jour in jours
        for s in jour['seances']
        if s.get('difficulte') in ['intense', 'seuil']
    )
    
    return {
        'semaine_num': semaine_num,
        'semaine_type': type_semaine,
        'num_affichage': num_affichage,
        'emoji': emoji_semaine,
        'date_debut': date_semaine.strftime('%Y-%m-%d'),
        'date_fin': (date_semaine + timedelta(days=6)).strftime('%Y-%m-%d'),
        'phase': phase,
        'volume_total': volume_total,
        'seances_intenses': seances_intenses,
        'nb_seances': {
            'CAP': nb_cap,
            'Velo': nb_velo,
            'Natation': nb_natation
        },
        'volumes_cibles': volumes,
        'jours': jours
    }


def generer_plan_complet(
    debut: datetime,
    date_objectif: datetime,
    profil: Dict,
    disponibilites: Dict,
    seances_vma: List[Dict] = None,
    seances_vc: List[Dict] = None
) -> List[Dict]:
    """
    Génère un plan complet sur plusieurs semaines.
    La dernière semaine est S-00 (semaine de l'objectif).
    Le plan s'arrête exactement le jour de l'objectif.
    """
    if seances_vma is None:
        seances_vma = []
    if seances_vc is None:
        seances_vc = []
    
    # Ajuster le début au lundi
    debut_lundi = debut - timedelta(days=debut.weekday())
    
    # Nombre de semaines
    delta = date_objectif - debut_lundi
    nb_semaines = max(1, delta.days // 7 + 1)
    
    semaines = []
    for s in range(nb_semaines):
        date_semaine = debut_lundi + timedelta(days=s * 7)
        semaine = generer_semaine(
            date_semaine=date_semaine,
            date_objectif=date_objectif,
            profil=profil,
            disponibilites=disponibilites,
            semaine_num=s + 1,
            nb_semaines=nb_semaines,
            seances_vma=seances_vma,
            seances_vc=seances_vc,
            semaines_anterieures=semaines
        )
        semaines.append(semaine)
    
    return semaines