# ============================================================
# FICHIER: tests/test_web.py
# RÔLE: Tests de la couche Web (FastAPI) de consultation des plans.
#       Chaque test utilise un repository LOCAL TEMPORAIRE : aucune
#       dépendance à outputs/plans ni à MEGAsync.
# ============================================================

import os
import socket
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from planificateur.fournisseur_ia import MockFournisseurModifications  # noqa: E402
from planificateur.fournisseurs.openrouter import (  # noqa: E402
    OpenRouterFournisseurIA,
)
from planificateur.validateur_plan import valider_plan_csv  # noqa: E402
from stockage import LocalPlanRepository  # noqa: E402
from src.web.app import creer_app  # noqa: E402
from src.web.services import agent as agent_service  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def _interdire_reseau_web(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError('Appel réseau interdit pendant les tests Web.')

    monkeypatch.setattr(socket, 'create_connection', _refuse, raising=True)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse, raising=True)


@pytest.fixture(autouse=True)
def _isoler_apercus_ia():
    agent_service.reinitialiser_apercus()
    yield
    agent_service.reinitialiser_apercus()

_JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
_DATES = ['03/08/2026', '04/08/2026', '05/08/2026', '06/08/2026',
          '07/08/2026', '08/08/2026', '09/08/2026']


_COLONNES_COMPLETES = {
    'TSS': '', 'CTL': '', 'ATL': '', 'TSB': '', 'Adaptation': '',
    'Plaisir (0-5)': '', 'Retour Athlète': '', 'Commentaires': '',
    'Niveau semaine': '', 'Séances clés': '', 'Message Envoyé ?': '',
    'Indice contrainte': '',
}


def _df_plan(valide=True):
    lignes = [
        {'N° semaine': 'OBJECTIF', 'Jour': '', 'Date': '15/11/2026', 'Discipline': '',
         'Type de séance': 'Objectif', 'Détails': 'Course', 'Durée (min)': '',
         'Journée type': '⭐', 'Contrainte planification': '', 'Message contrainte': '',
         **_COLONNES_COMPLETES},
        {'N° semaine': '---', 'Jour': '---', 'Date': '---', 'Discipline': '---',
         'Type de séance': '---', 'Détails': '---', 'Durée (min)': '---',
         'Journée type': '---', 'Contrainte planification': '', 'Message contrainte': '',
         **_COLONNES_COMPLETES},
    ]
    for jour, date in zip(_JOURS, _DATES):
        cap = jour in ('Lundi', 'Mercredi', 'Vendredi')
        lignes.append({
            'N° semaine': '🟢S-01', 'Jour': jour, 'Date': date,
            'Discipline': 'CAP' if cap else 'Repos',
            'Type de séance': 'Endurance fondamentale Z2' if cap else 'Repos',
            'Détails': 'Endurance fondamentale Z2 (45 min)' if cap else 'Repos',
            'Durée (min)': '45' if cap else '0',
            'Journée type': '🟩' if cap else '⬜',
            'Contrainte planification': '', 'Message contrainte': '',
            **_COLONNES_COMPLETES,
        })
    df = pd.DataFrame(lignes)
    if not valide:
        premiere_cap = df.index[df['Discipline'] == 'CAP'][0]
        df.at[premiere_cap, 'Durée (min)'] = '0'  # séance CAP à durée nulle
    return df


def _depot_temp(tmp_path, valide=True, dossiers=('Athlete_C',)):
    depot = LocalPlanRepository(str(tmp_path))
    for dossier in dossiers:
        nom = dossier.replace(' ', '_')
        fichier = f"{nom}_plan_20260801_120000.csv"
        depot.ecrire_plan(_df_plan(valide), str(tmp_path / dossier / fichier))
    return depot


def _client(tmp_path, **kwargs):
    return TestClient(creer_app(repository=_depot_temp(tmp_path, **kwargs)))


# 1. ACCUEIL
def test_get_accueil(tmp_path):
    reponse = _client(tmp_path).get('/')
    assert reponse.status_code == 200
    assert 'DEEPSEEK ATHLETE' in reponse.text


# 2. GET /plans (JSON)
def test_get_plans_json(tmp_path):
    reponse = _client(tmp_path).get('/plans')
    assert reponse.status_code == 200
    assert isinstance(reponse.json(), list)
    assert len(reponse.json()) == 1
    assert reponse.json()[0]['athlete'] == 'Athlete_C'
    assert reponse.json()[0]['identifiant']


# 3. LISTE VIDE
def test_liste_vide(tmp_path):
    app = creer_app(repository=LocalPlanRepository(str(tmp_path / 'vide')))
    client = TestClient(app)
    assert client.get('/plans').json() == []
    accueil = client.get('/')
    assert accueil.status_code == 200
    assert 'Aucun plan CSV disponible' in accueil.text


# 4. PLUSIEURS CSV
def test_plusieurs_csv(tmp_path):
    client = _client(tmp_path, dossiers=('A', 'B'))
    donnees = client.get('/plans').json()
    assert len(donnees) == 2
    assert {entree['athlete'] for entree in donnees} == {'A', 'B'}


# 5. NOMS PROCHES DISTINCTS
def test_noms_proches_distincts(tmp_path):
    client = _client(tmp_path, dossiers=('Athlete_A', 'Athlete_D'))
    donnees = client.get('/plans').json()
    assert len(donnees) == 2
    assert {entree['athlete'] for entree in donnees} == {'Athlete_A', 'Athlete_D'}
    assert len({entree['identifiant'] for entree in donnees}) == 2
    assert 'Athlete_A' in client.get('/').text
    assert 'Athlete_D' in client.get('/').text


# 6. OUVERTURE D'UN PLAN
def test_ouverture_plan(tmp_path):
    client = _client(tmp_path)
    identifiant = client.get('/plans').json()[0]['identifiant']
    reponse = client.get(f'/plans/{identifiant}')
    assert reponse.status_code == 200
    assert 'Endurance fondamentale Z2' in reponse.text
    assert 'Lundi' in reponse.text
    # toutes les colonnes CSV sont présentes telles quelles
    for colonne in ('Date', 'Jour', 'Discipline', 'Type de séance', 'Détails',
                    'Durée (min)', 'Journée type', 'Plaisir (0-5)',
                    'Retour Athlète', 'Commentaires', 'Niveau semaine',
                    'Séances clés', 'Message Envoyé ?'):
        assert colonne in reponse.text


# 7. PLAN INEXISTANT
def test_plan_inexistant(tmp_path):
    client = _client(tmp_path)
    assert client.get('/plans/inexistant').status_code == 404


# 8. VALIDATION OK
def test_validation_ok(tmp_path):
    client = _client(tmp_path)
    identifiant = client.get('/plans').json()[0]['identifiant']
    reponse = client.post(f'/plans/{identifiant}/validate')
    assert reponse.status_code == 200
    assert 'VALIDATION OK' in reponse.text


# 9. VALIDATION KO
def test_validation_ko(tmp_path):
    client = _client(tmp_path, valide=False)
    identifiant = client.get('/plans').json()[0]['identifiant']
    reponse = client.post(f'/plans/{identifiant}/validate')
    assert reponse.status_code == 200
    assert 'VALIDATION KO' in reponse.text
    assert 'durée nulle' in reponse.text


# 10. ACCÈS À UN CHEMIN ARBITRAIRE INTERDIT
@pytest.mark.parametrize('identifiant', [
    'inexistant', '..%2F..%2Fsecret', '..%5C..%5Csecret',
    'C:%5CWindows%5Cwin.ini', 'Athlete_C',
    'Athlete_C_plan_20260801_120000.csv',
])
def test_acces_chemin_arbitraire_interdit(tmp_path, identifiant):
    client = _client(tmp_path)
    reponse = client.get(f'/plans/{identifiant}')
    assert reponse.status_code == 404
    # aucun contenu de fichier arbitraire ne doit fuiter
    assert 'DEEPSEEK ATHLETE' not in reponse.text or 'Plan introuvable' in reponse.text


# 11. LES ROUTES UTILISENT LE REPOSITORY
def test_routes_utilisent_le_repository(tmp_path):
    class DepotEspion(LocalPlanRepository):
        def __init__(self, racine):
            super().__init__(racine)
            self.appels_lister = 0

        def lister_plans(self, racine=None):
            self.appels_lister += 1
            return super().lister_plans(racine)

    depot = DepotEspion(str(tmp_path))
    depot.ecrire_plan(_df_plan(), str(tmp_path / 'A' / 'A_plan_20260801_120000.csv'))
    client = TestClient(creer_app(repository=depot))

    assert client.get('/').status_code == 200
    assert depot.appels_lister >= 1
    appels_apres_accueil = depot.appels_lister
    assert client.get('/plans').status_code == 200
    assert depot.appels_lister > appels_apres_accueil


# ============================================================
# AGENT IA : APERÇU PUIS CONFIRMATION (fournisseur Mock, aucun réseau)
# ============================================================
DEMANDE_IA = "Réduis la durée de la sortie longue CAP du dimanche de 20 minutes."

_STRUCTURE_DUREE = {
    'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
    'type_seance': 'ENDURANCE', 'jour_cible': 'Lundi', 'duree_delta': -20,
}
_STRUCTURE_CLARIFICATION = {'action': 'INCOMPRIS',
                            'question': 'Quelle séance souhaitez-vous modifier ?'}
_STRUCTURE_CONFLIT = {
    'action': 'AJOUTER', 'discipline': 'CAP',
    'type_seance': 'ENDURANCE', 'jour_cible': 'Lundi',
}
_STRUCTURE_INVALIDE = {
    'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
    'type_seance': 'ENDURANCE', 'jour_cible': 'Lundi', 'duree': 0,
}


def _client_ia(tmp_path, structure=None, **kwargs):
    depot = _depot_temp(tmp_path, **kwargs)
    fournisseur = MockFournisseurModifications(structure=structure)
    client = TestClient(creer_app(repository=depot, fournisseur_ia=fournisseur))
    return client, depot


def _identifiant_client(client):
    return client.get('/plans').json()[0]['identifiant']


def _chemin_depot(depot):
    return depot.lister_plans()[0]['chemin']


def _contenu(depot, chemin):
    return depot.lire_plan(chemin).to_csv(index=False, sep=';')


# 12. ZONE ASSISTANT IA PRÉSENTE
def test_page_plan_contient_assistant_ia(tmp_path):
    client = _client(tmp_path)
    identifiant = _identifiant_client(client)
    page = client.get(f'/plans/{identifiant}')
    assert page.status_code == 200
    assert 'Assistant IA' in page.text
    assert 'Prévisualiser' in page.text
    assert 'Confirmer la modification' in page.text


# 12b. INDICATEUR DE TRAVAIL DE L'AGENT (état d'attente côté navigateur)
def test_page_plan_contient_indicateur_de_chargement(tmp_path):
    client = _client(tmp_path)
    identifiant = _identifiant_client(client)
    page = client.get(f'/plans/{identifiant}')
    assert page.status_code == 200
    assert "L'agent analyse votre demande et le plan" in page.text
    assert 'Analyse en cours...' in page.text
    assert 'boutonPreview.disabled = true' in page.text
    assert 'boutonPreview.disabled = false' in page.text
    assert 'textContent' in page.text


# 13. PRÉVISUALISATION VALIDE -> CSV INCHANGÉ
def test_preview_modification_valide(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    reponse = client.post(f'/plans/{identifiant}/ia/preview',
                          json={'demande': DEMANDE_IA})

    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees['resultat'] == 'APERCU'
    assert donnees['confirmation_requise'] is True
    assert isinstance(donnees['modifications'], list) and donnees['modifications']
    assert donnees['validation']['valide'] is True
    assert donnees['preview_id']
    assert 'chemin' not in donnees
    assert donnees['avant'][0]['duree'] == '45'
    assert donnees['apres'][0]['duree'] == '25'
    assert _contenu(depot, chemin) == avant


# 14. PRÉVISUALISATION CLARIFICATION -> QUESTION, CSV INCHANGÉ
def test_preview_clarification(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_CLARIFICATION)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    donnees = client.post(f'/plans/{identifiant}/ia/preview',
                          json={'demande': 'Déplace la séance.'}).json()

    assert donnees['resultat'] == 'CLARIFICATION_REQUISE'
    assert donnees['question'] == 'Quelle séance souhaitez-vous modifier ?'
    assert donnees['confirmation_requise'] is False
    assert _contenu(depot, chemin) == avant


# 15. PRÉVISUALISATION CONFLIT -> CSV INCHANGÉ
def test_preview_conflit(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_CONFLIT)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    donnees = client.post(f'/plans/{identifiant}/ia/preview',
                          json={'demande': 'Ajoute un CAP lundi.'}).json()

    assert donnees['resultat'] == 'CONFLIT'
    assert donnees['confirmation_requise'] is False
    assert any('déjà planifié' in conflit for conflit in donnees['conflits'])
    assert _contenu(depot, chemin) == avant


# 16. PRÉVISUALISATION INVALIDE -> VALIDATION KO, CSV INCHANGÉ
def test_preview_invalide(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_INVALIDE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    donnees = client.post(f'/plans/{identifiant}/ia/preview',
                          json={'demande': 'Mets la séance à 0 minute.'}).json()

    assert donnees['resultat'] == 'INVALIDE'
    assert donnees['confirmation_requise'] is False
    assert donnees['validation']['valide'] is False
    assert _contenu(depot, chemin) == avant


# 17. CONFIRMATION APRÈS APERÇU VALIDE -> ÉCRITURE
def test_confirm_apres_preview_valide(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)

    apercu = client.post(f'/plans/{identifiant}/ia/preview',
                         json={'demande': DEMANDE_IA}).json()
    reponse = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': apercu['preview_id']})

    assert reponse.status_code == 200
    resultat = reponse.json()
    assert resultat['resultat'] == 'CONFIRME'
    assert resultat['validation']['valide'] is True
    assert resultat['modifications_appliquees'] == 1

    df = depot.lire_plan(chemin)
    lundi = df[(df['Jour'] == 'Lundi') & (df['Discipline'] == 'CAP')]
    assert lundi.iloc[0]['Durée (min)'] == '25'
    assert valider_plan_csv(chemin)['valide'] is True

    # Aperçu à usage unique : une seconde confirmation est refusée.
    seconde = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': apercu['preview_id']})
    assert seconde.status_code == 409
    assert seconde.json()['resultat'] == 'PREVIEW_INCONNUE'


# 18. CONFIRMATION SANS APERÇU -> REFUS
def test_confirm_sans_preview(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    reponse = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': 'inconnu'})

    assert reponse.status_code == 409
    assert reponse.json()['resultat'] == 'PREVIEW_INCONNUE'
    assert _contenu(depot, chemin) == avant


# 19. CONFIRMATION AVEC APERÇU EXPIRÉ -> REFUS
def test_confirm_preview_expiree(tmp_path, monkeypatch):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    apercu = client.post(f'/plans/{identifiant}/ia/preview',
                         json={'demande': DEMANDE_IA}).json()
    monkeypatch.setattr(agent_service, 'DUREE_APERCU_SECONDES', 0)

    reponse = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': apercu['preview_id']})

    assert reponse.status_code == 409
    assert reponse.json()['resultat'] == 'PREVIEW_INCONNUE'
    assert _contenu(depot, chemin) == avant


# 20. CONFIRMATION APRÈS MODIFICATION DU CSV -> REFUS, CSV INCHANGÉ
def test_confirm_apres_modification_csv(tmp_path):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)

    apercu = client.post(f'/plans/{identifiant}/ia/preview',
                         json={'demande': DEMANDE_IA}).json()

    df = depot.lire_plan(chemin)
    index = df.index[(df['Jour'] == 'Lundi') & (df['Discipline'] == 'CAP')][0]
    df.at[index, 'Durée (min)'] = '50'
    depot.ecrire_plan(df, chemin)

    reponse = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': apercu['preview_id']})

    assert reponse.status_code == 409
    assert reponse.json()['resultat'] == 'PLAN_MODIFIE'
    apres = depot.lire_plan(chemin)
    assert apres.loc[index, 'Durée (min)'] == '50'


# 21. AUCUN CHEMIN PHYSIQUE ACCEPTÉ DEPUIS LE NAVIGATEUR
@pytest.mark.parametrize('preview_id', [
    'C:\\Windows\\win.ini', '..\\..\\secret.csv', 'outputs/plans/A_plan.csv',
    'A_plan_20260801_120000.csv', '../../etc/passwd',
])
def test_confirm_refuse_chemin_physique(tmp_path, preview_id):
    client, depot = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)
    identifiant = _identifiant_client(client)
    chemin = _chemin_depot(depot)
    avant = _contenu(depot, chemin)

    reponse = client.post(f'/plans/{identifiant}/ia/confirm',
                          json={'preview_id': preview_id})

    assert reponse.status_code == 409
    assert reponse.json()['resultat'] == 'PREVIEW_INCONNUE'
    assert _contenu(depot, chemin) == avant


# 22. PLAN_ID OPAQUE UNIQUEMENT
@pytest.mark.parametrize('plan_id', [
    'Athlete_C', 'Athlete_C_plan_20260801_120000.csv',
    'inconnu', 'outputs',
])
def test_ia_plan_id_opaque_uniquement(tmp_path, plan_id):
    client, _ = _client_ia(tmp_path, structure=_STRUCTURE_DUREE)

    apercu = client.post(f'/plans/{plan_id}/ia/preview',
                         json={'demande': DEMANDE_IA})
    confirmation = client.post(f'/plans/{plan_id}/ia/confirm',
                               json={'preview_id': 'x'})

    assert apercu.status_code == 404
    assert confirmation.status_code == 404


# 23. CONFIRMATION SUR UN AUTRE PLAN -> REFUS
def test_confirm_mauvais_plan(tmp_path):
    depot = _depot_temp(tmp_path, dossiers=('A', 'B'))
    fournisseur = MockFournisseurModifications(structure=_STRUCTURE_DUREE)
    client = TestClient(creer_app(repository=depot, fournisseur_ia=fournisseur))
    plans = client.get('/plans').json()
    identifiant_a = next(p['identifiant'] for p in plans if p['athlete'] == 'A')
    identifiant_b = next(p['identifiant'] for p in plans if p['athlete'] == 'B')
    chemin_b = next(p['chemin'] for p in depot.lister_plans()
                    if p['athlete'] == 'B')
    avant = _contenu(depot, chemin_b)

    apercu = client.post(f'/plans/{identifiant_a}/ia/preview',
                         json={'demande': DEMANDE_IA}).json()
    reponse = client.post(f'/plans/{identifiant_b}/ia/confirm',
                          json={'preview_id': apercu['preview_id']})

    assert reponse.status_code == 409
    assert reponse.json()['resultat'] == 'PREVIEW_INVALIDE'
    assert _contenu(depot, chemin_b) == avant


# 24. SANS FOURNISSEUR CONFIGURÉ -> INDISPONIBLE
def test_preview_sans_fournisseur(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    client = _client(tmp_path)
    identifiant = _identifiant_client(client)

    reponse = client.post(f'/plans/{identifiant}/ia/preview',
                          json={'demande': DEMANDE_IA})

    assert reponse.status_code == 503
    assert reponse.json()['resultat'] == 'INDISPONIBLE'


# ============================================================
# 25. CONFIGURATION AUTOMATIQUE DU FOURNISSEUR IA
# ============================================================
def test_creer_app_conserve_le_fournisseur_explicite(tmp_path):
    depot = _depot_temp(tmp_path)
    mock = MockFournisseurModifications(structure=_STRUCTURE_DUREE)
    application = creer_app(repository=depot, fournisseur_ia=mock)

    assert application.state.fournisseur_ia is mock


def test_creer_app_configure_openrouter_si_cle(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'cle-factice-de-test')
    monkeypatch.delenv('OPENROUTER_MODEL', raising=False)

    application = creer_app(repository=_depot_temp(tmp_path))

    assert isinstance(application.state.fournisseur_ia,
                      OpenRouterFournisseurIA)
    assert application.state.fournisseur_ia.modele == 'openrouter/free'


def test_creer_app_sans_cle_aucun_fournisseur(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

    application = creer_app(repository=_depot_temp(tmp_path))

    assert application.state.fournisseur_ia is None


def test_creer_app_prend_openrouter_model(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'cle-factice-de-test')
    monkeypatch.setenv('OPENROUTER_MODEL', 'modele/personnalise')

    application = creer_app(repository=_depot_temp(tmp_path))

    assert application.state.fournisseur_ia.modele == 'modele/personnalise'


def test_aucun_secret_dans_les_reponses_web(tmp_path, monkeypatch):
    secret = 'secret-openrouter-a-ne-jamais-exposer'
    monkeypatch.setenv('OPENROUTER_API_KEY', secret)

    depot = _depot_temp(tmp_path)
    application = creer_app(repository=depot)
    client = TestClient(application)
    identifiant = client.get('/plans').json()[0]['identifiant']

    page = client.get(f'/plans/{identifiant}')
    liste = client.get('/plans')

    assert secret not in page.text
    assert secret not in liste.text
    assert application.state.fournisseur_ia.cle_api_disponible is True
