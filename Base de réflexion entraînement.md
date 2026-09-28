# Base de réflexion entraînement

# Base de réflexion entraînement

## 

1. ## **Paramètres d'entrée (CSV \+ apports)**

Données personnelles

* Prénom/Nom, Sexe, Date de naissance, Taille/Poids  
* Métier/contraintes

Performances CAP

* Temps sur 10km, Semi-marathon, Marathon  
* VMA ou VC déclarée (ou test)

Performances vélo

* FTP (Watts)

Performances natation

* Temps sur 400m nage libre

Fréquences cardiaques max

* FC max CAP, FC max Natation, FC max Vélo

Disponibilités

* Jours d'entraînement CAP, Vélo, Natation  
* Bi-quotidien possible  
* Nombre de séances/semaine par discipline

Objectif et compétition

* Objectif principal, Compétition visée  
* Contraintes (métier, santé, emploi du temps)

Transformation Copier/Coller TSV → CSV

* Fichier créé : `src/transforme_sheet_csv.py`  
* Objectif : Permettre à l'utilisateur de coller directement le contenu d'un tableau (Excel, Google Sheets, LibreOffice) et le transformer en CSV analysable.  
* Fonctionnalités :  
  * Collecte du texte collé depuis le terminal  
  * Nettoyage des caractères spéciaux (MacRoman, DOS/863, etc.)  
  * Suppression des sauts de ligne dans les guillemets  
  * Préservation des colonnes vides (;;) qui maintiennent la structure  
  * Détection automatique de la fin de saisie (Ctrl+Z / Ctrl+D / FIN)  
  * Validation du nombre de colonnes  
  * Nom de fichier : YYYYMMDD\_HHMMSS-base\_analytique.csv

Intégration dans le Menu Principal

* Fichier modifié : src/main.py  
* Ajout :  
  * Option 8\. 🔄 Transformer un copier/coller TSV → CSV  
  * Import du module transforme\_sheet\_csv.py  
  * Appel interactif avec proposition d'analyse directe

Correction de la Sélection des Fichiers CSV (Option 1\)

* Fichier modifié : src/main.py et src/[liste.py](http://liste.py)  
* Avant : Saisie manuelle du nom du fichier → risques d'erreur  
* Après : Liste numérotée des fichiers CSV dans inputs/ → sélection par numéro  
* Fonctions ajoutées dans liste.py :  
  * lister\_elements() : liste générique  
  * choisir\_element() : sélection générique  
  * afficher\_elements() : affichage générique

Détection Automatique de l'Encodage

* Fichier modifié : src/[main.py](http://main.py)  
* Problème : UnicodeDecodeError sur les fichiers encodés en MacRoman ou DOS/863  
* Solution : Test de multiples encodages (utf-8, windows-1252, mac\_roman, cp863, cp850, etc.)  
* Fonctions ajoutées :  
  * detecter\_encodage() : utilise chardet si disponible  
  * lire\_csv\_avec\_encodage() : test de tous les encodages possibles

Nettoyage des En-têtes CSV

* Fichier modifié : src/transforme\_sheet\_csv.py  
* Problème : Guillemets autour des en-têtes décalent la lecture  
* Solution : normaliser\_guillemets\_en\_tete() supprime les guillemets inutiles

---

2. ## **Résultats calculés (pour la planification)**

Données physiologiques

* Traçabilité des données physiologiques  
  * Pour chaque valeur calculée ou estimée (VMA, VC, FTP, CSS...), le profil conserve la valeur, l'unité et l'origine de la donnée ou du calcul.  
  * Pour la VMA et la VC, l'origine doit permettre de distinguer au minimum : donnée déclarée, test, calcul à partir des performances, estimation à partir d'une autre donnée physiologique.  
* VMA (km/h), Vitesse Critique (km/h)  
  Si le test de Vitesse Critique (VC) 3'/6'/12' est fait les 3 distances faites seront notée avec la syntaxe suivante : 3=X/6=Y/12=Z ou X, Y et Z sont les distances **en mètres** réalisées en 3', 6' et 12'.  Le schéma regex de la réponse etant “^3=\\d+/6=\\d+/12=\\d+$”.  
* Âge, FC max théorique

Tableaux de zones (distances/temps) *basé sur la base de donnée en “P-Code” extrait de google sheet*

* VMA :  temps effort \+ récupération sur 200, 300, 400, 500, 600, 700, 800, 1000, 1600, 2000, 2400 2800, 3000 metres.  
* VC : temps effort \+ récupération sur 200, 300, 400, 500, 600, 700, 800, 1000, 1600, 2000, 2400 2800, 3000 metres.  
* Le programme de planification demandera le temps total de chaque cinétique de VO2max pour en calculer le nombre de répétition minimum  
* Voir Annexe 4  Explication des % VMA et VC par temps d’effort  
  * Mettre dans le PDF les vitesse à tenir et la distance à faire durant les temps d’intensité à faire sur 30"/45"/1'/1'15"/1'30"/1'45"/2'/2'30"/3'/4'/5'/6'/7'/8'/9'/10' Voir annexe 4 pour les % et mettre \-2% pour les femmes.

Zones d'entraînement avec l’origine des calculs 

* CAP :  
  *  %VMA → 6 zones (Z1 à Z6)   
  * %VC → 6 zones (Z1 à Z6)   
* Vélo : %FTP → 6 zones (Z1 à Z6)  
* Natation : %vitesse 400m → 6 zones (Z1 à Z6)  
* FC : %FC max → 5 zones (Z1 à Z5) par discipline

Allures cibles

* CAP : min/km par zone  
* Natation : min/100m par zone  
* Vélo : km/h ou W par zone

Indicateurs de charge

* Volume hebdomadaire par discipline (minutes)  
* Niveau estimé (Débutant/Intermédiaire/Avancé)

3. ## **Origine des calculs pour les autres résultats**

| Résultat | Méthode / Source |
| :---- | :---- |
| VMA | Calcul de la VMA estimée (par défaut)Lue directement dans le CSV (colonne dédiée),  En l’absence de VMA déclarée, ou pour vérification, la VMA est estimée à partir des performances en course selon les pourcentages moyens de soutien (10km : 88%, semi : 83%, marathon : 75%). La moyenne des estimations est retenue si au moins 2 distances sont disponibles.ou estimée depuis la VC (`VC / 0.85`). |
| VC | **Priorité des données pour le calcul de la VC** Priorité Source Condition 1 Test VC 3'/6'/12' (colonne dédiée) `3=X/6=Y/12=Z` renseigné 2 VC déclarée directement `VC=XX` dans la colonne VMA/VC 3 Régression sur 3 temps (10km, semi, marathon) Si les 3 sont renseignés 4 Régression sur 2 temps (10km \+ semi, ou semi \+ marathon) Si 2 sont renseignés 5 Temps unique (10km \> semi \> marathon) Si 1 seul renseigné 6 Estimation depuis la VMA `VC = VMA × 0.85`  |
| Âge | Calculé depuis la date de naissance (CSV). |
| FC max théorique | Formule de Tanaka : `208 – 0.7 × âge`. |
| Zones CAP (%VMA) | Origine : Adapté des travaux de Véronique Billat et de l'INSEP sur la modélisation de l'entraînement en fonction du pourcentage de la Vitesse Maximale Aérobie (VMA). Les pourcentages définissent des zones d'intensité (récupération, endurance, tempo, seuil, VMA, anaérobie) ayant des objectifs physiologiques spécifiques (ex: amélioration du VO2max, du seuil lactique).  Référence : Billat, L. V. (2001). *Physiologie et méthodologie de l'entraînement: de la théorie à la pratique.* De Boeck Supérieur.  |
| Zones CAP (%VC) | Origine : Ce modèle est dérivé du concept de Puissance Critique développé par Monod & Scherrer en 1965, qui postule une relation hyperbolique entre l'intensité et le temps jusqu'à épuisement . Pour la pratique, il a été popularisé par Dr. Andrew Coggan qui définit la FTP (Functional Threshold Power) comme la puissance maximale soutenable environ 1 heure, et propose un système de 7 zones d'intensité basées sur des pourcentages de la FTP . Références : Monod, H., & Scherrer, J. (1965). The work capacity of a synergic muscular group. *Ergonomics*.  Allen, H., & Coggan, A. (2006). *Training and Racing with a Power Meter.* VeloPress.  |
| Zones Vélo (%FTP) | Modèle Coggan : 55% à 150% de la FTP voir ci dessus |
| Zones Natation (%vitesse 400m) | Origine : Application du même modèle de zones d'intensité utilisé en cyclisme (Coggan) et en course à pied (Billat) à la natation. La vitesse de référence est calculée à partir du temps sur 400m nage libre. Référence : Maglischo, E. W. (2003). *Swimming Fastest.* Human Kinetics. (L'ouvrage de référence pour les zones d'entraînement en natation, basé sur des concepts similaires).  |
| Zones FC (%FC max) | Modèle Karvonen : 60% à 100% de la FC max.ouOrigine : Basé sur le modèle de zones d'entraînement par Fréquence Cardiaque, popularisé par Joe Friel. Ces zones, définies comme des pourcentages de la FC max, sont utilisées depuis plusieurs décennies en physiologie de l'exercice pour encadrer les intensités d'effort. Référence : Friel, J. (2009). *The Triathlete's Training Bible.* VeloPress. |
| Allures cibles | Origine : Calcul issu de la conversion mathématique de la vitesse (km/h) en temps par unité de distance (min/km ou min/100m). La vitesse de chaque zone étant déterminée par les pourcentages de VMA, VC, ou FTP, l'allure en découle directement . |
| Niveau estimé | Origine : Méthode empirique basée sur l'échelle de référence de la VMA chez les coureurs à pied, où les seuils de performance permettent de classer un athlète en "Débutant", "Intermédiaire" ou "Avancé".   |
| Volume hebdomadaire | Calculé à partir des jours et séances déclarés, ajusté par le niveau et le genre. |

# 🧭 Cahier des charges – Planificateur d’entraînement triathlon

### **1\. Objectif général du planificateur**

À partir des données physiologiques, des disponibilités et des objectifs d’un athlète, générer un plan d’entraînement hebdomadaire personnalisé qui :

* Respecte les zones d’intensité (VMA, VC, FTP, FC).  
* Répartir les séances sur les jours disponibles (CAP, vélo, natation).  
* Intègre des séances de qualité (VMA, VC, fractionné, seuil, endurance).  
* Propose un volume et une intensité adaptés au niveau et à l’objectif.  
* Offre une progressivité sur plusieurs semaines (périodisation).

---

### **2\. Sources de données utilisées**

Le planificateur s’appuie sur les fichiers générés par l’agent d’analyse :

| Source | Contenu |
| :---- | :---- |
| `profil.json` | Données physiologiques (VMA, VC, FTP, FC max, zones, profil, objectif) |
| `disponibilites.json` | Jours d’entraînement par discipline (CAP, vélo, natation) et bi-quotidien |
| `seances_VMA.csv` | Séances de fractionné VMA (distance, %VMA, temps effort/récup, répétitions) |
| `seances_VC.csv` | Séances de fractionné VC (distance, %VC, temps effort/récup, répétitions) |

---

### **3\. Règles de construction du plan hebdomadaire**

#### **3.1. Répartition des séances par discipline**

* Pour chaque discipline (CAP, vélo, natation), le planificateur utilise la liste des jours disponibles.  
* Chaque jour ne peut contenir qu’une séance par discipline (sauf bi-quotidien).  
* Si un jour est disponible pour plusieurs disciplines, elles sont réparties en priorité selon l’objectif (ex: Ironman → priorité vélo, Sprint → priorité CAP).

#### **3.2. Types de séances**

Le planificateur propose des séances selon un cycle type de 7 jours sauf la dernière semaine ou cel s’arrète le jour de l’objectif:

| Discipline | Types de séances |
| :---- | :---- |
| CAP | Endurance, Intensité, Seuil, Fartlek, Sortie longue, Footing récupérateur. Le « Type de séance » décrit l'objectif et la forme générale de la séance. Il ne constitue pas à lui seul une zone physiologique. L'intensité de la séance est déterminée séparément à partir de la zone et de la référence physiologique appropriée (VMA, VC ou FC). Si 1 ou 2 séances par semaine, une séance d’intensité toutes les 3 séances en continu, a cheval sur plusieurs semaines.1 séance d’intensité si 3 séances minimum2 séances d’intensité si 5 séances minimum 3 séances d’intensité si 7 séances minimum 4 séances d’intensité si 10 séances ou plus minimumL’intensité doit durer entre 15’ et 30’ (temps intensité+ temps recupération active) hors échauffement avant et récupération après. |
| Vélo | Endurance, Tempo, Seuil, FTP, VO₂max, Sortie longue. Le type de séance décrit l'objectif ; l'intensité est déterminée par les zones %FTP. Il peut y avoir des intensités à chaque sortie, ou pas si sortie longue de 4h.Jamais de sortie vélo inférieure à 80’. Le plus souvent \> 150' |
| Natation | Technique, Endurance, Seuil, Sprint, Anaérobie. L'intensité est déterminée par les zones %vitesse 400 m.Séance entre 2 et 6km pour les plus assidu. |
| Renforcement musculaire | Une séance par semaine à dispatcher différents jours. (tu mets juste le type de renforcement à faire, je mettrais les protocoles après) Le même jour, ou pas, avec une autre séance, à dispatcher en fonction de la planification.  |

#### **3.3. Choix des séances de qualité (CAP)**

* Si ni VMA ni VC ne sont disponibles → mettre 3 tests de 3’/6’/12’ distants de 48 h minimum pour déterminer la VC et estimer la VMA.  
* Si une VMA est disponible → le planificateur peut sélectionner des séances dont l'intensité est exprimée en %VMA.  
* Si une VC est disponible → le planificateur peut sélectionner des séances dont l'intensité est exprimée en %VC.  
* Si VMA et VC sont disponibles → le planificateur peut alterner les références VMA et VC selon l'objectif physiologique des séances.  
* Le type de séance est choisi selon l'objectif (intensité, seuil, fartlek, etc.) et la référence physiologique est choisie séparément.  
* Les séances sélectionnées doivent respecter les zones, les durées d'effort et les règles de récupération définies dans les bases de séances et l'Annexe 4\.


#### **3.4. Calcul du volume**

* Le volume hebdomadaire (en minutes) est estimé à partir du nombre de jours d’entraînement déclarés.  
* Un coefficient de niveau est appliqué :  
  * Débutant : 0.8 (volume réduit)  
  * Intermédiaire : 1.0  
  * Avancé : 1.2  
* La durée des séances est ajustée en fonction de l’objectif (ex: Ironman → plus de volume en vélo).

#### **3.5. Périodisation (macrocycle)**

Voici **10 règles fondamentales** à intégrer dans votre cahier des charges pour un planificateur d'entraînement respectant les principes de périodisation, synthétisées à partir des modèles de Matveev, Billat, Poliquin, Issurin et du modèle norvégien :

---

1. **Alternance systématique charge/récupération**  
   Le programme doit imposer une structure cyclique alternant phases de stress physiologique (entraînement) et de récupération, basée sur le principe de **surcompensation** (Selye) pour garantir des adaptations positives.

2. **Hiérarchie des cycles temporels**  
   Intégrer **4 niveaux de planification** :

   * Microcycles (1 semaine : alternance intensité/volume/récupération)  
   * Mésocycles (3–6 semaines : objectif d’adaptation spécifique)  
   * Macrocycles (3–12 mois : saison ou objectif majeur)  
   * Plan pluriannuel (2–4 ans : progression long terme).  
3. **Inversion volume/intensité**  
   Appliquer la règle : **« Quand l’intensité augmente, le volume diminue »**, et inversement, pour éviter la surcharge et optimiser l’adaptation.

4. **Phases classiques obligatoires**  
   Structurer l’année en **4 phases (Hors triathlon)** :

   * Préparation générale (volume élevé, intensité faible)  
   * Préparation spécifique (volume modéré, intensité élevée)  
   * Compétition/pic de forme (volume réduit, intensité maximale)  
   * Transition (repos actif, récupération physique et mentale).

5. **Variation des stimuli**  
   Éviter l’accoutumance en **diversifiant les stimuli** (exercices, méthodes, intensités) pour maintenir les gains physiologiques.

6. **Spécificité progressive**  
   Orienter l’entraînement des **bases générales** (endurance, force) vers les **qualités spécifiques** (vitesse, puissance, technique) au fil des phases.

7. **Flexibilité adaptative**  
   Permettre des ajustements dynamiques (ex : modèle norvégien) pour répondre aux feedbacks (fatigue, progrès, blessures), tout en conservant la structure globale.

8. **Réduction périodique de charge**  
   Intégrer des **baisses de volume de 25–35 % toutes les 3–4 semaines** (ex : modèle norvégien) pour prévenir le surentraînement.

9. **Distribution équilibrée des séances**  
   Alterner **jours difficiles/jours faciles** (périodisation ondulante) et, si pertinent, **2 séances/jour** avec gestion de l’intensité (ex : 80 % du volume en endurance à faible intensité, Z1–Z2).

10. **Alignement sur les objectifs de performance**  
    Caler les pics de forme (blocs de réalisation ou phases de compétition) sur les **dates clés** (compétitions, tests) en respectant les délais d’adaptation (ex : 2–4 semaines pour un pic).

11. **Prendre en compte les compétitions intermédiaires comme un entraînement d’intensité**  
    Il faut alléger la semaine précédente en intensité remplacé par la course mais ne pas faire un affûtage comme avant l’objectif principal

12. **Le dernier jour est celui de l’objectif qu’il faut mettre dans le plan et faire la planification pour arriver au top ce jour là**  
    Il faut faire mettre le statut d'affûtage les jours précédents la compétition suivant la méthode de  planification.  
    

---

### **4\. Algorithme de génération (pas à pas)**

1. Charger les données de l’athlète (`profil.json`, `disponibilites.json`, `seances_VMA.csv`, `seances_VC.csv`).  
2. Déterminer le nombre de jours d’entraînement par discipline.  
3. Calculer le volume hebdomadaire cible par discipline (minutes).  
4. Répartir les séances sur les jours disponibles (1 séance par discipline par jour).  
5. Sélectionner les références VMA ou VC  pour les jours de CAP identifiés comme "intenses".  
6. Générer les séances d’endurance pour les autres jours (Z2).  
7. Ajouter les séances de vélo et natation selon les jours disponibles (endurance, seuil, technique).  
8. Appliquer les règles de périodisation définies au §3.5 .  
9. Exporter le plan en CSV et PDF (avec le filigrane Sigle\_Papy.gif à la racine et aussi large que la page)  
10. Une fois le CSV validé ou amendé, le traduire pour l’interface  Intervals ICU.

---

### **5\. Exemple de sortie (plan hebdomadaire)**

| Jour | CAP | Vélo | Natation |
| :---- | :---- | :---- | :---- |
| Lundi | Endurance Z2 (45 min) | – | – |
| Mardi | Intensité 15x(200m/50m en 40”/20”) référence VMA  | – | Technique (3km) |
| Mercredi | – | Endurance Z2 (60 km) | – |
| Jeudi | Seuil 2 6x(800m/200m en 2’50”/1’20”) référence VC  | – | Seuil (4km) |
| Vendredi | Footing récup (30 min) | – | – |
| Samedi | Sortie longue Z2 (60 min) | Sortie longue Z2 (90 km) | – |
| Dimanche | Repos | Sortie longue 4h avec 10 sprint de 50m | – |

---

#### **Voici les colonnes à afficher dans le résultat :**


| N°semaine | Jour | Date | Discipline | Type de séance | Détails | Durée | Journée type | Plaisir (0-5) | Retour athlète | Commentaires | Niveau semaine \+ Séances clés | Message Envoyé ? |
| :---: | :---- | :---: | :---: | :---- | :---- | :---: | :---: | :---- | :---- | :---: | :---: | :---: |

1. N° semaine \= “Emoji S- le nombre de semaine qu’il reste avant l’objectif final”, le premier jour de la semaine étant le lundi (exemple : 🟢S-03 est du lundi 3 au dimanche 9, semaine normale, si l’objectif est le samedi 29, 🔵S-0 pour la semaine contenant l’objectif)  
   Emoji au choix reflétant la difficulté globale de la semaine (basé sur volume \+ intensité)   ⚪=récupération  🔵\=Affutage avant des courses 🟢=Semaine normale 🟡=semaine légèrement chargée  🔴\=semaine dure 🟤=semaine exceptionnelle la plus dure de la préparation.   
2. Jour \= Lundi, Mardi,..., Dimanche, Si plusieurs exercice le même jour mettre une étoile à la place du jour du second exercice  
3. Date \= Date de l’exercice  
4. Discipline \= sport pratiqué  
5. Type de séance \= Intensité, seuil, fartlek, endurance, etc…  
6. Détails \= détails de la séance  
7. Durée \= Durée prévu de la séance  
8. Journée type \= Emoji reflétant la difficulté de la journée (🟩=Endurance, 🟨=Seuil, 🟥=Intense, 🟦=Récupération, 🔲\=Rien)  
9. Plaisir (0-5) \= Colonne de saisie de l’athlete pour ses sentiments après la séance.  
10. Retour Athlete \= Saisie libre des retours de l'athlète.  
11. Commentaires, Niveau semaine \+ Séances clés et Message Envoyé ? sont des colonnes libre

#### **Ne pas oublier de sortir un fichier d’interface pour mettre dans interval/ICU dans le compte de l’athlète**

### **6\. Critères de validation du plan**

* Le plan est typé triathlon, Swimrun (CAP/Natation), Natation, Cyclisme ou CAP et utilise les méthodes adapté à chacun de ces 5 sports  
* Toutes les séances sont dans les zones d’intensité définies.  
* Le volume hebdomadaire ne dépasse pas la capacité estimée.  
* Les séances de qualité (VMA/VC) sont espacées d’au moins 36h par discipline.  
* Le plan respecte la progressivité (pas d’augmentation brutale du volume).  
* Pas 2 semaines identiques.  
* Le dernier jour doit être celui du plan  
* Le plan débute toujours un lundi. Si le lundi est dépassé, si le plan débute le mercredi, mettre la ligne mardi et lundi vide d’exercice.  
* Mettre aussi les journée de repos, ne pas oublier un jour. (un renforcement musculaire peut être mis un jour de repos)  
* Contrôles minimum :  
  * objectif correctement positionné ;  
  * disponibilités respectées ;  
  * disciplines respectées ;  
  * volume dans la limite définie ;  
  * progressivité respectée ;  
  * 80/20 respecté ;  
  * espacement des séances intenses respecté ;  
  * aucune journée impossible ;  
  * périodisation respectée ;  
  * semaine d'affûtage correcte ;  
  * compétitions intermédiaires correctement traitées ;  
  * aucune séance hors des zones autorisées.

---

### **7\. Prochaine étape technique**

Une fois ce cahier des charges validé, je peux coder le module `planificateur.py` qui implémente cet algorithme en Python. Il utilisera :

* `pandas` pour la manipulation des données.  
* `json` pour charger les profils.  
* `reportlab` pour exporter le plan en PDF.  
* `datetime` pour la gestion des semaines.

### **8\. Ajout initial**

Pour le  lancement du programme planificateur,  le sous programme de planificateur "liste.py" va lister tous les noms de dossiers d'athlètes en attente et proposer la liste avec des n°.  
Ainsi je choisi dans la liste et je ne fais pas d'erreur syntaxique en tapant le nom de l'athlète

### **9\. Contrainte technique finale**

TOUS LES PROGRAMMES (\*.py)  DEVRONT AVOIR EN COMMENTAIRE INITIAL UN DESCRIPTIF DE LEUR FONCTION

---

# **NOUVELLE APPROCHE :** **Plan de base PDF → Intervals.ICU → Retour**

### **Philosophie**

"On ne planifie pas pour un athlète, on planifie AVEC l'athlète."

Le plan est une base de travail, pas une prescription figée. L'athlète saisit ses retours dans [Intervals.ICU](https://intervals.icu/), et le programme ajuste le plan en conséquence.

### **Flux de travail**

┌─────────────────────────────────────────────────────────────────────┐  
│                    ÉTAPE 1 : PLAN DE BASE                           │  
│  • Généré par le planificateur (Option 2\)                           │  
│  • Exporté en PDF (aperçu) \+ CSV                                    │  
│  • le CSV, validé et amendé, est traduit pour Intervals puis        │  
│    Importé dans Intervals.ICU                                       │  
└───────────────────────────┬─────────────────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────────────────┐  
│                    ÉTAPE 2 : L'ATHLÈTE S'ENTRAÎNE                   │  
│  • Suit le plan dans Intervals.ICU                                  │  
│  • Saisie RPE \+ commentaires après chaque séance                    │  
│  • Saisie données de bien-être (FC repos, HRV, poids)               │  
└───────────────────────────┬─────────────────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────────────────┐  
│                    ÉTAPE 3 : RÉCUPÉRATION DES RETOURS               │  
│  • Programme interroge l'API Intervals.ICU                          │  
│  • Récupère : RPE, commentaires, CTL, ATL, TSB                      │  
│  • Période : 1-4 semaines                                           │  
└───────────────────────────┬─────────────────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────────────────┐  
│                    ÉTAPE 4 : ANALYSE ET AJUSTEMENT                  │  
│  • Calcul du TSB réel                                               │  
│  • Détection des écarts (fatigue, progression)                      │  
│  • Génération des ajustements :                                     │  
│    \- Allègement si TSB \< \-25                                        │  
│    \- Remplacement par récupération si TSB \< \-40                     │  
│    \- Intensification si progression \> 5%                            │  
└───────────────────────────┬─────────────────────────────────────────┘  
                            │  
                            ▼  
┌─────────────────────────────────────────────────────────────────────┐  
│                    ÉTAPE 5 : NOUVEAU PLAN                           │  
│  • PDF mis à jour (2 parties : plan \+ ajustements)                  │  
│  • Mise à jour automatique du plan dans Intervals.ICU               │  
│  • Notification à l'athlète                                         │  
└─────────────────────────────────────────────────────────────────────┘

# **Rajout fin de planification.**

Comment introduire un agent IA qui à partir d’une saisie libre complémentaire, va modifier le planning CSV avant la traduction pour Intervals.ICU 

P.e. “Mettre toutes les intensités de CAP le Mercredi”, “La natation sera impossible du 1er au 10 aout”, etc… Et l’agent modifie le plan en conséquence en respectant le cahier des charges.

# Annexes

# Annexes

# **Annexe 1**

# **Sources et méthode de calcul de la VC et de la VMA**

### **1\. Vitesse Critique (VC) – Méthode validée scientifiquement**

| Source | Détail |
| :---- | :---- |
| Modèle de Monod & Scherrer (1965) | Concept de Puissance Critique (CP) ou Vitesse Critique (CS), relation linéaire entre distance et temps pour des efforts de 3 à 30 minutes . |
| Smyth et al. (2020) | Validation terrain sur 25 000 coureurs : relation distance-temps linéaire (R \= 0,9999) . |
| Pettitt (2016) | Recommande les tests de 3, 7 et 12 minutes pour estimer la VC . |
| Gorostiaga et al. (2022) | La VC correspond à 95-99% de la vitesse moyenne sur la plus longue distance choisie . |

Calcul de la VC :

* Avec 3 distances (ex: 10km, semi, marathon) → régression linéaire de la relation distance/temps. La pente de la droite est la VC (en m/s) .  
* Avec 2 distances → régression linéaire sur 2 points (même modèle, moins précis).

Référence :  
Monod, H., & Scherrer, J. (1965). *The work capacity of a synergic muscular group*. Ergonomics.  
Pettitt, R. W. (2016). *Applying the Critical Speed Concept to Racing Strategy*. IJSPP.  
Gorostiaga, E. M., et al. (2022). *Over 55 years of critical power: Fact or artifact?* Scand J Med Sci Sports.

---

### **2\. VMA estimée – Approche par pourcentage de soutien**

La VMA n’est pas directement donnée par une seule distance, mais on peut l’estimer à partir des pourcentages de soutien moyens  :

| Distance | % de VMA typique |
| :---- | :---- |
| 10 km | 85–90% |
| Semi-marathon | 80–85% |
| Marathon | 70–80% |

Méthode proposée :

1. Calculer la vitesse moyenne sur chaque distance (km/h).  
2. Diviser chaque vitesse par le pourcentage de VMA correspondant (ex: 10km → 0,88).  
3. Faire la moyenne des VMA estimées (si 2 ou 3 distances disponibles).

Formule :

`text`

`VMA_estimee = moyenne( (vitesse_10km / 0,88), (vitesse_semi / 0,83), (vitesse_marathon / 0,75) )`

Source des % :

* 10km : 85–90%   
* Semi-marathon : 80–85%   
* Marathon : 70–80% 

---

### **3\. Comparaison avec la VMA déclarée**

| Cas | Action |
| :---- | :---- |
| VMA déclarée et VMA estimée | → Alerte si écart \> 10% |
| VMA déclarée non renseignée | → Utiliser la VMA estimée comme donnée par défaut |

#  **Annexe 2** **Sources et Méthodes par Discipline**

## **1\. TRIATHLON (vue d'ensemble)**

### **Méthode principale : Modèle de périodisation de Joe Friel**

Source :

* Friel, J. (2009). *The Triathlete's Training Bible*. VeloPress.

Principes clés :

* Périodisation en 3 phases : Base (volume), Construction (intensité), Pic (spécificité)  
  \=\>Spécifique au triathlon  
  Lorsque l'objectif est un triathlon et que les trois disciplines natation, cyclisme et course à pied sont planifiées, utiliser le modèle de périodisation spécifique triathlon de Friel. Dans les autres cas, appliquer le modèle général de périodisation à quatre phases.   
* Alternance volume/intensité  
* 80/20 rule : 80% du volume en endurance (Z1-Z2), 20% en intensité (Z3+)  
* Semaine de récupération toutes les 3-4 semaines

Méthode complémentaire : Modèle Norvégien

* Réduction de volume de 25-35% toutes les 3-4 semaines  
* Pics de forme alignés sur les compétitions  
* Suivi de la charge interne (RPE, FC)

---

## **2\. NATATION**

### **Méthode principale : Ernest W. Maglischo \- "Swimming Fastest"**

Source :

* Maglischo, E. W. (2003). *Swimming Fastest*. Human Kinetics.

Fondements :

| Concept | Application |
| :---- | :---- |
| Zones d'intensité | Basées sur la vitesse critique (CV) et le seuil lactique |
| Zones Maglischo | Z1: Récupération, Z2: Endurance aérobie, Z3: Seuil, Z4: VO2max, Z5: Sprint, Z6 `Anaérobie`  |
| Volume vs Intensité | 80% du volume en Z1-Z2, 20% en Z3-Z5 |

Zones utilisées dans le planificateur :

`text`

`Z1 - Récupération : < 55% vitesse 400m`  
`Z2 - Endurance : 55-75% vitesse 400m`  
`Z3 - Seuil aérobie : 75-90% vitesse 400m`  
`Z4 - VO2max : 90-105% vitesse 400m`  
`Z5 - Sprint : 105-120% vitesse 400m`

`Z6 - Anaérobie : 120-150% vitesse 400m`

Auteur pour la modélisation : Concept de "Critical Swim Speed" (CSS) basé sur les travaux de :

| Auteur | Contribution |
| :---- | :---- |
| Monod & Scherrer (1965) | Concept de Puissance Critique |
| Wakayoshi et al. (1992) | Application à la natation \- Critical Swimming Speed |
| Pyne et al. (2001) | Validation des zones d'entraînement en natation |

Séances types :

* Technique : Exercices de placement, respiration, virage (basé sur les travaux de Maglischo sur l'efficacité hydrodynamique)  
* Endurance : Longues distances en Z2 (amélioration du VO2max)  
* Seuil : Intervalles en Z4 (amélioration du seuil lactique)  
* Sprint : Courtes distances en Z5-Z6 (puissance anaérobie)

---

## **3\. CYCLISME**

### **Méthode principale : Dr. Andrew Coggan \- Modèle FTP**

Source :

* Allen, H., & Coggan, A. (2006). *Training and Racing with a Power Meter*. VeloPress.

Fondements :

| Concept | Définition |
| :---- | :---- |
| FTP | Functional Threshold Power \- puissance maximale soutenable \~1h |
| 7 zones Coggan | Basées sur %FTP |
| TSS | Training Stress Score \- quantification de la charge |

Zones Coggan utilisées :

`text`

`Z1 - Récupération : < 55% FTP`  
`Z2 - Endurance : 55-75% FTP`  
`Z3 - Tempo : 75-90% FTP`  
`Z4 - Seuil : 90-105% FTP`  
`Z5 - VO2max : 105-120% FTP`  
`Z6 - Capacité anaérobie : 120-150% FTP`

`Z7 - Neuromusculaire : > 150% FTP théorique non utilisée par le planificateur`

Auteurs complémentaires :

| Auteur | Contribution | Référence |
| :---- | :---- | :---- |
| T. Noakes | Concept de "Central Governor" | Noakes, T. (2012). *Lore of Running* |
| S. Seiler | Modèle polarisé 80/20 | Seiler, S. (2010). "What is best practice for training intensity and duration distribution in endurance athletes?" |
| M. Buchheit | Périodisation spécifique | Buchheit, M. (2014). "Monitoring training status with HR measures" |

Séances types :

* Endurance : Z2 \- longs parcours (développement du VO2max)  
* Tempo : Z3 \- travail au seuil aérobie  
* Seuil : Z4 \- intervalles au FTP (amélioration du seuil lactique)  
* VO2max : Z5 \- intervalles courts/intenses  
* Sortie longue : Z2 \- adaptation à l'endurance

---

## **4\. CAP (Course à Pied)**

### **Méthode principale : Véronique Billat \- Modèle VMA**

Source :

* Billat, L. V. (2001). *Physiologie et méthodologie de l'entraînement: de la théorie à la pratique*. De Boeck Supérieur.

Fondements :

| Concept | Définition |
| :---- | :---- |
| VMA | Vitesse Maximale Aérobie \- vitesse au VO2max |
| Zones VMA | %VMA pour chaque zone d'intensité |
| CV | Critical Velocity (ou Vitesse Critique) |

Zones VMA Billat :

`text`

`Z1 - Récupération : < 60% VMA`  
`Z2 - Endurance fondamentale : 60-75% VMA`  
`Z3 - Tempo/Seuil : 75-85% VMA`  
`Z4 - Seuil anaérobie : 85-95% VMA`  
`Z5 - Intensité : 95-105% VMA`

`Z6 - Anaérobie : > 105% VMA`

Zones VC (Vitesse Critique) :

`text`

`Z1 - Récupération : < 55% VC`  
`Z2 - Endurance : 55-75% VC`  
`Z3 - Seuil : 75-90% VC`  
`Z4 - VO2max : 90-105% VC`  
`Z5 - Sprint : 105-120% VC`

`Z6 - Anaérobie : 120-150% VC`

Auteurs complémentaires :

| Auteur | Contribution | Référence |
| :---- | :---- | :---- |
| P. Billat | Application pratique VMA | Billat, V. (2001). "Interval training at VO2max" |
| R. Pettitt | Critical Speed pour l'entraînement | Pettitt, R. (2016). "Applying the Critical Speed Concept" |
| I. Mujika | Périodisation en CAP | Mujika, I. (2017). "The science of training" |
| D. Martin | Modèles d'entraînement | Martin, D. (2012). *Better Training for Distance Runners* |

Séances types :

* Z1 — Récupération : footing actif à faible intensité  
* Z2 — Endurance : endurance aérobie / sorties longues  
* Z3 — Seuil 1 : tempo run / travail autour du seuil inférieur  
* Z4 — Seuil 2 : intervalles longs / travail autour du seuil supérieur  
* Z5 — Intensité : intervalles courts à haute intensité  
* Z6 — Haute intensité : efforts très courts / intensité maximale

---

## **5\. Synthèse des Méthodes par Discipline**

| Discipline | Méthode Principale | Auteur Principal | Source |
| :---- | :---- | :---- | :---- |
| Triathlon | Périodisation Friel | Joe Friel | The Triathlete's Training Bible |
| Natation | Critical Swim Speed | E.W. Maglischo | Swimming Fastest |
| Cyclisme | Modèle Coggan (FTP) | Andrew Coggan | Training and Racing with a Power Meter |
| CAP | Modèle Billat (VMA) | Véronique Billat | Physiologie et méthodologie de l'entraînement |

---

## **6\. Sources des Zones d'Entraînement Utilisées**

### **Zones CAP (Billat)**

| Source | Zone | %VMA |  | Zone |
| :---- | :---- | :---- | :---- | :---- |
| Billat (2001) | Z1 | \< 60 %  |  | Récupération  |
| Billat (2001) | Z2 | 60-75% |  | Endurance fondamentale |
| Billat (2001) | Z3 | 75-85% |  | Tempo/Seuil 1 |
| Billat (2001) | Z4 | 85-95% |  | Seuil 2 anaérobie |
| Billat (2001) | Z5 | 95-105% |  | Intensité /VO2max |
| Billat (2001) | Z6 | \>105% |  | Haute intensité Anaérobie |

### 

| Zone | %VC | Usage |
| :---: | ----- | ----- |
| Z1 | \<55 % | Récupération |
| Z2 | 55–75 % | Endurance |
| Z3 | 75–90 % | Seuil 1 |
| Z4 | 90–105 % | Seuil 2 |
| Z5 | 105–120 % | Intensité |
| Z6 | 120–150 % | Haute intensité |

### **Zones Vélo (Coggan)**

| Source | %FTP | Zone |
| :---- | :---- | :---- |
| Coggan (2006) | 0-55% | Récupération |
| Coggan (2006) | 55-75% | Endurance |
| Coggan (2006) | 75-90% | Tempo |
| Coggan (2006) | 90-105% | Seuil |
| Coggan (2006) | 105-120% | VO2max |
| Coggan (2006) | 120-150% | Anaérobie |

### **Zones Natation (Maglischo)**

| Source | %Vitesse 400m | Zone |
| :---- | :---- | :---- |
| Maglischo (2003) | 0-55% | Récupération |
| Maglischo (2003) | 55-75% | Endurance |
| Maglischo (2003) | 75-90% | Seuil aérobie |
| Maglischo (2003) | 90-105% | VO2max |
| Maglischo (2003) | 105-120% | Sprint |
| Maglischo (2003) | 120-150% | Anaérobie |

---

## **7\. Limitations et Améliorations Possibles**

### **Limitations Actuelles**

1. Pas de suivi de la charge : TSS (vélo), RPE (triathlon)  
2. Pas d'adaptation dynamique : Le plan ne s'adapte pas aux retours  
3. Périodisation standard : Pas d'ajustement individuel fin

### **Améliorations Suggérées**

1. Ajouter le suivi de la FC : Modèle Karvonen  
2. Intégrer le RPE : Échelle de Borg (6-20)  
3. Périodisation ondulante : Alternance jours faciles/difficiles  
4. Adaptation en temps réel : Ajustement selon les retours

---

Conclusion : Le planificateur s'appuie sur des méthodes validées scientifiquement :

* Billat pour la CAP  
* Coggan pour le vélo  
* Maglischo pour la natation  
* Friel pour l'intégration triathlon

Ces 4 auteurs sont les références académiques et pratiques reconnues mondialement dans leurs disciplines respectives.

#   **Annexe 3 Liste des Liens et Références Compilés**

## **1\. RÉFÉRENCES BIBLIOGRAPHIQUES**

### **CAP (Course à Pied)**

| Auteur | Année | Ouvrage/Article | Concept |
| :---- | :---- | :---- | :---- |
| Billat, L.V. | 2001 | *Physiologie et méthodologie de l'entraînement: de la théorie à la pratique*. De Boeck Supérieur. | VMA, zones d'entraînement |
| Billat, V. | 2001 | "Interval training at VO2max" | Applications pratiques VMA |
| Pettitt, R.W. | 2016 | "Applying the Critical Speed Concept to Racing Strategy". IJSPP. | Critical Speed |
| Monod, H. & Scherrer, J. | 1965 | "The work capacity of a synergic muscular group". Ergonomics. | Puissance Critique |
| Gorostiaga, E.M., et al. | 2022 | "Over 55 years of critical power: Fact or artifact?" Scand J Med Sci Sports. | Revue sur la Critical Power |
| Noakes, T. | 2012 | *Lore of Running*. Human Kinetics. | Central Governor |
| Martin, D. | 2012 | *Better Training for Distance Runners*. | Modèles d'entraînement |

### **Cyclisme**

| Auteur | Année | Ouvrage/Article | Concept |
| :---- | :---- | :---- | :---- |
| Allen, H., & Coggan, A. | 2006 | *Training and Racing with a Power Meter*. VeloPress. | FTP, 7 zones Coggan |
| Seiler, S. | 2010 | "What is best practice for training intensity and duration distribution in endurance athletes?" | Modèle polarisé 80/20 |
| Buchheit, M. | 2014 | "Monitoring training status with HR measures" | Périodisation spécifique |

### **Natation**

| Auteur | Année | Ouvrage/Article | Concept |
| :---- | :---- | :---- | :---- |
| Maglischo, E.W. | 2003 | *Swimming Fastest*. Human Kinetics. | Critical Swim Speed, zones |
| Wakayoshi et al. | 1992 | "Relationship between critical velocity and swimming performance" | Application CSS |
| Pyne et al. | 2001 | "Training and testing in swimming" | Validation des zones |

### **Triathlon et Périodisation**

| Auteur | Année | Ouvrage/Article | Concept |
| :---- | :---- | :---- | :---- |
| Friel, J. | 2009 | *The Triathlete's Training Bible*. VeloPress. | Périodisation triathlon |
| Friel, J. | 2009 | *The Triathlete's Training Bible*. VeloPress. | 80/20 rule |
| Matveev, L. | 1981 | *Fundamentals of Sports Training*. | Périodisation classique |
| Issurin, V. | 2010 | "New horizons for the methodology of physiological preparation" | Block periodization |
| Poliquin, C. | 1997 | *The Poliquin Principles*. | Périodisation ondulante |

---

## **2\. SOURCES SCIENTIFIQUES COMPLÉMENTAIRES**

### **Physiologie**

| Auteur | Année | Titre | Concept |
| :---- | :---- | :---- | :---- |
| Karvonen, M. | 1957 | "The effects of training on heart rate" | FC max (220 \- âge) |
| Selye, H. | 1936 | "A syndrome produced by diverse nocuous agents" | Syndrome général d'adaptation (surcompensation) |

### **Méthodologie**

| Auteur | Année | Titre | Concept |
| :---- | :---- | :---- | :---- |
| Smyth et al. | 2020 | "Critical speed and running performance" | Validation terrain 25 000 coureurs |

---

## **3\. STRUCTURE DU CAHIER DES CHARGES**

### **Points de Planification**

1. Objectif général : Personnalisation, zones d'intensité, répartition, progressivité  
2. Sources de données : profil.json, disponibilites.json, seances\_VMA.csv, seances\_VC.csv, bibliographie des Annexes.  
3. Règles de construction : 4 sous-règles (répartition, types, choix qualité, volume, périodisation)  
4. Algorithme de génération : 9 étapes  
5. Format de sortie : 14 colonnes dont N° semaine (émoji S-XX)  
6. Critères de validation : 7 critères (zones, volume, 48h, progressivité, semaines différentes, objectif, début lundi)  
7. Contraintes techniques : pandas, json, reportlab, datetime, [Intervals.ICU](https://intervals.icu/)

### **Émojis Utilisés**

| Émoji | Signification |
| :---- | :---- |
| ⚪ | Semaine de récupération |
| 🔵 | Affûtage avant course |
| 🟢 | Semaine normale |
| 🟡 | Semaine légèrement chargée |
| 🔴 | Semaine dure |
| 🟤 | Semaine exceptionnelle |
| 🟩 | Journée Endurance |
| 🟨 | Journée Seuil |
| 🟥 | Journée Intense |
| 🟦 | Journée Récupération |
| ⭐ | Course / Compétition |
| ⬜ | Repos |

---

## **4\. LIENS DES MODULES DU CODE**

### **Structure des Modules**

`Deepseek-athlete/`  
`│`  
`├── inputs/                          # Dossier des fichiers CSV d'entrée`  
`│   └── *.csv                        # Fichiers CSV des athlètes`  
`│`  
`├── outputs/                         # Dossier des sorties`  
`│   ├── Base par athlète/            # Données de base par athlète (créé par option 1)`  
`│   │   └── [Nom_Athlète]/           # Dossier par athlète`  
`│   │       ├── *_profil_*.json      # Profil physiologique`  
`│   │       ├── *_disponibilites_*.json  # Disponibilités`  
`│   │       ├── *_seances_VMA_*.csv  # Séances VMA générées`  
`│   │       ├── *_seances_VC_*.csv   # Séances VC générées`  
`│   │       └── *_resume_*.pdf       # Résumé PDF de l'athlète`  
`│   │`  
`│   └── plans/                       # Plans d'entraînement générés (option 2)`  
`│       └── [Nom_Athlète]/           # Dossier par athlète`  
`│           ├── *_intervals_*.csv    # Intervalles détaillés`  
`│           ├── *_plan_*.csv         # Plan d'entraînement complet`  
`│           └── *_plan_apercu_*.pdf  # Aperçu PDF du plan`  
`│`  
`├── src/`  
`│   ├── core/`  
`│   │   ├── physiology/`  
`│   │   │   ├── __init__.py`  
`│   │   │   ├── constants.py`  
`│   │   │   ├── vma.py`  
`│   │   │   ├── vc.py`  
`│   │   │   ├── ftp.py`  
`│   │   │   ├── natation.py`  
`│   │   │   └── profil.py`  
`│   │   ├── __init__.py              # MODIFIÉ (exporte PhysiologieSimple)`  
`│   │   ├── physiologie.py           # NETTOYÉ (prints supprimés)`  
`│   │   ├── physiologie_simple.py    # NOUVEAU`  
`│   │   ├── p_code_vma.py`  
`│   │   └── p_code_vc.py`  
`│   ├── export/`  
`│   │   ├── __init__.py`  
`│   │   ├── generateur_pdf.py`  
`│   │   ├── sections_pdf.py          # MODIFIÉ (repeatRows)`  
`│   │   ├── sov.py`  
`│   │   └── tables_pdf.py            # MODIFIÉ (repeatRows)`  
`│   ├── planificateur/`  
`│   │   ├── __init__.py`  
`│   │   ├── chargeur.py`  
`│   │   ├── constants_plan.py`  
`│   │   ├── export_csv.py`  
`│   │   ├── export_intervals.py`  
`│   │   ├── export_pdf_plan.py`  
`│   │   ├── main_plan.py`  
`│   │   ├── periodisation.py`  
`│   │   ├── volume.py`  
`│   │   └── generateur/`  
`│   │       ├── __init__.py`  
`│   │       ├── dates.py`  
`│   │       ├── generateur_semaine.py`  
`│   │       ├── journee.py`  
`│   │       ├── seances.py`  
`│   │       └── semaine.py`  
`│   ├── utils/`  
`│   │   ├── __init__.py`  
`│   │   ├── parsers.py`  
`│   │   └── validators.py            # NETTOYÉ (prints supprimés)`  
`│   ├── __init__.py`  
`│   ├── main.py                      # MODIFIÉ (allégé, importe PhysiologieSimple)`  
`│   ├── liste.py`  
`│   └── maj_intensites.py`  
`│`     
`├── .vscode/                         # Configuration VS Code`  
`│   └── settings.json`  
`│`  
`├── .gitignore                       # Fichiers ignorés par Git`  
`├── README.md                        # Documentation principale`  
`├── requirements.txt                 # Dépendances Python`  
`├── architecture.txt                 # Ce fichier d'architecture`  
`└── Sigle_Papy.gif                   # Logo ou image du projet`

---

## **5\. RAPPEL DES AUTEURS PAR DISCIPLINE**

| Discipline | Auteur Principal | Concept Clé | Source |
| :---- | :---- | :---- | :---- |
| CAP | Véronique Billat | VMA, zones %VMA | Physiologie et méthodologie de l'entraînement |
| CAP | Robert Pettitt | Critical Speed | IJSPP 2016 |
| CAP | Monod & Scherrer | Puissance Critique | Ergonomics 1965 |
| Cyclisme | Andrew Coggan | FTP, 7 zones | Training and Racing with a Power Meter |
| Cyclisme | Stephen Seiler | 80/20 polarisé | Revue 2010 |
| Natation | Ernest Maglischo | CSS, zones | Swimming Fastest |
| Triathlon | Joe Friel | Périodisation | The Triathlete's Training Bible |
| Périodisation | Matveev | Périodisation classique | Fundamentals of Sports Training |
| Périodisation | Issurin | Block periodization | 2010 |

---

## **6\. LIENS UTILES POUR LE SUIVI**

* Google Sheets P-Code : Base des coefficients VMA/VC (fichier extrait)  
* [Intervals.ICU](https://intervals.icu/) : Format d'export pour le compte athlète  
* ReportLab : Génération des PDF  
* Pandas : Manipulation des données CSV

---

## **Annexe 4  Explication des % VMA et VC par temps d’effort**

## **📝 SYNTHÈSE DES SOURCES PRINCIPALES**

1. Billat (CAP) \- VMA, zones, tests terrain  
2. Coggan (Vélo) \- FTP, puissance critique  
3. Maglischo (Natation) \- CSS, spécificité natation  
4. Friel (Triathlon) \- Périodisation, intégration  
5. Matveev (Périodisation) \- Structure annuelle  
6. Selye (Adaptation) \- Surcompensation  
7. Seiler (Modèle) \- 80/20 polarized

---

Voici un **tableau synthétique des pourcentages de VMA (Vitesse Maximale Aérobie) et de VC (Vitesse Critique)** à appliquer pour chaque durée d’effort, adapté aux formats intermittents type **30"/30"**, **45"/45"**, etc. Les valeurs sont basées sur les modèles physiologiques de **Billat, Monod & Schall, et Veronique Billat**, ainsi que sur les données empiriques du terrain (athlétisme, sports collectifs, cyclisme).

---

### **Tableau des % de VMA et VC par durée d’effort**

*(Pour des athlètes de niveau intermédiaire à élite, en endurance aérobie et anaérobie lactique)*

| Durée de l’effort | % VMA | % VC | Zone d’entraînement | Objectif principal |
| ----- | ----- | ----- | ----- | ----- |
| 30" | 115–120% | 125–130% | Anaérobie alactique / Puissance | Développement de la puissance et de l’explosivité |
| 45" | 110–115% | 120–125% | Anaérobie lactique / Transition | Haute intensité  |
| 1’ | 105–110% | 115–120% | Anaérobie lactique | Capacité anaérobie et VO₂max |
| 1’15" | 105% | 115% | Anaérobie lactique / Début de la VO₂max | VO₂max / haute intensité  |
| 1’30" | 100–105% | 110–115% | VO₂max (zone supérieure) | Optimisation de la consommation d’O₂ / VO₂max  |
| 2’ | 100% | 110% | VO₂max (zone centrale) | Maintien de la VO₂max |
| 2’30" | 98–100% | 105–110% | VO₂max / Endurance de vitesse | Renforcement de la capacité aérobie / VO₂max  |
| 3’ | 95–98% | 105% | VO₂max (zone inférieure) / Seuil lactique | VO₂max / transition  |
| 4’ | 95% | 100–105% | Seuil lactique (zone supérieure) | Amélioration de la vitesse au seuil, SV2 |
| 5’ | 92–95% | 100% | Seuil lactique (zone centrale) | SV1–SV2 limite haute |
| 6’ | 90–92% | 98–100% | Seuil lactique (zone inférieure) | Renforcement de la capacité à soutenir l’effort / SV1–SV2  |
| 7’ | 90% | 95–98% | SV1–SV2  (zone supérieure) | Adaptation métabolique aérobie /SV1–SV2  |
| 8’ | 88–90% | 95% | SV1–SV2  | Optimisation de l’efficacité énergétique / SV1–SV2  |
| 9’ | 88% | 93–95% | SV1–SV2  | SV1–SV2  |
| 10’ | 85–88% | 90–93% | SV1–SV2 (zone inférieure) | SV1–SV2 limite basse |

---

### **Explications clés**

#### **1\. VMA vs VC : Définitions et complémentarité**

* **VMA (Vitesse Maximale Aérobie)** : Vitesse de course associée à la **consommation maximale d’oxygène (VO₂max)**. Elle correspond à la vitesse que l’athlète peut maintenir pendant **4 à 8 minutes** selon son niveau.  
  * *Exemple* : Un coureur avec une VMA de 20 km/h ne pourra maintenir cette vitesse que pendant \~5–6 minutes en effort continu.  
  * **Utilité** : Base pour le travail de **VO₂max** et d’**endurance de vitesse**.  
* **VC (Vitesse Critique)** : La Vitesse Critique (VC) représente la limite supérieure du domaine d'intensité lourde et la frontière avec le domaine sévère. Elle correspond à une estimation du niveau maximal de puissance/vitesse compatible avec un état métabolique relativement stable. Au-dessus de la VC, la capacité d'effort est limitée et dépend notamment de la réserve D′.  
  * D′ (réserve de distance) : quantité finie de travail/distance disponible au-dessus de la Vitesse Critique (VC). Elle représente la capacité résiduelle de l'athlète à maintenir une vitesse supérieure à sa VC avant l'épuisement. Plus l'intensité est élevée au-dessus de la VC, plus cette réserve est consommée rapidement.  
  * Dans le modèle de planification, D′ peut être utilisée pour caractériser la capacité de l'athlète à soutenir des efforts au-dessus de la VC et pour contrôler la charge des séances à haute intensité.

---

#### **2\. Logique des pourcentages**

* **Efforts \< 2’** : Principalement **anaérobies** (alactique ou lactique). Les % de VMA dépassent **100 %** car l’athlète puise dans ses réserves énergétiques immédiates (ATP, phosphocréatine) et tolère une accumulation de lactate.  
  * *Exemple* : Un 30"/30" à **115–120 % VMA** sollicite la puissance et la filière anaérobie alactique.  
* **Efforts entre 2’ et 4’** : Zone de **transition entre VO₂max et seuil lactique**. Les % de VMA sont **proches de 100 %**, tandis que les % de VC dépassent **100 %** (car la VC est inférieure à la VMA).  
  * *Exemple* : Un 3’ à **95 % VMA** (soit \~105 % VC) travaille la **capacité à soutenir un effort intense** tout en développant la VO₂max.  
* **Efforts \> 4’** : intensité principalement aérobie. Selon l'intensité prescrite, l'effort peut se situer autour de SV1, entre SV1 et SV2 ou autour de SV2. La durée seule ne permet pas de déterminer la zone physiologique. Les % de VMA **diminuent** (\< 95 %), tandis que les % de VC se stabilisent autour de **90–100 %**.  
  * *Exemple* : Un 10’ à **85–88 % VMA** (soit \~95 % VC) renforce la **base aérobie** et l’efficacité énergétique.

---

#### **3\. Application pratique pour les formats intermittents**

Pour des séances type **30"/30"**, **45"/45"**, ou **1’/1’** :

* **Choisir le % en fonction de l’objectif** :  
  * **Puissance/Explosivité** : 115–120 % VMA (30") ou 110–115 % VMA (45").  
  * **VO₂max** : 100–105 % VMA (1’–2’).  
  * **Seuil lactique** : 90–95 % VMA (3’–5’).  
  * **Travail aérobie :** 85–90 % VMA (6’–10’), selon l’objectif autour de SV1 ou entre SV1 et SV2.   
* **Récupération** :  
  * Pour les efforts **\> 100 % VMA**, la récupération doit être **active** (marche, footing très léger) ou **complète** (arrêt) selon la durée de l’effort.  
  * *Exemple* : Pour un 30"/30" à 120 % VMA, la récupération à 30 % VMA (marche) permet de maintenir la qualité des répétitions.

---

#### **4\. Adaptation selon le niveau de l’athlète**

| Niveau | % VMA (efforts courts) | % VMA (efforts longs) | Remarques |
| ----- | ----- | ----- | ----- |
| Débutant | '-5 % | '+0 % | Risque de surentraînement : réduire l’intensité |
| Intermédiaire | ±0 % | ±0 % | Respecter les pourcentages du tableau |
| Élite | '+2–3 % | '-2–3 % | Meilleure tolérance aux efforts intenses |

---

#### **5\. Exemple concret : Séance type 30"/30"**

* **Objectif** : Développer la puissance anaérobie alactique.  
* **Intensité** : **115–120 % VMA** (ou 125–130 % VC).  
* **Récupération** : 30" à **30–40 % VMA** (marche ou footing très lent).  
* **Volume** : 10–15 répétitions (débutant) à 20–30 répétitions (élite).  
* **Fréquence** : 1–2 séances/semaine, espacées de 48h.

---

#### **6\. Références scientifiques**

* **Billat (1996, 2001\)** : Travaux sur la VMA et son application en entraînement intermittent.  
* **Monod & Schall (1994)** : Modèle de la **Vitesse Critique**, base pour les efforts \> 4’.  
* **Seiler (2010)** : Répartition des zones d’intensité (80/20) et application en endurance.  
* **Buchheit & Laursen (2013)** : Optimisation des séances HIIT (High-Intensity Interval Training).

---

### **Recommandation finale**

Pour un **planificateur automatisé**, intégrez :

1. Un **calculateur de VMA et VC** (via tests terrain : demi-Cooper, 3’ all-out, etc.).  
2. Une **base de données des % par durée** (comme le tableau ci-dessus).  
3. Un **système d’ajustement** selon le niveau, l’âge, et la discipline de l’athlète.  
4. Des **alertes** pour éviter les combinaisons dangereuses (ex : 10 x 1’ à 110 % VMA sans récupération suffisante).

