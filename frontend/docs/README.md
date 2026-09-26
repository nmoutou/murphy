# Documentation — frontend

Documentation technique du frontend de Murphy : l'interface de chat Next.js 16
(App Router) / React 19 / Tailwind v4 qui consomme le backend RAG en WebSocket.

## Quoi lire, dans quel ordre

| Document | Contenu |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Vue d'ensemble : le transport WebSocket, le contrat de messages, l'arborescence des composants. **Commencer ici.** |
| `reference/` | Références détaillées — *à écrire ; même ossature que `data/docs/reference/`.* |

La vue système globale (serving + ingestion + bases partagées) vit à la racine du dépôt :
[`docs/technical/ARCHITECTURE.md`](../../docs/technical/ARCHITECTURE.md).

---

## Opérations

### Avec Docker (stack complète)

Depuis la **racine du dépôt** (requiert `.env.dev`) : `npm run up` / `npm run watch`
/ `npm run down`. Le frontend écoute sur le port `3000` en dev. Seuls `src/` et `public/`
sont montés, avec hot-reload (`next dev`) : changer `package.json`, la config Next ou
`packages/contract` demande `npm run serve:build`.

### Sans Docker

Installer une fois **depuis la racine** : `npm install` (un seul lockfile pour les
workspaces ; le `postinstall` construit `packages/contract`). Puis, depuis `frontend/` :

```bash
npm run dev         # next dev --turbopack
npm run build       # next build --turbopack
npm run start       # next start (après build)
npm run type-check  # tsc --noEmit
npm run lint        # eslint — cassé jusqu'à FE-02
```

Alias de chemin TS : `@/*` → `src/*`.

### Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5000` | URL de base du backend. L'adresse du WebSocket de chat en est déduite (`ws:`/`wss:` + `/api/v1/chat/ws`) |
