# Dependencies - Murphy Project

## 📦 Backend (Node.js/Express)

### Production
- `express@^5.2.1` - Web framework
- `@qdrant/qdrant-js@^1.16.2` - Vector DB client
- `mongodb@^6.4.0` - MongoDB driver
- `cors@^2.8.6` - CORS middleware
- `helmet@^8.1.0` - Security middleware
- `express-rate-limit@^8.2.1` - Rate limiting
- `express-validator@^7.3.1` - Request validation
- `ws@^8.19.0`, `@types/ws@^8.18.1` - WebSocket
- `pino@^10.3.0`, `pino-http@^11.0.0`, `pino-pretty@^13.1.3` - Logging
- `ai@^6.0.87` - Vercel AI SDK
- `dotenv@^17.2.3` - Environment config

### Development
- `typescript@^5.9.3` - TypeScript compiler
- `ts-node@^10.9.2` - Direct TypeScript execution
- `nodemon@^3.1.11` - Auto-reload
- `jest@^30.2.0`, `ts-jest@^29.4.6` - Testing
- `@types/node@^25.0.10`, `@types/express@^5.0.6`, `@types/cors@^2.8.19`, `@types/jest@^30.0.0`, `@types/supertest@^6.0.3` - TypeScript types
- `supertest@^7.2.2` - HTTP testing

---

## 🎨 Frontend (Next.js/React)

### Production
- `next@^16.1.6` - React framework
- `react@^19.2.4`, `react-dom@^19.2.4` - React library
- `zustand@^5.0.11` - State management
- `@ai-sdk/react@^3.0.89` - Vercel AI SDK React
- `ai@^6.0.87` - Vercel AI SDK
- `react-markdown@^10.1.0` - Markdown rendering
- `remark-gfm@^4.0.1` - GitHub Flavored Markdown

### Development
- `typescript@^5.9.3` - TypeScript
- `tailwindcss@^4.1.18`, `@tailwindcss/postcss@^4.1.18` - CSS framework
- `eslint@^9.39.2`, `eslint-config-next@^16.1.6` - Linting
- `@types/react@^19.2.14`, `@types/react-dom@^19.2.3`, `@types/node@^25.2.3` - Types

---

> **Pas de code Python dans ce dépôt.** L'ingestion LEGIFRANCE (extraction, nettoyage,
> chunking, embedding, upload) et le seeding des bases vivent dans un autre dépôt. Murphy
> consomme des bases **pré-peuplées**.

---

## 🔧 Service d'embedding (TEI)

Le service d'embedding n'est **pas un service Python custom** : c'est l'image prête à
l'emploi **HuggingFace Text Embeddings Inference**, lancée via Docker Compose avec
`--model-id $EMBEDDING_MODEL --pooling mean --dtype float16`. Elle expose l'endpoint
`POST /v1/embeddings` et requiert un **GPU NVIDIA** (CUDA).

---

## 🐳 Docker Images

| Composant | Image | Version |
|-----------|-------|---------|
| Vector DB (Qdrant) | `qdrant/qdrant` | v1.16.3 |
| MongoDB | `mongo` | 8.2 |
| Neo4j (graphe, réservé) | `neo4j` | 2025.09.0 |
| Embeddings (TEI) | `ghcr.io/huggingface/text-embeddings-inference` | cuda-1.8.1 |
| Backend / Frontend | construites depuis `backend/Dockerfile` / `frontend/Dockerfile` | — |

---

## 💻 System Dependencies

- **Node.js**: 20 (backend), 22 (frontend)
- **Docker & Docker Compose** — orchestration des conteneurs
- **GPU NVIDIA (CUDA)** — requis par le service d'embedding TEI

---

## 🎯 Services d'infrastructure

- **MongoDB** — contenu des chunks (contexte LLM)
- **Qdrant** — index vectoriel (recherche sémantique)
- **HuggingFace TEI** — service d'embedding (GPU)
- **Neo4j** — base graphe, provisionnée mais réservée (non câblée)

---

## 📊 Synthèse

| Catégorie | Nombre |
|-----------|--------|
| Backend runtime | 14 paquets |
| Backend dev | 13 paquets |
| Frontend runtime | 8 paquets |
| Frontend dev | ~7 paquets |
| Images Docker (prébuilt) | 4 (Qdrant, MongoDB, Neo4j, TEI) |

