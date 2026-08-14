#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import pandas as pd
from datetime import datetime

# Ajouter le chemin src/ pour les imports
sys.path.insert(0, os.path.dirname(__file__))

from core.physiologie import Physiologie
from core.p_code_vma import generer_seances_vma
from core.p_code_vc import generer_seances_vc
from utils.parsers import parser_bi_quotidien
from utils.validators import analyser_jours_disponibles
from es.sov import sauvegarder_json, sauvegarder_csv
from es.pdf_generator import generer_pdf_athlete
from planificateur import planifier_athlete
from liste import choisir_athlete
from maj_intensites import maj_intensites


def analyser_csv():
    print("\n" + "="*60)
    print("📊 AGENT D'ANALYSE - Génération des séances")
    print("="*60)

    csv_file = input("📁 Nom du fichier CSV (dans inputs/) : ").strip()
    if not csv_file.endswith('.csv'):
        csv_file += '.csv'
    csv_path = os.path.join('inputs', csv_file)

    if not os.path.exists(csv_path):
        print(f"❌ Fichier {csv_path} introuvable")
        return

    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', delimiter=';')
        if df.empty:
            print(f"⚠️ Le fichier {csv_path} est vide.")
            return

        print(f"✅ {len(df)} athlètes chargés")

        base_dir = 'outputs/Base par athlète'
        os.makedirs(base_dir, exist_ok=True)

        for index, row in df.iterrows():
            athlete = row.to_dict()
            nom_brut = athlete.get('Prénom/Nom', f'Athlète {index+1}')
            nom_fichier = nom_brut.replace(' ', '_').replace('/', '_')
            sexe = athlete.get('Sexe', 'M').upper()

            print(f"\n--- {nom_brut} ---")

            try:
                physio = Physiologie(athlete)
            except Exception as e:
                print(f"   ❌ Erreur physiologie : {e}")
                continue

            vma = physio.vma
            vc = physio.vc
            seances_vma = []
            seances_vc = []

            if vma:
                print(f"   VMA : {vma} km/h (origine : {physio.vma_origine})")
                seances_vma = generer_seances_vma(vma, sexe)
            else:
                print("   ⚠️ VMA non renseignée")

            if vc:
                print(f"   VC : {vc} km/h (origine : {physio.vc_origine})")
                seances_vc = generer_seances_vc(vc, sexe)
            else:
                print("   ⚠️ VC non renseignée")

            if physio.profil:
                print(f"   Profil : {physio.profil}")

            jours_dispos = analyser_jours_disponibles(athlete)
            nb_bi = parser_bi_quotidien(athlete.get('Possibilité de faire du bi-quotidien ? voire Tri ou quadri ?', ''))

            athlete_dir = os.path.join(base_dir, nom_fichier)
            os.makedirs(athlete_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # ---- PROFIL.JSON ----
            profil = {
                "nom": nom_brut,
                "sexe": physio.genre,
                "age": physio.age,
                "taille_poids": athlete.get('Taille/Poids', ''),
                "metier_contraintes": athlete.get('Métier et ses contraintes', ''),
                "objectif_principal": athlete.get('Objectif principal', ''),
                "format_competition": athlete.get('Quel format de compétition ?', ''),
                "competition_objectif": athlete.get('Quelle est la compétition objectif ?', ''),
                "courses_preparatoires": physio.courses_preparatoires,
                "physiologie": {
                    "vma": physio.vma,
                    "vma_origine": physio.vma_origine,
                    "vc": physio.vc,
                    "vc_origine": physio.vc_origine,
                    "ftp": physio.ftp,
                    "temps_400m_natation": physio.temps_400m,
                    "fc_max_cap": physio.fc_max_cap,
                    "fc_max_natation": physio.fc_max_natation,
                    "fc_max_velo": physio.fc_max_velo
                },
                "profil": physio.profil,
                "vitesses_performances": physio.vitesses_performances,
                "alertes": physio.alertes_profil + [m['donnee'] + " : " + m['statut'] for m in physio.manques],
                "zones": {
                    "vma": physio.tableau_vma,
                    "vc": physio.tableau_vc
                },
                "disponibilites": jours_dispos,
                "bi_quotidien_nb": nb_bi,
                "seances": {
                    "VMA": f"{nom_fichier}_seances_VMA_{timestamp}.csv" if seances_vma else None,
                    "VC": f"{nom_fichier}_seances_VC_{timestamp}.csv" if seances_vc else None
                }
            }

            profil_path = sauvegarder_json(profil, os.path.join(athlete_dir, f'{nom_fichier}_profil_{timestamp}'))
            print(f"   ✅ Profil sauvegardé : {os.path.basename(profil_path)}")

            dispo_path = sauvegarder_json(jours_dispos, os.path.join(athlete_dir, f'{nom_fichier}_disponibilites_{timestamp}'))
            print(f"   ✅ Disponibilités sauvegardées : {os.path.basename(dispo_path)}")

            if seances_vma:
                df_vma = pd.DataFrame(seances_vma)
                vma_path = sauvegarder_csv(df_vma, os.path.join(athlete_dir, f'{nom_fichier}_seances_VMA_{timestamp}'))
                print(f"   ✅ {len(seances_vma)} séances VMA sauvegardées dans {os.path.basename(vma_path)}")

            if seances_vc:
                df_vc = pd.DataFrame(seances_vc)
                vc_path = sauvegarder_csv(df_vc, os.path.join(athlete_dir, f'{nom_fichier}_seances_VC_{timestamp}'))
                print(f"   ✅ {len(seances_vc)} séances VC sauvegardées dans {os.path.basename(vc_path)}")

            generer_pdf_athlete(nom_brut, physio, jours_dispos, nb_bi, seances_vma, seances_vc, athlete_dir)

        print("\n🎉 Analyse terminée !")
        print(f"📁 Données par athlète dans : {base_dir}")

    except Exception as e:
        print(f"❌ Erreur générale : {e}")


def planifier():
    print("\n" + "="*60)
    print("📅 PLANIFICATEUR D'ENTRAÎNEMENT")
    print("="*60)
    
    # Utiliser liste.py pour sélectionner l'athlète
    nom = choisir_athlete()
    if not nom:
        print("❌ Planification annulée.")
        return
    
    athlete_dir = os.path.join('outputs/Base par athlète', nom)
    
    if not os.path.exists(athlete_dir):
        print(f"❌ Athlète {nom} non trouvé")
        return
    
    # Demander la semaine
    semaine = input("Numéro de semaine (1 à 4) : ").strip()
    semaine = int(semaine) if semaine.isdigit() else 1
    
    # Demander la date de début
    date_debut = input("Date de début (YYYY-MM-DD) ou laisser vide pour aujourd'hui : ").strip()
    if not date_debut:
        date_debut = None
    
    # Générer le plan
    plan = planifier_athlete(athlete_dir, semaine, date_debut)
    
    if "error" in plan:
        print(f"❌ {plan['error']}")
        return
    
    # Afficher le plan
    print(f"\n📅 Plan pour {plan['athlete']} - Semaine {plan['semaine']} (début: {plan['date_debut']})")
    print(f"   Type de semaine : {plan.get('type_semaine_emoji', '🟢')} {plan.get('type_semaine', 'normale')}")
    print(f"   Volume total : {plan.get('volume_total', 0)} min")
    print("="*60)
    
    for jour, data in plan['plan'].items():
        print(f"\n{jour} ({data['date']}) :")
        if not data['seances']:
            print("   ⬜ Repos")
        else:
            for seance in data['seances']:
                emoji = plan['plan'][jour].get('emoji_journee', '')
                if seance.get('est_course'):
                    print(f"   ⭐ {seance['details']}")
                else:
                    print(f"   {emoji} {seance['discipline']} : {seance['type']} - {seance['details']} ({seance['duree']} min)")


def mise_a_jour_intensites():
    print("\n" + "="*60)
    print("🔄 MISE À JOUR DES INTENSITÉS")
    print("="*60)
    
    # Utiliser liste.py pour sélectionner l'athlète
    nom = choisir_athlete()
    if not nom:
        print("❌ Mise à jour annulée.")
        return
    
    athlete_dir = os.path.join('outputs/Base par athlète', nom)
    
    if not os.path.exists(athlete_dir):
        print(f"❌ Athlète {nom} non trouvé")
        return
    
    # Demander les nouvelles valeurs
    nouvelle_vma = input("Nouvelle VMA (km/h) ou laisser vide : ").strip()
    nouvelle_vma = float(nouvelle_vma) if nouvelle_vma else None
    
    nouvelle_vc = input("Nouvelle VC (km/h) ou laisser vide : ").strip()
    nouvelle_vc = float(nouvelle_vc) if nouvelle_vc else None
    
    if not nouvelle_vma and not nouvelle_vc:
        print("❌ Aucune nouvelle valeur saisie.")
        return
    
    maj_intensites(athlete_dir, nouvelle_vma, nouvelle_vc)


def menu():
    print("\n" + "="*60)
    print("🏊‍♂️ DEEPSEEK ATHLETE - OUTIL D'ENTRAÎNEMENT")
    print("="*60)
    print("1. 📊 Analyser un CSV (agent)")
    print("2. 📅 Planifier un entraînement (planificateur)")
    print("3. 🔄 Mettre à jour les intensités (post-tests)")
    print("9. 🚪 Quitter")
    print("="*60)


def main():
    os.makedirs('inputs', exist_ok=True)
    os.makedirs('outputs/Base par athlète', exist_ok=True)

    while True:
        menu()
        choix = input("\nVotre choix : ").strip()

        if choix == '1':
            analyser_csv()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '2':
            planifier()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '3':
            mise_a_jour_intensites()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '9':
            print("\n👋 Au revoir !")
            break
        else:
            print("❌ Choix invalide.")


if __name__ == '__main__':
    main()