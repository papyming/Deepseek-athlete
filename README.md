# 🏊‍♂️ Deepseek Athlete - Outil d'entraînement triathlon / CAP

Deepseek Athlete est un outil modulaire en Python destiné aux entraîneurs et athlètes de triathlon et de course à pied. Il permet d'analyser les données physiologiques d'un athlète, de générer des séances d'entraînement personnalisées (VMA, VC, FTP, natation) et de planifier un programme d'entraînement structuré sur plusieurs semaines.

## Fonctionnalités

- **Agent d'analyse** : lecture d’un CSV, calcul de la VMA, VC, FTP, FC max, zones, profil.
- **Génération de séances** : séances VMA et VC (effort + récupération) basées sur des P-Codes.
- **Estimation VMA/VC** : à partir des performances (10km, semi, marathon) avec pourcentages de soutien (88%, 83%, 75%).
- **Planificateur** : plan hebdomadaire avec périodisation (4 semaines) et alternance charge/récupération.
- **Export** : CSV (plan), Intervals.ICU, PDF récapitulatif.
- **Mise à jour des intensités** : post‑tests sans recréer tout le plan.

## Installation

1. Cloner le dépôt :
   git clone https://github.com/papyming/Deepseek-athlete.git
   cd Deepseek-athlete

2. Créer et activer un environnement virtuel (recommandé) :
   python -m venv .venv
   source .venv/bin/activate      # Linux/Mac
   .venv\Scripts\activate         # Windows

3. Installer les dépendances :
   pip install -r requirements.txt

4. Lancer l’application :
   python src/main.py

## Structure du projet

Deepseek-athlete/
├── inputs/                         # CSV d’entrée (questionnaires)
├── outputs/
│   ├── Base par athlète/           # Profil, disponibilités, séances par athlète
│   └── plans/                      # Plans exportés (CSV, Intervals.ICU)
├── src/
│   ├── core/                       # Physiologie, P‑codes
│   ├── es/                         # Export (PDF, CSV, sauvegarde)
│   ├── utils/                      # Parsers et validateurs
│   ├── main.py                     # Menu interactif
│   ├── planificateur.py            # Planification
│   ├── liste.py                    # Liste des athlètes
│   └── maj_intensites.py           # Mise à jour post‑tests
├── logo.png                        # Filigrane (optionnel)
├── Sigle_Papy.gif                  # Filigrane (optionnel)
├── README.md                       # Ce fichier
└── requirements.txt                # Dépendances Python

## Utilisation

Lancer le menu :
python src/main.py

Menu :
1. Analyser un CSV (agent)
2. Planifier un entraînement (planificateur)
3. Mettre à jour les intensités (post‑tests)
9. Quitter

## Formats de données

Entrée : CSV (séparateur `;`) avec les colonnes : nom, sexe, date de naissance, poids, métier, temps 10km/semi/marathon, VMA/VC, FTP, temps 400m natation, FC max, jours d'entraînement, objectifs, courses préparatoires, test VC 3'/6'/12'.

Sorties :
- `profil_*.json` : données physiologiques, profil, zones, alertes
- `disponibilites_*.json` : jours d'entraînement
- `seances_VMA_*.csv` et `seances_VC_*.csv` : séances
- `*_resume_*.pdf` : résumé complet
- `*_plan_*.csv` : plan hebdomadaire
- `*_intervals_*.csv` : plan pour Intervals.ICU

## Méthodes de calcul

- VMA : déclarée ou estimée depuis la VC (VC / 0.85) – Tanaka, Billat.
- VC : déclarée, régression linéaire sur 2‑3 performances, ou test 3'/6'/12' – Monod & Scherrer.
- VMA estimée : moyenne des vitesses / pourcentage de soutien (10km:88%, semi:83%, marathon:75%).
- VC estimée : régression linéaire sur performances.
- FC max : Tanaka (208 – 0.7 × âge).
- Zones CAP : %VMA ou %VC (6 zones) – Billat, INSEP.
- Zones vélo : %FTP (6 zones) – Coggan.
- Zones natation : %vitesse 400m (6 zones) – adapté de Coggan.
- Zones FC : %FC max (5 zones) – Karvonen, Friel.
- Périodisation : 4 semaines (préparation générale → spécifique → compétition → transition) – Matveev, Billat, Poliquin, Issurin.

## Tests et validation

Le projet est testé avec 10 athlètes (Base-athlete03). Les calculs sont validés par la détection d'incohérences, des alertes sur la fiabilité des données et la gestion des NaN.

## Contribution

Les contributions sont bienvenues. Merci d'utiliser des noms de variables explicites, de documenter les fonctions et de tester avec le jeu de données fourni.

## Licence

MIT – voir le fichier LICENSE.

## Auteur

PapyMing – GitHub : https://github.com/papyming

## Remerciements

Véronique Billat, Andrew Coggan, Monod & Scherrer, Joe Friel, INSEP.

Bon entraînement ! 🏊‍♂️🚴‍♂️🏃‍♂️