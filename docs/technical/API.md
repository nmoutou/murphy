# API REST & temps réel — Murphy

Base path : **`/api/v1`**. Toutes les réponses JSON passent par `buildApiResponse()`
(`backend/src/utils/response.ts`) et ont la forme :

```json
{
  "status": { "code": 200, "message": "OK" },
  "data": { },
  "meta": { "timestamp": "2026-06-26T10:00:00.000Z", "traceId": "uuid" }
}
```

`data` est omis quand il n'y a pas de charge utile.

---

## Chat & RAG

Le pipeline RAG (`createChatStream`, `backend/src/services/chatService.ts`) est exposé
par **trois transports** qui partagent exactement la même logique. Tous reçoivent un
tableau `messages` au format AI SDK (et non une chaîne `question`).

### WebSocket — `/api/v1/chat/ws` (transport principal)

C'est ce que le frontend utilise réellement (`frontend/src/hooks/useRagChat.ts`, via un
`WebSocketChatTransport` custom branché sur `useChat` de `@ai-sdk/react`).

- Le client envoie **un seul message** JSON : `{ "messages": AppUIMessage[] }`.
- Le serveur renvoie un **flux** de parts JSON (une part par trame WebSocket).
- Le socket est fermé par le serveur une fois le flux terminé.

### POST `/api/v1/chat/streams` (SSE)

Même pipeline, exposé en Server-Sent Events via `pipeUIMessageStreamToResponse` de l'AI SDK.
Utile pour des clients de test/non-WebSocket. Protégé par `streamRateLimiter` + validation
(`express-validator`).

**Requête**

```json
{
  "messages": [
    { "role": "user", "parts": [{ "type": "text", "text": "Quelle est la différence entre annulation et abrogation ?" }] }
  ]
}
```

### POST `/api/v1/chat/completions` (non-streamé)

Draine le flux côté serveur et renvoie une **réponse JSON unique** (pas de streaming).

**Réponse**

```json
{
  "status": { "code": 200, "message": "OK" },
  "data": { "role": "assistant", "parts": [{ "type": "text", "text": "L'annulation ..." }] },
  "meta": { }
}
```

### Parts du flux (contrat UI Message)

Le flux est produit avec `createUIMessageStream` (AI SDK). Les parts émises, dans l'ordre :

| `type`          | Charge utile                                                              | Rôle |
|-----------------|---------------------------------------------------------------------------|------|
| `start`         | `{ messageId }`                                                            | Début du message |
| `text-start`    | `{ id }`                                                                   | Début du bloc texte |
| `data-document` | `{ data: { chunkId, title?, type?, score } }`                             | **Une part par source**, émise *avant* le LLM |
| `text-delta`    | `{ id, delta }`                                                            | Token de la réponse LLM |
| `text-end`      | `{ id }`                                                                   | Fin du bloc texte |
| `finish`        | `{ finishReason, messageMetadata: { ragTiming } }`                        | Fin + métriques de latence |
| `error`         | `{ errorText }`                                                            | Émis à la place du reste en cas d'échec LLM |

Les sources (`data-document`) sont streamées **immédiatement après la recherche Qdrant**,
donc avant le premier token, pour que l'UI affiche les sources sans attendre la réponse.

`ragTiming` :

```typescript
type RagTiming = {
  embeddingMs: number;
  retrievalMs: number;
  docFetchMs?: number;
  llmMs?: number;
  totalMs: number;
};
```

> Le contrat de message/part est défini dans `backend/src/types/messages.ts`
> (`AppUIMessage`) et doit rester synchronisé avec `frontend/src/types/messages.ts`.

---

## Santé & monitoring

### GET `/api/v1/health`

Vérifie TEI (embeddings), Qdrant et MongoDB en parallèle.

```json
{
  "status": { "code": 200, "message": "OK" },
  "data": {
    "status": "ok",
    "services": {
      "tei": { "status": "ok" },
      "qdrant": { "status": "ok" },
      "mongodb": { "status": "ok" }
    }
  },
  "meta": { }
}
```

Logique de statut global : `ok` = tout est up, `degraded` = 1 service down,
`down` = 2 services ou plus down. Renvoie **`503`** dès que le statut n'est pas `ok`.

### GET `/api/v1/health/services`

Identique, mais chaque service porte en plus un `latencyMs` mesuré.

---

## Documents (lecture seule)

### GET `/api/v1/documents/:eli`

Récupère dans MongoDB tous les chunks d'un document par son `eli`.

```json
{
  "status": { "code": 200, "message": "OK" },
  "data": [
    { "eli": "LEGIARTI000006219120", "type": "article", "title": "Article 1", "chunk_index": 0 }
  ],
  "meta": { }
}
```

- `200` : document(s) trouvé(s)
- `404` : aucun chunk pour cet `eli`

---

## Erreurs & rate limiting

| Code | Cas |
|------|-----|
| `400` | Requête invalide (validation `express-validator`) |
| `404` | Ressource non trouvée (`notFoundHandler`) |
| `429` | Rate limit dépassé |
| `500` | Erreur interne / échec du pipeline |
| `503` | Au moins un service amont indisponible (health) |

Le rate limiting est configurable par variables d'environnement
(`RATE_LIMIT_*` global, `STREAM_RATE_LIMIT_*` pour le streaming chat). Les valeurs par
défaut vivent dans `backend/src/middleware/security.ts` et `streamRateLimiter.ts`.

> **Stateless par conception** : aucun historique conversationnel n'est stocké côté serveur,
> aucun retry automatique. Le champ `messages` peut contenir l'historique côté client, mais
> seule la dernière question `user` est utilisée par le pipeline.
