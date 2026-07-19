# murphy-eval — harnais d'évaluation IR (P2)

Scorer de récupération documentaire pour Murphy (RAG juridique). Évalue
uniquement la **récupération** (contrat `requête → IDs ordonnés`, ADR-016) :
aucune dépendance à un LLM générateur, aucune dépendance aux bases de données.

Périmètre actuel (**B-04**) : le scorer pur — `(qrels, run) → métriques`.
Voir `docs/product/ADR/ADR-027-plateforme-evaluation-end-to-end.md` (repo
parent) pour la place de ce projet dans la plateforme P2 complète.

## Installer

```bash
python -m pip install -e ".[dev]"
```

## Tester

```bash
python -m pytest              # suite primaire : goldens (oracle à la main) + unitaires
python -m pytest -m oracle    # cross-check trec_eval (nécessite pytrec_eval)
ruff check src
mypy src/murphy_eval
```
