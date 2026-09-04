# ============================================================
# FICHIER: src/export/sections_pdf.py
# RÔLE: Définit les sections du PDF
#       CORRIGÉ: Compatible avec Physiologie ET PhysiologieSimple
# ============================================================

import math
import re
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle


def clean_unicode(text):
    """Remplace les caractères Unicode problématiques."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '₂': '2', '₃': '3', '₄': '4', '₁': '1', '₀': '0',
        '²': '2', '³': '3', '·': '.', '–': '-', '—': '-',
        '’': "'", '‘': "'", '"': '"', '"': '"', '…': '...',
        '≤': '<=', '≥': '>=', '≠': '!=', '≈': '~', '±': '+/-',
        '×': 'x', '÷': '/', '✓': '[OK]', '✗': '[KO]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[\u200b\u200c\u200d\u2060\uFEFF]', '', text)
    return text


def get_style_wrapped(fontsize=7):
    return ParagraphStyle(
        'Wrapped',
        fontSize=fontsize,
        leading=fontsize + 2,
        wordWrap='CJK'
    )


def to_paragraph(text, style):
    """Convertit un texte en Paragraph de manière sécurisée."""
    if text is None:
        text = ""
    if not isinstance(text, str):
        text = str(text)
    return Paragraph(clean_unicode(text), style)


def ajouter_section_donnees_personnelles(story, physio, normal_style, sous_titre_style):
    """Ajoute la section des données personnelles."""
    story.append(Paragraph(clean_unicode("Données personnelles"), sous_titre_style))
    
    # CORRIGÉ: Récupérer les valeurs de manière sécurisée
    genre = str(physio.genre) if hasattr(physio, 'genre') and physio.genre else "Non renseigné"
    age = str(physio.age) if hasattr(physio, 'age') and physio.age else "Non renseigné"
    
    # Récupérer Taille/Poids
    taille_poids = "Non renseigné"
    if hasattr(physio, 'data') and physio.data:
        taille_poids = str(physio.data.get('Taille/Poids', 'Non renseigné'))
    
    # Récupérer Métier/Contraintes
    metier = "Aucune"
    if hasattr(physio, 'data') and physio.data:
        metier = str(physio.data.get('Métier et ses contraintes', 'Aucune'))
    
    data = [
        [to_paragraph("Sexe", normal_style), to_paragraph(genre, normal_style)],
        [to_paragraph("Âge", normal_style), to_paragraph(age, normal_style)],
        [to_paragraph("Taille/Poids", normal_style), to_paragraph(taille_poids, normal_style)],
        [to_paragraph("Métier/Contraintes", normal_style), to_paragraph(metier, normal_style)]
    ]
    table = Table(data, colWidths=[50*mm, 110*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def ajouter_section_objectif(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Objectif."""
    story.append(Paragraph(clean_unicode("Objectif"), sous_titre_style))
    
    objectif = "Non renseigné"
    competition = ""
    competition_objectif = ""
    date_objectif = ""
    
    if hasattr(physio, 'data') and physio.data:
        objectif = str(physio.data.get('Objectif principal', 'Non renseigné'))
        competition = str(physio.data.get('Quel format de compétition ?', ''))
        competition_objectif = str(physio.data.get('Quelle est la compétition objectif ?', ''))
        date_objectif = str(physio.data.get('date_objectif', ''))
    
    if competition_objectif and competition_objectif != '':
        if date_objectif and date_objectif != '':
            story.append(to_paragraph(f"Compétition : {competition_objectif} ({date_objectif})", normal_style))
        else:
            story.append(to_paragraph(f"Compétition : {competition_objectif}", normal_style))
    if competition and competition != '':
        story.append(to_paragraph(f"Format : {competition}", normal_style))
    story.append(to_paragraph(f"Objectif : {objectif}", normal_style))
    story.append(Spacer(1, 6))


def ajouter_section_courses_preparatoires(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Courses préparatoires."""
    courses = []
    if hasattr(physio, 'courses_preparatoires') and physio.courses_preparatoires:
        courses = physio.courses_preparatoires
    
    if not courses:
        return
    
    story.append(Paragraph(clean_unicode("Courses préparatoires"), sous_titre_style))
    for course in courses:
        story.append(to_paragraph(f"• {course}", normal_style))
    story.append(Spacer(1, 6))


def ajouter_section_performances(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Performances avec origine."""
    story.append(Paragraph(clean_unicode("Performances"), sous_titre_style))
    
    # Récupérer les valeurs de manière sécurisée
    vma = physio.vma if hasattr(physio, 'vma') and physio.vma and not math.isnan(physio.vma) else None
    vc = physio.vc if hasattr(physio, 'vc') and physio.vc and not math.isnan(physio.vc) else None
    ftp = physio.ftp if hasattr(physio, 'ftp') and physio.ftp else None
    temps_400m = physio.temps_400m if hasattr(physio, 'temps_400m') and physio.temps_400m else None
    
    vma_origine = physio.vma_origine if hasattr(physio, 'vma_origine') and physio.vma_origine else ""
    vc_origine = physio.vc_origine if hasattr(physio, 'vc_origine') and physio.vc_origine else ""
    
    fc_max_cap = physio.fc_max_cap if hasattr(physio, 'fc_max_cap') and physio.fc_max_cap else None
    fc_max_natation = physio.fc_max_natation if hasattr(physio, 'fc_max_natation') and physio.fc_max_natation else None
    fc_max_velo = physio.fc_max_velo if hasattr(physio, 'fc_max_velo') and physio.fc_max_velo else None
    
    # Fonction pour formater le temps
    def formater_temps(secondes):
        if secondes is None or math.isnan(secondes) or math.isinf(secondes):
            return "Non renseigné"
        heures = int(secondes // 3600)
        minutes = int((secondes % 3600) // 60)
        sec = int(secondes % 60)
        if heures > 0:
            return f"{heures:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"
    
    perfs = [
        ["VMA", f"{vma} km/h" if vma else "Non renseignée", vma_origine if vma else ""],
        ["VC", f"{vc} km/h" if vc else "Non renseignée", vc_origine if vc else ""],
        ["FTP Vélo", f"{ftp} W" if ftp else "Non renseignée", ""],
        ["Temps 400m natation", formater_temps(temps_400m), ""],
        ["FC max CAP", f"{fc_max_cap} bpm" if fc_max_cap else "Non renseignée", ""],
        ["FC max Natation", f"{fc_max_natation} bpm" if fc_max_natation else "Non renseignée", ""],
        ["FC max Vélo", f"{fc_max_velo} bpm" if fc_max_velo else "Non renseignée", ""]
    ]
    
    table_data = []
    for row in perfs:
        table_data.append([
            to_paragraph(row[0], normal_style),
            to_paragraph(row[1], normal_style),
            to_paragraph(row[2], normal_style)
        ])
    
    table = Table(table_data, colWidths=[40*mm, 50*mm, 70*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def ajouter_section_ratio(story, physio, normal_style, sous_titre_style):
    """Ajoute l'analyse du ratio VC / VMA."""
    # CORRIGÉ: Compatible avec les deux classes
    vma_val = getattr(physio, 'vma_saisie', physio.vma if hasattr(physio, 'vma') else None)
    vc_val = getattr(physio, 'vc_saisie', physio.vc if hasattr(physio, 'vc') else None)
    
    if vma_val and vc_val:
        if not math.isnan(vma_val) and not math.isnan(vc_val):
            ratio = round(vc_val / vma_val * 100)
            story.append(Paragraph(clean_unicode("Analyse du ratio VC / VMA"), sous_titre_style))
            story.append(to_paragraph(f"Ratio : {ratio}%", normal_style))
            if ratio < 80:
                story.append(to_paragraph("Manque d'endurance, performance en deçà du potentiel VMA", normal_style))
            elif ratio > 90:
                story.append(to_paragraph("Coureur endurant, bien entraîné", normal_style))
            else:
                story.append(to_paragraph("Coureur équilibré", normal_style))
            story.append(Spacer(1, 6))


def ajouter_section_profil(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Profil de l'athlète avec estimations."""
    profil = getattr(physio, 'profil', None)
    if not profil:
        return
    
    story.append(Paragraph(clean_unicode("Profil de l'athlète"), sous_titre_style))
    story.append(to_paragraph(f"Profil : {profil}", normal_style))
    
    vitesses = getattr(physio, 'vitesses_performances', {})
    if vitesses:
        nb_dist = len(vitesses)
        story.append(to_paragraph(f"(basé sur {nb_dist} distance{'s' if nb_dist > 1 else ''})", normal_style))
        
        for k, v in vitesses.items():
            temps = ""
            if hasattr(physio, 'data') and physio.data:
                if k == "10km":
                    temps = physio.data.get('Quel est votre temps sur 10kms ?', '')
                elif k == "semi":
                    temps = physio.data.get('Quel est votre temps sur semi marathon ?', '')
                elif k == "marathon":
                    temps = physio.data.get('Quel est votre temps sur marathon ?', '')
            if temps:
                story.append(to_paragraph(f"   - {k} : {v} km/h ({temps})", normal_style))
            else:
                story.append(to_paragraph(f"   - {k} : {v} km/h", normal_style))
        
        if nb_dist >= 2:
            vma_estimee = getattr(physio, 'vma_estimee', None)
            vc_estimee = getattr(physio, 'vc_estimee', None)
            
            if vma_estimee:
                story.append(to_paragraph("Estimations à partir des performances :", normal_style))
                story.append(to_paragraph(f"   VMA estimée : {vma_estimee} km/h", normal_style))
            if vc_estimee:
                story.append(to_paragraph(f"   VC estimée : {vc_estimee} km/h", normal_style))
    
    story.append(Spacer(1, 6))


def ajouter_section_intensites(story, physio, normal_style, sous_titre_style):
    """
    Tableau des intensités avec Allure (Temps/km).
    CORRIGÉ: Compatible avec Physiologie ET PhysiologieSimple
    """
    story.append(Paragraph(clean_unicode("Tableau des intensités (effort/récupération)"), sous_titre_style))
    
    tableau_intensites = getattr(physio, 'tableau_intensites', None)
    if not tableau_intensites:
        story.append(to_paragraph("VMA ou VC non renseignée - impossible de calculer les intensités", normal_style))
        story.append(Spacer(1, 6))
        return
    
    # CORRIGÉ: Compatible avec les deux classes
    vma_val = getattr(physio, 'vma_saisie', physio.vma if hasattr(physio, 'vma') else None)
    vc_val = getattr(physio, 'vc_saisie', physio.vc if hasattr(physio, 'vc') else None)
    
    afficher_vma = vma_val is not None and vma_val > 0
    afficher_vc = vc_val is not None and vc_val > 0
    
    # Pour l'affichage de la base, utiliser les valeurs réelles
    if afficher_vma:
        story.append(to_paragraph(f"   Basé sur VMA = {physio.vma:.1f} km/h" if hasattr(physio, 'vma') and physio.vma else "   Basé sur VMA", normal_style))
    if afficher_vc:
        story.append(to_paragraph(f"   Basé sur VC = {physio.vc:.1f} km/h" if hasattr(physio, 'vc') and physio.vc else "   Basé sur VC", normal_style))
    
    if hasattr(physio, 'genre') and physio.genre == 'F':
        story.append(to_paragraph("   Adapté à une athlète féminine", normal_style))
    
    story.append(Spacer(1, 3))
    
    wrapped_style_small = get_style_wrapped(6)
    
    # Construction de l'en-tête
    en_tete = ["Durée"]
    
    if afficher_vma:
        en_tete.extend(["VMA (km/h)", "Dist (m)", "Allure"])
    
    if afficher_vc:
        en_tete.extend(["VC (km/h)", "Dist (m)", "Allure"])
    
    en_tete.extend(["Zone", "Objectif"])
    
    data = [en_tete]
    
    for z in tableau_intensites:
        ligne = [z["label"]]
        
        if afficher_vma:
            ligne.extend([
                f"{z['vitesse_vma']:.1f}",
                f"{z['distance_vma']}",
                z.get('allure_vma', '')
            ])
        
        if afficher_vc:
            ligne.extend([
                f"{z['vitesse_vc']:.1f}",
                f"{z['distance_vc']}",
                z.get('allure_vc', '')
            ])
        
        ligne.append(Paragraph(clean_unicode(z["zone"]), wrapped_style_small))
        ligne.append(Paragraph(clean_unicode(z["objectif"]), wrapped_style_small))
        
        data.append(ligne)
    
    if afficher_vma and afficher_vc:
        col_widths = [18*mm, 20*mm, 16*mm, 22*mm, 20*mm, 16*mm, 22*mm, 28*mm, 38*mm]
    elif afficher_vma:
        col_widths = [18*mm, 20*mm, 16*mm, 22*mm, 28*mm, 38*mm]
    elif afficher_vc:
        col_widths = [18*mm, 20*mm, 16*mm, 22*mm, 28*mm, 38*mm]
    else:
        col_widths = [18*mm, 28*mm, 38*mm]
    
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def ajouter_section_alertes(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Alertes / Données manquantes."""
    alertes = []
    
    if hasattr(physio, 'manques') and physio.manques:
        for m in physio.manques:
            alertes.append(f"{m.get('donnee', '?')} : {m.get('statut', '?')}")
    
    if hasattr(physio, 'alertes_profil') and physio.alertes_profil:
        for a in physio.alertes_profil:
            alertes.append(a)
    
    vma = physio.vma if hasattr(physio, 'vma') and physio.vma else None
    vc = physio.vc if hasattr(physio, 'vc') and physio.vc else None
    
    if not vma or math.isnan(vma):
        alertes.append("VMA : Non renseignée")
    if not vc or math.isnan(vc):
        alertes.append("VC : Non renseignée")
    
    if alertes:
        story.append(Paragraph(clean_unicode("Alertes / Données manquantes"), sous_titre_style))
        for a in alertes:
            story.append(to_paragraph(f"• {a}", normal_style))
    else:
        story.append(Paragraph(clean_unicode("Aucune donnée manquante"), sous_titre_style))