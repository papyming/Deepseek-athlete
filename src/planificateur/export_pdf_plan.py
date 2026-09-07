# ============================================================
# FICHIER: src/planificateur/export_pdf_plan.py
# RÔLE: Export du plan en PDF (1 page, une semaine au hasard)
#       CORRIGÉ: Utilisation de caractères Unicode simples pour les émojis
# ============================================================

import os
import sys
import random
from datetime import datetime
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, cm

from export.sov import ajouter_filigrane_pdf


# CORRIGÉ: Utiliser des caractères Unicode simples au lieu des émojis
EMOJI_MAP = {
    '🟩': '●',   # Endurance
    '🟨': '◐',   # Seuil
    '🟥': '■',   # Intense
    '🟦': '○',   # Récupération
    '⭐': '★',   # Course
    '⬜': '□',   # Repos
    '🟢': '●',   # Semaine normale
    '🟡': '◐',   # Semaine chargée
    '🔴': '■',   # Semaine dure
    '⚪': '○',   # Semaine récupération
    '🔵': '◑',   # Affûtage
    '🟤': '◒',   # Exceptionnelle
}


def replace_emoji(text):
    """Remplace les émojis par des caractères Unicode simples."""
    if not text:
        return text
    for emoji, replacement in EMOJI_MAP.items():
        text = text.replace(emoji, replacement)
    return text


def exporter_pdf_plan(plan: Dict, plan_dir: str) -> str:
    """
    Exporte une page PDF du plan avec une semaine aléatoire.
    CORRIGÉ: Émojis remplacés par des caractères simples.
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
        f"Semaine {replace_emoji(semaine_choisie['emoji'])} S-{semaine_choisie['num_affichage']:02d} "
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
            # CORRIGÉ: Remplacer les émojis dans les détails
            details = replace_emoji(seance['details'])
            data.append([
                Paragraph(jour['jour'], normal_style),
                Paragraph(jour['date'], normal_style),
                Paragraph(seance['discipline'], normal_style),
                Paragraph(seance['type'], normal_style),
                Paragraph(details[:50] + "..." if len(details) > 50 else details, normal_style),
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
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))
    
    # ---- LÉGENDE ----
    # CORRIGÉ: Utilisation de caractères simples
    story.append(Paragraph(
        "Légende : "
        "● Endurance | ◐ Seuil | ■ Intense | ○ Récupération | ★ Course | □ Repos",
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