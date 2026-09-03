# ============================================================
# FICHIER: src/core/physiologie.py
# RÔLE: Orchestrateur principal des calculs physiologiques
#       CORRIGÉ: Recherche exacte des colonnes partout
# ============================================================

import math
import re
from datetime import datetime

from .physiology import (
    extraire_vma, estimer_vma, generer_tableau_vma,
    extraire_vc, generer_tableau_vc,
    extraire_ftp, generer_zones_velo, generer_tableau_velo,
    extraire_temps_400m, generer_zones_natation, generer_tableau_natation,
    analyser_profil
)


class Physiologie:
    """
    Classe principale qui orchestre tous les calculs physiologiques.
    """
    def __init__(self, athlete_data: dict):
        self.data = athlete_data
        self.genre = self.data.get('Sexe', 'M').upper()
        self.age = self._calculer_age()
        self.manques = []
        self.alertes_profil = []
        
        # ---- VMA ----
        vma_result = extraire_vma(athlete_data)
        self.vma = vma_result['vma']
        self.vma_origine = vma_result['origine']
        if vma_result['alerte']:
            self.alertes_profil.append(vma_result['alerte'])
        
        # ---- VC ----
        vc_result = extraire_vc(athlete_data, self.vma)
        self.vc = vc_result['vc']
        self.vc_origine = vc_result['origine']
        self.test_vc_3_6_12 = vc_result['test_3_6_12']
        if vc_result['alerte']:
            self.alertes_profil.append(vc_result['alerte'])
        
        # ---- FTP ----
        ftp_result = extraire_ftp(athlete_data)
        self.ftp = ftp_result['ftp']
        self.ftp_origine = ftp_result['origine']
        
        # ---- FC max ----
        self.fc_max_cap = self._extraire_fc('cap')
        self.fc_max_natation = self._extraire_fc('natation')
        self.fc_max_velo = self._extraire_fc('velo')
        
        # ---- Natation ----
        natation_result = extraire_temps_400m(athlete_data)
        self.temps_400m = natation_result['temps_sec']
        self.vitesse_400m = natation_result['vitesse_ms']
        self.allure_400m = natation_result['allure_100m']
        
        # ---- Courses préparatoires ----
        self.courses_preparatoires = self._extraire_courses()
        
        # ---- Date objectif ----
        self.date_objectif = self._extraire_date_objectif()
        
        # ---- Performances CAP ----
        self.vitesses_performances = self._extraire_vitesses_performances()
        
        # ---- Estimations ----
        self.vma_estimee = self._estimer_vma()
        self.vc_estimee = self._estimer_vc()
        
        # ---- Profil ----
        profil_result = analyser_profil(self.vitesses_performances, self.vma, self.vc)
        self.profil = profil_result['profil']
        for alerte in profil_result['alertes']:
            self.alertes_profil.append(alerte)
        
        # ---- Vérification écart VMA ----
        if self.vma and self.vma_estimee:
            ecart = abs(self.vma - self.vma_estimee) / self.vma * 100
            if ecart > 10:
                self.alertes_profil.append(
                    f"Écart VMA déclarée ({self.vma} km/h) vs estimée ({self.vma_estimee} km/h) : {ecart:.1f}% > 10%"
                )
        
        # ---- Tableaux ----
        self.tableau_vma = generer_tableau_vma(self.vma, self.genre)
        self.tableau_vc = generer_tableau_vc(self.vc, self.genre)
        self.tableau_velo = generer_tableau_velo(self.ftp)
        self.tableau_natation = generer_tableau_natation(self.vitesse_400m)
        self.zones_velo = generer_zones_velo(self.ftp)
        self.zones_natation = generer_zones_natation(self.vitesse_400m)
        
        # ---- Tableau des intensités ----
        self.tableau_intensites = self._generer_tableau_intensites()
    
    # ============================================================
    # MÉTHODES D'EXTRACTION
    # ============================================================
    
    def _extraire_date_objectif(self) -> str:
        texte = self.data.get('Objectif principal', '')
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
                    if 1 <= mois <= 12 and 1 <= jour <= 31:
                        return f"{annee}-{mois:02d}-{jour:02d}"
                elif len(groups) == 2 or (len(groups) == 3 and not groups[2]):
                    jour, mois = int(groups[0]), int(groups[1])
                    if 1 <= mois <= 12 and 1 <= jour <= 31:
                        annee = datetime.now().year
                        return f"{annee}-{mois:02d}-{jour:02d}"
        return None
    
    def _extraire_courses(self) -> list:
        courses_raw = self.data.get('Liste courses préparatoires avec les dates', '')
        if not courses_raw or courses_raw == '':
            return []
        courses_raw = str(courses_raw).replace(';', ',').replace('  ', ' ')
        courses = [c.strip() for c in courses_raw.split(',') if c.strip()]
        return courses
    
    def _trouver_colonne(self, patterns: list) -> str:
        """Trouve une colonne en fonction de patterns."""
        for key in self.data.keys():
            key_normalise = key.replace(' ', '').replace('?', '').replace(':', '').replace('.', '').replace('\n', '').replace('\r', '').lower()
            for pattern in patterns:
                pattern_normalise = pattern.replace(' ', '').replace('?', '').replace(':', '').replace('.', '').replace('\n', '').replace('\r', '').lower()
                if pattern_normalise in key_normalise:
                    return key
        return None
    
    def _extraire_vitesses_performances(self) -> dict:
        """Extrait les performances (10km, semi, marathon)."""
        vitesses = {}
        
        print(f"   🔍 Colonnes disponibles: {list(self.data.keys())}")
        
        # Recherche par nom EXACT d'abord
        col_10k = None
        col_semi = None
        col_marathon = None
        
        for key in self.data.keys():
            if key == 'Quel est votre temps sur 10kms ?':
                col_10k = key
            elif key == 'Quel est votre temps sur semi marathon ?':
                col_semi = key
            elif key == 'Quel est votre temps sur marathon ?':
                col_marathon = key
        
        # Si non trouvé, utiliser la recherche flexible
        if col_10k is None:
            col_10k = self._trouver_colonne(["10kms"])
        if col_semi is None:
            col_semi = self._trouver_colonne(["semi marathon"])
        if col_marathon is None:
            col_marathon = self._trouver_colonne(["marathon"])
            if col_marathon and 'semi' in col_marathon.lower():
                col_marathon = None
        
        print(f"   🔍 col_10k = '{col_10k}'")
        print(f"   🔍 col_semi = '{col_semi}'")
        print(f"   🔍 col_marathon = '{col_marathon}'")
        
        if col_10k:
            temps_raw = self.data.get(col_10k, '')
            t = self._temps_vers_secondes(temps_raw)
            if t and t > 0:
                vitesses['10km'] = round(10 / (t / 3600), 1)
                print(f"   🔍 10km: {temps_raw} → {t}s → {vitesses['10km']} km/h")
        
        if col_semi:
            temps_raw = self.data.get(col_semi, '')
            t = self._temps_vers_secondes(temps_raw)
            if t and t > 0:
                vitesses['semi'] = round(21.1 / (t / 3600), 1)
                print(f"   🔍 Semi: {temps_raw} → {t}s → {vitesses['semi']} km/h")
        
        if col_marathon:
            temps_raw = self.data.get(col_marathon, '')
            t = self._temps_vers_secondes(temps_raw)
            if t and t > 0:
                vitesses['marathon'] = round(42.195 / (t / 3600), 1)
                print(f"   🔍 Marathon: {temps_raw} → {t}s → {vitesses['marathon']} km/h")
        
        print(f"   🔍 Performances finales: {vitesses}")
        
        return vitesses
    
    def _extraire_fc(self, discipline: str) -> int:
        mapping = {
            'cap': 'Connais tu ta Fréquence Cardiaque Maximum (en CAP si possible)',
            'natation': 'Connais tu ta Fréquence Cardiaque Maximum en natation ?',
            'velo': 'Connais tu ta Fréquence Cardiaque Maximum en vélo ?'
        }
        champ = mapping.get(discipline.lower(), '')
        if not champ:
            return None
        
        col = self._trouver_colonne([champ, champ.replace(' ?', '?')])
        if not col:
            return None
        
        fc_val = self.data.get(col, '')
        if fc_val is None or fc_val == '':
            return None
        fc_str = str(fc_val).strip()
        if not fc_str or fc_str == '' or fc_str == 'nan' or fc_str == 'None':
            return None
        try:
            valeur = float(fc_str)
            if math.isnan(valeur):
                return None
            return int(valeur)
        except:
            return None
    
    def _estimer_vma(self) -> float:
        estimations = []
        
        if '10km' in self.vitesses_performances:
            estimations.append(self.vitesses_performances['10km'] / 0.88)
        if 'semi' in self.vitesses_performances:
            estimations.append(self.vitesses_performances['semi'] / 0.83)
        if 'marathon' in self.vitesses_performances:
            estimations.append(self.vitesses_performances['marathon'] / 0.75)
        
        if len(estimations) >= 2:
            return round(sum(estimations) / len(estimations), 1)
        return None
    
    def _estimer_vc(self) -> float:
        """Estime la VC par régression linéaire."""
        temps = []
        distances = []
        
        # CORRIGÉ: Recherche exacte des colonnes (identique à _extraire_vitesses_performances)
        col_10k = None
        col_semi = None
        col_marathon = None
        
        for key in self.data.keys():
            if key == 'Quel est votre temps sur 10kms ?':
                col_10k = key
            elif key == 'Quel est votre temps sur semi marathon ?':
                col_semi = key
            elif key == 'Quel est votre temps sur marathon ?':
                col_marathon = key
        
        if col_10k is None:
            col_10k = self._trouver_colonne(["10kms"])
        if col_semi is None:
            col_semi = self._trouver_colonne(["semi marathon"])
        if col_marathon is None:
            col_marathon = self._trouver_colonne(["marathon"])
            if col_marathon and 'semi' in col_marathon.lower():
                col_marathon = None
        
        if col_10k:
            t = self._temps_vers_secondes(self.data.get(col_10k, ''))
            if t and t > 0:
                temps.append(t)
                distances.append(10)
        
        if col_semi:
            t = self._temps_vers_secondes(self.data.get(col_semi, ''))
            if t and t > 0:
                temps.append(t)
                distances.append(21.1)
        
        if col_marathon:
            t = self._temps_vers_secondes(self.data.get(col_marathon, ''))
            if t and t > 0:
                temps.append(t)
                distances.append(42.195)
        
        print(f"   🔍 Régression VC: temps={temps}, distances={distances}")
        
        if len(distances) >= 2:
            try:
                import numpy as np
                coeffs = np.polyfit(temps, distances, 1)
                a = coeffs[0]
                vc = a * 3600
                if 8 <= vc <= 30:
                    return round(vc, 1)
            except:
                pass
        
        if self.vma:
            return round(self.vma * 0.85, 1)
        
        return None
    
    # ============================================================
    # CONVERSION DES TEMPS
    # ============================================================
    
    @staticmethod
    def _temps_vers_secondes(temps_str) -> int:
        if temps_str is None or temps_str == '':
            return None
        
        if isinstance(temps_str, (int, float)):
            val = float(temps_str)
            if val < 60:
                heures = int(val)
                minutes = int((val - heures) * 60)
                return heures * 3600 + minutes * 60
            if val < 100:
                return int(val * 60)
            return int(val)
        
        temps_str = str(temps_str).strip()
        temps_str = re.sub(r'[\s\xa0]', '', temps_str)
        temps_str = temps_str.replace('"', '').replace("'", '')
        
        if not temps_str or temps_str in ['nan', 'None', '']:
            return None
        
        if ':' in temps_str:
            parts = temps_str.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                elif len(parts) == 2:
                    if int(parts[0]) >= 60:
                        return int(parts[0]) * 60 + int(parts[1])
                    else:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60
            except:
                pass
        
        return None
    
    @staticmethod
    def _secondes_vers_temps(secondes: float) -> str:
        if math.isnan(secondes) or math.isinf(secondes):
            return "00:00"
        heures = int(secondes // 3600)
        minutes = int((secondes % 3600) // 60)
        sec = int(secondes % 60)
        if heures > 0:
            return f"{heures:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"
    
    def _calculer_age(self) -> int:
        date_naissance = self.data.get('Date de naissance', '')
        if date_naissance and date_naissance != '':
            try:
                date_str = str(date_naissance).strip()
                if '/' in date_str:
                    naissance = datetime.strptime(date_str, '%d/%m/%Y')
                elif '-' in date_str:
                    naissance = datetime.strptime(date_str, '%Y-%m-%d')
                else:
                    naissance = datetime.strptime(date_str, '%d/%m/%Y')
                age = datetime.now().year - naissance.year
                if datetime.now().month < naissance.month or (datetime.now().month == naissance.month and datetime.now().day < naissance.day):
                    age -= 1
                return age
            except:
                pass
        return None
    
    # ============================================================
    # TABLEAU DES INTENSITÉS
    # ============================================================
    
    def _generer_tableau_intensites(self) -> list:
        vitesse_base = self.vma if self.vma else (self.vc if self.vc else None)
        if not vitesse_base:
            return []
        
        correction_genre = 0.98 if self.genre == 'F' else 1.0
        
        zones_intensites = [
            {"duree": 30, "label": "30\"", "pct_vma": 118, "pct_vc": 128, "zone": "Anaérobie alactique", "objectif": "Puissance / Explosivité"},
            {"duree": 45, "label": "45\"", "pct_vma": 113, "pct_vc": 123, "zone": "Anaérobie lactique", "objectif": "Tolérance à l'acide lactique"},
            {"duree": 60, "label": "1'", "pct_vma": 108, "pct_vc": 118, "zone": "Anaérobie lactique", "objectif": "Capacité anaérobie / VO₂max"},
            {"duree": 75, "label": "1'15\"", "pct_vma": 105, "pct_vc": 115, "zone": "Anaérobie lactique", "objectif": "Transition vers endurance de vitesse"},
            {"duree": 90, "label": "1'30\"", "pct_vma": 103, "pct_vc": 113, "zone": "VO₂max sup.", "objectif": "Optimisation de la consommation d'O₂"},
            {"duree": 120, "label": "2'", "pct_vma": 100, "pct_vc": 110, "zone": "VO₂max cent.", "objectif": "Maintien de la VO₂max"},
            {"duree": 150, "label": "2'30\"", "pct_vma": 99, "pct_vc": 108, "zone": "VO₂max / Endurance", "objectif": "Renforcement capacité aérobie"},
            {"duree": 180, "label": "3'", "pct_vma": 97, "pct_vc": 105, "zone": "VO₂max inf. / Seuil", "objectif": "Transition vers endurance fondamentale"},
            {"duree": 240, "label": "4'", "pct_vma": 95, "pct_vc": 103, "zone": "Seuil lactique sup.", "objectif": "Amélioration de la vitesse au seuil"},
            {"duree": 300, "label": "5'", "pct_vma": 94, "pct_vc": 100, "zone": "Seuil lactique cent.", "objectif": "Développement endurance spécifique"},
            {"duree": 360, "label": "6'", "pct_vma": 91, "pct_vc": 99, "zone": "Seuil lactique inf.", "objectif": "Renforcement soutien effort"},
            {"duree": 420, "label": "7'", "pct_vma": 90, "pct_vc": 97, "zone": "Endurance fonda sup.", "objectif": "Adaptation métabolique aérobie"},
            {"duree": 480, "label": "8'", "pct_vma": 89, "pct_vc": 95, "zone": "Endurance fondamentale", "objectif": "Optimisation efficacité énergétique"},
            {"duree": 540, "label": "9'", "pct_vma": 88, "pct_vc": 94, "zone": "Endurance fondamentale", "objectif": "Maintien vitesse en endurance"},
            {"duree": 600, "label": "10'", "pct_vma": 87, "pct_vc": 92, "zone": "Endurance fonda inf.", "objectif": "Développement base aérobie"},
        ]
        
        resultat = []
        for z in zones_intensites:
            pct_vma = int(round(z["pct_vma"] * correction_genre))
            pct_vc = int(round(z["pct_vc"] * correction_genre))
            
            vitesse_vma = round(vitesse_base * (pct_vma / 100), 1)
            vitesse_vc = round(vitesse_base * (pct_vc / 100), 1)
            
            distance_vma = round(vitesse_vma * (z["duree"] / 3600) * 1000, 0)
            distance_vc = round(vitesse_vc * (z["duree"] / 3600) * 1000, 0)
            
            resultat.append({
                "duree": z["duree"],
                "label": z["label"],
                "pct_vma": pct_vma,
                "vitesse_vma": vitesse_vma,
                "distance_vma": int(distance_vma),
                "pct_vc": pct_vc,
                "vitesse_vc": vitesse_vc,
                "distance_vc": int(distance_vc),
                "zone": z["zone"],
                "objectif": z["objectif"]
            })
        
        return resultat
    
    # ============================================================
    # BILAN COMPLET
    # ============================================================
    
    def get_bilan_dict(self) -> dict:
        return {
            'athlete': self.data.get('Prénom/Nom', 'Inconnu'),
            'genre': self.genre,
            'age': self.age,
            'vma': self.vma,
            'vma_origine': self.vma_origine,
            'vc': self.vc,
            'vc_origine': self.vc_origine,
            'test_vc_3_6_12': self.test_vc_3_6_12,
            'vma_estimee': self.vma_estimee,
            'vc_estimee': self.vc_estimee,
            'profil': self.profil,
            'vitesses_performances': self.vitesses_performances,
            'alertes_profil': self.alertes_profil,
            'ftp': self.ftp,
            'temps_400m': self.temps_400m,
            'fc_max_cap': self.fc_max_cap,
            'fc_max_natation': self.fc_max_natation,
            'fc_max_velo': self.fc_max_velo,
            'courses_preparatoires': self.courses_preparatoires,
            'date_objectif': self.date_objectif,
            'tableau_vma': self.tableau_vma,
            'tableau_vc': self.tableau_vc,
            'tableau_velo': self.tableau_velo,
            'tableau_natation': self.tableau_natation,
            'zones_velo': self.zones_velo,
            'zones_natation': self.zones_natation,
            'manques': self.manques,
            'nb_manques': len(self.manques),
            'tableau_intensites': self.tableau_intensites
        }