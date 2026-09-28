# ============================================================
# FICHIER: src/planificateur/main_plan.py
# RÔLE: Planification principale d'un athlète.
#       Le moteur fabrique le CSV ; les exports (PDF / Intervals)
#       sont construits à partir du CSV courant.
# ============================================================

import os
import sys
import math
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .chargeur import charger_profil, charger_disponibilites, charger_seances
from .generateur.generateur_semaine import generer_plan_complet
from .generateur.semaine import extraire_courses
from stockage import get_plan_repository
from .export_csv import exporter_plan_csv
from .export_intervals import exporter_intervals
from .export_pdf_plan import exporter_pdf_plan
from .exports_csv_source import exporter_exports_depuis_csv, exporter_depuis_csv_courant
from .plan_csv import trouver_csv_courant
from .validateur_plan import valider_plan_csv
from utils.validators import valider_coherence_biquotidien
from utils.parsers import parser_date_debut


def _plan_dir_athlete(nom: str) -> str:
    """Dossier de plans d'un athlète (localisation fournie par le dépôt)."""
    return get_plan_repository().dossier_plan(nom)


def construire_plan_athlete(athlete_dir: str, date_debut: Optional[str] = None) -> Dict:
    """Fabrique le plan interne (sans export). Ne touche pas au moteur."""
    if not os.path.exists(athlete_dir):
        return {"error": f"Dossier {athlete_dir} introuvable"}

    profil = charger_profil(athlete_dir)
    if not profil:
        return {"error": "Profil non trouvé"}

    disponibilites = charger_disponibilites(athlete_dir)
    if not disponibilites:
        return {"error": "Disponibilités non trouvées"}

    validation_bi = valider_coherence_biquotidien(
        disponibilites,
        profil.get('nom', 'Inconnu'),
        disponibilites.get('bi_quotidien_capacite_brute')
    )
    if not validation_bi['valide']:
        print('\nPLANIFICATION BLOQUÉE')
        print(f"Athlète : {validation_bi['athlete']}")
        print(validation_bi['message'])
        print("Veuillez corriger les réponses de l'athlète avant de générer le plan.")
        return {
            'error': 'Données bi-quotidien incohérentes ou insuffisantes',
            'bi_quotidien_validation': validation_bi
        }

    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')

    sport_principal = profil.get('sport_principal')
    if sport_principal is None:
        print("   ⚠️ Sport principal absent du profil; aucun défaut silencieux appliqué.")

    seances_vma = []
    seances_vc = []
    if vma and not math.isnan(vma) and vma > 0:
        seances_vma = charger_seances(athlete_dir, 'VMA')
    if vc and not math.isnan(vc) and vc > 0:
        seances_vc = charger_seances(athlete_dir, 'VC')

    aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date_debut:
        debut = parser_date_debut(date_debut)
    else:
        debut = aujourd_hui

    date_objectif = profil.get('date_objectif')
    if date_objectif:
        if isinstance(date_objectif, str):
            try:
                date_objectif = datetime.strptime(date_objectif, '%Y-%m-%d')
            except ValueError:
                date_objectif = None
    if not date_objectif:
        date_objectif = debut + timedelta(days=56)

    courses_parsed = extraire_courses(
        profil.get('courses_preparatoires', []), date_objectif.year
    )
    courses_parsed = [
        course for course in courses_parsed if debut <= course['date'] <= date_objectif
    ]
    courses_parsed.sort(key=lambda x: x['date'])

    semaines = generer_plan_complet(
        debut=debut,
        date_objectif=date_objectif,
        profil=profil,
        disponibilites=disponibilites,
        seances_vma=seances_vma,
        seances_vc=seances_vc,
        courses_preparatoires=courses_parsed
    )

    plan_global = {
        'athlete': profil.get('nom', 'Inconnu'),
        'sport_principal': sport_principal,
        'date_debut': debut.strftime('%Y-%m-%d'),
        'date_objectif': date_objectif.strftime('%Y-%m-%d'),
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': disponibilites,
        'courses_preparatoires': courses_parsed
    }
    plan_dir = _plan_dir_athlete(plan_global['athlete'])
    return {'plan': plan_global, 'plan_dir': plan_dir}


def generer_csv_athlete(athlete_dir: str, date_debut: Optional[str] = None,
                        forcer: bool = False, confirmation=None) -> Dict:
    """Génère / recrée le CSV proposé (le moteur fabrique le CSV).

    Si un CSV courant existe déjà et que ``forcer`` est faux, ``confirmation``
    (callable renvoyant True/False) est appelée pour éviter d'écraser
    silencieusement le travail manuel du coach.
    """
    resultat = construire_plan_athlete(athlete_dir, date_debut)
    if 'error' in resultat:
        return resultat

    plan_global = resultat['plan']
    plan_dir = resultat['plan_dir']
    get_plan_repository().creer_stockage()

    csv_existant = trouver_csv_courant(plan_dir)
    if csv_existant and not forcer and confirmation is not None:
        if not confirmation(csv_existant):
            return {'annule': True, 'plan': plan_global, 'plan_dir': plan_dir}

    chemin_csv = exporter_plan_csv(plan_global, plan_dir)
    return {'plan': plan_global, 'plan_dir': plan_dir, 'chemin_csv': chemin_csv}


def valider_plan_athlete(athlete_dir: str) -> Dict:
    """Valide le CSV courant d'un athlète (sans régénérer le plan)."""
    profil = charger_profil(athlete_dir)
    if not profil:
        return {'valide': False, 'erreurs': ['Profil non trouvé'],
                'avertissements': [], 'stats': {}}
    nom = profil.get('nom', 'Inconnu')
    plan_dir = _plan_dir_athlete(nom)
    chemin_csv = trouver_csv_courant(plan_dir)
    if not chemin_csv:
        return {'valide': False, 'erreurs': ['Aucun CSV de plan trouvé'],
                'avertissements': [], 'stats': {}}
    disponibilites = charger_disponibilites(athlete_dir)
    return valider_plan_csv(chemin_csv, disponibilites)


def exporter_plan_athlete(athlete_dir: str) -> Dict:
    """Génère PDF + Intervals.ICU à partir du CSV courant (jamais du Python)."""
    profil = charger_profil(athlete_dir)
    if not profil:
        return {'valide': False,
                'validation': {'valide': False, 'erreurs': ['Profil non trouvé'],
                               'avertissements': [], 'stats': {}},
                'pdf': '', 'intervals': ''}
    nom = profil.get('nom', 'Inconnu')
    plan_dir = _plan_dir_athlete(nom)
    disponibilites = charger_disponibilites(athlete_dir)
    return exporter_depuis_csv_courant(plan_dir, athlete=nom,
                                       disponibilites=disponibilites)


def planifier_athlete(athlete_dir: str, date_debut: Optional[str] = None) -> Dict:
    """Génère le plan, écrit le CSV proposé puis exporte depuis ce CSV."""
    resultat = construire_plan_athlete(athlete_dir, date_debut)
    if 'error' in resultat:
        return resultat

    plan_global = resultat['plan']
    plan_dir = resultat['plan_dir']
    get_plan_repository().creer_stockage()

    chemin_csv = exporter_plan_csv(plan_global, plan_dir)

    exports = exporter_exports_depuis_csv(
        chemin_csv, plan_dir,
        athlete=plan_global['athlete'],
        disponibilites=plan_global['disponibilites'],
    )
    if not exports['valide']:
        print("   ❌ CSV proposé invalide : il ne devient pas le plan courant.")
        for erreur in exports['validation']['erreurs']:
            print(f"      - {erreur}")
        get_plan_repository().supprimer_plan(chemin_csv)
        plan_global['csv_validation'] = exports['validation']
        return plan_global

    print(f"✅ Plan généré pour {plan_global['athlete']}")
    print(f"   🏆 Sport principal : {plan_global['sport_principal']}")
    print(f"   {plan_global['nb_semaines']} semaines du "
          f"{plan_global['date_debut']} au {plan_global['date_objectif']}")
    if plan_global['courses_preparatoires']:
        print(f"   🏁 Compétitions intermédiaires intégrées : "
              f"{len(plan_global['courses_preparatoires'])}")
    print(f"   📁 Plans sauvegardés dans : {plan_dir}")
    plan_global['chemin_csv'] = chemin_csv
    plan_global['csv_validation'] = exports['validation']
    return plan_global


if __name__ == "__main__":
    test_dir = "outputs/Base par athlète/Test"
    if os.path.exists(test_dir):
        resultat = planifier_athlete(test_dir)
        print(resultat)
