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
        num_affichage = semaine.get('num_affichage', nb_semaines - s)
        emoji_semaine = EMOJI_SEMAINE.get(semaine.get('semaine_type', 'normale'), '🟢')
        num_semaine_str = f"{emoji_semaine}S-{num_affichage:02d}"
        
        # Séances clés: uniquement les séances CAP de qualité (VMA, VC, Seuil)
        # CORRIGÉ: Endurance n'est PAS une séance clé
        seances_cles = []
        for jour in semaine['jours']:
            for seance in jour['seances']:
                discipline = seance.get('discipline', '')
                difficulte = seance.get('difficulte', '')
                type_seance = seance.get('type', '')
                
                # CAP: VMA, VC, Seuil (pas Endurance)
                if discipline == 'CAP' and difficulte in ['intense', 'seuil']:
                    if 'VMA' in type_seance or 'VC' in type_seance or 'Seuil' in type_seance:
                        seances_cles.append(f"CAP: {type_seance}")
                # Vélo: Seuil uniquement
                elif discipline == 'Vélo' and difficulte in ['seuil']:
                    seances_cles.append(f"Vélo: {type_seance}")
                # Natation: Seuil uniquement
                elif discipline == 'Natation' and difficulte in ['seuil']:
                    seances_cles.append(f"Natation: {type_seance}")
        
        # Dédupliquer
        seances_cles = list(dict.fromkeys(seances_cles))
        seances_cles_str = ", ".join(seances_cles[:5])

        for jour in semaine['jours']:
            if not jour['seances']:
                continue
                
            for idx, seance in enumerate(jour['seances']):
                jour_affichage = jour['jour'] if idx == 0 else '*'
                emoji_journee = EMOJI_JOURNEE.get(seance.get('difficulte', 'endurance'), '🟩')
                
                details = seance['details']
                if 'récupératif' in details:
                    details = details.replace('récupératif', 'de récupération')
                if 'Récupératif' in details:
                    details = details.replace('Récupératif', 'de récupération')
                
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
                    'Séances clés': seances_cles_str if idx == 0 else '',
                    'Message Envoyé ?': ''
                })

    df = pd.DataFrame(rows)
    
    # Supprimer les jours vides (Repos avec durée 0)
    df = df[~((df['Discipline'] == 'Repos') & (df['Durée (min)'] == 0))]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_plan_{timestamp}.csv"
    chemin = os.path.join(plan_dir, nom_fichier)
    df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
    print(f"   📄 Plan CSV exporté : {chemin}")
    return chemin