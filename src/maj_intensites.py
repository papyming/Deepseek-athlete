# ============================================================
# FICHIER: src/maj_intensites.py
# RÔLE: Mise à jour des intensités d'un plan existant
#       après un post-test (nouvelle VMA ou VC)
# ============================================================

import os
import json
import pandas as pd
import math
import re
from datetime import datetime
from typing import Optional

from stockage import get_plan_repository


def charger_profil(athlete_dir: str) -> dict:
    """Charge le fichier profil le plus récent."""
    fichiers = [f for f in os.listdir(athlete_dir) if 'profil_' in f and f.endswith('.json')]
    if not fichiers:
        return {}
    fichiers.sort(reverse=True)
    with open(os.path.join(athlete_dir, fichiers[0]), 'r', encoding='utf-8') as f:
        return json.load(f)


def sauvegarder_profil(athlete_dir: str, profil: dict):
    """Sauvegarde le profil avec un nouveau timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = profil.get('nom', 'athlete').replace(' ', '_')
    nom_fichier = f"{nom}_profil_{timestamp}.json"
    with open(os.path.join(athlete_dir, nom_fichier), 'w', encoding='utf-8') as f:
        json.dump(profil, f, ensure_ascii=False, indent=2)


def maj_intensites(athlete_dir: str, nouvelle_vma: Optional[float] = None, nouvelle_vc: Optional[float] = None):
    """
    Met à jour les intensités d'un plan existant sans modifier sa structure.
    """
    print("\n" + "="*60)
    print("🔄 MISE À JOUR DES INTENSITÉS")
    print("="*60)
    
    # 1. Charger le plan existant (via le dépôt de plans)
    depot = get_plan_repository()
    profil_charge = charger_profil(athlete_dir)
    nom_charge = profil_charge.get('nom', os.path.basename(athlete_dir))
    plan_dir = depot.dossier_plan(nom_charge)
    plan_path = depot.trouver_plan_courant(plan_dir)
    if not plan_path:
        print("❌ Aucun plan trouvé. Veuillez d'abord générer un plan.")
        return
    df_plan = depot.lire_plan(plan_path)
    print(f"✅ Plan chargé : {os.path.basename(plan_path)}")
    
    # 2. Charger le profil
    profil = charger_profil(athlete_dir)
    if not profil:
        print("❌ Profil non trouvé.")
        return
    
    # 3. Mettre à jour les valeurs physiologiques
    if nouvelle_vma is not None and not math.isnan(nouvelle_vma):
        profil['physiologie']['vma'] = nouvelle_vma
        profil['physiologie']['vma_origine'] = "Mise à jour post-tests"
        print(f"✅ VMA mise à jour : {nouvelle_vma} km/h")
    
    if nouvelle_vc is not None and not math.isnan(nouvelle_vc):
        profil['physiologie']['vc'] = nouvelle_vc
        profil['physiologie']['vc_origine'] = "Mise à jour post-tests"
        print(f"✅ VC mise à jour : {nouvelle_vc} km/h")
    
    # 4. Recalculer les zones
    vma = profil['physiologie'].get('vma')
    vc = profil['physiologie'].get('vc')
    
    if not vma and not vc:
        print("❌ Aucune VMA ou VC renseignée.")
        return
    
    # 5. Mettre à jour les séances CAP
    for idx, row in df_plan.iterrows():
        details = row.get('Détails', '')
        if 'Endurance fondamentale' in details and vma:
            duree_match = re.search(r'(\d+)\s*min', details)
            duree = int(duree_match.group(1)) if duree_match else 45
            nouvelle_allure = round(vma * 0.7, 1)
            df_plan.at[idx, 'Détails'] = f"Endurance fondamentale Z2 ({duree} min à {nouvelle_allure} km/h)"
        elif 'VMA' in details and vma:
            df_plan.at[idx, 'Détails'] = f"{details} (mis à jour)"
        elif 'VC' in details and vc:
            df_plan.at[idx, 'Détails'] = f"{details} (mis à jour)"
    
    # 6. Sauvegarder la nouvelle version
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom_athlete = profil.get('nom', 'athlete').replace(' ', '_')
    nouveau_plan = os.path.join(plan_dir, f"{nom_athlete}_plan_{timestamp}.csv")
    depot.ecrire_plan(df_plan, nouveau_plan)
    print(f"✅ Plan mis à jour sauvegardé : {os.path.basename(nouveau_plan)}")
    
    # 7. Sauvegarder le profil mis à jour
    sauvegarder_profil(athlete_dir, profil)
    print("✅ Profil mis à jour")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python maj_intensites.py <dossier_athlete> [--vma XX] [--vc YY]")
        sys.exit(1)
    
    athlete_dir = sys.argv[1]
    nouvelle_vma = None
    nouvelle_vc = None
    
    for i, arg in enumerate(sys.argv):
        if arg == '--vma' and i+1 < len(sys.argv):
            try:
                nouvelle_vma = float(sys.argv[i+1])
            except:
                print(f"⚠️ Valeur VMA invalide : {sys.argv[i+1]}")
        elif arg == '--vc' and i+1 < len(sys.argv):
            try:
                nouvelle_vc = float(sys.argv[i+1])
            except:
                print(f"⚠️ Valeur VC invalide : {sys.argv[i+1]}")
    
    maj_intensites(athlete_dir, nouvelle_vma, nouvelle_vc)