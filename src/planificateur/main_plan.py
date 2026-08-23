# ============================================================
# FICHIER: src/planificateur/main_plan.py
# RÔLE: Planification principale d'un athlète
#       Orchestre le chargement, la génération et l'export du plan
#       Le plan s'arrête le jour de l'objectif (S-00)
# ============================================================

import os
import sys
import math
from datetime import datetime, timedelta
from typing import Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .chargeur import charger_profil, charger_disponibilites, charger_seances
from .generateur_semaine import generer_plan_complet
from .export_csv import exporter_plan_csv
from .export_intervals import exporter_intervals


def planifier_athlete(athlete_dir: str, date_debut: Optional[str] = None) -> Dict:
    """
    Fonction principale pour planifier un athlète.
    Le plan s'arrête le jour de l'objectif (S-00).
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
    
    # Ajuster au lundi
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

    # 4. Générer le plan (s'arrête à l'objectif)
    semaines = generer_plan_complet(
        debut=debut_lundi,
        date_objectif=date_objectif,
        profil=profil,
        disponibilites=disponibilites,
        seances_vma=seances_vma,
        seances_vc=seances_vc
    )

    # 5. Construire le plan global
    plan_global = {
        'athlete': profil.get('nom', 'Inconnu'),
        'date_debut': debut_lundi.strftime('%Y-%m-%d'),
        'date_objectif': date_objectif.strftime('%Y-%m-%d'),
        'nb_semaines': len(semaines),
        'semaines': semaines,
        'profil': profil,
        'disponibilites': disponibilites
    }

    # 6. Export
    plan_dir = os.path.join('outputs', 'plans', plan_global['athlete'].replace(' ', '_'))
    os.makedirs(plan_dir, exist_ok=True)

    exporter_plan_csv(plan_global, plan_dir)
    exporter_intervals(plan_global, plan_dir)

    print(f"✅ Plan généré pour {plan_global['athlete']}")
    print(f"   {len(semaines)} semaines du {plan_global['date_debut']} au {plan_global['date_objectif']}")
    print(f"   📁 Plans sauvegardés dans : {plan_dir}")

    return plan_global


if __name__ == "__main__":
    test_dir = "outputs/Base par athlète/Test"
    if os.path.exists(test_dir):
        resultat = planifier_athlete(test_dir)
        print(resultat)