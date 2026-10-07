# ============================================================
# FICHIER: src/planificateur/generateur/semaine.py
# RÔLE: Construction d'une semaine complète
#       CORRIGÉ: Passage du sport principal à calculer_volume_hebdo
# ============================================================

import math
import re
from datetime import datetime, timedelta
from typing import Dict, List

from ..constants_plan import JOURS_SEMAINE, get_emoji_semaine, get_sport_discipline_priority_order, get_sport_priority_map, VELO_DUREE_MIN, VELO_DUREE_MAX_TECHNIQUE
from ..periodisation import determiner_phase, determiner_type_semaine, get_volume_coeff, get_intensite_coeff
from ..volume import (
    calculer_volume_hebdo,
    get_nb_intenses_requis,
    get_natation_km,
    get_duree_longue_cible,
    repartir_volume_velo,
)
from .dates import generer_jour_date, jours_disponibles_renforcement, get_volume_semaine_affichage
from .journee import construire_journee, _SPORT_DISCIPLINES, _MAX_SPORT_PAR_STATUT
from .seances import generer_seance_renforcement


def _extraire_date_course(texte: str, annee_defaut: int) -> datetime:
    """
    Extrait une date d'une chaîne de type "4 Octobre 26" ou "15/09" ou "15 septembre"
    """
    texte = texte.strip()
    
    mois_fr = {
        'janvier': 1, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
        'juillet': 7, 'aout': 8, 'août': 8, 'septembre': 9, 'octobre': 10,
        'novembre': 11, 'decembre': 12, 'décembre': 12
    }
    
    # Format: "4 Octobre 26"
    match = re.search(r'(\d{1,2})\s+([A-Za-zàâéèêëïîôöùûç]+)\s+(\d{2,4})', texte, re.IGNORECASE)
    if match:
        jour = int(match.group(1))
        mois_str = match.group(2).lower()
        mois = mois_fr.get(mois_str)
        annee = int(match.group(3))
        if annee < 100:
            annee += 2000 if annee >= 24 else 2000
        if mois and 1 <= mois <= 12 and 1 <= jour <= 31:
            try:
                return datetime(annee, mois, jour)
            except ValueError:
                pass
    
    # Format: "4 octobre 2026"
    match = re.search(r'(\d{1,2})\s+([A-Za-zàâéèêëïîôöùûç]+)\s+(\d{4})', texte, re.IGNORECASE)
    if match:
        jour = int(match.group(1))
        mois_str = match.group(2).lower()
        mois = mois_fr.get(mois_str)
        annee = int(match.group(3))
        if mois and 1 <= mois <= 12 and 1 <= jour <= 31:
            try:
                return datetime(annee, mois, jour)
            except ValueError:
                pass
    
    # Format: "15/09"
    match = re.search(r'(\d{1,2})/(\d{1,2})', texte)
    if match:
        jour = int(match.group(1))
        mois = int(match.group(2))
        if 1 <= mois <= 12 and 1 <= jour <= 31:
            try:
                return datetime(annee_defaut, mois, jour)
            except ValueError:
                pass
    
    # Format: "15 septembre"
    match = re.search(r'(\d{1,2})\s+([A-Za-zàâéèêëïîôöùûç]+)', texte, re.IGNORECASE)
    if match:
        jour = int(match.group(1))
        mois_str = match.group(2).lower()
        mois = mois_fr.get(mois_str)
        if mois and 1 <= mois <= 12 and 1 <= jour <= 31:
            try:
                return datetime(annee_defaut, mois, jour)
            except ValueError:
                pass
    
    return None


_MOIS_FR = {
    'janvier': 1, 'fevrier': 2, 'février': 2, 'mars': 3, 'avril': 4, 'mai': 5,
    'juin': 6, 'juillet': 7, 'aout': 8, 'août': 8, 'septembre': 9, 'octobre': 10,
    'novembre': 11, 'decembre': 12, 'décembre': 12,
}


def _dates_dans_texte(texte: str, annee_defaut: int) -> List[tuple]:
    """Retourne les dates (debut, fin, datetime) trouvées dans un texte libre."""
    trouvees = []
    # Format JJ/MM ou JJ/MM/AAAA
    for match in re.finditer(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', texte):
        jour, mois = int(match.group(1)), int(match.group(2))
        annee = int(match.group(3)) if match.group(3) else annee_defaut
        if annee < 100:
            annee += 2000
        if 1 <= mois <= 12 and 1 <= jour <= 31:
            try:
                trouvees.append((match.start(), match.end(), datetime(annee, mois, jour)))
            except ValueError:
                pass
    # Format JJ mois ou JJ mois AAAA
    for match in re.finditer(r'(\d{1,2})\s+([A-Za-zÀ-ÿ]+)(?:\s+(\d{2,4}))?', texte, re.IGNORECASE):
        mois = _MOIS_FR.get(match.group(2).lower())
        if mois is None:
            continue
        jour = int(match.group(1))
        annee = int(match.group(3)) if match.group(3) else annee_defaut
        if annee < 100:
            annee += 2000
        if 1 <= jour <= 31:
            try:
                trouvees.append((match.start(), match.end(), datetime(annee, mois, jour)))
            except ValueError:
                pass
    trouvees.sort(key=lambda item: item[0])
    return trouvees


def _discipline_course(nom: str) -> str:
    """Déduit la discipline d'une course depuis son libellé."""
    texte = str(nom or '').lower()
    if any(mot in texte for mot in ('triathlon', 'duathlon', 'aquathlon', 'swimrun')):
        return 'CAP'
    if any(mot in texte for mot in ('natation', 'swim', 'eau libre', 'aquatique')):
        return 'Natation'
    if any(mot in texte for mot in (
        'cyclisme', 'vélo', 'velo', 'bike', 'contre-la-montre', 'clm', 'piste'
    )):
        return 'Vélo'
    return 'CAP'


def extraire_courses(courses_preparatoires: List, annee_defaut: int) -> List[Dict]:
    """Normalise les courses préparatoires en {'date', 'nom', 'discipline'}.

    Gère : dict {'date', 'nom'}, chaîne avec une ou plusieurs dates
    (JJ/MM, JJ/MM/AAAA, mois en toutes lettres).
    """
    resultat = []
    for course in courses_preparatoires or []:
        if isinstance(course, dict) and 'date' in course:
            date_course = course['date']
            if isinstance(date_course, datetime):
                nom = str(course.get('nom', '') or '')
                resultat.append({
                    'date': date_course,
                    'nom': nom,
                    'discipline': course.get('discipline') or _discipline_course(nom),
                })
            continue
        if not isinstance(course, str):
            continue
        texte = course.strip()
        trouves = _dates_dans_texte(texte, annee_defaut)
        if not trouves:
            continue
        for index, (debut, fin, date_course) in enumerate(trouves):
            debut_segment = trouves[index - 1][1] if index > 0 else 0
            nom = texte[debut_segment:debut].strip(' ,;:-.')
            nom = re.sub(r'(?i)\s+(le|la|les|du|de|au)$', '', nom).strip()
            if not nom:
                nom = texte
            resultat.append({
                'date': date_course,
                'nom': nom,
                'discipline': _discipline_course(nom or texte),
            })
    return resultat


def _determiner_nb_jours_utilises(nb_jours_disponibles: int, niveau: str, phase: str) -> int:
    """
    Détermine le nombre de jours à utiliser par discipline.
    """
    base_niveau = {
        'Débutant': 3,
        'Intermédiaire': 4,
        'Avancé': 5
    }.get(niveau, 4)
    
    if phase == 'preparation_generale':
        coeff = 0.9
    elif phase == 'preparation_specifique':
        coeff = 1.0
    elif phase == 'competition':
        coeff = 0.85
    else:
        coeff = 0.6
    
    nb_base = int(base_niveau * coeff)
    nb_utilises = min(nb_jours_disponibles, nb_base)
    
    return max(2, nb_utilises)


def _selectionner_jours_biquotidien(disponibilites: Dict, semaine_num: int = 1) -> List[str]:
    """Sélectionne une fenêtre variable de jours possibles pour la semaine."""
    nombre = disponibilites.get('bi_quotidien_nb')
    if nombre is None:
        return []
    if not isinstance(nombre, int) or isinstance(nombre, bool) or not 1 <= nombre <= 7:
        return []

    jours_disponibles = set(
        disponibilites.get('CAP', [])
        + disponibilites.get('Velo', [])
        + disponibilites.get('Natation', [])
    )
    if disponibilites.get('bi_quotidien_mode') == 'tri_quadri':
        jours_declares = disponibilites.get('bi_quotidien_tri_quadri', {})
    else:
        jours_declares = disponibilites.get('bi_quotidien', {})
    ordre_semaine = {jour: index for index, jour in enumerate(JOURS_SEMAINE)}
    jours = set()
    for discipline in ['CAP', 'Velo', 'Natation']:
        for jour in jours_declares.get(discipline, []):
            if jour in jours_disponibles and jour in ordre_semaine:
                jours.add(jour)

    jours_ordonnes = sorted(jours, key=ordre_semaine.get)
    if len(jours_ordonnes) <= nombre:
        return jours_ordonnes

    debut = (semaine_num - 1) % len(jours_ordonnes)
    return [
        jours_ordonnes[(debut + offset) % len(jours_ordonnes)]
        for offset in range(nombre)
    ]


def _jours_biquotidien_source(disponibilites: Dict) -> List[str]:
    jours_par_discipline = disponibilites.get(
        'bi_quotidien_source', disponibilites.get('bi_quotidien', {})
    )
    return sorted({
        jour
        for jours in jours_par_discipline.values()
        for jour in jours
        if jour in JOURS_SEMAINE
    }, key=JOURS_SEMAINE.index)


def _disciplines_objectif(competition_objectif: str, format_competition: str) -> set:
    """Déduit les disciplines de l'objectif sportif depuis le format et le contexte de compétition."""
    for texte in (str(format_competition or ''), str(competition_objectif or '')):
        texte = texte.lower()
        if not texte:
            continue
        if any(mot in texte for mot in ['triathlon', 'ironman', 'olympique']):
            return {'CAP', 'Velo', 'Natation'}
        if any(mot in texte for mot in ['swimrun', 'aquathlon']):
            return {'CAP', 'Natation'}
        if 'duathlon' in texte:
            return {'CAP', 'Velo'}
        if any(mot in texte for mot in ['marathon', 'semi', '10km', '10k', 'trail', 'ultra', 'course', 'cap']):
            return {'CAP'}
        if any(mot in texte for mot in ['cyclisme', 'vélo', 'velo', 'contre-la-montre', 'bike', 'clm']):
            return {'Velo'}
        if any(mot in texte for mot in ['natation', 'open water', 'eau libre', 'swim']):
            return {'Natation'}
    return set()


_PREFERENCE_JOURS = {
    'CAP': ['Mardi', 'Jeudi', 'Samedi', 'Lundi', 'Mercredi', 'Vendredi', 'Dimanche'],
    'Velo': ['Samedi', 'Dimanche', 'Mercredi', 'Vendredi', 'Mardi', 'Jeudi', 'Lundi'],
    'Natation': ['Mardi', 'Vendredi', 'Mercredi', 'Lundi', 'Jeudi', 'Samedi', 'Dimanche'],
}


def _trier_jours_preferes(discipline: str, jours: List[str]) -> List[str]:
    """Trie les jours candidats selon la preference de placement (intensite en semaine, long le week-end)."""
    ordre = _PREFERENCE_JOURS.get(discipline, JOURS_SEMAINE)
    return sorted(jours, key=lambda x: ordre.index(x) if x in ordre else 99)


def _jour_longue_prioritaire(
    discipline: str, jours_disponibles: List[str], jours_exclus: List[str] = None
) -> str:
    """Choisit le jour de la séance longue d'une discipline.

    Règle CDC : le dimanche, lorsqu'il est disponible et compatible avec les
    contraintes, est le jour prioritaire de la séance longue principale.
    Repli sur le samedi, puis sur le meilleur jour disponible. Ne crée jamais
    de disponibilité : ne retourne qu'un jour de ``jours_disponibles`` non
    exclu (compétition, etc.). Fonction pure, indépendante du calcul de volume.
    """
    exclus = set(jours_exclus or [])
    candidats = [jour for jour in jours_disponibles if jour not in exclus]
    if not candidats:
        return None
    for jour_prioritaire in ('Dimanche', 'Samedi'):
        if jour_prioritaire in candidats:
            return jour_prioritaire
    ordre = _PREFERENCE_JOURS.get(discipline, JOURS_SEMAINE)
    return sorted(candidats, key=lambda x: ordre.index(x) if x in ordre else 99)[0]


_JOURS_WEEKEND = ['Samedi', 'Dimanche']

# Intensité : priorité aux jours de semaine (lundi -> vendredi).
_PREFERENCES_INTENSITE = {
    'CAP': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi'],
    'Velo': ['Mercredi', 'Vendredi', 'Lundi', 'Mardi', 'Jeudi'],
    'Natation': ['Mardi', 'Vendredi', 'Lundi', 'Mercredi', 'Jeudi'],
}

# Créneaux historiques d'intensité pour Vélo et Natation.
_CRENEAUX_INTENSITE_FIXES = {
    'Velo': {'Mercredi', 'Vendredi'},
    'Natation': {'Mardi', 'Vendredi'},
}

# Longue : priorité au dimanche (jour prioritaire CDC), puis au samedi.
_PREFERENCES_LONGUE = {
    'CAP': ['Dimanche', 'Samedi'],
    'Velo': ['Dimanche', 'Samedi'],
}

_ROLES = ('intensite', 'longue', 'endurance')


def _selectionner_jours_avec_longue(
    discipline: str, jours_disponibles: List[str], nb_utilises: int
) -> List[str]:
    """Tronque les jours à nb_utilises tout en préservant un créneau week-end.

    La sortie longue ne doit jamais perdre un samedi/dimanche réellement
    disponible à cause de la limitation du nombre de jours : le jour week-end
    préféré est conservé en remplacement du jour le moins prioritaire, à
    nombre de jours constant.
    """
    tries = _trier_jours_preferes(discipline, jours_disponibles)
    if nb_utilises <= 0 or len(tries) <= nb_utilises:
        return tries[:nb_utilises] if nb_utilises > 0 else []

    selection = list(tries[:nb_utilises])

    preferences_longue = _PREFERENCES_LONGUE.get(discipline, [])
    if not preferences_longue or nb_utilises < 2:
        return selection

    creneaux_weekend = [j for j in preferences_longue if j in jours_disponibles]
    if not creneaux_weekend:
        return selection
    if any(j in creneaux_weekend for j in selection):
        return selection

    for jour in reversed(selection):
        if jour not in creneaux_weekend:
            selection.remove(jour)
            selection.append(creneaux_weekend[0])
            break
    return _trier_jours_preferes(discipline, selection)


def _date_du_jour(date_semaine: datetime, nom_jour: str) -> datetime:
    """Retourne la date réelle d'un jour de semaine dans la fenêtre courante."""
    decalage = (JOURS_SEMAINE.index(nom_jour) - date_semaine.weekday()) % 7
    return date_semaine + timedelta(days=decalage)


def _choisir_creneaux_intenses(
    candidats: List[str],
    date_semaine: datetime,
    dates_reference: List[datetime],
    quota: int
) -> List[str]:
    """Sélectionne des jours d'intensité en respectant l'espacement de 48 h."""
    selection = []
    reference = list(dates_reference)
    for nom_jour in candidats:
        if len(selection) >= quota:
            break
        date_jour = _date_du_jour(date_semaine, nom_jour)
        if all(abs((date_jour - date_ref).days) >= 2 for date_ref in reference):
            reference.append(date_jour)
            selection.append(nom_jour)
    return selection


def _roles_pour_discipline(
    discipline: str,
    jours: List[str],
    date_semaine: datetime,
    nb_intenses: int,
    derniere_intense: datetime = None,
    dates_imposees: List[datetime] = None,
    jours_a_eviter: List[str] = None
):
    """Décide le rôle (intensite/longue/endurance) de chaque jour d'une discipline.

    ``dates_imposees`` contient les dates de compétitions préparatoires: elles
    comptent comme séances d'intensité et doivent donc être espacées d'au moins
    48 h des séances intenses normales.

    ``jours_a_eviter`` (jours également vélo) n'est utilisé que pour la CAP :
    une séance de qualité y est placée en dernier recours, car la règle CDC
    CAP ≤ 50 % du vélo rend le cumul CAP qualité + vélo contraint. Les jours
    sans vélo restent prioritaires ; l'évitement n'exclut jamais un jour.
    """
    roles = {jour: 'endurance' for jour in jours}
    if not jours:
        return roles, []

    alertes = []
    eviter = set(jours_a_eviter or [])
    dates_reference = list(dates_imposees or [])
    if derniere_intense is not None:
        dates_reference.append(derniere_intense)

    if discipline == 'CAP':
        # Tri stable : les jours sans vélo passent en tête, l'ordre de
        # préférence CAP est conservé à l'intérieur de chaque groupe.
        candidats_semaine = sorted(
            [jour for jour in _PREFERENCES_INTENSITE['CAP'] if jour in jours],
            key=lambda jour: jour in eviter
        )
        selection = _choisir_creneaux_intenses(
            candidats_semaine, date_semaine, dates_reference, nb_intenses
        )
        if len(selection) < nb_intenses:
            candidats_weekend = sorted(
                [
                    jour for jour in _PREFERENCES_LONGUE['CAP']
                    if jour in jours and jour not in selection
                ],
                key=lambda jour: jour in eviter
            )
            reference = dates_reference + [
                _date_du_jour(date_semaine, jour) for jour in selection
            ]
            selection_weekend = _choisir_creneaux_intenses(
                candidats_weekend, date_semaine,
                reference, nb_intenses - len(selection)
            )
            if selection_weekend:
                alertes.append(
                    "Placement de l'intensité : aucun créneau de semaine "
                    "disponible, repli sur le week-end ("
                    + ', '.join(selection_weekend) + ")."
                )
            selection += selection_weekend
        for jour in selection:
            roles[jour] = 'intensite'
    else:
        creneaux_fixes = _CRENEAUX_INTENSITE_FIXES.get(discipline, set())
        imposees = dates_imposees or []
        for jour in jours:
            if jour not in creneaux_fixes:
                continue
            date_jour = _date_du_jour(date_semaine, jour)
            if any(abs((date_jour - date_ref).days) < 2 for date_ref in imposees):
                continue
            roles[jour] = 'intensite'

    if discipline in ('CAP', 'Velo'):
        restants = [jour for jour in jours if roles[jour] != 'intensite']
        # Une compétition n'est jamais déplacée : le jour de course est exclu
        # des candidats à la séance longue (repli sur un autre jour dispo).
        jours_competition = []
        if dates_imposees:
            dates_set = set(dates_imposees)
            jours_competition = [
                jour for jour in restants
                if _date_du_jour(date_semaine, jour) in dates_set
            ]
        jour_longue = _jour_longue_prioritaire(
            discipline, restants, jours_competition
        )
        if jour_longue is not None:
            roles[jour_longue] = 'longue'
            if jour_longue not in ('Dimanche', 'Samedi'):
                alertes.append(
                    f"Placement de la séance longue {discipline} : aucun créneau "
                    "week-end disponible, repli sur un jour disponible."
                )

    return roles, alertes


def _construire_roles_semaine(
    jours_cap: List[str],
    jours_velo: List[str],
    jours_natation: List[str],
    nb_intenses_cap: int,
    date_semaine: datetime,
    derniers_intenses: Dict,
    dates_courses: Dict = None
):
    """Construit le rôle de placement par jour et par discipline pour la semaine."""
    dates_courses = dates_courses or {}
    roles_par_jour = {jour: {} for jour in JOURS_SEMAINE}
    alertes = []

    roles_cap, alertes_cap = _roles_pour_discipline(
        'CAP', jours_cap, date_semaine, nb_intenses_cap,
        derniers_intenses.get('CAP'),
        dates_courses.get('CAP'),
        jours_a_eviter=jours_velo
    )
    for jour, role in roles_cap.items():
        roles_par_jour[jour]['CAP'] = role

    for discipline, jours in (('Velo', jours_velo), ('Natation', jours_natation)):
        roles, alertes_discipline = _roles_pour_discipline(
            discipline, jours, date_semaine, 0,
            derniers_intenses.get(discipline),
            dates_courses.get(discipline)
        )
        for jour, role in roles.items():
            roles_par_jour[jour][discipline] = role
        alertes.extend(alertes_discipline)

    return roles_par_jour, alertes_cap + alertes


_MESSAGES_CONTRAINTE = {
    'biquotidien': "Contrainte de planification : les contraintes imposent 2 séances CAP/Vélo/Natation ce jour. L'athlète choisit s'il fait une séance ou les deux.",
    'tri': "Contrainte de planification : les contraintes imposent 3 séances CAP/Vélo/Natation ce jour. L'athlète choisit s'il fait une, deux ou trois séances.",
    'quadri': "Contrainte de planification : les contraintes imposent 4 séances CAP/Vélo/Natation ce jour. L'athlète choisit le nombre de séances à réaliser.",
}


def _detecter_contrainte(jour: Dict, statut_jour: str) -> Dict:
    """Détecte un dépassement de capacité journalière sans retirer aucune séance."""
    capacite = _MAX_SPORT_PAR_STATUT.get(statut_jour, 1)
    disciplines = [
        seance.get('discipline')
        for seance in jour.get('seances', [])
        if seance.get('discipline') in _SPORT_DISCIPLINES
    ]
    nb_seances_sport = len(disciplines)
    depassement = max(0, nb_seances_sport - capacite)

    if depassement == 0:
        return {
            'active': False,
            'statut_jour': statut_jour,
            'capacite_normale': capacite,
            'nb_seances_sport': nb_seances_sport,
            'depassement': 0,
            'niveau_depasse': None,
            'disciplines': disciplines,
            'motif': '',
            'message': ''
        }

    if capacite == 1:
        niveau_depasse = 'biquotidien'
    elif capacite == 2:
        niveau_depasse = 'tri'
    else:
        niveau_depasse = 'quadri'

    motif = (
        f"Contrainte de disponibilité : le {jour.get('jour', '')} doit accueillir "
        f"{nb_seances_sport} séances ({', '.join(disciplines)}) alors que sa capacité normale "
        f"est de {capacite}."
    )

    return {
        'active': True,
        'statut_jour': statut_jour,
        'capacite_normale': capacite,
        'nb_seances_sport': nb_seances_sport,
        'depassement': depassement,
        'niveau_depasse': niveau_depasse,
        'disciplines': disciplines,
        'motif': motif,
        'message': _MESSAGES_CONTRAINTE[niveau_depasse]
    }


_RATIO_CAP_VELO = 0.5
_DUREE_MIN_CAP = 20
MESSAGE_CAP_VELO = (
    "La durée de la CAP dépasse 50 % de la durée du vélo prévu le même jour."
)


def _seance_cap_reductible(seance: Dict) -> bool:
    """Une séance CAP n'est réductible sans casser sa structure que si elle
    n'est pas une séance de qualité (VMA/VC/Test/Fartlek/Seuil)."""
    if seance.get('cle') is True:
        return False
    if seance.get('difficulte') in ('intense', 'seuil'):
        return False
    type_lower = str(seance.get('type', '')).lower()
    return not any(
        mot in type_lower for mot in ('vma', 'vc', 'test', 'fartlek', 'seuil')
    )


def _reecrire_duree_details(details: str, duree: int) -> str:
    """Remplace la durée entre parenthèses dans les détails d'une séance."""
    return re.sub(r'\(\d+\s*min\)', f'({duree} min)', str(details))


def _contrainte_cap_velo(cap: Dict, velo: Dict, jour: Dict) -> Dict:
    """Construit/complète la contrainte de planification CAP/Vélo du jour."""
    duree_cap = int(cap.get('duree', 0) or 0)
    duree_velo = int(velo.get('duree', 0) or 0)
    existante = jour.get('contrainte')
    if isinstance(existante, dict) and existante:
        contrainte = dict(existante)
        contrainte['active'] = True
        contrainte['duree_cap'] = duree_cap
        contrainte['duree_velo'] = duree_velo
        if MESSAGE_CAP_VELO not in str(contrainte.get('message', '')):
            contrainte['message'] = (
                str(contrainte.get('message', '')).strip() + ' ' + MESSAGE_CAP_VELO
            ).strip()
        if MESSAGE_CAP_VELO not in str(contrainte.get('motif', '')):
            contrainte['motif'] = (
                str(contrainte.get('motif', '')).strip() + ' ' + MESSAGE_CAP_VELO
            ).strip()
        return contrainte

    disciplines = [
        seance.get('discipline')
        for seance in jour.get('seances', [])
        if seance.get('discipline') in _SPORT_DISCIPLINES
    ]
    return {
        'active': True,
        'type': 'cap_velo',
        'statut_jour': None,
        'capacite_normale': None,
        'nb_seances_sport': len(disciplines),
        'depassement': 0,
        'niveau_depasse': None,
        'disciplines': disciplines,
        'duree_cap': duree_cap,
        'duree_velo': duree_velo,
        'motif': MESSAGE_CAP_VELO,
        'message': MESSAGE_CAP_VELO,
    }


def _appliquer_regle_cap_velo(jour: Dict) -> bool:
    """Applique la règle CAP <= 50 % du Vélo du même jour.

    Retourne True si la règle n'a pas pu être respectée proprement (contrainte
    de planification créée), False sinon. Ne supprime jamais de séance.
    """
    seances = jour.get('seances', [])
    velos = [s for s in seances if s.get('discipline') in ('Vélo', 'Velo')]
    caps = [s for s in seances if s.get('discipline') == 'CAP']
    if not velos or not caps:
        return False

    velo = max(velos, key=lambda s: int(s.get('duree', 0) or 0))
    duree_velo = int(velo.get('duree', 0) or 0)
    if duree_velo <= 0:
        return False

    limite = duree_velo * _RATIO_CAP_VELO
    contrainte_creee = False
    for cap in caps:
        duree_cap = int(cap.get('duree', 0) or 0)
        if duree_cap <= limite:
            continue
        if _seance_cap_reductible(cap) and limite >= _DUREE_MIN_CAP:
            nouvelle_duree = int(limite)
            if 0 < nouvelle_duree < duree_cap:
                cap['duree'] = nouvelle_duree
                cap['details'] = _reecrire_duree_details(
                    cap.get('details', ''), nouvelle_duree
                )
                continue
        jour['contrainte'] = _contrainte_cap_velo(cap, velo, jour)
        jour['contrainte_planification'] = True
        contrainte_creee = True
    return contrainte_creee


def _changer_duree_seance(seance: Dict, nouvelle_duree: int) -> None:
    """Met à jour la durée d'une séance et sa durée affichée dans les détails."""
    nouvelle_duree = int(nouvelle_duree)
    seance['duree'] = nouvelle_duree
    seance['details'] = _reecrire_duree_details(
        seance.get('details', ''), nouvelle_duree
    )


def _garantir_ratio_cap_velo(jours: List[Dict]) -> List[str]:
    """Garantit CAP ≤ 50 % du vélo le même jour pour les CAP non réductibles.

    Une CAP de qualité (VMA/VC/Seuil...) ne peut pas être rognée sans casser
    sa structure : le vélo du même jour doit donc valoir au moins 2 × CAP. Le
    budget vélo restant est prélevé sur les autres séances vélo, sans jamais
    descendre sous 80 min. Si le budget vélo est insuffisant, la correction
    est partielle et l'impossibilité est explicitement signalée (jamais de
    clamp silencieux).
    """
    alertes = []
    items = []
    for jour in jours:
        seances = jour.get('seances', [])
        velos = [s for s in seances if s.get('discipline') in ('Vélo', 'Velo')]
        if not velos:
            continue
        velo = max(velos, key=lambda s: int(s.get('duree', 0) or 0))
        plancher = VELO_DUREE_MIN
        for cap in seances:
            if cap.get('discipline') != 'CAP' or _seance_cap_reductible(cap):
                continue
            plancher = max(
                plancher,
                min(VELO_DUREE_MAX_TECHNIQUE, 2 * int(cap.get('duree', 0) or 0)),
            )
        items.append({
            'jour': jour,
            'seance': velo,
            'plancher': plancher,
            'surplus': int(velo.get('duree', 0) or 0) - plancher,
        })

    if not any(item['surplus'] < 0 for item in items):
        return alertes

    for item in items:
        seance = item['seance']
        besoin = item['plancher'] - int(seance.get('duree', 0) or 0)
        while besoin > 0:
            donneurs = [j for j in items if j['surplus'] > 0]
            if not donneurs:
                break
            donneur = max(donneurs, key=lambda j: j['surplus'])
            pris = min(donneur['surplus'], besoin)
            _changer_duree_seance(
                donneur['seance'], int(donneur['seance']['duree']) - pris
            )
            donneur['surplus'] -= pris
            _changer_duree_seance(seance, int(seance['duree']) + pris)
            besoin -= pris
        if besoin > 0:
            alertes.append(
                "Volume vélo insuffisant pour respecter la règle CAP ≤ 50 % du "
                f"vélo le {item['jour'].get('jour', '')} : impossible de "
                "sécuriser la CAP de qualité par un vélo d'au moins "
                f"{item['plancher']} min. Sécurisation partielle appliquée, "
                "à confirmer."
            )
    return alertes


def _journee_hors_plan(
    nom_jour: str, date_courante: datetime, date_objectif: datetime
) -> Dict:
    """Journée présente dans la semaine mais hors de la fenêtre du plan."""
    if date_courante <= date_objectif:
        date_str = date_courante.strftime('%Y-%m-%d')
    else:
        date_str = ''
    return {
        'jour': nom_jour,
        'date': date_str,
        'seances': [{
            'discipline': 'Repos',
            'type': 'Repos',
            'details': 'Hors plan',
            'duree': 0,
            'difficulte': 'repos'
        }],
        'difficulte': 'repos',
        'emoji': '⬜',
        'biquotidien': False,
        'hors_plan': True
    }


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
    courses_preparatoires: List[Dict] = None,
    derniers_intenses: Dict = None,
    date_debut_plan: datetime = None
) -> Dict:
    if seances_vma is None:
        seances_vma = []
    if seances_vc is None:
        seances_vc = []
    if semaines_anterieures is None:
        semaines_anterieures = []
    if courses_preparatoires is None:
        courses_preparatoires = []
    if derniers_intenses is None:
        derniers_intenses = {}
    if date_debut_plan is None:
        date_debut_plan = date_semaine

    # Les semaines sont toujours ancrées sur le lundi (structure CDC) :
    # le premier jour de la semaine est le lundi, le dernier le dimanche.
    lundi_semaine = date_semaine - timedelta(days=date_semaine.weekday())
    dimanche_semaine = lundi_semaine + timedelta(days=6)

    phase = determiner_phase(semaine_num, nb_semaines)
    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    niveau = profil.get('niveau_estime', 'Intermédiaire')
    objectif = profil.get('objectif_principal', '')
    competition_objectif = profil.get('competition_objectif', '') or ''
    format_competition = profil.get('format_competition', '') or ''
    
    # Le sport principal vient exclusivement du profil.
    # Le bloc de disponibilités ne fournit pas de défaut silencieux.
    sport_principal = profil.get('sport_principal')
    
    jours_cap = disponibilites.get('CAP', [])
    jours_velo = disponibilites.get('Velo', [])
    jours_natation = disponibilites.get('Natation', [])
    jours_biquotidien = _selectionner_jours_biquotidien(disponibilites, semaine_num)
    jours_biquotidien_normaux = []
    if disponibilites.get('bi_quotidien_mode') == 'tri_quadri':
        jours_biquotidien_normaux = [
            jour for jour in _jours_biquotidien_source(disponibilites)
            if jour not in jours_biquotidien
        ]

    mode_biquotidien = disponibilites.get('bi_quotidien_mode', 'standard')
    capacite_brute = str(disponibilites.get('bi_quotidien_capacite_brute', '') or '').lower()
    statut_par_jour = {}
    for nom_jour in JOURS_SEMAINE:
        if nom_jour in jours_biquotidien:
            if mode_biquotidien == 'tri_quadri':
                statut_par_jour[nom_jour] = 'quadri' if 'quadri' in capacite_brute else 'tri'
            else:
                statut_par_jour[nom_jour] = 'biquotidien'
        elif nom_jour in jours_biquotidien_normaux:
            statut_par_jour[nom_jour] = 'biquotidien'
        else:
            statut_par_jour[nom_jour] = 'normal'

    disciplines_objectif = _disciplines_objectif(competition_objectif, format_competition)

    nb_cap = len(jours_cap)
    nb_velo = len(jours_velo)
    nb_natation = len(jours_natation)
    
    nb_cap_utilises = _determiner_nb_jours_utilises(nb_cap, niveau, phase)
    nb_velo_utilises = _determiner_nb_jours_utilises(nb_velo, niveau, phase)
    nb_natation_utilises = _determiner_nb_jours_utilises(nb_natation, niveau, phase)

    # Règle métier: sport_principal fixe la priorité de base et
    # l'objectif sportif la renforce, sans jamais retirer de discipline
    # disponible. Seule la répartition des jours est ajustée.
    priority_map = get_sport_priority_map(sport_principal)
    if disciplines_objectif:
        priorite_max = max(priority_map.values()) if priority_map else 1
        for discipline in priority_map:
            if discipline in disciplines_objectif:
                priority_map[discipline] = priorite_max + 1
    max_priority = max(priority_map.values()) if priority_map else 1

    # La priorité la plus élevée conserve son compte de jours calculé.
    # Les disciplines moins prioritaires sont réduites d'un jour dans
    # le sous-ensemble réellement sélectionné; ainsi le plan bascule entre
    # les mêmes blocs métier mais avec une distribution de jours différente.
    for discipline, priority_value in priority_map.items():
        if priority_value < max_priority:
            if discipline == 'CAP':
                nb_cap_utilises = max(1, min(nb_cap_utilises, nb_cap) - 1)
            elif discipline == 'Velo':
                nb_velo_utilises = max(1, min(nb_velo_utilises, nb_velo) - 1)
            elif discipline == 'Natation':
                nb_natation_utilises = max(1, min(nb_natation_utilises, nb_natation) - 1)
    
    if nb_cap > nb_cap_utilises:
        jours_cap = _selectionner_jours_avec_longue('CAP', jours_cap, nb_cap_utilises)
        nb_cap = len(jours_cap)
    
    if nb_velo > nb_velo_utilises:
        jours_velo = _selectionner_jours_avec_longue('Velo', jours_velo, nb_velo_utilises)
        nb_velo = len(jours_velo)
    
    if nb_natation > nb_natation_utilises:
        jours_natation = _trier_jours_preferes('Natation', jours_natation)[:nb_natation_utilises]
        nb_natation = len(jours_natation)
    
    volume_approx = nb_cap * 45 + nb_velo * 90 + nb_natation * 45
    
    type_semaine = determiner_type_semaine(
        semaine_num, nb_semaines, volume_approx,
        min(get_nb_intenses_requis(nb_cap, semaine_num, 'normale'), nb_cap),
        phase, semaines_anterieures
    )
    
    if semaines_anterieures:
        dernier_type = semaines_anterieures[-1].get('semaine_type', 'normale')
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
    
    # CORRIGÉ: Passer le sport principal à calculer_volume_hebdo
    volumes = calculer_volume_hebdo(
        {'CAP': jours_cap, 'Velo': jours_velo, 'Natation': jours_natation},
        niveau, objectif, type_semaine, phase, semaine_num,
        sport_principal
    )

    # --- Budget hebdomadaire Vélo -> séances ---
    # `volumes['Velo']` est un budget de minutes pour la semaine, jamais une
    # durée de séance. Règle existante conservée : pas de vélo le dimanche si
    # un CAP y est placé.
    cible_longue_velo = get_duree_longue_cible(objectif, format_competition)
    if 'Dimanche' in jours_cap:
        jours_velo = [jour for jour in jours_velo if jour != 'Dimanche']
        nb_velo = len(jours_velo)

    alertes_volume_velo = []
    if nb_velo > 0:
        while True:
            budget_velo = calculer_volume_hebdo(
                {'CAP': jours_cap, 'Velo': jours_velo, 'Natation': []},
                niveau, objectif, type_semaine, phase, semaine_num,
                sport_principal
            ).get('Velo', 0)
            if budget_velo >= nb_velo * VELO_DUREE_MIN or nb_velo <= 1:
                break
            # Budget théorique insuffisant : réduire le nombre de séances
            # (sans créer de séance < 80 min).
            jours_velo = _selectionner_jours_avec_longue(
                'Velo', jours_velo, nb_velo - 1
            )
            nb_velo = len(jours_velo)
        volumes['Velo'] = budget_velo
        if budget_velo < nb_velo * VELO_DUREE_MIN:
            alertes_volume_velo.append(
                f"Volume vélo théorique insuffisant ({budget_velo} min) pour "
                f"{nb_velo} séance(s) : le minimum de {VELO_DUREE_MIN} min par "
                "séance ne peut pas être respecté. Sécurisation appliquée "
                f"({VELO_DUREE_MIN} min), à confirmer."
            )

    coeff_volume = get_volume_coeff(type_semaine, phase, semaine_num)
    coeff_intensite = get_intensite_coeff(type_semaine)
    natation_km = get_natation_km(niveau)
    
    renforcement_place = False
    
    jours_dispo_renforcement = jours_disponibles_renforcement(jours_cap, jours_velo, jours_natation)
    
    jours = []
    a_vma = vma is not None and not math.isnan(vma) and vma > 0
    a_vc = vc is not None and not math.isnan(vc) and vc > 0
    a_les_deux = a_vma and a_vc
    
    if nb_cap <= 2 and semaine_num % 3 == 0:
        nb_intenses_requis = max(nb_intenses_requis, 1)

    # Courses préparatoires de la semaine : événements imposés du calendrier.
    # Elles sont prioritaires sur le repos et sur toute séance normale, et
    # sont créées même sur un jour non sélectionné (mais dans la fenêtre du plan).
    courses_extraites = extraire_courses(courses_preparatoires, date_objectif.year)
    date_objectif_str = date_objectif.strftime('%Y-%m-%d')
    course_semaine = [
        course for course in courses_extraites
        if lundi_semaine <= course['date'] <= dimanche_semaine
        and course['date'].strftime('%Y-%m-%d') != date_objectif_str
    ]
    dates_courses = {
        'CAP': [c['date'] for c in course_semaine if c['discipline'] == 'CAP'],
        'Velo': [c['date'] for c in course_semaine if c['discipline'] == 'Vélo'],
        'Natation': [c['date'] for c in course_semaine if c['discipline'] == 'Natation'],
    }

    # Une compétition préparatoire compte comme séance d'intensité : elle
    # réduit le quota de séances intenses CAP supplémentaires de la semaine.
    nb_intenses_cap = max(0, nb_intenses_requis - len(dates_courses['CAP']))

    # Rôles de placement décidés au niveau semaine : intensité en semaine,
    # séance longue le week-end, selon les disponibilités réelles.
    roles_par_jour, alertes_placement = _construire_roles_semaine(
        jours_cap, jours_velo, jours_natation, nb_intenses_cap,
        date_semaine, derniers_intenses, dates_courses
    )
    nb_cap_intenses_placees = 0

    # Durées vélo par jour : répartition du budget hebdomadaire. La séance
    # longue (rôle 'longue', placée en priorité le dimanche si disponible)
    # reçoit la plus grande part ; les autres reçoivent le reliquat.
    durees_velo_par_jour = {}
    if nb_velo > 0:
        repartition_velo = repartir_volume_velo(
            volumes.get('Velo', 0), nb_velo, cible_longue_velo
        )
        if repartition_velo is None:
            # Sécurisation signalée : jamais de séance < 80 min.
            repartition_velo = [VELO_DUREE_MIN] * nb_velo
        repartition_velo = sorted(repartition_velo, reverse=True)
        jour_longue_velo = next(
            (
                jour for jour in jours_velo
                if roles_par_jour.get(jour, {}).get('Velo') == 'longue'
            ),
            None
        )
        if jour_longue_velo is None:
            jour_longue_velo = (
                _jour_longue_prioritaire('Velo', jours_velo) or jours_velo[0]
            )
        durees_velo_par_jour[jour_longue_velo] = repartition_velo[0]
        autres_jours_velo = [
            jour for jour in jours_velo if jour != jour_longue_velo
        ]
        for jour, duree in zip(autres_jours_velo, repartition_velo[1:]):
            durees_velo_par_jour[jour] = duree

    alertes_placement.extend(alertes_volume_velo)

    # Alternance COURTE / LONGUE des intensités CAP successives (état mémorisé
    # d'une semaine à l'autre via derniers_intenses).
    derniere_categorie_cap = (derniers_intenses or {}).get('CAP_categorie')

    # Les 7 jours calendaires (lundi -> dimanche) sont toujours présents.
    # Les jours hors de la fenêtre du plan restent affichés mais vides.
    for i in range(7):
        date_courante = lundi_semaine + timedelta(days=i)
        nom_jour = JOURS_SEMAINE[i]
        date_str = generer_jour_date(lundi_semaine, i)

        if date_courante < date_debut_plan or date_courante > date_objectif:
            jours.append(_journee_hors_plan(nom_jour, date_courante, date_objectif))
            continue

        course_du_jour = [c for c in course_semaine if date_str == c['date'].strftime('%Y-%m-%d')]
        if course_du_jour:
            course = course_du_jour[0]
            jour_course = {
                'jour': nom_jour,
                'date': date_str,
                'seances': [{
                    'discipline': course['discipline'],
                    'type': 'Compétition',
                    'details': course['nom'] or 'Compétition',
                    'duree': 0,
                    'difficulte': 'course',
                    'cle': True
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
            nb_intenses_requis, nb_cap_intenses_placees, 0, renforcement_place,
            a_vma, a_vc, a_les_deux,
            seances_vma, seances_vc,
            semaine_num, nb_cap, objectif, vma, vc,
            jours_dispo_renforcement, date_semaine, i,
            nb_semaines,
            sport_principal,
            nom_jour in jours_biquotidien or nom_jour in jours_biquotidien_normaux,
            statut_par_jour[nom_jour],
            roles_jour=roles_par_jour.get(nom_jour, {}),
            derniere_categorie_cap=derniere_categorie_cap,
            durees_velo_par_jour=durees_velo_par_jour
        )
        
        for s in jour['seances']:
            if s.get('discipline') == 'CAP' and s.get('difficulte') in ['intense', 'seuil']:
                nb_cap_intenses_placees += 1
            if s.get('discipline') == 'CAP' and s.get('categorie_intensite'):
                derniere_categorie_cap = s['categorie_intensite']
                if s.get('alternance_impossible'):
                    alertes_placement.append(
                        "Alternance des intensités CAP : aucune alternative "
                        "COURTE/LONGUE disponible ; séance conservée."
                    )
            if s.get('discipline') == 'Renforcement':
                renforcement_place = True
        
        jours.append(jour)

    if derniers_intenses is not None and derniere_categorie_cap:
        derniers_intenses['CAP_categorie'] = derniere_categorie_cap
    
    if not renforcement_place and type_semaine not in ['affutage', 'recuperation']:
        for jour in jours:
            if jour.get('difficulte') in ['endurance', 'recuperation']:
                jour['seances'].append(generer_seance_renforcement('Renforcement', 30))
                renforcement_place = True
                break

    for jour in jours:
        contrainte = _detecter_contrainte(jour, statut_par_jour.get(jour['jour'], 'normal'))
        jour['contrainte_planification'] = contrainte['active']
        jour['contrainte'] = contrainte

    # Règle métier CAP/Vélo le même jour : un jour partagé avec une CAP de
    # qualité reçoit d'abord un vélo ≥ 2 × CAP (prélèvement sur le budget vélo
    # de la semaine), puis la règle rogne les CAP réductibles restantes.
    alertes_placement.extend(_garantir_ratio_cap_velo(jours))
    for jour in jours:
        _appliquer_regle_cap_velo(jour)

    contraintes_semaine = [jour['contrainte'] for jour in jours if jour['contrainte']['active']]
    
    volume_total = sum(s.get('duree', 0) for jour in jours for s in jour['seances'] if s.get('discipline') not in ['Repos', 'Course'])
    # Une compétition préparatoire compte comme séance d'intensité.
    seances_intenses = sum(
        1 for jour in jours for s in jour['seances']
        if s.get('difficulte') in ['intense', 'seuil', 'course']
    )
    
    return {
        'semaine_num': semaine_num,
        'semaine_type': type_semaine,
        'num_affichage': num_affichage,
        'emoji': emoji_semaine,
        'date_debut': lundi_semaine.strftime('%Y-%m-%d'),
        'date_fin': dimanche_semaine.strftime('%Y-%m-%d'),
        'phase': phase,
        'volume_total': volume_total,
        'seances_intenses': seances_intenses,
        'nb_seances': {'CAP': nb_cap, 'Velo': nb_velo, 'Natation': nb_natation},
        'volumes_cibles': volumes,
        'sport_principal': sport_principal,
        'bi_quotidien_nb': disponibilites.get('bi_quotidien_nb'),
        'jours_biquotidien': jours_biquotidien,
        'jours_biquotidien_normaux': jours_biquotidien_normaux,
        'contrainte_planification': bool(contraintes_semaine),
        'contraintes_planification': contraintes_semaine,
        'alertes_placement': alertes_placement,
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
    
    # Structure CDC : les semaines sont ancrées sur le lundi. Si le plan
    # débute en cours de semaine, les jours précédant le début restent
    # présents mais vides (lundi, mardi, ...).
    debut_lundi = debut - timedelta(days=debut.weekday())
    nb_semaines = (date_objectif - debut_lundi).days // 7 + 1
    nb_semaines = max(1, nb_semaines)
    
    semaines = []
    derniers_intenses = {}
    for s in range(nb_semaines):
        date_semaine = debut_lundi + timedelta(days=s * 7)
        if date_semaine > date_objectif:
            break
        semaine = construire_semaine(
            date_semaine, date_objectif, profil, disponibilites,
            s + 1, nb_semaines, seances_vma, seances_vc, semaines,
            courses_preparatoires, derniers_intenses,
            date_debut_plan=debut
        )
        _mettre_a_jour_derniers_intenses(derniers_intenses, semaine)
        semaines.append(semaine)

    _appliquer_semaine_exceptionnelle(semaines)
    return semaines


def _appliquer_semaine_exceptionnelle(semaines: List[Dict]) -> None:
    """Promeut la semaine de charge la plus élevée de la préparation.

    La semaine 🟤 exceptionnelle est la semaine "dure" la plus chargée
    (volume mesuré) de la préparation (générale ou spécifique). Elle reste
    unique et n'est appliquée que si le cycle produit une semaine dure.
    """
    candidats = [
        semaine for semaine in semaines
        if semaine.get('semaine_type') == 'dure'
        and semaine.get('phase') in ('preparation_generale', 'preparation_specifique')
    ]
    if not candidats:
        return
    pic = max(candidats, key=lambda semaine: semaine.get('volume_total', 0))
    pic['semaine_type'] = 'exceptionnelle'
    pic['emoji'] = get_emoji_semaine('exceptionnelle')


def _mettre_a_jour_derniers_intenses(derniers_intenses: Dict, semaine: Dict) -> None:
    """Mémorise la date de la dernière intensité réellement générée par discipline."""
    for jour in semaine.get('jours', []):
        for seance in jour.get('seances', []):
            discipline = seance.get('discipline')
            if discipline in ('Velo', 'Vélo'):
                discipline = 'Velo'
            if discipline not in ('CAP', 'Velo', 'Natation'):
                continue
            if seance.get('cle') is not True and seance.get('difficulte') not in ('intense', 'seuil'):
                continue
            try:
                date_seance = datetime.strptime(jour.get('date', ''), '%Y-%m-%d')
            except (TypeError, ValueError):
                continue
            if discipline not in derniers_intenses or date_seance > derniers_intenses[discipline]:
                derniers_intenses[discipline] = date_seance