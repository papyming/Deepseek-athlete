# ============================================================
# FICHIER: src/export/tables_pdf.py
# RÔLE: Définit les tableaux du PDF (VMA, VC, Vélo, Natation)
#       CORRIGÉ: Largeurs adaptées avec wrap
# ============================================================

from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle


def clean_unicode(text):
    replacements = {
        '₂': '2', '₃': '3', '₄': '4', '₁': '1', '₀': '0',
        '²': '2', '³': '3', '·': '.', '–': '-', '—': '-',
        '’': "'", '‘': "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def get_style_wrapped(fontsize=8):
    return ParagraphStyle(
        'Wrapped',
        fontSize=fontsize,
        leading=fontsize + 2,
        wordWrap='CJK'
    )


def generer_tableau_vma(story, physio, normal_style, sous_titre_style):
    if not physio.tableau_vma:
        return
    
    story.append(Paragraph(clean_unicode("Zones VMA"), sous_titre_style))
    story.append(Spacer(1, 3))
    
    wrapped_style = get_style_wrapped(8)
    
    data = [
        [clean_unicode("Effort (m)"), clean_unicode("Vitesse (km/h)"), clean_unicode("Temps effort"), clean_unicode("Récup (m)"), clean_unicode("Temps recup")]
    ]
    for ligne in physio.tableau_vma:
        distance = ligne.get('distance', ligne.get('distance_effort', '?'))
        vitesse = ligne.get('vitesse', ligne.get('vitesse_effort', 0))
        temps = ligne.get('temps', ligne.get('temps_effort', '00:00'))
        distance_recup = ligne.get('distance_recup', 0)
        temps_recup = ligne.get('temps_recup', '00:00')
        
        data.append([
            str(distance),
            f"{vitesse:.1f}" if isinstance(vitesse, (int, float)) else str(vitesse),
            temps,
            str(int(distance_recup)),
            temps_recup
        ])
    
    table = Table(data, colWidths=[28*mm, 30*mm, 28*mm, 28*mm, 28*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_vc(story, physio, normal_style, sous_titre_style):
    if not physio.tableau_vc:
        return
    
    story.append(Paragraph(clean_unicode("Zones VC avec récupération"), sous_titre_style))
    story.append(Spacer(1, 3))
    
    data = [
        [clean_unicode("Effort (m)"), clean_unicode("Vitesse (km/h)"), clean_unicode("Temps effort"), clean_unicode("Récup (m)"), clean_unicode("Temps recup")]
    ]
    for ligne in physio.tableau_vc:
        distance = ligne.get('distance_effort', ligne.get('distance', '?'))
        vitesse = ligne.get('vitesse_effort', ligne.get('vitesse', 0))
        temps = ligne.get('temps_effort', ligne.get('temps', '00:00'))
        distance_recup = ligne.get('distance_recup', 0)
        temps_recup = ligne.get('temps_recup', '00:00')
        
        data.append([
            str(distance),
            f"{vitesse:.1f}" if isinstance(vitesse, (int, float)) else str(vitesse),
            temps,
            str(int(distance_recup)),
            temps_recup
        ])
    
    table = Table(data, colWidths=[28*mm, 30*mm, 28*mm, 28*mm, 28*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_velo(story, physio, normal_style, sous_titre_style):
    if not physio.ftp:
        return
    
    story.append(Paragraph(clean_unicode("Zones Vélo (FTP)"), sous_titre_style))
    story.append(Spacer(1, 3))
    
    data = [
        [clean_unicode("Zone"), clean_unicode("Puissance (W)")]
    ]
    zones = physio.zones_velo
    for zone, valeurs in zones.items():
        data.append([
            clean_unicode(zone),
            clean_unicode(f"{valeurs['min']} - {valeurs['max']} W")
        ])
    
    table = Table(data, colWidths=[40*mm, 100*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def generer_tableau_natation(story, physio, normal_style, sous_titre_style):
    if not physio.tableau_natation:
        return
    
    story.append(Paragraph(clean_unicode("Zones Natation (400m)"), sous_titre_style))
    story.append(Spacer(1, 3))
    
    wrapped_style = get_style_wrapped(7)
    
    data = [
        [clean_unicode("Zone"), clean_unicode("Allure (min/100m)"), clean_unicode("25m Effort/Repos"), clean_unicode("50m Effort/Repos"), clean_unicode("75m Effort/Repos"), clean_unicode("100m Effort/Repos")]
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
            clean_unicode(zone),
            clean_unicode(f"{allure}"),
            cellules[0],
            cellules[1],
            cellules[2],
            cellules[3]
        ])
    
    table = Table(data, colWidths=[22*mm, 28*mm, 28*mm, 28*mm, 28*mm, 28*mm], repeatRows=1)
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


def generer_tableau_jours(story, physio, jours_dispos, normal_style, sous_titre_style):
    story.append(Paragraph(clean_unicode("Jours d'entraînement"), sous_titre_style))
    story.append(Spacer(1, 3))
    
    data = [
        [clean_unicode("Discipline"), clean_unicode("Jours"), clean_unicode("Bi-quotidien")],
        [clean_unicode("CAP"), clean_unicode(", ".join(jours_dispos['CAP']) or "Aucun"), clean_unicode(", ".join(jours_dispos['bi_quotidien']['CAP']) or "Non")],
        [clean_unicode("Vélo"), clean_unicode(", ".join(jours_dispos['Velo']) or "Aucun"), clean_unicode(", ".join(jours_dispos['bi_quotidien']['Velo']) or "Non")],
        [clean_unicode("Natation"), clean_unicode(", ".join(jours_dispos['Natation']) or "Aucun"), clean_unicode(", ".join(jours_dispos['bi_quotidien']['Natation']) or "Non")]
    ]
    
    table = Table(data, colWidths=[40*mm, 55*mm, 55*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))