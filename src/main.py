# ============================================================
# FICHIER: src/main.py
# RÔLE: Point d'entrée principal de l'application
#       CORRIGÉ: Extraction du sport principal
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
from utils.parsers import parser_bi_quotidien, est_reponse_tri_quadri, selectionner_jours_tri_quadri, parser_date_debut
from utils.validators import analyser_jours_disponibles, valider_coherence_biquotidien
from export.sov import sauvegarder_json, sauvegarder_csv, sauvegarder_pdf
from export import generer_pdf_athlete
from export.sections_pdf import ajouter_section_intensites
from export.tables_pdf import generer_tableau_vma, generer_tableau_vc
from planificateur import (
    planifier_athlete,
    generer_csv_athlete,
    valider_plan_athlete,
    exporter_plan_athlete,
)
from planificateur.plan_intervals import IntervalsPlanManager
from planificateur.export_csv import exporter_plan_csv
from planificateur.export_pdf_plan import exporter_pdf_plan
from planificateur.chargeur import charger_profil, charger_disponibilites
from planificateur.plan_csv import (
    trouver_csv_courant,
    construire_plan_depuis_csv,
    lister_csv_plans,
    resoudre_selection,
)
from planificateur.validateur_plan import valider_plan_csv
from stockage import get_plan_repository
from liste import choisir_athletes, choisir_element


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
# OPTION 1 : ANALYSER UN FICHIER (TSV)
# ============================================================

def analyser_csv():
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

            # CORRIGÉ: Extraire le sport principal
            sport_principal = athlete.get("Quel sport est l'objectif principal de ce plan ?", '')
            if not sport_principal or sport_principal == '' or sport_principal == 'nan':
                sport_principal = 'Triathlon'  # Valeur par défaut
            sport_principal = sport_principal.strip()

            print(f"\n--- {nom_brut} ---")
            print(f"   🏆 Sport principal : {sport_principal}")

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
            capacite_bi_brute = athlete.get('Possibilité de faire du bi-quotidien ? voire Tri ou quadri ?', '')
            mode_bi = 'tri_quadri' if est_reponse_tri_quadri(capacite_bi_brute) else 'standard'
            if mode_bi == 'tri_quadri':
                bi_source = jours_dispos.get('bi_quotidien', {})
                bi_selectionne = selectionner_jours_tri_quadri(bi_source)
                nb_bi = len({
                    jour
                    for jours_discipline in bi_selectionne.values()
                    for jour in jours_discipline
                })
                if not nb_bi:
                    nb_bi = None
                jours_dispos['bi_quotidien_source'] = bi_source
                jours_dispos['bi_quotidien_tri_quadri'] = bi_selectionne
                jours_dispos['bi_quotidien_selectionne'] = bool(nb_bi)
            else:
                nb_bi = parser_bi_quotidien(capacite_bi_brute)
                jours_dispos['bi_quotidien_selectionne'] = None
            jours_dispos['bi_quotidien_nb'] = nb_bi
            jours_dispos['bi_quotidien_renseigne'] = nb_bi is not None
            jours_dispos['bi_quotidien_capacite_brute'] = capacite_bi_brute
            jours_dispos['bi_quotidien_mode'] = mode_bi
            jours_dispos['bi_quotidien_validation'] = valider_coherence_biquotidien(
                jours_dispos, nom_brut, capacite_bi_brute
            )
            if not jours_dispos['bi_quotidien_validation']['valide']:
                physio.alertes_profil.append(jours_dispos['bi_quotidien_validation']['message'])

            athlete_dir = os.path.join(base_dir, nom_fichier)
            os.makedirs(athlete_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # CORRIGÉ: Sauvegarder le sport principal
            profil = {
                "nom": nom_brut,
                "sexe": physio.genre,
                "age": physio.age,
                "taille_poids": athlete.get('Taille/Poids', ''),
                "metier_contraintes": athlete.get('Métier et ses contraintes', ''),
                "objectif_principal": athlete.get('Objectif principal', ''),
                "format_competition": athlete.get('Quel format de compétition ?', ''),
                "competition_objectif": athlete.get('Quelle est la compétition objectif ?', ''),
                "sport_principal": sport_principal,
                "date_objectif": physio.date_objectif,
                "courses_preparatoires": physio.courses_preparatoires,
                "niveau_estime": "Intermédiaire",
                "physiologie": {
                    "vma": physio.vma,
                    "vma_origine": physio.vma_origine if physio.vma is not None else None,
                    "vma_estimee": physio.vma_estimee,
                    "vc": physio.vc,
                    "vc_origine": physio.vc_origine if physio.vc is not None else None,
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
                "bi_quotidien_renseigne": nb_bi is not None,
                "bi_quotidien_capacite_brute": capacite_bi_brute,
                "bi_quotidien_mode": mode_bi,
                "bi_quotidien_validation": jours_dispos['bi_quotidien_validation'],
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
    print("\n" + "="*60)
    print("📅 PLANIFICATION (PDF + CSV)")
    print("="*60)

    noms = choisir_athletes()
    if not noms:
        print("❌ Planification annulée.")
        return

    saisie_date = input("📅 Date de début (JJ/MM/AAAA) ou laisser vide pour aujourd'hui : ").strip()
    try:
        date_debut_obj = parser_date_debut(saisie_date)
    except ValueError as erreur:
        print(f"   ❌ {erreur}")
        print("   Planification annulée.")
        return
    date_debut = date_debut_obj.strftime('%Y-%m-%d') if date_debut_obj else None

    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        if not os.path.exists(athlete_dir):
            print(f"❌ Athlète {nom} non trouvé")
            continue

        print(f"\n👤 Athlète : {nom}")

        print("   📊 Génération du plan...")
        plan = planifier_athlete(athlete_dir, date_debut)

        if "error" in plan:
            print(f"❌ {plan['error']}")
            continue

        print(f"\n✅ Plan généré pour {nom}")

    input("\nAppuyez sur Entrée pour continuer...")


# ============================================================
# OPTION 6 : METTRE À JOUR LE PLAN DEPUIS INTERVALS.ICU
#   Intervals.ICU -> CSV courant -> validation -> CSV courant
#   (distinct de l'option 5 qui fait CSV -> PDF + Intervals)
# ============================================================

def mettre_a_jour_plan():
    print("\n" + "="*60)
    print("6. METTRE À JOUR LE PLAN DEPUIS INTERVALS.ICU")
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

        profil = charger_profil(athlete_dir)
        disponibilites = charger_disponibilites(athlete_dir)
        plan_dir = get_plan_repository().dossier_plan(nom)
        chemin_csv = trouver_csv_courant(plan_dir)
        if not chemin_csv:
            print("   ❌ Aucun CSV courant. Générez d'abord le plan (option 2).")
            continue

        api_key = input("   Clé API : ").strip()
        if not api_key:
            api_key = os.getenv('INTERVALS_API_KEY', '')

        athlete_id = input("   ID Athlète : ").strip()
        if not athlete_id:
            athlete_id = os.getenv('INTERVALS_ATHLETE_ID', '')

        if not api_key or not athlete_id:
            print("   ❌ Clé API ou ID Athlète manquant.")
            continue

        start_date = input("   Date de début (YYYY-MM-DD) : ").strip()
        if not start_date:
            start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

        end_date = input("   Date de fin (YYYY-MM-DD) : ").strip()
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # Le CSV courant est la source : on ne régénère pas le plan.
        plan = construire_plan_depuis_csv(chemin_csv, athlete=nom)

        try:
            manager = IntervalsPlanManager(api_key, athlete_id)
            retours = manager.recuperer_retours(start_date, end_date)

            if not retours.get('retours'):
                print("   ⚠️ Aucun retour trouvé")
                continue

            ajustements = manager.ajuster_plan_depuis_retours(plan, retours)
            print(f"   🔧 {ajustements.get('modifications', 0)} séances ajustées")

            chemin_propose = exporter_plan_csv(plan, plan_dir)
            validation = valider_plan_csv(chemin_propose, disponibilites)
            if not validation['valide']:
                print("   ❌ CSV mis à jour invalide : il n'est pas retenu.")
                for erreur in validation['erreurs']:
                    print(f"      - {erreur}")
                try:
                    os.remove(chemin_propose)
                except OSError:
                    pass
                continue

            print(f"   ✅ CSV courant mis à jour depuis Intervals.ICU : "
                  f"{chemin_propose}")

        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            continue

    input("\nAppuyez sur Entrée pour continuer...")


# ============================================================
# RÉTROCOMPATIBILITÉ (hors menu) :
# export direct d'un CSV vers Intervals.ICU.
# N'est plus proposé comme option : l'option 5 couvre l'export.
# ============================================================

def exporter_csv_vers_intervals():
    print("\n" + "="*60)
    print("📤 EXPORT VERS INTERVALS.ICU")
    print("="*60)

    plans = [
        {'nom': entree['athlete'], 'fichier': entree['fichier'],
         'chemin': entree['chemin']}
        for entree in lister_csv_plans()
    ]
    if not plans:
        print("❌ Aucun plan CSV trouvé.")
        return

    for i, p in enumerate(plans):
        print(f"   {i+1}. {p['nom']} - {p['fichier']}")

    choix = input("\n👉 Sélectionnez un plan (numéro) : ").strip()
    if not choix.isdigit():
        return

    idx = int(choix) - 1
    if idx < 0 or idx >= len(plans):
        return

    plan_selectionne = plans[idx]

    api_key = input("   Clé API : ").strip() or os.getenv('INTERVALS_API_KEY', '')
    athlete_id = input("   ID Athlète : ").strip() or os.getenv('INTERVALS_ATHLETE_ID', '')

    if not api_key or not athlete_id:
        print("❌ Clé API ou ID Athlète manquant.")
        return

    try:
        from planificateur.plan_intervals import IntervalsPlanManager
        manager = IntervalsPlanManager(api_key, athlete_id)

        df = get_plan_repository().lire_plan(plan_selectionne['chemin'])
        plan_minimal = {
            'athlete': plan_selectionne['nom'],
            'semaines': [],
            'date_debut': df['Date'].iloc[0] if not df.empty else ''
        }

        resultat = manager.exporter_plan_de_base(plan_minimal, os.path.dirname(plan_selectionne['chemin']))
        print(f"\n✅ Plan exporté vers Intervals.ICU")

    except Exception as e:
        print(f"❌ Erreur : {e}")


# ============================================================
# OPTION 8 : CALCULER LES ALLURES VMA/VC
# ============================================================

def generer_pdf_allures():
    print("\n" + "="*60)
    print("🏃 CALCUL DES ALLURES VMA OU VC")
    print("="*60)

    nom = input("\n👉 Prénom/Nom de l'athlète : ").strip() or "Athlète"
    nom_fichier = re.sub(r'[<>:"/\\|?*\t\n\r]', '_', nom)
    nom_fichier = re.sub(r'_+', '_', nom_fichier)

    genre = input("👉 Genre (M/F) : ").strip().upper()
    if genre not in ['M', 'F']:
        genre = 'M'

    vma_input = input("👉 VMA (km/h) ou laisser vide : ").strip()
    vc_input = input("👉 VC (km/h) ou laisser vide : ").strip()

    vma_saisie = None
    vc_saisie = None

    if vma_input:
        try:
            vma_saisie = float(vma_input.replace(',', '.'))
        except ValueError:
            print("   ❌ Format VMA invalide.")
            return

    if vc_input:
        try:
            vc_saisie = float(vc_input.replace(',', '.'))
        except ValueError:
            print("   ❌ Format VC invalide.")
            return

    if vma_saisie is None and vc_saisie is None:
        print("   ❌ Aucune VMA ni VC saisie.")
        return

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


# ============================================================
# CHAÎNE CSV MAÎTRE : génération / validation / exports
# ============================================================

def _saisir_date_debut():
    saisie = input("📅 Date de début (JJ/MM/AAAA) ou laisser vide pour aujourd'hui : ").strip()
    try:
        date_debut_obj = parser_date_debut(saisie)
    except ValueError as erreur:
        print(f"   ❌ {erreur}")
        return None
    return date_debut_obj.strftime('%Y-%m-%d') if date_debut_obj else None


def generer_plan_csv():
    """Option 2 : le moteur fabrique (ou recrée) le CSV proposé."""
    print("\n" + "="*60)
    print("2. GÉNÉRER / RECRÉER LE PLAN CSV")
    print("="*60)
    noms = choisir_athletes()
    if not noms:
        print("❌ Opération annulée.")
        return
    date_debut = _saisir_date_debut()

    def confirmer(chemin_csv):
        reponse = input(
            f"   ⚠️ Un CSV courant existe déjà ({os.path.basename(chemin_csv)}).\n"
            "   Le régénérer écrasera d'éventuelles modifications manuelles.\n"
            "   Continuer ? (o/N) : "
        ).strip().lower()
        return reponse in ('o', 'oui', 'y', 'yes')

    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        if not os.path.exists(athlete_dir):
            print(f"❌ Athlète {nom} non trouvé")
            continue
        print(f"\n👤 Athlète : {nom}")
        resultat = generer_csv_athlete(athlete_dir, date_debut, confirmation=confirmer)
        if 'error' in resultat:
            print(f"❌ {resultat['error']}")
            continue
        if resultat.get('annule'):
            print("   Annulé : le CSV courant est conservé.")
            continue
        print(f"✅ CSV proposé enregistré : {resultat.get('chemin_csv')}")


def modifier_plan_csv_agent():
    """Option 3 : modification du CSV par l'agent IA (interface préparée)."""
    print("\n" + "="*60)
    print("3. MODIFIER LE PLAN CSV AVEC L'AGENT IA")
    print("="*60)
    print("🤖 La connexion à un agent IA n'est pas encore activée.")
    print("   L'architecture est prête :")
    print("     - planificateur.agent_plan_csv.FournisseurModifications (contrat)")
    print("     - planificateur.agent_plan_csv.appliquer_modifications_csv (déterministe + validation)")
    print("   Aucun plan ne sera régénéré : seule une liste de modifications du CSV")
    print("   sera appliquée puis validée.")


def valider_csv_plan():
    """Option 4 : validation déterministe des CSV sélectionnés (contrôle seul).

    La sélection porte sur les CSV réellement présents dans outputs/plans/.
    Aucune écriture, aucun PDF, aucun fichier Intervals.ICU.
    """
    print("\n" + "="*60)
    print("4. VALIDER LE CSV")
    print("="*60)

    plans = lister_csv_plans()
    if not plans:
        print("❌ Aucun plan CSV disponible dans outputs/plans/.")
        return

    print("\n" + "="*60)
    print("📋 LISTE DES PLANS CSV DISPONIBLES")
    print("="*60)
    for index, entree in enumerate(plans, start=1):
        print(f"{index:4d}. {entree['athlete']} — {entree['fichier']}")
    print("="*60)
    print("   Pour sélectionner plusieurs : 1,3,5")
    print("   Pour sélectionner une plage : 1-5")
    print("   Pour sélectionner tous : *")
    print("="*60)

    saisie = input("\n👉 Sélection : ").strip()
    indices = resoudre_selection(saisie, len(plans))
    if not indices:
        print("❌ Aucune sélection valide.")
        return

    for index in indices:
        entree = plans[index]
        disponibilites = None
        athlete_dir = os.path.join('outputs/Base par athlète', entree['athlete'])
        if os.path.isdir(athlete_dir):
            disponibilites = charger_disponibilites(athlete_dir)
        validation = valider_plan_csv(entree['chemin'], disponibilites)

        print(f"\n👤 {entree['athlete']}")
        print(f"📄 {entree['fichier']}")
        if validation.get('valide'):
            print("✅ VALIDÉ")
        else:
            print("❌ NON VALIDÉ")
            for erreur in validation.get('erreurs', []):
                print(f"   - ERREUR : {erreur}")
        for avertissement in validation.get('avertissements', []):
            print(f"   - AVERTISSEMENT : {avertissement}")


def exporter_pdf_intervals_csv():
    """Option 5 : PDF + Intervals.ICU à partir du CSV courant (avec re-validation)."""
    print("\n" + "="*60)
    print("5. GÉNÉRER PDF + INTERVALS.ICU DEPUIS LE CSV")
    print("="*60)
    noms = choisir_athletes()
    if not noms:
        print("❌ Opération annulée.")
        return
    for nom in noms:
        athlete_dir = os.path.join('outputs/Base par athlète', nom)
        resultat = exporter_plan_athlete(athlete_dir)
        if not resultat.get('valide'):
            print(f"\n👤 {nom} : ❌ CSV non valide, aucun export.")
            for erreur in resultat.get('validation', {}).get('erreurs', []):
                print(f"   - {erreur}")
            continue
        print(f"\n👤 {nom} : ✅ exports générés depuis {resultat.get('chemin_csv')}")
        print(f"   PDF       : {resultat.get('pdf')}")
        print(f"   Intervals : {resultat.get('intervals')}")


# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu():
    print("\n" + "="*60)
    print("🏊‍♂️ DEEPSEEK ATHLETE - OUTIL D'ENTRAÎNEMENT")
    print("="*60)
    print("1. 📊 Analyser un fichier (TSV)")
    print("2. 📅 Générer / recréer le plan CSV")
    print("3. 🤖 Modifier le plan CSV avec l'agent IA")
    print("4. ✅ Valider le CSV")
    print("5. 📄 Générer PDF + Intervals.ICU depuis le CSV")
    print("6. 🔄 Mettre à jour le plan depuis Intervals.ICU")
    print("7. 🏃 Calculer et afficher les allures VMA ou VC")
    print("8. 🚪 Quitter")
    print("="*60)


def main():
    os.makedirs('inputs', exist_ok=True)
    os.makedirs('outputs/Base par athlète', exist_ok=True)
    get_plan_repository().creer_stockage()

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
            generer_plan_csv()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '3':
            modifier_plan_csv_agent()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '4':
            valider_csv_plan()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '5':
            exporter_pdf_intervals_csv()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '6':
            mettre_a_jour_plan()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '7':
            generer_pdf_allures()
            input("\nAppuyez sur Entrée pour continuer...")
        elif choix == '8':
            print("\n👋 Au revoir !")
            break
        else:
            print("\n❌ Option invalide.")
            continue


if __name__ == '__main__':
    main()