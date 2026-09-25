# Documentation — murphy-frontend

Documentation technique du frontend de Murphy : l'interface de chat Next.js 16
(App Router) / React 19 / Tailwind v4 qui consomme le backend RAG en WebSocket.

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le transport WebSocket, le contrat de messages, l'arborescence des composants. **Commencer ici.** |
| `reference/` | Références détaillées — *à écrire ; même ossature que `data/docs/reference/`.* |

La vue système globale (serving + ingestion + bases partagées) vit dans le repo parent :
`docs/technical/ARCHITECTURE.md`.

---

## Opérations

### Avec Docker (stack complète)

Depuis la **racine du repo parent** (requiert `.env.dev`) : `npm run up` / `npm run watch`
/ `npm run down`. Le frontend écoute sur le port `3000` en dev, sources montées avec
hot-reload (`next dev`).

### Sans Docker

Depuis `frontend/` :

```bash
npm run dev      # next dev --turbopack
npm run build    # next build --turbopack
npm run start    # next start (après build)
npm run lint     # eslint
```

Alias de chemin TS : `@/*` → `src/*`.

### Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | — | URL de l'API backend |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:5000/api/v1/chat/ws` | URL du WebSocket de chat |
