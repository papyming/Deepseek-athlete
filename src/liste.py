# ============================================================
# FICHIER: src/liste.py
# RÔLE: Fonctions génériques de listage et sélection d'éléments
#       CORRIGÉ: Suppression de l'import circulaire
# ============================================================

import os
from typing import Optional, List, Tuple


def lister_elements(dossier: str, extensions: List[str] = None) -> List[Tuple[int, str]]:
    """
    Liste tous les éléments d'un dossier avec les extensions données.
    
    Args:
        dossier: Chemin du dossier à lister
        extensions: Liste des extensions à filtrer (ex: ['.csv', '.tsv'])
    
    Returns:
        Liste de tuples (numéro, nom)
    """
    if not os.path.exists(dossier):
        os.makedirs(dossier, exist_ok=True)
        return []
    
    if extensions is None:
        extensions = ['.csv', '.tsv']
    
    elements = []
    for f in os.listdir(dossier):
        chemin_complet = os.path.join(dossier, f)
        if os.path.isdir(chemin_complet):
            continue
        # Vérifier si le fichier a une des extensions
        for ext in extensions:
            if f.endswith(ext):
                elements.append(f)
                break
    
    elements.sort()
    return [(i+1, f) for i, f in enumerate(elements)]


def afficher_elements(elements: List[Tuple[int, str]], titre: str = "") -> None:
    """Affiche une liste numérotée d'éléments."""
    if not elements:
        print("❌ Aucun élément trouvé.")
        return
    
    print("\n" + "="*60)
    if titre:
        print(titre)
    else:
        print("📋 LISTE DES ÉLÉMENTS DISPONIBLES")
    print("="*60)
    
    for num, nom in elements:
        print(f"   {num}. {nom}")
    print("="*60)


def choisir_element(
    dossier: str,
    extensions: List[str] = None,
    titre: str = "",
    message: str = "",
    permettre_quitter: bool = True
) -> Optional[str]:
    """
    Affiche une liste numérotée et permet de choisir un élément.
    
    Args:
        dossier: Chemin du dossier
        extensions: Liste des extensions (ex: ['.csv', '.tsv'])
        titre: Titre personnalisé pour l'affichage
        message: Message personnalisé pour la saisie
        permettre_quitter: Si True, permet de quitter avec 'q'
    
    Returns:
        Le nom de l'élément sélectionné, ou None si annulé
    """
    if extensions is None:
        extensions = ['.csv', '.tsv']
    
    elements = lister_elements(dossier, extensions)
    
    if not elements:
        print(f"\n❌ Aucun fichier trouvé dans le dossier '{dossier}/'")
        ext_str = ", ".join(extensions) if extensions else "tous"
        print(f"   Extensions acceptées : {ext_str}")
        return None
    
    afficher_elements(elements, titre)
    
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
    """Parse une entrée utilisateur pour la sélection multiple."""
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
    """Liste tous les dossiers d'athlètes."""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        return []
    
    athletes = []
    for nom in os.listdir(base_dir):
        chemin = os.path.join(base_dir, nom)
        if os.path.isdir(chemin):
            fichiers = os.listdir(chemin)
            fichiers_utiles = [f for f in fichiers if f.endswith(('.json', '.csv'))]
            if fichiers_utiles:
                athletes.append(nom)
    
    athletes.sort()
    return [(i+1, nom) for i, nom in enumerate(athletes)]


def afficher_athletes(athletes: List[Tuple[int, str]]) -> None:
    """Affiche la liste des athlètes."""
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
    """Affiche la liste des athlètes et permet d'en choisir plusieurs."""
    athletes = lister_athletes(base_dir)
    
    if not athletes:
        print("❌ Aucun athlète trouvé dans 'outputs/Base par athlète/'")
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