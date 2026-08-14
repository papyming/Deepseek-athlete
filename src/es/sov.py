import os
import json
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def sauvegarder_json(data, base_path):
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = base_path + '.json'
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
    except PermissionError:
        print(f"   ⚠️ Fichier {path} verrouillé. Création d'une version...")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.json"
            if not os.path.exists(test_path):
                break
            version += 1
        with open(test_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return test_path
    except Exception as e:
        print(f"   ❌ Erreur lors de la sauvegarde JSON : {e}")
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
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = base_path + '.csv'
    try:
        df.to_csv(path, index=False, encoding='utf-8-sig', sep=';')
        return path
    except PermissionError:
        print(f"   ⚠️ Fichier {path} verrouillé. Création d'une version...")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.csv"
            if not os.path.exists(test_path):
                break
            version += 1
        df.to_csv(test_path, index=False, encoding='utf-8-sig', sep=';')
        return test_path
    except Exception as e:
        print(f"   ❌ Erreur lors de la sauvegarde CSV : {e}")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.csv"
            if not os.path.exists(test_path):
                break
            version += 1
        df.to_csv(test_path, index=False, encoding='utf-8-sig', sep=';')
        return test_path

def sauvegarder_pdf(doc, base_path):
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    path = str(base_path) + '.pdf'
    
    story = []
    if hasattr(doc, 'story'):
        story = doc.story
    elif hasattr(doc, '_flowables'):
        story = doc._flowables
    
    if not story:
        print("   ⚠️ Aucun story trouvé. Création d'un PDF minimal.")
        styles = getSampleStyleSheet()
        story = [Paragraph("PDF de secours (aucun story trouvé)", styles['Normal'])]
    
    try:
        new_doc = SimpleDocTemplate(path, pagesize=A4)
        new_doc.build(story)
        return path
    except PermissionError:
        print(f"   ⚠️ Fichier {path} verrouillé. Création d'une version...")
        version = 1
        while True:
            test_path = f"{base_path}_v{version}.pdf"
            if not os.path.exists(test_path):
                break
            version += 1
        new_doc = SimpleDocTemplate(test_path, pagesize=A4)
        new_doc.build(story)
        return test_path
    except Exception as e:
        print(f"   ❌ Erreur lors de la génération du PDF : {e}")
        txt_path = str(base_path) + '.txt'
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Erreur lors de la génération du PDF : {e}\n")
            f.write("Les données sont disponibles dans les fichiers JSON et CSV.\n")
        return txt_path