import math
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

class Physiologie:
    """
    Classe centrale pour tous les calculs physiologiques :
    - VMA / Vitesse Critique (CAP)
    - FTP (Vélo)
    - 400m natation
    - Fréquences cardiaques max
    - Zones d'entraînement
    - Allures
    """
    
    # Coefficients VMA (extraits de la fiche "VMA/Piste")
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
    
    # Coefficients VC (à ajuster selon ta feuille "Fractionné VC")
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
    
    VITESSE_RECUP_VC = 6.24  # km/h
    RAPPORT_RECUP_VC = 0.25  # 25% de la distance d'effort
    
    def __init__(self, athlete_data: Dict):
        self.data = athlete_data
        self.manques = []
        self.calculs = {}
        
        # Extraction des données
        self.vma = self._extraire_vma()
        self.vc = self._extraire_vc()
        self.genre = self.data.get('Sexe', 'M').upper()
        self.age = self._calculer_age()
        self.ftp = self._extraire_ftp()
        self.temps_400m = self._extraire_temps_400m()
        self.fc_max_cap = self._extraire_fc('cap')
        self.fc_max_natation = self._extraire_fc('natation')
        self.fc_max_velo = self._extraire_fc('velo')
        
        # Calculs des tableaux
        self.tableau_vma = self._generer_tableau_vma()
        self.tableau_vc = self._generer_tableau_vc()
        
        # Bilan
        self._generer_bilan()
    
    # ------------------------------------------------------------
    # EXTRACTION DES DONNÉES
    # ------------------------------------------------------------
    
    def _extraire_vma(self) -> Optional[float]:
        champ = self.data.get('Avez vous fait un test VMA ou de VC ? Sinon avez vous une idée de votre VMA ou de votre VC ? (mettre VC ou VMA)', '')
        if not champ or champ == '':
            self.manques.append({'donnee': 'VMA', 'statut': 'Manquant'})
            return None
        
        champ = champ.upper().replace(' ', '')
        match = re.search(r'VMA[=:]*([0-9.]+)', champ)
        if match:
            return float(match.group(1))
        
        try:
            return float(champ)
        except:
            self.manques.append({'donnee': 'VMA', 'statut': 'Non reconnue', 'valeur': champ})
            return None
    
    def _extraire_vc(self) -> Optional[float]:
        champ = self.data.get('Avez vous fait un test VMA ou de VC ? Sinon avez vous une idée de votre VMA ou de votre VC ? (mettre VC ou VMA)', '')
        if champ:
            champ = champ.upper().replace(' ', '')
            match = re.search(r'VC[=:]*([0-9.]+)', champ)
            if match:
                return float(match.group(1))
        
        # Calcul depuis les perfs
        perf = self._extraire_meilleure_performance()
        if perf:
            return perf
        
        if self.vma:
            return round(self.vma * 0.85, 1)
        
        return None
    
    def _extraire_meilleure_performance(self) -> Optional[float]:
        if self.data.get('Quel est votre temps sur 10kms ?'):
            temps = self._temps_vers_secondes(self.data['Quel est votre temps sur 10kms ?'])
            if temps and temps > 0:
                return round(10 / (temps / 3600), 1)
        
        if self.data.get('Quel est votre temps sur semi marathon ?'):
            temps = self._temps_vers_secondes(self.data['Quel est votre temps sur semi marathon ?'])
            if temps and temps > 0:
                return round(21.1 / (temps / 3600), 1)
        
        if self.data.get('Quel est votre temps sur marathon ?'):
            temps = self._temps_vers_secondes(self.data['Quel est votre temps sur marathon ?'])
            if temps and temps > 0:
                return round(42.195 / (temps / 3600), 1)
        
        return None
    
    def _extraire_ftp(self) -> Optional[int]:
        ftp_str = self.data.get('FTP vélo en watt (laisser vide sinon)', '')
        if ftp_str and ftp_str != '':
            try:
                return int(ftp_str)
            except:
                self.manques.append({'donnee': 'FTP', 'statut': 'Erreur', 'valeur': ftp_str})
                return None
        return None
    
    def _extraire_temps_400m(self) -> Optional[int]:
        temps_str = self.data.get('Temps actuel sur 400m nage libre (laisser vide sinon)', '')
        if temps_str and temps_str != '':
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
        
        fc_str = self.data.get(champ, '')
        if fc_str and fc_str != '':
            try:
                return int(fc_str)
            except:
                return None
        return None
    
    # ------------------------------------------------------------
    # GÉNÉRATION DES TABLEAUX
    # ------------------------------------------------------------
    
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
    
    # ------------------------------------------------------------
    # OUTILS
    # ------------------------------------------------------------
    
    @staticmethod
    def _temps_vers_secondes(temps_str: str) -> Optional[int]:
        if not temps_str or temps_str == '':
            return None
        parties = temps_str.strip().split(':')
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
        if date_naissance:
            try:
                naissance = datetime.strptime(date_naissance, '%Y-%m-%d')
                age = datetime.now().year - naissance.year
                if datetime.now().month < naissance.month or (datetime.now().month == naissance.month and datetime.now().day < naissance.day):
                    age -= 1
                return age
            except:
                pass
        return None
    
    # ------------------------------------------------------------
    # BILAN
    # ------------------------------------------------------------
    
    def _generer_bilan(self):
        self.bilan = {
            'athlete': self.data.get('Prénom/Nom', 'Inconnu'),
            'genre': self.genre,
            'age': self.age,
            'vma': self.vma,
            'vc': self.vc,
            'ftp': self.ftp,
            'temps_400m': self.temps_400m,
            'fc_max_cap': self.fc_max_cap,
            'fc_max_natation': self.fc_max_natation,
            'fc_max_velo': self.fc_max_velo,
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
            print(f"   VMA : {self.vma} km/h")
        if self.vc:
            print(f"   Vitesse Critique : {self.vc} km/h")
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
        
        if self.tableau_vma:
            print("\n🏃 TABLEAU VMA :")
            for ligne in self.tableau_vma:
                print(f"   {ligne['distance']}m : {ligne['temps']} ({ligne['vitesse']} km/h)")
        
        if self.tableau_vc:
            print("\n🏊 TABLEAU VC AVEC RÉCUPÉRATION :")
            for ligne in self.tableau_vc:
                print(f"   {ligne['distance_effort']}m : effort {ligne['temps_effort']} ({ligne['vitesse_effort']} km/h) → recup {ligne['distance_recup']}m en {ligne['temps_recup']}")
        
        if self.manques:
            print("\n⚠️ DONNÉES MANQUANTES :")
            for m in self.manques:
                print(f"   - {m['donnee']} : {m['statut']}")
        
        print("\n" + "="*70)
    
    def get_bilan_dict(self) -> Dict:
        return self.bilan