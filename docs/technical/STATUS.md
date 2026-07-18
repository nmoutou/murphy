# État d'implémentation — Murphy

Dernière mise à jour : 26 juin 2026.

## Vue d'ensemble

Le **chemin critique du MVP est opérationnel** : question utilisateur → embedding →
retrieval → contexte → réponse LLM streamée + sources. Le projet est stateless,
fail-fast, sans Temporal (orchestration retirée au profit d'un service RAG simple).

| Domaine | Statut |
|---------|--------|
| Pipeline RAG (embedding → retrieval → fetch → LLM) | ✅ Opérationnel |
| Transports (WebSocket, SSE, completions JSON) | ✅ Opérationnel |
| Frontend chat (streaming, sources, timing) | ✅ Opérationnel |
| Health check + observabilité (logs Pino, `ragTiming`) | ✅ Opérationnel |
| Neo4j (enrichissement graphe) | 🟡 Provisionné, non câblé |
| A/B testing, auth, métriques sans contenu | ❌ Roadmap beta |

## Ce qui est en place

### Backend (`backend/src/`)
- **`services/chatService.ts`** — `createChatStream` : orchestration complète, production
  d'un flux de parts UI (Vercel AI SDK).
- **`services/ragService.ts`** — helpers embedding / retrieval / fetch documentaire /
  construction de contexte / system prompt.
- **`infra/`** — clients TEI (`EmbeddingClient`), Qdrant (`QdrantVectorClient`), LLM
  (`LLMProvider`, OpenAI-compatible, streaming), MongoDB. Singletons paresseux via `Proxy`.
- **Routes** (`/api/v1`) :
  - `chatWebSocket.ts` → `/chat/ws` (transport principal du frontend) ;
  - `chat.ts` → `/chat/streams` (SSE) et `/chat/completions` (JSON non-streamé) ;
  - `health.ts` → `/health` et `/health/services` ;
  - `documents.ts` → `/documents/:eli`.
- **Middleware** : requestLogger, helmet / rate-limit / CORS, `streamRateLimiter`,
  validation (`express-validator`), `errorHandler` + `notFoundHandler`.
- **Tests** : Jest avec seuils de couverture (lines/statements 65 %, functions 60 %,
  branches 40 %).

### Frontend (`frontend/src/`)
- `useRagChat.ts` : `WebSocketChatTransport` custom branché sur `useChat`
  (`@ai-sdk/react`).
- Composants `MainPanel`, `ChatBox`, `chat/` — affichage progressif de la réponse, des
  sources et du timing.
- Store `zustand` pour l'état UI.

### Données
- MongoDB et Qdrant sont **supposés pré-peuplés** (ingestion hors dépôt). Si Qdrant est
  vide, le retrieval renvoie 0 source.

## Limites assumées (à date)

- **Neo4j non branché** : provisionné dans Compose, réservé à un enrichissement de contexte
  graphe futur.
- **Pas d'historique conversationnel serveur** : stateless par conception ; seule la
  dernière question `user` est utilisée.
- **Pas de retry / fallback LLM** : fail-fast volontaire.
- **Pas d'authentification** ni de métriques d'usage.
- **GPU requis** pour le service d'embedding TEI.

## Suite

Voir [ROADMAP.md](../product/ROADMAP.md) pour les jalons et [BETA.md](../product/BETA.md) pour le backlog beta
détaillé (A/B testing prompt/retrieval, OAuth 2.0, métriques sans contenu, E2EE, tests).
