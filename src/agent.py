import pandas as pd
import os
import json
import re
from datetime import datetime
from p_code_vma import generer_seances_vma
from p_code_vc import generer_seances_vc
from physiologie import Physiologie

# ============================================================
# 1. IMPORT POUR LE PDF
# ============================================================
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    PDF_DISPO = True
except ImportError:
    PDF_DISPO = False
    print("⚠️ ReportLab non installé. Installe-le avec : pip install reportlab")

# ============================================================
# 2. FONCTIONS DE PARSING ET VALIDATION
# ============================================================

def parser_bi_quotidien(valeur) -> int:
    """
    Convertit la réponse 'Possibilité de faire du bi-quotidien ?' en nombre de séances supplémentaires.
    Gère les valeurs float (NaN) et les chaînes vides.
    """
    # 🔥 Conversion en string si ce n'est pas déjà fait
    if valeur is None:
        return 0
    valeur = str(valeur).strip()
    if not valeur or valeur == '' or valeur == 'nan' or valeur == 'None':
        return 0
    
    valeur_lower = valeur.lower()
    
    if valeur_lower == 'non':
        return 0
    elif '1 fois' in valeur_lower:
        return 1
    elif '2 fois' in valeur_lower:
        return 2
    elif '3 fois' in valeur_lower:
        return 3
    elif 'tri' in valeur_lower or 'quadri' in valeur_lower:
        print("⚠️ Détection de 'tri/quadri' dans la réponse. Veuillez saisir le nombre de séances supplémentaires autorisées :")
        try:
            saisie = int(input("> "))
            return saisie
        except:
            print("⚠️ Saisie invalide. Valeur par défaut : 2")
            return 2
    elif valeur_lower == 'autre':
        print("⚠️ Réponse 'Autre' détectée. Veuillez saisir le nombre de séances supplémentaires autorisées :")
        try:
            saisie = int(input("> "))
            return saisie
        except:
            print("⚠️ Saisie invalide. Valeur par défaut : 1")
            return 1
    else:
        return 0


def parser_jours_disciplines(valeur) -> dict:
    """
    Parse la colonne 'Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)'
    Exemple : "Nat=Lundi,Mercredi Velo=Dimanche CAP=Mardi,Jeudi"
    Retourne : {'CAP': ['Mardi', 'Jeudi'], 'Velo': ['Dimanche'], 'Natation': ['Lundi', 'Mercredi']}
    Gère les valeurs float (NaN) et les chaînes vides.
    """
    resultat = {'CAP': [], 'Velo': [], 'Natation': []}
    
    # 🔥 Conversion en string si ce n'est pas déjà fait
    if valeur is None:
        return resultat
    valeur = str(valeur).strip()
    if not valeur or valeur == '' or valeur == 'nan' or valeur == 'None':
        return resultat
    
    parties = valeur.split()
    for partie in parties:
        if '=' not in partie:
            continue
        discipline, jours_str = partie.split('=', 1)
        discipline = discipline.strip().capitalize()
        jours = [j.strip().capitalize() for j in jours_str.split(',') if j.strip()]
        
        if discipline in ['Cap', 'Course', 'Running']:
            resultat['CAP'].extend(jours)
        elif discipline in ['Velo', 'Cyclisme', 'Bike']:
            resultat['Velo'].extend(jours)
        elif discipline in ['Nat', 'Natation', 'Swim']:
            resultat['Natation'].extend(jours)
    
    return resultat


def verifier_coherence(nb_str: str, liste_jours: list, discipline: str, erreurs: list, nom: str):
    """
    Vérifie que le nombre de jours déclaré correspond au nombre de jours listés.
    """
    if not nb_str or nb_str == '':
        nb = 0
    else:
        try:
            nb = int(nb_str)
        except:
            erreurs.append(f"{discipline} : nombre de jours non valide ('{nb_str}')")
            return
    
    nb_liste = len(liste_jours)
    
    if nb == 0 and nb_liste > 0:
        erreurs.append(f"{discipline} : {nb_liste} jours listés mais 0 déclaré")
    elif nb > 0 and nb_liste == 0:
        erreurs.append(f"{discipline} : {nb} jours déclarés mais aucun jour listé")
    elif nb > 0 and nb_liste > 0 and nb_liste != nb:
        erreurs.append(f"{discipline} : {nb_liste} jours listés mais {nb} déclarés")


def analyser_jours_disponibles(row: dict) -> dict:
    """
    Agrège toutes les informations de jours d'entraînement depuis le CSV.
    Vérifie la cohérence pour les 3 disciplines :
    - Nombre de jours déclaré = nombre de jours listés
    - Les jours bi-quotidiens sont dans les jours normaux
    """
    resultat = {
        'CAP': [],
        'Velo': [],
        'Natation': [],
        'bi_quotidien': {'CAP': [], 'Velo': [], 'Natation': []}
    }
    
    nom = row.get('Prénom/Nom', 'Athlète')
    erreurs = []
    
    # ----- CAP -----
    nb_cap_str = row.get('Nombre de jours de CAP par semaine', '')
    jours_cap = row.get('Quels jours ? (CAP)', '')
    # 🔥 Gestion des valeurs float/None pour les jours
    if jours_cap is None:
        jours_cap = ''
    liste_jours_cap = [j.strip().capitalize() for j in str(jours_cap).replace(';', ',').split(',') if j.strip()] if jours_cap else []
    resultat['CAP'] = liste_jours_cap
    verifier_coherence(nb_cap_str, liste_jours_cap, "CAP", erreurs, nom)
    
    # ----- Vélo -----
    nb_velo_str = row.get("Combien d'entrainement de vélo par semaine ?", '')
    jours_velo = row.get('Quels jours ? (Vélo)', '')
    if jours_velo is None:
        jours_velo = ''
    liste_jours_velo = [j.strip().capitalize() for j in str(jours_velo).replace(';', ',').split(',') if j.strip()] if jours_velo else []
    resultat['Velo'] = liste_jours_velo
    verifier_coherence(nb_velo_str, liste_jours_velo, "Vélo", erreurs, nom)
    
    # ----- Natation -----
    nb_nat_str = row.get("Combien d'entrainement Natation par semaine ?", '')
    jours_natation = row.get('Quels jours ? (Natation)', '')
    if jours_natation is None:
        jours_natation = ''
    liste_jours_nat = [j.strip().capitalize() for j in str(jours_natation).replace(';', ',').split(',') if j.strip()] if jours_natation else []
    resultat['Natation'] = liste_jours_nat
    verifier_coherence(nb_nat_str, liste_jours_nat, "Natation", erreurs, nom)
    
    # ----- Gestion des erreurs -----
    if erreurs:
        print(f"\n❌ ERREUR de cohérence pour {nom} :")
        for err in erreurs:
            print(f"   - {err}")
        print("   📌 Veuillez corriger le CSV (nombre de jours = nombre de jours listés)")
        raise ValueError(f"Incohérence dans les jours d'entraînement pour {nom}")
    
    # ----- Vérification bi-quotidien (sous-ensemble) -----
    bi_quotidien_str = row.get('Si oui quel(s) jour(s) ? (Bi-quotidien) et Quel(s) discipline(s)', '')
    if bi_quotidien_str and bi_quotidien_str != '':
        bi_parsed = parser_jours_disciplines(bi_quotidien_str)
        for discipline, jours in bi_parsed.items():
            if discipline in resultat['bi_quotidien']:
                jours_normaux = resultat.get(discipline, [])
                jours_valides = []
                jours_invalides = []
                
                for j in jours:
                    if j in jours_normaux:
                        jours_valides.append(j)
                    else:
                        jours_invalides.append(j)
                
                if jours_invalides:
                    print(f"❌ ERREUR pour {nom} : jours bi-quotidiens {discipline} non valides : {', '.join(jours_invalides)}")
                    print(f"   Ces jours ne sont pas dans les jours d'entraînement normaux : {', '.join(jours_normaux)}")
                    print(f"   Ils seront ignorés.")
                
                resultat['bi_quotidien'][discipline].extend(jours_valides)
    
    return resultat


# ============================================================
# 3. GÉNÉRATION DU PDF RÉSUMÉ
# ============================================================

def generer_pdf_athlete(nom: str, physio, jours_dispos: dict, nb_bi: int, seances_vma: list, seances_vc: list):
    """
    Génère un PDF récapitulatif pour un athlète.
    """
    if not PDF_DISPO:
        return
    
    pdf_path = f"outputs/plans/{nom}_resume.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Style personnalisé
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=12)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']
    
    # ---- TITRE ----
    story.append(Paragraph(f"Résumé Athlète : {nom}", titre_style))
    story.append(Spacer(1, 6))
    
    # ---- 1. DONNÉES PERSONNELLES ----
    story.append(Paragraph("1. Données personnelles", sous_titre_style))
    data = [
        ["Sexe", physio.genre],
        ["Âge", str(physio.age) if physio.age else "Non renseigné"],
        ["Taille/Poids", physio.data.get('Taille/Poids', 'Non renseigné')],
        ["Métier/Contraintes", physio.data.get('Métier et ses contraintes', 'Aucune')]
    ]
    table = Table(data, colWidths=[60*mm, 100*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    # ---- 2. PERFORMANCES ----
    story.append(Paragraph("2. Performances", sous_titre_style))
    perfs = [
        ["VMA", f"{physio.vma} km/h" if physio.vma else "Non renseignée"],
        ["Vitesse Critique", f"{physio.vc} km/h" if physio.vc else "Non renseignée"],
        ["FTP Vélo", f"{physio.ftp} W" if physio.ftp else "Non renseignée"],
        ["Temps 400m natation", physio._secondes_vers_temps(physio.temps_400m) if physio.temps_400m else "Non renseigné"],
        ["FC max CAP", f"{physio.fc_max_cap} bpm" if physio.fc_max_cap else "Non renseignée"],
        ["FC max Natation", f"{physio.fc_max_natation} bpm" if physio.fc_max_natation else "Non renseignée"],
        ["FC max Vélo", f"{physio.fc_max_velo} bpm" if physio.fc_max_velo else "Non renseignée"]
    ]
    table = Table(perfs, colWidths=[60*mm, 100*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    # ---- 3. JOURS D'ENTRAÎNEMENT ----
    story.append(Paragraph("3. Jours d'entraînement", sous_titre_style))
    jours_data = [
        ["Discipline", "Jours", "Bi-quotidien"],
        ["CAP", ", ".join(jours_dispos['CAP']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['CAP']) or "Non"],
        ["Vélo", ", ".join(jours_dispos['Velo']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['Velo']) or "Non"],
        ["Natation", ", ".join(jours_dispos['Natation']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['Natation']) or "Non"]
    ]
    table = Table(jours_data, colWidths=[50*mm, 60*mm, 60*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    # ---- 4. SÉANCES GÉNÉRÉES ----
    story.append(Paragraph("4. Séances générées", sous_titre_style))
    seances_data = [
        ["Type", "Nombre de séances"],
        ["VMA", str(len(seances_vma)) if seances_vma else "0"],
        ["VC", str(len(seances_vc)) if seances_vc else "0"]
    ]
    table = Table(seances_data, colWidths=[80*mm, 80*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    # ---- 5. ALERTES / MANQUES ----
    if physio.manques:
        story.append(Paragraph("5. Alertes / Données manquantes", sous_titre_style))
        for m in physio.manques:
            story.append(Paragraph(f"• {m['donnee']} : {m['statut']}", normal_style))
    else:
        story.append(Paragraph("5. ✅ Aucune donnée manquante", sous_titre_style))
    
    # ---- GÉNÉRATION DU PDF ----
    doc.build(story)
    print(f"   📄 PDF résumé généré : {pdf_path}")


# ============================================================
# 4. FONCTIONS DE SAUVEGARDE
# ============================================================

def sauvegarder_seances(seances, nom, type_seance):
    """Sauvegarde les séances en CSV"""
    if not seances:
        return seances
    
    df = pd.DataFrame(seances)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"outputs/plans/{nom}_{type_seance}_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';')
    print(f"   ✅ {len(seances)} séances {type_seance} sauvegardées dans {output_file}")
    return seances


# ============================================================
# 5. FONCTION PRINCIPALE
# ============================================================

def main():
    # 1. Lire le CSV
    input_path = 'inputs/athletes_complet.csv'
    if not os.path.exists(input_path):
        print(f"❌ Fichier {input_path} introuvable")
        print(f"   Chemin absolu attendu : {os.path.abspath(input_path)}")
        return
    
    df = pd.read_csv(input_path, encoding='utf-8-sig', delimiter=';')
    print(f"✅ {len(df)} athlètes chargés")
    
    # 2. Créer les dossiers de sortie
    os.makedirs('outputs/plans', exist_ok=True)
    os.makedirs('outputs/fichiers_fit', exist_ok=True)
    
    # 3. Traiter chaque athlète
    for index, row in df.iterrows():
        athlete = row.to_dict()
        nom = athlete.get('Prénom/Nom', 'Inconnu')
        sexe = athlete.get('Sexe', 'M').upper()
        
        print(f"\n--- {nom} ---")
        
        # 4. Parser et valider les jours
        try:
            nb_bi = parser_bi_quotidien(athlete.get('Possibilité de faire du bi-quotidien ? voire Tri ou quadri ?', ''))
            jours_dispos = analyser_jours_disponibles(athlete)
        except ValueError as e:
            print(f"   ⚠️ {e}")
            print("   ➡️ Cet athlète est ignoré.")
            continue
        
        print(f"   Bi-quotidien : {nb_bi} séances supplémentaires")
        print(f"   Jours CAP : {jours_dispos['CAP']}")
        print(f"   Jours Vélo : {jours_dispos['Velo']}")
        print(f"   Jours Natation : {jours_dispos['Natation']}")
        if any(jours_dispos['bi_quotidien'].values()):
            print(f"   Jours bi-quotidiens : {jours_dispos['bi_quotidien']}")
        
        # 5. Calculs physiologiques
        physio = Physiologie(athlete)
        vma = physio.vma
        vc = physio.vc
        seances_vma = []
        seances_vc = []
        
        if vma:
            print(f"   VMA : {vma} km/h")
            seances_vma = generer_seances_vma(vma, sexe)
            sauvegarder_seances(seances_vma, nom, "VMA")
        else:
            print("   ⚠️ VMA non renseignée")
        
        if vc:
            print(f"   VC : {vc} km/h")
            seances_vc = generer_seances_vc(vc, sexe)
            sauvegarder_seances(seances_vc, nom, "VC")
        else:
            print("   ⚠️ VC non renseignée")
        
        # 6. Sauvegarder les disponibilités en JSON
        disponibilites = {
            'nom': nom,
            'bi_quotidien_nb': nb_bi,
            'jours': jours_dispos
        }
        with open(f'outputs/plans/{nom}_disponibilites.json', 'w', encoding='utf-8') as f:
            json.dump(disponibilites, f, ensure_ascii=False, indent=2)
        
        # 7. Générer le PDF résumé
        generer_pdf_athlete(nom, physio, jours_dispos, nb_bi, seances_vma, seances_vc)
    
    print("\n🎉 Terminé !")


# ============================================================
# 6. POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    main()