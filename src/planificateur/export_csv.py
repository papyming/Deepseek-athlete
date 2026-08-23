# ============================================================
# FICHIER: src/planificateur/export_csv.py
# RÔLE: Export du plan en CSV avec toutes les colonnes
#       requises par le cahier des charges
# ============================================================

import os
import pandas as pd
from datetime import datetime
from typing import Dict

from .constants_plan import EMOJI_JOURNEE, EMOJI_SEMAINE


def exporter_plan_csv(plan: Dict, plan_dir: str) -> str:
    """Exporte le plan en CSV."""
    rows = []
    nb_semaines = plan['nb_semaines']

    for s, semaine in enumerate(plan['semaines']):
        # Utiliser num_affichage pour S-00, S-01, etc.
        num_affichage = semaine.get('num_affichage', nb_semaines - s)
        emoji_semaine = EMOJI_SEMAINE.get(semaine.get('semaine_type', 'normale'), '🟢')
        num_semaine_str = f"{emoji_semaine}S-{num_affichage:02d}"
        
        seances_cles = []
        for jour in semaine['jours']:
            for seance in jour['seances']:
                if seance.get('difficulte') in ['intense', 'seuil']:
                    seances_cles.append(f"{seance['discipline']}: {seance['type']}")
        seances_cles_str = ", ".join(seances_cles)

        for jour in semaine['jours']:
            # Ne pas afficher les jours vides (avant le début du plan)
            if not jour['seances'] or (len(jour['seances']) == 1 and jour['seances'][0].get('discipline') == 'Repos' and jour['seances'][0].get('duree', 0) == 0):
                continue
                
            for idx, seance in enumerate(jour['seances']):
                jour_affichage = jour['jour'] if idx == 0 else '*'
                emoji_journee = EMOJI_JOURNEE.get(seance.get('difficulte', 'endurance'), '🟩')
                
                # Correction: "récupératif" → "de récupération"
                details = seance['details']
                if 'récupératif' in details:
                    details = details.replace('récupératif', 'de récupération')
                if 'Récupératif' in details:
                    details = details.replace('Récupératif', 'de récupération')
                
                # Remplir les séances clés pour la première ligne du jour
                seances_cles_ligne = seances_cles_str if idx == 0 else ''
                
                rows.append({
                    'N° semaine': num_semaine_str,
                    'Jour': jour_affichage,
                    'Date': jour['date'],
                    'Discipline': seance['discipline'],
                    'Type de séance': seance['type'],
                    'Détails': details,
                    'Durée (min)': seance['duree'],
                    'Journée type': emoji_journee,
                    'Plaisir (0-5)': '',
                    'Retour Athlète': '',
                    'Commentaires': '',
                    'Niveau semaine': '',
                    'Séances clés': seances_cles_ligne,
                    'Message Envoyé ?': ''
                })

    # Ne garder que les lignes avec des séances (ignorer les jours vides)
    df = pd.DataFrame(rows)
    
    # Supprimer les jours vides (Repos avec durée 0) mais garder les repos avec durée
    df = df[~((df['Discipline'] == 'Repos') & (df['Durée (min)'] == 0))]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_plan_{timestamp}.csv"
    chemin = os.path.join(plan_dir, nom_fichier)
    df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
    print(f"   📄 Plan CSV exporté : {chemin}")
    return chemin