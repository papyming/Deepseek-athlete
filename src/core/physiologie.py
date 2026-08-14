import math
import re
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple, List

class Physiologie:
    """
    Classe centrale pour tous les calculs physiologiques :
    - VMA / Vitesse Critique (CAP) avec régression sur 3 chronos
    - FTP (Vélo)
    - 400m natation
    - Fréquences cardiaques max
    - Zones d'entraînement
    - Allures
    - Analyse de profil (endurant/moyen/explosif)
    - Origine des calculs VMA/VC
    - Courses préparatoires
    """
    
    COEFF_VMA_DISTANCE = {
        100: {'M': 1.05, 'F': 1.02},
        200: {'M': 1.05, 'F': 0.98},
        300: {'M': 0.99, 'F': 0.97},
        400: {'M': 0.98, 'F': 0.96},
        500: {'M': 0.98, 'F': 0.96},
        600: {'M': 0.95, 'F': 0.94},
        700: {'M': 0.93, 'F': 0.93},
        800: {'M': 0.94, 'F': 0.92},
        1000: {'M': 0.92, 'F': 0.90}
    }
    
    COEFF_VC_DISTANCE = {
        200: {'M': 1.164, 'F': 1.164},
        300: {'M': 1.145, 'F': 1.145},
        400: {'M': 1.106, 'F': 1.106},
        500: {'M': 1.086, 'F': 1.086},
        600: {'M': 1.067, 'F': 1.067},
        700: {'M': 1.048, 'F': 1.048},
        800: {'M': 1.019, 'F': 1.019},
        1000: {'M': 0.989, 'F': 0.989},
        1500: {'M': 0.961, 'F': 0.961},
        2000: {'M': 0.941, 'F': 0.941},
        2800: {'M': 0.931, 'F': 0.931}
    }
    
    VITESSE_RECUP_VC = 6.24
    RAPPORT_RECUP_VC = 0.25
    
    def __init__(self, athlete_data: Dict):
        self.data = athlete_data
        self.manques = []
        self.vma_origine = None
        self.vc_origine = None
        
        self.vma = self._extraire_vma()
        self.vc = self._extraire_vc()
        self.genre = self.data.get('Sexe', 'M').upper()
        self.age = self._calculer_age()
        self.ftp = self._extraire_ftp()
        self.temps_400m = self._extraire_temps_400m()
        self.fc_max_cap = self._extraire_fc('cap')
        self.fc_max_natation = self._extraire_fc('natation')
        self.fc_max_velo = self._extraire_fc('velo')
        
        self.courses_preparatoires = self._extraire_courses()
        
        self.profil, self.vitesses_performances, self.alertes_profil = self._analyser_profil()
        
        self.tableau_vma = self._generer_tableau_vma()
        self.tableau_vc = self._generer_tableau_vc()
        
        self._generer_bilan()
    
    def _extraire_courses(self) -> List[str]:
        """Extrait la liste des courses préparatoires depuis le CSV."""
        courses_raw = self.data.get('Liste courses préparatoires avec les dates', '')
        if not courses_raw or courses_raw == '':
            return []
        courses_raw = str(courses_raw).replace(';', ',').replace('  ', ' ')
        courses = [c.strip() for c in courses_raw.split(',') if c.strip()]
        return courses
    
    def _extraire_vma(self) -> Optional[float]:
        champ = self.data.get('Avez vous fait un test VMA ou de VC ? Sinon avez vous une idée de votre VMA ou de votre VC ? (mettre VC ou VMA)', '')
        if not champ or champ == '':
            self.manques.append({'donnee': 'VMA', 'statut': 'Manquant'})
            return None
        
        champ = str(champ).upper().replace(' ', '')
        match = re.search(r'VMA[=:]*([0-9.]+)', champ)
        if match:
            self.vma_origine = "Déclarée (colonne VMA)"
            return float(match.group(1))
        
        match_vc = re.search(r'VC[=:]*([0-9.]+)', champ)
        if match_vc:
            vc = float(match_vc.group(1))
            self.vma_origine = f"Estimée depuis la VC ({vc} km/h)"
            return round(vc / 0.85, 1)
        
        try:
            self.vma_origine = "Déclarée (valeur numérique)"
            return float(champ)
        except:
            self.manques.append({'donnee': 'VMA', 'statut': 'Non reconnue', 'valeur': champ})
            return None
    
    def _extraire_vc(self) -> Optional[float]:
        """
        Extrait la VC avec une priorité :
        1. Déclaration directe (VC=...)
        2. Régression linéaire sur 3 chronos (10km, semi, marathon)
        3. Moyenne sur 2 chronos
        4. Chrono unique
        5. Estimation depuis la VMA
        """
        champ = self.data.get('Avez vous fait un test VMA ou de VC ? Sinon avez vous une idée de votre VMA ou de votre VC ? (mettre VC ou VMA)', '')
        if champ and champ != '':
            champ = str(champ).upper().replace(' ', '')
            match = re.search(r'VC[=:]*([0-9.]+)', champ)
            if match:
                self.vc_origine = "Déclarée (colonne VC)"
                return float(match.group(1))
        
        vitesses = []
        distances = []
        origines = []
        
        if self.data.get('Quel est votre temps sur 10kms ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur 10kms ?'])
            if t and t > 0:
                vitesses.append(10 / (t / 3600))
                distances.append(10)
                origines.append("10km")
        
        if self.data.get('Quel est votre temps sur semi marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur semi marathon ?'])
            if t and t > 0:
                vitesses.append(21.1 / (t / 3600))
                distances.append(21.1)
                origines.append("semi-marathon")
        
        if self.data.get('Quel est votre temps sur marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur marathon ?'])
            if t and t > 0:
                vitesses.append(42.195 / (t / 3600))
                distances.append(42.195)
                origines.append("marathon")
        
        if len(vitesses) >= 2:
            try:
                temps = [d / v * 3600 for d, v in zip(distances, vitesses)]
                coeffs = np.polyfit(distances, temps, 1)
                a, b = coeffs[0], coeffs[1]
                vc = 3600 / a
                self.vc_origine = f"Calculée par régression sur {len(vitesses)} distances ({', '.join(origines)})"
                return round(vc, 1)
            except Exception as e:
                print(f"   ⚠️ Régression échouée ({e}), utilisation de la moyenne")
                vc = sum(vitesses) / len(vitesses)
                self.vc_origine = f"Moyenne sur {len(vitesses)} distances ({', '.join(origines)})"
                return round(vc, 1)
        
        elif len(vitesses) == 1:
            vc = vitesses[0]
            self.vc_origine = f"Calculée depuis le {origines[0]}"
            return round(vc, 1)
        
        if self.vma:
            self.vc_origine = f"Estimée depuis la VMA ({self.vma} km/h, 85%)"
            return round(self.vma * 0.85, 1)
        
        return None
    
    def _extraire_ftp(self) -> Optional[int]:
        ftp_str = self.data.get('FTP vélo en watt (laisser vide sinon)', '')
        if ftp_str is None or ftp_str == '':
            return None
        ftp_str = str(ftp_str).strip()
        if not ftp_str or ftp_str == '' or ftp_str == 'nan' or ftp_str == 'None':
            return None
        try:
            return int(float(ftp_str))
        except:
            self.manques.append({'donnee': 'FTP', 'statut': 'Erreur', 'valeur': ftp_str})
            return None
    
    def _extraire_temps_400m(self) -> Optional[int]:
        temps_val = self.data.get('Temps actuel sur 400m nage libre (laisser vide sinon)', '')
        if temps_val is None:
            return None
        temps_str = str(temps_val).strip()
        if not temps_str or temps_str == '' or temps_str == 'nan' or temps_str == 'None':
            return None
        temps_sec = self._temps_vers_secondes(temps_str)
        if temps_sec and temps_sec > 0:
            return temps_sec
        return None
    
    def _extraire_fc(self, discipline: str) -> Optional[int]:
        mapping = {
            'cap': 'Connais tu ta Fréquence Cardiaque Maximum (en CAP si possible)',
            'natation': 'Connais tu ta Fréquence Cardiaque Maximum en natation ?',
            'velo': 'Connais tu ta Fréquence Cardiaque Maximum en vélo ?'
        }
        champ = mapping.get(discipline.lower(), '')
        if not champ:
            return None
        fc_val = self.data.get(champ, '')
        if fc_val is None or fc_val == '':
            return None
        fc_str = str(fc_val).strip()
        if not fc_str or fc_str == '' or fc_str == 'nan' or fc_str == 'None':
            return None
        try:
            return int(float(fc_str))
        except:
            return None
    
    def _analyser_profil(self) -> Tuple[str, Dict, List]:
        vitesses = {}
        alertes = []
        
        if self.data.get('Quel est votre temps sur 10kms ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur 10kms ?'])
            if t and t > 0:
                vitesses['10km'] = round(10 / (t / 3600), 1)
        
        if self.data.get('Quel est votre temps sur semi marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur semi marathon ?'])
            if t and t > 0:
                vitesses['semi'] = round(21.1 / (t / 3600), 1)
        
        if self.data.get('Quel est votre temps sur marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur marathon ?'])
            if t and t > 0:
                vitesses['marathon'] = round(42.195 / (t / 3600), 1)
        
        nb_distances = len(vitesses)
        
        if nb_distances >= 3:
            v10 = vitesses.get('10km')
            vsemi = vitesses.get('semi')
            vmar = vitesses.get('marathon')
            if v10 and vsemi and vmar:
                if vsemi > (v10 - 1) and vmar > (vsemi - 1):
                    profil = "Endurant"
                elif vsemi < (v10 - 1) and vmar < (vsemi - 1):
                    profil = "Explosif"
                else:
                    profil = "Moyen"
            else:
                profil = "Non déterminé (données incomplètes)"
        elif nb_distances == 2:
            v10 = vitesses.get('10km')
            vsemi = vitesses.get('semi')
            vmar = vitesses.get('marathon')
            if v10 and vsemi:
                if vsemi > (v10 - 1):
                    profil = "Endurant (tendance)"
                elif vsemi < (v10 - 1):
                    profil = "Explosif (tendance)"
                else:
                    profil = "Moyen"
            elif vsemi and vmar:
                if vmar > (vsemi - 1):
                    profil = "Endurant"
                elif vmar < (vsemi - 1):
                    profil = "Explosif (tendance)"
                else:
                    profil = "Moyen"
            else:
                profil = "Non déterminé (2 distances)"
        elif nb_distances == 1:
            profil = "Non déterminé (1 seule distance)"
        else:
            profil = "Non déterminé (aucune distance)"
        
        if self.vma and self.vc:
            ratio = self.vc / self.vma
            if ratio < 0.75 or ratio > 0.95:
                alertes.append(f"Incohérence VMA/VC : VMA={self.vma} km/h, VC={self.vc} km/h (ratio {ratio:.2f})")
        
        return profil, vitesses, alertes
    
    def _generer_tableau_vma(self) -> List[Dict]:
        if not self.vma:
            return []
        tableau = []
        for distance, coeffs in self.COEFF_VMA_DISTANCE.items():
            coeff = coeffs.get(self.genre, 0.95)
            vitesse = self.vma * coeff
            temps_sec = distance / (vitesse / 3.6)
            tableau.append({
                'distance': distance,
                'vitesse': round(vitesse, 1),
                'coeff': coeff,
                'temps': self._secondes_vers_temps(temps_sec),
                'temps_sec': round(temps_sec, 2)
            })
        return tableau
    
    def _generer_tableau_vc(self) -> List[Dict]:
        if not self.vc:
            return []
        tableau = []
        for distance, coeffs in self.COEFF_VC_DISTANCE.items():
            coeff = coeffs.get(self.genre, 1.0)
            vitesse_effort = self.vc * coeff
            temps_effort_sec = distance / (vitesse_effort / 3.6)
            distance_recup = int(distance * self.RAPPORT_RECUP_VC)
            vitesse_recup = self.VITESSE_RECUP_VC
            temps_recup_sec = distance_recup / (vitesse_recup / 3.6)
            tableau.append({
                'distance_effort': distance,
                'vitesse_effort': round(vitesse_effort, 1),
                'temps_effort': self._secondes_vers_temps(temps_effort_sec),
                'temps_effort_sec': round(temps_effort_sec, 2),
                'distance_recup': distance_recup,
                'vitesse_recup': vitesse_recup,
                'temps_recup': self._secondes_vers_temps(temps_recup_sec),
                'temps_recup_sec': round(temps_recup_sec, 2),
                'coeff': coeff
            })
        return tableau
    
    @staticmethod
    def _temps_vers_secondes(temps_str: str) -> Optional[int]:
        if not temps_str or temps_str == '':
            return None
        temps_str = str(temps_str).strip()
        if not temps_str or temps_str == 'nan' or temps_str == 'None':
            return None
        parties = temps_str.split(':')
        try:
            if len(parties) == 2:
                return int(parties[0]) * 60 + int(parties[1])
            elif len(parties) == 3:
                return int(parties[0]) * 3600 + int(parties[1]) * 60 + int(parties[2])
        except:
            return None
        return None
    
    @staticmethod
    def _secondes_vers_temps(secondes: float) -> str:
        minutes = int(secondes // 60)
        sec = int(secondes % 60)
        return f"{minutes:02d}:{sec:02d}"
    
    def _calculer_age(self) -> Optional[int]:
        date_naissance = self.data.get('Date de naissance', '')
        if date_naissance and date_naissance != '':
            try:
                date_str = str(date_naissance).strip()
                naissance = datetime.strptime(date_str, '%Y-%m-%d')
                age = datetime.now().year - naissance.year
                if datetime.now().month < naissance.month or (datetime.now().month == naissance.month and datetime.now().day < naissance.day):
                    age -= 1
                return age
            except:
                pass
        return None
    
    def _generer_bilan(self):
        self.bilan = {
            'athlete': self.data.get('Prénom/Nom', 'Inconnu'),
            'genre': self.genre,
            'age': self.age,
            'vma': self.vma,
            'vma_origine': self.vma_origine,
            'vc': self.vc,
            'vc_origine': self.vc_origine,
            'profil': self.profil,
            'vitesses_performances': self.vitesses_performances,
            'alertes_profil': self.alertes_profil,
            'ftp': self.ftp,
            'temps_400m': self.temps_400m,
            'fc_max_cap': self.fc_max_cap,
            'fc_max_natation': self.fc_max_natation,
            'fc_max_velo': self.fc_max_velo,
            'courses_preparatoires': self.courses_preparatoires,
            'tableau_vma': self.tableau_vma,
            'tableau_vc': self.tableau_vc,
            'manques': self.manques,
            'nb_manques': len(self.manques)
        }
    
    def afficher_bilan(self):
        print("\n" + "="*70)
        print(f"📊 BILAN PHYSIOLOGIQUE - {self.bilan['athlete']}")
        print("="*70)
        print(f"   Genre : {self.genre}")
        if self.age:
            print(f"   Âge : {self.age} ans")
        if self.vma:
            print(f"   VMA : {self.vma} km/h (origine : {self.vma_origine})")
        if self.vc:
            print(f"   VC : {self.vc} km/h (origine : {self.vc_origine})")
        if self.profil:
            print(f"   Profil : {self.profil}")
        if self.vitesses_performances:
            print("   Vitesses performances :")
            for k, v in self.vitesses_performances.items():
                print(f"      - {k} : {v} km/h")
        if self.ftp:
            print(f"   FTP : {self.ftp} W")
        if self.temps_400m:
            print(f"   Temps 400m : {self._secondes_vers_temps(self.temps_400m)}")
        if self.fc_max_cap:
            print(f"   FC max CAP : {self.fc_max_cap} bpm")
        if self.fc_max_natation:
            print(f"   FC max Natation : {self.fc_max_natation} bpm")
        if self.fc_max_velo:
            print(f"   FC max Vélo : {self.fc_max_velo} bpm")
        if self.courses_preparatoires:
            print("   Courses préparatoires :")
            for c in self.courses_preparatoires:
                print(f"      - {c}")
        
        if self.tableau_vma:
            print("\n🏃 TABLEAU VMA :")
            for ligne in self.tableau_vma:
                print(f"   {ligne['distance']}m : {ligne['temps']} ({ligne['vitesse']} km/h)")
        
        if self.tableau_vc:
            print("\n🏊 TABLEAU VC AVEC RÉCUPÉRATION :")
            for ligne in self.tableau_vc:
                print(f"   {ligne['distance_effort']}m : effort {ligne['temps_effort']} ({ligne['vitesse_effort']} km/h) → recup {ligne['distance_recup']}m en {ligne['temps_recup']}")
        
        if self.manques or self.alertes_profil:
            print("\n⚠️ ALERTES / DONNÉES MANQUANTES :")
            for m in self.manques:
                print(f"   - {m['donnee']} : {m['statut']}")
            for a in self.alertes_profil:
                print(f"   - {a}")
        
        print("\n" + "="*70)
    
    def get_bilan_dict(self) -> Dict:
        return self.bilan