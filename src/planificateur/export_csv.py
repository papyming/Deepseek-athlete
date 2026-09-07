# ============================================================
# FICHIER: src/planificateur/export_csv.py
# RÔLE: Export du plan en CSV
#       CORRIGÉ: Affichage des courses intermédiaires
# ============================================================

import os
import pandas as pd
from datetime import datetime
from typing import Dict

from .constants_plan import EMOJI_JOURNEE, EMOJI_SEMAINE


def exporter_plan_csv(plan: Dict, plan_dir: str) -> str:
    """Exporte le plan en CSV avec infos objectif et courses."""
    rows = []
    nb_semaines = plan['nb_semaines']
    profil = plan.get('profil', {})
    
    # Récupérer les infos objectif
    objectif_nom = profil.get('competition_objectif', 'Compétition')
    objectif_date = plan.get('date_objectif', '')
    courses_prepa = profil.get('courses_preparatoires', [])
    
    # Ajouter les infos objectif en tête
    rows.append({
        'N° semaine': 'OBJECTIF',
        'Jour': '',
        'Date': objectif_date,
        'Discipline': '',
        'Type de séance': 'Objectif',
        'Détails': objectif_nom,
        'Durée (min)': '',
        'Journée type': '⭐',
        'Plaisir (0-5)': '',
        'Retour Athlète': '',
        'Commentaires': '',
        'Niveau semaine': '',
        'Séances clés': '',
        'Message Envoyé ?': '',
        'TSS': '',
        'CTL': '',
        'ATL': '',
        'TSB': '',
        'Adaptation': ''
    })
    
    # Ajouter les courses préparatoires
    if courses_prepa:
        rows.append({
            'N° semaine': 'COURSES',
            'Jour': '',
            'Date': '',
            'Discipline': '',
            'Type de séance': 'Préparatoires',
            'Détails': ' | '.join([str(c) for c in courses_prepa]),
            'Durée (min)': '',
            'Journée type': '⭐',
            'Plaisir (0-5)': '',
            'Retour Athlète': '',
            'Commentaires': '',
            'Niveau semaine': '',
            'Séances clés': '',
            'Message Envoyé ?': '',
            'TSS': '',
            'CTL': '',
            'ATL': '',
            'TSB': '',
            'Adaptation': ''
        })
    
    rows.append({
        'N° semaine': '---',
        'Jour': '---',
        'Date': '---',
        'Discipline': '---',
        'Type de séance': '---',
        'Détails': '---',
        'Durée (min)': '---',
        'Journée type': '---',
        'Plaisir (0-5)': '---',
        'Retour Athlète': '---',
        'Commentaires': '---',
        'Niveau semaine': '---',
        'Séances clés': '---',
        'Message Envoyé ?': '---',
        'TSS': '---',
        'CTL': '---',
        'ATL': '---',
        'TSB': '---',
        'Adaptation': '---'
    })

    for s, semaine in enumerate(plan['semaines']):
        num_affichage = semaine.get('num_affichage', nb_semaines - s)
        emoji_semaine = EMOJI_SEMAINE.get(semaine.get('semaine_type', 'normale'), '🟢')
        num_semaine_str = f"{emoji_semaine}S-{num_affichage:02d}"
        
        tss_semaine = semaine.get('tss', 0)
        ctl = semaine.get('ctl', 0)
        atl = semaine.get('atl', 0)
        tsb = semaine.get('tsb', 0)
        
        # Séances clés
        seances_cles = []
        for jour in semaine['jours']:
            for seance in jour['seances']:
                discipline = seance.get('discipline', '')
                difficulte = seance.get('difficulte', '')
                type_seance = seance.get('type', '')
                
                # CORRIGÉ: Inclure les courses intermédiaires comme séances clés
                if discipline == 'Course':
                    seances_cles.append(f"🏁 {type_seance}: {seance.get('details', '')[:30]}")
                elif discipline == 'CAP' and difficulte in ['intense', 'seuil']:
                    if 'VMA' in type_seance or 'VC' in type_seance or 'Seuil' in type_seance:
                        seances_cles.append(f"CAP: {type_seance}")
                elif discipline == 'Vélo' and difficulte in ['seuil']:
                    seances_cles.append(f"Vélo: {type_seance}")
                elif discipline == 'Natation' and difficulte in ['seuil']:
                    seances_cles.append(f"Natation: {type_seance}")
        
        seances_cles = list(dict.fromkeys(seances_cles))
        seances_cles_str = ", ".join(seances_cles[:5])

        for jour in semaine['jours']:
            if not jour['seances']:
                rows.append({
                    'N° semaine': num_semaine_str,
                    'Jour': jour['jour'],
                    'Date': jour['date'],
                    'Discipline': 'Repos',
                    'Type de séance': 'Repos',
                    'Détails': 'Repos',
                    'Durée (min)': 0,
                    'Journée type': '⬜',
                    'Plaisir (0-5)': '',
                    'Retour Athlète': '',
                    'Commentaires': '',
                    'Niveau semaine': '',
                    'Séances clés': '',
                    'Message Envoyé ?': '',
                    'TSS': '',
                    'CTL': '',
                    'ATL': '',
                    'TSB': '',
                    'Adaptation': ''
                })
                continue
                
            for idx, seance in enumerate(jour['seances']):
                jour_affichage = jour['jour'] if idx == 0 else '*'
                
                # CORRIGÉ: Émoji pour les courses
                if seance.get('discipline') == 'Course':
                    emoji_journee = '⭐'
                else:
                    emoji_journee = EMOJI_JOURNEE.get(seance.get('difficulte', 'endurance'), '🟩')
                
                details = seance['details']
                if 'récupératif' in details:
                    details = details.replace('récupératif', 'de récupération')
                if 'Récupératif' in details:
                    details = details.replace('Récupératif', 'de récupération')
                
                adaptation = seance.get('adaptation', '')
                
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
                    'Message Envoyé ?': '',
                    'TSS': tss_semaine if idx == 0 else '',
                    'CTL': ctl if idx == 0 else '',
                    'ATL': atl if idx == 0 else '',
                    'TSB': tsb if idx == 0 else '',
                    'Adaptation': adaptation
                })

    df = pd.DataFrame(rows)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_plan_{timestamp}.csv"
    chemin = os.path.join(plan_dir, nom_fichier)
    df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
    print(f"   📄 Plan CSV exporté : {chemin}")
    return chemin