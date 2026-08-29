# ============================================================
# FICHIER: src/liste.py
# RÔLE: Fonctions génériques de listage et sélection d'éléments
#       Supporte les dossiers, extensions, et sélection multiple
# ============================================================

import os
from typing import Optional, List, Tuple, Union


def lister_elements(dossier: str, extension: str = '.csv') -> List[Tuple[int, str]]:
    """
    Liste tous les éléments d'un dossier avec une extension donnée.
    
    Args:
        dossier: Chemin du dossier à lister
        extension: Extension à filtrer (ex: '.csv', '.json')
    
    Returns:
        Liste de tuples (numéro, nom)
    """
    if not os.path.exists(dossier):
        os.makedirs(dossier, exist_ok=True)
        return []
    
    elements = [f for f in os.listdir(dossier) if f.endswith(extension)]
    elements.sort()
    
    # Filtrer les dossiers si on liste des dossiers (extension='')
    if extension == '':
        elements = [f for f in elements if os.path.isdir(os.path.join(dossier, f))]
    
    return [(i+1, f) for i, f in enumerate(elements)]


def afficher_elements(elements: List[Tuple[int, str]], titre: str = "", dossier: str = "") -> None:
    """Affiche une liste numérotée d'éléments."""
    if not elements:
        print("❌ Aucun élément trouvé.")
        return
    
    print("\n" + "="*60)
    if titre:
        print(titre)
    elif dossier:
        print(f"📁 ÉLÉMENTS DISPONIBLES DANS {dossier}/")
    else:
        print("📋 LISTE DES ÉLÉMENTS DISPONIBLES")
    print("="*60)
    
    for num, nom in elements:
        print(f"   {num}. {nom}")
    print("="*60)


def choisir_element(
    dossier: str,
    extension: str = '.csv',
    titre: str = "",
    message: str = "",
    permettre_quitter: bool = True
) -> Optional[str]:
    """
    Affiche une liste numérotée et permet de choisir un élément.
    
    Args:
        dossier: Chemin du dossier
        extension: Extension à filtrer (ex: '.csv', '.json')
        titre: Titre personnalisé pour l'affichage
        message: Message personnalisé pour la saisie
        permettre_quitter: Si True, permet de quitter avec 'q'
    
    Returns:
        Le nom de l'élément sélectionné, ou None si annulé
    """
    elements = lister_elements(dossier, extension)
    
    if not elements:
        print(f"\n❌ Aucun fichier {extension} trouvé dans le dossier '{dossier}/'")
        print(f"   Veuillez y placer un fichier avant de continuer.")
        return None
    
    afficher_elements(elements, titre, dossier)
    
    if not message:
        message = "👉 Entrez le numéro de l'élément à sélectionner"
        if permettre_quitter:
            message += " (ou 'q' pour quitter)"
        message += " : "
    
    while True:
        try:
            choix = input("\n" + message).strip()
            
            if permettre_quitter and choix.lower() == 'q':
                return None
            
            if not choix.isdigit():
                print("❌ Veuillez entrer un numéro valide.")
                continue
            
            num = int(choix)
            if 1 <= num <= len(elements):
                return elements[num-1][1]
            else:
                print(f"❌ Numéro invalide. Choisissez entre 1 et {len(elements)}.")
                
        except KeyboardInterrupt:
            print("\n👋 Annulation.")
            return None
        except Exception as e:
            print(f"❌ Erreur: {e}")
            continue


def parser_selection(entree: str, nb_total: int) -> List[int]:
    """
    Parse une entrée utilisateur pour la sélection multiple.
    
    Exemples:
    - "1,3,5" → [1, 3, 5]
    - "1-5" → [1, 2, 3, 4, 5]
    - "*" → [1, 2, ..., nb_total]
    """
    if not entree or entree.strip() == '':
        return []
    
    entree = entree.strip()
    
    if entree == '*':
        return list(range(1, nb_total + 1))
    
    resultats = []
    parties = entree.split(',')
    
    for partie in parties:
        partie = partie.strip()
        if not partie:
            continue
        
        if '-' in partie:
            try:
                debut, fin = partie.split('-')
                debut = int(debut.strip())
                fin = int(fin.strip())
                resultats.extend(range(debut, fin + 1))
            except ValueError:
                print(f"⚠️ Plage invalide: {partie}")
        else:
            try:
                resultats.append(int(partie))
            except ValueError:
                print(f"⚠️ Numéro invalide: {partie}")
    
    resultats = sorted(set(resultats))
    resultats = [r for r in resultats if 1 <= r <= nb_total]
    
    return resultats


def lister_athletes(base_dir: str = 'outputs/Base par athlète') -> List[Tuple[int, str]]:
    """
    Liste tous les dossiers d'athlètes.
    Utilise la fonction générique lister_elements().
    """
    # On liste les dossiers (extension='') mais uniquement ceux qui ont des fichiers valides
    elements = lister_elements(base_dir, '')
    
    athletes = []
    for i, nom in elements:
        chemin = os.path.join(base_dir, nom)
        # Vérifier que le dossier contient des fichiers utiles
        fichiers = os.listdir(chemin)
        fichiers_utiles = [f for f in fichiers if f.endswith(('.json', '.csv'))]
        if fichiers_utiles:
            athletes.append((i, nom))
        else:
            print(f"   ⚠️ Dossier {nom} ignoré (aucun fichier valide)")
    
    # Recréer les numéros après filtrage
    return [(i+1, nom) for i, (_, nom) in enumerate(athletes)]


def afficher_athletes(athletes: List[Tuple[int, str]]) -> None:
    """Affiche la liste des athlètes avec leur numéro."""
    if not athletes:
        print("❌ Aucun athlète trouvé.")
        return
    
    print("\n" + "="*60)
    print("📋 LISTE DES ATHLÈTES DISPONIBLES")
    print("="*60)
    for num, nom in athletes:
        print(f"   {num}. {nom}")
    print("="*60)
    print("   Pour sélectionner plusieurs: 1,3,5 ou 1-5")
    print("   Pour sélectionner tous: *")
    print("="*60)


def choisir_athletes(base_dir: str = 'outputs/Base par athlète') -> List[str]:
    """
    Affiche la liste des athlètes et permet d'en choisir plusieurs.
    
    Returns:
        Liste des noms d'athlètes sélectionnés.
    """
    athletes = lister_athletes(base_dir)
    
    if not athletes:
        return []
    
    afficher_athletes(athletes)
    
    while True:
        try:
            entree = input("\n👉 Entrez les numéros (ex: 1,3,5 ou 1-5 ou * pour tous) : ").strip()
            
            if not entree:
                print("❌ Veuillez entrer une sélection.")
                continue
            
            if entree.lower() == 'q':
                return []
            
            indices = parser_selection(entree, len(athletes))
            
            if not indices:
                print("❌ Aucun athlète sélectionné.")
                continue
            
            noms = [athletes[i-1][1] for i in indices]
            print(f"✅ Athlètes sélectionnés: {', '.join(noms)}")
            return noms
            
        except KeyboardInterrupt:
            print("\n👋 Annulation.")
            return []
        except Exception as e:
            print(f"❌ Erreur: {e}")
            continue