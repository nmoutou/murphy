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
npm run lint        # eslint, zéro avertissement toléré
npm test            # vitest run (Testing Library, jsdom)
npm run format      # prettier --write src
npm run format:check  # le contrôle lancé par la CI
```

Alias de chemin TS : `@/*` → `src/*`.

Le lint (`eslint.config.mjs`) vérifie les limites du CLAUDE.md : 300 lignes par fichier,
200 pour un composant (`.tsx`), 30 lignes par fonction (hors lignes vides et
commentaires), imbrication 3, 4 paramètres, complexité 10, pas de nombre magique. Les
fichiers `*.test.ts(x)` sont exemptés des règles de longueur de fonction et de nombres
magiques.

Les tests (`vitest.config.mts`) tournent sur Vite, hors de Next, dans `src/__tests__/`
qui reprend l'arborescence de `src/`. `src/__tests__/fakeWebSocket.ts` joue le backend
côté socket : `stubWebSocket()` remplace le `WebSocket` global, puis le test ouvre le
socket, envoie des parties, le fait échouer ou le ferme. `npm run check`, donc la CI,
lance les tests. Pas de seuil de couverture pour l'instant. jsdom n'implémente pas
`<dialog>` : `src/__tests__/setup.ts` simule `showModal` et `close`, qui posent et
retirent l'attribut `open`.

**Un changement de CSS ne s'affiche pas en dev ?** Le cache de Turbopack dans le
conteneur (`.next/dev`) peut rester périmé, même après un redémarrage. Il faut le
vider : `docker exec frontend rm -rf /app/frontend/.next/dev && docker restart frontend`.

### Configuration

| Variable | Défaut | Rôle |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5000` | URL de base du backend. L'adresse du WebSocket de chat en est déduite (`ws:`/`wss:` + `/api/v1/chat/ws`). Inlinée dans le bundle client : lue au démarrage par `next dev`, mais au **build** par `next build` (argument de build de l'image de production ; la changer demande de reconstruire l'image) |
