# ============================================================
# FICHIER: src/web/app.py
# RÔLE: Application Web FastAPI de Deepseek-athlete.
#
#       Lancement :
#         .\.venv\Scripts\python.exe -m src.web.app
#       puis http://127.0.0.1:8000
#
#       La couche Web n'accède aux plans que via PlanRepository.
# ============================================================

import os
import sys

# Permet d'importer les paquets de premier niveau (stockage, planificateur, …)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from planificateur.fournisseurs.openrouter import OpenRouterFournisseurIA
from stockage import PlanRepository, get_plan_repository
from .routes import agent, plans

_BASE = Path(__file__).resolve().parent


def _fournisseur_par_defaut():
    """Fournisseur IA automatique : OpenRouter si ``OPENROUTER_API_KEY`` existe.

    La clé n'est JAMAIS écrite dans le code : elle est lue depuis
    l'environnement. Le modèle est choisi par le fournisseur lui-même
    (``OPENROUTER_MODEL`` sinon son défaut ``openrouter/free``).
    """
    if not os.environ.get('OPENROUTER_API_KEY', '').strip():
        return None
    return OpenRouterFournisseurIA()


def creer_app(repository: PlanRepository = None,
              fournisseur_ia=None) -> FastAPI:
    """Crée l'application Web avec repository et fournisseur IA injectables.

    - ``fournisseur_ia`` explicitement fourni = prioritaire (ex. Mock en test) ;
    - sinon, si ``OPENROUTER_API_KEY`` est présente, OpenRouter est configuré ;
    - sinon, aucun fournisseur (comportement inchangé).
    """
    application = FastAPI(title='Deepseek Athlete', version='0.1.0')
    application.mount(
        '/static', StaticFiles(directory=str(_BASE / 'static')), name='static'
    )
    application.state.repository = repository or get_plan_repository()
    if fournisseur_ia is None:
        fournisseur_ia = _fournisseur_par_defaut()
    application.state.fournisseur_ia = fournisseur_ia
    application.include_router(plans.router)
    application.include_router(agent.router)
    return application


app = creer_app()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
