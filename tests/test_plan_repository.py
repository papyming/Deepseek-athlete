# ============================================================
# FICHIER: tests/test_plan_repository.py
# RÔLE: Tests de la couche de stockage PlanRepository /
#       LocalPlanRepository.
# ============================================================

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

# Le code applicatif importe les paquets de premier niveau (src sur le path) :
# on utilise le même module `stockage` que celui utilisé par plan_csv.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from stockage import (  # noqa: E402
    PlanRepository,
    LocalPlanRepository,
    get_plan_repository,
    definir_plan_repository,
)
from src.planificateur.plan_csv import (  # noqa: E402
    lister_csv_plans,
    trouver_csv_courant,
    lire_csv_plan,
)


def _contenu_plan(discipline='CAP', duree='45'):
    return pd.DataFrame([
        {'N° semaine': 'OBJECTIF', 'Jour': '', 'Date': '15/11/2026',
         'Discipline': '', 'Type de séance': 'Objectif', 'Détails': 'Course',
         'Durée (min)': ''},
        {'N° semaine': '---', 'Jour': '---', 'Date': '---', 'Discipline': '---',
         'Type de séance': '---', 'Détails': '---', 'Durée (min)': '---'},
        {'N° semaine': '🟢S-01', 'Jour': 'Lundi', 'Date': '03/08/2026',
         'Discipline': discipline, 'Type de séance': 'Endurance fondamentale Z2',
         'Détails': f'Endurance fondamentale Z2 ({duree} min)', 'Durée (min)': duree},
    ])


def _ecrire(repo, dossier, fichier, contenu=None):
    contenu = _contenu_plan() if contenu is None else contenu
    return repo.ecrire_plan(contenu, str(Path(dossier) / fichier))


# 1. CRÉATION
def test_creation_repository_local(tmp_path):
    racine = tmp_path / 'plans'
    repo = LocalPlanRepository(str(racine))
    assert not racine.exists()
    repo.creer_stockage()
    assert racine.is_dir()
    assert isinstance(repo, PlanRepository)


def test_interface_abstraite_non_instanciable():
    with pytest.raises(TypeError):
        PlanRepository()


# 2. ÉCRITURE / 3. LECTURE
def test_ecriture_et_lecture_plan(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    chemin = _ecrire(repo, tmp_path / 'Athlete_C',
                     'Athlete_C_plan_20260801_120000.csv')
    assert Path(chemin).exists()

    df = repo.lire_plan(chemin)
    assert 'N° semaine' in df.columns
    assert df.iloc[-1]['Discipline'] == 'CAP'
    assert df.iloc[-1]['Durée (min)'] == '45'


# 4. LISTE
def test_liste_csv_plans(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    _ecrire(repo, tmp_path / 'A', 'A_plan_20260801_120000.csv')
    _ecrire(repo, tmp_path / 'B', 'B_plan_20260801_120000.csv')
    assert len(repo.lister_plans()) == 2
    fichiers = {entree['fichier'] for entree in repo.lister_plans()}
    assert fichiers == {'A_plan_20260801_120000.csv', 'B_plan_20260801_120000.csv'}


# 5. EXISTENCE
def test_existence_plan(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    chemin = _ecrire(repo, tmp_path / 'A', 'A_plan_20260801_120000.csv')
    assert repo.existe(chemin) is True
    assert repo.existe(str(tmp_path / 'A' / 'absent.csv')) is False


# 6. REMPLACEMENT
def test_remplacement_plan(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    chemin = _ecrire(repo, tmp_path / 'A', 'A_plan_20260801_120000.csv',
                     _contenu_plan(duree='45'))
    # écrasement direct
    repo.ecrire_plan(_contenu_plan(duree='60'), chemin)
    assert repo.lire_plan(chemin).iloc[-1]['Durée (min)'] == '60'
    # remplacement atomique via fichier temporaire
    temporaire = repo.chemin_temporaire(chemin)
    repo.ecrire_plan(_contenu_plan(duree='90'), temporaire)
    repo.remplacer_plan(temporaire, chemin)
    assert repo.lire_plan(chemin).iloc[-1]['Durée (min)'] == '90'
    assert not Path(temporaire).exists()


# 7. NOMS PROCHES / 8. PAS DE DÉDUPLICATION
def test_noms_proches_restent_distincts(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    _ecrire(repo, tmp_path / 'Athlete_A', 'Athlete_A_plan_20260801_120000.csv')
    _ecrire(repo, tmp_path / 'Athlete_D', 'Athlete_D_plan_20260801_120000.csv')
    entrees = repo.lister_plans()
    assert len(entrees) == 2
    athletes = {entree['athlete'] for entree in entrees}
    assert athletes == {'Athlete_A', 'Athlete_D'}


def test_plusieurs_plans_meme_athlete_non_fusionnes(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    _ecrire(repo, tmp_path / 'Athlete_K', 'Athlete_K_plan_20260801_120000.csv')
    _ecrire(repo, tmp_path / 'Athlete_K', 'Athlete_K_plan_20260901_120000.csv')
    entrees = repo.lister_plans()
    assert len(entrees) == 2
    assert len({entree['chemin'] for entree in entrees}) == 2


# 9. SOUS-RÉPERTOIRES + exclusions
def test_sous_repertoires_et_exclusions(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    _ecrire(repo, tmp_path / 'niveau1' / 'niveau2', 'A_plan_20260801_120000.csv')
    _ecrire(repo, tmp_path / 'B', 'B_plan_20260801_120000.csv')
    # exclusions : intervals et aperçu
    _ecrire(repo, tmp_path / 'B', 'B_intervals_20260801_120000.csv')
    (tmp_path / 'B' / 'B_plan_apercu_20260801_120000.pdf').write_text('x')
    entrees = repo.lister_plans()
    assert len(entrees) == 2
    assert {entree['fichier'] for entree in entrees} == {
        'A_plan_20260801_120000.csv', 'B_plan_20260801_120000.csv'
    }


# 10. AUCUN CSV
def test_aucun_csv(tmp_path):
    repo = LocalPlanRepository(str(tmp_path / 'inexistant'))
    assert repo.lister_plans() == []
    assert repo.trouver_plan_courant(str(tmp_path / 'inexistant')) is None
    assert repo.lister_plans(str(tmp_path)) == []


def test_trouver_plan_courant_le_plus_recent(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    ancien = _ecrire(repo, tmp_path / 'A', 'A_plan_20260801_120000.csv')
    # mtime garanti antérieur : la résolution d'horloge peut rendre deux
    # écritures rapprochées indiscernables (test déterministe).
    os.utime(ancien, (0, 0))
    recent = _ecrire(repo, tmp_path / 'A', 'A_plan_20260901_120000.csv')
    assert repo.trouver_plan_courant(str(tmp_path / 'A')) == recent


def test_plan_csv_utilise_le_repository_courant(tmp_path):
    repo = LocalPlanRepository(str(tmp_path))
    _ecrire(repo, tmp_path / 'A', 'A_plan_20260801_120000.csv')
    ancien = get_plan_repository()
    definir_plan_repository(repo)
    try:
        entrees = lister_csv_plans()
        assert len(entrees) == 1
        assert lire_csv_plan(entrees[0]['chemin']).iloc[-1]['Discipline'] == 'CAP'
        assert trouver_csv_courant(str(tmp_path / 'A')) == entrees[0]['chemin']
    finally:
        definir_plan_repository(ancien)
