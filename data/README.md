# Murphy — data

Python/Kedro **ingestion** pipeline for the Murphy RAG system. Ingests LEGIFRANCE XML
and writes documents, chunks and embeddings into MongoDB / OpenSearch / Neo4j. During the
migration (ADR-028, step 1), the backend still reads the Qdrant collection written before
it; the pipeline no longer writes Qdrant.

Runs **offline and out-of-band**: it is not part of the Docker serving stack and the
backend never calls into it. The two only share databases, no code.

> **Key fact:** the actual pipeline logic, Kedro hooks, and registry live in the
> `ragcore` package, **vendored in this repo** at `src/ragcore/`. `src/data/` is a thin
> Kedro shell that delegates to it.

**Full documentation lives in [`docs/technical/data/`](../docs/technical/data/README.md)** — architecture, node-by-node
pipeline reference, data model, configuration, telemetry.

## Run

The pipeline needs Mongo, OpenSearch, Neo4j and the TEI embedding service. They are declared
**once**, at the repository root. You do not have to leave this directory to start them:

```bash
npm run up       # the whole stack, including mongo, opensearch, neo4j, embedding-service (GPU).
npm run logs     # first TEI boot downloads the model — be patient, it is not a hang.
npm run down     # stop them
kedro run
```

## Configuration

There is **one** environment file, and it lives at the repo root: `../.env.dev` (copy it
from `../.env.example`). There is **no `.env` in this directory** — creating one has no
effect, since `ragcore/adapters/config/settings.py` reads the root file by absolute path.

One file, because TEI, the backend and the pipeline must agree on the embedding model:
they all read `EMBEDDING_MODEL`. The pipeline additionally checks TEI's `GET /info`
before writing anything, and measures the vector dimension with a probe request. TEI is
the only embedder: `EMBEDDING_MODEL` and `EMBEDDING_SERVICE_URL` are required.

Tuning surface: `conf/base/parameters.yml` holds dev conveniences only (ignored outside
`ENVIRONMENT=dev`). The chunking (`CHUNKING_MAX_CHARS`, `CHUNKING_OVERLAP_CHARS`) lives
in `../.env.dev`, next to `EMBEDDING_MODEL`, since the chunk size is measured against
the model's window. The
OpenSearch index has a fixed name, `OPENSEARCH_INDEX` in `../.env.dev`, which the backend
will share: after changing the mapping, the analyzers, the chunking or the embedding
model, re-ingest the whole corpus.

## Develop

What the CI's `python` job runs (`.github/workflows/ci.yml`):

```bash
uv sync --locked --extra dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy     # strict, on src/ragcore
uv run --locked pytest   # config in pyproject.toml; excludes -m integration, needs no databases and no .env.dev
```
