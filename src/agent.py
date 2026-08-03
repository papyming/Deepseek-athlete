import pandas as pd
import os
import json
from datetime import datetime
from p_code_vma import generer_seances_vma
from p_code_vc import generer_seances_vc
from physiologie import Physiologie

def main():
    # 1. Lire le CSV
    input_path = '../inputs/athletes_complet.csv'
    if not os.path.exists(input_path):
        print(f"❌ Fichier {input_path} introuvable")
        return
    
    df = pd.read_csv(input_path, encoding='utf-8-sig', delimiter=';')
    print(f"✅ {len(df)} athlètes chargés")
    
    # 2. Créer les dossiers de sortie
    os.makedirs('../outputs/plans', exist_ok=True)
    os.makedirs('../outputs/fichiers_fit', exist_ok=True)
    
    # 3. Traiter chaque athlète
    for index, row in df.iterrows():
        athlete = row.to_dict()
        nom = athlete.get('Prénom/Nom', 'Inconnu')
        sexe = athlete.get('Sexe', 'M').upper()
        
        print(f"\n--- {nom} ---")
        
        # 4. Calculs physiologiques (via physiologie.py)
        physio = Physiologie(athlete)
        vma = physio.vma
        vc = physio.vc
        
        if vma:
            print(f"VMA : {vma} km/h")
            # 5. Génération des séances VMA
            seances_vma = generer_seances_vma(vma, sexe)
            sauvegarder_seances(seances_vma, nom, "VMA")
        else:
            print("⚠️ VMA non renseignée")
        
        if vc:
            print(f"VC : {vc} km/h")
            # 6. Génération des séances VC
            seances_vc = generer_seances_vc(vc, sexe)
            sauvegarder_seances(seances_vc, nom, "VC")
        else:
            print("⚠️ VC non renseignée")
    
    print("\n🎉 Terminé !")


def sauvegarder_seances(seances, nom, type_seance):
    """Sauvegarde les séances en CSV"""
    if not seances:
        return
    
    df = pd.DataFrame(seances)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"../outputs/plans/{nom}_{type_seance}_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';')
    print(f"✅ {len(seances)} séances {type_seance} sauvegardées dans {output_file}")


if __name__ == "__main__":
    main()