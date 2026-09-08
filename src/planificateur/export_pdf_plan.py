# ============================================================
# FICHIER: src/planificateur/export_pdf_plan.py
# RÔLE: Export du plan en PDF (TOUTES les semaines)
#       CORRIGÉ: Légende émojis différenciés + tableau complet
# ============================================================

import os
import sys
from datetime import datetime
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.units import mm, cm

from export.sov import ajouter_filigrane_pdf


# CORRIGÉ: Utiliser des caractères Unicode simples au lieu des émojis
LEGENDE = {
    '●': 'Endurance',
    '◐': 'Seuil',
    '■': 'Intense',
    '○': 'Récupération',
    '★': 'Course',
    '□': 'Repos',
}

# CORRIGÉ: Remplacer les émojis par des caractères simples dans les données
EMOJI_TO_SYMBOL = {
    '🟩': '●',
    '🟨': '◐',
    '🟥': '■',
    '🟦': '○',
    '⭐': '★',
    '⬜': '□',
    '🟢': '●',
    '🟡': '◐',
    '🔴': '■',
    '⚪': '○',
    '🔵': '◑',
    '🟤': '◒',
}


def replace_emojis(text):
    """Remplace les émojis par des caractères simples."""
    if not text:
        return text
    for emoji, symbol in EMOJI_TO_SYMBOL.items():
        text = text.replace(emoji, symbol)
    return text


def exporter_pdf_plan(plan: Dict, plan_dir: str) -> str:
    """
    Exporte le plan complet en PDF avec toutes les semaines.
    CORRIGÉ: Toutes les semaines + légende claire.
    """
    if not plan['semaines']:
        print("   ⚠️ Aucune semaine à exporter")
        return ""

    styles = getSampleStyleSheet()

    titre_style = ParagraphStyle(
        'Titre', parent=styles['Heading1'],
        fontSize=16, alignment=TA_CENTER, spaceAfter=12
    )
    sous_titre_style = ParagraphStyle(
        'SousTitre', parent=styles['Heading2'],
        fontSize=12, spaceAfter=6
    )
    normal_style = styles['Normal']
    small_style = ParagraphStyle(
        'Small', parent=styles['Normal'],
        fontSize=7, alignment=TA_CENTER
    )

    story = []

    # ---- TITRE GÉNÉRAL ----
    story.append(Paragraph(
        f"Plan d'entraînement : {plan['athlete']}",
        titre_style
    ))
    story.append(Paragraph(
        f"Du {plan['date_debut']} au {plan['date_objectif']}",
        sous_titre_style
    ))
    story.append(Spacer(1, 6))

    # ---- LÉGENDE ----
    legend_text = "Légende : "
    for symbol, label in LEGENDE.items():
        legend_text += f"{symbol} = {label}  "
    story.append(Paragraph(legend_text, normal_style))
    story.append(Spacer(1, 6))

    # ---- TABLEAU DE TOUTES LES SEMAINES ----
    story.append(Paragraph("Planning complet", sous_titre_style))
    story.append(Spacer(1, 3))

    # Construction du tableau avec toutes les séances
    all_rows = []

    # En-tête
    header = ["Semaine", "Jour", "Date", "Discipline", "Type", "Détails", "Durée", "Intensité"]
    all_rows.append([Paragraph(h, small_style) for h in header])

    for semaine in plan['semaines']:
        num_affichage = semaine.get('num_affichage', '')
        emoji = replace_emojis(semaine.get('emoji', '●'))
        semaine_label = f"{emoji}S-{num_affichage:02d}"

        for jour in semaine.get('jours', []):
            for seance in jour.get('seances', []):
                if seance.get('discipline') == 'Repos':
                    continue

                details = replace_emojis(seance.get('details', ''))
                if len(details) > 40:
                    details = details[:37] + "..."

                # Niveau d'intensité
                difficulte = seance.get('difficulte', 'endurance')
                intensite_map = {
                    'recuperation': '○',
                    'endurance': '●',
                    'seuil': '◐',
                    'intense': '■',
                    'course': '★'
                }
                intensite = intensite_map.get(difficulte, '●')

                all_rows.append([
                    Paragraph(semaine_label, small_style),
                    Paragraph(jour.get('jour', ''), small_style),
                    Paragraph(jour.get('date', ''), small_style),
                    Paragraph(seance.get('discipline', ''), small_style),
                    Paragraph(seance.get('type', ''), small_style),
                    Paragraph(details, small_style),
                    Paragraph(f"{seance.get('duree', 0)} min", small_style),
                    Paragraph(intensite, small_style)
                ])

    # Largeurs des colonnes
    col_widths = [25*mm, 20*mm, 25*mm, 25*mm, 30*mm, 50*mm, 20*mm, 15*mm]

    # Création du tableau
    table = Table(all_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    story.append(table)

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