# ============================================================
# FICHIER: tests/test_fournisseurs_ia.py
# RÔLE: Tests des adaptateurs IA (Mistral, Gemini, OpenRouter) et
#       du banc d'essai.
#
#       AUCUN APPEL RÉSEAU :
#       - httpx.MockTransport simule toutes les réponses HTTP ;
#       - une fixture autouse interdit les connexions sortantes ;
#       - aucune clé réelle n'est utilisée (valeurs factices).
# ============================================================

import json
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
)

from planificateur.banc_essai_ia import (  # noqa: E402
    DEMANDES_REFERENCE,
    est_clarification,
    evaluer_criteres,
    tester_fournisseur as lancer_banc,
)
from planificateur.contexte_plan import construire_contexte_plan  # noqa: E402
from planificateur.export_csv import exporter_plan_csv  # noqa: E402
from planificateur.fournisseur_ia import (  # noqa: E402
    MockFournisseurModifications,
    traiter_demande_ia,
)
from planificateur.fournisseurs import (  # noqa: E402
    ConfigurationManquante,
    ErreurHTTPFournisseur,
    GeminiFournisseurIA,
    MistralFournisseurIA,
    OpenRouterFournisseurIA,
    ReponseInvalide,
    parser_reponse_ia,
    valider_structure_ia,
)
from planificateur.fournisseurs import base_http as module_base  # noqa: E402
from planificateur.generateur.generateur_semaine import (  # noqa: E402
    generer_plan_complet,
)

_JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
_REF = datetime(2026, 8, 5)
_CLE_FACTICE = 'cle-factice-de-test'

PROVIDERS = [
    (MistralFournisseurIA, 'MISTRAL_API_KEY', 'MISTRAL_MODEL', 'mistral-small-latest'),
    (GeminiFournisseurIA, 'GEMINI_API_KEY', 'GEMINI_MODEL', 'gemini-flash-latest'),
    (OpenRouterFournisseurIA, 'OPENROUTER_API_KEY', 'OPENROUTER_MODEL', 'openrouter/free'),
]


@pytest.fixture(autouse=True)
def _interdire_reseau(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError('Appel réseau interdit pendant les tests IA.')

    monkeypatch.setattr(socket, 'create_connection', _refuse, raising=True)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse, raising=True)


# ------------------------------------------------------------
# Helpers HTTP simulés
# ------------------------------------------------------------
def _corps(cls, contenu):
    if cls is GeminiFournisseurIA:
        return {'candidates': [{'content': {'parts': [{'text': contenu}]}}]}
    return {'choices': [{'message': {'content': contenu}}]}


def _handler(cls, contenu=None, *, status=200, body=None, texte=None,
             exception=None):
    appels = []

    def handler(request):
        appels.append(request)
        if exception is not None:
            raise exception
        if texte is not None:
            return httpx.Response(status, text=texte)
        charge = body if body is not None else _corps(cls, contenu)
        return httpx.Response(status, json=charge)

    return handler, appels


def _provider(cls, handler, api_key=_CLE_FACTICE, **kwargs):
    return cls(api_key=api_key, transport=httpx.MockTransport(handler), **kwargs)


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
        'athlete': 'Test Banc', 'date_debut': '2026-08-03',
        'date_objectif': '2026-12-15', 'nb_semaines': len(semaines),
        'semaines': semaines, 'profil': profil, 'disponibilites': dispo,
    }
    return exporter_plan_csv(plan, str(tmp_path)), plan, dispo


# ============================================================
# CONFIGURATION / CLÉ API
# ============================================================
@pytest.mark.parametrize('cls, var_cle, var_modele, modele_defaut', PROVIDERS)
def test_cle_absente_erreur_explicite(monkeypatch, cls, var_cle, var_modele,
                                      modele_defaut):
    monkeypatch.delenv(var_cle, raising=False)
    handler, appels = _handler(cls, contenu='{}')
    provider = _provider(cls, handler, api_key=None)
    assert provider.cle_api_disponible is False
    with pytest.raises(ConfigurationManquante) as erreur:
        provider.proposer_modifications('demande', {})
    assert var_cle in str(erreur.value)
    assert appels == []  # aucune requête si la clé est absente


@pytest.mark.parametrize('cls, var_cle, var_modele, modele_defaut', PROVIDERS)
def test_cle_presente_dans_la_requete(monkeypatch, cls, var_cle, var_modele,
                                      modele_defaut):
    monkeypatch.setenv(var_cle, _CLE_FACTICE)
    handler, appels = _handler(cls, contenu=json.dumps({'action': 'INCOMPRIS',
                                                        'question': '?'}))
    provider = _provider(cls, handler, api_key=None)
    assert provider.cle_api_disponible is True
    provider.proposer_modifications('demande', {})
    assert len(appels) == 1


@pytest.mark.parametrize('cls, var_cle, var_modele, modele_defaut', PROVIDERS)
def test_modele_configurable(monkeypatch, cls, var_cle, var_modele, modele_defaut):
    monkeypatch.delenv(var_modele, raising=False)
    assert cls(api_key=_CLE_FACTICE).modele == modele_defaut
    monkeypatch.setenv(var_modele, 'modele-personnalise')
    assert cls(api_key=_CLE_FACTICE).modele == 'modele-personnalise'
    assert cls(api_key=_CLE_FACTICE, model='param-modele').modele == 'param-modele'


def test_openrouter_modele_gratuit_configurable(monkeypatch):
    monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
    assert OpenRouterFournisseurIA(api_key=_CLE_FACTICE).modele == 'openrouter/free'
    monkeypatch.setenv('OPENROUTER_MODEL', 'modele/gratuit:free')
    assert OpenRouterFournisseurIA(api_key=_CLE_FACTICE).modele == 'modele/gratuit:free'


def test_cle_non_affichee_dans_erreur(monkeypatch):
    monkeypatch.delenv('MISTRAL_API_KEY', raising=False)
    handler, _ = _handler(MistralFournisseurIA, status=401,
                          body={'error': 'unauthorized'})
    provider = _provider(MistralFournisseurIA, handler, api_key='SECRET-DUMMY')
    with pytest.raises(ErreurHTTPFournisseur) as erreur:
        provider.proposer_modifications('demande', {})
    assert 'SECRET-DUMMY' not in str(erreur.value)


# ============================================================
# PARSING STRICT
# ============================================================
@pytest.mark.parametrize('cls', [MistralFournisseurIA, GeminiFournisseurIA,
                                 OpenRouterFournisseurIA])
def test_reponse_json_correcte(cls):
    contenu = json.dumps(_structure_ajout_velo())
    handler, appels = _handler(cls, contenu=contenu)
    structure = _provider(cls, handler).proposer_modifications('demande', {})
    assert structure['action'] == 'AJOUTER'
    assert structure['discipline'] == 'Vélo'
    assert len(appels) == 1


@pytest.mark.parametrize('cls', [p[0] for p in PROVIDERS])
@pytest.mark.parametrize('texte', [
    'ceci n\'est pas du JSON',
    '```json\n{"action": "INCOMPRIS"}\n```',
    '{"action": "INCOMPRIS"} puis du texte',
    '{"action": "ACTION_INCONNUE"}',
    '{"action": "AJOUTER", "champ_inconnu": 1}',
    '{"action": "AJOUTER", "discipline": "Ping-Pong", "jour_cible": "Lundi"}',
    '{"action": "AJOUTER", "jour_cible": "Lundi", "periode": {"type": "JAMAIS"}}',
    '',
])
def test_reponse_invalide_rejetee(cls, texte):
    handler, _ = _handler(cls, texte=texte)
    with pytest.raises(ReponseInvalide):
        _provider(cls, handler).proposer_modifications('demande', {})


def test_structure_invalide_detectee():
    assert valider_structure_ia({'action': 'AJOUTER', 'foo': 1})
    assert valider_structure_ia({'action': 'INCONNUE'})
    assert valider_structure_ia(None)
    assert valider_structure_ia({})
    assert valider_structure_ia({'modifications': []})
    assert valider_structure_ia({'action': 'AJOUTER', 'cible': {'inconnu': 1}})
    assert valider_structure_ia({'action': 'AJOUTER', 'discipline': 'Ping-Pong'})


def test_parser_reponse_ia_champ_inconnu_explicite():
    with pytest.raises(ReponseInvalide) as erreur:
        parser_reponse_ia('{"action": "AJOUTER", "couleur": "rouge"}')
    assert 'couleur' in str(erreur.value)


@pytest.mark.parametrize('cls', [p[0] for p in PROVIDERS])
def test_reponse_clarification_acceptee(cls):
    contenu = json.dumps({'action': 'INCOMPRIS', 'question': 'Quelle séance ?'})
    handler, _ = _handler(cls, contenu=contenu)
    structure = _provider(cls, handler).proposer_modifications('déplace la séance', {})
    assert est_clarification(structure) is True


# ============================================================
# ERREURS HTTP / RÉSEAU / FOURNISSEUR
# ============================================================
@pytest.mark.parametrize('cls', [p[0] for p in PROVIDERS])
def test_erreur_http(cls):
    handler, _ = _handler(cls, status=500, body={'error': 'boom'})
    with pytest.raises(ErreurHTTPFournisseur) as erreur:
        _provider(cls, handler).proposer_modifications('demande', {})
    assert erreur.value.statut == 500


@pytest.mark.parametrize('cls', [p[0] for p in PROVIDERS])
def test_timeout(cls):
    handler, _ = _handler(cls, exception=httpx.TimeoutException('trop long'))
    with pytest.raises(ErreurHTTPFournisseur) as erreur:
        _provider(cls, handler).proposer_modifications('demande', {})
    assert erreur.value.statut == 'TIMEOUT'


@pytest.mark.parametrize('cls', [p[0] for p in PROVIDERS])
def test_erreur_fournisseur_corps_invalide(cls):
    handler, _ = _handler(cls, body={'autre': 'chose'})
    with pytest.raises(ReponseInvalide):
        _provider(cls, handler).proposer_modifications('demande', {})


# ============================================================
# SÉCURITÉ
# ============================================================
def test_aucun_chemin_physique_dans_la_requete(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contexte = construire_contexte_plan(chemin, donnees_athlete={'nom': 'X'})
    contenu = json.dumps({'action': 'INCOMPRIS', 'question': '?'})
    handler, appels = _handler(MistralFournisseurIA, contenu=contenu)
    _provider(MistralFournisseurIA, handler).proposer_modifications(
        'demande', contexte
    )
    corps = appels[0].content.decode('utf-8')
    assert chemin not in corps
    assert str(tmp_path) not in corps
    assert 'identite_plan' in corps


def test_adaptateurs_sans_acces_disque():
    paquet = Path(module_base.__file__).parent
    sources = ''.join(
        f.read_text(encoding='utf-8') for f in paquet.glob('*.py')
    )
    for interdit in ('to_csv', '.write(', 'os.remove', 'shutil', 'open(',
                     'os.listdir', 'os.walk'):
        assert interdit not in sources, interdit


def test_aucune_cle_en_dur_dans_le_code():
    paquet = Path(module_base.__file__).parent
    motif = re.compile(r'''(API_KEY|api_key)\s*=\s*['"][^'"]+['"]''')
    for fichier in paquet.glob('*.py'):
        source = fichier.read_text(encoding='utf-8')
        for ligne in source.splitlines():
            ligne_nettoyee = ligne.strip()
            if ligne_nettoyee.startswith('#'):
                continue
            assert not motif.search(ligne_nettoyee), (fichier.name, ligne)


def test_reponse_ia_invalide_aucune_modification_csv(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    avant = Path(chemin).read_bytes()
    handler, _ = _handler(MistralFournisseurIA, texte='réponse non JSON')
    provider = _provider(MistralFournisseurIA, handler)
    resultat = traiter_demande_ia(
        chemin, 'demande', provider, disponibilites=dispo,
        date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'ERREUR_IA'
    assert resultat['erreurs']
    assert Path(chemin).read_bytes() == avant


def test_cle_absente_aucune_modification_csv(monkeypatch, tmp_path):
    monkeypatch.delenv('MISTRAL_API_KEY', raising=False)
    chemin, plan, dispo = _creer_plan(tmp_path)
    avant = Path(chemin).read_bytes()
    provider = MistralFournisseurIA(api_key=None)
    resultat = traiter_demande_ia(
        chemin, 'demande', provider, disponibilites=dispo,
        date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'ERREUR_IA'
    assert 'MISTRAL_API_KEY' in ' '.join(resultat['erreurs'])
    assert Path(chemin).read_bytes() == avant


def test_adaptateur_reel_bout_en_bout_sans_reseau(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contenu = json.dumps({
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
        'type_seance': 'ENDURANCE', 'jour_cible': 'Jeudi', 'duree': 45,
    })
    handler, _ = _handler(MistralFournisseurIA, contenu=contenu)
    provider = _provider(MistralFournisseurIA, handler)
    resultat = traiter_demande_ia(
        chemin, "Raccourcis l'endurance CAP du jeudi", provider,
        disponibilites=dispo, date_reference=_REF, ecrire=True,
    )
    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1


# ============================================================
# BANC D'ESSAI
# ============================================================
def test_banc_10_demandes_reference(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contexte = construire_contexte_plan(chemin, donnees_athlete={'nom': 'X'})
    mock = MockFournisseurModifications(
        structure={'action': 'INCOMPRIS', 'question': '?'}
    )
    rapport = lancer_banc(mock, contexte=contexte)
    assert len(rapport['resultats']) == 10
    assert rapport['resume']['total'] == 10
    assert rapport['resume']['conformes'] == 10
    for resultat in rapport['resultats']:
        assert resultat['fournisseur'] == 'MockFournisseurModifications'
        assert 'temps_secondes' in resultat
        assert resultat['conforme_contrat'] is True


def test_banc_ne_modifie_pas_le_csv(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contexte = construire_contexte_plan(chemin)
    mock = MockFournisseurModifications(structure=_structure_ajout_velo())
    avant = Path(chemin).read_bytes()
    lancer_banc(mock, contexte=contexte)
    assert Path(chemin).read_bytes() == avant


def test_banc_ne_lance_pas_le_moteur():
    source = (Path(__file__).resolve().parent.parent
              / 'src' / 'planificateur' / 'banc_essai_ia.py')
    contenu = source.read_text(encoding='utf-8')
    for interdit in ('moteur_modifications', 'get_plan_repository',
                     'previsualiser_modifications', 'to_csv', '.write('):
        assert interdit not in contenu, interdit


def test_banc_criteres_factuels():
    structure_velo = _structure_ajout_velo()
    criteres = DEMANDES_REFERENCE[1]['criteres']
    resultats = evaluer_criteres(structure_velo, criteres)
    assert resultats['action'] is True
    assert resultats['discipline'] is True
    assert resultats['jour_cible'] is True
    assert resultats['frequence'] is True
    assert resultats['tous'] is True

    clarification = {'action': 'INCOMPRIS', 'question': 'Quelle séance ?'}
    assert evaluer_criteres(clarification, {'clarification': True})['tous'] is True
    assert evaluer_criteres(structure_velo, {'clarification': True})['tous'] is False


def test_banc_avec_structures_par_demande(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contexte = construire_contexte_plan(chemin)

    def dynamique(demande, contexte_recu):
        if 'Déplace la séance' in demande or 'plus dur' in demande:
            return {'action': 'INCOMPRIS', 'question': 'Précisez.'}
        return _structure_ajout_velo()

    mock = MockFournisseurModifications(structure=dynamique)
    rapport = lancer_banc(mock, contexte=contexte)
    clarification = [
        r for r in rapport['resultats'] if r['clarification']
    ]
    assert len(clarification) == 2
    assert rapport['resume']['echecs'] == 0


def test_mock_existant_toujours_fonctionnel():
    mock = MockFournisseurModifications(structure={'action': 'AJOUTER'})
    assert mock.proposer_modifications('x', {'a': 1}) == {'action': 'AJOUTER'}
    assert mock.appels[0]['demande'] == 'x'


def test_demandes_reference_bien_formees():
    assert len(DEMANDES_REFERENCE) == 10
    for index, entree in enumerate(DEMANDES_REFERENCE, start=1):
        assert entree['id'] == index
        assert isinstance(entree['demande'], str) and entree['demande']
        assert isinstance(entree['criteres'], dict)


def test_aucun_appel_reseau_pendant_les_tests(tmp_path):
    chemin, plan, dispo = _creer_plan(tmp_path)
    contenu = json.dumps({'action': 'INCOMPRIS', 'question': '?'})
    handler, appels = _handler(GeminiFournisseurIA, contenu=contenu)
    provider = _provider(GeminiFournisseurIA, handler)
    assert provider.proposer_modifications('demande', {}) == {
        'action': 'INCOMPRIS', 'question': '?'
    }
    assert len(appels) == 1


# ============================================================
# OPENROUTER : PROMPT RENFORCÉ + PRÉPARATION DE SORTIE
# (les autres fournisseurs ne sont pas concernés)
# ============================================================
def _handler_sequence(cls, contenus, *, statut=200):
    """Handler MockTransport qui renvoie des contenus successifs."""
    appels = []

    def handler(request):
        appels.append(request)
        index = min(len(appels) - 1, len(contenus) - 1)
        contenu = contenus[index]
        if isinstance(contenu, dict):
            charge = contenu
        else:
            charge = _corps(cls, contenu)
        return httpx.Response(statut, json=charge)

    return handler, appels


def test_openrouter_prompt_contient_regles_cles():
    handler, appels = _handler(
        OpenRouterFournisseurIA, contenu=json.dumps({'action': 'INCOMPRIS',
                                                     'question': '?'})
    )
    _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'demande', {}
    )
    payload = json.loads(appels[0].content.decode('utf-8'))
    systeme = payload['messages'][0]['content']
    for extrait in (
        'UN SEUL objet JSON', 'Jamais de Markdown', 'AJOUTER',
        'AJOUTER_RESSOURCE', 'RENFORCEMENT', 'DATES', 'FIN_DU_PLAN',
        'duree_delta', 'INCOMPRIS', 'Contrainte',
    ):
        assert extrait in systeme, extrait


def test_openrouter_reessai_apres_texte_avant_json():
    handler, appels = _handler_sequence(OpenRouterFournisseurIA, [
        'Voici la réponse : {"action": "INCOMPRIS"}',
        json.dumps({'action': 'INCOMPRIS', 'question': 'Quelle séance ?'}),
    ])
    structure = _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'Déplace la séance.', {}
    )
    assert structure == {'action': 'INCOMPRIS', 'question': 'Quelle séance ?'}
    assert len(appels) == 2
    second = json.loads(appels[1].content.decode('utf-8'))
    assert 'RAPPEL' in second['messages'][1]['content']


def test_openrouter_reessai_apres_reponse_vide():
    handler, appels = _handler_sequence(OpenRouterFournisseurIA, [
        {'choices': [{'message': {'content': ''}}]},
        json.dumps(_structure_ajout_velo()),
    ])
    structure = _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'demande', {}
    )
    assert structure['action'] == 'AJOUTER'
    assert len(appels) == 2


def test_openrouter_echoue_apres_reessais():
    handler, appels = _handler_sequence(OpenRouterFournisseurIA, [
        'pas du JSON', 'toujours pas du JSON',
    ])
    with pytest.raises(ReponseInvalide):
        _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
            'demande', {}
        )
    assert len(appels) == 2


def test_openrouter_pas_de_reessai_sur_erreur_http():
    handler, appels = _handler(OpenRouterFournisseurIA, status=500,
                               body={'error': 'boom'})
    with pytest.raises(ErreurHTTPFournisseur):
        _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
            'demande', {}
        )
    assert len(appels) == 1


def test_mistral_sans_reessai_sur_reponse_invalide():
    handler, appels = _handler(MistralFournisseurIA, contenu='pas du JSON')
    with pytest.raises(ReponseInvalide):
        _provider(MistralFournisseurIA, handler).proposer_modifications(
            'demande', {}
        )
    assert len(appels) == 1


def _prompt_openrouter():
    handler, appels = _handler(
        OpenRouterFournisseurIA,
        contenu=json.dumps({'action': 'INCOMPRIS', 'question': '?'}),
    )
    _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'demande', {}
    )
    return json.loads(appels[0].content.decode('utf-8'))['messages'][0]['content']


@pytest.mark.parametrize('champ', ['cible', 'periode', 'contraintes'])
def test_openrouter_champ_objet_mal_forme_ne_plante_pas(champ):
    structure = {'action': 'AJOUTER', 'discipline': 'CAP',
                 'type_seance': 'INTENSITE', champ: ['x']}
    handler, appels = _handler(OpenRouterFournisseurIA,
                               contenu=json.dumps(structure))
    with pytest.raises(ReponseInvalide):
        _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
            'demande', {}
        )
    assert len(appels) == 2


def test_openrouter_reessai_corrige_champ_objet():
    handler, appels = _handler_sequence(OpenRouterFournisseurIA, [
        json.dumps({'action': 'AJOUTER', 'discipline': 'CAP',
                    'type_seance': 'INTENSITE', 'cible': ['CAP']}),
        json.dumps(_structure_ajout_velo()),
    ])
    structure = _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'demande', {}
    )
    assert structure['action'] == 'AJOUTER'
    assert len(appels) == 2


def test_openrouter_prompt_durees_en_minutes():
    systeme = _prompt_openrouter()
    for extrait in ('ENTIER en MINUTES', '3h = 180', '1h30 = 90',
                    '45 min = 45'):
        assert extrait in systeme, extrait


def test_openrouter_prompt_annee_non_inventee():
    systeme = _prompt_openrouter()
    for extrait in ("ne l'invente JAMAIS", 'contexte du plan',
                    "jamais l'année courante"):
        assert extrait in systeme, extrait


def test_openrouter_prompt_ajouter_exploitable():
    systeme = _prompt_openrouter()
    for extrait in ('AJOUTER doit être EXPLOITABLE',
                    'discipline ET type_seance', 'jamais un AJOUT vide'):
        assert extrait in systeme, extrait


def test_openrouter_prompt_url_brute_sans_markdown():
    systeme = _prompt_openrouter()
    for extrait in ('chaîne brute', 'lien Markdown', 'jamais de balises'):
        assert extrait in systeme, extrait


def test_openrouter_prompt_champs_objet_jamais_tableaux():
    systeme = _prompt_openrouter()
    assert 'OBJETS JSON' in systeme
    assert 'jamais des tableaux' in systeme


def test_openrouter_prompt_type_seance_strict():
    systeme = _prompt_openrouter()
    for extrait in ('TYPES DE SÉANCE (STRICT)', 'SORTIE LONGUE Z2',
                    'ne va JAMAIS', 'type_seance', 'details',
                    'Ne crée jamais un nouveau type_seance'):
        assert extrait in systeme, extrait


@pytest.mark.parametrize('mauvais', [
    'SORTIE LONGUE Z2', 'SEUIL Z4', 'ENDURANCE Z2', 'INTENSITE Z5',
])
def test_type_seance_avec_zone_rejete(mauvais):
    structure = {'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
                 'type_seance': mauvais}
    assert valider_structure_ia(structure)


@pytest.mark.parametrize('correct', [
    'SORTIE_LONGUE', 'SEUIL', 'ENDURANCE', 'INTENSITE', 'FARTLEK',
    'RECUPERATION', 'RENFORCEMENT', 'COMPETITION',
])
def test_type_seance_canonique_accepte(correct):
    structure = {'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
                 'type_seance': correct}
    assert valider_structure_ia(structure) == []


def test_openrouter_type_avec_zone_rejete_et_reessaye():
    contenu = json.dumps({'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
                          'type_seance': 'SORTIE LONGUE Z2'})
    handler, appels = _handler(OpenRouterFournisseurIA, contenu=contenu)
    with pytest.raises(ReponseInvalide):
        _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
            'demande', {}
        )
    assert len(appels) == 2


def test_openrouter_type_canonique_accepte():
    structure = {'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
                 'type_seance': 'SORTIE_LONGUE', 'jour_cible': 'Dimanche',
                 'duree_delta': -20}
    handler, appels = _handler(OpenRouterFournisseurIA,
                               contenu=json.dumps(structure))
    resultat = _provider(OpenRouterFournisseurIA, handler).proposer_modifications(
        'demande', {}
    )
    assert resultat['type_seance'] == 'SORTIE_LONGUE'
    assert len(appels) == 1
