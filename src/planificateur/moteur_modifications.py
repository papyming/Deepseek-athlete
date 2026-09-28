# ============================================================
# FICHIER: src/planificateur/moteur_modifications.py
# RÔLE: Moteur DÉTERMINISTE de modification du CSV.
#
#       - recherche les séances dans le CSV ;
#       - applique les actions du contrat ;
#       - respecte les règles (disponibilités, 48 h, CAP/Vélo,
#         structure, etc.) via le VALIDATEUR EXISTANT ;
#       - n'écrit le CSV que si le résultat est valide ;
#       - produit un aperçu AVANT / APRÈS.
#
#       Aucune connexion IA. Aucun accès au moteur de planification.
# ============================================================

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from stockage import get_plan_repository
from .constants_plan import EMOJI_JOURNEE, get_difficulte
from .contrat_modifications import (
    ACTION_AJOUTER, ACTION_DEPLACER, ACTION_REMPLACER, ACTION_SUPPRIMER,
    ACTION_MODIFIER_DUREE, ACTION_MODIFIER_DETAILS, ACTION_MODIFIER_FREQUENCE,
    ACTION_AJOUTER_RESSOURCE, ACTION_INCOMPRIS,
    DETAILS_AJOUTER,
    FREQUENCE_UNE_SEMAINE_SUR_DEUX, FREQUENCE_UNE_SEMAINE_SUR_TROIS,
    JOURS_SEMAINE as JOURS,
    PERIODE_DATES, PERIODE_DATE_FIN, PERIODE_FIN_DU_PLAN,
    PERIODE_JUSQU_OBJECTIF, PERIODE_SEMAINE_COURANTE,
    PERIODE_SEMAINE_PROCHAINE, PERIODE_SEMAINES, PERIODE_TOUT,
    TYPE_COMPETITION, TYPE_ENDURANCE, TYPE_FARTLEK, TYPE_INTENSITE,
    TYPE_RECUPERATION, TYPE_RENFORCEMENT, TYPE_SEUIL, TYPE_SORTIE_LONGUE,
    normaliser_demande,
)
from .plan_csv import LIGNES_ENTETE, lire_csv_plan
from .validateur_plan import valider_plan_csv

COL_SEMAINE = 'N° semaine'
COL_JOUR = 'Jour'
COL_DATE = 'Date'
COL_DISCIPLINE = 'Discipline'
COL_TYPE = 'Type de séance'
COL_DETAILS = 'Détails'
COL_DUREE = 'Durée (min)'
COL_JOURNEE = 'Journée type'
COL_RESSOURCES = 'Ressources'

_DIFFICULTES_CANONIQUES = [
    'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
]
_EMOJI_VERS_DIFFICULTE = {
    EMOJI_JOURNEE[difficulte]: difficulte for difficulte in _DIFFICULTES_CANONIQUES
}

# Type canonique -> (libellé CSV par défaut, clé de difficulté)
_DEFAUTS_TYPE = {
    ('CAP', TYPE_ENDURANCE): ('Endurance fondamentale Z2', 'endurance_fondamentale'),
    ('CAP', TYPE_SORTIE_LONGUE): ('Sortie longue Z2', 'sortie_longue'),
    ('CAP', TYPE_SEUIL): ('Seuil Z3', 'seuil'),
    ('CAP', TYPE_INTENSITE): ('VMA', 'vma'),
    ('CAP', TYPE_FARTLEK): ('Fartlek', 'fartlek'),
    ('CAP', TYPE_RECUPERATION): ('Footing de récupération Z1', 'endurance_recuperative'),
    ('Vélo', TYPE_ENDURANCE): ('Endurance Z2', 'endurance'),
    ('Vélo', TYPE_SORTIE_LONGUE): ('Sortie longue Z2', 'sortie_longue'),
    ('Vélo', TYPE_SEUIL): ('Seuil Z4', 'seuil'),
    ('Vélo', TYPE_INTENSITE): ('Seuil Z4', 'seuil'),
    ('Vélo', TYPE_RECUPERATION): ('Récupération active', 'recup'),
    ('Natation', TYPE_ENDURANCE): ('Endurance Z2', 'endurance'),
    ('Natation', TYPE_SEUIL): ('Seuil Z4', 'seuil'),
    ('Natation', TYPE_INTENSITE): ('Technique + Seuil', 'seuil'),
    ('Natation', TYPE_RECUPERATION): ('Récupération active', 'recup'),
    ('Renforcement', TYPE_RENFORCEMENT): ('Renforcement général', 'renforcement_general'),
}


def _iso(ddmmyyyy: str) -> str:
    if not ddmmyyyy:
        return ''
    try:
        return datetime.strptime(str(ddmmyyyy).strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        return ''


def _format_date(iso: str) -> str:
    if not iso:
        return ''
    try:
        return datetime.strptime(str(iso), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return ''


def _date_souple(valeur) -> str:
    """Accepte une date ISO (AAAA-MM-JJ) ou JJ/MM/AAAA -> ISO."""
    if not valeur:
        return ''
    texte = str(valeur).strip()
    for format_date in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(texte, format_date).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return ''


def _entier(valeur) -> int:
    try:
        return int(float(str(valeur).replace(',', '.')))
    except (ValueError, TypeError):
        return 0


def _normalise_discipline(valeur: str) -> str:
    return 'Vélo' if valeur in ('Vélo', 'Velo') else valeur


# ------------------------------------------------------------------
# Lecture / écriture par blocs (journées) : préserve l'ordre et les
# colonnes, n'altère que ce qui est demandé.
# ------------------------------------------------------------------

def _lire_blocs(chemin_csv: str):
    df = lire_csv_plan(chemin_csv)
    colonnes = list(df.columns)
    entetes: List[Dict] = []
    jours: List[Dict] = []
    for _, ligne in df.iterrows():
        ligne = {colonne: str(ligne[colonne]) for colonne in colonnes}
        if ligne[COL_SEMAINE] in LIGNES_ENTETE:
            entetes.append(ligne)
            continue
        if ligne[COL_JOUR] != '*':
            jours.append({
                'semaine': ligne[COL_SEMAINE],
                'jour': ligne[COL_JOUR],
                'date': _iso(ligne[COL_DATE]),
                'rows': [],
            })
        if jours:
            jours[-1]['rows'].append(ligne)
    return colonnes, entetes, jours


def _ajouter_colonne(colonnes, entetes, jours, nom):
    if nom in colonnes:
        return
    colonnes.append(nom)
    for entete in entetes:
        entete.setdefault(nom, '')
    for jour in jours:
        for row in jour['rows']:
            row.setdefault(nom, '')


def _ecrire_temp(colonnes, entetes, jours, chemin_reference) -> str:
    lignes = [{c: entete.get(c, '') for c in colonnes} for entete in entetes]
    for jour in jours:
        for index, row in enumerate(jour['rows']):
            sortie = {c: row.get(c, '') for c in colonnes}
            sortie[COL_SEMAINE] = jour['semaine']
            sortie[COL_JOUR] = jour['jour'] if index == 0 else '*'
            sortie[COL_DATE] = _format_date(jour['date'])
            lignes.append(sortie)
    df = pd.DataFrame(lignes, columns=colonnes)
    depot = get_plan_repository()
    chemin_temp = depot.chemin_temporaire(chemin_reference)
    depot.ecrire_plan(df, chemin_temp)
    return chemin_temp


# ------------------------------------------------------------------
# Contexte (semaines, objectif, référence)
# ------------------------------------------------------------------

def _construire_contexte(jours, date_reference: Optional[datetime]) -> Dict:
    objectif = None
    semaines: List[Dict] = []
    for jour in jours:
        if not semaines or semaines[-1]['label'] != jour['semaine']:
            semaines.append({'label': jour['semaine'], 'lundi': None, 'jours': {}})
        if jour['date']:
            semaines[-1]['jours'][jour['jour']] = jour['date']
    lundi_precedent = None
    for semaine in semaines:
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in semaine['jours'].values()]
        if dates:
            lundi = min(dates) - timedelta(days=min(dates).weekday())
        elif lundi_precedent is not None:
            lundi = lundi_precedent + timedelta(days=7)
        else:
            lundi = None
        semaine['lundi'] = lundi
        if lundi is not None:
            lundi_precedent = lundi

    if semaines:
        derniere = semaines[-1]
        # la date d'objectif = dernier jour non vide de la dernière semaine
        tous = [d for s in semaines for d in s['jours'].values()]
        if tous:
            objectif = max(tous)

    debut = None
    for jour in jours:
        if jour['date']:
            debut = jour['date']
            break

    return {
        'objectif': objectif,
        'debut': debut,
        'date_reference': date_reference or datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0),
        'semaines': semaines,
    }


def _index_semaine(semaines, reference: datetime) -> int:
    for index, semaine in enumerate(semaines):
        lundi = semaine['lundi']
        if lundi is not None and lundi <= reference <= lundi + timedelta(days=6):
            return index
    # repli : semaine la plus proche
    meilleur, distance = 0, None
    for index, semaine in enumerate(semaines):
        lundi = semaine['lundi']
        if lundi is None:
            continue
        d = abs((lundi - reference).days)
        if distance is None or d < distance:
            meilleur, distance = index, d
    return meilleur


def _semaines_cibles(modification, contexte):
    semaines = contexte['semaines']
    if not semaines:
        return []
    index_reference = _index_semaine(semaines, contexte['date_reference'])
    periode = modification.get('periode')
    if periode is None:
        # Période par défaut : fin du plan pour une création récurrente,
        # sinon opération ponctuelle sur la semaine courante.
        type_periode = modification.get('periode_par_defaut') or PERIODE_SEMAINE_COURANTE
        periode = {}
    else:
        type_periode = periode.get('type')

    if type_periode in (None, PERIODE_SEMAINE_COURANTE):
        return [index_reference]
    if type_periode == PERIODE_SEMAINE_PROCHAINE:
        return [min(index_reference + 1, len(semaines) - 1)]
    if type_periode == PERIODE_SEMAINES:
        nombre = int(periode.get('nb') or periode.get('nombre') or 1)
        return list(range(index_reference, min(index_reference + nombre, len(semaines))))
    if type_periode in (PERIODE_JUSQU_OBJECTIF, PERIODE_FIN_DU_PLAN):
        return list(range(index_reference, len(semaines)))
    if type_periode == PERIODE_TOUT:
        return list(range(len(semaines)))
    if type_periode in (PERIODE_DATES, PERIODE_DATE_FIN):
        debut = _date_souple(periode.get('debut') or periode.get('valeur') or '')
        fin = _date_souple(periode.get('fin') or periode.get('valeur') or '')
        selection = []
        for index, semaine in enumerate(semaines):
            if semaine['lundi'] is None:
                continue
            lundi = semaine['lundi'].strftime('%Y-%m-%d')
            dimanche = (semaine['lundi'] + timedelta(days=6)).strftime('%Y-%m-%d')
            if debut and dimanche < debut:
                continue
            if fin and lundi > fin:
                continue
            if index < index_reference:
                continue
            selection.append(index)
        return selection
    return [index_reference]


def _dates_pour(modification, contexte, utiliser_jour: bool = True,
                utiliser_date: bool = True) -> List[str]:
    semaines = contexte['semaines']
    indices = _semaines_cibles(modification, contexte)
    frequence = modification.get('frequence') or {}
    intervalle = 1
    type_freq = frequence.get('type')
    if type_freq == FREQUENCE_UNE_SEMAINE_SUR_DEUX:
        intervalle = 2
    elif type_freq == FREQUENCE_UNE_SEMAINE_SUR_TROIS:
        intervalle = 3
    intervalle = int(frequence.get('intervalle') or intervalle) or 1
    jour = (modification.get('jour_cible') or frequence.get('jour')) if utiliser_jour else None

    dates: List[str] = []
    for position, index in enumerate(indices):
        if position % intervalle != 0:
            continue
        semaine = semaines[index]
        if utiliser_date and modification.get('date_cible'):
            date_iso = _iso(modification['date_cible'])
            if date_iso:
                dates.append(date_iso)
            continue
        if jour and semaine['lundi'] is not None:
            date_iso = (semaine['lundi'] + timedelta(days=JOURS.index(jour))).strftime('%Y-%m-%d')
            dates.append(date_iso)
        elif not jour:
            dates.extend(sorted(semaine['jours'].values()))

    debut = contexte.get('debut')
    objectif = contexte.get('objectif')
    filtre = []
    for date_iso in sorted(set(dates)):
        if debut and date_iso < debut:
            continue
        if objectif and date_iso > objectif:
            continue
        filtre.append(date_iso)
    return filtre


def _trouver_jour(jours, date_iso):
    for jour in jours:
        if jour['date'] == date_iso:
            return jour
    return None


def _semaine_par_label(contexte, label):
    for semaine in contexte['semaines']:
        if semaine['label'] == label:
            return semaine
    return None


# ------------------------------------------------------------------
# Recherche de séances
# ------------------------------------------------------------------

def _type_correspond(row, type_canonique) -> bool:
    type_l = str(row.get(COL_TYPE, '')).lower()
    discipline = _normalise_discipline(row.get(COL_DISCIPLINE, ''))
    difficulte = _EMOJI_VERS_DIFFICULTE.get(row.get(COL_JOURNEE, ''), 'endurance')
    if type_canonique == TYPE_SORTIE_LONGUE:
        return 'sortie longue' in type_l
    if type_canonique == TYPE_RENFORCEMENT:
        return discipline == 'Renforcement'
    if type_canonique == TYPE_COMPETITION:
        return discipline == 'Course' or any(
            mot in type_l for mot in ('compétition', 'competition', 'objectif')
        )
    if type_canonique == TYPE_SEUIL:
        return 'seuil' in type_l or difficulte == 'seuil'
    if type_canonique == TYPE_INTENSITE:
        return difficulte in ('intense', 'seuil') or any(
            mot in type_l for mot in ('vma', 'vc', 'test', 'fartlek', 'seuil', 'intens')
        )
    if type_canonique == TYPE_FARTLEK:
        return 'fartlek' in type_l
    if type_canonique == TYPE_RECUPERATION:
        return difficulte == 'recuperation' or 'récup' in type_l or 'recup' in type_l
    if type_canonique == TYPE_ENDURANCE:
        return difficulte == 'endurance' and 'sortie longue' not in type_l
    return True


def _ligne_correspond(row, jour_bloc, cible) -> bool:
    discipline = cible.get('discipline')
    if discipline and _normalise_discipline(row.get(COL_DISCIPLINE, '')) != discipline:
        return False
    if cible.get('type_seance') and not _type_correspond(row, cible['type_seance']):
        return False
    if cible.get('jour') and jour_bloc['jour'] != cible['jour']:
        return False
    if cible.get('date') and jour_bloc['date'] != _iso(cible['date']):
        return False
    if cible.get('difficulte'):
        difficulte = _EMOJI_VERS_DIFFICULTE.get(row.get(COL_JOURNEE, ''), 'endurance')
        if difficulte != cible['difficulte']:
            return False
    if row.get(COL_DISCIPLINE, '') in ('Repos', 'Course'):
        return False
    return True


def _chercher(jours, cible, dates=None):
    resultats = []
    for jour_bloc in jours:
        if dates is not None and jour_bloc['date'] not in dates:
            continue
        for row in jour_bloc['rows']:
            if _ligne_correspond(row, jour_bloc, cible):
                resultats.append({'row': row, 'jour_bloc': jour_bloc})
    return resultats


def _cible_source(modification) -> Dict:
    """Critère de sélection de la séance SOURCE (sans le jour cible)."""
    cible = dict(modification.get('cible') or {})
    if modification.get('discipline'):
        cible.setdefault('discipline', modification['discipline'])
    if modification.get('type_seance'):
        cible.setdefault('type_seance', modification['type_seance'])
    return cible


def _cible_depuis(modification) -> Dict:
    cible = dict(modification.get('cible') or {})
    if modification.get('discipline'):
        cible.setdefault('discipline', modification['discipline'])
    if modification.get('type_seance'):
        cible.setdefault('type_seance', modification['type_seance'])
    if modification.get('jour_cible'):
        cible.setdefault('jour', modification['jour_cible'])
    return cible


# ------------------------------------------------------------------
# Construction / résumé de lignes
# ------------------------------------------------------------------

def _ligne_repos(colonnes) -> Dict:
    row = {colonne: '' for colonne in colonnes}
    row[COL_DISCIPLINE] = 'Repos'
    row[COL_TYPE] = 'Repos'
    row[COL_DETAILS] = 'Repos'
    row[COL_DUREE] = '0'
    row[COL_JOURNEE] = EMOJI_JOURNEE['repos']
    return row


def _resume(row) -> Dict:
    return {
        'discipline': row.get(COL_DISCIPLINE, ''),
        'type': row.get(COL_TYPE, ''),
        'duree': row.get(COL_DUREE, ''),
    }


def _resume_complet(jour_bloc, row) -> Dict:
    return {
        'semaine': jour_bloc['semaine'],
        'jour': jour_bloc['jour'],
        'date': jour_bloc['date'],
        **_resume(row),
    }


def _construire_ligne(discipline, type_canonique, duree, details, colonnes) -> Dict:
    libelle, cle = _DEFAUTS_TYPE.get(
        (discipline, type_canonique), _DEFAUTS_TYPE[('CAP', TYPE_ENDURANCE)]
    )
    difficulte = get_difficulte(cle)
    row = {colonne: '' for colonne in colonnes}
    row[COL_DISCIPLINE] = discipline
    row[COL_TYPE] = libelle
    row[COL_DETAILS] = details or f"{libelle} ({duree} min)"
    row[COL_DUREE] = str(int(duree))
    row[COL_JOURNEE] = EMOJI_JOURNEE.get(difficulte, EMOJI_JOURNEE['endurance'])
    return row


def _est_protegee(row) -> bool:
    type_l = str(row.get(COL_TYPE, '')).lower()
    return row.get(COL_DISCIPLINE, '') == 'Course' or any(
        mot in type_l for mot in ('compétition', 'competition', 'objectif')
    )


def _mettre_a_jour_duree_details(row, ancienne, nouvelle):
    details = row.get(COL_DETAILS, '')
    if f"({ancienne} min)" in details:
        row[COL_DETAILS] = details.replace(f"({ancienne} min)", f"({nouvelle} min)")


# ------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------

def _action_ajouter(modification, jours, colonnes, contexte, resultat):
    dates = _dates_pour(modification, contexte)
    if not dates:
        resultat['erreurs'].append('AJOUTER : aucune date cible résolue.')
        return
    discipline = modification['discipline']
    type_canonique = modification.get('type_seance') or TYPE_ENDURANCE
    duree = int(modification.get('duree') or 45)
    for date_iso in dates:
        jour_bloc = _trouver_jour(jours, date_iso)
        if jour_bloc is None:
            resultat['conflits'].append(f"AJOUTER : date {date_iso} hors du plan.")
            continue
        if discipline in ('CAP', 'Vélo', 'Natation') and any(
            _normalise_discipline(r.get(COL_DISCIPLINE, '')) == discipline
            for r in jour_bloc['rows']
        ):
            resultat['conflits'].append(
                f"AJOUTER : {discipline} déjà planifié le {date_iso}."
            )
            continue
        ligne = _construire_ligne(
            discipline, type_canonique, duree, modification.get('details'), colonnes
        )
        jour_bloc['rows'].append(ligne)
        resultat['apercu'].append({
            'avant': None,
            'apres': _resume_complet(jour_bloc, ligne),
            'raison': modification.get('raison'),
        })
        resultat['modifications_appliquees'] += 1


def _action_deplacer(modification, jours, colonnes, contexte, resultat):
    cible = _cible_source(modification)
    dates_source = _dates_pour(
        modification, contexte, utiliser_jour=False, utiliser_date=False
    )
    matches = _chercher(jours, cible, dates_source or None)
    if not matches:
        resultat['erreurs'].append('DEPLACER : séance introuvable.')
        return
    if len(matches) > 1:
        resultat['ambiguites'].append({
            'message': 'Plusieurs séances correspondent à la demande.',
            'candidats': [_resume_complet(m['jour_bloc'], m['row']) for m in matches],
        })
        return
    source = matches[0]
    date_iso = None
    if modification.get('date_cible'):
        date_iso = _iso(modification['date_cible'])
    elif modification.get('jour_cible'):
        semaine = _semaine_par_label(contexte, source['jour_bloc']['semaine'])
        if semaine is None or semaine['lundi'] is None:
            resultat['erreurs'].append('DEPLACER : semaine cible sans date.')
            return
        date_iso = (
            semaine['lundi'] + timedelta(days=JOURS.index(modification['jour_cible']))
        ).strftime('%Y-%m-%d')
    if not date_iso:
        resultat['erreurs'].append('DEPLACER : cible absente (date ou jour requis).')
        return

    cible_bloc = _trouver_jour(jours, date_iso)
    if cible_bloc is None:
        resultat['conflits'].append(f"DEPLACER : date {date_iso} hors du plan.")
        return
    if cible_bloc is source['jour_bloc']:
        return
    discipline = _normalise_discipline(source['row'].get(COL_DISCIPLINE, ''))
    if discipline in ('CAP', 'Vélo', 'Natation') and any(
        _normalise_discipline(r.get(COL_DISCIPLINE, '')) == discipline
        for r in cible_bloc['rows']
    ):
        resultat['conflits'].append(
            f"DEPLACER : {discipline} déjà planifié le {date_iso}."
        )
        return

    avant = _resume_complet(source['jour_bloc'], source['row'])
    source['jour_bloc']['rows'].remove(source['row'])
    if not source['jour_bloc']['rows']:
        source['jour_bloc']['rows'].append(_ligne_repos(colonnes))
    cible_bloc['rows'].append(source['row'])
    apres = _resume_complet(cible_bloc, source['row'])
    resultat['apercu'].append({'avant': avant, 'apres': apres,
                               'raison': modification.get('raison')})
    resultat['modifications_appliquees'] += 1


def _action_remplacer(modification, jours, colonnes, contexte, resultat):
    cible = _cible_depuis(modification)
    matches = _chercher(jours, cible, _dates_pour(modification, contexte) or None)
    if not matches:
        resultat['erreurs'].append('REMPLACER : séance introuvable.')
        return
    if len(matches) > 1:
        resultat['ambiguites'].append({
            'message': 'Plusieurs séances correspondent à la demande.',
            'candidats': [_resume_complet(m['jour_bloc'], m['row']) for m in matches],
        })
        return
    match = matches[0]
    row = match['row']
    avant = _resume_complet(match['jour_bloc'], row)
    discipline = _normalise_discipline(row.get(COL_DISCIPLINE, ''))
    type_canonique = modification.get('type_seance')
    if type_canonique:
        libelle, cle = _DEFAUTS_TYPE.get(
            (discipline, type_canonique), _DEFAUTS_TYPE.get(
                (discipline, TYPE_ENDURANCE), ('Endurance', 'endurance'))
        )
        duree = int(modification.get('duree') or _entier(row.get(COL_DUREE, '0')))
        row[COL_TYPE] = libelle
        row[COL_DETAILS] = modification.get('details') or f"{libelle} ({duree} min)"
        row[COL_DUREE] = str(duree)
        row[COL_JOURNEE] = EMOJI_JOURNEE.get(get_difficulte(cle), EMOJI_JOURNEE['endurance'])
    else:
        if modification.get('duree') is not None:
            row[COL_DUREE] = str(int(modification['duree']))
        if modification.get('details'):
            row[COL_DETAILS] = modification['details']
    resultat['apercu'].append({'avant': avant,
                               'apres': _resume_complet(match['jour_bloc'], row)})
    resultat['modifications_appliquees'] += 1


def _action_supprimer(modification, jours, colonnes, contexte, resultat):
    cible = _cible_depuis(modification)
    matches = _chercher(jours, cible, _dates_pour(modification, contexte) or None)
    if not matches:
        resultat['erreurs'].append('SUPPRIMER : séance introuvable.')
        return
    for match in matches:
        if _est_protegee(match['row']):
            resultat['conflits'].append(
                "SUPPRIMER : une compétition ne peut pas être supprimée automatiquement."
            )
            continue
        avant = _resume_complet(match['jour_bloc'], match['row'])
        match['jour_bloc']['rows'].remove(match['row'])
        if not match['jour_bloc']['rows']:
            match['jour_bloc']['rows'].append(_ligne_repos(colonnes))
        resultat['apercu'].append({'avant': avant, 'apres': None,
                                   'raison': modification.get('raison')})
        resultat['modifications_appliquees'] += 1


def _action_modifier_duree(modification, jours, colonnes, contexte, resultat):
    cible = _cible_depuis(modification)
    matches = _chercher(jours, cible, _dates_pour(modification, contexte) or None)
    if not matches:
        resultat['erreurs'].append('MODIFIER_DUREE : séance introuvable.')
        return
    for match in matches:
        row = match['row']
        ancienne = _entier(row.get(COL_DUREE, '0'))
        if modification.get('duree') is not None:
            nouvelle = int(modification['duree'])
        else:
            nouvelle = ancienne + int(modification.get('duree_delta') or 0)
        avant = _resume_complet(match['jour_bloc'], row)
        row[COL_DUREE] = str(nouvelle)
        _mettre_a_jour_duree_details(row, ancienne, nouvelle)
        resultat['apercu'].append({'avant': avant,
                                   'apres': _resume_complet(match['jour_bloc'], row)})
        resultat['modifications_appliquees'] += 1


def _action_modifier_details(modification, jours, colonnes, contexte, resultat):
    cible = _cible_depuis(modification)
    matches = _chercher(jours, cible, _dates_pour(modification, contexte) or None)
    if not matches:
        resultat['erreurs'].append('MODIFIER_DETAILS : séance introuvable.')
        return
    for match in matches:
        row = match['row']
        avant = _resume_complet(match['jour_bloc'], row)
        if modification.get('details_mode') == DETAILS_AJOUTER:
            row[COL_DETAILS] = f"{row.get(COL_DETAILS, '')} | {modification['details']}"
        else:
            row[COL_DETAILS] = modification['details']
        resultat['apercu'].append({'avant': avant,
                                   'apres': _resume_complet(match['jour_bloc'], row)})
        resultat['modifications_appliquees'] += 1


def _action_modifier_frequence(modification, jours, colonnes, contexte, resultat):
    cible = _cible_depuis(modification)
    dates = _dates_pour(modification, contexte)
    matches = _chercher(jours, cible, dates or None)
    if not matches:
        resultat['erreurs'].append('MODIFIER_FREQUENCE : aucune séance correspondante.')
        return
    for match in matches:
        row = match['row']
        avant = _resume_complet(match['jour_bloc'], row)
        if modification.get('duree') is not None:
            ancienne = _entier(row.get(COL_DUREE, '0'))
            row[COL_DUREE] = str(int(modification['duree']))
            _mettre_a_jour_duree_details(row, ancienne, int(modification['duree']))
        if modification.get('details'):
            row[COL_DETAILS] = modification['details']
        resultat['apercu'].append({'avant': avant,
                                   'apres': _resume_complet(match['jour_bloc'], row)})
        resultat['modifications_appliquees'] += 1


def _action_ajouter_ressource(modification, jours, colonnes, entetes, contexte, resultat):
    _ajouter_colonne(colonnes, entetes, jours, COL_RESSOURCES)
    dates = _dates_pour(modification, contexte)
    type_canonique = modification.get('type_seance')
    cible = _cible_depuis(modification)
    if not type_canonique:
        type_canonique = cible.get('type_seance')
    ressources = [str(url).strip() for url in modification.get('ressources', []) if str(url).strip()]
    if not dates:
        resultat['erreurs'].append('AJOUTER_RESSOURCE : aucune date cible résolue.')
        return

    for date_iso in dates:
        jour_bloc = _trouver_jour(jours, date_iso)
        if jour_bloc is None:
            resultat['conflits'].append(f"AJOUTER_RESSOURCE : date {date_iso} hors du plan.")
            continue
        jour_nom = modification.get('jour_cible') or jour_bloc['jour']
        if type_canonique and jour_nom != jour_bloc['jour']:
            continue
        candidats = [
            row for row in jour_bloc['rows']
            if type_canonique and _type_correspond(row, type_canonique)
        ]
        if candidats:
            for row in candidats:
                avant = _resume_complet(jour_bloc, row)
                existantes = [r for r in str(row.get(COL_RESSOURCES, '')).split(' | ') if r]
                nouvelles = existantes + [r for r in ressources if r not in existantes]
                row[COL_RESSOURCES] = ' | '.join(nouvelles)
                resultat['apercu'].append({'avant': avant,
                                           'apres': _resume_complet(jour_bloc, row),
                                           'ressources': ressources})
                resultat['modifications_appliquees'] += 1
        elif type_canonique == TYPE_RENFORCEMENT:
            ligne = _construire_ligne(
                'Renforcement', TYPE_RENFORCEMENT, int(modification.get('duree') or 30),
                modification.get('details'), colonnes,
            )
            ligne[COL_RESSOURCES] = ' | '.join(ressources)
            jour_bloc['rows'].append(ligne)
            resultat['apercu'].append({'avant': None,
                                       'apres': _resume_complet(jour_bloc, ligne),
                                       'ressources': ressources})
            resultat['modifications_appliquees'] += 1
        else:
            resultat['conflits'].append(
                f"AJOUTER_RESSOURCE : aucune séance {type_canonique} le {date_iso}."
            )


# ------------------------------------------------------------------
# Point d'entrée déterministe
# ------------------------------------------------------------------

def executer_demande(chemin_csv, demande, disponibilites=None,
                     date_reference=None, ecrire=False,
                     chemin_sortie=None) -> Dict:
    """Applique une demande structurée.

    - ``ecrire=False`` : prévisualisation (aucune écriture définitive).
    - ``ecrire=True``  : écrit le CSV seulement si la validation passe.

    Retour : {'resultat': 'OK'|'AMBIGU'|'CONFLIT'|'INVALIDE'|'ERREUR_SCHEMA',
              'apercu', 'ambiguites', 'conflits', 'erreurs', 'validation',
              'modifications_appliquees', 'chemin'}.
    """
    demande_normalisee = normaliser_demande(demande)
    resultat = {
        'resultat': 'OK',
        'categorie': None,
        'question': None,
        'questions': [],
        'apercu': [],
        'ambiguites': [],
        'conflits': [],
        'erreurs': list(demande_normalisee['erreurs']),
        'validation': None,
        'modifications_appliquees': 0,
        'chemin': chemin_csv,
    }
    if demande_normalisee['erreurs']:
        resultat['resultat'] = 'INVALIDE'
        return resultat
    if not demande_normalisee['modifications']:
        resultat['resultat'] = 'INVALIDE'
        resultat['erreurs'].append('Aucune modification fournie.')
        return resultat

    # Information indispensable manquante -> question ciblée (aucune écriture).
    if demande_normalisee.get('questions'):
        resultat['resultat'] = 'CLARIFICATION_REQUISE'
        resultat['categorie'] = 'INFO_MANQUANTE'
        resultat['questions'] = [q['question'] for q in demande_normalisee['questions']]
        resultat['question'] = resultat['questions'][0]
        return resultat

    # Incompréhension explicite (l'interprétation n'a pas compris la consigne).
    for modification in demande_normalisee['modifications']:
        if modification['action'] == ACTION_INCOMPRIS or not modification.get('compris', True):
            resultat['resultat'] = 'CLARIFICATION_REQUISE'
            resultat['categorie'] = 'INCOMPRIS'
            resultat['question'] = modification.get('question') or (
                'Pouvez-vous préciser la modification souhaitée '
                '(durée, intensité, type de séance ou contenu) ?'
            )
            return resultat

    # Ambiguïté signalée par l'interprétation (ex. période indéterminée).
    for modification in demande_normalisee['modifications']:
        if modification.get('periode_ambigue'):
            resultat['resultat'] = 'CLARIFICATION_REQUISE'
            resultat['categorie'] = 'PERIODE'
            resultat['question'] = modification.get('question') or (
                'Voulez-vous appliquer cette modification uniquement cette semaine '
                "ou jusqu'à la fin du plan ?"
            )
            return resultat
        if modification.get('ambigu'):
            resultat['resultat'] = 'CLARIFICATION_REQUISE'
            resultat['categorie'] = 'AMBIGU'
            resultat['question'] = modification.get('question') or (
                'La demande est ambiguë. Pouvez-vous la préciser ?'
            )
            return resultat

    try:
        colonnes, entetes, jours = _lire_blocs(chemin_csv)
    except Exception as erreur:
        resultat['resultat'] = 'ERREUR_SCHEMA'
        resultat['erreurs'].append(f'CSV illisible : {erreur}')
        return resultat

    contexte = _construire_contexte(jours, date_reference)

    for modification in demande_normalisee['modifications']:
        action = modification['action']
        if action == ACTION_AJOUTER:
            _action_ajouter(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_DEPLACER:
            _action_deplacer(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_REMPLACER:
            _action_remplacer(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_SUPPRIMER:
            _action_supprimer(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_MODIFIER_DUREE:
            _action_modifier_duree(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_MODIFIER_DETAILS:
            _action_modifier_details(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_MODIFIER_FREQUENCE:
            _action_modifier_frequence(modification, jours, colonnes, contexte, resultat)
        elif action == ACTION_AJOUTER_RESSOURCE:
            _action_ajouter_ressource(
                modification, jours, colonnes, entetes, contexte, resultat
            )

    if resultat['ambiguites']:
        resultat['resultat'] = 'AMBIGU'
        resultat['categorie'] = 'AMBIGU'
        resultat['question'] = resultat['ambiguites'][0].get(
            'message', 'Plusieurs séances correspondent. Laquelle souhaitez-vous modifier ?'
        )
        return resultat
    if resultat['conflits']:
        resultat['resultat'] = 'CONFLIT'
        return resultat
    if resultat['erreurs']:
        resultat['resultat'] = 'ERREUR_SCHEMA' if not resultat['apercu'] else 'CONFLIT'
        return resultat
    if resultat['modifications_appliquees'] == 0:
        resultat['resultat'] = 'OK'
        return resultat

    chemin_temp = _ecrire_temp(colonnes, entetes, jours, chemin_csv)
    validation = valider_plan_csv(chemin_temp, disponibilites)
    resultat['validation'] = validation
    depot = get_plan_repository()
    if not validation['valide']:
        depot.supprimer_plan(chemin_temp)
        resultat['resultat'] = 'INVALIDE'
        resultat['erreurs'] = list(validation['erreurs'])
        return resultat

    if ecrire:
        cible = chemin_sortie or chemin_csv
        depot.remplacer_plan(chemin_temp, cible)
        resultat['chemin'] = cible
    else:
        depot.supprimer_plan(chemin_temp)
    resultat['resultat'] = 'OK'
    return resultat


def previsualiser_modifications(chemin_csv, demande, disponibilites=None,
                                date_reference=None) -> Dict:
    """Prévisualisation AVANT / APRÈS sans aucune écriture."""
    return executer_demande(
        chemin_csv, demande, disponibilites=disponibilites,
        date_reference=date_reference, ecrire=False,
    )


def appliquer_modifications_structurees(chemin_csv, demande, disponibilites=None,
                                        date_reference=None,
                                        chemin_sortie=None) -> Dict:
    """Applique et écrit le CSV seulement si le résultat est valide."""
    return executer_demande(
        chemin_csv, demande, disponibilites=disponibilites,
        date_reference=date_reference, ecrire=True, chemin_sortie=chemin_sortie,
    )
