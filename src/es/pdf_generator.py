import os
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .sov import sauvegarder_pdf

# ============================================================
# FONCTION FILIGRANE (WATERMARK)
# ============================================================

def ajouter_filigrane(canvas_obj, largeur_page, hauteur_page, chemin_image="Sigle_Papy.gif"):
    """
    Ajoute un logo en filigrane (watermark) sur une page PDF.
    """
    if not os.path.exists(chemin_image):
        return
    
    try:
        img = ImageReader(chemin_image)
        img_width, img_height = img.getSize()
        
        facteur_echelle = 0.30
        largeur_filigrane = largeur_page * facteur_echelle
        hauteur_filigrane = img_height * (largeur_filigrane / img_width)
        
        x = (largeur_page - largeur_filigrane) / 2
        y = (hauteur_page - hauteur_filigrane) / 2
        
        canvas_obj.saveState()
        canvas_obj.setFillAlpha(0.15)
        canvas_obj.setStrokeAlpha(0.15)
        
        canvas_obj.drawImage(
            img,
            x, y,
            width=largeur_filigrane,
            height=hauteur_filigrane,
            mask='auto',
            preserveAspectRatio=True
        )
        
        canvas_obj.restoreState()
        
    except Exception as e:
        print(f"   ⚠️ Impossible d'ajouter le filigrane : {e}")


# ============================================================
# GÉNÉRATION DU PDF
# ============================================================

def generer_pdf_athlete(nom, physio, jours_dispos, nb_bi, seances_vma, seances_vc, athlete_dir):
    """
    Génère un PDF récapitulatif complet pour un athlète.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = os.path.join(athlete_dir, f"{nom.replace(' ', '_')}_resume_{timestamp}")
    
    doc = SimpleDocTemplate(base_path + '.pdf', pagesize=A4)
    
    def filigrane_callback(canvas_obj, doc):
        largeur_page, hauteur_page = A4
        chemin_logo = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Sigle_Papy.gif')
        ajouter_filigrane(canvas_obj, largeur_page, hauteur_page, chemin_logo)
    
    doc.onFirstPage = filigrane_callback
    doc.onLaterPages = filigrane_callback
    
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

    # ---- 2. OBJECTIF ----
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

    # ---- 3. COURSES PRÉPARATOIRES ----
    if hasattr(physio, 'courses_preparatoires') and physio.courses_preparatoires:
        story.append(Paragraph("3. Courses préparatoires", sous_titre_style))
        for course in physio.courses_preparatoires:
            if ' ' in course:
                parts = course.rsplit(' ', 1)
                if len(parts) == 2 and parts[1].replace('/', '').replace('-', '').isdigit():
                    story.append(Paragraph(f"• {parts[0]} → {parts[1]}", normal_style))
                else:
                    story.append(Paragraph(f"• {course}", normal_style))
            else:
                story.append(Paragraph(f"• {course}", normal_style))
        story.append(Spacer(1, 6))

    # ---- 4. PERFORMANCES AVEC ORIGINE ----
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
         Paragraph("Non renseignée" if not physio.ftp else "", normal_style)],
        [Paragraph("Temps 400m natation", normal_style), 
         Paragraph(physio._secondes_vers_temps(physio.temps_400m) if physio.temps_400m else "Non renseigné", normal_style),
         Paragraph("Non renseigné" if not physio.temps_400m else "", normal_style)],
        [Paragraph("FC max CAP", normal_style), 
         Paragraph(f"{physio.fc_max_cap} bpm" if physio.fc_max_cap else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_cap else "", normal_style)],
        [Paragraph("FC max Natation", normal_style), 
         Paragraph(f"{physio.fc_max_natation} bpm" if physio.fc_max_natation else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_natation else "", normal_style)],
        [Paragraph("FC max Vélo", normal_style), 
         Paragraph(f"{physio.fc_max_velo} bpm" if physio.fc_max_velo else "Non renseignée", normal_style),
         Paragraph("Non renseignée" if not physio.fc_max_velo else "", normal_style)]
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

    # ---- 5. ANALYSE RATIO ----
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

    # ---- 6. PROFIL DE L'ATHLÈTE AVEC ESTIMATIONS ----
    if physio.profil:
        story.append(Paragraph("5. Profil de l'athlète", sous_titre_style))
        story.append(Paragraph(f"Profil : {physio.profil}", normal_style))
        
        if physio.vitesses_performances:
            nb_dist = len(physio.vitesses_performances)
            story.append(Paragraph(f"(basé sur {nb_dist} distance{'s' if nb_dist > 1 else ''})", normal_style))
            
            # Affichage des performances
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
            
            # 🔥 Ajout des estimations (si au moins 2 distances)
            if nb_dist >= 2:
                if hasattr(physio, 'vma_estimee') and physio.vma_estimee:
                    story.append(Paragraph(f"🔹 Estimations à partir des performances :", normal_style))
                    story.append(Paragraph(f"   VMA estimée : {physio.vma_estimee} km/h", normal_style))
                if hasattr(physio, 'vc_estimee') and physio.vc_estimee:
                    story.append(Paragraph(f"   VC estimée : {physio.vc_estimee} km/h", normal_style))
        
        story.append(Spacer(1, 6))

    # ---- 7. ZONES VMA (5 colonnes) ----
    if physio.tableau_vma:
        story.append(Paragraph("6. Zones VMA", sous_titre_style))
        vma_data = [
            [Paragraph("Effort (m)", normal_style), 
             Paragraph("Vitesse (km/h)", normal_style),
             Paragraph("Temps effort", normal_style), 
             Paragraph("Récup (m)", normal_style), 
             Paragraph("Temps recup", normal_style)]
        ]
        for ligne in physio.tableau_vma:
            vma_data.append([
                Paragraph(str(ligne.get('distance', '?')), normal_style),
                Paragraph(str(ligne.get('vitesse', 0)), normal_style),
                Paragraph(ligne.get('temps', '00:00'), normal_style),
                Paragraph(str(int(ligne.get('distance_recup', 0))), normal_style),
                Paragraph(ligne.get('temps_recup', '00:00'), normal_style)
            ])
        table = Table(vma_data, colWidths=[30*mm, 35*mm, 30*mm, 30*mm, 30*mm])
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

    # ---- 8. ZONES VC (5 colonnes) ----
    if physio.tableau_vc:
        story.append(Paragraph("7. Zones VC avec récupération", sous_titre_style))
        vc_data = [
            [Paragraph("Effort (m)", normal_style), 
             Paragraph("Vitesse effort (km/h)", normal_style),
             Paragraph("Temps effort", normal_style), 
             Paragraph("Récup (m)", normal_style), 
             Paragraph("Temps recup", normal_style)]
        ]
        for ligne in physio.tableau_vc:
            vc_data.append([
                Paragraph(str(ligne.get('distance_effort', ligne.get('distance', '?'))), normal_style),
                Paragraph(str(ligne.get('vitesse_effort', 0)), normal_style),
                Paragraph(ligne.get('temps_effort', '00:00'), normal_style),
                Paragraph(str(int(ligne.get('distance_recup', 0))), normal_style),
                Paragraph(ligne.get('temps_recup', '00:00'), normal_style)
            ])
        table = Table(vc_data, colWidths=[30*mm, 35*mm, 30*mm, 30*mm, 30*mm])
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

    # ---- 9. JOURS ----
    story.append(Paragraph("8. Jours d'entraînement", sous_titre_style))
    jours_data = [
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
    table = Table(jours_data, colWidths=[45*mm, 55*mm, 55*mm])
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

    # ---- 10. ALERTES ----
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

    doc.story = story
    pdf_path = sauvegarder_pdf(doc, base_path)
    print(f"   📄 PDF résumé généré : {pdf_path}")