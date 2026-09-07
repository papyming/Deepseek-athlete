# ============================================================
# FICHIER: src/main.py
# RÔLE: Point d'entrée principal de l'application
#       CORRIGÉ: Sauvegarde correcte de VMA/VC et origines
# ============================================================

import os
import sys
import pandas as pd
import math
import re
from datetime import datetime, timedelta

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
from planificateur.plan_intervals import IntervalsPlanManager
from planificateur.export_csv import exporter_plan_csv
from planificateur.export_pdf_plan import exporter_pdf_plan
from liste import choisir_athletes, choisir_element


# ============================================================
# FONCTIONS DE LECTURE
# ============================================================

def detecter_encodage(fichier_path: str) -> str:
    """Détecte l'encodage d'un fichier."""
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
    """
    Lit un fichier TSV en forçant TOUTES les colonnes en chaîne.
    """
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
# OPTION 1 : ANALYSER UN FICHIER (TSV)
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

            # CORRIGÉ: Sauvegarder correctement VMA/VC et leurs origines
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
                    # CORRIGÉ: VMA déclarée (None si non déclarée)
                    "vma": physio.vma,
                    "vma_origine": physio.vma_origine if physio.vma is not None else None,
                    # CORRIGÉ: VMA estimée depuis les performances (indépendante)
                    "vma_estimee": physio.vma_estimee,
                    # CORRIGÉ: VC déclarée ou calculée (None si non disponible)
                    "vc": physio.vc,
                    "vc_origine": physio.vc_origine if physio.vc is not None else None,
                    # CORRIGÉ: VC estimée depuis les performances (indépendante)
                    "vc_estimee": physio.vc_estimee,
                    "test_vc_3_6_12": physio.test_vc_3_6_12,
                    "ftp": physio.ftp,
                    "ftp_origine": physio.ftp_origine,
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
# OPTION 2 : PLANIFIER (PDF + CSV)
# ============================================================

def planifier():
    """
    Option 2 : Planification complète
    - Génère le plan (PDF + CSV)
    - Sans export Intervals (fait via Option 5)
    """
    print("\n" + "="*60)
    print("📅 PLANIFICATION (PDF + CSV)")
    print("="*60)
    print("\n📋 Cette option génère :")
    print("   1. Un PDF du plan d'entraînement")
    print("   2. Un CSV exportable vers Intervals.ICU")
    print("   3. L'export vers Intervals se fait via l'Option 5 après validation")
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

        print(f"\n👤 Athlète : {nom}")

        # Générer le plan
        print("   📊 Génération du plan...")
        plan = planifier_athlete(athlete_dir, date_debut)

        if "error" in plan:
            print(f"❌ {plan['error']}")
            continue

        plan_dir = os.path.join('outputs', 'plans', nom.replace(' ', '_'))
        os.makedirs(plan_dir, exist_ok=True)

        # 1. Exporter le CSV
        print("   📄 Export du CSV...")
        csv_path = exporter_plan_csv(plan, plan_dir)
        print(f"      ✅ {os.path.basename(csv_path)}")

        # 2. Exporter le PDF
        print("   📄 Export du PDF...")
        pdf_path = exporter_pdf_plan(plan, plan_dir)
        print(f"      ✅ {os.path.basename(pdf_path)}")

        print(f"\n✅ Plan généré pour {nom}")
        print(f"   📁 Dossier : {plan_dir}")
        print(f"   📄 CSV : {os.path.basename(csv_path)}")
        print(f"   📄 PDF : {os.path.basename(pdf_path)}")
        print("\n⚠️  Export Intervals non effectué. Vérifiez le plan CSV puis utilisez l'Option 5.")

    input("\nAppuyez sur Entrée pour continuer...")


# ============================================================
# OPTION 3 : METTRE À JOUR LE PLAN DEPUIS INTERVALS.ICU
# ============================================================

def mettre_a_jour_plan():
    """
    Option 3 : Mise à jour du plan depuis Intervals.ICU
    """
    print("\n" + "="*60)
    print("🔄 MISE À JOUR DU PLAN DEPUIS INTERVALS.ICU")
    print("="*60)
    print("\n📋 Cette option permet de :")
    print("   1. Récupérer les retours de l'athlète (RPE, commentaires)")
    print("   2. Analyser la fatigue (TSB)")
    print("   3. Ajuster automatiquement le plan")
    print("   4. Exporter PDF + CSV mis à jour")
    print("="*60)

    noms = choisir_athletes()
    if not noms:
        print("❌ Mise à jour annulée.")
        return

    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        if not os.path.exists(athlete_dir):
            print(f"❌ Athlète {nom} non trouvé")
            continue

        print(f"\n👤 Athlète : {nom}")

        # Récupérer la configuration Intervals
        print("\n🔑 Configuration Intervals.ICU")
        api_key = input("   Clé API : ").strip()
        if not api_key:
            api_key = os.getenv('INTERVALS_API_KEY', '')
            if api_key:
                print("   → Clé API trouvée dans .env")

        athlete_id = input("   ID Athlète : ").strip()
        if not athlete_id:
            athlete_id = os.getenv('INTERVALS_ATHLETE_ID', '')
            if athlete_id:
                print("   → ID Athlète trouvé dans .env")

        if not api_key or not athlete_id:
            print("   ❌ Clé API ou ID Athlète manquant. Impossible de continuer.")
            continue

        # Période de récupération des retours
        print("\n📅 Période de récupération des retours")
        print("   (Laissez vide pour les 14 derniers jours)")
        start_date = input("   Date de début (YYYY-MM-DD) : ").strip()
        if not start_date:
            start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
            print(f"   → {start_date}")

        end_date = input("   Date de fin (YYYY-MM-DD) : ").strip()
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            print(f"   → {end_date}")

        # Générer le plan de base
        print("\n   📊 Génération du plan de base...")
        plan = planifier_athlete(athlete_dir, None)

        if "error" in plan:
            print(f"❌ {plan['error']}")
            continue

        plan_dir = os.path.join('outputs', 'plans', nom.replace(' ', '_'))
        os.makedirs(plan_dir, exist_ok=True)

        # Cycle complet Intervals
        print("\n   🔗 Connexion à Intervals.ICU...")
        try:
            manager = IntervalsPlanManager(api_key, athlete_id)

            # Récupérer les retours
            print("   📥 Récupération des retours...")
            retours = manager.recuperer_retours(start_date, end_date)

            if not retours.get('retours'):
                print("   ⚠️ Aucun retour trouvé sur la période")
                print("   📄 Génération du plan de base uniquement")
                csv_path = exporter_plan_csv(plan, plan_dir)
                pdf_path = exporter_pdf_plan(plan, plan_dir)
                print(f"   ✅ Plan de base : {os.path.basename(csv_path)}")
                continue

            print(f"   ✅ {len(retours.get('retours', []))} retours récupérés")

            # Ajuster le plan
            print("   🔄 Ajustement du plan...")
            ajustements = manager.ajuster_plan_depuis_retours(plan, retours)

            print(f"   🔧 {ajustements.get('modifications', 0)} séances ajustées")
            print(f"   📊 TSB = {ajustements.get('tsb', 0):.1f}")
            print(f"   📝 {ajustements.get('message', '')}")

            # Exporter le CSV ajusté
            print("   📄 Export du CSV ajusté...")
            csv_path = exporter_plan_csv(plan, plan_dir)
            print(f"      ✅ {os.path.basename(csv_path)}")

            # Exporter le PDF ajusté
            print("   📄 Export du PDF ajusté...")
            pdf_path = manager.exporter_pdf_plan_ajuste(plan, plan_dir, ajustements)
            if pdf_path:
                print(f"      ✅ {os.path.basename(pdf_path)}")

        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            import traceback
            traceback.print_exc()
            continue

        print(f"\n✅ Mise à jour terminée pour {nom}")
        print(f"   📁 Dossier : {plan_dir}")

    input("\nAppuyez sur Entrée pour continuer...")


# ============================================================
# OPTION 5 : EXPORTER UN PLAN CSV VERS INTERVALS.ICU
# ============================================================

def exporter_csv_vers_intervals():
    """
    Option 5 : Exporter un plan CSV validé vers Intervals.ICU
    """
    print("\n" + "="*60)
    print("📤 EXPORT VERS INTERVALS.ICU")
    print("="*60)
    print("\n📋 Cette option permet d'exporter un plan CSV validé")
    print("   vers Intervals.ICU après vérification du plan.")
    print("="*60)

    # Lister les CSV de plans
    plan_dir = 'outputs/plans'
    if not os.path.exists(plan_dir):
        print("❌ Aucun plan trouvé. Générez un plan d'abord (Option 2).")
        return
    
    plans = []
    for root, dirs, files in os.walk(plan_dir):
        for f in files:
            if 'plan_' in f and f.endswith('.csv'):
                nom = os.path.basename(root)
                plans.append({'nom': nom, 'fichier': f, 'chemin': os.path.join(root, f)})
    
    if not plans:
        print("❌ Aucun plan CSV trouvé.")
        return
    
    print("\n📋 PLANS DISPONIBLES :")
    for i, p in enumerate(plans):
        print(f"   {i+1}. {p['nom']} - {p['fichier']}")
    
    choix = input("\n👉 Sélectionnez un plan (numéro) : ").strip()
    if not choix.isdigit():
        print("❌ Sélection invalide.")
        return
    
    idx = int(choix) - 1
    if idx < 0 or idx >= len(plans):
        print("❌ Sélection invalide.")
        return
    
    plan_selectionne = plans[idx]
    
    # Demander les identifiants Intervals
    print("\n🔑 Configuration Intervals.ICU")
    api_key = input("   Clé API : ").strip()
    if not api_key:
        api_key = os.getenv('INTERVALS_API_KEY', '')
        if api_key:
            print("   → Clé API trouvée dans .env")
    
    athlete_id = input("   ID Athlète : ").strip()
    if not athlete_id:
        athlete_id = os.getenv('INTERVALS_ATHLETE_ID', '')
        if athlete_id:
            print("   → ID Athlète trouvé dans .env")
    
    if not api_key or not athlete_id:
        print("❌ Clé API ou ID Athlète manquant.")
        return
    
    try:
        from planificateur.plan_intervals import IntervalsPlanManager
        manager = IntervalsPlanManager(api_key, athlete_id)
        
        # Lire le CSV validé
        df = pd.read_csv(plan_selectionne['chemin'], sep=';', encoding='utf-8-sig')
        
        # Construire un plan minimal
        plan_minimal = {
            'athlete': plan_selectionne['nom'],
            'semaines': [],
            'date_debut': df['Date'].iloc[0] if not df.empty else ''
        }
        
        # Upload vers Intervals
        print(f"\n   📤 Export vers Intervals.ICU pour {plan_selectionne['nom']}...")
        resultat = manager.exporter_plan_de_base(plan_minimal, os.path.dirname(plan_selectionne['chemin']))
        
        print(f"\n✅ Plan exporté vers Intervals.ICU")
        print(f"   📤 {resultat.get('intervals_result', {}).get('evenements_crees', 0)} événements créés")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# OPTION 8 : CALCULER LES ALLURES VMA/VC
# ============================================================

def generer_pdf_allures():
    """
    Option 8 : Calcul des allures VMA/VC
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
    vma_saisie = None
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
# MENU PRINCIPAL
# ============================================================

def menu():
    """Affiche le menu principal."""
    print("\n" + "="*60)
    print("🏊‍♂️ DEEPSEEK ATHLETE - OUTIL D'ENTRAÎNEMENT")
    print("="*60)
    print("1. 📊 Analyser un fichier (TSV)")
    print("2. 📅 Planifier un entraînement (PDF + CSV)")
    print("3. 🔄 Mettre à jour le plan depuis Intervals.ICU (PDF + CSV)")
    print("5. 📤 Exporter un plan CSV vers Intervals.ICU")
    print("8. 🏃 Calculer et afficher les allures VMA ou VC")
    print("9. 🚪 Quitter")
    print("="*60)


def main():
    """Fonction principale."""
    os.makedirs('inputs', exist_ok=True)
    os.makedirs('outputs/Base par athlète', exist_ok=True)
    os.makedirs('outputs/plans', exist_ok=True)

    while True:
        menu()
        choix = input("\nVotre choix : ").strip()

        if choix == '':
            print("\n👋 Au revoir !")
            break

        if choix == '1':
            analyser_csv()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '2':
            planifier()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '3':
            mettre_a_jour_plan()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '5':
            exporter_csv_vers_intervals()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '8':
            generer_pdf_allures()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '9':
            print("\n👋 Au revoir !")
            break
        else:
            print("\n❌ Option invalide. Tapez 1, 2, 3, 5, 8 ou 9.")
            continue


if __name__ == '__main__':
    main()