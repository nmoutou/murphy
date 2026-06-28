# murphy

Parent repository for the **Murphy** RAG system. It holds the Docker Compose serving
stack and pulls in the application repos as **git submodules**:

```
murphy/                # this repo (orchestration + infra)
├── backend/           # submodule → https://github.com/left-eyebr0w/murphy-backend
├── frontend/          # submodule → https://github.com/left-eyebr0w/murphy-frontend
├── data/              # submodule → https://github.com/left-eyebr0w/murphy-data
└── docker-compose.*.yml
```

The backend and frontend images are built from their submodule directories. The `data/`
ingestion pipeline is **not** part of the serving stack; it runs offline and only shares
the databases.

## Clone

```bash
git clone --recursive git@github.com:left-eyebr0w/murphy.git
# already cloned without --recursive?
git submodule update --init --recursive
```

To pull every submodule to the latest `main` of its own repo:

```bash
git submodule update --remote --merge
```

## Prerequisites

- Submodules initialized (see above).
- An `.env.dev` file at the repo root (gitignored). Copy `.env.example` and fill it in.
- An NVIDIA GPU for the embedding service (declared in `docker-compose.dev.yml`).

## Usage

```bash
npm run up        # build + start dev stack detached
npm run watch     # same, foreground (streams logs)
npm run logs      # tail logs
npm run status    # container status table
npm run down      # stop everything (incl. prod override)
```

Dev ports: frontend `3000`, backend `5000`, Qdrant `6333`, Mongo `27017`,
Neo4j `7474`/`7687`, embedding service `5001→80`.

## Working with submodules

Each submodule is a full git repo. To change application code, commit **inside** the
submodule and push it, then commit the updated pointer in this parent repo:

```bash
cd backend
# ... edit, commit, push on backend's own main ...
cd ..
git add backend           # records the new commit pointer
git commit -m "Bump backend to <short message>"
```

See [CLAUDE.md](CLAUDE.md) for the full architecture overview.
