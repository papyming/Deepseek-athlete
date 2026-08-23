# ============================================================
# FICHIER: src/export/sections_pdf.py
# RÔLE: Définit les sections du PDF (données personnelles,
#       objectif, performances, profil, alertes, etc.)
# ============================================================

import math
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm


def ajouter_section_donnees_personnelles(story, physio, normal_style, sous_titre_style):
    """Ajoute la section des données personnelles."""
    story.append(Paragraph("1. Données personnelles", sous_titre_style))
    data = [
        [Paragraph("Sexe", normal_style), Paragraph(str(physio.genre), normal_style)],
        [Paragraph("Âge", normal_style), Paragraph(str(physio.age) if physio.age else "Non renseigné", normal_style)],
        [Paragraph("Taille/Poids", normal_style), Paragraph(str(physio.data.get('Taille/Poids', 'Non renseigné')), normal_style)],
        [Paragraph("Métier/Contraintes", normal_style), Paragraph(str(physio.data.get('Métier et ses contraintes', 'Aucune')), normal_style)]
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
    story.append(Paragraph("2. Objectif", sous_titre_style))
    objectif = physio.data.get('Objectif principal', 'Non renseigné')
    competition = physio.data.get('Quel format de compétition ?', '')
    competition_objectif = physio.data.get('Quelle est la compétition objectif ?', '')
    date_objectif = physio.data.get('date_objectif', '')
    
    if competition_objectif:
        if date_objectif:
            story.append(Paragraph(f"Compétition : {competition_objectif} ({date_objectif})", normal_style))
        else:
            story.append(Paragraph(f"Compétition : {competition_objectif}", normal_style))
    if competition:
        story.append(Paragraph(f"Format : {competition}", normal_style))
    story.append(Paragraph(f"Objectif : {objectif}", normal_style))
    story.append(Spacer(1, 6))


def ajouter_section_courses_preparatoires(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Courses préparatoires."""
    if not hasattr(physio, 'courses_preparatoires') or not physio.courses_preparatoires:
        return
    
    story.append(Paragraph("3. Courses préparatoires", sous_titre_style))
    for course in physio.courses_preparatoires:
        story.append(Paragraph(f"• {course}", normal_style))
    story.append(Spacer(1, 6))


def ajouter_section_performances(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Performances avec origine."""
    story.append(Paragraph("4. Performances", sous_titre_style))
    perfs = [
        [Paragraph("VMA", normal_style), 
         Paragraph(f"{physio.vma} km/h" if physio.vma and not math.isnan(physio.vma) else "Non renseignée", normal_style),
         Paragraph(physio.vma_origine if physio.vma and not math.isnan(physio.vma) else "Non renseignée", normal_style)],
        [Paragraph("VC", normal_style), 
         Paragraph(f"{physio.vc} km/h" if physio.vc and not math.isnan(physio.vc) else "Non renseignée", normal_style),
         Paragraph(physio.vc_origine if physio.vc and not math.isnan(physio.vc) else "Non renseignée", normal_style)],
        [Paragraph("FTP Vélo", normal_style), 
         Paragraph(f"{physio.ftp} W" if physio.ftp else "Non renseignée", normal_style),
         Paragraph("", normal_style)],
        [Paragraph("Temps 400m natation", normal_style), 
         Paragraph(physio._secondes_vers_temps(physio.temps_400m) if physio.temps_400m else "Non renseigné", normal_style),
         Paragraph("", normal_style)],
        [Paragraph("FC max CAP", normal_style), 
         Paragraph(f"{physio.fc_max_cap} bpm" if physio.fc_max_cap else "Non renseignée", normal_style),
         Paragraph("", normal_style)],
        [Paragraph("FC max Natation", normal_style), 
         Paragraph(f"{physio.fc_max_natation} bpm" if physio.fc_max_natation else "Non renseignée", normal_style),
         Paragraph("", normal_style)],
        [Paragraph("FC max Vélo", normal_style), 
         Paragraph(f"{physio.fc_max_velo} bpm" if physio.fc_max_velo else "Non renseignée", normal_style),
         Paragraph("", normal_style)]
    ]
    table = Table(perfs, colWidths=[40*mm, 50*mm, 70*mm])
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
    if physio.vma and physio.vc:
        if not math.isnan(physio.vma) and not math.isnan(physio.vc):
            ratio = round(physio.vc / physio.vma * 100)
            story.append(Paragraph("Analyse du ratio VC / VMA", sous_titre_style))
            story.append(Paragraph(f"Ratio : {ratio}%", normal_style))
            if ratio < 80:
                story.append(Paragraph("Manque d'endurance, performance en deçà du potentiel VMA", normal_style))
            elif ratio > 90:
                story.append(Paragraph("Coureur endurant, bien entraîné", normal_style))
            else:
                story.append(Paragraph("Coureur moyen", normal_style))
            story.append(Spacer(1, 6))


def ajouter_section_profil(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Profil de l'athlète avec estimations."""
    if not physio.profil:
        return
    
    story.append(Paragraph("5. Profil de l'athlète", sous_titre_style))
    story.append(Paragraph(f"Profil : {physio.profil}", normal_style))
    
    if physio.vitesses_performances:
        nb_dist = len(physio.vitesses_performances)
        story.append(Paragraph(f"(basé sur {nb_dist} distance{'s' if nb_dist > 1 else ''})", normal_style))
        
        for k, v in physio.vitesses_performances.items():
            temps = ""
            if k == "10km":
                temps = physio.data.get('Quel est votre temps sur 10kms ?', '')
            elif k == "semi":
                temps = physio.data.get('Quel est votre temps sur semi marathon ?', '')
            elif k == "marathon":
                temps = physio.data.get('Quel est votre temps sur marathon ?', '')
            if temps:
                story.append(Paragraph(f"   - {k} : {v} km/h ({temps})", normal_style))
            else:
                story.append(Paragraph(f"   - {k} : {v} km/h", normal_style))
        
        if nb_dist >= 2:
            if hasattr(physio, 'vma_estimee') and physio.vma_estimee:
                story.append(Paragraph("🔹 Estimations à partir des performances :", normal_style))
                story.append(Paragraph(f"   VMA estimée : {physio.vma_estimee} km/h", normal_style))
            if hasattr(physio, 'vc_estimee') and physio.vc_estimee:
                story.append(Paragraph(f"   VC estimée : {physio.vc_estimee} km/h", normal_style))
    
    story.append(Spacer(1, 6))


def ajouter_section_alertes(story, physio, normal_style, sous_titre_style):
    """Ajoute la section Alertes / Données manquantes."""
    alertes = []
    
    if physio.manques:
        for m in physio.manques:
            alertes.append(f"{m['donnee']} : {m['statut']}")
    if physio.alertes_profil:
        for a in physio.alertes_profil:
            alertes.append(a)
    if not physio.vma or math.isnan(physio.vma):
        alertes.append("VMA : Non renseignée")
    if not physio.vc or math.isnan(physio.vc):
        alertes.append("VC : Non renseignée")
    
    if alertes:
        story.append(Paragraph("9. Alertes / Données manquantes", sous_titre_style))
        for a in alertes:
            story.append(Paragraph(f"• {a}", normal_style))
    else:
        story.append(Paragraph("9. Aucune donnée manquante", sous_titre_style))