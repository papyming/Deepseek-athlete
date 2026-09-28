# ============================================================
# FICHIER: src/core/physiologie_simple.py
# RÔLE: Version simplifiée de Physiologie pour des calculs
#       rapides sans données CSV (saisie manuelle VMA/VC)
#       CORRIGÉ: Ne pas estimer automatiquement VMA/VC
# ============================================================

import math
from .physiology.vma import generer_tableau_vma as gen_vma
from .physiology.vc import generer_tableau_vc as gen_vc


class PhysiologieSimple:
    """
    Classe simplifiée qui imite Physiologie pour générer
    des tableaux à partir d'une VMA ou VC saisie manuellement.
    """
    def __init__(self, vma, vc, genre, nom):
        # CORRIGÉ: Conserver EXACTEMENT les valeurs saisies
        # Ne pas estimer automatiquement l'une depuis l'autre
        self.vma_saisie = vma  # Pour savoir ce qui a été saisi
        self.vc_saisie = vc    # Pour savoir ce qui a été saisi
        
        self.vma = vma
        self.vc = vc
        self.genre = genre
        self.nom = nom
        self.age = None
        self.data = {}
        self.alertes_profil = []
        self.manques = []
        self.vitesses_performances = {}
        self.profil = "Non déterminé"
        
        # Générer les tableaux UNIQUEMENT pour ce qui a été saisi
        self.tableau_vma = []
        self.tableau_vc = []
        self.tableau_intensites = []
        
        if self.vma:
            self.tableau_vma = gen_vma(self.vma, self.genre)
        if self.vc:
            self.tableau_vc = gen_vc(self.vc, self.genre)
        
        # Générer le tableau des intensités (effort/récupération)
        self.tableau_intensites = self._generer_tableau_intensites()
    
    def _generer_tableau_intensites(self):
        """
        Génère le tableau des intensités avec allure (Temps/km).
        CORRIGÉ: N'utilise que les valeurs SAISIES.
        """
        # CORRIGÉ: Utiliser vma_saisie et vc_saisie pour décider
        if not self.vma_saisie and not self.vc_saisie:
            return []
        
        correction_genre = 0.98 if self.genre == 'F' else 1.0
        
        zones_intensites = [
            {"duree": 30, "label": "30\"", "pct_vma": 118, "pct_vc": 128, 
             "zone": "Anaérobie alactique", "objectif": "Puissance / Explosivité"},
            {"duree": 45, "label": "45\"", "pct_vma": 113, "pct_vc": 123, 
             "zone": "Anaérobie lactique", "objectif": "Tolérance à l'acide lactique"},
            {"duree": 60, "label": "1'", "pct_vma": 108, "pct_vc": 118, 
             "zone": "Anaérobie lactique", "objectif": "Capacité anaérobie / VO2max"},
            {"duree": 75, "label": "1'15\"", "pct_vma": 105, "pct_vc": 115, 
             "zone": "Anaérobie lactique", "objectif": "Transition vers endurance de vitesse"},
            {"duree": 90, "label": "1'30\"", "pct_vma": 103, "pct_vc": 113, 
             "zone": "VO2max sup.", "objectif": "Optimisation de la consommation d'O2"},
            {"duree": 120, "label": "2'", "pct_vma": 100, "pct_vc": 110, 
             "zone": "VO2max cent.", "objectif": "Maintien de la VO2max"},
            {"duree": 150, "label": "2'30\"", "pct_vma": 99, "pct_vc": 108, 
             "zone": "VO2max / Endurance", "objectif": "Renforcement capacité aérobie"},
            {"duree": 180, "label": "3'", "pct_vma": 97, "pct_vc": 105, 
             "zone": "VO2max inf. / Seuil", "objectif": "Transition vers endurance fondamentale"},
            {"duree": 240, "label": "4'", "pct_vma": 95, "pct_vc": 103, 
             "zone": "Seuil lactique sup.", "objectif": "Amélioration de la vitesse au seuil"},
            {"duree": 300, "label": "5'", "pct_vma": 94, "pct_vc": 100, 
             "zone": "Seuil lactique cent.", "objectif": "Développement endurance spécifique"},
            {"duree": 360, "label": "6'", "pct_vma": 91, "pct_vc": 99, 
             "zone": "Seuil lactique inf.", "objectif": "Renforcement soutien effort"},
            {"duree": 420, "label": "7'", "pct_vma": 90, "pct_vc": 97, 
             "zone": "Endurance fonda sup.", "objectif": "Adaptation métabolique aérobie"},
            {"duree": 480, "label": "8'", "pct_vma": 89, "pct_vc": 95, 
             "zone": "Endurance fondamentale", "objectif": "Optimisation efficacité énergétique"},
            {"duree": 540, "label": "9'", "pct_vma": 88, "pct_vc": 94, 
             "zone": "Endurance fondamentale", "objectif": "Maintien vitesse en endurance"},
            {"duree": 600, "label": "10'", "pct_vma": 87, "pct_vc": 92, 
             "zone": "Endurance fonda inf.", "objectif": "Développement base aérobie"},
        ]
        
        resultat = []
        for z in zones_intensites:
            pct_vma = z["pct_vma"] * correction_genre
            pct_vc = z["pct_vc"] * correction_genre
            
            # CORRIGÉ: N'utiliser que les valeurs SAISIES
            vitesse_vma = round(self.vma_saisie * (pct_vma / 100), 1) if self.vma_saisie else 0
            vitesse_vc = round(self.vc_saisie * (pct_vc / 100), 1) if self.vc_saisie else 0
            
            distance_vma = round(vitesse_vma * (z["duree"] / 3600) * 1000, 0)
            distance_vc = round(vitesse_vc * (z["duree"] / 3600) * 1000, 0)
            
            # Calcul des allures (Temps/km)
            allure_vma = self._vitesse_vers_allure(vitesse_vma) if vitesse_vma > 0 else ""
            allure_vc = self._vitesse_vers_allure(vitesse_vc) if vitesse_vc > 0 else ""
            
            resultat.append({
                "duree": z["duree"],
                "label": z["label"],
                "pct_vma": int(pct_vma),
                "vitesse_vma": vitesse_vma,
                "distance_vma": int(distance_vma),
                "allure_vma": allure_vma,
                "pct_vc": int(pct_vc),
                "vitesse_vc": vitesse_vc,
                "distance_vc": int(distance_vc),
                "allure_vc": allure_vc,
                "zone": z["zone"],
                "objectif": z["objectif"]
            })
        
        return resultat

    @staticmethod
    def _vitesse_vers_allure(vitesse_kmh: float) -> str:
        """Convertit une vitesse (km/h) en allure (min/km)."""
        if vitesse_kmh <= 0:
            return ""
        minutes_par_km = 60 / vitesse_kmh
        minutes = int(minutes_par_km)
        secondes = int((minutes_par_km - minutes) * 60)
        return f"{minutes}'{secondes:02d}\"/km"

    @staticmethod
    def _secondes_vers_temps(secondes):
        if secondes is None or math.isnan(secondes) or math.isinf(secondes):
            return "00:00"
        heures = int(secondes // 3600)
        minutes = int((secondes % 3600) // 60)
        sec = int(secondes % 60)
        if heures > 0:
            return f"{heures:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"