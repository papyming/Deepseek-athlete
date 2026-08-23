# ============================================================
# FICHIER: src/planificateur/export_intervals.py
# RÔLE: Export du plan au format Intervals.ICU
#       Format compatible avec l'import Intervals.ICU
# ============================================================

import os
import pandas as pd
from datetime import datetime
from typing import Dict


def exporter_intervals(plan: Dict, plan_dir: str) -> str:
    """
    Exporte le plan au format Intervals.ICU.
    Colonnes: Date, Name, Description, Planned Duration, Intensity, Notes
    """
    rows = []
    for semaine in plan['semaines']:
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance['discipline'] in ['Repos', 'Course']:
                    continue
                
                # Mapping des difficultés vers les intensités Intervals.ICU
                intensite_map = {
                    'endurance': 'Easy',
                    'seuil': 'Moderate',
                    'intense': 'Hard',
                    'recuperation': 'Recovery',
                    'course': 'Race',
                    'renforcement': 'Strength'
                }
                
                # Extraire la distance si présente dans les détails
                details = seance['details']
                distance = ''
                if 'm x' in details:
                    import re
                    match = re.search(r'(\d+)m x (\d+)', details)
                    if match:
                        distance = f"{match.group(1)}m x {match.group(2)}"
                
                # Créer le nom de la séance
                nom_seance = f"{seance['discipline']} - {seance['type']}"
                if distance:
                    nom_seance += f" ({distance})"
                
                rows.append({
                    'Date': jour['date'],
                    'Name': nom_seance,
                    'Description': details,
                    'Planned Duration': f"{seance['duree']} min",
                    'Intensity': intensite_map.get(seance.get('difficulte', 'endurance'), 'Easy'),
                    'Notes': ''
                })

    df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_intervals_{timestamp}.csv"
    chemin = os.path.join(plan_dir, nom_fichier)
    
    # Utiliser la virgule comme séparateur pour Intervals.ICU
    df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=',')
    print(f"   📄 Intervals.ICU exporté : {chemin}")
    return chemin