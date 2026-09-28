# ============================================================
# FICHIER: src/planificateur/export_pdf_plan.py
# RÔLE: Export du plan en PDF, 2 semaines par page
#       Présentation : entête + légendes répétés, symboles
#       d'intensité DESSINÉS (formes vectorielles), grand
#       tableau qui remplit la page, période et numéro de page.
# ============================================================

import math
import os
import sys
from datetime import datetime
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable,
)
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdfcanvas

from export.sov import ajouter_filigrane_pdf


def _format_date_for_user(value):
    """Formate une date ISO interne pour l'affichage utilisateur."""
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        return value


# ---- LÉGENDE D'INTENSITÉ (API historique conservée) ----
LEGENDE = {
    '●': 'Endurance',
    '◐': 'Seuil',
    '■': 'Intense',
    '○': 'Récupération',
    '★': 'Course',
    '□': 'Repos',
}

LEGENDE_INTENSITE = [
    ('endurance', 'Endurance'),
    ('seuil', 'Seuil'),
    ('intense', 'Intense'),
    ('recuperation', 'Récupération'),
    ('course', 'Course'),
    ('repos', 'Repos'),
]

# Formes vectorielles : (type de forme, couleur). Elles sont DESSINÉES par
# ReportLab (cercle, carré, triangle, losange, étoile) et non écrites en Unicode.
FORMES_INTENSITE = {
    'endurance': ('cercle', '#2E7D32'),      # cercle plein vert
    'seuil': ('carre', '#E65100'),           # carré plein orange
    'intense': ('triangle', '#C62828'),      # triangle plein rouge
    'recuperation': ('losange', '#1565C0'),  # losange plein bleu
    'course': ('etoile', '#6A1B9A'),         # étoile pleine violette
    'repos': ('cercle', '#9E9E9E'),          # cercle gris
}

# Alias historique
SYMBOLES_INTENSITE = FORMES_INTENSITE
SYMBOLE_FONT = 'Helvetica'
TAILLE_SYMBOLE = 9  # points


def _symbole_intensite(difficulte):
    """Retourne le couple (forme, couleur) d'un niveau d'intensité."""
    return FORMES_INTENSITE.get(difficulte, FORMES_INTENSITE['endurance'])


class FormeIntensite(Flowable):
    """Symbole d'intensité dessiné avec des primitives ReportLab.

    Le même Flowable est utilisé dans la légende et dans la colonne
    Intensité du tableau : la forme et la couleur sont donc identiques.
    """

    def __init__(self, forme, couleur, taille=TAILLE_SYMBOLE):
        Flowable.__init__(self)
        self.forme = forme
        self.couleur = colors.HexColor(couleur)
        self.taille = taille
        self.width = taille
        self.height = taille

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = self.taille
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        taille = self.taille
        centre_x = self.width / 2.0
        centre_y = taille / 2.0
        rayon = taille / 2.0
        canvas.setFillColor(self.couleur)
        canvas.setStrokeColor(self.couleur)

        if self.forme == 'cercle':
            canvas.circle(centre_x, centre_y, rayon, stroke=0, fill=1)
        elif self.forme == 'carre':
            canvas.rect(centre_x - rayon, centre_y - rayon, taille, taille, stroke=0, fill=1)
        elif self.forme == 'triangle':
            chemin = canvas.beginPath()
            chemin.moveTo(centre_x, centre_y + rayon)
            chemin.lineTo(centre_x - rayon, centre_y - rayon)
            chemin.lineTo(centre_x + rayon, centre_y - rayon)
            chemin.close()
            canvas.drawPath(chemin, stroke=0, fill=1)
        elif self.forme == 'losange':
            chemin = canvas.beginPath()
            chemin.moveTo(centre_x, centre_y + rayon)
            chemin.lineTo(centre_x + rayon, centre_y)
            chemin.lineTo(centre_x, centre_y - rayon)
            chemin.lineTo(centre_x - rayon, centre_y)
            chemin.close()
            canvas.drawPath(chemin, stroke=0, fill=1)
        elif self.forme == 'etoile':
            points = []
            for index in range(10):
                angle = math.pi / 2 + index * math.pi / 5
                distance = rayon if index % 2 == 0 else rayon * 0.42
                points.append((
                    centre_x + distance * math.cos(angle),
                    centre_y + distance * math.sin(angle),
                ))
            chemin = canvas.beginPath()
            chemin.moveTo(*points[0])
            for point in points[1:]:
                chemin.lineTo(*point)
            chemin.close()
            canvas.drawPath(chemin, stroke=0, fill=1)


class FormeCoche(Flowable):
    """Coche verte dessinée (primitives ReportLab, pas un caractère Unicode)."""

    def __init__(self, taille=8, couleur='#2E7D32'):
        Flowable.__init__(self)
        self.taille = taille
        self.couleur = colors.HexColor(couleur)
        self.width = taille
        self.height = taille

    def wrap(self, availWidth, availHeight):
        self.width = self.taille
        self.height = self.taille
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        taille = self.taille
        canvas.setStrokeColor(self.couleur)
        canvas.setLineWidth(1.4)
        chemin = canvas.beginPath()
        chemin.moveTo(taille * 0.12, taille * 0.52)
        chemin.lineTo(taille * 0.40, taille * 0.20)
        chemin.lineTo(taille * 0.90, taille * 0.80)
        canvas.drawPath(chemin, stroke=1, fill=0)


# CORRIGÉ: Remplacer les émojis par des caractères simples dans les données
EMOJI_TO_SYMBOL = {
    '🟩': '[END]',
    '🟨': '[SEUIL]',
    '🟥': '[INTENSE]',
    '🟦': '[RECUP]',
    '⭐': '[COURSE]',
    '⬜': '[REPOS]',
    '🟢': '[NORMAL]',
    '🟡': '[CHARGE]',
    '🔴': '[DURE]',
    '⚪': '[RECUP]',
    '🔵': '[AFFUTAGE]',
    '🟤': '[EXCEPTIONNELLE]',
    '⚠️': '[!]',
    '⚠': '[!]',
    '✅': '[OK]',
    '❌': '[ERREUR]',
    '🏁': '[COURSE]',
    '🏆': '[SPORT]',
    '📅': '[DATE]',
}


def replace_emojis(text):
    """Remplace les émojis par des caractères simples."""
    if not text:
        return text
    for emoji, symbol in EMOJI_TO_SYMBOL.items():
        text = text.replace(emoji, symbol)
    return text


# ---- PALETTE PASTEL PAR TYPE DE SÉANCE ----
# Fonds très clairs, texte noir, lisibles à l'impression.
COULEUR_ENDURANCE = colors.HexColor('#F5F5F5')       # neutre très clair
COULEUR_INTENSE = colors.HexColor('#FBE3E3')          # rouge/rose très clair (VMA, VC, Test)
COULEUR_SEUIL = colors.HexColor('#FCE8D5')            # orange très clair
COULEUR_FARTLEK = colors.HexColor('#FFF6CC')          # jaune très clair
COULEUR_LONGUE = colors.HexColor('#DCEBF7')           # bleu très clair (sortie longue)
COULEUR_COMPETITION = colors.HexColor('#EADCF5')      # violet très clair
COULEUR_RENFORCEMENT = colors.HexColor('#DDF2DD')     # vert très clair

# ---- CONTRAINTES : priorité visuelle ----
COULEUR_CONTRAINTE_NORMALE = colors.HexColor('#FFF9C4')    # jaune pâle
COULEUR_CONTRAINTE_IMPORTANTE = colors.HexColor('#F8D7DA')  # rouge pâle

# ---- WEEK-END : repérage visuel (sans refaire la charte graphique) ----
COULEUR_WEEKEND = colors.HexColor('#E8F0FE')             # surlignage jour week-end
COULEUR_SEPARATEUR_WEEKEND = colors.HexColor('#1F4E79')  # trait vendredi/samedi
JOURS_WEEKEND = ('Samedi', 'Dimanche')

# ---- TABLEAU ----
COULEUR_ENTETE_TABLE = colors.HexColor('#E6E6E6')   # gris clair
COULEUR_COLONNE_SEMAINE = colors.HexColor('#EFEFEF')  # colonne Semaine neutre
COULEUR_BORDURE = colors.HexColor('#9E9E9E')
PADDING_MIN = 2            # points, padding vertical minimal des lignes
COULEUR_LEGENDE_HAUTEUR = 24  # points, hauteur des cases de la légende couleurs
COULEUR_TITRE_SECTION = colors.HexColor('#1F4E79')  # bleu foncé
COULEUR_CADRE = colors.HexColor('#F7F7F7')          # fond de cadre très léger


# ---- CONTENU PÉDAGOGIQUE (dernière page) ----
TITRE_PEDAGOGIQUE = "COMPRENDRE LES LÉGENDES DU PLAN"
INTRO_PEDAGOGIQUE = (
    "Ce plan utilise deux codes complémentaires pour vous aider à lire rapidement "
    "chaque séance : la couleur de la case indique le type de séance et le symbole "
    "indique l'intensité ou la nature de la journée."
)

# (label, couleur, explication) — les couleurs sont les constantes du PDF.
TYPES_SEANCE = [
    ('Endurance', COULEUR_ENDURANCE,
     "Travail aérobie principalement en endurance (Z1/Z2)."),
    ('Intensité', COULEUR_INTENSE,
     "Travail de haute intensité : VMA, VC, VO2max, efforts courts/intenses, etc."),
    ('Seuil', COULEUR_SEUIL,
     "Travail autour du seuil physiologique, notamment SV1/SV2 selon la séance."),
    ('Fartlek', COULEUR_FARTLEK,
     "Alternance structurée ou libre d'allures et d'intensités."),
    ('Sortie longue', COULEUR_LONGUE,
     "Séance caractérisée principalement par sa durée et son objectif "
     "d'endurance prolongée."),
    ('Compétition', COULEUR_COMPETITION,
     "Course, triathlon, épreuve ou compétition intégrée dans le plan."),
    ('Renforcement', COULEUR_RENFORCEMENT,
     "Travail de renforcement musculaire (gainage, PPG, musculation, etc.)."),
]

EXPLICATIONS_INTENSITE = {
    'endurance': "Journée à dominante endurance / faible sollicitation.",
    'seuil': "Journée avec une sollicitation de type seuil.",
    'intense': "Journée avec une sollicitation importante / séance intense.",
    'recuperation': "Journée ou séance à dominante récupération.",
    'course': "Journée de compétition ou course.",
    'repos': "Pas de séance sportive planifiée.",
}

NOMS_FORMES = {
    'cercle': 'cercle', 'carre': 'carré', 'triangle': 'triangle',
    'losange': 'losange', 'etoile': 'étoile',
}
NOMS_COULEURS = {
    '#2E7D32': 'vert', '#E65100': 'orange', '#C62828': 'rouge',
    '#1565C0': 'bleu', '#6A1B9A': 'violet', '#9E9E9E': 'gris',
}
NOMS_NATURE = {
    'endurance': 'Endurance', 'seuil': 'Seuil', 'intense': 'Intense',
    'recuperation': 'Récupération', 'course': 'Course', 'repos': 'Repos',
}

REPERES_ATHLETE = [
    "Les couleurs et les symboles sont deux informations complémentaires.",
    "Une sortie longue est généralement une séance d'endurance (cercle vert).",
    "Une séance de seuil peut apparaître avec un carré orange.",
    "Les jours de repos sont toujours visibles dans le plan.",
    "Les compétitions sont repérées par une étoile violette.",
    "Le plan s'adapte à vos disponibilités et à votre profil.",
    "En cas de contrainte, un indicateur [!n] est affiché dans le tableau.",
    "N'hésitez pas à contacter votre entraîneur si vous avez des questions.",
]


def _indices_debut_week_end(jours_affichage):
    """Indices des lignes où débute le week-end (premier samedi)."""
    return [
        index for index, jour in enumerate(jours_affichage)
        if jour == 'Samedi'
    ]


def _commandes_separateur_weekend(indices):
    """Trait horizontal épais séparant vendredi de samedi."""
    return [
        ('LINEABOVE', (0, index), (-1, index), 1.2, COULEUR_SEPARATEUR_WEEKEND)
        for index in indices
    ]


def _commandes_surlignage_weekend(indices):
    """Surligne la colonne Jour des samedis et dimanches."""
    commandes = []
    for index in indices:
        commandes.append(('BACKGROUND', (1, index), (1, index), COULEUR_WEEKEND))
        commandes.append(('FONTNAME', (1, index), (1, index), 'Helvetica-Bold'))
    return commandes


def _couleur_seance(seance: Dict):
    """Retourne la couleur pastel associée au type de séance (texte noir conservé)."""
    discipline = seance.get('discipline', '')
    if discipline == 'Renforcement':
        return COULEUR_RENFORCEMENT
    if discipline == 'Course' or seance.get('difficulte') == 'course':
        return COULEUR_COMPETITION

    type_lower = str(seance.get('type', '')).lower()
    if 'fartlek' in type_lower:
        return COULEUR_FARTLEK
    if 'vma' in type_lower or 'vc' in type_lower or 'test' in type_lower:
        return COULEUR_INTENSE
    if 'seuil' in type_lower:
        return COULEUR_SEUIL
    if 'sortie longue' in type_lower:
        return COULEUR_LONGUE
    if any(mot in type_lower for mot in (
        'renforcement', 'pliométrie', 'pliometrie',
        'gainage', 'excentrique'
    )):
        return COULEUR_RENFORCEMENT
    if any(mot in type_lower for mot in ('compétition', 'competition', 'objectif')):
        return COULEUR_COMPETITION

    difficulte = seance.get('difficulte', 'endurance')
    if difficulte == 'intense':
        return COULEUR_INTENSE
    if difficulte == 'seuil':
        return COULEUR_SEUIL
    if difficulte == 'course':
        return COULEUR_COMPETITION
    return COULEUR_ENDURANCE


def _couleur_contrainte(contrainte: Dict):
    """Jaune pâle pour une contrainte normale, rouge pâle pour une contrainte importante."""
    capacite = contrainte.get('capacite_normale', 1)
    if isinstance(capacite, int) and capacite >= 2:
        return COULEUR_CONTRAINTE_IMPORTANTE
    return COULEUR_CONTRAINTE_NORMALE


def _commandes_fond(couleurs_type, contraintes_lignes):
    """Commandes de fond : couleur de type sur toute la ligne, puis contrainte prioritaire.

    La contrainte est appliquée après la couleur de type, uniquement sur la
    cellule Discipline, afin que les deux informations restent visibles.
    """
    commandes = []
    for index_ligne, couleur in couleurs_type:
        commandes.append(('BACKGROUND', (0, index_ligne), (-1, index_ligne), couleur))
    for index_ligne, couleur in contraintes_lignes:
        commandes.append(('BACKGROUND', (3, index_ligne), (3, index_ligne), couleur))
        commandes.append(('TEXTCOLOR', (3, index_ligne), (3, index_ligne), colors.darkred))
        commandes.append(('FONTNAME', (3, index_ligne), (3, index_ligne), 'Helvetica-Bold'))
    return commandes


def _largeurs_proportionnelles(labels, largeur_dispo, font, size, marge):
    """Répartit la largeur disponible selon la longueur du texte des colonnes."""
    natures = [stringWidth(str(label), font, size) + marge for label in labels]
    total = sum(natures)
    if total <= 0:
        return [largeur_dispo / max(1, len(labels))] * len(labels)
    facteur = largeur_dispo / total
    return [valeur * facteur for valeur in natures]


def _tableau_legende_couleurs(style, largeur_table=None):
    """Légende colorée des types de séance sur UNE SEULE ligne."""
    entrees = [
        ('Endurance', COULEUR_ENDURANCE),
        ('Intensité', COULEUR_INTENSE),
        ('Seuil', COULEUR_SEUIL),
        ('Fartlek', COULEUR_FARTLEK),
        ('Sortie longue', COULEUR_LONGUE),
        ('Compétition', COULEUR_COMPETITION),
        ('Renforcement', COULEUR_RENFORCEMENT),
    ]
    labels = [label for label, _ in entrees]
    largeur_table = largeur_table or (270 * mm)
    largeurs = _largeurs_proportionnelles(labels, largeur_table, 'Helvetica', 9, 10 * mm)
    table = Table(
        [[Paragraph(label, style) for label, _ in entrees]],
        colWidths=largeurs, rowHeights=[COULEUR_LEGENDE_HAUTEUR], hAlign='CENTER',
    )
    commandes = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]
    for index, (_, couleur) in enumerate(entrees):
        commandes.append(('BACKGROUND', (index, 0), (index, 0), couleur))
    table.setStyle(TableStyle(commandes))
    return table


def _bloc_legende_intensite(style, largeur_table=None):
    """Légende des intensités sur UNE SEULE ligne, avec formes dessinées."""
    largeur_table = largeur_table or (270 * mm)
    prefixe = 'Légende :'
    cellules = [Paragraph(prefixe, style)]
    largeurs = [stringWidth(prefixe, 'Helvetica', 9) + 4 * mm]
    for difficulte, label in LEGENDE_INTENSITE:
        forme, couleur = _symbole_intensite(difficulte)
        cellules.append(FormeIntensite(forme, couleur))
        largeurs.append(TAILLE_SYMBOLE + 5 * mm)
        cellules.append(Paragraph(label, style))
        largeurs.append(stringWidth(label, 'Helvetica', 9) + 7 * mm)

    total = sum(largeurs)
    if total > largeur_table:
        facteur = largeur_table / total
        largeurs = [valeur * facteur for valeur in largeurs]

    table = Table([cellules], colWidths=largeurs, hAlign='CENTER')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return table


# ---- ORGANISATION PAR SEMAINES (lundi -> dimanche) ----
# Le premier jour de la semaine est le lundi : la séparation de semaine est
# donc placée AVANT le lundi (et non avant le samedi).
TAILLE_PAGE_SEMAINES = 2
COULEUR_SEPARATEUR_SEMAINE = colors.HexColor('#000000')


def _indices_debut_semaine(jours_affichage):
    """Indices des lignes de lundi, début de chaque semaine."""
    return [
        index for index, jour in enumerate(jours_affichage)
        if jour == 'Lundi'
    ]


def _commandes_separateur_semaine(indices):
    """Trait horizontal fort au-dessus de chaque lundi (nouvelle semaine)."""
    return [
        ('LINEABOVE', (0, index), (-1, index), 1.5, COULEUR_SEPARATEUR_SEMAINE)
        for index in indices
    ]


def _grouper_semaines_par_page(semaines, taille=TAILLE_PAGE_SEMAINES):
    """Regroupe les semaines par page (2 semaines maximum par page)."""
    return [
        list(semaines[index:index + taille])
        for index in range(0, len(semaines), taille)
    ]


def _date_debut_semaine(semaine):
    """Lundi d'une semaine, avec repli sur la première date disponible."""
    if semaine.get('date_debut'):
        return semaine['date_debut']
    for jour in semaine.get('jours', []):
        if jour.get('date'):
            return jour['date']
    return ''


def _date_fin_semaine(semaine):
    """Dimanche d'une semaine, avec repli sur la dernière date disponible."""
    if semaine.get('date_fin'):
        return semaine['date_fin']
    for jour in reversed(semaine.get('jours', [])):
        if jour.get('date'):
            return jour['date']
    return ''


def _periode_groupe(groupe):
    """Période exacte des semaines affichées : Du JJ/MM/AAAA au JJ/MM/AAAA."""
    debut = _format_date_for_user(_date_debut_semaine(groupe[0]))
    fin = _format_date_for_user(_date_fin_semaine(groupe[-1]))
    return f"Du {debut} au {fin}"


def _collecter_contraintes(plan):
    """Numérote les messages de contrainte dans l'ordre d'apparition."""
    contraintes = []
    index_par_message = {}
    for semaine in plan.get('semaines', []):
        for jour in semaine.get('jours', []):
            contrainte = jour.get('contrainte', {})
            if not contrainte.get('active'):
                continue
            message = contrainte.get('message', '')
            if message not in index_par_message:
                contraintes.append((len(contraintes) + 1, message))
                index_par_message[message] = len(contraintes)
    return contraintes, index_par_message


def _creer_styles_pdf():
    """Styles typographiques du PDF (titres, table, légendes, période)."""
    styles = getSampleStyleSheet()
    return {
        'titre': ParagraphStyle(
            'Titre', parent=styles['Heading1'], fontName='Helvetica-Bold',
            fontSize=17, leading=21, alignment=TA_CENTER, spaceAfter=4,
        ),
        'sous_titre': ParagraphStyle(
            'SousTitre', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=4,
        ),
        'normal': ParagraphStyle(
            'NormalPdf', parent=styles['Normal'], fontName='Helvetica',
            fontSize=9, leading=11, spaceAfter=2,
        ),
        'legende': ParagraphStyle(
            'Legende', parent=styles['Normal'], fontName='Helvetica',
            fontSize=9, leading=11, alignment=TA_CENTER,
        ),
        'small': ParagraphStyle(
            'Small', parent=styles['Normal'], fontName='Helvetica',
            fontSize=8.5, leading=10.5, alignment=TA_CENTER,
        ),
        'small_bold': ParagraphStyle(
            'SmallBold', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=9, leading=11, alignment=TA_CENTER,
        ),
        'periode': ParagraphStyle(
            'Periode', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=11, leading=14, alignment=TA_CENTER, spaceBefore=10,
        ),
        'pedago_titre': ParagraphStyle(
            'PedagoTitre', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=14, leading=17, alignment=TA_CENTER,
            textColor=COULEUR_TITRE_SECTION, spaceBefore=4, spaceAfter=2,
        ),
        'intro': ParagraphStyle(
            'Intro', parent=styles['Normal'], fontName='Helvetica',
            fontSize=9, leading=11.5, alignment=TA_CENTER,
        ),
        'section': ParagraphStyle(
            'Section', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=11, leading=13, textColor=COULEUR_TITRE_SECTION,
            spaceBefore=6, spaceAfter=1,
        ),
        'case_titre': ParagraphStyle(
            'CaseTitre', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=8, leading=9.5, alignment=TA_CENTER,
        ),
        'case_texte': ParagraphStyle(
            'CaseTexte', parent=styles['Normal'], fontName='Helvetica',
            fontSize=6.5, leading=8, alignment=TA_CENTER,
        ),
        'puce': ParagraphStyle(
            'Puce', parent=styles['Normal'], fontName='Helvetica',
            fontSize=8.5, leading=10.5,
        ),
        'footer': ParagraphStyle(
            'Footer', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=10, leading=12, alignment=TA_CENTER,
            textColor=COULEUR_TITRE_SECTION,
        ),
    }


def _bloc_entete(plan, contraintes_pdf, styles, largeur_table=None):
    """Entête répété sur chaque page : titre, périodes, légendes, contraintes."""
    bloc = [
        Paragraph(f"Plan d'entraînement : {plan.get('athlete', '')}", styles['titre']),
        Paragraph(
            "Du "
            f"{_format_date_for_user(plan.get('date_debut', ''))} au "
            f"{_format_date_for_user(plan.get('date_objectif', ''))}",
            styles['sous_titre'],
        ),
        Spacer(1, 6),
        _bloc_legende_intensite(styles['legende'], largeur_table),
        Spacer(1, 6),
        Paragraph("Couleurs des séances :", styles['normal']),
        Spacer(1, 2),
        _tableau_legende_couleurs(styles['legende'], largeur_table),
    ]
    if contraintes_pdf:
        contraintes_txt = "Contraintes de planification : "
        contraintes_txt += "  ".join(
            f"[!{indice}] {message}" for indice, message in contraintes_pdf
        )
        bloc.append(Spacer(1, 4))
        bloc.append(Paragraph(contraintes_txt, styles['normal']))
    bloc.append(Spacer(1, 6))
    return bloc


def _hauteur_flowables(flowables, largeur, hauteur):
    """Hauteur totale approximative d'une liste de Flowables (paddings inclus)."""
    total = 0
    for flowable in flowables:
        space_before = flowable.getSpaceBefore() if hasattr(flowable, 'getSpaceBefore') else 0
        space_after = flowable.getSpaceAfter() if hasattr(flowable, 'getSpaceAfter') else 0
        _, hauteur_flowable = flowable.wrap(largeur, hauteur)
        total += space_before + hauteur_flowable + space_after
    return total


def _tableau_semaines(groupe, index_par_message, small_style, header_style=None):
    """Construit le tableau d'une page (2 semaines) avec ses commandes de style."""
    header_style = header_style or small_style
    header = ["Semaine", "Jour", "Date", "Discipline", "Type", "Détails", "Durée", "Intensité"]
    rows = [[Paragraph(h, header_style) for h in header]]
    couleurs_type = []
    contraintes_lignes = []
    lignes_weekend = []
    lignes_semaine = []
    disciplines_sport = ('CAP', 'Vélo', 'Velo', 'Natation')

    for semaine in groupe:
        lignes_semaine.append(len(rows))
        num_affichage = semaine.get('num_affichage', '')
        emoji = replace_emojis(semaine.get('emoji', '●'))
        semaine_label = f"{emoji}S-{num_affichage:02d}"

        for jour in semaine.get('jours', []):
            jour_label = jour.get('jour', '')
            contrainte = jour.get('contrainte', {})
            contrainte_active = bool(contrainte.get('active'))
            indice_contrainte = None
            if contrainte_active:
                indice_contrainte = index_par_message.get(contrainte.get('message', ''))

            seances_jour = jour.get('seances', [])
            if not seances_jour:
                seances_jour = [{
                    'discipline': 'Repos', 'type': 'Repos',
                    'details': 'Repos', 'duree': 0, 'difficulte': 'repos'
                }]

            # Les journées de repos sont affichées comme les autres : aucun
            # jour ne doit disparaître du PDF.
            for idx, seance in enumerate(seances_jour):
                details = replace_emojis(seance.get('details', ''))
                forme, couleur = _symbole_intensite(seance.get('difficulte', 'endurance'))
                intensite = FormeIntensite(forme, couleur)
                aff_jour = jour_label if idx == 0 else '*'

                discipline_label = seance.get('discipline', '')
                if contrainte_active and seance.get('discipline') in disciplines_sport:
                    discipline_label = f"{discipline_label} [!{indice_contrainte}]"

                index_ligne = len(rows)
                rows.append([
                    Paragraph(semaine_label, small_style),
                    Paragraph(aff_jour, small_style),
                    Paragraph(_format_date_for_user(jour.get('date', '')), small_style),
                    Paragraph(discipline_label, small_style),
                    Paragraph(seance.get('type', ''), small_style),
                    Paragraph(details, small_style),
                    Paragraph(f"{seance.get('duree', 0)} min", small_style),
                    intensite,
                ])
                if idx == 0 and jour_label in JOURS_WEEKEND:
                    lignes_weekend.append(index_ligne)
                couleurs_type.append((index_ligne, _couleur_seance(seance)))
                if contrainte_active and seance.get('discipline') in disciplines_sport:
                    contraintes_lignes.append(
                        (index_ligne, _couleur_contrainte(contrainte))
                    )

    return rows, couleurs_type, contraintes_lignes, lignes_weekend, lignes_semaine


# Proportions de colonnes demandées (normalisées sur leur somme).
PROPORTIONS_COLONNES = [12, 8, 10, 11, 14, 35, 7, 7]
LARGEUR_REFERENCE = 277 * mm


def _calculer_largeurs(largeur_table):
    total = sum(PROPORTIONS_COLONNES)
    return [largeur_table * proportion / total for proportion in PROPORTIONS_COLONNES]


LARGEURS_COLONNES = _calculer_largeurs(LARGEUR_REFERENCE)


def _spans_semaines(lignes_semaine, nombre_lignes):
    """Fusionne verticalement la colonne Semaine pour chaque semaine."""
    spans = []
    for index, debut in enumerate(lignes_semaine):
        fin = (lignes_semaine[index + 1] - 1) if index + 1 < len(lignes_semaine) else nombre_lignes - 1
        if fin > debut:
            spans.append(('SPAN', (0, debut), (0, fin)))
    return spans


def _style_tableau(rows, largeurs, couleurs_type, contraintes_lignes,
                   lignes_weekend, lignes_semaine, padding):
    """Construit la Table stylée d'une page (séparateurs, couleurs, fusion)."""
    table = Table(rows, colWidths=largeurs, repeatRows=1, hAlign='CENTER')
    style_cmds = [
        ('GRID', (0, 0), (-1, -1), 0.4, COULEUR_BORDURE),
        ('BACKGROUND', (0, 0), (-1, 0), COULEUR_ENTETE_TABLE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('TOPPADDING', (0, 0), (-1, 0), padding + 2),
        ('BOTTOMPADDING', (0, 0), (-1, 0), padding + 2),
        ('TOPPADDING', (0, 1), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 1), (-1, -1), padding),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]
    style_cmds.extend(_commandes_fond(couleurs_type, contraintes_lignes))
    # Colonne Semaine neutre (le fond de type ne doit pas la colorer).
    style_cmds.append(('BACKGROUND', (0, 1), (0, -1), COULEUR_COLONNE_SEMAINE))
    style_cmds.extend(_spans_semaines(lignes_semaine, len(rows)))
    style_cmds.extend(_commandes_separateur_semaine(lignes_semaine))
    style_cmds.extend(_commandes_surlignage_weekend(lignes_weekend))
    table.setStyle(TableStyle(style_cmds))
    return table


TAILLES_TEXTE_TABLEAU = (8.5, 8.2, 8.0, 7.7, 7.5, 7.2, 7.0)


def _styles_tableau(taille):
    """Styles de corps du tableau pour une taille de police donnée."""
    base = getSampleStyleSheet()['Normal']
    leading = taille * 1.25
    small = ParagraphStyle(
        'SmallT', parent=base, fontName='Helvetica',
        fontSize=taille, leading=leading, alignment=TA_CENTER,
    )
    small_bold = ParagraphStyle(
        'SmallTB', parent=base, fontName='Helvetica-Bold',
        fontSize=taille + 0.5, leading=leading, alignment=TA_CENTER,
    )
    return small, small_bold


def _construire_tableau(groupe, index_par_message, styles, largeur_table=None,
                        hauteur_disponible=None):
    """Tableau centré qui remplit la hauteur disponible sans dépasser la page.

    La taille de police est réduite par paliers uniquement si la version
    lisible ne tient pas (cas le plus chargé). Le padding est ensuite ajusté
    pour remplir l'espace restant.
    """
    largeur_table = largeur_table or (sum(LARGEURS_COLONNES))
    largeurs = _calculer_largeurs(largeur_table)

    tailles = TAILLES_TEXTE_TABLEAU if hauteur_disponible else (TAILLES_TEXTE_TABLEAU[0],)
    resultat = None
    for taille in tailles:
        small, small_bold = _styles_tableau(taille)
        rows, couleurs_type, contraintes_lignes, lignes_weekend, lignes_semaine = (
            _tableau_semaines(groupe, index_par_message, small, small_bold)
        )
        table = _style_tableau(
            rows, largeurs, couleurs_type, contraintes_lignes,
            lignes_weekend, lignes_semaine, PADDING_MIN,
        )
        _, hauteur_base = table.wrap(largeur_table, hauteur_disponible or (10 ** 6))
        resultat = (
            rows, couleurs_type, contraintes_lignes, lignes_weekend,
            lignes_semaine, table, hauteur_base,
        )
        if (hauteur_disponible is None
                or hauteur_base <= hauteur_disponible - ECART_TABLEAU_PERIODE):
            break

    (rows, couleurs_type, contraintes_lignes, lignes_weekend,
     lignes_semaine, table, hauteur_base) = resultat
    if hauteur_disponible is None or not rows:
        return table

    # Remplissage : viser l'espace disponible en gardant un écart avant la
    # période, sans jamais dépasser la hauteur disponible.
    cible = min(hauteur_disponible, max(hauteur_base, hauteur_disponible - ECART_TABLEAU_PERIODE))
    padding = PADDING_MIN
    hauteur_courante = hauteur_base
    for _ in range(8):
        if hauteur_courante >= cible:
            break
        ajustement = (cible - hauteur_courante) / (2.0 * len(rows))
        if ajustement < 0.1:
            break
        candidat_padding = padding + ajustement
        candidat = _style_tableau(
            rows, largeurs, couleurs_type, contraintes_lignes,
            lignes_weekend, lignes_semaine, candidat_padding,
        )
        _, hauteur_candidat = candidat.wrap(largeur_table, hauteur_disponible)
        if hauteur_candidat > hauteur_disponible:
            break
        table, padding, hauteur_courante = candidat, candidat_padding, hauteur_candidat
    return table


class _PlanCanvas(pdfcanvas.Canvas):
    """Canvas qui ajoute « Page X / Y » sur chaque page (2e passe)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for etat in self._saved_page_states:
            self.__dict__.update(etat)
            self._dessiner_numero_page(total)
            super().showPage()
        super().save()

    def _dessiner_numero_page(self, total):
        largeur, _ = self._pagesize
        self.setFont('Helvetica', 9)
        self.setFillColor(colors.HexColor('#444444'))
        self.drawRightString(largeur - 12 * mm, 8 * mm, f"Page {self._pageNumber} / {total}")


# Marges de la page (paysage A4).
MARGE_GAUCHE = 10 * mm
MARGE_DROITE = 10 * mm
MARGE_HAUT = 10 * mm
MARGE_BAS = 15 * mm
ECART_TABLEAU_PERIODE = 8 * mm


def _label_type_couleur(couleur):
    """Retrouve le libellé d'un type de séance à partir de sa couleur."""
    for label, couleur_type, _ in TYPES_SEANCE:
        if couleur_type == couleur:
            return label
    return 'Endurance'


def _construire_exemple(semaine, jour, seance):
    """Construit l'exemple de ligne à partir d'une séance réelle du plan."""
    num_affichage = semaine.get('num_affichage', '')
    emoji = replace_emojis(semaine.get('emoji', ''))
    if isinstance(num_affichage, int):
        semaine_label = f"{emoji}S-{num_affichage:02d}"
    else:
        semaine_label = f"{emoji}S-{num_affichage}"
    return {
        'semaine_label': semaine_label,
        'jour': jour.get('jour', ''),
        'date': _format_date_for_user(jour.get('date', '')),
        'discipline': seance.get('discipline', ''),
        'type': seance.get('type', ''),
        'details': replace_emojis(seance.get('details', '')),
        'duree': seance.get('duree', 0),
        'difficulte': seance.get('difficulte', 'endurance'),
        'couleur': _couleur_seance(seance),
    }


def _exemple_synthetique():
    """Exemple de repli, uniquement si aucune séance réelle n'est disponible."""
    return {
        'semaine_label': 'S-01', 'jour': 'Mardi', 'date': '01/08/2026',
        'discipline': 'CAP', 'type': 'VC', 'details': 'VC (49 min)',
        'duree': 49, 'difficulte': 'intense', 'couleur': COULEUR_INTENSE,
    }


def _exemple_depuis_plan(plan):
    """Sélectionne une ligne réelle du plan (intensité de préférence)."""
    criteres = (
        lambda s: _couleur_seance(s) == COULEUR_INTENSE and s.get('difficulte') == 'intense',
        lambda s: _couleur_seance(s) == COULEUR_INTENSE,
        lambda s: s.get('difficulte') == 'intense',
        lambda s: True,
    )
    for critere in criteres:
        for semaine in plan.get('semaines', []):
            for jour in semaine.get('jours', []):
                for seance in jour.get('seances', []):
                    if seance.get('discipline') == 'Repos':
                        continue
                    if critere(seance):
                        return _construire_exemple(semaine, jour, seance)
    return _exemple_synthetique()


def _tableau_types_seance(styles, largeur):
    """Section 1 : les 7 types de séance en cases colorées."""
    largeurs = [largeur / len(TYPES_SEANCE)] * len(TYPES_SEANCE)
    titres = [Paragraph(label.upper(), styles['case_titre']) for label, _, _ in TYPES_SEANCE]
    textes = [Paragraph(texte, styles['case_texte']) for _, _, texte in TYPES_SEANCE]
    table = Table([titres, textes], colWidths=largeurs, hAlign='CENTER')
    commandes = [
        ('GRID', (0, 0), (-1, -1), 0.5, COULEUR_BORDURE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]
    for index, (_, couleur, _) in enumerate(TYPES_SEANCE):
        commandes.append(('BACKGROUND', (index, 0), (index, 0), couleur))
    table.setStyle(TableStyle(commandes))
    return table


def _tableau_intensites(styles, largeur):
    """Section 2 : les 6 symboles d'intensité (formes dessinées)."""
    largeurs = [largeur / len(LEGENDE_INTENSITE)] * len(LEGENDE_INTENSITE)
    formes = []
    libelles = []
    textes = []
    for difficulte, label in LEGENDE_INTENSITE:
        forme, couleur = _symbole_intensite(difficulte)
        formes.append(FormeIntensite(forme, couleur, taille=12))
        libelles.append(Paragraph(label.upper(), styles['case_titre']))
        textes.append(Paragraph(EXPLICATIONS_INTENSITE.get(difficulte, ''), styles['case_texte']))
    table = Table([formes, libelles, textes], colWidths=largeurs, hAlign='CENTER')
    commandes = [
        ('GRID', (0, 0), (-1, -1), 0.5, COULEUR_BORDURE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 0), (-1, 0), COULEUR_CADRE),
    ]
    table.setStyle(TableStyle(commandes))
    return table


def _tableau_exemple(exemple, styles, largeur):
    """Section 3 : reproduction d'une ligne réelle du tableau."""
    header = ["Semaine", "Jour", "Date", "Discipline", "Type", "Détails", "Durée", "Intensité"]
    forme, couleur = _symbole_intensite(exemple['difficulte'])
    ligne = [
        Paragraph(exemple['semaine_label'], styles['small']),
        Paragraph(exemple['jour'], styles['small']),
        Paragraph(exemple['date'], styles['small']),
        Paragraph(exemple['discipline'], styles['small']),
        Paragraph(exemple['type'], styles['small']),
        Paragraph(exemple['details'], styles['small']),
        Paragraph(f"{exemple['duree']} min", styles['small']),
        FormeIntensite(forme, couleur, taille=11),
    ]
    table = Table(
        [[Paragraph(h, styles['small_bold']) for h in header], ligne],
        colWidths=_calculer_largeurs(largeur), hAlign='CENTER',
    )
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, COULEUR_BORDURE),
        ('BACKGROUND', (0, 0), (-1, 0), COULEUR_ENTETE_TABLE),
        ('BACKGROUND', (0, 1), (-1, 1), exemple['couleur']),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table


def _explications_exemple(exemple, styles, largeur):
    """Deux encadrés expliquant la couleur puis le symbole de l'exemple."""
    couleur_label = _label_type_couleur(exemple['couleur'])
    forme, couleur_hex = _symbole_intensite(exemple['difficulte'])
    forme_nom = NOMS_FORMES.get(forme, forme)
    couleur_nom = NOMS_COULEURS.get(couleur_hex, '')
    nature = NOMS_NATURE.get(exemple['difficulte'], 'Endurance')
    gauche = Paragraph(
        f"La couleur de la case indique que le type de séance est « {couleur_label} ».",
        styles['puce'],
    )
    droite = Paragraph(
        f"Le {forme_nom} {couleur_nom} indique que cette journée est considérée "
        f"comme « {nature} ».",
        styles['puce'],
    )
    demi = (largeur - 6 * mm) / 2.0
    table = Table([[gauche, droite]], colWidths=[demi, demi], hAlign='CENTER')
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 0.5, COULEUR_BORDURE),
        ('BOX', (1, 0), (1, 0), 0.5, COULEUR_BORDURE),
        ('BACKGROUND', (0, 0), (-1, -1), COULEUR_CADRE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table


def _tableau_reperes(styles, largeur):
    """Section 4 : repères de l'athlète, sur deux colonnes cochées."""
    colonne_texte = (largeur - 2 * (8 * mm)) / 2.0
    largeurs = [8 * mm, colonne_texte, 8 * mm, colonne_texte]
    lignes = []
    for index in range(0, len(REPERES_ATHLETE), 2):
        paire = REPERES_ATHLETE[index:index + 2]
        ligne = []
        for texte in paire:
            ligne.append(FormeCoche())
            ligne.append(Paragraph(texte, styles['puce']))
        while len(ligne) < 4:
            ligne.append('')
        lignes.append(ligne)
    table = Table(lignes, colWidths=largeurs, hAlign='CENTER')
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return table


def _bloc_page_pedagogique(plan, styles, largeur):
    """Dernière page : comprendre les couleurs et les symboles du plan."""
    exemple = _exemple_depuis_plan(plan)
    return [
        Paragraph(f"Plan d'entraînement : {plan.get('athlete', '')}", styles['titre']),
        Paragraph(
            "Du "
            f"{_format_date_for_user(plan.get('date_debut', ''))} au "
            f"{_format_date_for_user(plan.get('date_objectif', ''))}",
            styles['sous_titre'],
        ),
        Spacer(1, 4),
        Paragraph(TITRE_PEDAGOGIQUE, styles['pedago_titre']),
        Paragraph(INTRO_PEDAGOGIQUE, styles['intro']),
        Spacer(1, 4),
        Paragraph("1. Types de séance (couleurs des cases)", styles['section']),
        Paragraph(
            "La couleur de la case indique l'objectif ou la nature principale "
            "de la séance.", styles['normal'],
        ),
        Spacer(1, 2),
        _tableau_types_seance(styles, largeur),
        Paragraph("2. Intensité ou nature de la journée (symboles)", styles['section']),
        Paragraph(
            "Le symbole indique le niveau de sollicitation ou la nature globale "
            "de la journée.", styles['normal'],
        ),
        Spacer(1, 2),
        _tableau_intensites(styles, largeur),
        Paragraph("3. Exemple de lecture d'une ligne", styles['section']),
        Spacer(1, 2),
        _tableau_exemple(exemple, styles, largeur),
        Spacer(1, 3),
        _explications_exemple(exemple, styles, largeur),
        Paragraph("4. Quelques repères pour bien utiliser votre plan", styles['section']),
        Spacer(1, 2),
        _tableau_reperes(styles, largeur),
        Spacer(1, 4),
        Paragraph("Entraînement • Progression • Plaisir", styles['footer']),
        Paragraph("Merci pour votre engagement et bonne préparation !", styles['footer']),
    ]


def exporter_pdf_plan(plan: Dict, plan_dir: str) -> str:
    """
    Exporte le plan complet en PDF, 2 semaines par page maximum.
    Chaque page reprend l'entête et affiche la période des semaines
    présentées ainsi que le numéro de page.
    """
    if not plan['semaines']:
        print("   ⚠️ Aucune semaine à exporter")
        return ""

    styles = _creer_styles_pdf()
    contraintes_pdf, index_par_message = _collecter_contraintes(plan)
    groupes = _grouper_semaines_par_page(plan['semaines'])

    largeur_page, hauteur_page = landscape(A4)
    largeur_utile = largeur_page - MARGE_GAUCHE - MARGE_DROITE
    hauteur_utile = hauteur_page - MARGE_HAUT - MARGE_BAS

    story = []
    for index_page, groupe in enumerate(groupes):
        entete = _bloc_entete(plan, contraintes_pdf, styles, largeur_utile)
        hauteur_entete = _hauteur_flowables(entete, largeur_utile, hauteur_utile)
        periode = Paragraph(_periode_groupe(groupe), styles['periode'])
        _, h_periode = periode.wrap(largeur_utile, hauteur_utile)
        hauteur_periode = (
            styles['periode'].spaceBefore + h_periode + styles['periode'].spaceAfter
        )
        hauteur_tableau = hauteur_utile - hauteur_entete - hauteur_periode
        hauteur_tableau = max(hauteur_tableau, 80 * mm)

        story.extend(entete)
        story.append(_construire_tableau(
            groupe, index_par_message, styles, largeur_utile, hauteur_tableau,
        ))
        story.append(periode)
        if index_page < len(groupes) - 1:
            story.append(PageBreak())

    # ---- DERNIÈRE PAGE PÉDAGOGIQUE ----
    story.append(PageBreak())
    story.extend(_bloc_page_pedagogique(plan, styles, largeur_utile))

    # ---- GÉNÉRATION DU PDF ----
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom = plan['athlete'].replace(' ', '_')
    nom_fichier = f"{nom}_plan_apercu_{timestamp}.pdf"
    chemin = os.path.join(plan_dir, nom_fichier)

    try:
        doc = SimpleDocTemplate(
            chemin, pagesize=landscape(A4),
            topMargin=MARGE_HAUT, bottomMargin=MARGE_BAS,
            leftMargin=MARGE_GAUCHE, rightMargin=MARGE_DROITE,
            pageCompression=0,
        )
        doc.onFirstPage = ajouter_filigrane_pdf
        doc.onLaterPages = ajouter_filigrane_pdf
        doc.build(story, canvasmaker=_PlanCanvas)
        print(f"   📄 Plan PDF aperçu exporté : {chemin}")
        return chemin
    except Exception as e:
        print(f"   ❌ Erreur PDF : {e}")
        return ""
