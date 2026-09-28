# ============================================================
# FICHIER: tests/test_e2e_ia_csv.py
# RÔLE: Tests END-TO-END DÉTERMINISTES (aucun réseau) de la chaîne
#
#           demande → fournisseur IA Mock → contrat
#                   → traiter_demande_ia → moteur existant
#                   → copie temporaire du CSV → validation existante
#
#       Chaque test :
#       - travaille sur une COPIE TEMPORAIRE (jamais outputs/plans) ;
#       - utilise le VRAI moteur et le VRAI validateur (non simulés) ;
#       - vérifie l'empreinte du CSV d'origine AVANT / APRÈS ;
#       - existe en variante "référence externe optionnelle" (CSV non
#         versionné, tests ignorés s'il est absent) et en variante construite.
#
#       AUCUN APPEL RÉSEAU : une fixture autouse l'interdit.
# ============================================================

import hashlib
import os
import shutil
import socket
import sys
from datetime import datetime

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, 'src'))

from planificateur.export_csv import exporter_plan_csv  # noqa: E402
from planificateur.fournisseur_ia import (  # noqa: E402
    MockFournisseurModifications,
    traiter_demande_ia,
)
from planificateur.generateur.generateur_semaine import (  # noqa: E402
    generer_plan_complet,
)
from planificateur.plan_csv import construire_plan_depuis_csv  # noqa: E402
from planificateur.validateur_plan import valider_plan_csv  # noqa: E402

# CSV de référence externe OPTIONNEL (jamais versionné, aucun athlète réel
# codé en dur) : les tests qui l'utilisent sont ignorés s'il est absent.
CSV_REFERENCE = os.path.join(
    RACINE, 'outputs', 'plans', 'Athlete_D',
    'Athlete_D_plan_20260921_161329.csv',
)

DEMANDE_DUREE = "Réduis la durée de la sortie longue CAP du dimanche de 20 minutes."
DEMANDE_NATATION = "Intensité natation le jeudi."
DEMANDE_VELO = "Rajoute 1 lundi sur 2 une séance d'endurance en vélo de 3h."
DEMANDE_DEPLACER = "Mettre toutes les intensités de CAP le mercredi."
DEMANDE_CLARIFICATION = "Déplace la séance."
DEMANDE_CONTRAINTE = (
    "Ajoute une séance qui crée volontairement une contrainte avec la séance existante."
)


@pytest.fixture(autouse=True)
def _interdire_reseau(monkeypatch):
    def _refuse(*args, **kwargs):
        raise AssertionError('Appel réseau interdit pendant ces tests.')

    monkeypatch.setattr(socket, 'create_connection', _refuse, raising=True)
    monkeypatch.setattr(socket.socket, 'connect_ex', _refuse, raising=True)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _sha256(chemin):
    with open(chemin, 'rb') as flux:
        return hashlib.sha256(flux.read()).hexdigest()


@pytest.fixture
def copie_reference(tmp_path):
    """Copie temporaire du CSV réel validé + empreinte de l'original."""
    if not os.path.exists(CSV_REFERENCE):
        pytest.skip(f'CSV de référence absent : {CSV_REFERENCE}')
    original_hash = _sha256(CSV_REFERENCE)
    copie = tmp_path / os.path.basename(CSV_REFERENCE)
    shutil.copy2(CSV_REFERENCE, str(copie))
    return str(copie), original_hash


def _lancer(copie, structure, demande, date_reference):
    """Chaîne existante : Mock → traiter_demande_ia → moteur → validation."""
    mock = MockFournisseurModifications(structure=structure)
    return traiter_demande_ia(
        copie, demande, mock,
        date_reference=datetime.strptime(date_reference, '%Y-%m-%d'),
        ecrire=True, chemin_sortie=copie,
    )


def _sessions(chemin, *, date=None, jour=None, discipline=None,
              type_contient=None):
    plan = construire_plan_depuis_csv(chemin)
    resultats = []
    for semaine in plan['semaines']:
        for jour_plan in semaine['jours']:
            for seance in jour_plan['seances']:
                if date and jour_plan['date'] != date:
                    continue
                if jour and jour_plan['jour'] != jour:
                    continue
                if discipline and seance['discipline'] != discipline:
                    continue
                if type_contient and type_contient.lower() not in seance['type'].lower():
                    continue
                resultats.append({
                    'date': jour_plan['date'],
                    'jour': jour_plan['jour'],
                    'discipline': seance['discipline'],
                    'type': seance['type'],
                    'duree': seance['duree'],
                    'details': seance['details'],
                })
    return resultats


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


def _creer_plan_csv(tmp_path):
    profil, dispo = _profil(), _dispo()
    semaines = generer_plan_complet(
        datetime(2026, 8, 3), datetime(2026, 12, 15), profil, dispo
    )
    plan = {
        'athlete': 'Test E2E', 'date_debut': '2026-08-03',
        'date_objectif': '2026-12-15', 'nb_semaines': len(semaines),
        'semaines': semaines, 'profil': profil, 'disponibilites': dispo,
    }
    return exporter_plan_csv(plan, str(tmp_path))


# ============================================================
# 1. MODIFICATION DE DURÉE (cas E2E réel : 90 → 70)
# ============================================================
def test_modifier_duree_sortie_longue_dimanche(copie_reference):
    copie, original_hash = copie_reference
    structure = {
        'action': 'MODIFIER_DUREE', 'discipline': 'CAP',
        'type_seance': 'SORTIE_LONGUE', 'jour_cible': 'Dimanche',
        'duree_delta': -20,
    }
    avant = _sessions(copie, date='2026-10-11', discipline='CAP',
                      type_contient='sortie longue')
    assert len(avant) == 1
    avant = avant[0]

    resultat = _lancer(copie, structure, DEMANDE_DUREE, '2026-10-11')

    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1
    assert resultat['interpretation'] == structure

    apres = _sessions(copie, date='2026-10-11', discipline='CAP',
                      type_contient='sortie longue')
    assert len(apres) == 1
    apres = apres[0]
    assert avant['duree'] == 90
    assert apres['duree'] == 70 == avant['duree'] - 20
    assert apres['discipline'] == 'CAP'
    assert 'sortie longue' in apres['type'].lower()
    assert apres['jour'] == 'Dimanche'

    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


# ============================================================
# 2. AJOUT SIMPLE (natation intensité le jeudi)
# ============================================================
def test_ajout_natation_intensite_jeudi(copie_reference):
    copie, original_hash = copie_reference
    avant = _sessions(copie, discipline='Natation')
    structure = {
        'action': 'AJOUTER', 'discipline': 'Natation',
        'type_seance': 'INTENSITE', 'jour_cible': 'Jeudi',
    }

    resultat = _lancer(copie, structure, DEMANDE_NATATION, '2026-10-11')

    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1
    apres = _sessions(copie, discipline='Natation')
    assert len(apres) == len(avant) + 1

    ajoutees = [s for s in apres if s not in avant]
    assert len(ajoutees) == 1
    ajoutee = ajoutees[0]
    assert ajoutee['jour'] == 'Jeudi'
    assert ajoutee['date'] == '2026-10-08'
    assert ajoutee['discipline'] == 'Natation'
    # Libellé canonique du type INTENSITE pour la natation (moteur existant).
    assert ajoutee['type'] == 'Technique + Seuil'
    assert ajoutee['duree'] == 45

    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


# ============================================================
# 3. AJOUT RÉCURRENT (vélo lundi 1/2, 180 min, FIN_DU_PLAN)
# ============================================================
def test_ajout_recurrent_velo_lundi_espacement(copie_reference):
    copie, original_hash = copie_reference
    structure = {
        'action': 'AJOUTER', 'discipline': 'Vélo', 'type_seance': 'ENDURANCE',
        'jour_cible': 'Lundi', 'duree': 180,
        'frequence': {'type': 'UNE_SEMAINE_SUR_DEUX'},
        'periode': {'type': 'FIN_DU_PLAN'},
    }

    resultat = _lancer(copie, structure, DEMANDE_VELO, '2026-08-03')

    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 6

    velos = _sessions(copie, discipline='Vélo', jour='Lundi')
    dates = sorted(s['date'] for s in velos)
    assert dates == [
        '2026-08-03', '2026-08-17', '2026-08-31',
        '2026-09-14', '2026-09-28', '2026-10-12',
    ]
    for seance in velos:
        assert seance['duree'] == 180
        assert seance['type'] == 'Endurance Z2'

    jours = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
    assert all((suivant - precedent).days == 14
               for precedent, suivant in zip(jours, jours[1:]))

    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


# ============================================================
# 4. DÉPLACEMENT
# ============================================================
def test_deplacement_unique_intensite_cap(copie_reference):
    copie, original_hash = copie_reference
    structure = {
        'action': 'DEPLACER', 'discipline': 'CAP',
        'type_seance': 'INTENSITE', 'jour_cible': 'Mercredi',
    }

    resultat = _lancer(copie, structure, DEMANDE_DEPLACER, '2026-10-05')

    assert resultat['resultat'] == 'OK'
    assert resultat['modifications_appliquees'] == 1
    assert _sessions(copie, date='2026-10-06', discipline='CAP') == []
    apres = _sessions(copie, date='2026-10-07', discipline='CAP')
    assert len(apres) == 1
    assert apres[0]['duree'] == 54
    assert apres[0]['type'] == 'VC'
    assert apres[0]['jour'] == 'Mercredi'

    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


def test_deplacement_multiple_detecte_ambigu(copie_reference):
    copie, original_hash = copie_reference
    structure = {
        'action': 'DEPLACER', 'discipline': 'CAP',
        'type_seance': 'INTENSITE', 'jour_cible': 'Mercredi',
        'periode': {'type': 'FIN_DU_PLAN'},
    }
    avant_copie = _sha256(copie)

    resultat = _lancer(copie, structure, DEMANDE_DEPLACER, '2026-08-03')

    assert resultat['resultat'] == 'AMBIGU'
    assert resultat['modifications_appliquees'] == 0
    assert resultat['ambiguites']
    assert _sha256(copie) == avant_copie
    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


# ============================================================
# 5. CLARIFICATION (aucune écriture)
# ============================================================
def test_clarification_sans_modification(copie_reference):
    copie, original_hash = copie_reference
    structure = {'action': 'INCOMPRIS',
                 'question': 'Quelle séance souhaitez-vous déplacer ?'}
    avant_copie = _sha256(copie)

    resultat = _lancer(copie, structure, DEMANDE_CLARIFICATION, '2026-10-11')

    assert resultat['resultat'] == 'CLARIFICATION_REQUISE'
    assert resultat['modifications_appliquees'] == 0
    assert resultat['interpretation'] == structure
    assert _sha256(copie) == avant_copie
    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


# ============================================================
# 6. CONFLIT / CONTRAINTE (le MOTEUR décide, pas l'IA)
# ============================================================
def test_conflit_detecte_par_le_moteur(copie_reference):
    copie, original_hash = copie_reference
    # Modification de contrat valide : l'IA ne décide d'aucune contrainte.
    structure = {
        'action': 'AJOUTER', 'discipline': 'CAP',
        'type_seance': 'ENDURANCE', 'jour_cible': 'Mardi',
    }
    avant_copie = _sha256(copie)

    resultat = _lancer(copie, structure, DEMANDE_CONTRAINTE, '2026-10-05')

    assert resultat['resultat'] == 'CONFLIT'
    assert resultat['modifications_appliquees'] == 0
    assert any('déjà planifié' in conflit for conflit in resultat['conflits'])
    assert _sha256(copie) == avant_copie
    assert valider_plan_csv(copie)['valide'] is True
    assert _sha256(CSV_REFERENCE) == original_hash


def test_contrainte_detectee_par_le_validateur(tmp_path):
    chemin = _creer_plan_csv(tmp_path)
    assert valider_plan_csv(chemin)['valide'] is True
    avant = _sha256(chemin)

    # AJOUTER une longue séance CAP un mercredi déjà chargé en vélo :
    # l'IA fournit une modification valide, le moteur applique, mais le
    # validateur existant refuse (CAP > 50 % du vélo) -> aucune écriture.
    structure = {
        'action': 'AJOUTER', 'discipline': 'CAP',
        'type_seance': 'ENDURANCE', 'jour_cible': 'Mercredi', 'duree': 100,
    }

    resultat = _lancer(chemin, structure, DEMANDE_CONTRAINTE, '2026-08-05')

    assert resultat['resultat'] == 'INVALIDE'
    assert resultat['validation'] is not None
    assert resultat['validation']['valide'] is False
    assert any('50 %' in erreur for erreur in resultat['validation']['erreurs'])
    assert _sha256(chemin) == avant
    assert valider_plan_csv(chemin)['valide'] is True
