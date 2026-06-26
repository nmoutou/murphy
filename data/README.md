# murphy-data

Python/Kedro **ingestion** pipeline for the Murphy RAG system. Ingests LEGIFRANCE XML
and writes chunks/embeddings into MongoDB / Qdrant / Neo4j — the same datastores the
backend reads from.

Runs **offline and out-of-band**: it is not part of the Docker serving stack and the
backend never calls into it. The two only share databases, no code.

> **Key fact:** the actual pipeline logic, Kedro hooks, and registry live in an external
> `ragcore` package (not in this repo). `src/data/` is a thin Kedro shell that delegates
> to `ragcore`. `ragcore` must be installed in the Python env for the project to run.

## Develop

```bash
kedro run
kedro viz
ruff check .     # lint/format
pytest           # config in pyproject.toml
```

Loads its own `.env` from this directory. Tuning surface: `conf/base/parameters.yml`.
