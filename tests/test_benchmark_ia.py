# ============================================================
# FICHIER: tests/test_benchmark_ia.py
# RÔLE: Tests DÉTERMINISTES du benchmark Phase 2B.
#
#       AUCUN APPEL RÉSEAU :
#       - le benchmark reçoit toujours un fournisseur mocké ;
#       - une fixture autouse interdit toute connexion sortante ;
#       - aucune clé réelle n'est utilisée.
#
#       Les tests NE MODIFIENT AUCUN CSV (vérifié par empreinte).
# ============================================================

import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from planificateur import benchmark_ia  # noqa: E402
from planificateur.banc_essai_ia import (  # noqa: E402
    DEMANDES_REFERENCE,
    evaluer_criteres,
)
from planificateur.benchmark_ia import (  # noqa: E402
    MODELE_PAR_DEFAUT,
    STATUT_CLARIFICATION,
    STATUT_ERREUR,
    STATUT_NON_CONFORME,
    STATUT_OK,
    classer_reponse,
    demandes_benchmark,
    formater_rapport,
    fournisseur_par_defaut,
    lancer_benchmark,
    main,
)
from planificateur.contexte_plan import construire_contexte_plan  # noqa: E402
from planificateur.export_csv import exporter_plan_csv  # noqa: E402
from planificateur.fournisseur_ia import (  # noqa: E402
    MockFournisseurModifications,
)
from planificateur.fournisseurs import (  # noqa: E402
    ConfigurationManquante,
    OpenRouterFournisseurIA,
)
from planificateur.fournisseurs.base_http import (  # noqa: E402
    valider_structure_ia,
)
from planificateur.generateur.generateur_semaine import (  # noqa: E402
    generer_plan_complet,
)

_CLE_FACTICE = 'cle-factice-de-test'


@pytest.fixture(autouse=True)
def _interdire_reseau(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError('Appel réseau interdit pendant les tests IA.')

    monkeypatch.setattr(socket, 'create_connection', _refuse, raising=True)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse, raising=True)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _structure_ajout_velo():
    return {
        'action': 'AJOUTER', 'discipline': 'Vélo', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Lundi', 'duree': 180,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
    }


def _profil():
    return {
        'niveau_estime': 'Intermédiaire', 'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': 14.2}, 'sport_principal': 'Triathlon',
    }


def _dispo():
    return {
        'CAP': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Samedi'],
        'Velo': ['Lundi', 'Mercredi', 'Jeudi', 'Dimanche'],
        'Natation': ['Mardi', 'Vendredi'],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }


def _creer_plan(tmp_path):
    profil, dispo = _profil(), _dispo()
    semaines = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), profil, dispo
    )
    plan = {
        'athlete': 'Test Benchmark', 'date_debut': '2026-08-03',
        'date_objectif': '2026-12-15', 'nb_semaines': len(semaines),
        'semaines': semaines, 'profil': profil, 'disponibilites': dispo,
    }
    return exporter_plan_csv(plan, str(tmp_path)), plan, dispo


# ------------------------------------------------------------
# Configuration / modèle par défaut
# ------------------------------------------------------------
def test_demandes_benchmark_10():
    demandes = demandes_benchmark()
    assert len(demandes) == 10
    assert [d['id'] for d in demandes] == list(range(1, 11))
    for entree in demandes:
        assert isinstance(entree['demande'], str) and entree['demande']
        assert isinstance(entree['criteres'], dict)


def test_modele_par_defaut_openrouter_free():
    assert MODELE_PAR_DEFAUT == 'openrouter/free'


def test_fournisseur_par_defaut_est_openrouter(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    provider = fournisseur_par_defaut(api_key=_CLE_FACTICE)
    assert isinstance(provider, OpenRouterFournisseurIA)
    assert provider.nom == 'openrouter'
    assert provider.cle_api_disponible is True


def test_fournisseur_par_defaut_modele_env(monkeypatch):
    monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
    assert fournisseur_par_defaut(api_key=_CLE_FACTICE).modele == 'openrouter/free'
    monkeypatch.setenv('OPENROUTER_MODEL', 'modele/gratuit:free')
    assert fournisseur_par_defaut(api_key=_CLE_FACTICE).modele == 'modele/gratuit:free'
    assert fournisseur_par_defaut(api_key=_CLE_FACTICE,
                                  modele='force').modele == 'force'


# ------------------------------------------------------------
# Classification
# ------------------------------------------------------------
@pytest.mark.parametrize('structure, erreur, erreurs_contrat, attendu', [
    (_structure_ajout_velo(), None, [], STATUT_OK),
    ({'action': 'INCOMPRIS', 'question': '?'}, None, [],
     STATUT_CLARIFICATION),
    ({'action': 'AJOUTER', 'champ_inconnu': 1}, None, ['champ inconnu'],
     STATUT_NON_CONFORME),
    (None, None, [], STATUT_NON_CONFORME),
    (None, 'ConfigurationManquante: OPENROUTER_API_KEY', [], STATUT_ERREUR),
])
def test_classer_reponse(structure, erreur, erreurs_contrat, attendu):
    assert classer_reponse(structure, erreur=erreur,
                           erreurs_contrat=erreurs_contrat) == attendu


# ------------------------------------------------------------
# Benchmark avec fournisseur mocké (aucun réseau)
# ------------------------------------------------------------
def test_benchmark_mock_ok():
    mock = MockFournisseurModifications(structure=_structure_ajout_velo())
    rapport = lancer_benchmark(mock, contexte={})
    assert len(rapport['resultats']) == 10
    assert rapport['resume']['ok'] == 10
    assert rapport['resume']['conformes_contrat'] == 10
    assert rapport['resume']['erreurs'] == 0
    for resultat in rapport['resultats']:
        assert resultat['statut'] == STATUT_OK
        assert resultat['conforme_contrat'] is True
        assert 'temps_secondes' in resultat


def test_benchmark_mock_clarification():
    mock = MockFournisseurModifications(
        structure={'action': 'INCOMPRIS', 'question': 'Précisez.'}
    )
    rapport = lancer_benchmark(mock, contexte={})
    assert rapport['resume']['clarifications'] == 10
    assert rapport['resume']['ok'] == 0
    assert all(r['statut'] == STATUT_CLARIFICATION for r in rapport['resultats'])


def test_benchmark_mock_non_conforme():
    mock = MockFournisseurModifications(
        structure={'action': 'AJOUTER', 'champ_inconnu': 1}
    )
    rapport = lancer_benchmark(mock, contexte={})
    assert rapport['resume']['non_conformes'] == 10
    assert all(r['statut'] == STATUT_NON_CONFORME for r in rapport['resultats'])
    assert all(r['erreurs_contrat'] for r in rapport['resultats'])


def test_benchmark_erreur_fournisseur():
    mock = MockFournisseurModifications(
        erreur=ConfigurationManquante('OPENROUTER_API_KEY')
    )
    rapport = lancer_benchmark(mock, contexte={})
    assert rapport['resume']['erreurs'] == 10
    assert all('OPENROUTER_API_KEY' in r['erreur'] for r in rapport['resultats'])
    assert all(r['statut'] == STATUT_ERREUR for r in rapport['resultats'])
    assert all(r['structure'] is None for r in rapport['resultats'])


def test_benchmark_avec_criteres():
    demandes = [{
        'id': 1, 'demande': "Rajoute un lundi sur 2 du vélo.",
        'criteres': {
            'action': {'AJOUTER'}, 'discipline': {'Vélo'},
            'jour_cible': {'Lundi'}, 'frequence': {'UNE_SEMAINE_SUR_DEUX'},
        },
    }]
    mock = MockFournisseurModifications(structure=_structure_ajout_velo())
    rapport = lancer_benchmark(mock, demandes=demandes, contexte={})
    resultat = rapport['resultats'][0]
    assert resultat['criteres_ok'] is True
    assert resultat['criteres']['tous'] is True


def test_benchmark_dynamique_par_demande():
    def dynamique(demande, contexte_recu):
        if 'Déplace la séance' in demande or 'plus dur' in demande:
            return {'action': 'INCOMPRIS', 'question': 'Précisez.'}
        return _structure_ajout_velo()

    mock = MockFournisseurModifications(structure=dynamique)
    rapport = lancer_benchmark(mock, contexte={})
    clarifications = [
        r for r in rapport['resultats'] if r['statut'] == STATUT_CLARIFICATION
    ]
    assert len(clarifications) == 2
    assert rapport['resume']['erreurs'] == 0


def test_benchmark_sans_contexte():
    mock = MockFournisseurModifications(
        structure={'action': 'INCOMPRIS', 'question': '?'}
    )
    rapport = lancer_benchmark(mock, contexte=None)
    assert rapport['contexte_erreur'] is None
    assert len(rapport['resultats']) == 10
    assert mock.appels[0]['contexte'] == {}


# ------------------------------------------------------------
# Contexte : lecture seule du CSV
# ------------------------------------------------------------
def test_benchmark_contexte_depuis_csv(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    mock = MockFournisseurModifications(
        structure={'action': 'INCOMPRIS', 'question': '?'}
    )
    rapport = lancer_benchmark(mock, chemin_csv=chemin)
    assert rapport['contexte_erreur'] is None
    contexte = mock.appels[0]['contexte']
    assert 'identite_plan' in contexte
    assert contexte['identite_plan']['athlete'] == 'Test Benchmark'


def test_benchmark_ne_modifie_aucun_csv(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    avant = Path(chemin).read_bytes()
    mock = MockFournisseurModifications(structure=_structure_ajout_velo())
    lancer_benchmark(mock, chemin_csv=chemin, disponibilites=dispo)
    assert Path(chemin).read_bytes() == avant


# ------------------------------------------------------------
# Sécurité : aucun moteur, aucun appel réseau
# ------------------------------------------------------------
def test_benchmark_ne_lance_pas_le_moteur():
    source = (Path(__file__).resolve().parent.parent
              / 'src' / 'planificateur' / 'benchmark_ia.py')
    contenu = source.read_text(encoding='utf-8')
    for interdit in ('appliquer_modifications_structurees',
                     'previsualiser_modifications', 'moteur_modifications',
                     'to_csv', '.write('):
        assert interdit not in contenu, interdit


def test_benchmark_nappelle_pas_le_reseau_avec_mock():
    appels = []

    class FournisseurEspion(MockFournisseurModifications):
        def proposer_modifications(self, demande, contexte):
            appels.append(demande)
            return super().proposer_modifications(demande, contexte)

    mock = FournisseurEspion(structure=_structure_ajout_velo())
    lancer_benchmark(mock, contexte={})
    assert len(appels) == 10


# ------------------------------------------------------------
# Affichage / CLI
# ------------------------------------------------------------
def test_formater_rapport_contient_structure_et_statut():
    mock = MockFournisseurModifications(structure=_structure_ajout_velo())
    rapport = lancer_benchmark(mock, contexte={})
    texte = formater_rapport(rapport)
    assert 'Benchmark IA' in texte
    assert f'[{STATUT_OK}]' in texte
    assert 'openrouter' not in texte  # fournisseur mock
    assert '"action": "AJOUTER"' in texte
    assert 'Réponse structurée reçue' in texte


def test_afficher_rapport_utilise_sortie_injectee():
    mock = MockFournisseurModifications(
        structure={'action': 'INCOMPRIS', 'question': '?'}
    )
    rapport = lancer_benchmark(mock, contexte={})
    sorties = []
    benchmark_ia.afficher_rapport(rapport, sortie=sorties.append)
    assert len(sorties) == 1
    assert STATUT_CLARIFICATION in sorties[0]


def test_main_sans_reseau(monkeypatch, capsys):
    rapport = {
        'fournisseur': 'openrouter', 'modele': 'openrouter/free',
        'contexte_erreur': None, 'resultats': [],
        'resume': {
            'total': 10, 'ok': 10, 'clarifications': 0, 'erreurs': 0,
            'non_conformes': 0, 'conformes_contrat': 10,
            'temps_total_secondes': 0.0, 'temps_moyen_secondes': 0.0,
        },
    }
    monkeypatch.setattr(benchmark_ia, 'lancer_benchmark',
                        lambda **kwargs: rapport)
    code = main([])
    assert code == 0
    assert 'Résumé' in capsys.readouterr().out

    rapport['resume']['erreurs'] = 1
    monkeypatch.setattr(benchmark_ia, 'lancer_benchmark',
                        lambda **kwargs: rapport)
    assert main([]) == 1


# ------------------------------------------------------------
# Attentes Phase 2B (structures conformes attendues de l'IA)
# ------------------------------------------------------------
_ATTENTES_PHASE_2B = {
    1: {
        'action': 'AJOUTER', 'discipline': 'CAP',
        'type_seance': 'INTENSITE', 'date_cible': '2026-11-26',
        'jour_cible': 'Jeudi', 'details': 'VMA 500 m',
    },
    2: {
        'action': 'AJOUTER', 'discipline': 'Vélo',
        'type_seance': 'ENDURANCE', 'jour_cible': 'Lundi', 'duree': 180,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
        'periode': {'type': 'FIN_DU_PLAN'},
    },
    3: {
        'action': 'DEPLACER', 'discipline': 'CAP',
        'type_seance': 'INTENSITE', 'jour_cible': 'Mercredi',
    },
    4: {
        'action': 'SUPPRIMER', 'discipline': 'Natation',
        'periode': {'type': 'DATES', 'debut': '2026-08-01',
                    'fin': '2026-08-10'},
    },
    5: {
        'action': 'AJOUTER_RESSOURCE', 'type_seance': 'RENFORCEMENT',
        'jour_cible': 'Vendredi', 'ressources': ['https://youtu.be/exemple'],
        'frequence': {'type': 'HEBDOMADAIRE'},
        'periode': {'type': 'FIN_DU_PLAN'},
    },
    6: {'action': 'INCOMPRIS',
        'question': 'Quelle séance et vers quel jour ?'},
    7: {'action': 'INCOMPRIS',
        'question': 'Quelle séance rendre plus dure mercredi ?'},
    9: {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
        'type_seance': 'SORTIE_LONGUE', 'jour_cible': 'Dimanche',
        'duree_delta': -20, 'periode': {'type': 'FIN_DU_PLAN'},
    },
    10: {
        'action': 'AJOUTER', 'discipline': 'Natation',
        'type_seance': 'INTENSITE', 'jour_cible': 'Jeudi',
        'periode': {'type': 'FIN_DU_PLAN'},
    },
}


def _est_ajout_exploitable(structure):
    return (
        structure.get('action') == 'AJOUTER'
        and bool(structure.get('discipline'))
        and bool(structure.get('type_seance'))
    )


@pytest.mark.parametrize('identifiant', sorted(_ATTENTES_PHASE_2B))
def test_attente_phase_2b_conforme_et_criteres(identifiant):
    structure = _ATTENTES_PHASE_2B[identifiant]
    entree = next(e for e in DEMANDES_REFERENCE if e['id'] == identifiant)

    assert valider_structure_ia(structure) == []
    if entree['criteres'].get('clarification'):
        assert classer_reponse(structure) == STATUT_CLARIFICATION
    else:
        assert classer_reponse(structure) == STATUT_OK

    criteres = evaluer_criteres(structure, entree['criteres'])
    assert criteres['tous'] is True, (identifiant, criteres)


def test_attentes_non_clarification_pour_demandes_claires():
    for identifiant in (1, 2, 3, 4, 5, 9, 10):
        assert classer_reponse(_ATTENTES_PHASE_2B[identifiant]) == STATUT_OK


def test_attentes_clarification_structuree():
    for identifiant in (6, 7):
        structure = _ATTENTES_PHASE_2B[identifiant]
        assert valider_structure_ia(structure) == []
        assert classer_reponse(structure) == STATUT_CLARIFICATION


def test_attente_duree_entiere_en_minutes():
    structure = _ATTENTES_PHASE_2B[2]
    assert isinstance(structure['duree'], int)
    assert structure['duree'] == 180
    assert valider_structure_ia(structure) == []
    invalide = dict(structure, duree='3h')
    assert valider_structure_ia(invalide)


def test_attente_url_brute_sans_markdown():
    ressources = _ATTENTES_PHASE_2B[5]['ressources']
    assert ressources == ['https://youtu.be/exemple']
    for ressource in ressources:
        assert '](' not in ressource
        assert not ressource.startswith('[')


def test_attente_champs_objet_jamais_tableau():
    for structure in _ATTENTES_PHASE_2B.values():
        for champ in ('cible', 'periode', 'contraintes'):
            if champ in structure:
                assert isinstance(structure[champ], dict), (champ, structure)


def test_attente_annee_issue_du_contexte():
    structure = _ATTENTES_PHASE_2B[4]
    annee = structure['periode']['debut'][:4]
    assert annee == structure['periode']['fin'][:4]
    assert annee == '2026'
    assert annee != '2025'


def test_attente_demande_8_jamais_ajout_vide():
    vide = {'action': 'AJOUTER'}
    assert not _est_ajout_exploitable(vide)

    complet = {'action': 'AJOUTER', 'discipline': 'CAP',
               'type_seance': 'ENDURANCE', 'jour_cible': 'Samedi'}
    assert _est_ajout_exploitable(complet)
    assert valider_structure_ia(complet) == []

    clarification = {'action': 'INCOMPRIS',
                     'question': 'Quelle séance souhaitez-vous ajouter ?'}
    assert valider_structure_ia(clarification) == []
    assert classer_reponse(clarification) == STATUT_CLARIFICATION
