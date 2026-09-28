# ============================================================
# SCRIPT: scripts/e2e_ia_csv.py
# RÔLE: Test END-TO-END RÉEL (hors pytest) de la chaîne
#
#           demande → OpenRouterFournisseurIA → contrat
#                   → moteur de modifications → validation CSV
#
#       SÉCURITÉ :
#       - travaille UNIQUEMENT sur une copie temporaire ;
#       - ne modifie JAMAIS le CSV d'origine ni outputs/plans ;
#       - réutilise les fonctions existantes (fournisseur, moteur,
#         validateur) sans en réimplémenter la logique ;
#       - supprime la copie temporaire à la fin.
#
#       ENTRÉE (aucun athlète ni chemin réel n'est codé) :
#       - soit un chemin CSV fourni en argument ;
#       - soit, à défaut, un CSV de test neutre généré dans un
#         dossier temporaire par le script lui-même.
#
#       Ce script appelle réellement OpenRouter (pas de mock).
# ============================================================

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, 'src'))

from planificateur.export_csv import exporter_plan_csv  # noqa: E402
from planificateur.fournisseur_ia import traiter_demande_ia  # noqa: E402
from planificateur.fournisseurs.openrouter import (  # noqa: E402
    OpenRouterFournisseurIA,
)
from planificateur.generateur.generateur_semaine import (  # noqa: E402
    generer_plan_complet,
)
from planificateur.plan_csv import construire_plan_depuis_csv  # noqa: E402
from planificateur.validateur_plan import valider_plan_csv  # noqa: E402

# --- Cas de test unique (générique) ---
DEMANDE = "Réduis la durée de la sortie longue CAP du dimanche de 20 minutes."


def _sha256(chemin):
    with open(chemin, 'rb') as flux:
        return hashlib.sha256(flux.read()).hexdigest()


def _creer_csv_test(dossier):
    """Génère un plan CSV neutre contenant des sorties longues CAP du dimanche."""
    profil = {
        'niveau_estime': 'Intermédiaire',
        'objectif_principal': '',
        'physiologie': {'vma': 18.0, 'vc': None},
        'sport_principal': 'Course à pied',
    }
    disponibilites = {
        'CAP': ['Mardi', 'Jeudi', 'Dimanche'],
        'Velo': [],
        'Natation': [],
        'bi_quotidien_nb': 0,
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []},
    }
    semaines = generer_plan_complet(
        datetime(2026, 8, 1), datetime(2026, 12, 15), profil, disponibilites
    )
    plan = {
        'athlete': 'Athlete_Test',
        'date_debut': '2026-08-01',
        'date_objectif': '2026-12-15',
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': disponibilites,
    }
    return exporter_plan_csv(plan, dossier)


def _seances_cible(chemin):
    """Sorties longues CAP du dimanche du plan, triées par date."""
    plan = construire_plan_depuis_csv(chemin)
    trouves = []
    for semaine in plan['semaines']:
        for jour in semaine['jours']:
            if jour['jour'] != 'Dimanche':
                continue
            for seance in jour['seances']:
                if (seance['discipline'] == 'CAP'
                        and 'sortie longue' in seance['type'].lower()):
                    trouves.append({
                        'date': jour['date'],
                        'jour': jour['jour'],
                        'discipline': seance['discipline'],
                        'type': seance['type'],
                        'duree': seance['duree'],
                        'details': seance['details'],
                    })
    return sorted(trouves, key=lambda seance: seance['date'])


def _seances_du_jour(chemin, date_iso):
    return [s for s in _seances_cible(chemin) if s['date'] == date_iso]


def _resume(seance):
    return (f"{seance['date']} | {seance['jour']} | {seance['discipline']} | "
            f"{seance['type']} | {seance['duree']} min | "
            f"{seance['details']}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    print('=' * 60)
    print('TEST END-TO-END IA → CSV')
    print('=' * 60)

    dossier_temp = tempfile.mkdtemp(prefix='e2e_ia_')
    try:
        if argv:
            csv_source = os.path.abspath(argv[0])
            if not os.path.exists(csv_source):
                print(f'CSV introuvable : {csv_source}')
                return 1
        else:
            source_dir = os.path.join(dossier_temp, 'source')
            os.makedirs(source_dir, exist_ok=True)
            csv_source = _creer_csv_test(source_dir)
            print("Aucun CSV fourni : un CSV de test neutre a été généré "
                  f"({os.path.basename(csv_source)}).")

        original_hash = _sha256(csv_source)

        # Copie temporaire (le CSV d'origine n'est jamais touché).
        copie = os.path.join(dossier_temp, os.path.basename(csv_source))
        shutil.copy2(csv_source, copie)

        # Séance cible : dernière sortie longue CAP du dimanche du plan.
        cibles = _seances_cible(copie)
        if not cibles:
            print('Aucune sortie longue CAP du dimanche dans le plan. '
                  "Rien n'est modifié.")
            return 1
        avant = cibles[-1]
        date_cible = avant['date']

        # Fournisseur OpenRouter réel + demande exacte.
        fournisseur = OpenRouterFournisseurIA()

        # Chaîne existante : IA -> moteur -> validation (copie seule).
        resultat = traiter_demande_ia(
            copie, DEMANDE, fournisseur,
            date_reference=datetime.strptime(date_cible, '%Y-%m-%d'),
            ecrire=True, chemin_sortie=copie,
        )

        interpretation = resultat.get('interpretation')
        reponse_ia = json.dumps(interpretation, ensure_ascii=False, indent=2,
                                default=str)

        # Séance APRÈS.
        apres_liste = _seances_du_jour(copie, date_cible)
        apres = apres_liste[0] if len(apres_liste) == 1 else None

        # Validation du CSV résultant (validateur existant).
        validation = valider_plan_csv(copie)

        # Vérifications automatiques.
        original_inchange = _sha256(csv_source) == original_hash
        duree_ok = (apres is not None
                    and apres['duree'] == avant['duree'] - 20)
        discipline_ok = apres is not None and apres['discipline'] == 'CAP'
        type_ok = (apres is not None
                   and 'sortie longue' in apres['type'].lower())
        jour_ok = apres is not None and apres['jour'] == 'Dimanche'

        # Rapport.
        print(f'CSV testé : {os.path.basename(csv_source)} (copie temporaire)')
        print(f'Séance ciblée : {date_cible} (sortie longue CAP du dimanche)')
        print(f'Demande : {DEMANDE}')
        print('Réponse IA :')
        print(reponse_ia)
        print(f"Moteur : {resultat.get('resultat')} "
              f"(modifications={resultat.get('modifications_appliquees')})")
        print(f"AVANT : {_resume(avant)}")
        print(f"APRÈS : {_resume(apres) if apres else 'séance introuvable'}")
        print(f"Validation CSV : {'OK' if validation['valide'] else 'KO'}")
        if not validation['valide']:
            print('   erreurs : ' + ' ; '.join(validation['erreurs']))
        print(f"Durée -20 min : {'OK' if duree_ok else 'KO'}")
        print(f"Discipline CAP : {'OK' if discipline_ok else 'KO'}")
        print(f"Type SORTIE_LONGUE : {'OK' if type_ok else 'KO'}")
        print(f"Jour Dimanche : {'OK' if jour_ok else 'KO'}")
        print(f"Original modifié : {'OUI' if not original_inchange else 'NON'}")

        global_ok = (
            resultat.get('resultat') == 'OK'
            and validation['valide']
            and duree_ok and discipline_ok and type_ok and jour_ok
            and original_inchange
        )
        print(f"Résultat global : {'OK' if global_ok else 'KO'}")
        print('=' * 60)
        return 0 if global_ok else 1
    finally:
        # Suppression de la copie temporaire.
        shutil.rmtree(dossier_temp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
