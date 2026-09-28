# ============================================================
# FICHIER: src/planificateur/plan_csv.py
# RÔLE: Le CSV comme représentation opérationnelle du plan.
#       - localiser le CSV courant d'un athlète
#       - lire un CSV de plan et le reconstruire en structure
#         exploitable par les exports (PDF / Intervals)
#       Aucun accès au moteur de planification.
# ============================================================

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from stockage import get_plan_repository
from .constants_plan import EMOJI_JOURNEE, EMOJI_SEMAINE

LIGNES_ENTETE = {'OBJECTIF', 'COURSES', '---'}

# Difficultés canoniques utilisées pour décoder la colonne « Journée type ».
_DIFFICULTES_CANONIQUES = [
    'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
]
_EMOJI_VERS_DIFFICULTE = {
    EMOJI_JOURNEE[difficulte]: difficulte for difficulte in _DIFFICULTES_CANONIQUES
}
_EMOJI_VERS_TYPE_SEMAINE = {emoji: type_ for type_, emoji in EMOJI_SEMAINE.items()}


def _iso(ddmmyyyy: str) -> str:
    """Convertit JJ/MM/AAAA (CSV) en AAAA-MM-JJ (interne). Vide si impossible."""
    if not ddmmyyyy:
        return ''
    try:
        return datetime.strptime(ddmmyyyy.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        return ''


def _entier(valeur) -> int:
    try:
        return int(float(str(valeur).replace(',', '.')))
    except (ValueError, TypeError):
        return 0


def _nom_athlete_depuis_fichier(chemin_csv: str) -> str:
    base = os.path.basename(chemin_csv)
    base = re.sub(r'\.csv$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'_plan_\d{8}_\d{6}$', '', base)
    return base.replace('_', ' ').strip()


def trouver_csv_courant(plan_dir: str) -> Optional[str]:
    """Retourne le CSV de plan courant (le plus récent) du dossier d'un athlète.

    Délègue au dépôt de plans (LocalPlanRepository par défaut).
    """
    return get_plan_repository().trouver_plan_courant(plan_dir)


def lire_csv_plan(chemin_csv: str) -> pd.DataFrame:
    """Lit un CSV de plan via le dépôt de plans."""
    return get_plan_repository().lire_plan(chemin_csv)


def construire_plan_depuis_csv(chemin_csv: str, athlete: Optional[str] = None) -> Dict:
    """Reconstruit une structure de plan à partir du CSV courant.

    La structure produite est compatible avec les fonctions d'export
    existantes (clés 'semaines', 'jours', 'seances', 'date_debut', ...).
    Aucune donnée n'est inventée : tout provient du CSV.
    """
    df = lire_csv_plan(chemin_csv)

    lignes_objectif = df[df['N° semaine'] == 'OBJECTIF']
    date_objectif = ''
    if not lignes_objectif.empty:
        date_objectif = _iso(lignes_objectif.iloc[0].get('Date', ''))

    data = df[~df['N° semaine'].isin(LIGNES_ENTETE)].reset_index(drop=True)

    semaines: List[Dict] = []
    semaine_courante = None
    jour_courant = None

    for _, ligne in data.iterrows():
        label = ligne.get('N° semaine', '')
        if semaine_courante is None or semaine_courante['_label'] != label:
            semaine_courante = {
                '_label': label,
                'jours': [],
                'emoji': '',
                'semaine_type': 'normale',
                'num_affichage': '',
            }
            semaines.append(semaine_courante)
            jour_courant = None

        if ligne.get('Jour', '') != '*':
            jour_courant = {
                'jour': ligne.get('Jour', ''),
                'date': _iso(ligne.get('Date', '')),
                'seances': [],
                'contrainte': {'active': False, 'message': ''},
                'hors_plan': False,
            }
            semaine_courante['jours'].append(jour_courant)

        if jour_courant is None:
            continue

        details = ligne.get('Détails', '')
        emoji = ligne.get('Journée type', '')
        difficulte = _EMOJI_VERS_DIFFICULTE.get(emoji, 'endurance')
        seance = {
            'discipline': ligne.get('Discipline', ''),
            'type': ligne.get('Type de séance', ''),
            'details': details,
            'duree': _entier(ligne.get('Durée (min)', '0')),
            'difficulte': difficulte,
            'cle': False,
        }
        jour_courant['seances'].append(seance)
        if details == 'Hors plan':
            jour_courant['hors_plan'] = True
        if ligne.get('Contrainte planification', '') == 'Oui':
            jour_courant['contrainte'] = {
                'active': True,
                'message': ligne.get('Message contrainte', ''),
                'capacite_normale': 1,
            }

    # Compléments par semaine : emoji, type, numéro, bornes lundi/dimanche.
    lundi_precedent = None
    for semaine in semaines:
        label = semaine.pop('_label')
        semaine['emoji'] = _emoji_depuis_label(label)
        semaine['semaine_type'] = _EMOJI_VERS_TYPE_SEMAINE.get(
            semaine['emoji'], 'normale'
        )
        semaine['num_affichage'] = _numero_affichage(label)

        lundi = _lundi_semaine(semaine, lundi_precedent)
        if lundi is not None:
            semaine['date_debut'] = lundi.strftime('%Y-%m-%d')
            semaine['date_fin'] = (lundi + timedelta(days=6)).strftime('%Y-%m-%d')
            lundi_precedent = lundi
        else:
            semaine['date_debut'] = ''
            semaine['date_fin'] = ''

        for jour in semaine['jours']:
            jour['contrainte_planification'] = bool(jour['contrainte']['active'])

    # date_debut du plan = première journée réellement dans la fenêtre du plan.
    date_debut = ''
    for semaine in semaines:
        for jour in semaine['jours']:
            if jour['date'] and not jour['hors_plan']:
                date_debut = jour['date']
                break
        if date_debut:
            break
    if not date_debut and semaines:
        for jour in semaines[0]['jours']:
            if jour['date']:
                date_debut = jour['date']
                break

    return {
        'athlete': athlete or _nom_athlete_depuis_fichier(chemin_csv),
        'date_debut': date_debut,
        'date_objectif': date_objectif,
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': {},
        'disponibilites': {},
    }


def _emoji_depuis_label(label: str) -> str:
    """Extrait l'emoji d'un libellé de semaine (ex: '🟢S-15' -> '🟢')."""
    return ''.join(c for c in str(label) if not (c.isalnum() or c in '-'))


def _numero_affichage(label: str):
    match = re.search(r'S-(\d+)', str(label))
    return int(match.group(1)) if match else ''


def _lundi_semaine(semaine: Dict, lundi_precedent) -> Optional[datetime]:
    for jour in semaine['jours']:
        if jour['date']:
            date = datetime.strptime(jour['date'], '%Y-%m-%d')
            return date - timedelta(days=date.weekday())
    if lundi_precedent is not None:
        return lundi_precedent + timedelta(days=7)
    return None


def ecrire_csv_plan(plan: Dict, plan_dir: str) -> str:
    """Écrit le CSV du plan dans le dossier de l'athlète (délègue à l'export)."""
    from .export_csv import exporter_plan_csv
    return exporter_plan_csv(plan, plan_dir)


def lister_csv_plans(racine: Optional[str] = None) -> List[Dict]:
    """Liste tous les CSV de plans présents sous ``racine`` (récursif).

    Délègue au dépôt de plans. Chaque entrée représente UN fichier CSV
    (chemin = référence). Aucune déduplication par nom d'athlète : deux
    préparations distinctes (ou deux dossiers aux noms proches) restent
    deux entrées distinctes.
    """
    return get_plan_repository().lister_plans(racine)


def resoudre_selection(saisie: str, nombre: int) -> List[int]:
    """Convertit une sélection utilisateur en indices 0-based.

    Formats acceptés : ``1``, ``1,3,5``, ``1-5``, ``*`` (tout).
    Les indices hors bornes sont ignorés, les doublons supprimés.
    """
    texte = str(saisie or '').strip()
    if not texte or nombre <= 0:
        return []
    if texte == '*':
        return list(range(nombre))
    indices = set()
    for morceau in re.split(r'[,\s;]+', texte):
        if not morceau:
            continue
        if '-' in morceau:
            debut, _, fin = morceau.partition('-')
            if debut.strip().isdigit() and fin.strip().isdigit():
                borne_a, borne_b = int(debut), int(fin)
                for valeur in range(min(borne_a, borne_b), max(borne_a, borne_b) + 1):
                    if 1 <= valeur <= nombre:
                        indices.add(valeur - 1)
        elif morceau.isdigit():
            valeur = int(morceau)
            if 1 <= valeur <= nombre:
                indices.add(valeur - 1)
    return sorted(indices)
