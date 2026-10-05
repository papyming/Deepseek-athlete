from abc import ABC
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Flowable

from src.core.physiology.profil import analyser_profil
from src.export.sections_pdf import ajouter_section_ratio
from src.export.tables_pdf import generer_tableau_vc
from src.planificateur.chargeur import (
    charger_profil,
    charger_disponibilites,
    charger_seances,
)
from src.planificateur.export_csv import _format_date_for_user
from src.planificateur.export_pdf_plan import (
    _format_date_for_user as format_pdf_date,
    exporter_pdf_plan,
    _couleur_seance,
    _couleur_contrainte,
    _commandes_fond,
    _commandes_separateur_weekend,
    _commandes_surlignage_weekend,
    _indices_debut_week_end,
    _commandes_separateur_semaine,
    _indices_debut_semaine,
    _grouper_semaines_par_page,
    _periode_groupe,
    _tableau_semaines,
    _symbole_intensite,
    _creer_styles_pdf,
    _construire_tableau,
    _bloc_legende_intensite,
    _spans_semaines,
    _styles_tableau,
    _bloc_page_pedagogique,
    _tableau_intensites,
    _tableau_types_seance,
    _exemple_depuis_plan,
    _hauteur_flowables,
    FormeIntensite,
    FormeCoche,
    SYMBOLES_INTENSITE,
    FORMES_INTENSITE,
    SYMBOLE_FONT,
    LEGENDE_INTENSITE,
    TYPES_SEANCE,
    EXPLICATIONS_INTENSITE,
    TITRE_PEDAGOGIQUE,
    REPERES_ATHLETE,
    LARGEURS_COLONNES,
    PROPORTIONS_COLONNES,
    COULEUR_SEPARATEUR_SEMAINE,
    TAILLE_PAGE_SEMAINES,
    MARGE_GAUCHE,
    MARGE_DROITE,
    MARGE_HAUT,
    MARGE_BAS,
    COULEUR_ENDURANCE,
    COULEUR_INTENSE,
    COULEUR_SEUIL,
    COULEUR_FARTLEK,
    COULEUR_LONGUE,
    COULEUR_COMPETITION,
    COULEUR_RENFORCEMENT,
    COULEUR_CONTRAINTE_NORMALE,
    COULEUR_CONTRAINTE_IMPORTANTE,
    COULEUR_WEEKEND,
    COULEUR_SEPARATEUR_WEEKEND,
    JOURS_WEEKEND,
)
from src.planificateur.plan_csv import (
    trouver_csv_courant,
    construire_plan_depuis_csv,
    lister_csv_plans,
    resoudre_selection,
    LIGNES_ENTETE,
)
from src.planificateur.validateur_plan import valider_plan_csv
from src.planificateur.exports_csv_source import (
    exporter_pdf_depuis_csv,
    exporter_intervals_depuis_csv,
    exporter_exports_depuis_csv,
)
from src.planificateur.agent_plan_csv import (
    FournisseurModifications,
    appliquer_modifications_csv,
    previsualiser_modifications,
    appliquer_modifications_structurees,
    executer_demande,
)
from src.planificateur.contrat_modifications import normaliser_demande
from src.planificateur.export_csv import exporter_plan_csv
from src.planificateur.volume import (
    calculer_unites_hebdo,
    total_unites_hebdo,
    unites_depuis_minutes,
)
from src.planificateur.generateur.semaine import (
    _selectionner_jours_biquotidien,
    _selectionner_jours_avec_longue,
    _trier_jours_preferes,
    _appliquer_regle_cap_velo,
    MESSAGE_CAP_VELO,
    generer_plan_complet,
    extraire_courses,
)
from src.utils.parsers import (
    parser_bi_quotidien,
    selectionner_jours_tri_quadri,
    parser_date_debut,
)
from src.utils.validators import analyser_jours_disponibles, valider_coherence_biquotidien


def test_tri_quadri_accepts_three(monkeypatch):
    assert parser_bi_quotidien('Oui tri') is None


def test_tri_quadri_rejects_zero_and_empty_is_none(monkeypatch):
    assert parser_bi_quotidien('Oui tri') is None


def test_parser_bi_quotidien_non_returns_zero():
    assert parser_bi_quotidien('Non') == 0


def test_parser_bi_quotidien_une_fois_returns_one():
    assert parser_bi_quotidien('Oui 1 fois') == 1


def test_parser_bi_quotidien_deux_fois_returns_two():
    assert parser_bi_quotidien('Oui 2 fois') == 2


def test_parser_bi_quotidien_trois_fois_returns_three():
    assert parser_bi_quotidien('Oui 3 fois') == 3


def test_parser_bi_quotidien_autre_ou_a_voir_returns_none():
    assert parser_bi_quotidien('Autre') is None
    assert parser_bi_quotidien('Autre a voir avec l\'entraineur') is None


def test_tri_quadri_without_source_days_returns_empty_selection():
    assert selectionner_jours_tri_quadri({}) == {}


def test_tri_quadri_proposes_only_source_days(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt='': '1,2')
    source = {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []}
    assert selectionner_jours_tri_quadri(source) == source


def test_tri_quadri_selects_one_source_day_and_keeps_discipline(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt='': '1')
    source = {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []}
    assert selectionner_jours_tri_quadri(source) == {
        'CAP': [], 'Velo': ['Lundi'], 'Natation': []
    }


def test_tri_quadri_same_day_multiple_disciplines_counts_once(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda prompt='': '1')
    source = {'CAP': ['Jeudi'], 'Velo': [], 'Natation': ['Jeudi']}
    selection = selectionner_jours_tri_quadri(source)
    assert selection == source
    assert len({jour for jours in selection.values() for jour in jours}) == 1


def test_tri_quadri_count_is_used_for_declared_days():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    disponibilites = {
        'CAP': ['Lundi', 'Mercredi', 'Vendredi'],
        'Velo': ['Lundi', 'Mercredi', 'Vendredi'],
        'Natation': [],
        'bi_quotidien_nb': 3,
        'bi_quotidien': {
            'CAP': ['Lundi', 'Mercredi', 'Vendredi'],
            'Velo': ['Lundi', 'Mercredi', 'Vendredi'],
            'Natation': []
        }
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3),
        datetime(2026, 12, 13),
        profil,
        disponibilites
    )
    semaine = plan[0]
    assert semaine['bi_quotidien_nb'] == 3
    assert semaine['jours_biquotidien'] == ['Lundi', 'Mercredi', 'Vendredi']
    assert [jour['jour'] for jour in semaine['jours'] if jour['biquotidien']] == [
        'Lundi', 'Mercredi', 'Vendredi'
    ]


def test_tri_quadri_none_does_not_invent_days():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    disponibilites = {
        'CAP': ['Lundi'],
        'Velo': ['Lundi'],
        'Natation': [],
        'bi_quotidien_nb': None,
        'bi_quotidien': {'CAP': ['Lundi'], 'Velo': ['Lundi'], 'Natation': []}
    }
    semaine = generer_plan_complet(
        datetime(2026, 8, 3),
        datetime(2026, 8, 9),
        profil,
        disponibilites
    )[0]
    assert semaine['bi_quotidien_nb'] is None
    assert semaine['jours_biquotidien'] == []
    assert not any(jour['biquotidien'] for jour in semaine['jours'])


def test_start_date_is_first_plan_date():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 1),
        datetime(2026, 8, 8),
        profil,
        {'CAP': [], 'Velo': [], 'Natation': []}
    )
    # CDC §324 : la semaine est ancrée sur le lundi ; si le plan débute en
    # cours de semaine, les jours précédant le début restent présents et vides.
    assert plan[0]['jours'][0]['jour'] == 'Lundi'
    assert plan[0]['jours'][0]['date'] == '2026-07-27'
    assert any(jour['date'] == '2026-08-01' for jour in plan[0]['jours'])


def test_past_plan_start_generates_sessions_before_today():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }
    plan = generer_plan_complet(datetime(2026, 8, 1), datetime(2026, 12, 15), profil, {'CAP': ['Lundi'], 'Velo': [], 'Natation': []})
    jour = next(jour for semaine in plan for jour in semaine['jours'] if jour['date'] == '2026-08-03')
    assert any(seance['discipline'] == 'CAP' for seance in jour['seances'])


def test_future_plan_start_still_generates_sessions():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }
    plan = generer_plan_complet(datetime(2026, 10, 1), datetime(2026, 12, 15), profil, {'CAP': ['Lundi'], 'Velo': [], 'Natation': []})
    jour = next(jour for semaine in plan for jour in semaine['jours'] if jour['date'] == '2026-10-05')
    assert any(seance['discipline'] == 'CAP' for seance in jour['seances'])


def test_sport_principal_comes_from_profile():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3),
        datetime(2026, 8, 9),
        profil,
        {'CAP': ['Lundi'], 'Velo': ['Mardi'], 'Natation': []}
    )
    assert plan[0]['sport_principal'] == 'Course à pied'


def test_ratio_at_79_percent_has_no_contradictory_alert():
    result = analyser_profil(
        {'10km': 14.5, 'semi': 14.1, 'marathon': 13.1},
        vma=18.0,
        vc=14.22
    )
    assert result['profil'] == 'Endurant'
    assert result['ratio'] == 14.22 / 18.0
    assert not any('Ratio VC/VMA' in alerte for alerte in result['alertes'])


def test_exports_format_dates_for_users():
    assert _format_date_for_user('2026-08-01') == '01/08/2026'
    assert format_pdf_date('2026-08-01') == '01/08/2026'


def test_pdf_keeps_vc_title_with_table():
    styles = getSampleStyleSheet()
    physio = SimpleNamespace(tableau_vc=[{
        'distance_effort': 200,
        'vitesse_effort': 14.0,
        'temps_effort': '00:51',
        'distance_recup': 50,
        'temps_recup': '00:26'
    }])
    story = []
    generer_tableau_vc(story, physio, styles['Normal'], styles['Heading2'])
    assert isinstance(story[0], KeepTogether)


def _bi_availability(value):
    return analyser_jours_disponibles({
        'CAP': 'Lundi Mardi Mercredi Jeudi',
        'Velo': 'Lundi Mardi',
        'Natation': 'Lundi Mardi',
        'Bi-quotidien': value
    })


def test_biquotidien_coherence_matrix():
    cases = [
        ('Athlete_A', 1, 'Mardi CAP', 'coherent'),
        ('Athlete_B', 3, 'CAP=Jeudi Nat=Lundi', 'contradiction'),
        ('Athlete_K', 3, 'CAP=Jeudi Velo=Lundi', 'contradiction'),
        ('Athlete_M', 0, 'Lundi', 'contradiction'),
        ('Athlete_J', 1, 'Nat=Lundi CAP=Mercredi', 'coherent'),
        ('Athlete_H', 2, 'CAP=Jeudi Velo=Mardi', 'coherent'),
        ('Athlete_F', 3, 'CAP=Lundi Nat=Mardi', 'contradiction'),
    ]
    for nom, capacite, jours, statut in cases:
        disponibilites = _bi_availability(jours)
        disponibilites['bi_quotidien_nb'] = capacite
        resultat = valider_coherence_biquotidien(disponibilites, nom, str(capacite))
        assert resultat['statut'] == statut, (nom, resultat)


def test_biquotidien_capacity_less_than_two_days_is_valid():
    disponibilites = _bi_availability('Nat=Lundi CAP=Mercredi')
    disponibilites['bi_quotidien_nb'] = 1
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_I', 'Oui 1 fois')
    assert resultat['valide'] is True
    assert resultat['statut'] == 'coherent'


def test_biquotidien_capacity_equal_to_two_days_is_valid():
    disponibilites = _bi_availability('Nat=Lundi CAP=Mercredi')
    disponibilites['bi_quotidien_nb'] = 2
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_J', 'Oui 2 fois')
    assert resultat['valide'] is True
    assert resultat['statut'] == 'coherent'


def test_biquotidien_capacity_greater_than_two_days_is_blocked():
    disponibilites = _bi_availability('Nat=Lundi CAP=Mercredi')
    disponibilites['bi_quotidien_nb'] = 3
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_B', 'Oui 3 fois')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'contradiction'


def test_biquotidien_zero_with_one_day_is_blocked():
    disponibilites = _bi_availability('Lundi')
    disponibilites['bi_quotidien_nb'] = 0
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_M', 'Non')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'contradiction'


def test_biquotidien_positive_capacity_without_any_day_is_insufficient():
    disponibilites = _bi_availability('')
    disponibilites['bi_quotidien_nb'] = 2
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete', 'Oui 2 fois')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'insuffisant'


def test_biquotidien_zero_capacity_without_any_day_is_coherent():
    disponibilites = _bi_availability('')
    disponibilites['bi_quotidien_nb'] = 0
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete', 'Non')
    assert resultat['valide'] is True
    assert resultat['statut'] == 'coherent'


def test_biquotidien_other_requires_confirmation():
    disponibilites = _bi_availability('')
    disponibilites['bi_quotidien_nb'] = None
    resultat = valider_coherence_biquotidien(
        disponibilites,
        'Athlete_C',
        "Autre a voir avec l'entraineur"
    )
    assert resultat['statut'] == 'a_confirmer'
    assert resultat['valide'] is False


def test_planification_is_blocked_before_generation(monkeypatch, tmp_path):
    from src.planificateur import main_plan

    monkeypatch.setattr(main_plan, 'charger_profil', lambda path: {
        'nom': 'Athlete_M',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    })
    disponibilites = _bi_availability('Lundi')
    disponibilites['bi_quotidien_nb'] = 0
    disponibilites['bi_quotidien_capacite_brute'] = 'Non'
    monkeypatch.setattr(main_plan, 'charger_disponibilites', lambda path: disponibilites)
    monkeypatch.setattr(
        main_plan,
        'generer_plan_complet',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('generation should be blocked'))
    )

    resultat = main_plan.planifier_athlete(str(tmp_path))
    assert 'error' in resultat
    assert resultat['bi_quotidien_validation']['statut'] == 'contradiction'


def test_contradiction_has_explicit_message():
    disponibilites = _bi_availability('Lundi')
    disponibilites['bi_quotidien_nb'] = 0
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_M', 'Non')
    assert resultat['statut'] == 'contradiction'
    assert 'Athlete_M' in resultat['message']
    assert 'Capacite declaree : Non' in resultat['message']
    assert 'Contradiction' in resultat['message']


def test_missing_day_message_is_explicit():
    for nom, jours in [
        ('Athlete_B', 'CAP=Jeudi Nat=Lundi'),
        ('Athlete_F', 'CAP=Lundi Nat=Mardi')
    ]:
        disponibilites = _bi_availability(jours)
        disponibilites['bi_quotidien_nb'] = 3
        resultat = valider_coherence_biquotidien(disponibilites, nom, 'Oui 3 fois par semaine')
        assert resultat['statut'] == 'contradiction'
        assert nom in resultat['message']
        assert '2' in resultat['message']
        assert '3' in resultat['message']
        assert 'capacité de 3 supérieure' in resultat['message']


def test_source_and_tri_quadri_selection_separate():
    source = {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []}
    selected = {'CAP': [], 'Velo': ['Lundi'], 'Natation': []}
    disponibilites = {
        'CAP': ['Jeudi'],
        'Velo': ['Lundi'],
        'Natation': [],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': source,
        'bi_quotidien_tri_quadri': selected,
        'bi_quotidien_nb': 1
    }
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_K', 'Tri/quadri')
    assert resultat['valide'] is True
    assert resultat['jours_source'] == ['Jeudi', 'Lundi']
    assert resultat['jours_tri_quadri'] == ['Lundi']
    assert resultat['jours_biquotidien_restants'] == ['Jeudi']
    assert 'Lundi' in resultat['message']
    assert 'Jeudi' in resultat['message']


def test_tri_quadri_selection_outside_source_is_blocked():
    resultat = valider_coherence_biquotidien({
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []},
        'bi_quotidien_tri_quadri': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []},
        'bi_quotidien_nb': 1
    }, 'Athlete_K', 'Tri/quadri')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'contradiction'
    assert 'Mardi' in resultat['message']


def test_can_select_both_source_days_as_tri_quadri():
    disponibilites = {
        'CAP': ['Jeudi'],
        'Velo': ['Lundi'],
        'Natation': [],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []},
        'bi_quotidien_tri_quadri': {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []},
        'bi_quotidien_nb': 2
    }
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_K', 'Tri/quadri')
    assert resultat['valide'] is True
    assert resultat['jours_biquotidien_restants'] == []


def test_tri_quadri_empty_source_is_blocked():
    disponibilites = {
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': [], 'Velo': [], 'Natation': []},
        'bi_quotidien_tri_quadri': {},
        'bi_quotidien_nb': None
    }
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_K', 'Tri/quadri')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'insuffisant'


def _disponibilites_tri_quadri(selection):
    return {
        'CAP': ['Jeudi'],
        'Velo': ['Lundi'],
        'Natation': [],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {
            'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []
        },
        'bi_quotidien_tri_quadri': selection,
        'bi_quotidien_nb': len({
            jour for jours in selection.values() for jour in jours
        })
    }


def _triathlon_profil():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }


def test_selected_one_day_leaves_thursday_as_biquotidien():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 9), _triathlon_profil(),
        _disponibilites_tri_quadri({'CAP': [], 'Velo': ['Lundi'], 'Natation': []})
    )
    assert plan[0]['jours_biquotidien'] == ['Lundi']
    assert plan[0]['jours_biquotidien_normaux'] == ['Jeudi']
    jeudi = next(jour for jour in plan[0]['jours'] if jour['jour'] == 'Jeudi')
    assert jeudi['biquotidien'] is False


def test_selected_both_days_has_no_biquotidien_remaining():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 9), _triathlon_profil(),
        _disponibilites_tri_quadri({'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []})
    )
    assert plan[0]['jours_biquotidien'] == ['Lundi', 'Jeudi']


def test_biquotidien_selection_rotates_when_capacity_is_lower_than_available_days():
    disponibilites = {
        'CAP': ['Mercredi', 'Vendredi'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {
            'CAP': ['Mercredi', 'Vendredi'], 'Velo': [], 'Natation': []
        }
    }
    assert _selectionner_jours_biquotidien(disponibilites, 1) == ['Mercredi']
    assert _selectionner_jours_biquotidien(disponibilites, 2) == ['Vendredi']


def test_objectif_natation_ne_supprime_pas_cap_disponible():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2027-01-10',
        'competition_objectif': 'Finale de natation',
        'format_competition': 'Natation',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }
    plan = generer_plan_complet(
        datetime(2027, 1, 4), datetime(2027, 1, 10), profil,
        {'CAP': ['Lundi'], 'Velo': [], 'Natation': ['Mardi']}
    )
    disciplines = _disciplines_planifiees(plan[0])
    assert 'Natation' in disciplines
    assert 'CAP' in disciplines


def test_invalid_tri_quadri_selection_is_blocked_before_generation(monkeypatch, tmp_path):
    from src.planificateur import main_plan

    monkeypatch.setattr(main_plan, 'charger_profil', lambda path: {
        'nom': 'Athlete_K',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    })
    monkeypatch.setattr(main_plan, 'charger_disponibilites', lambda path: {
        'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': [],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []},
        'bi_quotidien_tri_quadri': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []},
        'bi_quotidien_nb': 1
    })
    monkeypatch.setattr(
        main_plan,
        'generer_plan_complet',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('generation should be blocked'))
    )

    resultat = main_plan.planifier_athlete(str(tmp_path))
    assert 'error' in resultat
    assert resultat['bi_quotidien_validation']['statut'] == 'contradiction'


def _disciplines_planifiees(semaine):
    return {
        seance['discipline']
        for jour in semaine['jours']
        for seance in jour['seances']
    }


def _compte_disciplines(plan):
    compte = {}
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                discipline = seance['discipline']
                if discipline == 'Vélo':
                    discipline = 'Velo'
                compte[discipline] = compte.get(discipline, 0) + 1
    return compte


def _plan_avec_objectif(sport_principal, competition_objectif, format_competition, disponibilites):
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2026-12-15',
        'competition_objectif': competition_objectif,
        'format_competition': format_competition,
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': sport_principal
    }
    return generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), profil, disponibilites
    )


def _profil_course_a_pied():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }


def test_biquotidien_day_without_second_session_is_not_flagged():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 9), _triathlon_profil(),
        _disponibilites_tri_quadri({'CAP': [], 'Velo': ['Lundi'], 'Natation': []})
    )
    semaine = plan[0]
    assert semaine['jours_biquotidien'] == ['Lundi']
    lundi = next(jour for jour in semaine['jours'] if jour['jour'] == 'Lundi')
    assert len([s for s in lundi['seances'] if s['discipline'] != 'Repos']) < 2
    assert lundi['biquotidien'] is False
    for jour in semaine['jours']:
        if jour['biquotidien']:
            assert len([s for s in jour['seances'] if s['discipline'] != 'Repos']) >= 2


def test_biquotidien_source_outside_availability_is_contradiction():
    disponibilites = {
        'CAP': ['Mardi', 'Mercredi', 'Jeudi', 'Samedi', 'Dimanche'],
        'Velo': ['Samedi', 'Dimanche'],
        'Natation': [],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mercredi', 'Vendredi'], 'Velo': [], 'Natation': []}
    }
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_I', 'Oui 1 fois')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'contradiction'
    assert 'Vendredi' in resultat['message']


def test_biquotidien_source_hors_disponibilite_is_contradiction():
    disponibilites = {
        'CAP': ['Mardi', 'Jeudi'],
        'Velo': ['Jeudi'],
        'Natation': ['Mercredi'],
        'bi_quotidien_nb': 3,
        'bi_quotidien': {'CAP': ['Lundi'], 'Velo': [], 'Natation': ['Mardi']}
    }
    resultat = valider_coherence_biquotidien(disponibilites, 'Athlete_F', 'Oui 3 fois par semaine')
    assert resultat['valide'] is False
    assert resultat['statut'] == 'contradiction'
    assert 'Lundi' in resultat['message']


def test_biquotidien_selection_can_vary_across_weeks():
    disponibilites = {
        'CAP': ['Mercredi', 'Vendredi'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mercredi', 'Vendredi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 23), _profil_course_a_pied(), disponibilites
    )
    selections = [semaine['jours_biquotidien'] for semaine in plan]
    assert len(selections) >= 2
    assert len({tuple(selection) for selection in selections}) >= 2
    for selection in selections:
        assert len(selection) <= 1
        assert set(selection) <= {'Mercredi', 'Vendredi'}


def test_biquotidien_selection_never_outside_availability():
    disponibilites = {
        'CAP': ['Mercredi', 'Vendredi'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 2,
        'bi_quotidien': {'CAP': ['Mercredi', 'Vendredi', 'Samedi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 23), _profil_course_a_pied(), disponibilites
    )
    for semaine in plan:
        assert set(semaine['jours_biquotidien']) <= {'Mercredi', 'Vendredi'}
        assert all(jour['jour'] != 'Samedi' for jour in semaine['jours'] if jour['biquotidien'])


def test_objectif_principal_is_ignored_for_discipline():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': 'Natation',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), profil,
        {'CAP': ['Lundi', 'Jeudi'], 'Velo': [], 'Natation': ['Mardi']}
    )
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Natation', 0) > 0
    assert compte.get('CAP', 0) > compte.get('Natation', 0)


def test_format_competition_marathon_is_cap():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2026-12-15',
        'competition_objectif': 'Marathon de Lyon 2027',
        'format_competition': 'Marathon',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), profil,
        {'CAP': ['Lundi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    )
    disciplines = _disciplines_planifiees(plan[0])
    assert 'CAP' in disciplines
    assert any(d in disciplines for d in ['Velo', 'Vélo'])
    assert 'Natation' in disciplines


def test_format_competition_semi_marathon_is_cap():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2026-12-15',
        'competition_objectif': 'Semi-marathon de Lyon 2026',
        'format_competition': 'Semi-marathon',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), profil,
        {'CAP': ['Lundi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    )
    disciplines = _disciplines_planifiees(plan[0])
    assert 'CAP' in disciplines
    assert any(d in disciplines for d in ['Velo', 'Vélo'])
    assert 'Natation' in disciplines


def test_objectif_cap_outranks_triathlon_sport_principal():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2026-12-15',
        'competition_objectif': 'Semi-marathon de Lyon 2026',
        'format_competition': 'Semi-marathon',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), profil,
        {'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    )
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Velo', 0) > 0
    assert compte.get('Natation', 0) > 0
    assert compte.get('CAP', 0) >= compte.get('Velo', 0)
    assert compte.get('CAP', 0) >= compte.get('Natation', 0)


def test_date_objectif_controls_plan_end():
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 9, 30), _profil_course_a_pied(),
        {'CAP': ['Lundi'], 'Velo': [], 'Natation': []}
    )
    toutes_les_dates = [jour['date'] for semaine in plan for jour in semaine['jours']]
    assert all(date <= '2026-09-30' for date in toutes_les_dates)
    assert max(toutes_les_dates) == '2026-09-30'


def test_objectif_marathon_triathlon_conserve_les_disciplines_complementaires():
    disponibilites = {'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    plan = _plan_avec_objectif('Triathlon', 'Marathon', 'Marathon', disponibilites)
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Velo', 0) > 0
    assert compte.get('Natation', 0) > 0
    assert compte.get('CAP', 0) >= compte.get('Velo', 0)
    assert compte.get('CAP', 0) >= compte.get('Natation', 0)


def test_objectif_marathon_course_a_pied_conserve_les_disciplines_complementaires():
    disponibilites = {'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    plan = _plan_avec_objectif('Course à pied', 'Marathon', 'Marathon', disponibilites)
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Velo', 0) > 0
    assert compte.get('Natation', 0) > 0
    assert compte.get('CAP', 0) >= compte.get('Velo', 0)
    assert compte.get('CAP', 0) >= compte.get('Natation', 0)


def test_objectif_triathlon_conserve_les_trois_disciplines():
    disponibilites = {'CAP': ['Lundi'], 'Velo': ['Mardi'], 'Natation': ['Mercredi']}
    plan = _plan_avec_objectif('Triathlon', 'Triathlon', 'Olympique', disponibilites)
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Velo', 0) > 0
    assert compte.get('Natation', 0) > 0


def test_sport_principal_sans_objectif_conserve_le_velo():
    disponibilites = {'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi'], 'Natation': []}
    plan = _plan_avec_objectif('Course à pied', '', '', disponibilites)
    compte = _compte_disciplines(plan)
    assert compte.get('CAP', 0) > 0
    assert compte.get('Velo', 0) > 0
    assert compte.get('CAP', 0) >= compte.get('Velo', 0)


def test_planifier_n_appelle_qu_un_seul_export_csv(monkeypatch):
    from src import main as main_module

    plan_factice = {'athlete': 'Athlete_A', 'semaines': []}
    appels = {'csv': 0}

    def planifier_athlete_avec_export(athlete_dir, date_debut):
        main_module.exporter_plan_csv(plan_factice, 'outputs/plans/Athlete_A')
        return plan_factice

    monkeypatch.setattr(main_module, 'choisir_athletes', lambda: ['Athlete_A'])
    monkeypatch.setattr(main_module, 'planifier_athlete', planifier_athlete_avec_export)
    monkeypatch.setattr(main_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr(main_module.os, 'makedirs', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_module,
        'exporter_plan_csv',
        lambda plan, plan_dir: appels.__setitem__('csv', appels['csv'] + 1) or 'plan.csv'
    )
    monkeypatch.setattr(main_module, 'exporter_pdf_plan', lambda plan, plan_dir: 'plan.pdf')
    monkeypatch.setattr('builtins.input', lambda prompt='': '')

    main_module.planifier()

    assert appels['csv'] == 1


def test_le_plan_utilise_le_libelle_canonique_velo():
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '2026-10-01',
        'competition_objectif': 'Olympique de Lyon 2026',
        'format_competition': 'Olympique',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 10, 1), profil,
        {'CAP': ['Lundi', 'Jeudi'], 'Velo': ['Mardi', 'Samedi'], 'Natation': ['Mercredi']}
    )
    disciplines = {
        seance['discipline']
        for semaine in plan
        for jour in semaine['jours']
        for seance in jour['seances']
    }
    assert 'Vélo' in disciplines
    assert 'Velo' not in disciplines


_SPORT_DISC = ('CAP', 'Vélo', 'Velo', 'Natation')


def _jours_doubles_sport(plan):
    doubles = {}
    for semaine in plan:
        for jour in semaine['jours']:
            sports = [s['discipline'] for s in jour['seances'] if s['discipline'] in _SPORT_DISC]
            if len(sports) >= 2:
                doubles[jour['date']] = (jour['jour'], sports)
    return doubles


def _profil_triathlon():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Triathlon'
    }


def test_conserve_cap_natation_jeudi_avec_contrainte():
    disponibilites = {
        'CAP': ['Mardi', 'Jeudi'],
        'Velo': ['Mercredi'],
        'Natation': ['Jeudi'],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    jeudis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Jeudi']
    assert jeudis
    for jour in jeudis:
        disciplines = [s['discipline'] for s in jour['seances'] if s['discipline'] in _SPORT_DISC]
        assert 'CAP' in disciplines
        assert 'Natation' in disciplines
        assert jour['contrainte_planification'] is True
        assert jour['contrainte']['active'] is True
        assert jour['contrainte']['nb_seances_sport'] == 2
        assert jour['contrainte']['capacite_normale'] == 1
        assert jour['contrainte']['depassement'] == 1
        assert 'Natation' in jour['contrainte']['disciplines']
        assert jour['contrainte']['message']


def test_conserve_les_doubles_necessaires_avec_contrainte():
    disponibilites = {
        'CAP': ['Lundi', 'Mercredi', 'Vendredi'],
        'Velo': ['Mercredi'],
        'Natation': ['Jeudi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    assert _jours_doubles_sport(plan)
    mercredis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Mercredi']
    assert mercredis
    for jour in mercredis:
        disciplines = [s['discipline'] for s in jour['seances'] if s['discipline'] in _SPORT_DISC]
        assert 'CAP' in disciplines
        assert any(d in disciplines for d in ('Vélo', 'Velo'))
        assert jour['contrainte_planification'] is True
        assert jour['contrainte']['depassement'] == 1


def test_conserve_les_doubles_hors_candidats_avec_contrainte():
    disponibilites = {
        'CAP': ['Lundi', 'Mercredi', 'Vendredi', 'Samedi'],
        'Velo': ['Lundi', 'Jeudi'],
        'Natation': ['Mardi', 'Jeudi', 'Samedi'],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Lundi', 'Mercredi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    doubles_hors_candidats = [
        jour
        for semaine in plan
        for jour in semaine['jours']
        if jour['jour'] in ('Jeudi', 'Samedi')
        and len([s for s in jour['seances'] if s['discipline'] in _SPORT_DISC]) >= 2
    ]
    assert doubles_hors_candidats
    for jour in doubles_hors_candidats:
        assert jour['contrainte_planification'] is True
        assert jour['contrainte']['depassement'] >= 1


def test_jour_biquotidien_autorise_sans_contrainte():
    disponibilites = {
        'CAP': ['Mercredi', 'Jeudi'],
        'Velo': ['Jeudi'],
        'Natation': [],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Jeudi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    jeudis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Jeudi']
    assert jeudis
    for jour in jeudis:
        assert jour['contrainte']['nb_seances_sport'] == 2
        assert jour['contrainte_planification'] is False


def test_jour_tri_quadri_autorise_sans_contrainte():
    disponibilites = {
        'CAP': ['Jeudi'],
        'Velo': ['Jeudi'],
        'Natation': ['Jeudi'],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Jeudi'], 'Natation': ['Jeudi']},
        'bi_quotidien_tri_quadri': {'CAP': ['Jeudi'], 'Velo': ['Jeudi'], 'Natation': ['Jeudi']},
        'bi_quotidien_nb': 1
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    jeudis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Jeudi']
    assert jeudis
    for jour in jeudis:
        assert jour['contrainte']['nb_seances_sport'] == 3
        assert jour['contrainte_planification'] is False


def test_renforcement_ne_declenche_pas_de_contrainte():
    disponibilites = {
        'CAP': ['Lundi', 'Jeudi'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    jours_renforcement = [
        jour
        for semaine in plan
        for jour in semaine['jours']
        if any(s['discipline'] == 'Renforcement' for s in jour['seances'])
    ]
    assert jours_renforcement
    for jour in jours_renforcement:
        assert jour['contrainte']['nb_seances_sport'] <= 1
        assert jour['contrainte_planification'] is False


def test_preference_jours_velo_long_le_week_end():
    assert _trier_jours_preferes('Velo', ['Mercredi', 'Samedi'])[0] == 'Samedi'


def test_preference_jours_natation_intensite_en_semaine():
    assert _trier_jours_preferes('Natation', ['Samedi', 'Mardi'])[0] == 'Mardi'


def test_preference_jours_repli_si_aucun_creneau_prefere():
    assert set(_trier_jours_preferes('Natation', ['Samedi', 'Dimanche'])) == {'Samedi', 'Dimanche'}


def test_preference_jours_ne_cree_pas_de_jour_hors_disponibilite():
    assert set(_trier_jours_preferes('Velo', ['Lundi', 'Mercredi'])) <= {'Lundi', 'Mercredi'}


def test_seance_longue_velo_placee_le_week_end_quand_possible():
    disponibilites = {
        'CAP': [],
        'Velo': ['Mardi', 'Mercredi', 'Jeudi', 'Samedi'],
        'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    jours_velo = {
        jour['jour']
        for jour in plan[0]['jours']
        if any(s['discipline'] in ('Vélo', 'Velo') for s in jour['seances'])
    }
    assert 'Samedi' in jours_velo
    samedi = next(jour for jour in plan[0]['jours'] if jour['jour'] == 'Samedi')
    assert any(s['type'] == 'Sortie longue Z2' for s in samedi['seances'])


def test_seance_intensite_natation_placee_en_semaine_quand_possible():
    disponibilites = {
        'CAP': [],
        'Velo': [],
        'Natation': ['Mardi', 'Mercredi', 'Vendredi', 'Samedi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    jours_natation = {
        jour['jour']
        for jour in plan[0]['jours']
        if any(s['discipline'] == 'Natation' for s in jour['seances'])
    }
    assert jours_natation
    assert 'Samedi' not in jours_natation
    assert jours_natation <= {'Mardi', 'Vendredi', 'Mercredi'}


def test_repli_sur_jour_disponible_sans_creneau_prefere():
    disponibilites = {
        'CAP': [],
        'Velo': ['Samedi', 'Dimanche'],
        'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    jours_velo = {
        jour['jour']
        for jour in plan[0]['jours']
        if any(s['discipline'] in ('Vélo', 'Velo') for s in jour['seances'])
    }
    assert jours_velo
    assert jours_velo <= {'Samedi', 'Dimanche'}


def test_preference_ne_supprime_ni_jour_disponible_ni_seance():
    disponibilites = {
        'CAP': [],
        'Velo': ['Mercredi', 'Samedi'],
        'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    jours_velo = {
        jour['jour']
        for jour in plan[0]['jours']
        if any(s['discipline'] in ('Vélo', 'Velo') for s in jour['seances'])
    }
    assert jours_velo == {'Mercredi', 'Samedi'}


def test_unite_1h_cap_egale_1_unite():
    assert unites_depuis_minutes('CAP', 60) == 1.0


def test_unite_1h_natation_egale_1_unite():
    assert unites_depuis_minutes('Natation', 60) == 1.0


def test_unite_1h_velo_egale_demi_unite():
    assert unites_depuis_minutes('Velo', 60) == 0.5


def test_unite_2h_velo_egale_1_unite():
    assert unites_depuis_minutes('Velo', 120) == 1.0


def test_unite_45min_cap_egale_90min_velo():
    assert unites_depuis_minutes('CAP', 45) == unites_depuis_minutes('Velo', 90)


def test_unite_libelle_velo_accentue():
    assert unites_depuis_minutes('Vélo', 120) == 1.0


def test_unite_zero_minute_et_discipline_inconnue():
    assert unites_depuis_minutes('CAP', 0) == 0.0
    assert unites_depuis_minutes('Inconnue', 60) == 0.0


def test_calculer_unites_hebdo_et_total():
    volumes = {'CAP': 120, 'Natation': 60, 'Velo': 180}
    assert calculer_unites_hebdo(volumes) == {'CAP': 2.0, 'Natation': 1.0, 'Velo': 1.5}
    assert total_unites_hebdo(volumes) == 4.5


def test_jour_biquotidien_autorise_peut_rester_a_une_seance():
    disponibilites = {
        'CAP': ['Lundi', 'Mardi', 'Jeudi', 'Dimanche'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    mardis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Mardi']
    assert mardis
    for jour in mardis:
        assert len([s for s in jour['seances'] if s['discipline'] in _SPORT_DISC]) == 1


def test_jour_tri_quadri_non_casse():
    disponibilites = {
        'CAP': ['Lundi', 'Jeudi', 'Samedi'],
        'Velo': ['Mercredi'],
        'Natation': ['Vendredi'],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Lundi'], 'Natation': []},
        'bi_quotidien_tri_quadri': {'CAP': ['Jeudi'], 'Velo': [], 'Natation': []},
        'bi_quotidien_nb': 1
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_course_a_pied(), disponibilites
    )
    assert plan[0]['jours_biquotidien'] == ['Jeudi']
    jeudis = [jour for semaine in plan for jour in semaine['jours'] if jour['jour'] == 'Jeudi']
    assert jeudis
    for jour in jeudis:
        nb_sport = len([s for s in jour['seances'] if s['discipline'] in _SPORT_DISC])
        assert 1 <= nb_sport <= 3


def test_aucune_seance_sportive_sur_jour_indisponible():
    disponibilites = {
        'CAP': ['Mardi', 'Jeudi'],
        'Velo': ['Mercredi'],
        'Natation': ['Jeudi'],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []}
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 13), _profil_triathlon(), disponibilites
    )
    dispo_par_discipline = {
        'CAP': set(disponibilites['CAP']),
        'Velo': set(disponibilites['Velo']),
        'Natation': set(disponibilites['Natation'])
    }
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                discipline = 'Velo' if seance['discipline'] in ('Vélo', 'Velo') else seance['discipline']
                if discipline in dispo_par_discipline:
                    assert jour['jour'] in dispo_par_discipline[discipline], (jour['date'], jour['jour'], discipline)


# ============================================================
# PLACEMENT : intensité en semaine / séance longue le week-end
# ============================================================

def _seances_vma_fictives():
    return [{
        'distance_effort': 300,
        'vitesse_effort': 15.0,
        'temps_effort': '01:00',
        'temps_effort_sec': 60,
        'nb_rep': 6,
        'distance_recup': 100,
        'temps_recup': '01:00',
        'temps_recup_sec': 60,
    }]


def _jours_intenses(plan, discipline):
    jours = []
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance.get('discipline') != discipline:
                    continue
                if seance.get('cle') is True or seance.get('difficulte') in ('intense', 'seuil'):
                    jours.append((jour['date'], jour['jour']))
    return jours


def _profil_cap_avec_vma():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': None},
        'sport_principal': 'Course à pied',
    }


def _disponibilites_avec_bi(cap, velo, natation):
    return {
        'CAP': list(cap),
        'Velo': list(velo),
        'Natation': list(natation),
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }


def test_1_intensite_cap_evite_le_samedi_si_jour_de_semaine_disponible():
    disponibilites = _disponibilites_avec_bi(
        ['Mardi', 'Jeudi', 'Samedi', 'Dimanche'], [], []
    )
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_cap_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    intensites = _jours_intenses(plan, 'CAP')
    assert intensites
    assert all(jour not in ('Samedi', 'Dimanche') for _, jour in intensites)
    assert any(jour in ('Mardi', 'Jeudi') for _, jour in intensites)


def test_2_quota_intensite_cap_non_consomme_par_velo_ou_natation():
    disponibilites = _disponibilites_avec_bi(
        ['Mardi', 'Jeudi'], ['Mercredi'], ['Vendredi']
    )
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_cap_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    cap = _jours_intenses(plan, 'CAP')
    velo = _jours_intenses(plan, 'Vélo')
    natation = _jours_intenses(plan, 'Natation')
    assert velo or natation
    assert cap
    assert all(jour in ('Mardi', 'Jeudi') for _, jour in cap)


def test_3_4_espacement_48h_et_continuite_entre_semaines():
    disponibilites = _disponibilites_avec_bi(
        ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi'], [], []
    )
    profil = _profil_cap_avec_vma()
    profil['niveau_estime'] = 'Avancé'
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2027, 6, 30),
        profil, disponibilites, _seances_vma_fictives(), []
    )

    semaines_multi = []
    for semaine in plan:
        dates = sorted(
            datetime.strptime(date, '%Y-%m-%d')
            for date, _ in _jours_intenses([semaine], 'CAP')
        )
        for precedente, suivante in zip(dates, dates[1:]):
            assert (suivante - precedente).days >= 2
        if len(dates) >= 2:
            semaines_multi.append(semaine['semaine_num'])
    assert semaines_multi

    dates = sorted(
        datetime.strptime(date, '%Y-%m-%d')
        for date, _ in _jours_intenses(plan, 'CAP')
    )
    assert len(dates) >= 2
    for precedente, suivante in zip(dates, dates[1:]):
        assert (suivante - precedente).days >= 2


def test_5_seance_longue_cap_privilegie_le_week_end():
    disponibilites = _disponibilites_avec_bi(['Mardi', 'Samedi'], [], [])
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_cap_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    samedi = next(jour for jour in plan[0]['jours'] if jour['jour'] == 'Samedi')
    assert any(
        seance['discipline'] == 'CAP' and seance['type'] == 'Sortie longue Z2'
        for seance in samedi['seances']
    )


def test_6_repli_intensite_week_end_si_aucun_jour_de_semaine():
    disponibilites = _disponibilites_avec_bi(['Samedi', 'Dimanche'], [], [])
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_cap_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    intensites = _jours_intenses(plan, 'CAP')
    assert intensites
    assert all(jour in ('Samedi', 'Dimanche') for _, jour in intensites)
    assert any(semaine.get('alertes_placement') for semaine in plan)


def test_7_repli_ne_cree_pas_de_jour_semaine_hors_disponibilite():
    disponibilites = _disponibilites_avec_bi(['Samedi', 'Dimanche'], [], [])
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_cap_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    jours_cap = {
        jour['jour']
        for semaine in plan
        for jour in semaine['jours']
        for seance in jour['seances']
        if seance['discipline'] == 'CAP'
    }
    assert jours_cap
    assert jours_cap <= {'Samedi', 'Dimanche'}


def test_8_placement_conserve_le_tri_quadri():
    disponibilites = {
        'CAP': ['Jeudi'], 'Velo': ['Jeudi'], 'Natation': ['Jeudi'],
        'bi_quotidien_mode': 'tri_quadri',
        'bi_quotidien_source': {'CAP': ['Jeudi'], 'Velo': ['Jeudi'], 'Natation': ['Jeudi']},
        'bi_quotidien_tri_quadri': {'CAP': ['Jeudi'], 'Velo': ['Jeudi'], 'Natation': ['Jeudi']},
        'bi_quotidien_nb': 1,
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15), _profil_triathlon(), disponibilites
    )
    jeudis = [
        jour for semaine in plan for jour in semaine['jours']
        if jour['jour'] == 'Jeudi' and not jour.get('hors_plan')
    ]
    assert jeudis
    for jour in jeudis:
        nb_sport = len([s for s in jour['seances'] if s['discipline'] in _SPORT_DISC])
        assert nb_sport == 3
        assert jour['contrainte_planification'] is False


def test_9_placement_conserve_les_contraintes_signalees():
    disponibilites = {
        'CAP': ['Mardi', 'Jeudi'], 'Velo': ['Mercredi'], 'Natation': ['Jeudi'],
        'bi_quotidien_nb': 1,
        'bi_quotidien': {'CAP': ['Mardi'], 'Velo': [], 'Natation': []},
    }
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15), _profil_triathlon(), disponibilites
    )
    jeudis = [
        jour for semaine in plan for jour in semaine['jours']
        if jour['jour'] == 'Jeudi' and not jour.get('hors_plan')
    ]
    assert jeudis
    for jour in jeudis:
        disciplines = [s['discipline'] for s in jour['seances'] if s['discipline'] in _SPORT_DISC]
        assert 'CAP' in disciplines
        assert 'Natation' in disciplines
        assert jour['contrainte_planification'] is True
        assert jour['contrainte']['active'] is True
        assert jour['contrainte']['message']


_BASE_ATHLETES = Path('outputs/Base par athlète')


def _verifier_placement_profil(plan, disponibilites, nom):
    dispo = {
        'CAP': set(disponibilites.get('CAP', [])),
        'Velo': set(disponibilites.get('Velo', [])),
        'Natation': set(disponibilites.get('Natation', [])),
    }
    for semaine in plan:
        cap_jours = set()
        for jour in semaine['jours']:
            for seance in jour['seances']:
                discipline = 'Velo' if seance['discipline'] in ('Vélo', 'Velo') else seance['discipline']
                if discipline in dispo:
                    assert jour['jour'] in dispo[discipline], (nom, jour['date'], discipline)
                if discipline == 'CAP':
                    cap_jours.add(jour['jour'])

        for _, jour_intense in _jours_intenses([semaine], 'CAP'):
            if jour_intense in ('Samedi', 'Dimanche'):
                assert not (cap_jours - {'Samedi', 'Dimanche'}), (nom, semaine['date_debut'])

        # Une sortie longue ne doit pas être en semaine si un créneau week-end
        # est réellement disponible pour la discipline.
        for discipline, cle in (('CAP', 'CAP'), ('Vélo', 'Velo')):
            dispo_weekend = [j for j in dispo[cle] if j in ('Samedi', 'Dimanche')]
            if not dispo_weekend:
                continue
            for jour in semaine['jours']:
                for seance in jour['seances']:
                    if seance['discipline'] != discipline:
                        continue
                    if 'sortie longue' not in str(seance.get('type', '')).lower():
                        continue
                    assert jour['jour'] in ('Samedi', 'Dimanche'), (
                        nom, jour['date'], discipline
                    )


def test_10_les_profils_reels_respectent_le_placement():
    if not _BASE_ATHLETES.exists():
        pytest.skip('Profils réels indisponibles')
    dossiers = sorted(d for d in _BASE_ATHLETES.iterdir() if d.is_dir())
    if not dossiers:
        pytest.skip('Profils réels indisponibles')
    assert dossiers
    for dossier in dossiers:
        profil = charger_profil(str(dossier))
        disponibilites = charger_disponibilites(str(dossier))
        assert profil, dossier.name
        assert disponibilites, dossier.name
        try:
            date_objectif = datetime.strptime(profil['date_objectif'], '%Y-%m-%d')
        except (KeyError, TypeError, ValueError):
            pytest.skip(f"date objectif absente pour {dossier.name}")
        vma = profil.get('physiologie', {}).get('vma')
        vc = profil.get('physiologie', {}).get('vc')
        seances_vma = charger_seances(str(dossier), 'VMA') if vma else []
        seances_vc = charger_seances(str(dossier), 'VC') if vc else []
        plan = generer_plan_complet(
            datetime(2026, 8, 1), date_objectif, profil, disponibilites,
            seances_vma, seances_vc
        )
        _verifier_placement_profil(plan, disponibilites, dossier.name)
        dates = sorted(
            datetime.strptime(date, '%Y-%m-%d')
            for date, _ in _jours_intenses(plan, 'CAP')
        )
        for precedente, suivante in zip(dates, dates[1:]):
            assert (suivante - precedente).days >= 2, dossier.name


# ============================================================
# EXPORT PDF : export unique + coloration des séances
# ============================================================

def _plan_pdf_minimal():
    return {
        'athlete': 'Athlète Test',
        'date_debut': '2026-08-01',
        'date_objectif': '2026-08-31',
        'semaines': [{
            'num_affichage': 4,
            'emoji': '🟢',
            'jours': [{
                'jour': 'Lundi',
                'date': '2026-08-03',
                'contrainte': {
                    'active': True,
                    'capacite_normale': 1,
                    'message': 'Contrainte de test',
                },
                'seances': [
                    {'discipline': 'CAP', 'type': 'VMA', 'details': 'VMA (45 min)', 'duree': 45, 'difficulte': 'intense'},
                    {'discipline': 'Vélo', 'type': 'Seuil Z4', 'details': 'Seuil Z4 (80 min)', 'duree': 80, 'difficulte': 'seuil'},
                    {'discipline': 'Natation', 'type': 'Sortie longue Z2', 'details': 'Sortie longue Z2 (60 min)', 'duree': 60, 'difficulte': 'endurance'},
                ],
            }],
        }],
    }


def test_un_seul_pdf_par_athlete(monkeypatch):
    from src import main as main_module

    appels = {'planifications': 0, 'pdf': 0}

    def planifier_athlete_simule(athlete_dir, date_debut):
        appels['planifications'] += 1
        main_module.exporter_pdf_plan({'athlete': 'X', 'semaines': []}, 'plan_dir')
        return {'athlete': 'X', 'semaines': []}

    monkeypatch.setattr(main_module, 'choisir_athletes', lambda: ['Athlete_B'])
    monkeypatch.setattr(main_module, 'planifier_athlete', planifier_athlete_simule)
    monkeypatch.setattr(main_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr(main_module.os, 'makedirs', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_module, 'exporter_pdf_plan',
        lambda plan, plan_dir: appels.__setitem__('pdf', appels['pdf'] + 1) or 'plan.pdf'
    )
    monkeypatch.setattr('builtins.input', lambda prompt='': '')

    main_module.planifier()

    assert appels['planifications'] == 1
    assert appels['pdf'] == 1


def test_export_pdf_cree_un_fichier(tmp_path):
    chemin = exporter_pdf_plan(_plan_pdf_minimal(), str(tmp_path))
    assert chemin
    fichier = Path(chemin)
    assert fichier.exists()
    assert fichier.stat().st_size > 0
    assert fichier.suffix == '.pdf'


def test_couleurs_types_seances():
    cas = [
        ({'discipline': 'CAP', 'type': 'Endurance fondamentale Z2', 'difficulte': 'endurance'}, COULEUR_ENDURANCE),
        ({'discipline': 'CAP', 'type': 'Footing de récupération Z1', 'difficulte': 'recuperation'}, COULEUR_ENDURANCE),
        ({'discipline': 'CAP', 'type': 'VMA', 'difficulte': 'intense'}, COULEUR_INTENSE),
        ({'discipline': 'CAP', 'type': 'VC', 'difficulte': 'seuil'}, COULEUR_INTENSE),
        ({'discipline': 'CAP', 'type': "Test 3'/6'/12'", 'difficulte': 'intense'}, COULEUR_INTENSE),
        ({'discipline': 'CAP', 'type': 'Fartlek', 'difficulte': 'intense'}, COULEUR_FARTLEK),
        ({'discipline': 'Vélo', 'type': 'Seuil Z4', 'difficulte': 'seuil'}, COULEUR_SEUIL),
        ({'discipline': 'Natation', 'type': 'Technique + Seuil', 'difficulte': 'seuil'}, COULEUR_SEUIL),
        ({'discipline': 'CAP', 'type': 'Sortie longue Z2', 'difficulte': 'endurance'}, COULEUR_LONGUE),
        ({'discipline': 'Vélo', 'type': 'Sortie longue Z2', 'difficulte': 'endurance'}, COULEUR_LONGUE),
        ({'discipline': 'Course', 'type': 'Compétition intermédiaire', 'difficulte': 'course'}, COULEUR_COMPETITION),
        ({'discipline': 'Renforcement', 'type': 'Gainage', 'difficulte': 'endurance'}, COULEUR_RENFORCEMENT),
    ]
    for seance, attendu in cas:
        assert _couleur_seance(seance) == attendu, seance


def test_couleurs_seances_identiques_entre_disciplines():
    for discipline in ('CAP', 'Vélo', 'Natation'):
        assert _couleur_seance({'discipline': discipline, 'type': 'VMA', 'difficulte': 'intense'}) == COULEUR_INTENSE
        assert _couleur_seance({'discipline': discipline, 'type': 'Seuil Z4', 'difficulte': 'seuil'}) == COULEUR_SEUIL
        assert _couleur_seance({'discipline': discipline, 'type': 'Sortie longue Z2', 'difficulte': 'endurance'}) == COULEUR_LONGUE
        assert _couleur_seance({'discipline': discipline, 'type': 'Endurance Z2', 'difficulte': 'endurance'}) == COULEUR_ENDURANCE


def test_contrainte_prioritaire_sur_la_couleur_de_type():
    couleur_type = COULEUR_INTENSE
    normale = _couleur_contrainte({'active': True, 'capacite_normale': 1})
    importante = _couleur_contrainte({'active': True, 'capacite_normale': 2})
    assert normale == COULEUR_CONTRAINTE_NORMALE
    assert importante == COULEUR_CONTRAINTE_IMPORTANTE
    assert normale != couleur_type

    commandes = _commandes_fond([(1, couleur_type)], [(1, normale)])
    fonds = [c for c in commandes if c[0] == 'BACKGROUND']
    assert fonds[0] == ('BACKGROUND', (0, 1), (-1, 1), couleur_type)
    assert fonds[1] == ('BACKGROUND', (3, 1), (3, 1), normale)
    assert commandes.index(fonds[0]) < commandes.index(fonds[1])

    textes = [c for c in commandes if c[0] == 'TEXTCOLOR']
    assert textes == [('TEXTCOLOR', (3, 1), (3, 1), colors.darkred)]


def test_pdf_conserve_indicateur_et_section_contraintes(tmp_path):
    plan = _plan_pdf_minimal()
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    assert Path(chemin).exists()
    jour = plan['semaines'][0]['jours'][0]
    assert jour['contrainte']['active'] is True
    assert jour['contrainte']['message'] == 'Contrainte de test'


# ============================================================
# SORTIES LONGUES : priorité au week-end réellement disponible
# ============================================================

def test_selection_longue_quota_deux_conserve_le_dimanche():
    jours = _selectionner_jours_avec_longue('CAP', ['Mardi', 'Jeudi', 'Dimanche'], 2)
    assert len(jours) == 2
    assert 'Dimanche' in jours
    assert 'Mardi' in jours


def test_selection_longue_quota_trois_conserve_le_samedi():
    jours = _selectionner_jours_avec_longue(
        'CAP', ['Mardi', 'Jeudi', 'Lundi', 'Mercredi', 'Samedi'], 3
    )
    assert len(jours) == 3
    assert 'Samedi' in jours


def test_selection_longue_samedi_indisponible_dimanche_disponible():
    cap = _selectionner_jours_avec_longue('CAP', ['Mardi', 'Jeudi', 'Dimanche'], 2)
    assert 'Dimanche' in cap
    velo = _selectionner_jours_avec_longue('Velo', ['Lundi', 'Jeudi', 'Dimanche'], 2)
    assert 'Dimanche' in velo


def test_selection_longue_sans_week_end_repli_semaine():
    jours = _selectionner_jours_avec_longue('CAP', ['Mardi', 'Jeudi', 'Lundi'], 2)
    assert len(jours) == 2
    assert set(jours) <= {'Mardi', 'Jeudi', 'Lundi'}
    assert not (set(jours) & {'Samedi', 'Dimanche'})


def test_selection_longue_ne_cree_pas_de_jour_hors_disponibilite():
    cas = [
        ('CAP', ['Mardi', 'Jeudi', 'Dimanche'], 2),
        ('CAP', ['Mardi', 'Jeudi', 'Lundi', 'Mercredi', 'Samedi'], 3),
        ('CAP', ['Lundi', 'Mercredi', 'Vendredi'], 2),
        ('Velo', ['Lundi', 'Jeudi', 'Dimanche'], 2),
        ('Velo', ['Samedi', 'Dimanche'], 2),
    ]
    for discipline, disponibilites, quota in cas:
        jours = _selectionner_jours_avec_longue(discipline, disponibilites, quota)
        assert len(jours) <= quota
        assert set(jours) <= set(disponibilites)


def _profil_longue_avec_vma():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': None},
        'sport_principal': 'Course à pied',
    }


def test_plan_place_les_longues_le_dimanche_quand_disponible():
    disponibilites = _disponibilites_avec_bi(['Mardi', 'Jeudi', 'Dimanche'], [], [])
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        _profil_longue_avec_vma(), disponibilites, _seances_vma_fictives(), []
    )
    longues = [
        jour['jour']
        for semaine in plan
        for jour in semaine['jours']
        for seance in jour['seances']
        if seance['discipline'] == 'CAP' and seance['type'] == 'Sortie longue Z2'
    ]
    assert longues
    assert set(longues) == {'Dimanche'}


def test_profil_place_les_longues_le_dimanche():
    # CAP disponible Lun/Mar/Jeu/Dim : Dimanche doit accueillir toutes les longues.
    disponibilites = _disponibilites_avec_bi(['Lundi', 'Mardi', 'Jeudi', 'Dimanche'], [], [])
    profil = _profil_longue_avec_vma()
    profil['niveau_estime'] = 'Intermédiaire'
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15),
        profil, disponibilites, _seances_vma_fictives(), []
    )
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance['discipline'] == 'CAP' and seance['type'] == 'Sortie longue Z2':
                    assert jour['jour'] == 'Dimanche', (semaine['date_debut'], jour['jour'])
    # aucune séance CAP en dehors des disponibilités
    for semaine in plan:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance['discipline'] == 'CAP':
                    assert jour['jour'] in ('Lundi', 'Mardi', 'Jeudi', 'Dimanche')


# ============================================================
# A — AFFICHAGE COMPLET DES 7 JOURS (structure CDC, lundi -> dimanche)
# ============================================================

_JOURS_CDC = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def test_chaque_semaine_contient_7_jours_dans_l_ordre_lundi_dimanche():
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15), _profil_triathlon(),
        _disponibilites_avec_bi(['Lundi', 'Jeudi'], ['Mercredi'], ['Mardi'])
    )
    assert plan
    for semaine in plan:
        assert len(semaine['jours']) == 7
        assert [jour['jour'] for jour in semaine['jours']] == _JOURS_CDC


def test_semaine_partielle_debut_conserve_7_jours():
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 8, 15), _profil_triathlon(),
        _disponibilites_avec_bi(['Lundi'], [], [])
    )
    premiere = plan[0]
    assert len(premiere['jours']) == 7
    assert premiere['jours'][0]['jour'] == 'Lundi'
    # les jours précédant le début du plan restent présents mais vides
    hors_plan = [jour for jour in premiere['jours'] if jour.get('hors_plan')]
    assert hors_plan
    for jour in hors_plan:
        assert [s['discipline'] for s in jour['seances']] == ['Repos']


def test_semaine_partielle_fin_conserve_7_jours():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 9, 30), _profil_triathlon(),
        _disponibilites_avec_bi(['Lundi'], [], [])
    )
    derniere = plan[-1]
    assert len(derniere['jours']) == 7
    assert derniere['jours'][-1]['jour'] == 'Dimanche'
    apres_objectif = [jour for jour in derniere['jours'] if jour['date'] == '']
    assert apres_objectif
    for jour in apres_objectif:
        assert all(s['discipline'] == 'Repos' for s in jour['seances'])


def test_aucune_seance_artificielle_sur_jour_hors_plan():
    plan = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 8, 15), _profil_course_a_pied(),
        _disponibilites_avec_bi(['Lundi'], [], [])
    )
    for semaine in plan:
        for jour in semaine['jours']:
            if jour.get('hors_plan'):
                assert [s['discipline'] for s in jour['seances']] == ['Repos']


def test_jours_de_repos_presents_dans_le_plan():
    plan = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 8, 16), _profil_triathlon(),
        _disponibilites_avec_bi(['Lundi'], [], [])
    )
    assert any(
        any(s['discipline'] == 'Repos' for s in jour['seances'])
        for semaine in plan for jour in semaine['jours']
    )


def test_separateur_weekend_present_dans_les_commandes_pdf():
    indices = _indices_debut_week_end(_JOURS_CDC)
    assert indices == [5]
    commandes = _commandes_separateur_weekend(indices)
    assert len(commandes) == 1
    commande = commandes[0]
    assert commande[0] == 'LINEABOVE'
    assert commande[4] == COULEUR_SEPARATEUR_WEEKEND
    surlignage = _commandes_surlignage_weekend([5, 6])
    assert ('BACKGROUND', (1, 5), (1, 5), COULEUR_WEEKEND) in surlignage
    assert ('BACKGROUND', (1, 6), (1, 6), COULEUR_WEEKEND) in surlignage
    assert JOURS_WEEKEND == ('Samedi', 'Dimanche')


def test_export_pdf_avec_jour_de_repos_produit_un_fichier(tmp_path):
    plan = {
        'athlete': 'Athlète Test',
        'date_debut': '2026-08-01',
        'date_objectif': '2026-08-31',
        'semaines': [{
            'num_affichage': 1,
            'emoji': '🟢',
            'jours': [
                {
                    'jour': jour,
                    'date': f'2026-08-{index + 3:02d}',
                    'seances': ([{'discipline': 'CAP', 'type': 'Endurance Z2',
                                  'details': 'Endurance Z2 (45 min)', 'duree': 45,
                                  'difficulte': 'endurance'}]
                                if jour == 'Lundi'
                                else [{'discipline': 'Repos', 'type': 'Repos',
                                       'details': 'Repos', 'duree': 0,
                                       'difficulte': 'repos'}]),
                }
                for index, jour in enumerate(_JOURS_CDC)
            ],
        }],
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    assert chemin
    fichier = Path(chemin)
    assert fichier.exists()
    assert fichier.stat().st_size > 0


# ============================================================
# B — RÈGLE CAP + VÉLO LE MÊME JOUR (CAP <= 50 % du vélo)
# ============================================================

def _jour_cap_velo(duree_cap, duree_velo, type_cap='Endurance fondamentale Z2',
                   difficulte='endurance', cle=False):
    return {
        'jour': 'Mercredi',
        'date': '2026-08-05',
        'seances': [
            {
                'discipline': 'CAP',
                'type': type_cap,
                'details': f'{type_cap} ({duree_cap} min)',
                'duree': duree_cap,
                'difficulte': difficulte,
                'cle': cle,
            },
            {
                'discipline': 'Vélo',
                'type': 'Endurance Z2',
                'details': f'Endurance Z2 ({duree_velo} min)',
                'duree': duree_velo,
                'difficulte': 'endurance',
                'cle': False,
            },
        ],
    }


def test_regle_cap_velo_exactement_50_pourcent_ok():
    jour = _jour_cap_velo(40, 80)
    assert _appliquer_regle_cap_velo(jour) is False
    assert jour['seances'][0]['duree'] == 40
    assert not jour.get('contrainte_planification', False)


def test_regle_cap_velo_inferieure_a_50_pourcent_ok():
    jour = _jour_cap_velo(30, 80)
    assert _appliquer_regle_cap_velo(jour) is False
    assert jour['seances'][0]['duree'] == 30
    assert not jour.get('contrainte_planification', False)


def test_regle_cap_velo_superieure_a_50_pourcent_est_reduite():
    jour = _jour_cap_velo(60, 80)
    assert _appliquer_regle_cap_velo(jour) is False
    assert jour['seances'][0]['duree'] == 40
    assert jour['seances'][0]['discipline'] == 'CAP'
    assert jour['seances'][0]['difficulte'] == 'endurance'
    assert '40 min' in jour['seances'][0]['details']
    assert not jour.get('contrainte', {}).get('active', False)


def test_regle_cap_velo_correction_impossible_detecte_contrainte():
    jour = _jour_cap_velo(60, 80, type_cap='VMA', difficulte='intense', cle=True)
    assert _appliquer_regle_cap_velo(jour) is True
    assert jour['contrainte_planification'] is True
    assert MESSAGE_CAP_VELO in jour['contrainte']['message']
    # aucune séance supprimée, la CAP n'est pas rognée
    assert len(jour['seances']) == 2
    assert jour['seances'][0]['duree'] == 60


def test_regle_cap_seul_ne_declenche_aucune_contrainte():
    jour = {
        'jour': 'Mercredi', 'date': '2026-08-05',
        'seances': [{
            'discipline': 'CAP', 'type': 'Endurance fondamentale Z2',
            'details': 'Endurance fondamentale Z2 (60 min)', 'duree': 60,
            'difficulte': 'endurance', 'cle': False,
        }],
    }
    assert _appliquer_regle_cap_velo(jour) is False
    assert not jour.get('contrainte_planification', False)


def test_regle_velo_seul_ne_declenche_aucune_contrainte():
    jour = {
        'jour': 'Mercredi', 'date': '2026-08-05',
        'seances': [{
            'discipline': 'Vélo', 'type': 'Endurance Z2',
            'details': 'Endurance Z2 (80 min)', 'duree': 80,
            'difficulte': 'endurance', 'cle': False,
        }],
    }
    assert _appliquer_regle_cap_velo(jour) is False
    assert not jour.get('contrainte_planification', False)


def test_regle_natation_et_cap_aucune_contrainte_specifique():
    jour = {
        'jour': 'Jeudi', 'date': '2026-08-06',
        'seances': [
            {
                'discipline': 'CAP', 'type': 'VMA',
                'details': 'VMA (60 min)', 'duree': 60,
                'difficulte': 'intense', 'cle': True,
            },
            {
                'discipline': 'Natation', 'type': 'Technique',
                'details': 'Technique (45 min)', 'duree': 45,
                'difficulte': 'endurance', 'cle': False,
            },
        ],
    }
    assert _appliquer_regle_cap_velo(jour) is False
    assert not jour.get('contrainte_planification', False)


def test_regle_cap_velo_durees_jamais_nulles_ou_negatives():
    for duree_velo in range(0, 201, 10):
        jour = _jour_cap_velo(90, duree_velo)
        _appliquer_regle_cap_velo(jour)
        cap = jour['seances'][0]
        velo = jour['seances'][1]
        assert cap['duree'] > 0
        assert velo['duree'] >= 0
        if jour.get('contrainte_planification'):
            # correction impossible : la séance reste intacte
            assert cap['duree'] == 90
        else:
            assert cap['duree'] <= max(90, 0.5 * duree_velo + 1e-9)


def test_11_les_profils_reels_respectent_7_jours_et_regle_cap_velo():
    if not _BASE_ATHLETES.exists():
        pytest.skip('Profils réels indisponibles')
    dossiers = sorted(d for d in _BASE_ATHLETES.iterdir() if d.is_dir())
    if not dossiers:
        pytest.skip('Profils réels indisponibles')
    assert dossiers
    for dossier in dossiers:
        profil = charger_profil(str(dossier))
        disponibilites = charger_disponibilites(str(dossier))
        try:
            date_objectif = datetime.strptime(profil['date_objectif'], '%Y-%m-%d')
        except (KeyError, TypeError, ValueError):
            pytest.skip(f"date objectif absente pour {dossier.name}")
        vma = profil.get('physiologie', {}).get('vma')
        vc = profil.get('physiologie', {}).get('vc')
        seances_vma = charger_seances(str(dossier), 'VMA') if vma else []
        seances_vc = charger_seances(str(dossier), 'VC') if vc else []
        plan = generer_plan_complet(
            datetime(2026, 8, 1), date_objectif, profil, disponibilites,
            seances_vma, seances_vc
        )
        assert plan, dossier.name
        for semaine in plan:
            assert len(semaine['jours']) == 7, dossier.name
            assert [j['jour'] for j in semaine['jours']] == _JOURS_CDC, dossier.name
            for jour in semaine['jours']:
                if jour.get('hors_plan'):
                    assert [s['discipline'] for s in jour['seances']] == ['Repos'], dossier.name
                caps = [s for s in jour['seances'] if s['discipline'] == 'CAP']
                velos = [
                    s for s in jour['seances']
                    if s['discipline'] in ('Vélo', 'Velo')
                ]
                if caps and velos:
                    duree_velo = max(s['duree'] for s in velos)
                    for cap in caps:
                        assert cap['duree'] <= 0.5 * duree_velo + 1e-9, (
                            dossier.name, jour['date'], cap['duree'], duree_velo
                        )


# ============================================================
# 1 — SAISIE DE LA DATE DE DÉBUT (JJ/MM/AAAA)
# ============================================================

def test_parser_date_debut_jj_mm_aaaa():
    date = parser_date_debut('01/08/2026')
    assert date == datetime(2026, 8, 1)
    assert date.strftime('%Y-%m-%d') == '2026-08-01'


def test_parser_date_debut_iso_accepte_pour_compatibilite():
    assert parser_date_debut('2026-08-01') == datetime(2026, 8, 1)


@pytest.mark.parametrize('saisie', [
    '32/01/2026', '31/02/2026', '2026/08/01', '01-08-2026', 'abc', '01/08/26',
])
def test_parser_date_debut_invalide_est_refusee(saisie):
    with pytest.raises(ValueError):
        parser_date_debut(saisie)


def test_parser_date_debut_vide_retourne_none():
    assert parser_date_debut('') is None
    assert parser_date_debut('   ') is None
    assert parser_date_debut(None) is None


def test_planifier_convertit_la_date_jj_mm_aaaa(monkeypatch):
    from src import main as main_module

    capture = {}

    def _planifier(athlete_dir, date_debut):
        capture['date_debut'] = date_debut
        return {'athlete': 'X', 'semaines': []}

    monkeypatch.setattr(main_module, 'choisir_athletes', lambda: ['Athlete_B'])
    monkeypatch.setattr(main_module, 'planifier_athlete', _planifier)
    monkeypatch.setattr(main_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr('builtins.input', lambda prompt='': '01/08/2026')

    main_module.planifier()

    assert capture['date_debut'] == '2026-08-01'


def test_planifier_refuse_une_date_invalide(monkeypatch):
    from src import main as main_module

    appels = {'n': 0}

    def _planifier(athlete_dir, date_debut):
        appels['n'] += 1
        return {'athlete': 'X', 'semaines': []}

    monkeypatch.setattr(main_module, 'choisir_athletes', lambda: ['Athlete_B'])
    monkeypatch.setattr(main_module, 'planifier_athlete', _planifier)
    monkeypatch.setattr(main_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr('builtins.input', lambda prompt='': '31/02/2026')

    main_module.planifier()

    assert appels['n'] == 0


def test_planifier_date_vide_conserve_aujourd_hui(monkeypatch):
    from src import main as main_module

    capture = {}

    def _planifier(athlete_dir, date_debut):
        capture['date_debut'] = date_debut
        return {'athlete': 'X', 'semaines': []}

    monkeypatch.setattr(main_module, 'choisir_athletes', lambda: ['Athlete_B'])
    monkeypatch.setattr(main_module, 'planifier_athlete', _planifier)
    monkeypatch.setattr(main_module.os.path, 'exists', lambda path: True)
    monkeypatch.setattr('builtins.input', lambda prompt='': '')

    main_module.planifier()

    assert capture.get('date_debut') is None


def test_planifier_athlete_accepte_jj_mm_aaaa(monkeypatch):
    from src.planificateur import main_plan

    capture = {}

    def _generer(**kwargs):
        capture['debut'] = kwargs['debut']
        return []

    monkeypatch.setattr(main_plan, 'charger_profil', lambda path: {
        'nom': 'Test',
        'physiologie': {'vma': None, 'vc': None},
        'sport_principal': 'Course à pied',
        'date_objectif': '2026-12-15',
    })
    monkeypatch.setattr(main_plan, 'charger_disponibilites', lambda path: {
        'CAP': [], 'Velo': [], 'Natation': [],
        'bi_quotidien_nb': 0, 'bi_quotidien_capacite_brute': 'Non',
    })
    monkeypatch.setattr(main_plan, 'generer_plan_complet', _generer)
    monkeypatch.setattr(main_plan.os.path, 'exists', lambda path: True)
    monkeypatch.setattr(main_plan.os, 'makedirs', lambda *args, **kwargs: None)
    monkeypatch.setattr(main_plan, 'exporter_plan_csv', lambda *a, **k: '')
    monkeypatch.setattr(main_plan, 'exporter_intervals', lambda *a, **k: '')
    monkeypatch.setattr(main_plan, 'exporter_pdf_plan', lambda *a, **k: '')

    resultat = main_plan.planifier_athlete('dossier', '01/08/2026')

    assert capture['debut'] == datetime(2026, 8, 1)
    assert resultat.get('date_debut') == '2026-08-01'


# ============================================================
# 2-6 — PDF : 2 SEMAINES PAR PAGE, ENTÊTE ET PÉRIODES
# ============================================================

def _compter_pages_pdf(data):
    return data.count(b'/Type /Page') - data.count(b'/Type /Pages')


def _semaine_fictive(debut_iso, fin_iso, emoji='🟢'):
    return {
        'num_affichage': 1,
        'emoji': emoji,
        'date_debut': debut_iso,
        'date_fin': fin_iso,
        'jours': [
            {
                'jour': nom_jour,
                'date': '',
                'seances': [{
                    'discipline': 'Repos', 'type': 'Repos', 'details': 'Repos',
                    'duree': 0, 'difficulte': 'repos',
                }],
            }
            for nom_jour in _JOURS_CDC
        ],
    }


def test_grouper_semaines_par_page_deux_par_deux():
    assert TAILLE_PAGE_SEMAINES == 2
    groupes = _grouper_semaines_par_page(list(range(5)))
    assert groupes == [[0, 1], [2, 3], [4]]
    assert _grouper_semaines_par_page([]) == []


def test_periode_groupe_format_jj_mm_aaaa():
    groupe = [
        _semaine_fictive('2026-07-27', '2026-08-02'),
        _semaine_fictive('2026-08-03', '2026-08-09'),
    ]
    assert _periode_groupe(groupe) == 'Du 27/07/2026 au 09/08/2026'


def test_separateur_semaine_place_avant_lundi():
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche',
             'Lundi', 'Mardi']
    indices = _indices_debut_semaine(jours)
    assert indices == [0, 7]
    commandes = _commandes_separateur_semaine(indices)
    assert len(commandes) == 2
    for commande in commandes:
        assert commande[0] == 'LINEABOVE'
        assert commande[4] == COULEUR_SEPARATEUR_SEMAINE


def test_aucun_separateur_de_semaine_avant_samedi():
    jours = _JOURS_CDC
    assert 5 not in _indices_debut_semaine(jours)


def test_tableau_separe_les_semaines_avant_lundi_pas_samedi():
    styles = getSampleStyleSheet()
    small = styles['Normal']
    groupe = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
    ]
    rows, _, _, lignes_weekend, lignes_semaine = _tableau_semaines(groupe, {}, small)
    assert len(rows) == 1 + 14
    assert lignes_semaine == [1, 8]
    assert len(lignes_weekend) == 4
    assert not (set(lignes_semaine) & set(lignes_weekend))


def test_pdf_deux_semaines_par_page_entete_et_periodes(tmp_path):
    semaines = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
        _semaine_fictive('2026-08-17', '2026-08-23'),
    ]
    plan = {
        'athlete': 'Synthetique',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-08-23',
        'semaines': semaines,
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()

    # 2 pages de planning + 1 page pédagogique finale
    assert _compter_pages_pdf(data) == 3
    # titre répété sur chaque page (planning + pédagogique)
    assert data.count(b"Plan d'entra") == 3
    # la légende "Légende :" n'est présente que sur les pages de planning
    assert data.count(b'gende :') == 2
    # période exacte des semaines présentées sous chaque tableau
    assert b'Du 03/08/2026 au 16/08/2026' in data
    assert b'Du 17/08/2026 au 23/08/2026' in data


def test_pdf_derniere_page_une_seule_semaine(tmp_path):
    semaines = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
        _semaine_fictive('2026-08-17', '2026-08-23'),
    ]
    plan = {
        'athlete': 'Synthetique',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-08-23',
        'semaines': semaines,
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()
    # 2 pages de planning + 1 page pédagogique finale
    assert _compter_pages_pdf(data) == 3
    # la dernière page de planning ne contient que la 3e semaine
    assert b'Du 17/08/2026 au 23/08/2026' in data
    assert data.count(b'Plan d\'entra') == 3


def test_pdf_plan_reel_deux_semaines_par_page_et_periodes(tmp_path):
    import math

    if not _BASE_ATHLETES.exists():
        pytest.skip('Profils réels indisponibles')
    dossier = _BASE_ATHLETES / 'Athlete_C'
    if not dossier.exists():
        pytest.skip('Profil Athlete_C indisponible')
    profil = charger_profil(str(dossier))
    disponibilites = charger_disponibilites(str(dossier))
    date_objectif = datetime.strptime(profil['date_objectif'], '%Y-%m-%d')
    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    seances_vma = charger_seances(str(dossier), 'VMA') if vma else []
    seances_vc = charger_seances(str(dossier), 'VC') if vc else []
    semaines = generer_plan_complet(
        datetime(2026, 8, 1), date_objectif, profil, disponibilites,
        seances_vma, seances_vc
    )
    plan = {
        'athlete': profil['nom'],
        'date_debut': '2026-08-01',
        'date_objectif': date_objectif.strftime('%Y-%m-%d'),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': disponibilites,
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()

    pages_planning = math.ceil(len(semaines) / 2)
    pages = _compter_pages_pdf(data)
    # pages de planning + 1 page pédagogique finale
    assert pages == pages_planning + 1
    # entête répété sur chaque page (planning + pédagogique)
    assert data.count(b"Plan d'entra") == pages
    # la légende "Légende :" n'est présente que sur les pages de planning
    assert data.count(b'gende :') == pages_planning
    # période générale du plan répétée dans l'entête de chaque page
    periode_generale = (
        f"Du {_format_date_for_user('2026-08-01')} "
        f"au {_format_date_for_user(plan['date_objectif'])}"
    ).encode()
    assert data.count(periode_generale) == pages
    # période exacte de la première page (lundi de la première semaine)
    assert b'Du 27/07/2026 au 09/08/2026' in data
    # semaines lundi -> dimanche
    for semaine in semaines:
        assert len(semaine['jours']) == 7
        assert [j['jour'] for j in semaine['jours']] == _JOURS_CDC


# ============================================================
# RENDU GRAPHIQUE PDF : symboles colorés, légendes, en-tête, pagination
# ============================================================

def _pdf_bytes_plan_minimal():
    import tempfile
    dossier = tempfile.mkdtemp()
    chemin = exporter_pdf_plan(_plan_pdf_minimal(), dossier)
    return Path(chemin).read_bytes()


def test_pdf_titre_et_periode_generale_presents():
    data = _pdf_bytes_plan_minimal()
    assert b"Plan d'entra" in data
    assert b'Du 01/08/2026 au 31/08/2026' in data


class _CanvasRecorder:
    """Canvas minimal qui enregistre les primitives de dessin appelées."""

    def __init__(self):
        self.calls = []

    def setFillColor(self, *args, **kwargs):
        self.calls.append(('setFillColor', args))

    def setStrokeColor(self, *args, **kwargs):
        self.calls.append(('setStrokeColor', args))

    def setLineWidth(self, *args, **kwargs):
        self.calls.append(('setLineWidth', args))

    def circle(self, *args, **kwargs):
        self.calls.append(('circle', args))

    def rect(self, *args, **kwargs):
        self.calls.append(('rect', args))

    def beginPath(self):
        recorder = self

        class _Path:
            def moveTo(self, *args):
                recorder.calls.append(('moveTo', args))

            def lineTo(self, *args):
                recorder.calls.append(('lineTo', args))

            def close(self, *args):
                recorder.calls.append(('close', args))

        return _Path()

    def drawPath(self, *args, **kwargs):
        self.calls.append(('drawPath', args))


def test_pdf_legendes_presentes():
    data = _pdf_bytes_plan_minimal()
    assert b'gende :' in data                  # « Légende : »
    assert b'Couleurs des s' in data           # « Couleurs des séances : »
    # libellés de la légende d'intensité
    for label in (b'Endurance', b'Seuil', b'Intense', b'Course', b'Repos'):
        assert label in data


def test_legendes_intensite_et_couleurs_completes():
    assert len(LEGENDE_INTENSITE) == 6
    difficultes = {difficulte for difficulte, _ in LEGENDE_INTENSITE}
    assert difficultes == {
        'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
    }
    # les 7 couleurs de type sont sur UNE SEULE ligne
    from src.planificateur.export_pdf_plan import _tableau_legende_couleurs
    styles = getSampleStyleSheet()
    table = _tableau_legende_couleurs(styles['Normal'])
    assert len(table._cellvalues) == 1
    labels = [cellule.getPlainText() for cellule in table._cellvalues[0]]
    for attendu in ('Endurance', 'Intensité', 'Seuil', 'Fartlek',
                    'Sortie longue', 'Compétition', 'Renforcement'):
        assert attendu in labels


def test_symboles_intensite_distincts_et_colores():
    assert set(FORMES_INTENSITE) == {
        'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
    }
    formes = [forme for forme, _ in FORMES_INTENSITE.values()]
    couleurs = [couleur for _, couleur in FORMES_INTENSITE.values()]
    # couleurs distinctes ; au moins 5 formes distinctes (repos = cercle gris)
    assert len(set(couleurs)) == 6
    assert len(set(formes)) >= 5
    for _, couleur in FORMES_INTENSITE.values():
        assert couleur.startswith('#') and len(couleur) == 7

    forme, couleur = _symbole_intensite('intense')
    assert forme == FORMES_INTENSITE['intense'][0]
    assert couleur == FORMES_INTENSITE['intense'][1]
    # valeur inconnue -> endurance par défaut
    assert _symbole_intensite('inconnue') == FORMES_INTENSITE['endurance']


def test_formes_intensite_reellement_dessinees():
    for difficulte in FORMES_INTENSITE:
        forme, couleur = _symbole_intensite(difficulte)
        flowable = FormeIntensite(forme, couleur)
        assert isinstance(flowable, Flowable)
        recorder = _CanvasRecorder()
        flowable.wrap(30, 30)
        flowable.canv = recorder
        flowable.draw()
        assert recorder.calls, difficulte
        assert any(appel[0] in ('circle', 'rect', 'drawPath')
                   for appel in recorder.calls), difficulte
        if forme in ('triangle', 'losange', 'etoile'):
            assert any(appel[0] == 'drawPath' for appel in recorder.calls)
    assert FORMES_INTENSITE['endurance'][0] == 'cercle'
    assert FORMES_INTENSITE['seuil'][0] == 'carre'


def test_symboles_intensite_presents_dans_la_legende():
    styles = _creer_styles_pdf()
    table = _bloc_legende_intensite(styles['legende'])
    # légende sur une seule ligne
    assert len(table._cellvalues) == 1
    formes = [
        cellule for cellule in table._cellvalues[0]
        if isinstance(cellule, FormeIntensite)
    ]
    assert len(formes) == 6


def test_tableau_centre_et_colonne_details_large():
    styles = _creer_styles_pdf()
    groupe = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
    ]
    table = _construire_tableau(groupe, {}, styles)
    assert table.hAlign == 'CENTER'
    # Détails est la colonne la plus large
    assert LARGEURS_COLONNES[5] == max(LARGEURS_COLONNES)
    assert PROPORTIONS_COLONNES[5] == max(PROPORTIONS_COLONNES)
    # 1 ligne d'en-tête + 7 jours x 2 semaines
    assert len(table._cellvalues) == 1 + 14
    # en-tête du tableau en gras
    assert styles['small_bold'].fontName == 'Helvetica-Bold'


def test_periode_de_page_centree_et_en_gras():
    styles = _creer_styles_pdf()
    assert styles['periode'].alignment == TA_CENTER
    assert styles['periode'].fontName == 'Helvetica-Bold'
    assert styles['titre'].alignment == TA_CENTER
    assert styles['sous_titre'].alignment == TA_CENTER
    assert styles['titre'].fontName == 'Helvetica-Bold'


def test_pdf_numero_de_page_present():
    # 1 page de planning + 1 page pédagogique = 2 pages
    data = _pdf_bytes_plan_minimal()
    assert b'Page 1 / 2' in data
    assert b'Page 2 / 2' in data


def test_pdf_numero_de_page_sur_plusieurs_pages(tmp_path):
    semaines = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
        _semaine_fictive('2026-08-17', '2026-08-23'),
    ]
    plan = {
        'athlete': 'Synthetique',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-08-23',
        'semaines': semaines,
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()
    # 2 pages de planning + 1 page pédagogique = 3 pages
    assert _compter_pages_pdf(data) == 3
    assert b'Page 1 / 3' in data
    assert b'Page 2 / 3' in data
    assert b'Page 3 / 3' in data


def test_pdf_contraintes_affichees_quand_presentes(tmp_path):
    plan = _plan_pdf_minimal()
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()
    # le message de contrainte et le marqueur [!1] sont présents
    assert b'Contraintes de planification' in data
    assert b'Contrainte de test' in data
    assert b'[!1]' in data


def test_pdf_entete_et_legende_repetes_par_page(tmp_path):
    semaines = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
        _semaine_fictive('2026-08-17', '2026-08-23'),
    ]
    plan = {
        'athlete': 'Synthetique',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-08-23',
        'semaines': semaines,
    }
    chemin = exporter_pdf_plan(plan, str(tmp_path))
    data = Path(chemin).read_bytes()
    pages_planning = 2
    pages = _compter_pages_pdf(data)
    assert pages == pages_planning + 1  # + page pédagogique
    # titre répété sur toutes les pages, légende seulement sur le planning
    assert data.count(b"Plan d'entra") == pages
    assert data.count(b'gende :') == pages_planning
    # période de page centrée et présente sous chaque tableau
    assert b'Du 03/08/2026 au 16/08/2026' in data
    assert b'Du 17/08/2026 au 23/08/2026' in data


# ============================================================
# MISE EN PAGE : grand tableau, fusion Semaine, formes dessinées
# ============================================================

def test_colonne_intensite_utilise_des_formes_dessinees():
    styles = _creer_styles_pdf()
    groupe = [_semaine_fictive('2026-08-03', '2026-08-09')]
    rows, _, _, _, _ = _tableau_semaines(groupe, {}, styles['small'])
    # la dernière colonne (Intensité) contient un Flowable dessiné
    for ligne in rows[1:]:
        assert isinstance(ligne[-1], FormeIntensite)


def test_spans_semaines_fusionnent_la_colonne_semaine():
    assert _spans_semaines([1, 8], 15) == [
        ('SPAN', (0, 1), (0, 7)),
        ('SPAN', (0, 8), (0, 14)),
    ]
    assert _spans_semaines([1, 8, 15], 22) == [
        ('SPAN', (0, 1), (0, 7)),
        ('SPAN', (0, 8), (0, 14)),
        ('SPAN', (0, 15), (0, 21)),
    ]
    assert _spans_semaines([1], 1) == []


def test_tableau_utilise_toute_la_largeur_utile():
    styles = _creer_styles_pdf()
    groupe = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
    ]
    largeur = 277 * mm
    table = _construire_tableau(groupe, {}, styles, largeur)
    assert table.hAlign == 'CENTER'
    assert abs(sum(table._argW) - largeur) < 0.5
    # Détails reste la colonne la plus large
    assert max(table._argW) == table._argW[5]


def test_tableau_remplit_la_hauteur_disponible():
    styles = _creer_styles_pdf()
    groupe = [
        _semaine_fictive('2026-08-03', '2026-08-09'),
        _semaine_fictive('2026-08-10', '2026-08-16'),
    ]
    hauteur = 150 * mm
    table = _construire_tableau(groupe, {}, styles, 277 * mm, hauteur)
    _, hauteur_reelle = table.wrap(277 * mm, hauteur)
    # le tableau remplit la majorité de l'espace disponible
    assert hauteur_reelle <= hauteur
    assert hauteur_reelle >= hauteur * 0.7


def test_police_corps_du_tableau_lisible():
    small, small_bold = _styles_tableau(8.5)
    assert 8 <= small.fontSize <= 9
    assert small_bold.fontName == 'Helvetica-Bold'
    assert small.fontName == 'Helvetica'


# ============================================================
# PAGE PÉDAGOGIQUE FINALE (comprendre les légendes)
# ============================================================

def _plan_trois_semaines(athlete='Athlete_C'):
    return {
        'athlete': athlete,
        'date_debut': '2026-08-03',
        'date_objectif': '2026-08-23',
        'semaines': [
            _semaine_fictive('2026-08-03', '2026-08-09'),
            _semaine_fictive('2026-08-10', '2026-08-16'),
            _semaine_fictive('2026-08-17', '2026-08-23'),
        ],
    }


def test_page_pedagogique_ajoutee_en_derniere_page(tmp_path):
    chemin = exporter_pdf_plan(_plan_trois_semaines(), str(tmp_path))
    data = Path(chemin).read_bytes()
    # 2 pages de planning + 1 page pédagogique
    assert _compter_pages_pdf(data) == 3
    # le titre pédagogique n'apparaît qu'une fois (sur la dernière page)
    assert data.count(b'COMPRENDRE LES L') == 1
    assert b'Page 3 / 3' in data


def test_page_pedagogique_nom_athlete_et_periode(tmp_path):
    chemin = exporter_pdf_plan(_plan_trois_semaines('Athlete_C'), str(tmp_path))
    data = Path(chemin).read_bytes()
    assert b'Athlete_C' in data
    assert b'Du 03/08/2026 au 23/08/2026' in data


def test_page_pedagogique_introduction_et_reperes(tmp_path):
    chemin = exporter_pdf_plan(_plan_trois_semaines(), str(tmp_path))
    data = Path(chemin).read_bytes()
    assert b'deux codes compl' in data
    assert b'mentaires' in data
    assert b"Entra" in data and b"nement" in data  # pied de page
    for repere in (b'compl', b'cercle vert', b'orange', b'violette'):
        assert repere in data


def test_page_pedagogique_sept_types_presents():
    styles = _creer_styles_pdf()
    table = _tableau_types_seance(styles, 277 * mm)
    assert len(table._cellvalues) == 2
    assert len(table._cellvalues[0]) == 7
    labels = [cellule.getPlainText() for cellule in table._cellvalues[0]]
    for label, _, _ in TYPES_SEANCE:
        assert label.upper() in labels


def test_page_pedagogique_couleurs_identiques_au_pdf():
    couleurs = [couleur for _, couleur, _ in TYPES_SEANCE]
    assert couleurs == [
        COULEUR_ENDURANCE, COULEUR_INTENSE, COULEUR_SEUIL,
        COULEUR_FARTLEK, COULEUR_LONGUE, COULEUR_COMPETITION,
        COULEUR_RENFORCEMENT,
    ]


def test_page_pedagogique_six_formes_dessinees():
    styles = _creer_styles_pdf()
    table = _tableau_intensites(styles, 277 * mm)
    assert len(table._cellvalues) == 3
    assert len(table._cellvalues[0]) == 6
    formes = [
        cellule for cellule in table._cellvalues[0]
        if isinstance(cellule, FormeIntensite)
    ]
    assert len(formes) == 6
    # chaque difficulté a bien son explication
    assert set(EXPLICATIONS_INTENSITE) == {
        'endurance', 'seuil', 'intense', 'recuperation', 'course', 'repos',
    }


def test_page_pedagogique_exemple_issu_du_plan_reel():
    plan = _plan_pdf_minimal()  # contient une séance CAP VMA (intense)
    exemple = _exemple_depuis_plan(plan)
    assert exemple['discipline'] == 'CAP'
    assert exemple['difficulte'] == 'intense'
    assert exemple['couleur'] == COULEUR_INTENSE
    assert exemple['duree'] == 45


def test_page_pedagogique_tient_sur_une_seule_page():
    styles = _creer_styles_pdf()
    largeur = landscape(A4)[0] - MARGE_GAUCHE - MARGE_DROITE
    hauteur = landscape(A4)[1] - MARGE_HAUT - MARGE_BAS
    bloc = _bloc_page_pedagogique(_plan_pdf_minimal(), styles, largeur)
    assert _hauteur_flowables(bloc, largeur, hauteur) <= hauteur


def test_forme_coche_dessinee():
    flowable = FormeCoche()
    assert isinstance(flowable, Flowable)
    recorder = _CanvasRecorder()
    flowable.wrap(10, 10)
    flowable.canv = recorder
    flowable.draw()
    assert any(appel[0] == 'drawPath' for appel in recorder.calls)
    assert len(REPERES_ATHLETE) == 8


# ============================================================
# ARCHITECTURE CSV MAÎTRE : CSV -> PDF / Intervals
# ============================================================

def _creer_plan_csv_test(tmp_path, athlete='Athlete CSV'):
    profil = _profil_triathlon()
    dispo = _disponibilites_avec_bi(
        ['Lundi', 'Mardi', 'Jeudi'], ['Mercredi'], ['Vendredi']
    )
    semaines = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 9, 27), profil, dispo
    )
    plan = {
        'athlete': athlete,
        'date_debut': '2026-08-03',
        'date_objectif': '2026-09-27',
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': dispo,
    }
    chemin = exporter_plan_csv(plan, str(tmp_path))
    return chemin, plan


def _index_ligne_data(chemin_csv, discipline, extrait_type):
    df = pd.read_csv(chemin_csv, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    data = df[~df['N° semaine'].isin(LIGNES_ENTETE)].reset_index(drop=True)
    indices = data.index[
        (data['Discipline'] == discipline)
        & (data['Type de séance'].str.contains(extrait_type))
    ].tolist()
    assert indices, f"Aucune ligne {discipline}/{extrait_type}"
    return indices[0]


def _modifier_seance_cap(chemin_csv):
    ligne = _index_ligne_data(chemin_csv, 'CAP', 'Endurance')
    resultat = appliquer_modifications_csv(chemin_csv, [
        {'ligne': ligne, 'colonne': 'Type de séance', 'valeur': 'Endurance TEST'},
        {'ligne': ligne, 'colonne': 'Durée (min)', 'valeur': '77'},
        {'ligne': ligne, 'colonne': 'Détails', 'valeur': 'Endurance TEST (77 min)'},
    ])
    assert resultat['applique'] is True
    return ligne


def test_trouver_csv_courant_ignore_les_intervals(tmp_path):
    chemin, _ = _creer_plan_csv_test(tmp_path)
    (tmp_path / 'Athlete_CSV_intervals_20260101_000000.csv').write_text(
        'Date,Name\n', encoding='utf-8'
    )
    courant = trouver_csv_courant(str(tmp_path))
    assert courant == chemin
    assert '_plan_' in Path(courant).name


def test_construire_plan_depuis_csv_reconstruit_les_donnees(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    reconstruit = construire_plan_depuis_csv(chemin, athlete='Athlete CSV')
    assert reconstruit['athlete'] == 'Athlete CSV'
    assert reconstruit['date_debut'] == plan['date_debut']
    assert reconstruit['date_objectif'] == plan['date_objectif']
    assert len(reconstruit['semaines']) == len(plan['semaines'])
    for semaine_orig, semaine_csv in zip(plan['semaines'], reconstruit['semaines']):
        assert len(semaine_csv['jours']) == 7
        assert [j['jour'] for j in semaine_csv['jours']] == _JOURS_CDC
        seances_orig = [
            (s['discipline'], s['type'], s['duree'])
            for j in semaine_orig['jours'] for s in j['seances']
        ]
        seances_csv = [
            (s['discipline'], s['type'], s['duree'])
            for j in semaine_csv['jours'] for s in j['seances']
        ]
        assert seances_csv == seances_orig


def test_csv_modifie_reflete_dans_le_pdf(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    _modifier_seance_cap(chemin)
    resultat = exporter_pdf_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert resultat['chemin']
    contenu = Path(resultat['chemin']).read_bytes()
    assert b'Endurance TEST' in contenu
    assert b'77 min' in contenu


def test_csv_modifie_reflete_dans_intervals(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    _modifier_seance_cap(chemin)
    resultat = exporter_intervals_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert resultat['chemin']
    intervals = pd.read_csv(resultat['chemin'], sep=',', encoding='utf-8-sig', dtype=str)
    assert any('Endurance TEST' in nom for nom in intervals['Name'])
    assert any('77 min' == duree for duree in intervals['Planned Duration'])


def test_pdf_et_intervals_issus_du_meme_csv(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    _modifier_seance_cap(chemin)
    resultat = exporter_exports_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert resultat['valide'] is True
    pdf = Path(resultat['pdf']).read_bytes()
    intervals = pd.read_csv(resultat['intervals'], sep=',', encoding='utf-8-sig', dtype=str)
    assert b'Endurance TEST' in pdf
    assert any('Endurance TEST' in nom for nom in intervals['Name'])
    assert any('77 min' == duree for duree in intervals['Planned Duration'])


def test_export_ne_modifie_pas_le_csv(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    _modifier_seance_cap(chemin)
    avant = Path(chemin).read_bytes()
    exporter_pdf_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert Path(chemin).read_bytes() == avant


def test_csv_valide_autorise_les_exports(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    validation = valider_plan_csv(chemin, plan['disponibilites'])
    assert validation['valide'] is True
    resultat = exporter_exports_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert resultat['valide'] is True
    assert Path(resultat['pdf']).exists()
    assert Path(resultat['intervals']).exists()


def test_csv_invalide_bloque_les_exports(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    ligne = _index_ligne_data(chemin, 'CAP', 'Endurance')
    df = pd.read_csv(chemin, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    positions = df.index[~df['N° semaine'].isin(LIGNES_ENTETE)].tolist()
    df.at[positions[ligne], 'Durée (min)'] = '0'
    df.to_csv(chemin, sep=';', index=False, encoding='utf-8-sig')

    validation = valider_plan_csv(chemin)
    assert validation['valide'] is False
    assert validation['erreurs']

    resultat_pdf = exporter_pdf_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV'
    )
    assert resultat_pdf['chemin'] == ''
    resultat = exporter_exports_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV'
    )
    assert resultat['valide'] is False
    assert resultat['pdf'] == '' and resultat['intervals'] == ''


def test_exports_prennent_un_chemin_csv():
    import inspect
    assert list(inspect.signature(exporter_pdf_depuis_csv).parameters)[0] == 'chemin_csv'
    assert list(inspect.signature(exporter_intervals_depuis_csv).parameters)[0] == 'chemin_csv'
    assert list(inspect.signature(exporter_exports_depuis_csv).parameters)[0] == 'chemin_csv'


def test_interface_agent_sans_connexion_ia():
    assert issubclass(FournisseurModifications, ABC)
    with pytest.raises(TypeError):
        FournisseurModifications()
    import src.planificateur.agent_plan_csv as module
    source = Path(module.__file__).read_text(encoding='utf-8')
    for interdit in ('import requests', 'import openai', 'import deepseek', 'import anthropic'):
        assert interdit not in source


def test_appliquer_modifications_valide_ou_refuse(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    ligne = _index_ligne_data(chemin, 'CAP', 'Endurance')

    ok = appliquer_modifications_csv(
        chemin, [{'ligne': ligne, 'colonne': 'Durée (min)', 'valeur': '88'}]
    )
    assert ok['applique'] is True

    avant = Path(chemin).read_bytes()
    refuse = appliquer_modifications_csv(
        chemin, [{'ligne': ligne, 'colonne': 'Durée (min)', 'valeur': '-9'}]
    )
    assert refuse['applique'] is False
    assert refuse['erreurs']
    assert Path(chemin).read_bytes() == avant


# ============================================================
# MENU FINAL ET WORKFLOW CSV
# ============================================================

def test_menu_ordre_final():
    import contextlib
    import io
    from src import main as main_module

    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        main_module.menu()
    texte = tampon.getvalue()

    attendus = [
        '1. 📊 Analyser un fichier (TSV)',
        '2. 📅 Générer / recréer le plan CSV',
        '3. 🤖 Modifier le plan CSV avec l\'agent IA',
        '4. ✅ Valider le CSV',
        '5. 📄 Générer PDF + Intervals.ICU depuis le CSV',
        '6. 🔄 Mettre à jour le plan depuis Intervals.ICU',
        '7. 🏃 Calculer et afficher les allures VMA ou VC',
        '8. 🚪 Quitter',
    ]
    positions = []
    for libelle in attendus:
        assert libelle in texte, libelle
        positions.append(texte.index(libelle))
    assert positions == sorted(positions)
    # l'ancien export direct n'est plus proposé
    assert 'Exporter un plan CSV vers Intervals.ICU' not in texte


def test_menu_dispatch_des_options(monkeypatch):
    from src import main as main_module

    appels = []
    options = [
        'analyser_csv', 'generer_plan_csv', 'modifier_plan_csv_agent',
        'valider_csv_plan', 'exporter_pdf_intervals_csv',
        'mettre_a_jour_plan', 'generer_pdf_allures',
    ]
    for nom in options:
        monkeypatch.setattr(
            main_module, nom,
            (lambda appel: (lambda *a, **k: appels.append(appel)))(nom),
        )
    entrees = iter(['1', '', '2', '', '3', '', '4', '', '5', '', '6', '', '7', '', '8'])
    monkeypatch.setattr('builtins.input', lambda prompt='': next(entrees))

    main_module.main()

    assert appels == options


def test_export_revalide_apres_une_validation_ancienne(tmp_path):
    chemin, plan = _creer_plan_csv_test(tmp_path)
    # validation "ancienne" OK
    assert valider_plan_csv(chemin, plan['disponibilites'])['valide'] is True
    # le CSV est modifié (invalide) entre la validation et l'export
    ligne = _index_ligne_data(chemin, 'CAP', 'Endurance')
    df = pd.read_csv(chemin, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    positions = df.index[~df['N° semaine'].isin(LIGNES_ENTETE)].tolist()
    df.at[positions[ligne], 'Durée (min)'] = '0'
    df.to_csv(chemin, sep=';', index=False, encoding='utf-8-sig')

    resultat = exporter_exports_depuis_csv(
        chemin, str(tmp_path), athlete='Athlete CSV',
        disponibilites=plan['disponibilites'],
    )
    assert resultat['valide'] is False
    assert resultat['pdf'] == '' and resultat['intervals'] == ''


# ============================================================
# OPTION 4 : SÉLECTION DES CSV PRÉSENTS DANS outputs/plans/
# ============================================================

def _ecrire_csv_factice(chemin):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text('N° semaine;Jour\n', encoding='utf-8')


def test_lister_csv_plans_exclut_intervals_et_pdf(tmp_path):
    _ecrire_csv_factice(tmp_path / 'Athlete_C' / 'Athlete_C_plan_20260101_000000.csv')
    _ecrire_csv_factice(tmp_path / 'Athlete_C' / 'Athlete_C_intervals_20260101_000000.csv')
    _ecrire_csv_factice(tmp_path / 'Athlete_C' / 'Athlete_C_plan_apercu_20260101_000000.pdf')
    entrees = lister_csv_plans(str(tmp_path))
    assert len(entrees) == 1
    assert entrees[0]['fichier'] == 'Athlete_C_plan_20260101_000000.csv'
    assert entrees[0]['athlete'] == 'Athlete_C'


def test_lister_csv_plans_sans_deduction_de_nom(tmp_path):
    _ecrire_csv_factice(tmp_path / 'Athlete_A' / 'Athlete_A_plan_20260101_000000.csv')
    _ecrire_csv_factice(tmp_path / 'Athlete_D' / 'Athlete_D_plan_20260101_000000.csv')
    _ecrire_csv_factice(tmp_path / 'Athlete_A' / 'Athlete_A_plan_20260201_000000.csv')
    entrees = lister_csv_plans(str(tmp_path))
    assert len(entrees) == 3
    athletes = [entree['athlete'] for entree in entrees]
    assert athletes.count('Athlete_A') == 2
    assert 'Athlete_D' in athletes
    chemins = {entree['chemin'] for entree in entrees}
    assert len(chemins) == 3


def test_lister_csv_plans_racine_absente(tmp_path):
    assert lister_csv_plans(str(tmp_path / 'inexistant')) == []


def test_resoudre_selection_formats():
    assert resoudre_selection('*', 4) == [0, 1, 2, 3]
    assert resoudre_selection('1,3,5', 5) == [0, 2, 4]
    assert resoudre_selection('2-4', 6) == [1, 2, 3]
    assert resoudre_selection('1; 3', 4) == [0, 2]
    assert resoudre_selection('9', 4) == []
    assert resoudre_selection('', 4) == []
    assert resoudre_selection('*', 0) == []


def _entrees_csv_test(tmp_path, noms):
    entrees = []
    for athlete in noms:
        dossier = tmp_path / athlete
        dossier.mkdir(parents=True, exist_ok=True)
        chemin, _ = _creer_plan_csv_test(dossier, athlete=athlete)
        entrees.append({
            'athlete': athlete,
            'dossier': str(dossier),
            'fichier': Path(chemin).name,
            'chemin': chemin,
        })
    return entrees


def test_option4_aucun_csv(monkeypatch):
    import contextlib
    import io
    from src import main as main_module

    monkeypatch.setattr(main_module, 'lister_csv_plans', lambda racine=None: [])
    monkeypatch.setattr('builtins.input', lambda prompt='': '')
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        main_module.valider_csv_plan()
    sortie = tampon.getvalue()
    assert 'Aucun plan CSV disponible dans outputs/plans/.' in sortie
    assert 'Athlete_C' not in sortie
    assert 'LISTE DES ATHLÈTES' not in sortie


def test_option4_un_csv(monkeypatch, tmp_path):
    import contextlib
    import io
    from src import main as main_module

    entrees = _entrees_csv_test(tmp_path, ['Athlete_A'])
    monkeypatch.setattr(main_module, 'lister_csv_plans', lambda racine=None: entrees)
    monkeypatch.setattr('builtins.input', lambda prompt='': '1')
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        main_module.valider_csv_plan()
    sortie = tampon.getvalue()
    assert 'LISTE DES PLANS CSV DISPONIBLES' in sortie
    assert 'Athlete_A' in sortie
    assert entrees[0]['fichier'] in sortie
    assert '✅ VALIDÉ' in sortie


def test_option4_selection_etoile(monkeypatch, tmp_path):
    import contextlib
    import io
    from src import main as main_module

    entrees = _entrees_csv_test(tmp_path, ['Athlete_A', 'Athlete_B', 'Athlete_C'])
    monkeypatch.setattr(main_module, 'lister_csv_plans', lambda racine=None: entrees)
    monkeypatch.setattr('builtins.input', lambda prompt='': '*')
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        main_module.valider_csv_plan()
    sortie = tampon.getvalue()
    assert sortie.count('✅ VALIDÉ') == 3
    for entree in entrees:
        assert entree['fichier'] in sortie


def test_option4_selection_multiple(monkeypatch, tmp_path):
    import contextlib
    import io
    from src import main as main_module

    entrees = _entrees_csv_test(tmp_path, ['Athlete_A', 'Athlete_B', 'Athlete_C'])
    monkeypatch.setattr(main_module, 'lister_csv_plans', lambda racine=None: entrees)
    monkeypatch.setattr('builtins.input', lambda prompt='': '1,3')
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        main_module.valider_csv_plan()
    sortie = tampon.getvalue()
    assert sortie.count('✅ VALIDÉ') == 2
    assert '👤 Athlete_A' in sortie and '👤 Athlete_C' in sortie
    assert '👤 Athlete_B' not in sortie


def test_option4_ne_modifie_aucun_csv(monkeypatch, tmp_path):
    import contextlib
    import io
    from src import main as main_module

    entrees = _entrees_csv_test(tmp_path, ['Athlete_A', 'Athlete_B'])
    avant = {entree['chemin']: Path(entree['chemin']).read_bytes() for entree in entrees}
    monkeypatch.setattr(main_module, 'lister_csv_plans', lambda racine=None: entrees)
    monkeypatch.setattr('builtins.input', lambda prompt='': '*')
    with contextlib.redirect_stdout(io.StringIO()):
        main_module.valider_csv_plan()
    apres = {entree['chemin']: Path(entree['chemin']).read_bytes() for entree in entrees}
    assert apres == avant


# ============================================================
# SOCLE AGENT IA : MODIFICATIONS STRUCTURÉES DU CSV
# ============================================================

_REF_MODIF = datetime(2026, 8, 5)  # mercredi de la 1re semaine


def _profil_modif():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': 14.2},
        'sport_principal': 'Triathlon',
    }


def _dispo_modif():
    return {
        'CAP': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Samedi'],
        'Velo': ['Lundi', 'Mercredi', 'Jeudi', 'Dimanche'],
        'Natation': ['Mardi', 'Vendredi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }


def _creer_plan_modif(tmp_path):
    profil = _profil_modif()
    dispo = _dispo_modif()
    semaines = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), profil, dispo
    )
    plan = {
        'athlete': 'Test Modif',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-12-15',
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': dispo,
    }
    chemin = exporter_plan_csv(plan, str(tmp_path))
    return chemin, plan, dispo


def _copie_csv(chemin, tmp_path, nom='copie.csv'):
    destination = tmp_path / nom
    destination.write_bytes(Path(chemin).read_bytes())
    return str(destination)


def _lignes_data(chemin):
    df = pd.read_csv(chemin, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    return df[~df['N° semaine'].isin(LIGNES_ENTETE)].reset_index(drop=True)


def _date_iso(jour, semaine_lundi=datetime(2026, 8, 3)):
    return (semaine_lundi + timedelta(days=_JOURS_CDC.index(jour))).strftime('%Y-%m-%d')


def _jour_libre(chemin, dispo, discipline, semaine_lundi=datetime(2026, 8, 3)):
    """Premier jour de la semaine, disponible pour la discipline et sans séance."""
    data = _lignes_data(chemin)
    for jour in dispo[discipline]:
        date_iso = _date_iso(jour, semaine_lundi)
        date_fr = datetime.strptime(date_iso, '%Y-%m-%d').strftime('%d/%m/%Y')
        lignes_jour = data[data['Date'] == date_fr]
        if lignes_jour.empty:
            continue
        if not any(lignes_jour['Discipline'].isin(['Vélo', 'Velo'] if discipline == 'Velo' else [discipline])):
            return date_iso, jour
    return None, None


# 1-2. CONTRAT + DÉPLACEMENT D'UNE INTENSITÉ CAP
def test_contrat_represente_un_deplacement_cap():
    resultat = normaliser_demande({
        'action': 'DEPLACER', 'discipline': 'CAP', 'type_seance': 'INTENSITE',
        'periode': 'SEMAINE_COURANTE', 'jour_cible': 'MERCREDI',
    })
    assert resultat['erreurs'] == []
    modification = resultat['modifications'][0]
    assert modification['action'] == 'DEPLACER'
    assert modification['discipline'] == 'CAP'
    assert modification['type_seance'] == 'INTENSITE'
    assert modification['jour_cible'] == 'Mercredi'
    assert modification['periode']['type'] == 'SEMAINE_COURANTE'


def test_deplacer_intensite_cap_au_mercredi(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'DEPLACER', 'discipline': 'CAP', 'type_seance': 'INTENSITE',
        'jour_cible': 'Mercredi',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1
    apercu = resultat['apercu'][0]
    assert apercu['avant']['jour'] == 'Mardi'
    assert apercu['apres']['jour'] == 'Mercredi'
    assert apercu['apres']['type'] == "Test 3'/6'/12'"  # séance conservée


# 3. INTENSITÉ NATATION LE JEUDI (représentation + résolution)
def test_representation_intensite_natation_jeudi():
    resultat = normaliser_demande({
        'action': 'MODIFIER_DUREE', 'discipline': 'NATATION',
        'type_seance': 'intensite', 'jour_cible': 'jeudi', 'duree': 60,
    })
    assert resultat['erreurs'] == []
    modification = resultat['modifications'][0]
    assert modification['discipline'] == 'Natation'
    assert modification['type_seance'] == 'INTENSITE'
    assert modification['jour_cible'] == 'Jeudi'


def test_intensite_natation_resolue(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    # la natation d'intensité existe le mardi dans la semaine de référence
    resultat = previsualiser_modifications(chemin, {
        'action': 'MODIFIER_DUREE', 'discipline': 'Natation',
        'type_seance': 'INTENSITE', 'jour_cible': 'Mardi', 'duree': 75,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['apercu'][0]['apres']['duree'] == '75'


# 4. AJOUT D'UNE SÉANCE VÉLO DE 3 H
def test_ajouter_seance_velo_3h(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    date_iso, jour = _jour_libre(chemin, dispo, 'Velo')
    assert date_iso is not None
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER', 'discipline': 'VELO', 'type_seance': 'ENDURANCE',
        'jour_cible': jour, 'duree': 180,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    apres = resultat['apercu'][0]['apres']
    assert apres['discipline'] == 'Vélo'
    assert apres['duree'] == '180'


# 5. RÉCURRENCE UNE SEMAINE SUR DEUX
def test_recurrence_une_semaine_sur_deux(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    # mercredi est un jour de repos disponible pour la CAP
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Mercredi', 'duree': 50,
        'periode': {'type': 'SEMAINES', 'nb': 4},
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    dates = [apercu['apres']['date'] for apercu in resultat['apercu'] if apercu['apres']]
    assert dates == ['2026-08-05', '2026-08-19']


# 6-8. RESSOURCES (tous les vendredis) + URL conservées
def test_ajouter_ressources_tous_les_vendredis(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    urls = ['https://youtu.be/aaa', 'https://youtu.be/bbb', 'https://youtu.be/ccc']
    copie = _copie_csv(chemin, tmp_path, 'ressources.csv')
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'AJOUTER_RESSOURCE', 'type_seance': 'RENFORCEMENT',
        'jour_cible': 'Vendredi', 'ressources': urls,
        'periode': {'type': 'SEMAINES', 'nb': 3},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 3

    df = pd.read_csv(copie, sep=';', encoding='utf-8-sig', dtype=str, keep_default_na=False)
    assert 'Ressources' in df.columns
    lignes_avec_ressources = df[df['Ressources'] != '']
    assert len(lignes_avec_ressources) == 3
    assert all(
        datetime.strptime(date, '%d/%m/%Y').weekday() == 4
        for date in lignes_avec_ressources['Date']
    )
    for url in urls:
        assert all(url in valeur for valeur in lignes_avec_ressources['Ressources'])
    assert resultat['apercu'][0]['ressources'] == urls


# 9. MODIFICATION DE DURÉE
def test_modifier_duree(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Jeudi', 'duree': 45,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['apercu'][0]['avant']['duree'] == '60'
    assert resultat['apercu'][0]['apres']['duree'] == '45'


# 10. MODIFICATION DE DÉTAILS
def test_modifier_details(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'MODIFIER_DETAILS', 'discipline': 'Renforcement',
        'jour_cible': 'Jeudi', 'details': 'Gainage 15 min',
        'details_mode': 'REMPLACER',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] >= 1


# 11. SUPPRESSION
def test_supprimer_seance(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'suppression.csv')
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'SUPPRIMER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Jeudi',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    data = _lignes_data(copie)
    assert not any(
        (data['Date'] == '06/08/2026') & (data['Discipline'] == 'CAP')
    )
    # la journée reste présente (Repos)
    assert any(data['Date'] == '06/08/2026')


# 12. AMBIGUÏTÉ
def test_ambiguite_de_selection(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'DEPLACER', 'discipline': 'CAP', 'type_seance': 'INTENSITE',
        'jour_cible': 'Mercredi', 'periode': {'type': 'SEMAINES', 'nb': 2},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'AMBIGU'
    assert resultat['ambiguites']
    assert resultat['modifications_appliquees'] == 0


# 13. CONFLIT
def test_conflit_de_planification(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    # la sortie longue CAP (samedi) ne peut pas aller sur un jour ayant déjà CAP
    resultat = previsualiser_modifications(chemin, {
        'action': 'DEPLACER', 'discipline': 'CAP', 'type_seance': 'SORTIE_LONGUE',
        'date_cible': '04/08/2026',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CONFLIT'
    assert resultat['conflits']
    assert resultat['modifications_appliquees'] == 0


# 14-16. VALIDATION : valide / invalide / aucune écriture si KO
def test_modification_valide_ok(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Mercredi', 'duree': 50,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['validation']['valide'] is True


def test_modification_invalide_est_refusee(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'date_cible': '07/08/2026', 'duree': 50,  # vendredi : CAP indisponible
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'INVALIDE'
    assert resultat['validation']['valide'] is False


def test_aucune_ecriture_si_validation_ko(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'invalide.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'date_cible': '07/08/2026', 'duree': 50,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'INVALIDE'
    assert Path(copie).read_bytes() == avant


# 17. CONSERVATION DES DONNÉES NON CONCERNÉES
def test_conservation_des_donnees_non_concernees(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'conservation.csv')
    avant = _lignes_data(copie)
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Jeudi', 'duree': 45,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    apres = _lignes_data(copie)
    # même nombre de lignes, mêmes colonnes
    assert list(apres.columns) == list(avant.columns)
    assert len(apres) == len(avant)
    # seule la ligne CAP endurance du 06/08 change de durée
    cle = lambda df: list(zip(df['Date'], df['Discipline'], df['Type de séance']))
    for (d1, disc1, t1), (d2, disc2, t2) in zip(cle(avant), cle(apres)):
        assert (d1, disc1, t1) == (d2, disc2, t2)
    masque = (apres['Date'] == '06/08/2026') & (apres['Discipline'] == 'CAP')
    assert apres.loc[masque, 'Durée (min)'].tolist() == ['45']


# 18. PLUSIEURS MODIFICATIONS DANS UNE MÊME DEMANDE
def test_plusieurs_modifications(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'modifications': [
            {'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
             'type_seance': 'ENDURANCE', 'jour_cible': 'Jeudi', 'duree': 45},
            {'action': 'MODIFIER_DUREE', 'discipline': 'Vélo',
             'type_seance': 'SORTIE_LONGUE', 'duree': 100},
        ]
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] >= 2


# 19. PÉRIODE LIMITÉE
def test_periode_limitee_une_semaine(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'MODIFIER_DUREE', 'discipline': 'Vélo', 'type_seance': 'SORTIE_LONGUE',
        'duree_delta': -30, 'periode': {'type': 'SEMAINES', 'nb': 1},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    dates = [a['avant']['date'] for a in resultat['apercu']]
    assert dates == ['2026-08-09']  # uniquement la 1re semaine


# 20. JUSQU'À L'OBJECTIF
def test_jusqua_objectif(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER_RESSOURCE', 'type_seance': 'RENFORCEMENT',
        'jour_cible': 'Vendredi', 'ressources': ['https://n'],
        'periode': {'type': 'JUSQU_OBJECTIF'},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    data = _lignes_data(chemin)
    vendredis_attendus = [
        valeur for valeur in data['Date'].unique()
        if valeur and datetime.strptime(valeur, '%d/%m/%Y').weekday() == 4
    ]
    assert resultat['modifications_appliquees'] == len(vendredis_attendus)


# 24. TESTS SUR CSV RÉELS (copies, sans écraser la production)
def test_modification_sur_csv_reel_en_copie(tmp_path):
    base = _BASE_ATHLETES
    if not base.exists():
        pytest.skip('Profils réels indisponibles')
    dossier = base / 'Athlete_C'
    if not dossier.exists():
        pytest.skip('Profil Athlete_C indisponible')
    profil = charger_profil(str(dossier))
    disponibilites = charger_disponibilites(str(dossier))
    date_objectif = datetime.strptime(profil['date_objectif'], '%Y-%m-%d')
    semaines = generer_plan_complet(
        datetime(2026, 8, 1), date_objectif, profil, disponibilites,
        charger_seances(str(dossier), 'VMA'), charger_seances(str(dossier), 'VC'),
    )
    plan = {
        'athlete': profil['nom'], 'date_debut': '2026-08-01',
        'date_objectif': date_objectif.strftime('%Y-%m-%d'),
        'nb_semaines': len(semaines), 'semaines': semaines,
        'profil': profil, 'disponibilites': disponibilites,
    }
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    chemin = exporter_plan_csv(plan, str(source_dir))
    production_avant = Path(chemin).read_bytes()
    copie = _copie_csv(chemin, tmp_path, 'claire_copie.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'periode': {'type': 'TOUT'}, 'duree_delta': -5,
    }, disponibilites, date_reference=datetime(2026, 8, 3))
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] >= 1
    assert Path(copie).read_bytes() != avant
    # le CSV de production n'a pas été touché
    assert Path(chemin).read_bytes() == production_avant


# ============================================================
# PÉRIODES PAR DÉFAUT ET CLARIFICATIONS
# ============================================================

def test_absence_de_periode_utilise_fin_du_plan():
    resultat = normaliser_demande({
        'action': 'AJOUTER', 'discipline': 'Vélo', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Lundi', 'duree': 180,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
    })
    assert resultat['erreurs'] == []
    assert resultat['questions'] == []
    modification = resultat['modifications'][0]
    assert modification['periode'] is None
    assert modification['periode_explicite'] is False
    assert modification['periode_par_defaut'] == 'FIN_DU_PLAN'


def test_periode_explicite_conservee():
    resultat = normaliser_demande({
        'action': 'AJOUTER', 'discipline': 'Vélo', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Lundi', 'duree': 180,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
        'periode': {'type': 'SEMAINES', 'nb': 2},
    })
    modification = resultat['modifications'][0]
    assert modification['periode_explicite'] is True
    assert modification['periode_par_defaut'] is None
    assert modification['periode']['type'] == 'SEMAINES'


def test_recurrence_une_semaine_sur_deux_jusqua_fin_du_plan(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Mercredi', 'duree': 50,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'OK'
    dates = [apercu['apres']['date'] for apercu in resultat['apercu'] if apercu['apres']]
    assert dates[0] == '2026-08-05'
    base = datetime.strptime(dates[0], '%Y-%m-%d')
    assert all(
        (datetime.strptime(d, '%Y-%m-%d') - base).days % 14 == 0 for d in dates
    )
    # la récurrence va jusqu'à la fin du plan (et non SEMAINES(4))
    assert dates[-1] >= '2026-12-01'
    assert len(dates) > 4


def test_ambiguite_periode_demande_clarification(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'clarif.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'DEPLACER', 'discipline': 'Natation', 'type_seance': 'INTENSITE',
        'jour_cible': 'Jeudi', 'periode_ambigue': True,
        'question': "Voulez-vous placer l'intensité natation le jeudi uniquement cette "
                    'semaine ou tous les jeudis jusqu\'à la fin du plan ?',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'PERIODE'
    assert resultat['question']
    assert resultat['modifications_appliquees'] == 0
    assert Path(copie).read_bytes() == avant  # aucune écriture


def test_incomprehension_demande_clarification(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'incompris.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'INCOMPRIS',
        'question': 'Que souhaitez-vous modifier mercredi : la durée, l\'intensité, '
                    'le type de séance ou le contenu ?',
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'INCOMPRIS'
    assert 'mercredi' in resultat['question']
    assert Path(copie).read_bytes() == avant


def test_aucune_ecriture_lors_d_une_clarification(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'clarif2.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'DEPLACER', 'discipline': 'Natation', 'type_seance': 'INTENSITE',
        'jour_cible': 'Jeudi', 'periode_ambigue': True,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert Path(copie).read_bytes() == avant


def test_information_manquante_question_ciblee(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'DEPLACER',  # ni séance source ni cible
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'INFO_MANQUANTE'
    assert resultat['questions']
    assert any('déplacer' in question for question in resultat['questions'])


def test_selection_multiple_cible_manquante(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    resultat = previsualiser_modifications(chemin, {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP',  # durée manquante
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert any('durée' in question.lower() for question in resultat['questions'])


def test_plusieurs_modifications_dont_une_ambigue(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'multi_ambig.csv')
    avant = Path(copie).read_bytes()
    resultat = appliquer_modifications_structurees(copie, {
        'modifications': [
            {'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
             'type_seance': 'ENDURANCE', 'jour_cible': 'Jeudi', 'duree': 45},
            {'action': 'DEPLACER', 'discipline': 'Natation',
             'type_seance': 'INTENSITE', 'jour_cible': 'Jeudi',
             'periode_ambigue': True},
        ]
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['questions'] or resultat['question']
    # aucune modification définitive : le CSV reste inchangé
    assert Path(copie).read_bytes() == avant


def test_validation_finale_obligatoire(tmp_path):
    chemin, plan, dispo = _creer_plan_modif(tmp_path)
    copie = _copie_csv(chemin, tmp_path, 'validation_finale.csv')
    avant = Path(copie).read_bytes()
    # modification structurellement comprise mais invalide au regard du CDC
    resultat = appliquer_modifications_structurees(copie, {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'date_cible': '07/08/2026', 'duree': 50,
    }, dispo, date_reference=_REF_MODIF)
    assert resultat['resultat'] == 'INVALIDE'
    assert resultat['validation']['valide'] is False
    assert Path(copie).read_bytes() == avant

