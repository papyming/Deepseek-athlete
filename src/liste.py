#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from typing import Optional, List, Tuple

def lister_athletes(base_dir: str = 'outputs/Base par athlète') -> List[Tuple[int, str]]:
    """
    Liste tous les dossiers d'athlètes dans le répertoire Base par athlète.
    
    Args:
        base_dir: Chemin du dossier contenant les athlètes.
    
    Returns:
        Liste de tuples (numéro, nom_athlète)
    """
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
    """
    Affiche la liste des athlètes avec leur numéro.
    """
    if not athletes:
        print("❌ Aucun athlète trouvé.")
        print("   Veuillez d'abord analyser un CSV avec l'option 1.")
        return
    
    print("\n" + "="*60)
    print("📋 LISTE DES ATHLÈTES DISPONIBLES")
    print("="*60)
    for num, nom in athletes:
        print(f"   {num}. {nom}")
    print("="*60)


def choisir_athlete(base_dir: str = 'outputs/Base par athlète') -> Optional[str]:
    """
    Affiche la liste des athlètes et permet à l'utilisateur d'en choisir un.
    
    Returns:
        Nom de l'athlète sélectionné, ou None si annulation.
    """
    athletes = lister_athletes(base_dir)
    
    if not athletes:
        return None
    
    afficher_athletes(athletes)
    
    while True:
        try:
            choix = input("\n👉 Entrez le numéro de l'athlète (ou 'q' pour quitter) : ").strip()
            
            if choix.lower() == 'q':
                return None
            
            num = int(choix)
            if 1 <= num <= len(athletes):
                nom = athletes[num-1][1]
                print(f"✅ Athlète sélectionné : {nom}")
                return nom
            else:
                print(f"❌ Numéro invalide. Choisissez entre 1 et {len(athletes)}.")
        except ValueError:
            print("❌ Veuillez entrer un nombre valide.")
        except KeyboardInterrupt:
            print("\n👋 Annulation.")
            return None


def lister_athletes_simple(base_dir: str = 'outputs/Base par athlète') -> List[str]:
    """
    Retourne une liste simple des noms d'athlètes (sans numéro).
    """
    athletes = lister_athletes(base_dir)
    return [nom for _, nom in athletes]


if __name__ == "__main__":
    print("🧪 Test du module liste.py")
    print("-"*40)
    
    athletes = lister_athletes()
    afficher_athletes(athletes)
    
    nom = choisir_athlete()
    if nom:
        print(f"\n✅ Vous avez sélectionné : {nom}")
    else:
        print("\n❌ Aucun athlète sélectionné.")
        