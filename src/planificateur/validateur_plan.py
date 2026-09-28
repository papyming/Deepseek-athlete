# ============================================================
# FICHIER: src/planificateur/validateur_plan.py
# RÔLE: Validateur DÉTERMINISTE du CSV de plan.
#       Contrôle le CSV tel qu'il existe, sans reconstruire le
#       plan et sans dépendre du moteur de planification ni
#       d'un quelconque fournisseur d'IA.
# ============================================================

from datetime import datetime
from typing import Dict, List, Optional

from .constants_plan import EMOJI_JOURNEE
from .plan_csv import LIGNES_ENTETE, lire_csv_plan

COLONNES_OBLIGATOIRES = [
    'N° semaine', 'Jour', 'Date', 'Discipline', 'Type de séance',
    'Détails', 'Durée (min)',
]

DISCIPLINES_CONNUES = {
    'CAP', 'Vélo', 'Velo', 'Natation', 'Renforcement', 'Repos', 'Course',
}
DISCIPLINES_SPORT = {'CAP', 'Vélo', 'Velo', 'Natation'}
DISCIPLINES_ENDURANCE = {'CAP', 'Vélo', 'Velo'}
TYPES_SANS_DUREE = {'Repos', 'Compétition', 'Objectif', '', 'Préparatoires'}
JOURS_SEMAINE = [
    'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche',
]

_DIFFICULTES_CANONIQUES = [
    'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
]
_EMOJI_VERS_DIFFICULTE = {
    EMOJI_JOURNEE[difficulte]: difficulte for difficulte in _DIFFICULTES_CANONIQUES
}


def _est_entier(valeur) -> bool:
    try:
        int(float(str(valeur).replace(',', '.')))
        return True
    except (ValueError, TypeError):
        return False


def _entier(valeur) -> int:
    try:
        return int(float(str(valeur).replace(',', '.')))
    except (ValueError, TypeError):
        return 0


def _iso(ddmmyyyy: str) -> str:
    if not ddmmyyyy:
        return ''
    try:
        return datetime.strptime(str(ddmmyyyy).strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        return ''


def valider_plan_csv(chemin_csv: str, disponibilites: Optional[Dict] = None) -> Dict:
    """Valide un CSV de plan selon les règles du CDC.

    Retourne : {'valide', 'erreurs', 'avertissements', 'stats'}.
    """
    erreurs: List[str] = []
    avertissements: List[str] = []

    try:
        df = lire_csv_plan(chemin_csv)
    except FileNotFoundError:
        return {'valide': False, 'erreurs': ['Fichier CSV introuvable'],
                'avertissements': [], 'stats': {}}
    except Exception as erreur:  # CSV illisible
        return {'valide': False, 'erreurs': [f'CSV illisible : {erreur}'],
                'avertissements': [], 'stats': {}}

    manquantes = [c for c in COLONNES_OBLIGATOIRES if c not in df.columns]
    if manquantes:
        erreurs.append('Colonnes obligatoires manquantes : ' + ', '.join(manquantes))
        return {'valide': False, 'erreurs': erreurs, 'avertissements': avertissements,
                'stats': {'lignes': len(df)}}

    if not (df['N° semaine'] == 'OBJECTIF').any():
        erreurs.append("Ligne OBJECTIF absente (date de l'objectif inconnue).")

    data = df[~df['N° semaine'].isin(LIGNES_ENTETE)].reset_index(drop=True)

    # ---- Regroupement par jour ----
    jours: List[Dict] = []
    for _, ligne in data.iterrows():
        if ligne.get('Jour', '') != '*':
            jours.append({
                'semaine': ligne.get('N° semaine', ''),
                'jour': ligne.get('Jour', ''),
                'date': ligne.get('Date', ''),
                'lignes': [],
            })
        if not jours:
            erreurs.append('Journée sans libellé de jour.')
            continue
        jours[-1]['lignes'].append(ligne)

    _valider_structure(df, data, jours, erreurs, avertissements)
    _valider_lignes(data, erreurs, avertissements)
    _valider_espacement_intensites(jours, erreurs)
    if disponibilites:
        _valider_disponibilites(jours, disponibilites, erreurs, avertissements)

    stats = {
        'lignes': int(len(data)),
        'journees': len(jours),
        'semaines': int(data['N° semaine'].nunique()),
    }
    return {
        'valide': not erreurs,
        'erreurs': erreurs,
        'avertissements': avertissements,
        'stats': stats,
    }


def _valider_structure(df, data, jours, erreurs, avertissements):
    # Regroupement par semaine : 7 jours Lundi -> Dimanche
    semaines: List[Dict] = []
    for jour in jours:
        if not semaines or semaines[-1]['semaine'] != jour['semaine']:
            semaines.append({'semaine': jour['semaine'], 'jours': []})
        semaines[-1]['jours'].append(jour)

    for semaine in semaines:
        noms = [j['jour'] for j in semaine['jours']]
        if len(noms) != 7:
            erreurs.append(
                f"Semaine {semaine['semaine']}: {len(noms)} journées (7 attendues)."
            )
        if noms != JOURS_SEMAINE:
            erreurs.append(
                f"Semaine {semaine['semaine']}: ordre des jours invalide ({noms})."
            )

    for jour in jours:
        if jour['date'] and not _iso(jour['date']):
            erreurs.append(
                f"Jour {jour['jour']} ({jour['semaine']}): date invalide '{jour['date']}'."
            )
        if not jour['date']:
            seances = [l.get('Discipline', '') for l in jour['lignes']]
            if any(discipline in DISCIPLINES_SPORT for discipline in seances):
                erreurs.append(
                    f"Jour {jour['jour']} ({jour['semaine']}): séance sportive sans date."
                )


def _valider_lignes(data, erreurs, avertissements):
    for index, ligne in data.iterrows():
        discipline = ligne.get('Discipline', '')
        type_seance = ligne.get('Type de séance', '')
        duree_brute = ligne.get('Durée (min)', '')
        details = ligne.get('Détails', '')
        reference = f"{ligne.get('Jour', '')} {ligne.get('Date', '')} ({ligne.get('Discipline', '')}/{ligne.get('Type de séance', '')})"

        if discipline not in DISCIPLINES_CONNUES:
            erreurs.append(f"Discipline inconnue '{discipline}' — {reference}.")
        if not _est_entier(duree_brute):
            erreurs.append(f"Durée non numérique '{duree_brute}' — {reference}.")
            continue
        duree = _entier(duree_brute)

        if discipline == 'Repos' and duree != 0:
            erreurs.append(f"Repos avec durée {duree} — {reference}.")
        if discipline in DISCIPLINES_SPORT:
            if duree < 0:
                erreurs.append(f"Durée négative {duree} — {reference}.")
            elif duree == 0 and type_seance not in TYPES_SANS_DUREE:
                erreurs.append(f"Séance {discipline} à durée nulle — {reference}.")
        if not details:
            avertissements.append(f"Détails vides — {reference}.")


def _valider_espacement_intensites(jours, erreurs):
    """Vérifie la règle des 48 h par discipline et la règle CAP <= 50 % Velo."""
    intensites: Dict[str, List[str]] = {}
    for jour in jours:
        date_iso = _iso(jour['date'])
        velos = []
        caps = []
        for ligne in jour['lignes']:
            discipline = ligne.get('Discipline', '')
            if discipline in ('Vélo', 'Velo'):
                velos.append(_entier(ligne.get('Durée (min)', '0')))
            if discipline == 'CAP':
                caps.append(_entier(ligne.get('Durée (min)', '0')))
            difficulte = _EMOJI_VERS_DIFFICULTE.get(ligne.get('Journée type', ''), 'endurance')
            if difficulte in ('intense', 'seuil', 'course') and discipline in DISCIPLINES_SPORT:
                cle = 'Velo' if discipline in ('Vélo', 'Velo') else discipline
                intensites.setdefault(cle, [])
                if date_iso and date_iso not in intensites[cle]:
                    intensites[cle].append(date_iso)

        if caps and velos and max(velos) > 0:
            duree_velo = max(velos)
            for duree_cap in caps:
                if duree_cap > 0.5 * duree_velo + 1e-9:
                    erreurs.append(
                        f"CAP {duree_cap} min > 50 % du Vélo {duree_velo} min le "
                        f"{jour['date'] or jour['jour']}."
                    )

    for discipline, dates in intensites.items():
        dates_triees = sorted(datetime.strptime(d, '%Y-%m-%d') for d in dates)
        for precedente, suivante in zip(dates_triees, dates_triees[1:]):
            if (suivante - precedente).days < 2:
                erreurs.append(
                    f"Espacement des intensités {discipline} < 48 h "
                    f"({precedente.date()} → {suivante.date()})."
                )


def _valider_disponibilites(jours, disponibilites, erreurs, avertissements):
    dispo = {
        'CAP': set(disponibilites.get('CAP', [])),
        'Velo': set(disponibilites.get('Velo', [])),
        'Natation': set(disponibilites.get('Natation', [])),
    }
    dispo_toutes = dispo['CAP'] | dispo['Velo'] | dispo['Natation']
    for jour in jours:
        nb_sport = 0
        for ligne in jour['lignes']:
            discipline = ligne.get('Discipline', '')
            type_seance = ligne.get('Type de séance', '')
            if discipline in DISCIPLINES_SPORT:
                nb_sport += 1
                cle = 'Velo' if discipline in ('Vélo', 'Velo') else discipline
                if type_seance in ('Compétition', 'Objectif'):
                    continue  # une course imposée n'est pas soumise aux disponibilités
                if jour['jour'] not in dispo.get(cle, set()):
                    erreurs.append(
                        f"{discipline} le {jour['jour']} hors disponibilité."
                    )
            elif discipline == 'Renforcement':
                if jour['jour'] not in dispo_toutes:
                    avertissements.append(
                        f"Renforcement le {jour['jour']} hors disponibilité."
                    )
        if nb_sport > 1 and not any(
            ligne.get('Contrainte planification', '') == 'Oui'
            for ligne in jour['lignes']
        ):
            avertissements.append(
                f"{nb_sport} séances le {jour['jour']} sans contrainte de planification."
            )
