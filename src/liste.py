# ============================================================
# FICHIER: src/liste.py
# RÔLE: Liste et sélection des athlètes
#       Permet la sélection multiple (1,3,5 ou 1-5 ou *)
# ============================================================

import os
from typing import Optional, List, Tuple


def lister_athletes(base_dir: str = 'outputs/Base par athlète') -> List[Tuple[int, str]]:
    """Liste tous les dossiers d'athlètes."""
    if not os.path.exists(base_dir):
        print(f"❌ Dossier {base_dir} introuvable.")
        return []
    
    dossiers = [d for d in os.listdir(base_dir) 
                if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith('.')]
    dossiers.sort()
    
    athletes = []
    for i, nom in enumerate(dossiers, 1):
        chemin = os.path.join(base_dir, nom)
        fichiers = os.listdir(chemin)
        fichiers_utiles = [f for f in fichiers if f.endswith(('.json', '.csv'))]
        if fichiers_utiles:
            athletes.append((i, nom))
        else:
            print(f"   ⚠️ Dossier {nom} ignoré (aucun fichier valide)")
    
    return athletes


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