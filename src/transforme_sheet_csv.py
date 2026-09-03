# ============================================================
# FICHIER: src/transforme_sheet_csv.py
# RÔLE: Transformation d'un fichier TSV (tabulations) en CSV standard (séparateur ;)
#       Compatible avec les exports Google Sheets / LibreOffice / Excel
# ============================================================

import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple


def normaliser_caracteres_speciaux(contenu: str) -> str:
    """Remplace les caractères spéciaux problématiques."""
    replacements = {
        'NḞ': 'N°',
        '????????????': 'Compléments',
        '??????????': 'Compléments',
        '𝐂𝐨𝐦𝐩𝐥𝐞́𝐦𝐞𝐧𝐭𝐬': 'Compléments',
        '𝐚̀': 'à',
        '𝐫𝐚𝐣𝐨𝐮𝐭𝐞𝐫': 'rajouter',
        '𝐩𝐨𝐮𝐫': 'pour',
        '𝐚𝐦𝐞́𝐥𝐢𝐨𝐫𝐞𝐫': 'améliorer',
        '𝐥𝐞': 'le',
        '𝐬𝐮𝐢𝐯𝐢': 'suivi',
        '𝐜𝐨𝐧𝐭𝐫𝐚𝐢𝐧𝐭𝐞𝐬': 'contraintes',
        '𝐩𝐫𝐨': 'pro',
        '𝐩𝐞𝐫𝐬𝐨': 'perso',
        '𝐬𝐚𝐧𝐭𝐞́': 'santé',
        '𝐝𝐢𝐚𝐛𝐞̀𝐭𝐞': 'diabète',
        '𝐚𝐥𝐥𝐞𝐫𝐠𝐢𝐞': 'allergie',
        '𝐞𝐭𝐜': 'etc',
        '𝐞𝐦𝐩𝐥𝐨𝐢': 'emploi',
        '𝐝𝐮': 'du',
        '𝐭𝐞𝐦𝐩𝐬': 'temps'
    }
    for ancien, nouveau in replacements.items():
        contenu = contenu.replace(ancien, nouveau)
    # Supprimer les ? en trop
    contenu = re.sub(r'[?]{2,}', '', contenu)
    return contenu


def transformer_tsv_en_csv(contenu: str) -> str:
    """
    Transforme un contenu TSV (tabulations) en CSV (séparateur ;).
    Nettoie l'en-tête et les données.
    """
    # Remplacer les tabulations par des points-virgules
    contenu = contenu.replace('\t', ';')
    
    # Normaliser les caractères spéciaux
    contenu = normaliser_caracteres_speciaux(contenu)
    
    # Séparer l'en-tête des données
    lignes = contenu.split('\n')
    if len(lignes) < 2:
        return contenu
    
    en_tete = lignes[0]
    donnees = '\n'.join(lignes[1:])
    
    # --- Nettoyer l'en-tête ---
    # Supprimer les guillemets inutiles
    en_tete = re.sub(r'"([^"]*)"', r'\1', en_tete)
    
    # Supprimer les espaces en début/fin de colonne
    en_tete = re.sub(r' +;', ';', en_tete)
    en_tete = re.sub(r'; +', ';', en_tete)
    
    # Supprimer les espaces multiples
    en_tete = re.sub(r'  +', ' ', en_tete)
    
    # Supprimer les ; en fin d'en-tête
    en_tete = re.sub(r';+$', '', en_tete)
    
    # Normaliser les espaces avant les ? (garder un espace)
    en_tete = re.sub(r'([^ ])\?', r'\1 ?', en_tete)
    
    # --- Nettoyer les données ---
    # Supprimer les ; en fin de ligne
    lignes_donnees = donnees.split('\n')
    lignes_nettoyees = []
    
    for ligne in lignes_donnees:
        if not ligne.strip():
            continue
        # Supprimer les ; en fin de ligne
        ligne = re.sub(r';+$', '', ligne)
        # Supprimer le caractère EOF (Ctrl+Z)
        ligne = ligne.replace('', '')
        if ligne.strip():
            lignes_nettoyees.append(ligne)
    
    # Reconstruire
    return en_tete + '\n' + '\n'.join(lignes_nettoyees)


def lire_tsv_et_transformer(chemin_entree: str) -> Optional[pd.DataFrame]:
    """
    Lit un fichier TSV (tabulations) et le transforme en DataFrame standard.
    """
    try:
        # Détecter l'encodage
        encodages = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        
        for enc in encodages:
            try:
                with open(chemin_entree, 'r', encoding=enc) as f:
                    contenu = f.read()
                
                # Remplacer les tabulations par des points-virgules
                contenu = contenu.replace('\t', ';')
                
                # Normaliser les caractères spéciaux
                contenu = normaliser_caracteres_speciaux(contenu)
                
                # Lire avec pandas
                from io import StringIO
                df = pd.read_csv(
                    StringIO(contenu),
                    delimiter=';',
                    encoding='utf-8',
                    engine='python',
                    quotechar='"',
                    quoting=1
                )
                
                # Nettoyer les noms de colonnes
                df.columns = df.columns.str.replace('\n', ' ', regex=False)
                df.columns = df.columns.str.replace('\r', '', regex=False)
                df.columns = df.columns.str.strip()
                df.columns = df.columns.str.replace(r'  +', ' ', regex=True)
                
                # Supprimer les colonnes vides
                df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                df = df.dropna(axis=1, how='all')
                
                print(f"   ✅ Lecture réussie (encodage: {enc})")
                return df
                
            except Exception as e:
                continue
        
        print("❌ Aucun encodage n'a fonctionné.")
        return None
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return None


def transformer_fichier_csv(chemin_entree: str) -> Optional[str]:
    """
    Transforme un fichier TSV (exporté depuis Google Sheets/LibreOffice) en CSV standard.
    """
    try:
        print(f"   📖 Lecture du fichier : {chemin_entree}")
        
        # Lire le fichier et le transformer en DataFrame
        df = lire_tsv_et_transformer(chemin_entree)
        
        if df is None or df.empty:
            print("❌ Aucune donnée lue.")
            return None
        
        print(f"   📊 {len(df)} lignes, {len(df.columns)} colonnes")
        
        # Sauvegarder en CSV standard
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom_sortie = f"{timestamp}-base_analytique.csv"
        chemin_sortie = os.path.join('inputs', nom_sortie)
        
        df.to_csv(chemin_sortie, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"   💾 Fichier transformé : {chemin_sortie}")
        
        return chemin_sortie
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return None


def choisir_fichier_tsv() -> Optional[str]:
    """Affiche la liste des fichiers dans inputs/ et permet d'en choisir un."""
    from liste import choisir_element
    
    return choisir_element(
        dossier='inputs',
        extension='.tsv',
        titre="📁 FICHIERS TSV DISPONIBLES DANS inputs/"
    )


def choisir_fichier_csv() -> Optional[str]:
    """Affiche la liste des fichiers CSV dans inputs/ et permet d'en choisir un."""
    from liste import choisir_element
    
    return choisir_element(
        dossier='inputs',
        extension='.csv',
        titre="📁 FICHIERS CSV DISPONIBLES DANS inputs/"
    )


def transformer_copier_coller() -> Optional[str]:
    """
    Fonction principale : demande le fichier à transformer.
    Supporte les fichiers .tsv et .csv.
    """
    print("\n" + "="*60)
    print("🔄 TRANSFORMATION FICHIER TSV/CSV → CSV STANDARD")
    print("="*60)
    print("\n📋 Instructions:")
    print("   1. Exportez votre fichier depuis Google Sheets:")
    print("      Fichier → Télécharger → Valeurs séparées par des tabulations (.tsv)")
    print("   2. Ou depuis LibreOffice/Excel au format TSV")
    print("   3. Placez le fichier dans le dossier 'inputs/'")
    print("   4. Sélectionnez-le ci-dessous")
    print("="*60)
    
    # Lister les fichiers TSV d'abord, puis CSV
    fichier_tsv = choisir_fichier_tsv()
    if fichier_tsv:
        chemin = os.path.join('inputs', fichier_tsv)
        return transformer_fichier_csv(chemin)
    
    fichier_csv = choisir_fichier_csv()
    if fichier_csv:
        chemin = os.path.join('inputs', fichier_csv)
        return transformer_fichier_csv(chemin)
    
    print("❌ Aucun fichier trouvé dans inputs/")
    print("   Placez un fichier .tsv ou .csv dans le dossier inputs/")
    return None


def analyser_fichier_apres_transformation(chemin: str) -> Optional[pd.DataFrame]:
    """Analyse le fichier transformé pour vérifier sa structure."""
    if not chemin or not os.path.exists(chemin):
        print("⚠️ Fichier introuvable.")
        return None
    
    try:
        df = pd.read_csv(chemin, delimiter=';', encoding='utf-8-sig', engine='python')
        
        if df.empty:
            print("⚠️ Le fichier est vide.")
            return None
        
        print(f"\n📊 Structure détectée :")
        print(f"   - {len(df)} lignes")
        print(f"   - {len(df.columns)} colonnes")
        
        # Vérifier les colonnes vides
        colonnes_vides = [col for col in df.columns if col.strip() == '' or col.startswith('Unnamed')]
        if colonnes_vides:
            print(f"   ⚠️ {len(colonnes_vides)} colonnes vides détectées")
        else:
            print("   ✅ Pas de colonnes vides")
        
        # Vérifier la colonne VMA
        for col in df.columns:
            if 'VMA' in col or 'test VMA' in col:
                print(f"   ✅ Colonne VMA trouvée : {col}")
                if not df.empty:
                    valeurs = df[col].dropna()
                    if not valeurs.empty:
                        print(f"   📊 Valeur VMA : {valeurs.iloc[0]}")
                break
        
        return df
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification : {e}")
        return None


def afficher_resume_transformation(chemin: str) -> None:
    """Affiche un résumé du fichier transformé."""
    if not chemin:
        return
    
    df = analyser_fichier_apres_transformation(chemin)
    if df is not None:
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DU FICHIER TRANSFORMÉ")
        print("="*60)
        print(f"   📁 Fichier : {os.path.basename(chemin)}")
        print(f"   📋 Colonnes : {len(df.columns)}")
        print(f"   📏 Lignes : {len(df)}")
        print("="*60)