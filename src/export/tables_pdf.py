# ============================================================
# FICHIER: src/export/tables_pdf.py
# RÔLE: Définit les tableaux du PDF (VMA, VC, Vélo, Natation)
# ============================================================

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import mm


def generer_tableau_vma(story, physio, normal_style, sous_titre_style):
    """Génère le tableau des zones VMA."""
    if not physio.tableau_vma:
        return
    
    story.append(Paragraph("6. Zones VMA", sous_titre_style))
    data = [
        [Paragraph("Effort (m)", normal_style), 
         Paragraph("Vitesse (km/h)", normal_style),
         Paragraph("Temps effort", normal_style), 
         Paragraph("Récup (m)", normal_style), 
         Paragraph("Temps recup", normal_style)]
    ]
    for ligne in physio.tableau_vma:
        data.append([
            Paragraph(str(ligne.get('distance', '?')), normal_style),
            Paragraph(str(ligne.get('vitesse', 0)), normal_style),
            Paragraph(ligne.get('temps', '00:00'), normal_style),
            Paragraph(str(int(ligne.get('distance_recup', 0))), normal_style),
            Paragraph(ligne.get('temps_recup', '00:00'), normal_style)
        ])
    table = Table(data, colWidths=[30*mm, 35*mm, 30*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_vc(story, physio, normal_style, sous_titre_style):
    """Génère le tableau des zones VC."""
    if not physio.tableau_vc:
        return
    
    story.append(Paragraph("7. Zones VC avec récupération", sous_titre_style))
    data = [
        [Paragraph("Effort (m)", normal_style), 
         Paragraph("Vitesse effort (km/h)", normal_style),
         Paragraph("Temps effort", normal_style), 
         Paragraph("Récup (m)", normal_style), 
         Paragraph("Temps recup", normal_style)]
    ]
    for ligne in physio.tableau_vc:
        data.append([
            Paragraph(str(ligne.get('distance_effort', ligne.get('distance', '?'))), normal_style),
            Paragraph(str(ligne.get('vitesse_effort', 0)), normal_style),
            Paragraph(ligne.get('temps_effort', '00:00'), normal_style),
            Paragraph(str(int(ligne.get('distance_recup', 0))), normal_style),
            Paragraph(ligne.get('temps_recup', '00:00'), normal_style)
        ])
    table = Table(data, colWidths=[30*mm, 35*mm, 30*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_velo(story, physio, normal_style, sous_titre_style):
    """Génère le tableau des zones vélo basées sur FTP."""
    if not physio.ftp:
        return
    
    story.append(Paragraph("8. Zones Vélo (FTP)", sous_titre_style))
    data = [
        [Paragraph("Zone", normal_style), 
         Paragraph("Puissance (W)", normal_style)]
    ]
    zones = physio.zones_velo
    for zone, valeurs in zones.items():
        data.append([
            Paragraph(zone, normal_style),
            Paragraph(f"{valeurs['min']} - {valeurs['max']} W", normal_style)
        ])
    table = Table(data, colWidths=[40*mm, 100*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_natation(story, physio, normal_style, sous_titre_style):
    """Génère le tableau des zones natation basées sur le temps 400m."""
    if not physio.tableau_natation:
        return
    
    story.append(Paragraph("9. Zones Natation (400m)", sous_titre_style))
    
    data = [
        [Paragraph("Zone", normal_style),
         Paragraph("Allure\n(min/100m)", normal_style),
         Paragraph("25m\nEffort/Repos", normal_style),
         Paragraph("50m\nEffort/Repos", normal_style),
         Paragraph("75m\nEffort/Repos", normal_style),
         Paragraph("100m\nEffort/Repos", normal_style)]
    ]
    
    for ligne in physio.tableau_natation:
        zone = ligne['zone']
        allure = ligne['allure_max']
        distances = ligne['distances']
        temps_intensite = ligne['temps_intensite']
        temps_repos = ligne['temps_repos']
        
        cellules = []
        for d in distances:
            effort = temps_intensite.get(d, "00:00")
            repos = temps_repos.get(d, "00:00")
            cellules.append(f"{effort} / {repos}")
        
        data.append([
            Paragraph(zone, normal_style),
            Paragraph(f"{allure}", normal_style),
            Paragraph(cellules[0], normal_style),
            Paragraph(cellules[1], normal_style),
            Paragraph(cellules[2], normal_style),
            Paragraph(cellules[3], normal_style)
        ])
    
    table = Table(data, colWidths=[25*mm, 30*mm, 30*mm, 30*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_jours(story, physio, jours_dispos, normal_style, sous_titre_style):
    """Génère le tableau des jours d'entraînement."""
    story.append(Paragraph("10. Jours d'entraînement", sous_titre_style))
    data = [
        [Paragraph("Discipline", normal_style), 
         Paragraph("Jours", normal_style), 
         Paragraph("Bi-quotidien", normal_style)],
        [Paragraph("CAP", normal_style), 
         Paragraph(", ".join(jours_dispos['CAP']) or "Aucun", normal_style), 
         Paragraph(", ".join(jours_dispos['bi_quotidien']['CAP']) or "Non", normal_style)],
        [Paragraph("Vélo", normal_style), 
         Paragraph(", ".join(jours_dispos['Velo']) or "Aucun", normal_style), 
         Paragraph(", ".join(jours_dispos['bi_quotidien']['Velo']) or "Non", normal_style)],
        [Paragraph("Natation", normal_style), 
         Paragraph(", ".join(jours_dispos['Natation']) or "Aucun", normal_style), 
         Paragraph(", ".join(jours_dispos['bi_quotidien']['Natation']) or "Non", normal_style)]
    ]
    table = Table(data, colWidths=[45*mm, 55*mm, 55*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))