# ============================================================
# FICHIER: src/export/generateur_pdf.py
# RÔLE: Construction du contenu du PDF récapitulatif
#       Assemble toutes les sections et tableaux
# ============================================================

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Paragraph, Spacer

from .sections_pdf import (
    ajouter_section_donnees_personnelles,
    ajouter_section_objectif,
    ajouter_section_courses_preparatoires,
    ajouter_section_performances,
    ajouter_section_ratio,
    ajouter_section_profil,
    ajouter_section_alertes
)
from .tables_pdf import (
    generer_tableau_vma,
    generer_tableau_vc,
    generer_tableau_velo,
    generer_tableau_natation,
    generer_tableau_jours
)
from .sov import sauvegarder_pdf


def generer_pdf_athlete(nom, physio, jours_dispos, nb_bi, seances_vma, seances_vc, athlete_dir):
    """
    Génère un PDF récapitulatif complet pour un athlète.
    
    Args:
        nom: Nom de l'athlète
        physio: Objet Physiologie contenant toutes les données
        jours_dispos: Disponibilités par discipline
        nb_bi: Nombre de jours bi-quotidiens
        seances_vma: Liste des séances VMA
        seances_vc: Liste des séances VC
        athlete_dir: Dossier de destination
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = os.path.join(athlete_dir, f"{nom.replace(' ', '_')}_resume_{timestamp}")
    
    styles = getSampleStyleSheet()
    story = []
    
    titre_style = ParagraphStyle('Titre', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=12)
    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Heading2'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']
    
    # ---- TITRE ----
    story.append(Paragraph(f"Résumé Athlète : {nom}", titre_style))
    story.append(Spacer(1, 6))
    
    # ---- SECTIONS ----
    ajouter_section_donnees_personnelles(story, physio, normal_style, sous_titre_style)
    ajouter_section_objectif(story, physio, normal_style, sous_titre_style)
    ajouter_section_courses_preparatoires(story, physio, normal_style, sous_titre_style)
    ajouter_section_performances(story, physio, normal_style, sous_titre_style)
    ajouter_section_ratio(story, physio, normal_style, sous_titre_style)
    ajouter_section_profil(story, physio, normal_style, sous_titre_style)
    
    # ---- TABLEAUX ----
    generer_tableau_vma(story, physio, normal_style, sous_titre_style)
    generer_tableau_vc(story, physio, normal_style, sous_titre_style)
    generer_tableau_velo(story, physio, normal_style, sous_titre_style)
    generer_tableau_natation(story, physio, normal_style, sous_titre_style)
    generer_tableau_jours(story, physio, jours_dispos, normal_style, sous_titre_style)
    
    # ---- ALERTES ----
    ajouter_section_alertes(story, physio, normal_style, sous_titre_style)
    
    # Créer un document temporaire pour le story
    class DocTemp:
        pass
    doc = DocTemp()
    doc.story = story
    
    # Sauvegarder avec filigrane (via sov.py)
    pdf_path = sauvegarder_pdf(doc, base_path)
    print(f"   📄 PDF résumé généré : {pdf_path}")