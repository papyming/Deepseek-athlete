#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

# ============================================================
# CONSTANTES ÉMOJIS
# ============================================================

EMOJI_JOURNEE = {
    'endurance': '🟩',
    'seuil': '🟨',
    'intense': '🟥',
    'recuperation': '🟦',
    'course': '⭐',
    'repos': '⬜'
}

EMOJI_SEMAINE = {
    'coupe': '🔵',
    'normale': '🟢',
    'chargee': '🟡',
    'dure': '🔴'
}

# ============================================================
# CLASSE PRINCIPALE
# ============================================================

class Planificateur:
    def __init__(self, athlete_dir: str):
        self.athlete_dir = athlete_dir
        self.profil = None
        self.disponibilites = None
        self.seances_vma = []
        self.seances_vc = []
        self.courses = []
        self.date_objectif = None
        self.niveau = "Intermédiaire"
        self.coeff_volume = 1.0
        
        self._charger_donnees()
    
    def _charger_donnees(self):
        """Charge les données depuis le dossier de l'athlète."""
        profil_files = [f for f in os.listdir(self.athlete_dir) if 'profil_' in f and f.endswith('.json')]
        if profil_files:
            profil_files.sort(reverse=True)
            with open(os.path.join(self.athlete_dir, profil_files[0]), 'r', encoding='utf-8') as f:
                self.profil = json.load(f)
        
        dispo_files = [f for f in os.listdir(self.athlete_dir) if 'disponibilites_' in f and f.endswith('.json')]
        if dispo_files:
            dispo_files.sort(reverse=True)
            with open(os.path.join(self.athlete_dir, dispo_files[0]), 'r', encoding='utf-8') as f:
                self.disponibilites = json.load(f)
        
        vma_files = [f for f in os.listdir(self.athlete_dir) if 'seances_VMA_' in f and f.endswith('.csv')]
        if vma_files:
            vma_files.sort(reverse=True)
            self.seances_vma = pd.read_csv(os.path.join(self.athlete_dir, vma_files[0]), sep=';', encoding='utf-8-sig').to_dict('records')
        
        vc_files = [f for f in os.listdir(self.athlete_dir) if 'seances_VC_' in f and f.endswith('.csv')]
        if vc_files:
            vc_files.sort(reverse=True)
            self.seances_vc = pd.read_csv(os.path.join(self.athlete_dir, vc_files[0]), sep=';', encoding='utf-8-sig').to_dict('records')
        
        if self.profil:
            self.courses = self.profil.get('courses_preparatoires', [])
            self.date_objectif = self.profil.get('date_objectif')
            self.niveau = self.profil.get('niveau_estime', 'Intermédiaire')
            self.coeff_volume = self._calculer_coeff_volume()
    
    def _get_plans_dir(self) -> str:
        nom = self.profil.get('nom', 'inconnu').replace(' ', '_')
        plans_dir = os.path.join('outputs', 'plans', nom)
        os.makedirs(plans_dir, exist_ok=True)
        return plans_dir
    
    def _calculer_coeff_volume(self) -> float:
        if self.niveau == "Débutant":
            return 0.8
        elif self.niveau == "Avancé":
            return 1.2
        return 1.0
    
    def _extraire_date(self, texte: str) -> Optional[datetime]:
        if not texte:
            return None
        patterns = [
            r'(\d{2})/(\d{2})(?:/(\d{4}))?',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{2})[\.\-](\d{2})(?:[\.\-](\d{4}))?'
        ]
        for pattern in patterns:
            match = re.search(pattern, texte)
            if match:
                groups = match.groups()
                if len(groups) == 3 and groups[2]:
                    jour, mois, annee = int(groups[0]), int(groups[1]), int(groups[2])
                    if annee < 100:
                        annee += 2000
                    return datetime(annee, mois, jour)
                elif len(groups) == 2:
                    jour, mois = int(groups[0]), int(groups[1])
                    annee = datetime.now().year
                    return datetime(annee, mois, jour)
        return None
    
    def _est_jour_course(self, date: datetime) -> Optional[str]:
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == date.date():
                return course
        return None
    
    def _est_semaine_avant_course(self, date: datetime) -> bool:
        debut_semaine = date - timedelta(days=date.weekday())
        fin_semaine = debut_semaine + timedelta(days=6)
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and debut_semaine.date() <= date_course.date() <= fin_semaine.date():
                return True
        return False
    
    def _est_jour_avant_course(self, date: datetime) -> bool:
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == (date + timedelta(days=1)).date():
                return True
        return False
    
    def _est_jour_apres_course(self, date: datetime) -> bool:
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == (date - timedelta(days=1)).date():
                return True
        return False
    
    def _choisir_seance(self, seances: List[Dict], semaine: int, jour: int, phase: str) -> Optional[Dict]:
        if not seances:
            return None
        if phase == "preparation_generale":
            filtrees = [s for s in seances if s.get('distance', 0) > 800]
        elif phase == "preparation_specifique":
            filtrees = [s for s in seances if 300 <= s.get('distance', 0) <= 800]
        elif phase == "competition":
            filtrees = [s for s in seances if s.get('distance', 0) <= 400]
        else:
            filtrees = seances
        if not filtrees:
            filtrees = seances
        index = (semaine * 3 + jour) % len(filtrees)
        return filtrees[index % len(filtrees)]
    
    def _formater_seance(self, seance: Dict, type_seance: str) -> str:
        distance = seance.get('distance', '?')
        nb_rep = seance.get('nb_rep', 1)
        temps_effort = seance.get('temps_effort', '00:00')
        temps_recup = seance.get('temps_recup', '00:00')
        return f"{type_seance} : {distance}m x {nb_rep} (effort {temps_effort}, recup {temps_recup})"
    
    def _generer_endurance(self, vitesse: float, duree: int = 45) -> str:
        if vitesse:
            return f"Endurance fondamentale Z2 ({duree} min à {round(vitesse * 0.7, 1)} km/h)"
        return f"Endurance fondamentale Z2 ({duree} min)"
    
    def _generer_test_vc(self, duree: int) -> str:
        return f"TEST VC : {duree} min (effort maximal) - à réaliser avec FC"
    
    def _generer_sortie_longue(self, vitesse: float, discipline: str = "CAP") -> str:
        if discipline == "CAP":
            return f"Sortie longue Z2 (60 min à {round(vitesse * 0.7, 1)} km/h)"
        elif discipline == "Vélo":
            return f"Sortie longue vélo Z2 (90 min)"
        else:
            return f"Sortie longue natation Z2 (60 min)"
    
    def _calculer_duree_seance(self, seance: Dict) -> int:
        """Calcule la durée d'une séance à partir de son temps total."""
        try:
            temps_total = seance.get('temps_total_seance', '00:00')
            # 🔥 Vérifier que temps_total est valide
            if not temps_total or temps_total == '' or temps_total == 'nan' or temps_total == 'None':
                return 45
            if ':' in temps_total:
                parts = temps_total.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 45
        except:
            return 45
    
    def _determiner_phase(self, semaine: int, nb_semaines: int) -> str:
        ratio = semaine / nb_semaines
        if ratio < 0.25:
            return "preparation_generale"
        elif ratio < 0.60:
            return "preparation_specifique"
        elif ratio < 0.85:
            return "competition"
        else:
            return "transition"
    
    def _determiner_type_semaine(self, semaine: int, phase: str, volume_total: int, seances_intenses: int, est_course: bool = False) -> str:
        if semaine % 4 == 0:
            return 'coupe'
        elif est_course or seances_intenses > 3:
            return 'dure'
        elif volume_total > 450 or seances_intenses > 2:
            return 'chargee'
        else:
            return 'normale'
    
    def generer_plan(self, date_debut: Optional[str] = None) -> Dict:
        if not self.profil or not self.disponibilites:
            return {"error": "Données insuffisantes"}
        
        if date_debut:
            debut = datetime.strptime(date_debut, '%Y-%m-%d')
        else:
            debut = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            debut = debut - timedelta(days=debut.weekday())
        
        if isinstance(self.date_objectif, str):
            try:
                self.date_objectif = datetime.strptime(self.date_objectif, '%Y-%m-%d')
            except:
                self.date_objectif = None
        
        if not self.date_objectif:
            date_str = input("📅 Date de l'objectif (YYYY-MM-DD) : ").strip()
            if date_str:
                self.date_objectif = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                self.date_objectif = debut + timedelta(days=28)
        
        delta = self.date_objectif - debut
        nb_semaines = max(1, delta.days // 7 + 1)
        
        jours_cap = self.disponibilites.get('CAP', [])
        jours_velo = self.disponibilites.get('Velo', [])
        jours_natation = self.disponibilites.get('Natation', [])
        
        vma = self.profil.get('physiologie', {}).get('vma')
        vc = self.profil.get('physiologie', {}).get('vc')
        ftp = self.profil.get('physiologie', {}).get('ftp')
        
        a_vma = vma is not None and self.seances_vma
        a_vc = vc is not None and self.seances_vc
        
        jours_semaine = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        plan_global = {
            'athlete': self.profil.get('nom', 'Inconnu'),
            'date_debut': debut.strftime('%Y-%m-%d'),
            'date_objectif': self.date_objectif.strftime('%Y-%m-%d'),
            'nb_semaines': nb_semaines,
            'semaines': []
        }
        
        for s in range(nb_semaines):
            semaine_num = s + 1
            phase = self._determiner_phase(semaine_num, nb_semaines)
            date_semaine = debut + timedelta(days=s * 7)
            
            plan_semaine = {
                'numero': semaine_num,
                'phase': phase,
                'semaine_type': '',
                'date_debut': date_semaine.strftime('%Y-%m-%d'),
                'jours': []
            }
            
            volume_total = 0
            seances_intenses = 0
            est_course_semaine = self._est_semaine_avant_course(date_semaine)
            
            if semaine_num % 4 == 0:
                coeff_reduction = 0.7
            else:
                coeff_reduction = 1.0
            
            if phase in ["preparation_specifique", "competition"]:
                coeff_intensite = 1.2
                coeff_volume_phase = 0.8
            else:
                coeff_intensite = 0.8
                coeff_volume_phase = 1.0
            
            seances_qualite_cap = 0
            
            for i, jour in enumerate(jours_semaine):
                date_jour = date_semaine + timedelta(days=i)
                jour_plan = {
                    'jour': jour,
                    'date': date_jour.strftime('%Y-%m-%d'),
                    'seances': []
                }
                
                course = self._est_jour_course(date_jour)
                if course:
                    jour_plan['seances'].append({
                        'discipline': 'Course',
                        'type': 'Course',
                        'details': course,
                        'duree': 0,
                        'difficulte': 'course'
                    })
                    seances_intenses += 1
                    continue
                
                if self._est_jour_avant_course(date_jour):
                    jour_plan['seances'].append({
                        'discipline': 'CAP',
                        'type': 'Mise en jambes',
                        'details': "30' footing + 5x100m accélérations",
                        'duree': 30,
                        'difficulte': 'endurance'
                    })
                    continue
                
                if self._est_jour_apres_course(date_jour):
                    jour_plan['seances'].append({
                        'discipline': 'Repos',
                        'type': 'Récupération',
                        'details': "Repos actif (20' footing)",
                        'duree': 20,
                        'difficulte': 'recuperation'
                    })
                    continue
                
                if est_course_semaine:
                    if jour in jours_cap:
                        duree = int(45 * self.coeff_volume * coeff_reduction * 0.8)
                        jour_plan['seances'].append({
                            'discipline': 'CAP',
                            'type': 'Endurance',
                            'details': self._generer_endurance(vma or vc or 12, duree),
                            'duree': duree,
                            'difficulte': 'endurance'
                        })
                    if jour in jours_velo:
                        duree = int(45 * self.coeff_volume * coeff_reduction * 0.8)
                        jour_plan['seances'].append({
                            'discipline': 'Vélo',
                            'type': 'Endurance',
                            'details': f"Endurance vélo Z2 ({duree} min)",
                            'duree': duree,
                            'difficulte': 'endurance'
                        })
                    if jour in jours_natation:
                        duree = int(45 * self.coeff_volume * coeff_reduction * 0.8)
                        jour_plan['seances'].append({
                            'discipline': 'Natation',
                            'type': 'Technique',
                            'details': f"Technique natation ({duree} min)",
                            'duree': duree,
                            'difficulte': 'endurance'
                        })
                    continue
                
                # ---- CAP ----
                if jour in jours_cap:
                    max_qualite = 2 if phase == "competition" else 1
                    
                    if not a_vma and not a_vc:
                        tests = [3, 6, 12]
                        if s < len(tests) and seances_qualite_cap < 1:
                            duree_test = tests[s]
                            jour_plan['seances'].append({
                                'discipline': 'CAP',
                                'type': 'Test VC',
                                'details': self._generer_test_vc(duree_test),
                                'duree': duree_test,
                                'difficulte': 'intense'
                            })
                            seances_intenses += 1
                            seances_qualite_cap += 1
                        else:
                            duree = int(45 * self.coeff_volume * coeff_volume_phase * coeff_reduction)
                            jour_plan['seances'].append({
                                'discipline': 'CAP',
                                'type': 'Endurance',
                                'details': self._generer_endurance(vma or vc or 12, duree),
                                'duree': duree,
                                'difficulte': 'endurance'
                            })
                    else:
                        if seances_qualite_cap < max_qualite and jour in ['Mardi', 'Jeudi', 'Samedi']:
                            if a_vma and a_vc:
                                if s % 2 == 0:
                                    seance = self._choisir_seance(self.seances_vma, semaine_num, i, phase)
                                    if seance:
                                        jour_plan['seances'].append({
                                            'discipline': 'CAP',
                                            'type': 'VMA',
                                            'details': self._formater_seance(seance, 'VMA'),
                                            'duree': self._calculer_duree_seance(seance),
                                            'difficulte': 'intense'
                                        })
                                        seances_intenses += 1
                                        seances_qualite_cap += 1
                                else:
                                    seance = self._choisir_seance(self.seances_vc, semaine_num, i, phase)
                                    if seance:
                                        jour_plan['seances'].append({
                                            'discipline': 'CAP',
                                            'type': 'VC',
                                            'details': self._formater_seance(seance, 'VC'),
                                            'duree': self._calculer_duree_seance(seance),
                                            'difficulte': 'seuil'
                                        })
                                        seances_intenses += 1
                                        seances_qualite_cap += 1
                            elif a_vma:
                                seance = self._choisir_seance(self.seances_vma, semaine_num, i, phase)
                                if seance:
                                    jour_plan['seances'].append({
                                        'discipline': 'CAP',
                                        'type': 'VMA',
                                        'details': self._formater_seance(seance, 'VMA'),
                                        'duree': self._calculer_duree_seance(seance),
                                        'difficulte': 'intense'
                                    })
                                    seances_intenses += 1
                                    seances_qualite_cap += 1
                            elif a_vc:
                                seance = self._choisir_seance(self.seances_vc, semaine_num, i, phase)
                                if seance:
                                    jour_plan['seances'].append({
                                        'discipline': 'CAP',
                                        'type': 'VC',
                                        'details': self._formater_seance(seance, 'VC'),
                                        'duree': self._calculer_duree_seance(seance),
                                        'difficulte': 'seuil'
                                    })
                                    seances_intenses += 1
                                    seances_qualite_cap += 1
                        else:
                            duree = int(45 * self.coeff_volume * coeff_volume_phase * coeff_reduction)
                            if phase == "preparation_generale":
                                duree = int(duree * 1.2)
                            elif phase == "competition":
                                duree = int(duree * 0.8)
                            jour_plan['seances'].append({
                                'discipline': 'CAP',
                                'type': 'Endurance',
                                'details': self._generer_endurance(vma or vc or 12, duree),
                                'duree': duree,
                                'difficulte': 'endurance'
                            })
                
                # ---- Vélo ----
                if jour in jours_velo:
                    duree = int(60 * self.coeff_volume * coeff_volume_phase * coeff_reduction)
                    if phase == "preparation_generale":
                        duree = int(duree * 1.2)
                    elif phase == "competition":
                        duree = int(duree * 0.8)
                    
                    if ftp and phase in ["preparation_specifique", "competition"]:
                        jour_plan['seances'].append({
                            'discipline': 'Vélo',
                            'type': 'Seuil',
                            'details': f"Seuil Z4 : 3x12 min à {round(ftp * 0.95)} W (recup 5 min)",
                            'duree': duree,
                            'difficulte': 'seuil'
                        })
                        seances_intenses += 1
                    else:
                        jour_plan['seances'].append({
                            'discipline': 'Vélo',
                            'type': 'Endurance',
                            'details': f"Endurance Z2 : {duree} min à {round(ftp * 0.65) if ftp else 0} W",
                            'duree': duree,
                            'difficulte': 'endurance'
                        })
                
                # ---- Natation ----
                if jour in jours_natation:
                    duree = int(45 * self.coeff_volume * coeff_volume_phase * coeff_reduction)
                    if phase == "preparation_generale":
                        duree = int(duree * 1.2)
                    elif phase == "competition":
                        duree = int(duree * 0.8)
                    
                    if phase in ["preparation_specifique", "competition"]:
                        jour_plan['seances'].append({
                            'discipline': 'Natation',
                            'type': 'Seuil',
                            'details': "Seuil : 10x100m (départ 1'50) + 200m récup",
                            'duree': duree,
                            'difficulte': 'seuil'
                        })
                        seances_intenses += 1
                    else:
                        jour_plan['seances'].append({
                            'discipline': 'Natation',
                            'type': 'Technique',
                            'details': "Technique : 20x50m (alternance bras/coupes) + 400m pull-buoy",
                            'duree': duree,
                            'difficulte': 'endurance'
                        })
                
                if not jour_plan['seances']:
                    jour_plan['seances'].append({
                        'discipline': 'Repos',
                        'type': 'Repos',
                        'details': 'Repos total ou étirements',
                        'duree': 0,
                        'difficulte': 'repos'
                    })
                
                for seance in jour_plan['seances']:
                    volume_total += seance.get('duree', 0)
                
                plan_semaine['jours'].append(jour_plan)
            
            type_semaine = self._determiner_type_semaine(semaine_num, phase, volume_total, seances_intenses, est_course_semaine)
            plan_semaine['semaine_type'] = type_semaine
            plan_semaine['volume_total'] = volume_total
            
            plan_global['semaines'].append(plan_semaine)
        
        return plan_global
    
    def exporter_csv(self, plan: Dict, nom_fichier: str = None) -> str:
        if not plan:
            return None
        
        rows = []
        for s, semaine in enumerate(plan['semaines']):
            for jour in semaine['jours']:
                for idx, seance in enumerate(jour['seances']):
                    jour_affichage = jour['jour'] if idx == 0 else '*'
                    rows.append({
                        'N° semaine': plan['nb_semaines'] - s,
                        'Jour': jour_affichage,
                        'Date': jour['date'],
                        'Discipline': seance['discipline'],
                        'Type de séance': seance['type'],
                        'Détails': seance['details'],
                        'Durée (min)': seance['duree'],
                        'Journée type': EMOJI_JOURNEE.get(seance['difficulte'], '🟩'),
                        'Semaine type': EMOJI_SEMAINE.get(semaine['semaine_type'], '🟢'),
                        'Plaisir (0-5)': '',
                        'Retour Athlète': '',
                        'Commentaires': '',
                        'Niveau semaine': '',
                        'Séances clés': '',
                        'Message Envoyé ?': ''
                    })
        
        df = pd.DataFrame(rows)
        if not nom_fichier:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nom = plan['athlete'].replace(' ', '_')
            nom_fichier = f"{nom}_plan_{timestamp}.csv"
        
        plans_dir = self._get_plans_dir()
        chemin = os.path.join(plans_dir, nom_fichier)
        df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
        print(f"   📄 Plan CSV exporté : {chemin}")
        return chemin
    
    def exporter_intervals(self, plan: Dict) -> str:
        if not plan:
            return None
        
        rows = []
        for semaine in plan['semaines']:
            for jour in semaine['jours']:
                for seance in jour['seances']:
                    if seance['discipline'] == 'Repos' or seance['type'] == 'Course':
                        continue
                    intensite_map = {
                        'endurance': 'Easy',
                        'seuil': 'Moderate',
                        'intense': 'Hard',
                        'recuperation': 'Recovery',
                        'course': 'Race'
                    }
                    rows.append({
                        'Date': jour['date'],
                        'Name': f"{seance['discipline']} - {seance['type']}",
                        'Description': seance['details'],
                        'Planned Duration': f"{seance['duree']} min",
                        'Intensity': intensite_map.get(seance['difficulte'], 'Easy'),
                        'Notes': ''
                    })
        
        df = pd.DataFrame(rows)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom = plan['athlete'].replace(' ', '_')
        nom_fichier = f"{nom}_intervals_{timestamp}.csv"
        
        plans_dir = self._get_plans_dir()
        chemin = os.path.join(plans_dir, nom_fichier)
        df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
        print(f"   📄 Intervals.ICU exporté : {chemin}")
        return chemin


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def planifier_athlete(athlete_dir: str, date_debut: Optional[str] = None) -> Dict:
    planificateur = Planificateur(athlete_dir)
    plan = planificateur.generer_plan(date_debut)
    if "error" not in plan:
        planificateur.exporter_csv(plan)
        planificateur.exporter_intervals(plan)
    return plan


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python planificateur.py <dossier_athlete> [date_debut]")
        print("Exemple: python planificateur.py 'outputs/Base par athlète/Claire_LEFEVRE' 2026-08-10")
        sys.exit(1)
    
    athlete_dir = sys.argv[1]
    date_debut = sys.argv[2] if len(sys.argv) > 2 else None
    
    plan = planifier_athlete(athlete_dir, date_debut)
    print(json.dumps(plan, indent=2, ensure_ascii=False, default=str))