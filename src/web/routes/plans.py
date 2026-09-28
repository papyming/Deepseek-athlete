# ============================================================
# FICHIER: src/web/routes/plans.py
# RÔLE: Routes de consultation et de validation des plans.
#       La logique reste dans les services ; le repository est la
#       seule source d'accès aux plans.
# ============================================================

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..services import plans as service

router = APIRouter()

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / 'templates'))


def _depot(request: Request):
    return request.app.state.repository


def _rendre(request: Request, nom: str, contexte: dict):
    """Rendu compatible avec les différentes signatures de TemplateResponse."""
    try:
        return _TEMPLATES.TemplateResponse(request, nom, contexte)
    except TypeError:
        contexte = {**contexte, 'request': request}
        return _TEMPLATES.TemplateResponse(nom, contexte)


def _contexte_plan(request: Request, entree: dict, validation=None) -> dict:
    df = service.lire_plan(entree, _depot(request))
    return {
        'plan': entree,
        'colonnes': list(df.columns),
        'lignes': df.to_dict('records'),
        'validation': validation,
    }


@router.get('/', response_class=HTMLResponse)
def accueil(request: Request):
    plans = service.lister_plans(_depot(request))
    return _rendre(request, 'index.html', {'plans': plans})


@router.get('/plans')
def liste_plans(request: Request):
    return JSONResponse(service.lister_plans(_depot(request)))


@router.get('/plans/{identifiant}', response_class=HTMLResponse)
def page_plan(request: Request, identifiant: str):
    entree = service.obtenir_plan(identifiant, _depot(request))
    if entree is None:
        raise HTTPException(status_code=404, detail='Plan introuvable')
    return _rendre(request, 'plan.html', _contexte_plan(request, entree))


@router.post('/plans/{identifiant}/validate', response_class=HTMLResponse)
def valider_plan(request: Request, identifiant: str):
    entree = service.obtenir_plan(identifiant, _depot(request))
    if entree is None:
        raise HTTPException(status_code=404, detail='Plan introuvable')
    validation = service.valider_plan(entree, _depot(request))
    return _rendre(request, 'plan.html', _contexte_plan(request, entree, validation))
