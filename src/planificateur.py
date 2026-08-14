#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

class Planificateur:
    """
    Planificateur d'entraînement triathlon.
    Génère un plan hebdomadaire personnalisé à partir des données de l'athlète.
    """
    
    # Émojis carrés pour les journées (difficulté)
    EMOJI_JOURNEE = {
        'endurance': '🟩',
        'seuil': '🟨',
        'intense': '🟥',
        'recuperation': '🟦',
        'course': '⭐',
        'repos': '⬜'
    }
    
    # Émojis ronds pour les semaines (charge globale)
    EMOJI_SEMAINE = {
        'coupe': '🔵',
        'normale': '🟢',
        'chargee': '🟡',
        'dure': '🔴'
    }
    
    # Mapping des types de séance vers la difficulté
    DIFFICULTE = {
        'VMA': 'intense',
        'VC': 'seuil',
        'Seuil': 'seuil',
        'Tempo': 'seuil',
        'Endurance': 'endurance',
        'Fartlek': 'intense',
        'Technique': 'endurance',
        'Sprint': 'intense',
        'Récupération': 'recuperation',
        'Repos': 'repos',
        'Test': 'intense',
        'Course': 'course'
    }
    
    def __init__(self, athlete_dir: str):
        self.athlete_dir = athlete_dir
        self.profil = None
        self.disponibilites = None
        self.seances_vma = []
        self.seances_vc = []
        self.courses = []
        self.date_objectif = None
        
        self._charger_donnees()
    
    def _charger_donnees(self):
        """Charge les données de l'athlète depuis le dossier."""
        # 1. Profil
        profil_files = [f for f in os.listdir(self.athlete_dir) if f.startswith('profil_') and f.endswith('.json')]
        if profil_files:
            profil_files.sort(reverse=True)
            with open(os.path.join(self.athlete_dir, profil_files[0]), 'r', encoding='utf-8') as f:
                self.profil = json.load(f)
                # Extraire la date de l'objectif
                objectif = self.profil.get('competition_objectif', '')
                if objectif:
                    # Essayer d'extraire une date (ex: "Semi-marathon de Lyon 2026" → pas de date)
                    # On laissera l'utilisateur saisir la date de l'objectif
                    pass
        
        # 2. Disponibilités
        dispo_files = [f for f in os.listdir(self.athlete_dir) if f.startswith('disponibilites_') and f.endswith('.json')]
        if dispo_files:
            dispo_files.sort(reverse=True)
            with open(os.path.join(self.athlete_dir, dispo_files[0]), 'r', encoding='utf-8') as f:
                self.disponibilites = json.load(f)
        
        # 3. Séances VMA
        vma_files = [f for f in os.listdir(self.athlete_dir) if f.startswith('seances_VMA_') and f.endswith('.csv')]
        if vma_files:
            vma_files.sort(reverse=True)
            self.seances_vma = pd.read_csv(os.path.join(self.athlete_dir, vma_files[0]), sep=';', encoding='utf-8-sig').to_dict('records')
        
        # 4. Séances VC
        vc_files = [f for f in os.listdir(self.athlete_dir) if f.startswith('seances_VC_') and f.endswith('.csv')]
        if vc_files:
            vc_files.sort(reverse=True)
            self.seances_vc = pd.read_csv(os.path.join(self.athlete_dir, vc_files[0]), sep=';', encoding='utf-8-sig').to_dict('records')
        
        # 5. Courses préparatoires
        if self.profil:
            self.courses = self.profil.get('courses_preparatoires', [])
    
    def _extraire_date(self, texte: str) -> Optional[datetime]:
        """Extrait une date d'un texte (ex: 'Triathlon Mâcon 15/08' → 2026-08-15)."""
        if not texte:
            return None
        # Chercher des motifs de date JJ/MM ou JJ/MM/AAAA ou AAAA-MM-JJ
        patterns = [
            r'(\d{2})/(\d{2})(?:/(\d{4}))?',  # 15/08 ou 15/08/2026
            r'(\d{4})-(\d{2})-(\d{2})',        # 2026-08-15
            r'(\d{2})[\.\-](\d{2})(?:[\.\-](\d{4}))?'  # 15-08 ou 15-08-2026
        ]
        for pattern in patterns:
            match = re.search(pattern, texte)
            if match:
                groups = match.groups()
                if len(groups) == 3 and groups[2]:  # JJ/MM/AAAA
                    jour, mois, annee = int(groups[0]), int(groups[1]), int(groups[2])
                    if annee < 100:
                        annee += 2000
                    return datetime(annee, mois, jour)
                elif len(groups) == 2 or (len(groups) == 3 and not groups[2]):  # JJ/MM
                    jour, mois = int(groups[0]), int(groups[1])
                    # On suppose l'année en cours
                    annee = datetime.now().year
                    return datetime(annee, mois, jour)
        return None
    
    def _calculer_nb_semaines(self, date_debut: datetime) -> int:
        """Calcule le nombre de semaines restantes avant l'objectif."""
        if not self.date_objectif:
            return 1  # Par défaut
        delta = self.date_objectif - date_debut
        return max(1, delta.days // 7 + 1)
    
    def _est_jour_course(self, date: datetime) -> Optional[str]:
        """Vérifie si la date correspond à une course préparatoire."""
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == date.date():
                return course
        return None
    
    def _est_jour_avant_course(self, date: datetime) -> bool:
        """Vérifie si c'est la veille d'une course."""
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == (date + timedelta(days=1)).date():
                return True
        return False
    
    def _est_jour_apres_course(self, date: datetime) -> bool:
        """Vérifie si c'est le lendemain d'une course."""
        for course in self.courses:
            date_course = self._extraire_date(course)
            if date_course and date_course.date() == (date - timedelta(days=1)).date():
                return True
        return False
    
    def _choisir_seance(self, seances: List[Dict], semaine: int, jour: int) -> Optional[Dict]:
        """Choisit une séance en fonction de la semaine et du jour."""
        if not seances:
            return None
        # Alterner entre les séances (courtes, longues) selon la semaine
        index = (semaine * 2 + jour) % len(seances)
        return seances[index % len(seances)]
    
    def _formater_seance(self, seance: Dict, type_seance: str) -> str:
        """Formate une séance en texte lisible."""
        distance = seance.get('distance', '?')
        nb_rep = seance.get('nb_rep', 1)
        temps_effort = seance.get('temps_effort', '00:00')
        temps_recup = seance.get('temps_recup', '00:00')
        return f"{type_seance} : {distance}m x {nb_rep} (effort {temps_effort}, recup {temps_recup})"
    
    def _generer_endurance(self, vitesse: float, duree: int = 45) -> str:
        """Génère une séance d'endurance."""
        if vitesse:
            return f"Endurance fondamentale Z2 ({duree} min à {round(vitesse * 0.7, 1)} km/h)"
        else:
            return f"Endurance fondamentale Z2 ({duree} min)"
    
    def _generer_velo(self, ftp: int, semaine: int, duree: int = 60) -> str:
        """Génère une séance vélo."""
        if semaine % 2 == 0:
            return f"Seuil Z4 : 3x12 min à {round(ftp * 0.95)} W (recup 5 min)"
        else:
            return f"Endurance Z2 : {duree} min à {round(ftp * 0.65)} W"
    
    def _generer_natation(self, semaine: int) -> str:
        """Génère une séance natation."""
        if semaine % 2 == 0:
            return "Seuil : 10x100m (départ 1'50) + 200m récup"
        else:
            return "Technique : 20x50m (alternance bras/coupes) + 400m pull-buoy"
    
    def _generer_test_vc(self, duree: int) -> str:
        """Génère un test de VC de durée donnée."""
        return f"TEST VC : {duree} min (effort maximal) - à réaliser avec FC"
    
    def _obtenir_vma(self) -> Optional[float]:
        """Retourne la VMA depuis le profil."""
        if self.profil:
            return self.profil.get('physiologie', {}).get('vma')
        return None
    
    def _obtenir_vc(self) -> Optional[float]:
        """Retourne la VC depuis le profil."""
        if self.profil:
            return self.profil.get('physiologie', {}).get('vc')
        return None
    
    def _obtenir_ftp(self) -> Optional[int]:
        """Retourne la FTP depuis le profil."""
        if self.profil:
            return self.profil.get('physiologie', {}).get('ftp')
        return None
    
    def _obtenir_temps_400m(self) -> Optional[int]:
        """Retourne le temps 400m natation depuis le profil."""
        if self.profil:
            return self.profil.get('physiologie', {}).get('temps_400m_natation')
        return None
    
    def _obtenir_fc_max(self, discipline: str) -> Optional[int]:
        """Retourne la FC max pour une discipline."""
        if self.profil:
            mapping = {
                'cap': 'fc_max_cap',
                'natation': 'fc_max_natation',
                'velo': 'fc_max_velo'
            }
            return self.profil.get('physiologie', {}).get(mapping.get(discipline, ''))
        return None
    
    def _obtenir_niveau(self) -> str:
        """Retourne le niveau estimé de l'athlète."""
        if self.profil:
            return self.profil.get('niveau_estime', 'Intermédiaire')
        return "Intermédiaire"
    
    def _obtenir_coeff_volume(self) -> float:
        """Retourne le coefficient de volume selon le niveau."""
        niveau = self._obtenir_niveau()
        if niveau == "Débutant":
            return 0.8
        elif niveau == "Avancé":
            return 1.2
        return 1.0
    
    def _obtenir_objectif(self) -> str:
        """Retourne l'objectif principal."""
        if self.profil:
            return self.profil.get('objectif_principal', 'Améliorer chrono')
        return "Améliorer chrono"
    
    def _determiner_type_semaine(self, semaine: int, volume_total: int, seances_intenses: int) -> str:
        """
        Détermine le type de semaine (Coupe/Normale/Chargée/Dure).
        """
        if semaine == 4:  # Semaine de récupération
            return 'coupe'
        elif volume_total > 600 or seances_intenses > 3:
            return 'dure'
        elif volume_total > 450 or seances_intenses > 2:
            return 'chargee'
        else:
            return 'normale'
    
    def generer_plan(self, semaine: int = 1, date_debut: Optional[str] = None) -> Dict:
        """
        Génère un plan d'entraînement pour une semaine donnée.
        
        Args:
            semaine: Numéro de semaine (1 à 4 pour un microcycle)
            date_debut: Date de début de la semaine (format 'YYYY-MM-DD')
        
        Returns:
            Dict contenant le plan hebdomadaire
        """
        if not self.profil or not self.disponibilites:
            return {"error": "Données insuffisantes"}
        
        # 1. Déterminer la date de début
        if date_debut:
            debut = datetime.strptime(date_debut, '%Y-%m-%d')
        else:
            debut = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # Ajuster au lundi
            debut = debut - timedelta(days=debut.weekday())
        
        # 2. Récupérer les disponibilités
        jours_cap = self.disponibilites.get('CAP', [])
        jours_velo = self.disponibilites.get('Velo', [])
        jours_natation = self.disponibilites.get('Natation', [])
        
        # 3. Récupérer les bi-quotidiens
        bi_quotidien = self.disponibilites.get('bi_quotidien', {'CAP': [], 'Velo': [], 'Natation': []})
        
        # 4. Récupérer les données physiologiques
        vma = self._obtenir_vma()
        vc = self._obtenir_vc()
        ftp = self._obtenir_ftp()
        niveau = self._obtenir_niveau()
        coeff_volume = self._obtenir_coeff_volume()
        objectif = self._obtenir_objectif()
        
        # 5. Déterminer si on a des séances de qualité
        a_vma = vma is not None and self.seances_vma
        a_vc = vc is not None and self.seances_vc
        
        # 6. Si ni VMA ni VC → générer des tests
        tests_vc = []
        if not a_vma and not a_vc:
            tests_vc = [3, 6, 12]  # 3', 6', 12'
        
        # 7. Construire le plan
        plan = {}
        jours_semaine = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        toutes_seances = []
        volume_total = 0
        seances_intenses = 0
        
        # Déterminer les jours où il y a bi-quotidien
        jours_bi = {}
        for discipline, jours in bi_quotidien.items():
            for j in jours:
                if j not in jours_bi:
                    jours_bi[j] = []
                jours_bi[j].append(discipline)
        
        for i, jour in enumerate(jours_semaine):
            date_jour = debut + timedelta(days=i)
            plan[jour] = {
                'date': date_jour.strftime('%Y-%m-%d'),
                'seances': [],
                'est_course': False,
                'est_repos': False
            }
            
            # Vérifier si c'est un jour de course préparatoire
            course_jour = self._est_jour_course(date_jour)
            if course_jour:
                plan[jour]['est_course'] = True
                plan[jour]['seances'].append({
                    'discipline': 'Course',
                    'type': 'Course',
                    'details': course_jour,
                    'duree': 0,
                    'difficulte': 'course',
                    'est_course': True
                })
                seances_intenses += 1
                continue
            
            # Vérifier si c'est un jour avant course
            if self._est_jour_avant_course(date_jour):
                plan[jour]['seances'].append({
                    'discipline': 'CAP',
                    'type': 'Mise en jambes',
                    'details': "30' footing + 5x100m accélérations",
                    'duree': 30,
                    'difficulte': 'endurance'
                })
                continue
            
            # Vérifier si c'est un jour après course
            if self._est_jour_apres_course(date_jour):
                plan[jour]['seances'].append({
                    'discipline': 'Repos',
                    'type': 'Récupération',
                    'details': "Repos actif (20' footing)",
                    'duree': 20,
                    'difficulte': 'recuperation'
                })
                continue
            
            # Séances CAP
            if jour in jours_cap:
                # Vérifier si on doit faire un test VC
                if tests_vc:
                    duree_test = tests_vc.pop(0)
                    plan[jour]['seances'].append({
                        'discipline': 'CAP',
                        'type': 'Test VC',
                        'details': self._generer_test_vc(duree_test),
                        'duree': duree_test,
                        'difficulte': 'intense'
                    })
                    seances_intenses += 1
                elif a_vma and a_vc:
                    # Alterner VMA et VC selon le jour
                    if i % 2 == 0:
                        seance = self._choisir_seance(self.seances_vma, semaine, i)
                        if seance:
                            plan[jour]['seances'].append({
                                'discipline': 'CAP',
                                'type': 'VMA',
                                'details': self._formater_seance(seance, 'VMA'),
                                'duree': self._calculer_duree_seance(seance),
                                'difficulte': 'intense'
                            })
                            seances_intenses += 1
                    else:
                        seance = self._choisir_seance(self.seances_vc, semaine, i)
                        if seance:
                            plan[jour]['seances'].append({
                                'discipline': 'CAP',
                                'type': 'VC',
                                'details': self._formater_seance(seance, 'VC'),
                                'duree': self._calculer_duree_seance(seance),
                                'difficulte': 'seuil'
                            })
                            seances_intenses += 1
                elif a_vma:
                    seance = self._choisir_seance(self.seances_vma, semaine, i)
                    if seance:
                        plan[jour]['seances'].append({
                            'discipline': 'CAP',
                            'type': 'VMA',
                            'details': self._formater_seance(seance, 'VMA'),
                            'duree': self._calculer_duree_seance(seance),
                            'difficulte': 'intense'
                        })
                        seances_intenses += 1
                elif a_vc:
                    seance = self._choisir_seance(self.seances_vc, semaine, i)
                    if seance:
                        plan[jour]['seances'].append({
                            'discipline': 'CAP',
                            'type': 'VC',
                            'details': self._formater_seance(seance, 'VC'),
                            'duree': self._calculer_duree_seance(seance),
                            'difficulte': 'seuil'
                        })
                        seances_intenses += 1
                else:
                    # Séance d'endurance
                    duree = int(45 * coeff_volume)
                    plan[jour]['seances'].append({
                        'discipline': 'CAP',
                        'type': 'Endurance',
                        'details': self._generer_endurance(vma or vc or 12, duree),
                        'duree': duree,
                        'difficulte': 'endurance'
                    })
                
                # Bi-quotidien CAP
                if jour in jours_bi.get('CAP', []):
                    plan[jour]['seances'].append({
                        'discipline': 'CAP (Bis)',
                        'type': 'Endurance',
                        'details': f"Footing récupératif ({int(30 * coeff_volume)} min)",
                        'duree': int(30 * coeff_volume),
                        'difficulte': 'recuperation'
                    })
            
            # Séances Vélo
            if jour in jours_velo:
                if ftp:
                    duree = int(60 * coeff_volume)
                    plan[jour]['seances'].append({
                        'discipline': 'Vélo',
                        'type': 'Vélo',
                        'details': self._generer_velo(ftp, semaine, duree),
                        'duree': duree,
                        'difficulte': 'seuil' if semaine % 2 == 0 else 'endurance'
                    })
                else:
                    duree = int(45 * coeff_volume)
                    plan[jour]['seances'].append({
                        'discipline': 'Vélo',
                        'type': 'Endurance',
                        'details': f"Endurance vélo Z2 ({duree} min)",
                        'duree': duree,
                        'difficulte': 'endurance'
                    })
                
                # Bi-quotidien Vélo
                if jour in jours_bi.get('Velo', []):
                    plan[jour]['seances'].append({
                        'discipline': 'Vélo (Bis)',
                        'type': 'Endurance',
                        'details': f"Endurance vélo Z2 ({int(30 * coeff_volume)} min)",
                        'duree': int(30 * coeff_volume),
                        'difficulte': 'endurance'
                    })
            
            # Séances Natation
            if jour in jours_natation:
                duree = int(45 * coeff_volume)
                plan[jour]['seances'].append({
                    'discipline': 'Natation',
                    'type': 'Natation',
                    'details': self._generer_natation(semaine),
                    'duree': duree,
                    'difficulte': 'seuil' if semaine % 2 == 0 else 'endurance'
                })
                
                # Bi-quotidien Natation
                if jour in jours_bi.get('Natation', []):
                    plan[jour]['seances'].append({
                        'discipline': 'Natation (Bis)',
                        'type': 'Technique',
                        'details': f"Technique natation ({int(30 * coeff_volume)} min)",
                        'duree': int(30 * coeff_volume),
                        'difficulte': 'endurance'
                    })
            
            # Si aucune séance prévue, ajouter un repos
            if not plan[jour]['seances'] and not plan[jour]['est_course']:
                plan[jour]['seances'].append({
                    'discipline': 'Repos',
                    'type': 'Repos',
                    'details': 'Repos total ou étirements',
                    'duree': 0,
                    'difficulte': 'repos'
                })
                plan[jour]['est_repos'] = True
            
            # Calculer le volume et les séances intenses
            for seance in plan[jour]['seances']:
                volume_total += seance.get('duree', 0)
                if seance.get('difficulte') in ['intense', 'seuil']:
                    seances_intenses += 1
                toutes_seances.append({
                    'jour': jour,
                    'date': date_jour.strftime('%Y-%m-%d'),
                    'discipline': seance['discipline'],
                    'type': seance['type'],
                    'details': seance['details'],
                    'duree': seance['duree'],
                    'difficulte': seance['difficulte'],
                    'est_course': seance.get('est_course', False)
                })
        
        # 8. Déterminer le type de semaine
        type_semaine = self._determiner_type_semaine(semaine, volume_total, seances_intenses)
        
        # 9. Calculer le nombre de semaines restantes
        nb_semaines = self._calculer_nb_semaines(debut)
        
        return {
            'athlete': self.profil.get('nom', 'Inconnu'),
            'semaine': semaine,
            'nb_semaines_restantes': nb_semaines,
            'date_debut': debut.strftime('%Y-%m-%d'),
            'type_semaine': type_semaine,
            'type_semaine_emoji': self.EMOJI_SEMAINE.get(type_semaine, '🟢'),
            'volume_total': volume_total,
            'seances_intenses': seances_intenses,
            'plan': plan,
            'seances_flat': toutes_seances,
            'courses': self.courses,
            'objectif': objectif
        }
    
    def _calculer_duree_seance(self, seance: Dict) -> int:
        """Calcule la durée totale d'une séance à partir de ses répétitions."""
        try:
            temps_total = seance.get('temps_total_seance', '00:00')
            if ':' in temps_total:
                parts = temps_total.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 45  # Durée par défaut
        except:
            return 45
    
    def exporter_csv(self, plan: Dict, nom_fichier: str = None) -> str:
        """
        Exporte le plan en CSV avec toutes les colonnes demandées.
        """
        if not plan:
            return None
        
        # Préparer les données
        rows = []
        for jour, data in plan['plan'].items():
            # Ne garder qu'une ligne par séance
            for seance in data['seances']:
                row = {
                    'N° semaine': plan.get('nb_semaines_restantes', 1),
                    'Jour': jour,
                    'Date': data['date'],
                    'Discipline': seance['discipline'],
                    'Type de séance': seance['type'],
                    'Détails': seance['details'],
                    'Durée (min)': seance['duree'],
                    'Journée type': self.EMOJI_JOURNEE.get(seance['difficulte'], '🟩'),
                    'Semaine type': plan.get('type_semaine_emoji', '🟢'),
                    'Plaisir (0-5)': '',
                    'Retour Athlète': '',
                    'Commentaires': '',
                    'Niveau semaine': '',
                    'Séances clés': '',
                    'Message Envoyé ?': ''
                }
                rows.append(row)
        
        # Créer le DataFrame
        df = pd.DataFrame(rows)
        
        # Générer le nom du fichier
        if not nom_fichier:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nom = plan['athlete'].replace(' ', '_')
            nom_fichier = f"{nom}_plan_{timestamp}.csv"
        
        chemin = os.path.join(self.athlete_dir, nom_fichier)
        df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
        print(f"   📄 Plan CSV exporté : {chemin}")
        return chemin
    
    def exporter_intervals(self, plan: Dict) -> str:
        """
        Exporte le plan au format Intervals.ICU.
        """
        if not plan:
            return None
        
        rows = []
        for jour, data in plan['plan'].items():
            for seance in data['seances']:
                if seance['discipline'] == 'Repos' or seance.get('est_course'):
                    continue
                
                # Déterminer l'intensité pour Intervals.ICU
                intensite_map = {
                    'endurance': 'Easy',
                    'seuil': 'Moderate',
                    'intense': 'Hard',
                    'recuperation': 'Recovery',
                    'course': 'Race'
                }
                
                row = {
                    'Date': data['date'],
                    'Name': f"{seance['discipline']} - {seance['type']}",
                    'Description': seance['details'],
                    'Planned Duration': f"{seance['duree']} min",
                    'Intensity': intensite_map.get(seance['difficulte'], 'Easy'),
                    'Notes': ''
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Générer le nom du fichier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom = plan['athlete'].replace(' ', '_')
        nom_fichier = f"{nom}_intervals_{timestamp}.csv"
        chemin = os.path.join(self.athlete_dir, nom_fichier)
        df.to_csv(chemin, index=False, encoding='utf-8-sig', sep=';')
        print(f"   📄 Intervals.ICU exporté : {chemin}")
        return chemin


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def planifier_athlete(athlete_dir: str, semaine: int = 1, date_debut: Optional[str] = None) -> Dict:
    """
    Fonction principale pour planifier un athlète.
    """
    planificateur = Planificateur(athlete_dir)
    plan = planificateur.generer_plan(semaine, date_debut)
    
    if "error" not in plan:
        planificateur.exporter_csv(plan)
        planificateur.exporter_intervals(plan)
    
    return plan


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python planificateur.py <dossier_athlete> [semaine] [date_debut]")
        print("Exemple: python planificateur.py 'outputs/Base par athlète/Claire_LEFEVRE' 1 2026-08-10")
        sys.exit(1)
    
    athlete_dir = sys.argv[1]
    semaine = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    date_debut = sys.argv[3] if len(sys.argv) > 3 else None
    
    plan = planifier_athlete(athlete_dir, semaine, date_debut)
    print(json.dumps(plan, indent=2, ensure_ascii=False, default=str))