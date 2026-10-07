# ============================================================
# FICHIER: tests/test_agent_ia.py
# RÔLE: Tests de la couche d'abstraction IA (Phase 1).
#
#       AUCUN appel API IA, AUCUN appel réseau :
#       - fournisseur Mock uniquement ;
#       - moteur existant = unique mécanisme d'application ;
#       - clarification / incompréhension / conflit => aucune écriture.
# ============================================================

import os
import socket
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from stockage import LocalPlanRepository  # noqa: E402
from src.planificateur.agent_plan_csv import FournisseurModifications  # noqa: E402
from src.planificateur.contrat_modifications import normaliser_demande  # noqa: E402
from src.planificateur.contexte_plan import (  # noqa: E402
    construire_contexte_plan,
    identifiant_logique,
)
from src.planificateur.export_csv import exporter_plan_csv  # noqa: E402
from src.planificateur.fournisseur_ia import (  # noqa: E402
    ClarificationRequise,
    FournisseurIAAbstrait,
    FournisseurIAFictif,
    MockFournisseurModifications,
    traiter_demande_ia,
)
from src.planificateur import fournisseur_ia as module_ia  # noqa: E402
from src.planificateur.generateur.generateur_semaine import (  # noqa: E402
    generer_plan_complet,
)
from src.planificateur.plan_csv import LIGNES_ENTETE  # noqa: E402
from src.web.app import creer_app  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

_JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
_REF = datetime(2026, 8, 5)  # mercredi de la 1re semaine


# ------------------------------------------------------------
# AUCUN APPEL RÉSEAU PENDANT TOUTE LA DURÉE DES TESTS IA
# ------------------------------------------------------------
@pytest.fixture(autouse=True)
def _interdire_reseau(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError('Appel réseau interdit pendant les tests IA.')

    monkeypatch.setattr(socket, 'create_connection', _refuse, raising=True)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse, raising=True)


# ------------------------------------------------------------
# PLAN DE TEST (identique au socle de modifications existant)
# ------------------------------------------------------------
def _profil():
    return {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': 14.2},
        'sport_principal': 'Triathlon',
    }


def _dispo():
    return {
        'CAP': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Samedi'],
        'Velo': ['Lundi', 'Mercredi', 'Jeudi', 'Dimanche'],
        'Natation': ['Mardi', 'Vendredi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }


def _creer_plan_ia(tmp_path):
    profil = _profil()
    dispo = _dispo()
    semaines = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), profil, dispo
    )
    plan = {
        'athlete': 'Test IA',
        'date_debut': '2026-08-03',
        'date_objectif': '2026-12-15',
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': dispo,
    }
    return exporter_plan_csv(plan, str(tmp_path)), plan, dispo


def _copie(chemin, tmp_path, nom='copie_ia.csv'):
    destination = tmp_path / nom
    destination.write_bytes(Path(chemin).read_bytes())
    return str(destination)


def _lignes_data(chemin):
    df = pd.read_csv(chemin, sep=';', encoding='utf-8-sig', dtype=str,
                     keep_default_na=False)
    return df[~df['N° semaine'].isin(LIGNES_ENTETE)].reset_index(drop=True)


def _date_iso(jour, lundi=datetime(2026, 8, 3)):
    return (lundi + timedelta(days=_JOURS.index(jour))).strftime('%Y-%m-%d')


def _fr(date_iso):
    return datetime.strptime(date_iso, '%Y-%m-%d').strftime('%d/%m/%Y')


def _jour_libre(chemin, dispo, discipline):
    data = _lignes_data(chemin)
    for jour in dispo[discipline]:
        date_iso = _date_iso(jour)
        date_fr = _fr(date_iso)
        lignes = data[data['Date'] == date_fr]
        if lignes.empty:
            continue
        valeurs = ['Vélo', 'Velo'] if discipline == 'Velo' else [discipline]
        if not any(lignes['Discipline'].isin(valeurs)):
            return date_iso, jour
    return None, None


def _date_seance(chemin, discipline, extrait_type):
    data = _lignes_data(chemin)
    lignes = data[
        (data['Discipline'] == discipline)
        & (data['Type de séance'].str.contains(extrait_type))
    ]
    assert not lignes.empty, f'Aucune séance {discipline}/{extrait_type}'
    return lignes.iloc[0]['Date']


def _struct_duree_cap():
    return {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
        'type_seance': 'ENDURANCE', 'jour_cible': 'Jeudi', 'duree': 45,
    }


# ============================================================
# 1. FOURNISSEUR MOCK
# ============================================================
def test_1_mock_fournisseur_enregistre_et_retourne():
    mock = MockFournisseurModifications(structure={'action': 'AJOUTER'})
    assert isinstance(mock, FournisseurIAAbstrait)
    assert isinstance(mock, FournisseurModifications)
    assert mock.proposer_modifications('demande', {'a': 1}) == {'action': 'AJOUTER'}
    assert mock.appels == [{'demande': 'demande', 'contexte': {'a': 1}}]
    assert FournisseurIAFictif is MockFournisseurModifications


def test_1b_mock_fournisseur_file_de_reponses_et_erreur():
    mock = MockFournisseurModifications(reponses=[{'action': 'A'}, {'action': 'B'}])
    assert mock.proposer_modifications('x', {}) == {'action': 'A'}
    assert mock.proposer_modifications('y', {}) == {'action': 'B'}

    vide = MockFournisseurModifications()
    assert vide.proposer_modifications('x', {}) is None

    defaut = MockFournisseurModifications(erreur=ClarificationRequise('?'))
    with pytest.raises(ClarificationRequise):
        defaut.proposer_modifications('x', {})


# ============================================================
# 2. DEMANDE LIBRE -> STRUCTURE -> MOTEUR
# ============================================================
def test_2_demande_libre_transmise_puis_moteur(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    mock = MockFournisseurModifications(structure=_struct_duree_cap())
    resultat = traiter_demande_ia(
        chemin, "Raccourcis l'endurance CAP du jeudi à 45 min", mock,
        disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'OK'
    assert resultat['interpretation'] == _struct_duree_cap()
    assert mock.appels
    assert mock.appels[0]['demande'].startswith('Raccourcis')


# ============================================================
# 3. STRUCTURE VALIDE -> MOTEUR
# ============================================================
def test_3_structure_valide_appliquee_par_le_moteur(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    mock = MockFournisseurModifications(structure=_struct_duree_cap())
    resultat = traiter_demande_ia(
        chemin, 'demande', mock, disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'OK'
    assert resultat['validation']['valide'] is True
    assert resultat['modifications_appliquees'] == 1
    assert resultat['apercu'][0]['apres']['duree'] == '45'


# ============================================================
# 4. STRUCTURE INVALIDE -> REJET
# ============================================================
def test_4_structure_invalide_rejetee(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    mock = MockFournisseurModifications(structure={'action': 'NIMPORTEQUOI'})
    resultat = traiter_demande_ia(
        chemin, 'demande', mock, disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'INVALIDE'
    assert resultat['erreurs']
    assert resultat['modifications_appliquees'] == 0


def test_4b_structure_non_dict_rejetee(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    mock = MockFournisseurModifications(structure='je ne suis pas un contrat')
    resultat = traiter_demande_ia(chemin, 'demande', mock, date_reference=_REF)
    assert resultat['resultat'] == 'INVALIDE'
    assert resultat['erreurs']


# ============================================================
# 5. CLARIFICATION -> AUCUN CSV MODIFIÉ
# ============================================================
def test_5_clarification_periode_sans_ecriture(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    copie = _copie(chemin, tmp_path, 'clarif.csv')
    avant = Path(copie).read_bytes()
    mock = MockFournisseurModifications(structure={
        'action': 'DEPLACER', 'discipline': 'Natation',
        'type_seance': 'INTENSITE', 'jour_cible': 'Jeudi',
        'periode_ambigue': True,
        'question': 'Cette semaine seulement ou jusqu\'à la fin du plan ?',
    })
    resultat = traiter_demande_ia(
        copie, 'déplace la natation jeudi', mock,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'PERIODE'
    assert resultat['question'] == 'Cette semaine seulement ou jusqu\'à la fin du plan ?'
    assert resultat['modifications_appliquees'] == 0
    assert Path(copie).read_bytes() == avant


def test_5b_clarification_levee_par_le_fournisseur_sans_ecriture(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    copie = _copie(chemin, tmp_path, 'clarif_levee.csv')
    avant = Path(copie).read_bytes()
    mock = MockFournisseurModifications(
        erreur=ClarificationRequise('Quel jour exactement ?', categorie='INFO_MANQUANTE')
    )
    resultat = traiter_demande_ia(
        copie, 'ajoute une séance', mock,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'INFO_MANQUANTE'
    assert resultat['questions'] == ['Quel jour exactement ?']
    assert Path(copie).read_bytes() == avant


# ============================================================
# 6. INCOMPRÉHENSION -> AUCUN CSV MODIFIÉ
# ============================================================
def test_6_incomprehension_sans_ecriture(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    copie = _copie(chemin, tmp_path, 'incompris.csv')
    avant = Path(copie).read_bytes()
    mock = MockFournisseurModifications(structure={
        'action': 'INCOMPRIS',
        'question': "Que modifier mercredi : durée, intensité ou contenu ?",
    })
    resultat = traiter_demande_ia(
        copie, 'fais quelque chose de plus dur mercredi', mock,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'INCOMPRIS'
    assert Path(copie).read_bytes() == avant


def test_6b_reponse_vide_du_fournisseur_sans_ecriture(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    copie = _copie(chemin, tmp_path, 'vide.csv')
    avant = Path(copie).read_bytes()
    mock = MockFournisseurModifications(structure=None)
    resultat = traiter_demande_ia(
        copie, 'bonjour', mock, disponibilites=dispo,
        date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['categorie'] == 'INCOMPRIS'
    assert Path(copie).read_bytes() == avant


# ============================================================
# 7. CONFLIT -> AUCUN CSV MODIFIÉ
# ============================================================
def test_7_conflit_sans_ecriture(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    copie = _copie(chemin, tmp_path, 'conflit.csv')
    avant = Path(copie).read_bytes()
    mock = MockFournisseurModifications(structure={
        'action': 'DEPLACER', 'discipline': 'CAP', 'type_seance': 'SORTIE_LONGUE',
        'date_cible': '04/08/2026',
    })
    resultat = traiter_demande_ia(
        copie, 'déplace la sortie longue', mock,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'CONFLIT'
    assert resultat['conflits']
    assert resultat['modifications_appliquees'] == 0
    assert Path(copie).read_bytes() == avant


# ============================================================
# 8. RÉCURRENCE SANS PÉRIODE -> FIN_DU_PLAN
# ============================================================
def test_8_recurrence_sans_periode_fin_du_plan(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    structure = {
        'action': 'AJOUTER', 'discipline': 'CAP', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Mercredi', 'duree': 40,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
    }
    normalisee = normaliser_demande(structure)
    assert normalisee['erreurs'] == []
    assert normalisee['questions'] == []
    assert normalisee['modifications'][0]['periode_par_defaut'] == 'FIN_DU_PLAN'

    mock = MockFournisseurModifications(structure=structure)
    resultat = traiter_demande_ia(
        chemin, 'ajoute du CAP une semaine sur deux',
        mock, disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'OK'
    dates = [a['apres']['date'] for a in resultat['apercu'] if a.get('apres')]
    assert dates[0] == '2026-08-05'
    base = datetime.strptime(dates[0], '%Y-%m-%d')
    assert all(
        (datetime.strptime(d, '%Y-%m-%d') - base).days % 14 == 0 for d in dates
    )
    assert len(dates) > 4  # va bien au-delà de 4 semaines -> fin du plan


# ============================================================
# 9. DEMANDE EXPLICITE AVEC DATE
# ============================================================
def test_9_demande_explicite_avec_date(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    date_iso, jour = _jour_libre(chemin, dispo, 'Velo')
    assert date_iso is not None
    structure = {
        'action': 'AJOUTER', 'discipline': 'VELO', 'type_seance': 'ENDURANCE',
        'date_cible': _fr(date_iso), 'duree': 90,
    }
    mock = MockFournisseurModifications(structure=structure)
    resultat = traiter_demande_ia(
        chemin, f'ajoute du vélo le {date_iso}', mock,
        disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'OK'
    date_attendue = datetime.strptime(date_iso, '%Y-%m-%d').strftime('%Y-%m-%d')
    assert all(a['apres']['date'] == date_attendue for a in resultat['apercu'])


# ============================================================
# 10. DEMANDE VMA + DISTANCE (valeur explicite, pas d'extrapolation)
# ============================================================
def test_10_demande_vma_avec_distance_explicite(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    date_fr = _date_seance(chemin, 'CAP', 'VMA|Test')
    structure = {
        'action': 'MODIFIER_DETAILS', 'discipline': 'CAP',
        'type_seance': 'INTENSITE', 'date_cible': date_fr,
        'details': 'VMA 500 m', 'details_mode': 'REMPLACER',
    }
    # le fournisseur a identifié la demande explicite (500 m)
    mock = MockFournisseurModifications(structure=structure)
    resultat = traiter_demande_ia(
        chemin, 'Mettre une intensité CAP VMA de 500 m', mock,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1
    assert resultat['apercu'][0]['apres']['date'] == \
        datetime.strptime(date_fr, '%d/%m/%Y').strftime('%Y-%m-%d')
    # la valeur appliquée est exactement celle demandée
    data = _lignes_data(chemin)
    assert (data['Détails'] == 'VMA 500 m').any()


# ============================================================
# 11. CONTEXTE ATHLÈTE TRANSMIS AU FOURNISSEUR
# ============================================================
def test_11_contexte_structure_transmis(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    donnees_athlete = {'nom': 'Athlete_C', 'vma': 18.0, 'vc': 14.2}
    mock = MockFournisseurModifications(structure=_struct_duree_cap())
    traiter_demande_ia(
        chemin, 'demande', mock,
        donnees_athlete=donnees_athlete, disponibilites=dispo,
        date_reference=_REF,
    )
    contexte = mock.appels[0]['contexte']
    assert contexte['athlete'] == donnees_athlete
    assert contexte['periode']['date_objectif'] == '2026-12-15'
    assert contexte['periode']['debut'] == '2026-08-03'
    assert 'CAP' in contexte['disciplines_disponibles']
    assert contexte['seances']
    assert contexte['identite_plan']['athlete'] == 'Test IA'
    assert contexte['identite_plan']['identifiant'] == identifiant_logique(chemin)
    # le contexte ne contient AUCUN chemin de fichier brut
    assert chemin not in repr(contexte)


# ============================================================
# 12. L'IA NE PEUT PAS ÉCRIRE DE FICHIER ELLE-MÊME
# ============================================================
def test_12_ia_ne_peut_pas_ecrire_de_fichier(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    victime = tmp_path / 'fichier_pirate.csv'
    date_iso, jour = _jour_libre(chemin, dispo, 'Velo')
    structure = {
        'action': 'AJOUTER', 'discipline': 'VELO', 'type_seance': 'ENDURANCE',
        'date_cible': _fr(date_iso), 'duree': 90,
        # clés hostiles que l'IA tenterait d'imposer : elles doivent être ignorées
        'chemin': str(victime), 'chemin_sortie': str(victime), 'fichier': str(victime),
    }
    mock = MockFournisseurModifications(structure=structure)
    resultat = traiter_demande_ia(
        chemin, 'demande', mock, disponibilites=dispo,
        date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'OK'
    # l'IA ne crée jamais le fichier qu'elle prétend viser
    assert not victime.exists()
    # seul le CSV cible (fourni par Python) a été modifié, via le moteur
    data = _lignes_data(chemin)
    assert (data['Détails'].str.contains('90 min')).any()
    # le fournisseur Mock n'expose aucune primitive d'écriture
    assert not hasattr(mock, 'ecrire')
    assert not hasattr(mock, 'ecrire_plan')


# ============================================================
# 13. LE MOTEUR EXISTANT RESTE L'UNIQUE MÉCANISME D'APPLICATION
# ============================================================
def test_13_delegation_au_moteur_existant(tmp_path, monkeypatch):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    appels = {'previsualiser': 0, 'appliquer': 0}

    def fausse_previsualisation(*args, **kwargs):
        appels['previsualiser'] += 1
        return {'resultat': 'OK', 'apercu': [], 'modifications_appliquees': 0,
                'chemin': args[0] if args else ''}

    def fausse_application(*args, **kwargs):
        appels['appliquer'] += 1
        return {'resultat': 'OK', 'apercu': [], 'modifications_appliquees': 0,
                'chemin': args[0] if args else ''}

    monkeypatch.setattr(module_ia, 'previsualiser_modifications',
                        fausse_previsualisation)
    monkeypatch.setattr(module_ia, 'appliquer_modifications_structurees',
                        fausse_application)

    mock = MockFournisseurModifications(structure=_struct_duree_cap())
    traiter_demande_ia(chemin, 'aperçu', mock, date_reference=_REF)
    assert appels['previsualiser'] == 1
    assert appels['appliquer'] == 0

    traiter_demande_ia(chemin, 'application', mock, date_reference=_REF, ecrire=True)
    assert appels['appliquer'] == 1


def test_13b_fournisseur_ia_n_ecrit_jamais_dans_le_csv():
    source = Path(module_ia.__file__).read_text(encoding='utf-8')
    for interdit in ('to_csv', 'write(', 'os.remove', 'replace('):
        assert interdit not in source, interdit


# ============================================================
# 14. ROUTE FASTAPI DE TEST AVEC MOCK
# ============================================================
def test_14_route_fastapi_avec_mock(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    date_iso, jour = _jour_libre(chemin, dispo, 'Velo')
    assert date_iso is not None
    structure = {
        'action': 'AJOUTER', 'discipline': 'VELO', 'type_seance': 'ENDURANCE',
        'date_cible': _fr(date_iso), 'duree': 90,
    }
    mock = MockFournisseurModifications(structure=structure)
    application = creer_app(
        repository=LocalPlanRepository(str(tmp_path)), fournisseur_ia=mock
    )
    client = TestClient(application)

    avant = Path(chemin).read_bytes()
    identifiant = client.get('/plans').json()[0]['identifiant']
    reponse = client.post(
        f'/plans/{identifiant}/ia',
        json={'demande': 'Ajoute une sortie vélo', 'ecrire': False},
    )
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees['resultat'] == 'OK'
    assert donnees['modifications_appliquees'] == 1
    assert mock.appels
    # mode aperçu : le CSV n'est pas modifié
    assert Path(chemin).read_bytes() == avant


def test_14b_route_fastapi_sans_fournisseur_indisponible(tmp_path, monkeypatch):
    # Sans clé API, l'application ne configure aucun fournisseur.
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    _creer_plan_ia(tmp_path)
    application = creer_app(repository=LocalPlanRepository(str(tmp_path)))
    client = TestClient(application)
    identifiant = client.get('/plans').json()[0]['identifiant']
    reponse = client.post(
        f'/plans/{identifiant}/ia', json={'demande': 'test', 'ecrire': False}
    )
    assert reponse.status_code == 503
    assert reponse.json()['resultat'] == 'INDISPONIBLE'


# ============================================================
# 15. AUCUN APPEL RÉSEAU (fixture autouse + test explicite)
# ============================================================
def test_15_aucun_appel_reseau(tmp_path, monkeypatch):
    appels = []

    def _refuse(*args, **kwargs):
        appels.append((args, kwargs))
        raise AssertionError('Appel réseau interdit')

    monkeypatch.setattr(socket, 'create_connection', _refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse)

    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    mock = MockFournisseurModifications(structure=_struct_duree_cap())
    resultat = traiter_demande_ia(
        chemin, 'demande', mock, disponibilites=dispo, date_reference=_REF,
    )
    assert resultat['resultat'] == 'OK'
    assert appels == []


def test_15b_construire_contexte_sans_chemin_brut(tmp_path):
    chemin, plan, dispo = _creer_plan_ia(tmp_path)
    contexte = construire_contexte_plan(chemin, donnees_athlete={'nom': 'X'})
    assert chemin not in repr(contexte)
    assert 'identite_plan' in contexte
    assert 'seances' in contexte
