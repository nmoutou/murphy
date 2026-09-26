# Améliorations de qualité

Journal des améliorations faites et des pistes écartées. Une amélioration listée ici
n'est pas refaite. Les lots précédents (BE-01…18, FE-01…11, TR-01…07, DA-01…06) sont
dans l'historique git : `git show 9c32a83^:docs/pilotage/corrections/`.

## Faites

### 2026-09-26 — `/completions` soumis au budget de stream par IP

- **Fichiers** : `backend/src/routes/chat.ts`, `backend/src/middleware/streamRateLimiter.ts`,
  `backend/src/__tests__/middleware/streamRateLimiter.test.ts`,
  `docs/technical/backend/ARCHITECTURE.md`, `CLAUDE.md`.
- **Catégorie** : sécurité / coût (limitation de débit).
- **Fait** : `POST /api/v1/chat/completions` passe par `streamRateLimiter`, comme
  `/streams`. Les trois transports du chat (SSE, JSON, WebSocket) tirent sur le même
  budget par IP (10/min par défaut). Un test vérifie qu'une fois le budget épuisé par
  `/streams`, `/completions` répond 429 `STREAM_RATE_LIMIT_EXCEEDED` ; il échoue sans le
  correctif (400).
- **Pourquoi** : `/completions` exécute tout le pipeline (TEI, Qdrant, Mongo, puis le LLM
  payant) mais n'était couvert que par le limiteur global (100 requêtes / 15 min, sans
  limite de rafale). Un client pouvait donc lancer 100 générations d'un coup, en plus de
  son budget de stream sur `/streams` et le WebSocket. Changement d'une ligne, sans effet
  sur le frontend, qui n'utilise que le WebSocket.
- **Vérification** : `npm run check` vert avant et après (backend : 17 suites, 115 puis
  116 tests).

## Pistes écartées

- **Tests du frontend** (aucun runner aujourd'hui) : forte valeur, mais installer un
  runner (Vitest + Testing Library) touche la config, les dépendances et la CI ; à
  traiter comme un chantier dédié.
- **`readLines` (`infra/llm.ts`) perd une dernière ligne sans saut de ligne final** :
  comportement documenté ; le SSE termine chaque événement par une ligne vide, donc sans
  effet avec un fournisseur conforme.
