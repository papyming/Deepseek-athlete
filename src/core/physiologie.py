import math
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
        self.vma_estimee = estimer_vma(self.vitesses_performances)
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
    
    # ============================================================
    # MÉTHODES D'EXTRACTION
    # ============================================================
    
    def _extraire_date_objectif(self) -> str:
        """Extrait la date de l'objectif depuis le champ 'Objectif principal'."""
        texte = self.data.get('Objectif principal', '')
        if not texte:
            return None
        import re
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
        """Extrait la liste des courses préparatoires depuis le CSV."""
        courses_raw = self.data.get('Liste courses préparatoires avec les dates', '')
        if not courses_raw or courses_raw == '':
            return []
        courses_raw = str(courses_raw).replace(';', ',').replace('  ', ' ')
        courses = [c.strip() for c in courses_raw.split(',') if c.strip()]
        return courses
    
    def _extraire_vitesses_performances(self) -> dict:
        vitesses = {}
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
        fc_val = self.data.get(champ, '')
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
    
    def _estimer_vc(self) -> float:
        """Estime la VC par régression linéaire sur les performances disponibles."""
        temps = []
        distances = []
        
        if self.data.get('Quel est votre temps sur 10kms ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur 10kms ?'])
            if t and t > 0:
                temps.append(t)
                distances.append(10)
        
        if self.data.get('Quel est votre temps sur semi marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur semi marathon ?'])
            if t and t > 0:
                temps.append(t)
                distances.append(21.1)
        
        if self.data.get('Quel est votre temps sur marathon ?'):
            t = self._temps_vers_secondes(self.data['Quel est votre temps sur marathon ?'])
            if t and t > 0:
                temps.append(t)
                distances.append(42.195)
        
        if len(distances) >= 2:
            try:
                import numpy as np
                coeffs = np.polyfit(temps, distances, 1)
                return round(coeffs[0] * 3600, 1)
            except:
                pass
        return None
    
    # ============================================================
    # MÉTHODES UTILITAIRES
    # ============================================================
    
    @staticmethod
    def _temps_vers_secondes(temps_str: str) -> int:
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
        if math.isnan(secondes) or math.isinf(secondes):
            return "00:00"
        minutes = int(secondes // 60)
        sec = int(secondes % 60)
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
            'nb_manques': len(self.manques)
        }