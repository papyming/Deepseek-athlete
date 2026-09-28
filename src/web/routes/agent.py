# ============================================================
# FICHIER: src/web/routes/agent.py
# RÔLE: Routes Web de l'agent IA (aperçu puis confirmation).
#
#       - POST /plans/{identifiant}/ia/preview : aperçu AVANT/APRÈS
#         (aucune écriture du CSV courant) ;
#       - POST /plans/{identifiant}/ia/confirm : écriture après
#         confirmation explicite, via un jeton d'aperçu opaque.
#
#       Le fournisseur IA est celui de app.state.fournisseur_ia :
#       aucun fournisseur réseau n'est codé ici. Le navigateur ne
#       transmet jamais de chemin : le plan est résolu via PlanRepository.
# ============================================================

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..services import agent as service
from ..services import plans as plans_service

router = APIRouter()


class DemandeIA(BaseModel):
    demande: str = ''
    ecrire: bool = False
    donnees_athlete: Optional[Dict] = None


class DemandeApercu(BaseModel):
    demande: str = ''


class DemandeConfirmation(BaseModel):
    preview_id: str = ''


def _fournisseur(request: Request):
    return getattr(request.app.state, 'fournisseur_ia', None)


def _indisponible():
    return JSONResponse(
        {'resultat': 'INDISPONIBLE',
         'erreurs': ['Aucun fournisseur IA configuré.'],
         'confirmation_requise': False},
        status_code=503,
    )


def _resoudre_plan(request: Request, identifiant: str) -> Dict:
    entree = plans_service.obtenir_plan(
        identifiant, request.app.state.repository
    )
    if entree is None:
        raise HTTPException(status_code=404, detail='Plan introuvable')
    return entree


@router.post('/plans/{identifiant}/ia/preview')
def apercu_ia(request: Request, identifiant: str, corps: DemandeApercu):
    entree = _resoudre_plan(request, identifiant)
    fournisseur = _fournisseur(request)
    if fournisseur is None:
        return _indisponible()

    resultat = service.generer_apercu(
        entree,
        corps.demande,
        fournisseur,
        repository=request.app.state.repository,
    )
    return JSONResponse(resultat)


@router.post('/plans/{identifiant}/ia/confirm')
def confirmer_ia(request: Request, identifiant: str, corps: DemandeConfirmation):
    entree = _resoudre_plan(request, identifiant)

    resultat = service.confirmer_apercu(
        entree,
        corps.preview_id,
        repository=request.app.state.repository,
    )
    statut = 200 if resultat.get('resultat') == 'CONFIRME' else 409
    return JSONResponse(resultat, status_code=statut)


@router.post('/plans/{identifiant}/ia')
def demander_modification_ia(request: Request, identifiant: str, corps: DemandeIA):
    entree = _resoudre_plan(request, identifiant)
    fournisseur = _fournisseur(request)
    if fournisseur is None:
        return _indisponible()

    resultat = service.traiter_demande_ia_plan(
        entree,
        corps.demande,
        fournisseur,
        donnees_athlete=corps.donnees_athlete,
        ecrire=corps.ecrire,
    )
    return JSONResponse(resultat)
