# Architecture — frontend

## Ce que c'est

L'UI conversationnelle de Murphy : une question posée, un flux de réponse streamé avec
ses **sources affichées avant la réponse** (le backend émet les documents avant de lancer
le LLM). Next.js 16 (App Router), React 19, Tailwind v4.

## Le transport : WebSocket sur `useChat`

Le cœur vit dans `src/hooks/useRagChat.ts` : un `WebSocketChatTransport` custom branché
sur `useChat` de `@ai-sdk/react`. Une question envoyée sur
`/api/v1/chat/ws` (`NEXT_PUBLIC_WS_URL`), un flux de parts JSON reçu (format
UI-message-stream du Vercel AI SDK), socket fermée en fin de réponse. Pas d'historique
côté serveur : le backend est stateless, la conversation vit dans l'état du client.

## Le contrat de messages

`src/types/messages.ts` définit `AppUIMessage` — **à garder synchronisé** avec
`backend/src/types/messages.ts` :

- parts `text-delta` : les tokens du LLM ;
- parts custom `data-document` `{ document: DocumentChunk }` : les sources, émises avant
  la génération ;
- part `finish` avec metadata `{ ragTiming }` : latences par étape du pipeline RAG.

Les erreurs typées vivent dans `src/types/errors.ts`.

## Arborescence des composants

```
src/
├── app/                    # App Router : layout.tsx, page.tsx
├── hooks/useRagChat.ts     # le transport WS + l'état du chat
├── types/                  # messages.ts (contrat backend), errors.ts
├── lib/api.ts              # appels HTTP hors chat
├── components/
│   ├── MainPanel.tsx, ChatBox.tsx        # entrée + panneau principal
│   ├── chat/               # ChatContent, ChatBubble, AIMessage, UserMessage,
│   │                       # SourcesList/SourceItem (les documents), ErrorMessage
│   ├── layouts/            # WelcomeLayout (accueil) / ChatLayout (conversation)
│   ├── providers/ThemeProvider.tsx
│   └── icons/
└── styles/                 # globals.css, scrollbar.css (Tailwind v4)
```

L'état UI est géré par `zustand` ; le thème par `ThemeProvider`.
