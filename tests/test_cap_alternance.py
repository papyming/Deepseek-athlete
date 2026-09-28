# ============================================================
# FICHIER: tests/test_cap_alternance.py
# RÔLE: Alternance COURTE / LONGUE des intensités CAP (conception
#       initiale du générateur). Tests déterministes.
# ============================================================

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from planificateur.generateur.seances import (  # noqa: E402
    classer_intensite_cap,
    choisir_seance_qualite,
    CATEGORIE_COURTE,
    CATEGORIE_LONGUE,
)
from planificateur.generateur.semaine import (  # noqa: E402
    generer_plan_complet,
    extraire_courses,
)
from planificateur.chargeur import (  # noqa: E402
    charger_profil,
    charger_disponibilites,
    charger_seances,
)

_BASE = Path('outputs/Base par athlète')


def _s(distance, temps_effort_sec=60.0, type_seance='VMA'):
    return {'distance': distance, 'temps_effort_sec': temps_effort_sec, 'type': type_seance}


# 1. CLASSIFICATION
def test_classification_courte_par_distance():
    for distance in (100, 200, 300, 400):
        assert classer_intensite_cap(_s(distance)) == CATEGORIE_COURTE


def test_classification_longue_par_distance():
    for distance in (500, 600, 700, 800, 1000, 2000, 3000):
        assert classer_intensite_cap(_s(distance)) == CATEGORIE_LONGUE


def test_400m_reste_court_meme_au_dela_de_3_minutes():
    # aucune équivalence durée <-> distance : 400 m = COURTE même si > 3 min
    assert classer_intensite_cap(_s(400, temps_effort_sec=240.0)) == CATEGORIE_COURTE


def test_sans_distance_duree_effort_departage():
    assert classer_intensite_cap({'temps_effort_sec': 181.0}) == CATEGORIE_LONGUE
    assert classer_intensite_cap({'temps_effort_sec': 180.0}) == CATEGORIE_COURTE
    assert classer_intensite_cap({'temps_effort_sec': 120.0}) == CATEGORIE_COURTE


def test_sprint_et_30_30_courts():
    assert classer_intensite_cap({'type': 'Sprint', 'details': 'Sprint 10x'}) == CATEGORIE_COURTE
    assert classer_intensite_cap({'type': '30/30', 'details': '30"/30"'}) == CATEGORIE_COURTE


# 2-5. ALTERNANCE DE BASE
def test_courte_suivie_de_longue():
    liste = [_s(400), _s(700)]
    donnee, reference = choisir_seance_qualite(
        liste, [], 2, 18.0, None, 3, 0, derniere_categorie=CATEGORIE_COURTE
    )
    assert donnee['distance'] == 700
    assert donnee['categorie_intensite'] == CATEGORIE_LONGUE
    assert donnee['alternance_impossible'] is False


def test_longue_suivie_de_courte():
    liste = [_s(400), _s(700)]
    # index force sur 700 (LONGUE) ; l'alternative COURTE doit être choisie
    donnee, _ = choisir_seance_qualite(
        liste, [], 2, 18.0, None, 3, 1, derniere_categorie=CATEGORIE_LONGUE
    )
    assert donnee['distance'] == 400
    assert donnee['categorie_intensite'] == CATEGORIE_COURTE


def test_courte_suivie_de_courte_avec_alternative():
    liste = [_s(400), _s(700)]
    donnee, _ = choisir_seance_qualite(
        liste, [], 2, 18.0, None, 3, 0, derniere_categorie=CATEGORIE_COURTE
    )
    assert donnee['categorie_intensite'] != CATEGORIE_COURTE


def test_longue_suivie_de_longue_avec_alternative():
    liste = [_s(400), _s(700)]
    donnee, _ = choisir_seance_qualite(
        liste, [], 2, 18.0, None, 3, 1, derniere_categorie=CATEGORIE_LONGUE
    )
    assert donnee['categorie_intensite'] != CATEGORIE_LONGUE


# 6. VMA 700 -> VC 700 : bascule vers une alternative VC COURTE
def test_vma700_puis_vc700_avec_alternative():
    vma = [_s(700, type_seance='VMA')]
    vc = [_s(700, type_seance='VC'), _s(300, type_seance='VC')]
    donnee, reference = choisir_seance_qualite(
        vma, vc, 2, 18.0, 14.0, 3, 0, derniere_categorie=CATEGORIE_LONGUE
    )
    assert reference == 'VC'
    assert donnee['distance'] == 300
    assert donnee['categorie_intensite'] == CATEGORIE_COURTE
    assert donnee['alternance_impossible'] is False


# 7. AUCUNE ALTERNATIVE -> séance conservée + alerte
def test_aucune_alternative_conserve_et_alerte():
    donnee, _ = choisir_seance_qualite(
        [_s(700)], [_s(700)], 2, 18.0, 14.0, 3, 0,
        derniere_categorie=CATEGORIE_LONGUE,
    )
    assert donnee['categorie_intensite'] == CATEGORIE_LONGUE
    assert donnee['alternance_impossible'] is True


def _profil(vma=18.0, vc=14.0):
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': vma, 'vc': vc},
        'sport_principal': 'Triathlon',
    }


def _dispo(cap):
    return {
        'CAP': list(cap), 'Velo': [], 'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }


def test_alerte_presente_dans_le_plan_si_aucune_alternative():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), _profil(),
        _dispo(['Lundi', 'Mardi', 'Jeudi']),
        [_s(700, type_seance='VMA')], [_s(700, type_seance='VC')],
    )
    alertes = [a for semaine in plan for a in semaine.get('alertes_placement', [])]
    assert any('Alternance des intensités CAP' in alerte for alerte in alertes)


# 8. AUTRES DISCIPLINES NON AFFECTÉES
def test_autres_disciplines_non_affectees():
    profil = _profil()
    dispo = {
        'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), profil, dispo,
        [_s(300, type_seance='VMA')], [_s(300, type_seance='VC')],
    )
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance.get('categorie_intensite'):
                    assert seance['discipline'] == 'CAP'


# 9-10. Athlete_I : aucune succession interdite (VMA/VC)
def test_alternance_cap_vma_vc_sur_profil_reel():
    dossier = _BASE / 'Athlete_I'
    if not dossier.exists():
        pytest.skip('Profil Athlete_I indisponible')
    profil = charger_profil(str(dossier))
    disponibilites = charger_disponibilites(str(dossier))
    if not profil or not disponibilites:
        pytest.skip('Données Athlete_I indisponibles')
    date_objectif = datetime.strptime(profil['date_objectif'], '%Y-%m-%d')
    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    seances_vma = charger_seances(str(dossier), 'VMA') if vma else []
    seances_vc = charger_seances(str(dossier), 'VC') if vc else []
    courses = extraire_courses(profil.get('courses_preparatoires', []), date_objectif.year)

    plan = generer_plan_complet(
        datetime(2026, 8, 1), date_objectif, profil, disponibilites,
        seances_vma, seances_vc, courses,
    )

    sequence = []
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance.get('discipline') == 'CAP' and seance.get('categorie_intensite'):
                    sequence.append(seance)
    assert sequence, 'Aucune intensité CAP VMA/VC trouvée'
    for precedente, suivante in zip(sequence, sequence[1:]):
        if precedente['categorie_intensite'] == suivante['categorie_intensite']:
            # une succession identique n'est tolérée que si aucune alternative
            assert precedente.get('alternance_impossible') or \
                suivante.get('alternance_impossible'), (
                    precedente['type'], precedente['categorie_intensite'],
                    suivante['type'], suivante['categorie_intensite'],
                )
