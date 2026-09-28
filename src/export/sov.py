# ============================================================
# FICHIER: src/export/sov.py
# RÔLE: Sauvegarde des fichiers (JSON, CSV, PDF)
#       Contient la gestion du FILIGRANE en pleine largeur
# ============================================================

import os
import json
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader


def sauvegarder_json(data, base_path):
    """Sauvegarde un dictionnaire en fichier JSON."""
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = base_path + '.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
    except Exception as e:
        print(f"   ❌ Erreur JSON : {e}")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.json"
            if not os.path.exists(test_path):
                break
            version += 1
        with open(test_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return test_path


def sauvegarder_csv(df, base_path):
    """Sauvegarde un DataFrame pandas en fichier CSV."""
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = base_path + '.csv'
    try:
        df.to_csv(path, index=False, encoding='utf-8-sig', sep=';')
        return path
    except Exception as e:
        print(f"   ❌ Erreur CSV : {e}")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.csv"
            if not os.path.exists(test_path):
                break
            version += 1
        df.to_csv(test_path, index=False, encoding='utf-8-sig', sep=';')
        return test_path


def ajouter_filigrane_pdf(canvas_obj, doc):
    """
    Ajoute le logo Sigle_Papy.gif en filigrane sur TOUTE LA LARGEUR de la page.
    Le fichier doit être à la racine du projet.
    """
    largeur_page, hauteur_page = A4
    
    # Recherche du fichier Sigle_Papy.gif
    chemins_possibles = [
        'Sigle_Papy.gif',
        os.path.join(os.getcwd(), 'Sigle_Papy.gif'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Sigle_Papy.gif'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Sigle_Papy.gif'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Sigle_Papy.gif'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'Sigle_Papy.gif'),
    ]
    
    chemin_image = None
    for path in chemins_possibles:
        if os.path.exists(path):
            chemin_image = path
            break
    
    if not chemin_image:
        return
    
    try:
        img = ImageReader(chemin_image)
        img_width, img_height = img.getSize()
        
        # Largeur = TOUTE LA LARGEUR DE LA PAGE
        largeur_filigrane = largeur_page
        hauteur_filigrane = img_height * (largeur_filigrane / img_width)
        
        # Position: collé à gauche, centré verticalement
        x = 0
        y = (hauteur_page - hauteur_filigrane) / 2
        
        canvas_obj.saveState()
        canvas_obj.setFillAlpha(0.15)
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
        pass


def sauvegarder_pdf(doc, base_path):
    """
    Sauvegarde un PDF avec filigrane sur chaque page.
    """
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = str(base_path) + '.pdf'
    
    # Récupérer le contenu (story)
    story = []
    if hasattr(doc, 'story'):
        story = doc.story
    elif hasattr(doc, '_flowables'):
        story = doc._flowables
    
    if not story or len(story) == 0:
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        story = [Paragraph("PDF de secours", styles['Normal'])]
    
    try:
        new_doc = SimpleDocTemplate(path, pagesize=A4)
        new_doc.onFirstPage = ajouter_filigrane_pdf
        new_doc.onLaterPages = ajouter_filigrane_pdf
        new_doc.build(story)
        return path
    except Exception as e:
        print(f"   ❌ Erreur PDF : {e}")
        txt_path = str(base_path) + '.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Erreur: {e}\n")
        return txt_path

def sauvegarder_intensites_csv(tableau_intensites: list, base_path: str) -> str:
    """
    Sauvegarde le tableau des intensités en CSV.
    """
    if not tableau_intensites:
        return None
    
    import pandas as pd
    df = pd.DataFrame(tableau_intensites)
    path = base_path + '_intensites.csv'
    df.to_csv(path, index=False, encoding='utf-8-sig', sep=';')
    return path