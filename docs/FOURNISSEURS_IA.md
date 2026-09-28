# Fournisseurs IA — Configuration

Ce document décrit la configuration des fournisseurs IA interchangeables
(Mistral, Gemini, OpenRouter). **Aucune clé ne doit être écrite dans le code,
les tests, `requirements.txt` ou Git.** Les clés proviennent uniquement de
variables d'environnement.

## Variables d'environnement

| Fournisseur | Clé API                  | Modèle (optionnel)   | Modèle par défaut        |
|-------------|--------------------------|----------------------|--------------------------|
| Mistral     | `MISTRAL_API_KEY`        | `MISTRAL_MODEL`      | `mistral-small-latest`   |
| Gemini      | `GEMINI_API_KEY`         | `GEMINI_MODEL`       | `gemini-flash-latest`    |
| OpenRouter  | `OPENROUTER_API_KEY`     | `OPENROUTER_MODEL`   | `openrouter/free`        |

- Si la variable du modèle est absente, la valeur par défaut ci-dessus est
  utilisée. Elle reste surchargeable par variable d'environnement ou par le
  paramètre `model` du constructeur.
- Si la variable de clé est absente, une erreur explicite `ConfigurationManquante`
  est levée **sans contacter le fournisseur**.

## Exemple (PowerShell)

```powershell
$env:MISTRAL_API_KEY = "..."
$env:MISTRAL_MODEL   = "mistral-small-latest"

$env:GEMINI_API_KEY  = "..."
$env:GEMINI_MODEL    = "gemini-flash-latest"

$env:OPENROUTER_API_KEY = "..."
$env:OPENROUTER_MODEL   = "openrouter/free"
```

## Utilisation

```python
from planificateur.fournisseurs import MistralFournisseurIA

fournisseur = MistralFournisseurIA()          # clé lue dans l'environnement
structure = fournisseur.proposer_modifications(demande, contexte)
```

La structure retournée respecte `contrat_modifications.py`. Le moteur
déterministe (`moteur_modifications.py`) reste la seule autorité pour appliquer
et valider une modification ; un fournisseur n'écrit jamais de fichier et
n'accède jamais au disque.

## Rappels de sécurité

- Ne jamais journaliser une clé.
- Ne jamais placer une clé dans un fichier versionné.
- Un fournisseur ne reçoit aucun chemin de fichier : le contexte est construit
  par Python (`contexte_plan.py`).
