# ============================================================
# FICHIER: src/planificateur/export_pdf_plan.py
# RÔLE: Export du plan en PDF (1 page, une semaine au hasard)
#       Permet de visualiser l'agencement du plan
# ============================================================

import os
import sys
import random
from datetime import datetime
from typing import Dict

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm

# Import modifié - utilisation d'un import absolu
from export.sov import ajouter_filigrane_pdf


def exporter_pdf_plan(plan: Dict, plan_dir: str) -> str:
    """
    Exporte une page PDF du plan avec une semaine aléatoire.
    Permet de visualiser l'agencement du plan.
    """
    if not plan['semaines']:
        print("   ⚠️ Aucune semaine à exporter")
        return ""
    
    # Choisir une semaine au hasard
    semaine_choisie = random.choice(plan['semaines'])
    
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    titre_style = ParagraphStyle(
        'Titre', parent=styles['Heading1'],
        fontSize=16, alignment=TA_CENTER, spaceAfter=12
    )
    sous_titre_style = ParagraphStyle(
        'SousTitre', parent=styles['Heading2'],
        fontSize=12, spaceAfter=6
    )
    normal_style = styles['Normal']
    
    story = []
    
    # ---- TITRE ----
    story.append(Paragraph(
        f"Plan d'entraînement : {plan['athlete']}",
        titre_style
    ))
    story.append(Paragraph(
        f"Semaine {semaine_choisie['emoji']} S-{semaine_choisie['num_affichage']:02d} "
        f"du {semaine_choisie['date_debut']} au {semaine_choisie['date_fin']}",
        sous_titre_style
    ))
    story.append(Spacer(1, 6))
    
    # ---- INFORMATIONS ----
    story.append(Paragraph(
        f"Phase : {semaine_choisie['phase'].replace('_', ' ').capitalize()} | "
        f"Volume total : {semaine_choisie['volume_total']} min | "
        f"Séances intenses : {semaine_choisie['seances_intenses']}",
        normal_style
    ))
    story.append(Spacer(1, 6))
    
    # ---- TABLEAU DES SÉANCES ----
    data = [
        [
            Paragraph("Jour", normal_style),
            Paragraph("Date", normal_style),
            Paragraph("Discipline", normal_style),
            Paragraph("Type", normal_style),
            Paragraph("Détails", normal_style),
            Paragraph("Durée", normal_style)
        ]
    ]
    
    for jour in semaine_choisie['jours']:
        for seance in jour['seances']:
            if seance['discipline'] == 'Repos':
                continue
            data.append([
                Paragraph(jour['jour'], normal_style),
                Paragraph(jour['date'], normal_style),
                Paragraph(seance['discipline'], normal_style),
                Paragraph(seance['type'], normal_style),
                Paragraph(seance['details'][:50] + "..." if len(seance['details']) > 50 else seance['details'], normal_style),
                Paragraph(f"{seance['duree']} min", normal_style)
            ])
    
    table = Table(data, colWidths=[30*mm, 30*mm, 30*mm, 35*mm, 45*mm, 25*mm])
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
    
    # ---- LÉGENDE ----
    story.append(Paragraph(
        "Légende : "
        "🟩 Endurance | 🟨 Seuil | 🟥 Intense | 🟦 Récupération | ⭐ Course | ⬜ Repos",
        normal_style
    ))
    
    # ---- GÉNÉRATION DU PDF ----
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_plan_apercu_{timestamp}.pdf"
    chemin = os.path.join(plan_dir, nom_fichier)
    
    try:
        doc = SimpleDocTemplate(chemin, pagesize=landscape(A4))
        doc.onFirstPage = ajouter_filigrane_pdf
        doc.onLaterPages = ajouter_filigrane_pdf
        doc.build(story)
        print(f"   📄 Plan PDF aperçu exporté : {chemin}")
        return chemin
    except Exception as e:
        print(f"   ❌ Erreur PDF : {e}")
        return ""