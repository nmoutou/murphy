# murphy-eval — harnais d'évaluation IR (P2)

Scorer de récupération documentaire pour Murphy (RAG juridique). Évalue
uniquement la **récupération** (contrat `requête → IDs ordonnés`, ADR-016) :
aucune dépendance à un LLM générateur, aucune dépendance aux bases de données.

Périmètre actuel :

- **B-04** — le scorer pur : `(qrels, run) → métriques`.
- **B-05** — l'adapter baseline (config dense de référence) : `(topics, R) → run`.
  `BaselineRetriever` embarque chaque requête (TEI), interroge Qdrant en direct
  (chemin de lecture dédié, sans importer `ragcore` — ADR-027) et écrit un run
  JSONL canonique immuable (ADR-008). Le `doc_id` canonique (ADR-018) est lu du
  payload Qdrant (clé `identifier`), sans résolution externe. Le nom de
  collection provient du pointeur `MURPHY_META` publié par la dernière
  ingestion `ok`.
- **B-06** — les invariants structurels de strate 1 (ADR-017), part **pure**
  (aucune base de données). `core/services/invariants.py` collecte les
  `Violation` d'un run/qrels : rangs contigus et uniques par requête, pas de
  doublon `(query_id, chunk_id)`, `doc_id`/`chunk_id` non vides, et espaces de
  nommage `doc_id` compatibles entre run et qrels (garde-fou contre des
  métriques à 0 muettes). Branchés en option sur les loaders JSONL
  (`load_jsonl_run(..., validate=True)` → lève `InvariantError`). La complétude
  et l'intégrité des liens (strate 1 *live*, sur BDD peuplées) restent hors v0
  par décision de cadrage — déjà couvertes côté `data/`.

Voir `docs/product/ADR/ADR-027-plateforme-evaluation-end-to-end.md` (repo
parent) pour la place de ce projet dans la plateforme P2 complète.

## Installer

```bash
python -m pip install -e ".[dev]"
```

## Tester

```bash
python -m pytest                 # suite primaire : goldens (oracle à la main) + unitaires
python -m pytest -m oracle       # cross-check trec_eval (nécessite pytrec_eval)
python -m pytest -m integration  # chemin réel Qdrant (testcontainers — nécessite Docker)
ruff check src
mypy src/murphy_eval
```
