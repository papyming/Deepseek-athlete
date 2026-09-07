# ============================================================
# FICHIER: src/planificateur/generateur/semaine.py
# RÔLE: Construction d'une semaine complète
#       CORRIGÉ: Sélection des jours prioritaires
# ============================================================

import math
import re
from datetime import datetime, timedelta
from typing import Dict, List

from ..constants_plan import JOURS_SEMAINE, get_emoji_semaine
from ..periodisation import determiner_phase, determiner_type_semaine, get_volume_coeff, get_intensite_coeff
from ..volume import calculer_volume_hebdo, get_nb_intenses_requis, get_natation_km
from .dates import generer_jour_date, jours_disponibles_renforcement, get_volume_semaine_affichage
from .journee import construire_journee
from .seances import generer_seance_renforcement


def construire_semaine(
    date_semaine: datetime,
    date_objectif: datetime,
    profil: Dict,
    disponibilites: Dict,
    semaine_num: int,
    nb_semaines: int,
    seances_vma: List[Dict] = None,
    seances_vc: List[Dict] = None,
    semaines_anterieures: List[Dict] = None,
    courses_preparatoires: List[Dict] = None
) -> Dict:
    if seances_vma is None:
        seances_vma = []
    if seances_vc is None:
        seances_vc = []
    if semaines_anterieures is None:
        semaines_anterieures = []
    if courses_preparatoires is None:
        courses_preparatoires = []
    
    phase = determiner_phase(semaine_num, nb_semaines)
    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    niveau = profil.get('niveau_estime', 'Intermédiaire')
    objectif = profil.get('objectif_principal', '')
    
    jours_cap = disponibilites.get('CAP', [])
    jours_velo = disponibilites.get('Velo', [])
    jours_natation = disponibilites.get('Natation', [])
    
    nb_cap = len(jours_cap)
    nb_velo = len(jours_velo)
    nb_natation = len(jours_natation)
    
    # CORRIGÉ: Sélection des jours prioritaires
    ordre_priorite = ['Mardi', 'Jeudi', 'Samedi', 'Lundi', 'Mercredi', 'Vendredi', 'Dimanche']
    
    # CAP: max 4 jours par semaine
    if nb_cap > 4:
        jours_cap_tries = sorted(jours_cap, key=lambda x: ordre_priorite.index(x) if x in ordre_priorite else 99)
        jours_cap = jours_cap_tries[:4]
        nb_cap = len(jours_cap)
    
    # Vélo: max 3 jours par semaine
    if nb_velo > 3:
        jours_velo_tries = sorted(jours_velo, key=lambda x: ordre_priorite.index(x) if x in ordre_priorite else 99)
        jours_velo = jours_velo_tries[:3]
        nb_velo = len(jours_velo)
    
    # Natation: max 3 jours par semaine
    if nb_natation > 3:
        jours_natation_tries = sorted(jours_natation, key=lambda x: ordre_priorite.index(x) if x in ordre_priorite else 99)
        jours_natation = jours_natation_tries[:3]
        nb_natation = len(jours_natation)
    
    volume_approx = nb_cap * 45 + nb_velo * 90 + nb_natation * 45
    
    type_semaine = determiner_type_semaine(
        semaine_num, nb_semaines, volume_approx,
        min(get_nb_intenses_requis(nb_cap, semaine_num, 'normale'), nb_cap),
        phase, semaines_anterieures
    )
    
    if semaines_anterieures:
        dernier_type = semaines_anterieures[-1].get('semaine_type', 'normale')
        dernier_volume = semaines_anterieures[-1].get('volume_total', 0)
        
        if dernier_type == type_semaine and type_semaine not in ['affutage', 'recuperation']:
            alternance = {
                'normale': 'chargee',
                'chargee': 'dure' if phase in ['preparation_specifique', 'competition'] else 'normale',
                'dure': 'chargee'
            }
            type_semaine = alternance.get(type_semaine, 'normale')
    
    emoji_semaine = get_emoji_semaine(type_semaine)
    nb_intenses_requis = get_nb_intenses_requis(nb_cap, semaine_num, type_semaine)
    num_affichage = get_volume_semaine_affichage(semaine_num, nb_semaines)
    
    volumes = calculer_volume_hebdo(
        {'CAP': jours_cap, 'Velo': jours_velo, 'Natation': jours_natation},
        niveau, objectif, type_semaine, phase, semaine_num
    )
    
    coeff_volume = get_volume_coeff(type_semaine, phase, semaine_num)
    coeff_intensite = get_intensite_coeff(type_semaine)
    natation_km = get_natation_km(niveau)
    
    seances_intenses_placees = 0
    dernier_jour_intense = -10
    renforcement_place = False
    
    jours_dispo_renforcement = jours_disponibles_renforcement(jours_cap, jours_velo, jours_natation)
    
    jours = []
    a_vma = vma is not None and not math.isnan(vma) and vma > 0
    a_vc = vc is not None and not math.isnan(vc) and vc > 0
    a_les_deux = a_vma and a_vc
    
    if nb_cap <= 2 and semaine_num % 3 == 0:
        nb_intenses_requis = max(nb_intenses_requis, 1)
    
    # Courses préparatoires
    course_semaine = None
    fin_semaine = date_semaine + timedelta(days=6)
    
    for course in courses_preparatoires:
        if isinstance(course, dict) and 'date' in course:
            date_course = course['date']
            if isinstance(date_course, datetime):
                if date_semaine <= date_course <= fin_semaine:
                    course_semaine = course
                    break
        elif isinstance(course, str):
            match = re.search(r'(\d{2})/(\d{2})', course)
            if match:
                jour = int(match.group(1))
                mois = int(match.group(2))
                annee = date_objectif.year
                if mois > date_objectif.month:
                    annee = date_objectif.year - 1
                try:
                    date_course = datetime(annee, mois, jour)
                    if date_semaine <= date_course <= fin_semaine:
                        course_semaine = {'date': date_course, 'nom': course}
                        break
                except ValueError:
                    pass
    
    for i, nom_jour in enumerate(JOURS_SEMAINE):
        date_str = generer_jour_date(date_semaine, i)
        date_courante = datetime.strptime(date_str, '%Y-%m-%d')
        if date_courante > date_objectif:
            break
        
        if course_semaine and date_str == course_semaine['date'].strftime('%Y-%m-%d'):
            jour_course = {
                'jour': nom_jour,
                'date': date_str,
                'seances': [{
                    'discipline': 'Course',
                    'type': 'Compétition intermédiaire',
                    'details': course_semaine['nom'],
                    'duree': 0,
                    'difficulte': 'course'
                }],
                'difficulte': 'course',
                'emoji': '⭐'
            }
            jours.append(jour_course)
            continue
        
        jour = construire_journee(
            nom_jour, date_str, date_objectif, type_semaine,
            jours_cap, jours_velo, jours_natation,
            volumes, coeff_volume, coeff_intensite, natation_km,
            nb_intenses_requis, seances_intenses_placees, dernier_jour_intense, renforcement_place,
            a_vma, a_vc, a_les_deux,
            seances_vma, seances_vc,
            semaine_num, nb_cap, objectif, vma, vc,
            jours_dispo_renforcement, date_semaine, i,
            nb_semaines
        )
        
        for s in jour['seances']:
            if s.get('difficulte') in ['intense', 'seuil']:
                seances_intenses_placees += 1
                dernier_jour_intense = i
            if s.get('discipline') == 'Renforcement':
                renforcement_place = True
        
        jours.append(jour)
    
    if not renforcement_place and type_semaine not in ['affutage', 'recuperation']:
        for jour in jours:
            if jour.get('difficulte') in ['endurance', 'recuperation']:
                jour['seances'].append(generer_seance_renforcement('Renforcement', 30))
                renforcement_place = True
                break
    
    volume_total = sum(s.get('duree', 0) for jour in jours for s in jour['seances'] if s.get('discipline') not in ['Repos', 'Course'])
    seances_intenses = sum(1 for jour in jours for s in jour['seances'] if s.get('difficulte') in ['intense', 'seuil'])
    
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
        'nb_seances': {'CAP': nb_cap, 'Velo': nb_velo, 'Natation': nb_natation},
        'volumes_cibles': volumes,
        'jours': jours
    }


def generer_plan_complet(
    debut: datetime,
    date_objectif: datetime,
    profil: Dict,
    disponibilites: Dict,
    seances_vma: List[Dict] = None,
    seances_vc: List[Dict] = None,
    courses_preparatoires: List[Dict] = None
) -> List[Dict]:
    if seances_vma is None:
        seances_vma = []
    if seances_vc is None:
        seances_vc = []
    if courses_preparatoires is None:
        courses_preparatoires = []
    
    debut_lundi = debut - timedelta(days=debut.weekday())
    nb_semaines = (date_objectif - debut_lundi).days // 7 + 1
    nb_semaines = max(1, nb_semaines)
    
    semaines = []
    for s in range(nb_semaines):
        date_semaine = debut_lundi + timedelta(days=s * 7)
        if date_semaine > date_objectif:
            break
        semaine = construire_semaine(
            date_semaine, date_objectif, profil, disponibilites,
            s + 1, nb_semaines, seances_vma, seances_vc, semaines,
            courses_preparatoires
        )
        semaines.append(semaine)
    
    return semaines