# Architecture — frontend

## Ce que c'est

L'UI conversationnelle de Murphy : une question posée, un flux de réponse streamé avec
ses **sources affichées avant la réponse** (le backend émet les documents avant de lancer
le LLM). Next.js 16 (App Router), React 19, Tailwind v4.

## Le transport : WebSocket sur `useChat`

Le cœur vit dans `src/hooks/useRagChat.ts` : le transport custom
`src/lib/webSocketChatTransport.ts`, branché sur `useChat` de `@ai-sdk/react`. Une
question envoyée sur
`/api/v1/chat/ws` (l'adresse est déduite de `NEXT_PUBLIC_API_URL` par
`src/lib/chatSocketUrl.ts`), un flux de parts JSON reçu (format
UI-message-stream du Vercel AI SDK), socket fermée en fin de réponse. Pas d'historique
côté serveur : le backend est stateless, la conversation vit dans l'état du client.

Le flux lu par `useChat` se règle **une seule fois** :
- il est fermé après la part `finish` ou `error`, ou sur un arrêt ;
- il passe en erreur quand le socket échoue ou se ferme avant la fin de la réponse.

Fermer le socket (bouton d'arrêt, erreur) arrête aussi le pipeline côté backend, LLM
compris (ADR-041).

## Les erreurs : une modale (ADR-041)

Le chemin d'une erreur, du backend jusqu'à l'écran :
1. Une part `error` porte `{ stage, code }` (`@murphy/contract/errors`), et `useChat`
   passe en `status: 'error'`.
2. `lib/chatErrorStage.ts:readErrorStage` en tire l'étape à afficher. Un socket en échec
   donne `connection`, un texte hors contrat donne `internal`.
3. `useRagChat` retire la bulle de l'IA (`onFinish`, `isError`), logue l'erreur avec
   `console.error`, et expose `errorStage` et `clearError`.
4. `MainPanel` monte `ErrorDialog`, une phrase par étape, dans `components/ui/Modal.tsx`.
   Fermer la modale efface l'erreur.

`Modal` est la coquille commune des fenêtres modales :
- elle repose sur l'élément `<dialog>` et `showModal()` : fond grisé, page inerte,
  focus piégé, fermeture par Échap ;
- elle affiche un titre et un bouton « Fermer » ;
- son contenu est libre (`children`) ;
- montée, elle est ouverte : c'est le parent qui décide de l'afficher.

## Le contrat de messages

`AppUIMessage` vient de `@murphy/contract/messages` (`packages/contract/`, ADR-040),
partagé avec le backend : une modification casse la compilation des deux côtés à la
fois. `useRagChat` passe ses schémas zod à `useChat` (`dataPartSchemas`,
`messageMetadataSchema`) : une part qui ne respecte pas le contrat est rejetée à
l'arrivée.

- parts `text-delta` : les tokens du LLM ;
- parts custom `data-parentDocument` `{ parentDocument: ParentDocument }` : le document
  entier d'où viennent des passages, une fois par document, avant ses passages (pas
  encore affiché) ;
- parts custom `data-document` `{ document: DocumentChunk }` : les passages, émis avant
  la génération, avec leurs offsets UTF-16 dans le `content` du parent ;
- part `finish` avec metadata `{ ragTiming }` : latences par étape du pipeline RAG.

## Arborescence des composants

```
src/
├── app/                    # App Router : layout.tsx, page.tsx
├── hooks/useRagChat.ts     # l'état du chat, l'erreur à afficher
├── lib/                    # webSocketChatTransport.ts, chatSocketUrl.ts (adresse du
│                           # WebSocket), chatErrorStage.ts, messageText.ts
├── components/
│   ├── MainPanel.tsx, ChatBox.tsx        # panneau principal + formulaire de question
│   ├── chat/               # ChatContent, ChatBubble, AIMessage, UserMessage,
│   │                       # SourcesList/SourceItem (les documents), ErrorDialog
│   ├── ui/Modal.tsx        # la coquille des fenêtres modales
│   ├── layouts/            # WelcomeLayout (accueil) / ChatLayout (conversation)
│   └── icons/              # Icon, AnimatedIcon (décoratives), ButtonIcon, Logo
└── styles/globals.css      # Tailwind v4 : @theme, @utility scrollbar, classes du chat
```

## Styles et accessibilité

- **Couleurs** : le thème, unique et sombre, est déclaré dans le `@theme` de
  `globals.css`. Les composants emploient des classes Tailwind (`bg-secondary`,
  `text-tertiary`…). Il n'y a pas de contexte de thème ni de style inline.
- **Police** : Geist, chargée par `next/font` dans `app/layout.tsx`, et appliquée par
  `font-sans` sur le `body`.
- **Icônes** : `Icon` et `AnimatedIcon` sont décoratives (`alt=""`). Un bouton-icône
  porte son nom accessible (`ButtonIcon`, prop `label` → `aria-label`).
- **Saisie** : le `ChatBox` est un `<form>`. « Entrée » soumet depuis le champ, et une
  question vide n'est pas envoyée.
