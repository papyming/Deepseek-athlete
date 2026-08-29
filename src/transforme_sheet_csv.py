# ============================================================
# FICHIER: src/transforme_sheet_csv.py
# RÔLE: Transformation d'un copier/coller TSV (depuis tableur) en CSV formaté
#       CORRIGÉ: Supprime les guillemets autour des en-têtes pour correspondre à l'original
# ============================================================

import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, List, Tuple


def collecter_texte_colle() -> Optional[List[str]]:
    """
    Collecte le texte collé depuis le terminal.
    Pour terminer : Ctrl+Z (Windows) / Ctrl+D (Mac/Linux) ou taper 'FIN'
    """
    print("\n📝 Collez le contenu ici")
    print("   Pour terminer : Ctrl+Z (Windows) / Ctrl+D (Mac/Linux) ou tapez 'FIN'")
    print("-" * 60)
    
    lignes = []
    
    while True:
        try:
            ligne = input()
            if ligne.strip().upper() == 'FIN':
                break
            lignes.append(ligne)
        except KeyboardInterrupt:
            print("\n👋 Annulation.")
            return None
        except EOFError:
            print("\n✅ Fin de saisie détectée.")
            break
    
    return lignes if lignes else None


def nettoyer_lignes(lignes: List[str]) -> List[str]:
    """Nettoie les lignes collectées."""
    lignes_nettoyees = []
    
    for ligne in lignes:
        ligne = ligne.replace('\t', ';')
        ligne = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', ligne)
        ligne = re.sub(r'""', '"', ligne)
        lignes_nettoyees.append(ligne)
    
    return lignes_nettoyees


def normaliser_guillemets(contenu: str) -> str:
    """Remplace les sauts de ligne à l'intérieur des guillemets par des espaces."""
    def nettoyer_guillemets(match):
        return '"' + match.group(1).replace('\n', ' ').replace('\r', ' ') + '"'
    return re.sub(r'"([^"]*)"', nettoyer_guillemets, contenu)


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
    contenu = re.sub(r'[?]{2,}', '', contenu)
    return contenu


def normaliser_guillemets_en_tete(contenu: str) -> str:
    """
    CORRIGÉ: Supprime les guillemets autour des en-têtes pour correspondre à l'original.
    """
    lignes = contenu.split('\n')
    if not lignes:
        return contenu
    
    # Traiter l'en-tête : supprimer les guillemets inutiles
    en_tete = lignes[0]
    # Supprimer les guillemets autour des en-têtes qui ne contiennent pas de ; ou de sauts de ligne
    en_tete = re.sub(r'"([^";\n]+)"', r'\1', en_tete)
    lignes[0] = en_tete
    
    return '\n'.join(lignes)


def supprimer_colonnes_vides(contenu: str) -> str:
    """Supprime UNIQUEMENT les colonnes vides en fin de ligne."""
    lignes = contenu.split('\n')
    lignes_nettoyees = []
    
    for ligne in lignes:
        if not ligne.strip():
            lignes_nettoyees.append(ligne)
            continue
        ligne = re.sub(r';+$', '', ligne)
        lignes_nettoyees.append(ligne)
    
    return '\n'.join(lignes_nettoyees)


def valider_structure(contenu: str) -> Tuple[bool, str]:
    """Valide que le contenu a une structure de tableau correcte."""
    lignes = contenu.split('\n')
    if len(lignes) < 2:
        return False, "Le contenu doit avoir au moins 2 lignes."
    
    en_tete = lignes[0]
    if ';' not in en_tete and '\t' not in en_tete:
        return False, "L'en-tête ne contient pas de séparateurs."
    
    sep = ';' if ';' in en_tete else '\t'
    nb_colonnes = len(en_tete.split(sep))
    
    if nb_colonnes < 3:
        return False, f"L'en-tête n'a que {nb_colonnes} colonnes."
    
    return True, f"Structure valide : {nb_colonnes} colonnes."


def compter_colonnes_par_ligne(contenu: str, nb_attendu: int) -> Tuple[bool, List[int]]:
    """Vérifie que toutes les lignes ont le même nombre de colonnes."""
    lignes = contenu.split('\n')
    lignes_problemes = []
    
    for i, ligne in enumerate(lignes):
        if not ligne.strip():
            continue
        nb_colonnes = len(ligne.split(';'))
        if nb_colonnes != nb_attendu:
            lignes_problemes.append(i + 1)
    
    if lignes_problemes:
        return False, lignes_problemes
    return True, []


def transformer_tsv_en_csv(contenu: str) -> Tuple[str, str]:
    """Transforme un contenu TSV en CSV formaté."""
    # Étape 1: Normaliser les guillemets
    contenu = normaliser_guillemets(contenu)
    
    # Étape 2: Normaliser les caractères spéciaux
    contenu = normaliser_caracteres_speciaux(contenu)
    
    # Étape 3: Remplacer les tabulations par des points-virgules
    contenu = contenu.replace('\t', ';')
    
    # Étape 4: Supprimer les colonnes vides en fin de ligne
    contenu = supprimer_colonnes_vides(contenu)
    
    # Étape 5: CORRIGÉ - Normaliser les guillemets dans l'en-tête
    contenu = normaliser_guillemets_en_tete(contenu)
    
    # Étape 6: Supprimer les lignes vides
    lignes = [l for l in contenu.split('\n') if l.strip() or l == '']
    contenu = '\n'.join(lignes)
    
    # Étape 7: Nom de fichier
    maintenant = datetime.now()
    nom_fichier = f"{maintenant.strftime('%Y%m%d_%H%M%S')}-base_analytique.csv"
    
    chemin = os.path.join('inputs', nom_fichier)
    with open(chemin, 'w', encoding='utf-8-sig') as f:
        f.write(contenu)
    
    return chemin, contenu


def analyser_fichier_apres_transformation(chemin: str) -> Optional[pd.DataFrame]:
    """Analyse le fichier transformé pour vérifier sa structure."""
    try:
        df = pd.read_csv(chemin, delimiter=';', encoding='utf-8-sig', engine='python')
        if df.empty:
            print("⚠️ Le fichier est vide.")
            return None
        
        print(f"\n📊 Structure détectée :")
        print(f"   - {len(df)} lignes")
        print(f"   - {len(df.columns)} colonnes")
        
        colonnes_non_vides = [col for col in df.columns if col.strip() and not col.startswith('Unnamed')]
        print(f"   - Colonnes non vides : {len(colonnes_non_vides)}")
        
        colonnes_vides = [col for col in df.columns if col.strip() == '' or col.startswith('Unnamed')]
        if colonnes_vides:
            print(f"   ⚠️ {len(colonnes_vides)} colonnes vides détectées")
        
        return df
        
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification : {e}")
        return None


def transformer_copier_coller() -> Optional[str]:
    """Fonction principale : collecte, transforme et sauvegarde."""
    print("\n" + "="*60)
    print("🔄 TRANSFORMATION COPIER/COLLER TSV → CSV")
    print("="*60)
    print("\n📋 Instructions:")
    print("   1. Copiez le contenu du tableau depuis votre tableur")
    print("   2. Collez-le ci-dessous")
    print("   3. Pour terminer : Ctrl+Z (Windows) / Ctrl+D (Mac) / FIN")
    print("="*60)
    
    lignes = collecter_texte_colle()
    if not lignes:
        print("❌ Aucune donnée collectée.")
        return None
    
    print(f"\n✅ {len(lignes)} lignes récupérées.")
    
    lignes_nettoyees = nettoyer_lignes(lignes)
    contenu = '\n'.join(lignes_nettoyees)
    
    est_valide, message = valider_structure(contenu)
    if not est_valide:
        print(f"⚠️ Problème détecté : {message}")
    
    chemin, contenu_final = transformer_tsv_en_csv(contenu)
    
    # Vérifier le nombre de colonnes
    en_tete = contenu_final.split('\n')[0]
    nb_colonnes_attendu = len(en_tete.split(';'))
    est_valide, lignes_problemes = compter_colonnes_par_ligne(contenu_final, nb_colonnes_attendu)
    
    print(f"\n✅ Fichier transformé sauvegardé : {chemin}")
    print(f"   📋 {nb_colonnes_attendu} colonnes détectées")
    if est_valide:
        print("   ✅ Toutes les lignes sont conformes")
    else:
        print(f"   ⚠️ Lignes problématiques : {lignes_problemes}")
    
    return chemin


def afficher_resume_transformation(chemin: str) -> None:
    """Affiche un résumé du fichier transformé."""
    if not chemin or not os.path.exists(chemin):
        return
    
    try:
        with open(chemin, 'r', encoding='utf-8-sig') as f:
            contenu = f.read()
            lignes = contenu.split('\n')
            
            print("\n" + "="*60)
            print("📊 RÉSUMÉ DU FICHIER TRANSFORMÉ")
            print("="*60)
            print(f"   📁 Fichier : {os.path.basename(chemin)}")
            print(f"   📏 Lignes : {len(lignes)}")
            
            if lignes and lignes[0].strip():
                en_tete = lignes[0].split(';')
                print(f"   📋 Colonnes : {len(en_tete)}")
                for i, col in enumerate(en_tete[:5], 1):
                    affiche_col = col[:50] + '...' if len(col) > 50 else col
                    print(f"      {i}. {affiche_col}")
                if len(en_tete) > 5:
                    print(f"      ... et {len(en_tete) - 5} autres")
            
            print("="*60)
            
    except Exception as e:
        print(f"⚠️ Erreur : {e}")