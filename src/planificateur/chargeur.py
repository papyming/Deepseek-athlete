# ============================================================
# FICHIER: src/planificateur/chargeur.py
# RÔLE: Chargement des données d'un athlète (profil,
#       disponibilités, séances VMA/VC)
# ============================================================

import os
import json
import pandas as pd
from typing import Dict, List, Optional


def charger_profil(athlete_dir: str) -> Optional[Dict]:
    """Charge le fichier profil le plus récent."""
    fichiers = [f for f in os.listdir(athlete_dir) if 'profil_' in f and f.endswith('.json')]
    if not fichiers:
        return None
    fichiers.sort(reverse=True)
    try:
        with open(os.path.join(athlete_dir, fichiers[0]), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur chargement profil : {e}")
        return None


def charger_disponibilites(athlete_dir: str) -> Optional[Dict]:
    """Charge le fichier disponibilités le plus récent."""
    fichiers = [f for f in os.listdir(athlete_dir) if 'disponibilites_' in f and f.endswith('.json')]
    if not fichiers:
        return None
    fichiers.sort(reverse=True)
    try:
        with open(os.path.join(athlete_dir, fichiers[0]), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur chargement disponibilités : {e}")
        return None


def charger_seances(athlete_dir: str, type_seance: str) -> List[Dict]:
    """Charge les séances VMA ou VC depuis le CSV le plus récent."""
    fichiers = [f for f in os.listdir(athlete_dir) if f'seances_{type_seance}_' in f and f.endswith('.csv')]
    if not fichiers:
        return []
    fichiers.sort(reverse=True)
    try:
        df = pd.read_csv(os.path.join(athlete_dir, fichiers[0]), sep=';', encoding='utf-8-sig')
        return df.to_dict('records')
    except Exception as e:
        print(f"⚠️ Erreur chargement séances {type_seance} : {e}")
        return []