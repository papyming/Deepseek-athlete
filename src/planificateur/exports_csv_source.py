# ============================================================
# FICHIER: src/planificateur/exports_csv_source.py
# RÔLE: Chaîne d'export CSV maître.
#       PDF et Intervals.ICU sont TOUS DEUX construits à partir
#       du CSV courant (jamais de l'objet Python du générateur).
#       Le CSV est validé avant tout export.
# ============================================================

from typing import Dict, Optional

from .export_intervals import exporter_intervals
from .export_pdf_plan import exporter_pdf_plan
from .plan_csv import construire_plan_depuis_csv, trouver_csv_courant
from .validateur_plan import valider_plan_csv


def _valider(chemin_csv: str, disponibilites: Optional[Dict]):
    return valider_plan_csv(chemin_csv, disponibilites)


def exporter_pdf_depuis_csv(chemin_csv: str, plan_dir: str, athlete: Optional[str] = None,
                            disponibilites: Optional[Dict] = None,
                            valider: bool = True) -> Dict:
    """Génère le PDF à partir du CSV (validation préalable)."""
    validation = _valider(chemin_csv, disponibilites) if valider else {
        'valide': True, 'erreurs': [], 'avertissements': [], 'stats': {}
    }
    if not validation['valide']:
        return {'chemin': '', 'validation': validation}
    plan = construire_plan_depuis_csv(chemin_csv, athlete)
    chemin = exporter_pdf_plan(plan, plan_dir)
    return {'chemin': chemin, 'validation': validation}


def exporter_intervals_depuis_csv(chemin_csv: str, plan_dir: str,
                                  athlete: Optional[str] = None,
                                  disponibilites: Optional[Dict] = None,
                                  valider: bool = True) -> Dict:
    """Génère l'export Intervals.ICU à partir du CSV (validation préalable)."""
    validation = _valider(chemin_csv, disponibilites) if valider else {
        'valide': True, 'erreurs': [], 'avertissements': [], 'stats': {}
    }
    if not validation['valide']:
        return {'chemin': '', 'validation': validation}
    plan = construire_plan_depuis_csv(chemin_csv, athlete)
    chemin = exporter_intervals(plan, plan_dir)
    return {'chemin': chemin, 'validation': validation}


def exporter_exports_depuis_csv(chemin_csv: str, plan_dir: str,
                                athlete: Optional[str] = None,
                                disponibilites: Optional[Dict] = None,
                                valider: bool = True) -> Dict:
    """Génère PDF ET Intervals.ICU depuis le même CSV (source unique)."""
    validation = _valider(chemin_csv, disponibilites) if valider else {
        'valide': True, 'erreurs': [], 'avertissements': [], 'stats': {}
    }
    if not validation['valide']:
        return {
            'valide': False, 'validation': validation,
            'pdf': '', 'intervals': '',
        }
    plan = construire_plan_depuis_csv(chemin_csv, athlete)
    pdf = exporter_pdf_plan(plan, plan_dir)
    intervals = exporter_intervals(plan, plan_dir)
    return {
        'valide': True, 'validation': validation,
        'pdf': pdf, 'intervals': intervals, 'plan': plan,
    }


def exporter_depuis_csv_courant(plan_dir: str, athlete: Optional[str] = None,
                                disponibilites: Optional[Dict] = None) -> Dict:
    """Identifie le CSV courant d'un athlète puis génère PDF + Intervals."""
    chemin_csv = trouver_csv_courant(plan_dir)
    if not chemin_csv:
        return {
            'valide': False,
            'validation': {'valide': False, 'erreurs': ['Aucun CSV de plan trouvé'],
                           'avertissements': [], 'stats': {}},
            'pdf': '', 'intervals': '', 'chemin_csv': '',
        }
    resultat = exporter_exports_depuis_csv(
        chemin_csv, plan_dir, athlete=athlete, disponibilites=disponibilites
    )
    resultat['chemin_csv'] = chemin_csv
    return resultat
