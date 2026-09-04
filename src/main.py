# ============================================================
# FICHIER: src/main.py
# RÔLE: Point d'entrée principal de l'application
#       CORRIGÉ: Passage des valeurs saisies à PhysiologieSimple
# ============================================================

import os
import sys
import pandas as pd
import math
import re
from datetime import datetime

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

sys.path.insert(0, os.path.dirname(__file__))

from core.physiologie import Physiologie
from core.physiologie_simple import PhysiologieSimple
from core.p_code_vma import generer_seances_vma
from core.p_code_vc import generer_seances_vc
from utils.parsers import parser_bi_quotidien
from utils.validators import analyser_jours_disponibles
from export.sov import sauvegarder_json, sauvegarder_csv, sauvegarder_pdf
from export import generer_pdf_athlete
from export.sections_pdf import ajouter_section_intensites
from export.tables_pdf import generer_tableau_vma, generer_tableau_vc
from planificateur import planifier_athlete
from liste import choisir_athletes, choisir_element
from maj_intensites import maj_intensites


# ============================================================
# FONCTIONS DE LECTURE
# ============================================================

def detecter_encodage(fichier_path: str) -> str:
    if HAS_CHARDET:
        try:
            with open(fichier_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8-sig')
        except Exception:
            pass
    return 'utf-8-sig'


def lire_fichier_donnees(fichier_path: str) -> pd.DataFrame:
    enc = detecter_encodage(fichier_path)
    
    df = pd.read_csv(
        fichier_path,
        delimiter='\t',
        encoding=enc,
        engine='python',
        quotechar='"',
        dtype=str,
        keep_default_na=False
    )
    
    for col in df.columns:
        df[col] = df[col].astype(str)
    
    df.columns = df.columns.str.replace('\n', ' ', regex=False)
    df.columns = df.columns.str.replace('\r', '', regex=False)
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace(r'  +', ' ', regex=True)
    
    cols_a_garder = []
    for col in df.columns:
        if col == '' or col.startswith('Unnamed'):
            continue
        if df[col].astype(str).str.strip().ne('').any():
            cols_a_garder.append(col)
    
    df = df[cols_a_garder]
    
    print(f"   ✅ {len(df)} lignes, {len(df.columns)} colonnes")
    
    return df


# ============================================================
# NOUVELLE FONCTION : GÉNÉRER PDF ALLURES
# ============================================================

def generer_pdf_allures():
    """
    Fonction pour l'option 4 du menu.
    Saisie utilisateur et génération d'un PDF avec les allures.
    """
    print("\n" + "="*60)
    print("🏃 CALCUL DES ALLURES VMA OU VC")
    print("="*60)
    print("\n📋 Cette option permet de générer un PDF personnalisé")
    print("   avec le tableau des intensités (effort/récupération)")
    print("   et les zones d'entraînement correspondantes.")
    print("="*60)

    nom = input("\n👉 Prénom/Nom de l'athlète : ").strip()
    if not nom:
        nom = "Athlète"
    
    nom_fichier = nom.replace(' ', '_')
    nom_fichier = nom_fichier.replace('\t', '_')
    nom_fichier = nom_fichier.replace('\n', '_')
    nom_fichier = nom_fichier.replace('\r', '_')
    nom_fichier = re.sub(r'[<>:"/\\|?*]', '_', nom_fichier)
    nom_fichier = re.sub(r'_+', '_', nom_fichier)

    genre = input("👉 Genre (M/F) : ").strip().upper()
    if genre not in ['M', 'F']:
        print("   ⚠️ Genre non reconnu. Utilisation de 'M' par défaut.")
        genre = 'M'

    print("\n   Vous devez saisir soit une VMA, soit une VC (ou les deux).")
    vma_input = input("👉 VMA (km/h) ou laisser vide : ").strip()
    vc_input = input("👉 VC (km/h) ou laisser vide : ").strip()

    vma = None
    vc = None
    vma_saisie = None  # Pour savoir ce qui a été saisi
    vc_saisie = None

    if vma_input:
        try:
            vma = float(vma_input.replace(',', '.'))
            vma_saisie = vma
            print(f"   ✅ VMA saisie : {vma} km/h")
        except ValueError:
            print("   ❌ Format de VMA invalide.")
            return

    if vc_input:
        try:
            vc = float(vc_input.replace(',', '.'))
            vc_saisie = vc
            print(f"   ✅ VC saisie : {vc} km/h")
        except ValueError:
            print("   ❌ Format de VC invalide.")
            return

    if vma is None and vc is None:
        print("   ❌ Aucune VMA ni VC saisie. Opération annulée.")
        return

    print("\n" + "="*60)
    print("   📊 Génération du PDF en cours...")
    print("="*60)

    # CORRIGÉ: Passer les valeurs SAISIES à PhysiologieSimple
    physio_simule = PhysiologieSimple(vma_saisie, vc_saisie, genre, nom)

    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import Paragraph, Spacer

    class DocTemp:
        pass
    doc = DocTemp()
    story = []
    
    styles = getSampleStyleSheet()
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=12)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']
    
    story.append(Paragraph(f"Tableau des allures pour : {nom}", titre_style))
    story.append(Spacer(1, 6))
    
    story.append(Paragraph(f"Genre : {genre}", normal_style))
    if vma_saisie:
        story.append(Paragraph(f"VMA : {vma_saisie:.1f} km/h", normal_style))
    if vc_saisie:
        story.append(Paragraph(f"VC : {vc_saisie:.1f} km/h", normal_style))
    story.append(Spacer(1, 10))
    
    ajouter_section_intensites(story, physio_simule, normal_style, sous_titre_style)
    
    if vma_saisie:
        generer_tableau_vma(story, physio_simule, normal_style, sous_titre_style)
    if vc_saisie:
        generer_tableau_vc(story, physio_simule, normal_style, sous_titre_style)
    
    doc.story = story
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = os.path.join('outputs', f'allures_{nom_fichier}_{timestamp}')
    
    os.makedirs('outputs', exist_ok=True)
    
    pdf_path = sauvegarder_pdf(doc, base_path)
    print(f"\n✅ PDF généré avec succès : {pdf_path}")
    print("="*60)


# ============================================================
# OPTION 1 : ANALYSER UN FICHIER
# ============================================================

def analyser_csv():
    """Analyse un fichier et génère les données pour chaque athlète."""
    print("\n" + "="*60)
    print("📊 AGENT D'ANALYSE - Génération des séances")
    print("="*60)
    print("\n📋 Fichiers supportés : .tsv (tabulations)")
    print("="*60)
    
    fichier = choisir_element(
        dossier='inputs',
        extensions=['.tsv'],
        titre="📁 FICHIERS TSV DISPONIBLES DANS inputs/"
    )
    
    if not fichier:
        print("❌ Analyse annulée.")
        return
    
    fichier_path = os.path.join('inputs', fichier)
    
    try:
        print(f"\n   📖 Lecture du fichier : {fichier}")
        df = lire_fichier_donnees(fichier_path)
        
        if df.empty:
            print(f"⚠️ Le fichier {fichier_path} est vide.")
            return
        
        print(f"\n✅ {len(df)} athlètes chargés depuis {fichier}")
        print("="*60)

        base_dir = 'outputs/Base par athlète'
        os.makedirs(base_dir, exist_ok=True)

        for index, row in df.iterrows():
            athlete = row.to_dict()
            
            athlete_clean = {}
            for k, v in athlete.items():
                key_clean = str(k).strip() if k is not None else ''
                val_clean = str(v).strip() if v is not None else ''
                athlete_clean[key_clean] = val_clean
            
            athlete = athlete_clean
            
            nom_brut = athlete.get('Prénom/Nom', '')
            if not nom_brut or nom_brut == '' or nom_brut == 'nan':
                nom_brut = f'Athlète {index+1}'
            nom_brut = nom_brut.strip()
            
            nom_fichier = nom_brut.replace(' ', '_').replace('/', '_')
            sexe = athlete.get('Sexe', 'M')
            if not sexe or sexe == '' or sexe == 'nan':
                sexe = 'M'
            sexe = sexe.upper().strip()

            print(f"\n--- {nom_brut} ---")

            try:
                physio = Physiologie(athlete)
            except Exception as e:
                print(f"   ❌ Erreur physiologie : {e}")
                import traceback
                traceback.print_exc()
                continue

            vma = physio.vma
            vc = physio.vc
            seances_vma = []
            seances_vc = []

            if vma and not math.isnan(vma):
                print(f"   VMA : {vma} km/h (origine : {physio.vma_origine})")
                seances_vma = generer_seances_vma(vma, sexe)
            else:
                print("   ⚠️ VMA non renseignée")

            if vc and not math.isnan(vc):
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

            profil = {
                "nom": nom_brut,
                "sexe": physio.genre,
                "age": physio.age,
                "taille_poids": athlete.get('Taille/Poids', ''),
                "metier_contraintes": athlete.get('Métier et ses contraintes', ''),
                "objectif_principal": athlete.get('Objectif principal', ''),
                "format_competition": athlete.get('Quel format de compétition ?', ''),
                "competition_objectif": athlete.get('Quelle est la compétition objectif ?', ''),
                "date_objectif": physio.date_objectif,
                "courses_preparatoires": physio.courses_preparatoires,
                "niveau_estime": "Intermédiaire",
                "physiologie": {
                    "vma": physio.vma,
                    "vma_origine": physio.vma_origine,
                    "vc": physio.vc,
                    "vc_origine": physio.vc_origine,
                    "test_vc_3_6_12": physio.test_vc_3_6_12,
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
        import traceback
        traceback.print_exc()


# ============================================================
# OPTION 2 : PLANIFIER
# ============================================================

def planifier():
    print("\n" + "="*60)
    print("📅 PLANIFICATEUR D'ENTRAÎNEMENT")
    print("="*60)
    
    noms = choisir_athletes()
    if not noms:
        print("❌ Planification annulée.")
        return
    
    date_debut = input("📅 Date de début (YYYY-MM-DD) ou laisser vide pour aujourd'hui : ").strip()
    if not date_debut:
        date_debut = None
    
    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        if not os.path.exists(athlete_dir):
            print(f"❌ Athlète {nom} non trouvé")
            continue
        
        plan = planifier_athlete(athlete_dir, date_debut)
        if "error" in plan:
            print(f"❌ {plan['error']}")
            continue
        
        print(f"\n📅 Plan pour {plan['athlete']}")
        print(f"   Du {plan['date_debut']} au {plan['date_objectif']}")
        print(f"   {plan['nb_semaines']} semaines")
        print("="*60)


# ============================================================
# OPTION 3 : MISE À JOUR
# ============================================================

def mise_a_jour_intensites():
    print("\n" + "="*60)
    print("🔄 MISE À JOUR DES INTENSITÉS")
    print("="*60)
    
    noms = choisir_athletes()
    if not noms:
        print("❌ Mise à jour annulée.")
        return
    
    nouvelle_vma = input("Nouvelle VMA (km/h) ou laisser vide : ").strip()
    nouvelle_vma = float(nouvelle_vma) if nouvelle_vma else None
    
    nouvelle_vc = input("Nouvelle VC (km/h) ou laisser vide : ").strip()
    nouvelle_vc = float(nouvelle_vc) if nouvelle_vc else None
    
    if not nouvelle_vma and not nouvelle_vc:
        print("❌ Aucune nouvelle valeur saisie.")
        return
    
    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        if not os.path.exists(athlete_dir):
            print(f"❌ Athlète {nom} non trouvé")
            continue
        maj_intensites(athlete_dir, nouvelle_vma, nouvelle_vc)


# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu():
    print("\n" + "="*60)
    print("🏊‍♂️ DEEPSEEK ATHLETE - OUTIL D'ENTRAÎNEMENT")
    print("="*60)
    print("1. 📊 Analyser un fichier (TSV)")
    print("2. 📅 Planifier un entraînement (planificateur)")
    print("3. 🔄 Mettre à jour les intensités (post-tests)")
    print("4. 🏃 Calculer et afficher les allures VMA ou VC")
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
        elif choix == '4':
            generer_pdf_allures()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '9':
            print("\n👋 Au revoir !")
            break
        else:
            print("\n❌ Option invalide. Arrêt du programme.")
            break


if __name__ == '__main__':
    main()