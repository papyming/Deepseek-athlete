# ============================================================
# FICHIER: src/planificateur/main_plan.py
# RÔLE: Planification principale d'un athlète
#       Orchestre le chargement, la génération et l'export du plan
#       CORRIGÉ: Intégration des compétitions intermédiaires
# ============================================================

import os
import sys
import math
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .chargeur import charger_profil, charger_disponibilites, charger_seances
from .generateur.generateur_semaine import generer_plan_complet
from .export_csv import exporter_plan_csv
from .export_intervals import exporter_intervals
from .export_pdf_plan import exporter_pdf_plan


def planifier_athlete(athlete_dir: str, date_debut: Optional[str] = None) -> Dict:
    """
    Fonction principale pour planifier un athlète.
    CORRIGÉ: Intègre les compétitions intermédiaires.
    """
    if not os.path.exists(athlete_dir):
        return {"error": f"Dossier {athlete_dir} introuvable"}

    # 1. Charger les données
    profil = charger_profil(athlete_dir)
    if not profil:
        return {"error": "Profil non trouvé"}

    disponibilites = charger_disponibilites(athlete_dir)
    if not disponibilites:
        return {"error": "Disponibilités non trouvées"}

    vma = profil.get('physiologie', {}).get('vma')
    vc = profil.get('physiologie', {}).get('vc')
    
    seances_vma = []
    seances_vc = []
    
    if vma and not math.isnan(vma) and vma > 0:
        seances_vma = charger_seances(athlete_dir, 'VMA')
    if vc and not math.isnan(vc) and vc > 0:
        seances_vc = charger_seances(athlete_dir, 'VC')

    # 2. Date de début (ajustée au lundi)
    aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_debut:
        debut = datetime.strptime(date_debut, '%Y-%m-%d')
    else:
        debut = aujourd_hui
    
    debut_lundi = debut - timedelta(days=debut.weekday())

    # 3. Date objectif
    date_objectif = profil.get('date_objectif')
    if date_objectif:
        if isinstance(date_objectif, str):
            try:
                date_objectif = datetime.strptime(date_objectif, '%Y-%m-%d')
            except ValueError:
                date_objectif = None
    if not date_objectif:
        date_objectif = debut_lundi + timedelta(days=56)

    # 4. Extraire les courses préparatoires
    courses_preparatoires = profil.get('courses_preparatoires', [])
    courses_parsed = []
    for course in courses_preparatoires:
        if isinstance(course, str):
            match = re.search(r'(\d{2})/(\d{2})(?:/(\d{4}))?', course)
            if match:
                jour = int(match.group(1))
                mois = int(match.group(2))
                annee = int(match.group(3)) if match.group(3) else date_objectif.year
                if annee < 100:
                    annee += 2000
                date_course = datetime(annee, mois, jour)
                if date_course < date_objectif and date_course > debut_lundi:
                    courses_parsed.append({
                        'date': date_course,
                        'nom': course
                    })
    
    courses_parsed.sort(key=lambda x: x['date'])

    # 5. Générer le plan avec les compétitions intermédiaires
    semaines = generer_plan_complet(
        debut=debut_lundi,
        date_objectif=date_objectif,
        profil=profil,
        disponibilites=disponibilites,
        seances_vma=seances_vma,
        seances_vc=seances_vc,
        courses_preparatoires=courses_parsed
    )

    # 6. Construire le plan global
    plan_global = {
        'athlete': profil.get('nom', 'Inconnu'),
        'date_debut': debut_lundi.strftime('%Y-%m-%d'),
        'date_objectif': date_objectif.strftime('%Y-%m-%d'),
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': disponibilites,
        'courses_preparatoires': courses_parsed
    }

    # 7. Export
    plan_dir = os.path.join('outputs', 'plans', plan_global['athlete'].replace(' ', '_'))
    os.makedirs(plan_dir, exist_ok=True)

    exporter_plan_csv(plan_global, plan_dir)
    exporter_intervals(plan_global, plan_dir)
    exporter_pdf_plan(plan_global, plan_dir)

    print(f"✅ Plan généré pour {plan_global['athlete']}")
    print(f"   {len(semaines)} semaines du {plan_global['date_debut']} au {plan_global['date_objectif']}")
    if courses_parsed:
        print(f"   🏁 Compétitions intermédiaires intégrées : {len(courses_parsed)}")
    print(f"   📁 Plans sauvegardés dans : {plan_dir}")

    return plan_global


if __name__ == "__main__":
    test_dir = "outputs/Base par athlète/Test"
    if os.path.exists(test_dir):
        resultat = planifier_athlete(test_dir)
        print(resultat)