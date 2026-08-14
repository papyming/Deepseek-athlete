import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from .sov import sauvegarder_pdf

def generer_pdf_athlete(nom, physio, jours_dispos, nb_bi, seances_vma, seances_vc, athlete_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = os.path.join(athlete_dir, f"{nom.replace(' ', '_')}_resume_{timestamp}")
    
    doc = SimpleDocTemplate(base_path + '.pdf', pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=12)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']

    story.append(Paragraph(f"Résumé Athlète : {nom}", titre_style))
    story.append(Spacer(1, 6))

    # ---- 1. DONNÉES PERSONNELLES ----
    story.append(Paragraph("1. Données personnelles", sous_titre_style))
    data = [
        ["Sexe", str(physio.genre)],
        ["Âge", str(physio.age) if physio.age else "Non renseigné"],
        ["Taille/Poids", str(physio.data.get('Taille/Poids', 'Non renseigné'))],
        ["Métier/Contraintes", str(physio.data.get('Métier et ses contraintes', 'Aucune'))]
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

    # ---- 2. COURSES PRÉPARATOIRES ----
    if hasattr(physio, 'courses_preparatoires') and physio.courses_preparatoires:
        story.append(Paragraph("2. Courses préparatoires", sous_titre_style))
        for course in physio.courses_preparatoires:
            if ' ' in course:
                parts = course.rsplit(' ', 1)
                if len(parts) == 2 and parts[1].replace('/', '').replace('-', '').isdigit():
                    story.append(Paragraph(f"• {parts[0]} ({parts[1]})", normal_style))
                else:
                    story.append(Paragraph(f"• {course}", normal_style))
            else:
                story.append(Paragraph(f"• {course}", normal_style))
        story.append(Spacer(1, 6))

    # ---- 3. PERFORMANCES AVEC ORIGINE ----
    story.append(Paragraph("3. Performances", sous_titre_style))
    perfs = [
        ["VMA", 
         Paragraph(f"{physio.vma} km/h" if physio.vma else "Non renseignée", normal_style),
         Paragraph(physio.vma_origine if physio.vma else "Non renseignée", normal_style)],
        ["VC", 
         Paragraph(f"{physio.vc} km/h" if physio.vc else "Non renseignée", normal_style),
         Paragraph(physio.vc_origine if physio.vc else "Non renseignée", normal_style)],
        ["FTP Vélo", 
         Paragraph(f"{physio.ftp} W" if physio.ftp else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.ftp else "", normal_style)],
        ["Temps 400m natation", 
         Paragraph(physio._secondes_vers_temps(physio.temps_400m) if physio.temps_400m else "Non renseigné", normal_style),
         Paragraph("Non renseigné" if not physio.temps_400m else "", normal_style)],
        ["FC max CAP", 
         Paragraph(f"{physio.fc_max_cap} bpm" if physio.fc_max_cap else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_cap else "", normal_style)],
        ["FC max Natation", 
         Paragraph(f"{physio.fc_max_natation} bpm" if physio.fc_max_natation else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_natation else "", normal_style)],
        ["FC max Vélo", 
         Paragraph(f"{physio.fc_max_velo} bpm" if physio.fc_max_velo else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_velo else "", normal_style)]
    ]
    table = Table(perfs, colWidths=[35*mm, 45*mm, 80*mm])
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

    # ---- 4. ANALYSE RATIO ----
    if physio.vma and physio.vc:
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

    # ---- 5. PROFIL ----
    if physio.profil:
        story.append(Paragraph("4. Profil de l'athlète", sous_titre_style))
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
        story.append(Spacer(1, 6))

    # ---- 6. ZONES VMA ----
    if physio.tableau_vma:
        story.append(Paragraph("5. Zones VMA", sous_titre_style))
        vma_data = [["Distance", "Vitesse (km/h)", "Temps"]]
        for ligne in physio.tableau_vma:
            vma_data.append([
                Paragraph(f"{ligne['distance']}m", normal_style),
                Paragraph(f"{ligne['vitesse']} km/h", normal_style),
                Paragraph(ligne['temps'], normal_style)
            ])
        table = Table(vma_data, colWidths=[35*mm, 45*mm, 45*mm])
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

    # ---- 7. ZONES VC ----
    if physio.tableau_vc:
        story.append(Paragraph("6. Zones VC avec récupération", sous_titre_style))
        vc_data = [["Distance", "Vitesse effort", "Temps effort", "Récup", "Temps recup"]]
        for ligne in physio.tableau_vc:
            vc_data.append([
                Paragraph(f"{ligne['distance_effort']}m", normal_style),
                Paragraph(f"{ligne['vitesse_effort']} km/h", normal_style),
                Paragraph(ligne['temps_effort'], normal_style),
                Paragraph(f"{ligne['distance_recup']}m", normal_style),
                Paragraph(ligne['temps_recup'], normal_style)
            ])
        table = Table(vc_data, colWidths=[28*mm, 32*mm, 28*mm, 22*mm, 28*mm])
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

    # ---- 8. JOURS ----
    story.append(Paragraph("7. Jours d'entraînement", sous_titre_style))
    jours_data = [
        ["Discipline", "Jours", "Bi-quotidien"],
        ["CAP", ", ".join(jours_dispos['CAP']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['CAP']) or "Non"],
        ["Vélo", ", ".join(jours_dispos['Velo']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['Velo']) or "Non"],
        ["Natation", ", ".join(jours_dispos['Natation']) or "Aucun", ", ".join(jours_dispos['bi_quotidien']['Natation']) or "Non"]
    ]
    table = Table(jours_data, colWidths=[45*mm, 55*mm, 55*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))

    # ---- 9. ALERTES ----
    alertes = []
    if physio.manques:
        for m in physio.manques:
            alertes.append(f"{m['donnee']} : {m['statut']}")
    if physio.alertes_profil:
        for a in physio.alertes_profil:
            alertes.append(a)
    if not physio.vma:
        alertes.append("VMA : Non renseignée")
    if not physio.vc:
        alertes.append("VC : Non renseignée")
    
    if alertes:
        story.append(Paragraph("8. Alertes / Données manquantes", sous_titre_style))
        for a in alertes:
            story.append(Paragraph(f"• {a}", normal_style))
    else:
        story.append(Paragraph("8. Aucune donnée manquante", sous_titre_style))

    doc.story = story
    pdf_path = sauvegarder_pdf(doc, base_path)
    print(f"   📄 PDF résumé généré : {pdf_path}")