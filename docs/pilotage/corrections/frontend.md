# Corrections — frontend

> Périmètre : le dossier `frontend/`. Chemins
> relatifs à `frontend/`. Index et ordre d'exécution :
> [`README.md`](README.md).

## 1. Tableau

| ID | Point | Sévérité | Statut |
|---|---|---|---|
| FE-01 | `tsc` en erreur : `components/chat/types.ts` importe un type inexistant | Bloquant | ✅ avec TR-04 |
| FE-02 | eslint ne démarre pas | Bloquant | ⬜ |
| FE-03 | Les erreurs du pipeline ne s'affichent jamais — **décidé** | Bloquant | ⬜ mini-ADR |
| FE-04 | Code mort (liste §2.4) | Dette | ⬜ |
| FE-05 | Callbacks vides propagés sur 4 niveaux | Dette | ⬜ |
| FE-06 | Bugs discrets (liste §2.6) | Dette | ⬜ |
| FE-07 | Extraction du texte d'un message dupliquée 3 fois, avec des `any` | Dette | ⬜ |
| FE-08 | Styles inline partout pour un thème unique et statique | Dette | ⬜ cascade |
| FE-09 | `WebSocketChatTransport` : états de stream incohérents | Dette | ⬜ |
| FE-10 | Accessibilité : les boutons-icônes n'ont pas de nom accessible | Confort | ⬜ |
| FE-11 | Configuration : cible ES2015, pas d'Error Boundary, formatage hétérogène | Confort | ⬜ |

## 2. Détail

### FE-01 — `tsc`

`components/chat/types.ts` importe `DocumentSource`, absent de
`types/messages.ts`. Aucun fichier n'importe `types.ts` : **le supprimer**
suffit. Les composants déclarent déjà leurs props localement.

### FE-02 — eslint

`eslint.config.mjs` passe par `FlatCompat` (`@eslint/eslintrc`) pour
charger `next/core-web-vitals`. Or `eslint-config-next` 16 exporte
directement une config *flat*, et `FlatCompat` plante en la sérialisant
(`Converting circular structure to JSON`).

- Importer `eslint-config-next/core-web-vitals` et
  `eslint-config-next/typescript` directement, avec `defineConfig` et
  `globalIgnores` de `eslint/config`.
- Retirer `@eslint/eslintrc` des `devDependencies`.
- S'attendre à de nouvelles erreurs une fois le lint réparé : au moins
  les `any` de FE-07 et de `useRagChat.ts:13`, plus les variables
  inutilisées de FE-04 et FE-05.
- Une fois le lint vert, l'ajouter au script `check` de la racine, que
  la CI lance (ADR-040).

### FE-03 — erreurs invisibles (décidé)

- Le backend signale un échec par une part `{ type: 'error', errorText }` :
  voir `chatService.ts:93` et `onError`, ainsi que `chatWebSocket.ts:31`.
- `useChat` la convertit en `status === 'error'` et en `error`.
- `useRagChat` ne renvoie pas `error`, et `MainPanel` ne regarde pas
  `status === 'error'`.
- Seul chemin vers `ErrorMessage` : un texte qui commence par « ❌ »
  (`ChatLayout.tsx:41-42`, `ErrorMessage.tsx:12`), ce que rien ne produit.

**Résultat** : si TEI, Qdrant, Mongo ou le LLM échoue, l'utilisateur voit
une bulle vide et `…` s'arrête de clignoter.

**Correction** : exposer `error` depuis `useRagChat`, puis afficher
`ErrorMessage` sous le dernier message quand `error` est défini. Retirer
la détection du préfixe « ❌ » et le `replace('❌ ', '')`. Le message
affiché reste générique ; le détail part dans `console.error`, comme
l'exige `CLAUDE.md`.

### FE-04 — code mort

| Élément | Pourquoi mort |
|---|---|
| `lib/api.ts` + `types/errors.ts` | `checkHealth` n'est importé nulle part. `NEXT_PUBLIC_API_URL` n'est lue qu'ici (voir TR-02) |
| `components/KeyComboListener.tsx` | jamais monté. Il est en plus faux : `combos` est utilisé avant sa déclaration, et l'effet ne retire pas ses écouteurs |
| `components/chat/types.ts` | voir FE-01 |
| dépendance `zustand` | aucun import |
| `quinary` … `denary` | `ThemeProvider.tsx:13-18`, jamais lues |
| prop `status` de `ChatLayout` | reçue, jamais lue |
| `theme` et `className` de `ChatContent` | inutilisés ; la branche « enfants non-string » ne sert pas non plus, seules des chaînes sont passées |
| CSS commenté | `styles/scrollbar.css:6-25` |
| `--background` / `--foreground` | `globals.css:4-5,11-12` : jamais définies |
| commentaire modèle | `next.config.ts:4` |
| `<head><meta charSet>` | `app/layout.tsx:24-26` : Next l'émet déjà |

### FE-05 — callbacks vides

`MainPanel` crée `handleSourceClick` et `handleCopy`, deux no-ops
(`MainPanel.tsx:23-29`). Ils sont transmis à `ChatLayout`, puis
`AIMessage`, `SourcesList` et `SourceItem` : 4 niveaux, là où `CLAUDE.md`
en autorise 2.

- **`onSourceClick`** : le supprimer sur toute la chaîne. Retirer aussi
  le `cursor-pointer` de `.source-item`, qui promet un clic sans effet.
  La fonctionnalité reviendra avec sa conception.
- **`onCopy`** : `AIMessage` copie déjà lui-même. Retirer le callback et
  toujours afficher le bouton de copie. Au passage, `AIMessage` n'attend
  pas `navigator.clipboard.writeText`, qui est une promesse non gérée.

### FE-06 — bugs discrets

| Emplacement | Défaut | Correction |
|---|---|---|
| `icons/Logo.tsx:9` | `height` est calculée à partir de `LOGO_DEFAULT_WIDTH`, pas de `width` | `width * LOGO_RATIO` |
| `chat/SourcesList.tsx:28` | `key={idx}`, interdit par `CLAUDE.md` | `key={chunk.chunkId}` |
| `layouts/ChatLayout.tsx:38` | `key={message.id ?? index}`, alors que `id` est toujours défini | `key={message.id}` |
| `ChatBox.tsx:26-38` | « Entrée » est écoutée sur **tout le `document`** : elle soumet même quand le focus est ailleurs, et ignore `NumpadEnter` (`e.code == "Enter"`, avec `==`) | un `<form onSubmit>` autour du champ |
| `ChatBox.tsx:12` | la prop `absolute` produit un `fixed` | la renommer `isDocked` |
| `app/layout.tsx:27-31` | `ThemeProvider`, un composant client, est placé entre `<html>` et `<body>` | le placer dans `<body>`, ou le supprimer (FE-08) |
| `globals.css:13` | `font-family: Arial` sur `body` écrase la police Geist chargée dans `layout.tsx` | utiliser `var(--font-sans)` |
| `styles/scrollbar.css:1-3` | les directives `@tailwind` sont la syntaxe v3 ; en v4, `@layer utilities` devient `@utility` | fusionner dans `globals.css` avec `@utility scrollbar` |

### FE-07 — texte d'un message

`AIMessage.tsx:16-27`, `UserMessage.tsx:12-17` et `ChatLayout.tsx:41-42`
extraient chacun le texte des `parts`, avec `(part: any)`. Comme
`AppUIMessage` est typé, `part.type === 'text'` suffit à restreindre le
type, sans `any` ni cast. Écrire une seule fonction
`getMessageText(message)`, à côté de `types/messages.ts`. De même,
`part.type === 'data-document'` donne `part.data` typé `DocumentChunk`.

### FE-08 — styles inline

Le thème est **unique et statique** (`darkTheme`), mais ses couleurs
passent par `style={{ … }}` dans 7 composants : `ChatBox`, `ChatBubble`,
`SourceItem`, `SourcesList`, `MainPanel`, `ButtonIcon` et `Logo`/`Icon`
via `theme.name`. `CLAUDE.md` interdit les styles inline quand les
valeurs ne sont pas calculées.

**Cible** : déclarer les couleurs comme variables dans le `@theme` de
`globals.css`, puis utiliser des classes Tailwind (`bg-secondary`,
`text-tertiary`…). `ThemeProvider` et `useTheme` n'ont alors plus de
raison d'exister : le contexte ne sert qu'à lire des constantes. Le
filtre `invert` sur les icônes devient une classe fixe. Cascade :
environ 10 fichiers ; si un thème clair arrive un jour, il se fera
en CSS (`prefers-color-scheme`).

### FE-09 — `WebSocketChatTransport`

`hooks/useRagChat.ts`

- **Transport recréé à chaque rendu** (l. 65) : `useChat` ne garde que
  le premier, les suivants sont construits pour rien. En faire une
  constante de module.
- **Promesse sans objet** (l. 13-55) : le `new Promise` résout
  immédiatement, et le `reject` de `onerror` arrive après la
  résolution, donc il est sans effet. Une fonction `async` qui renvoie
  le stream suffit.
- **Fermeture sur un stream en erreur** : `onerror` appelle
  `controller.error()`, puis `onclose` appelle `controller.close()` sur
  ce stream déjà en erreur, ce qui lève une `TypeError` non capturée. Il
  faut une garde d'état.
- **Typage** : `ReadableStream<any>` → `ReadableStream<UIMessageChunk>`.
  Le `JSON.parse` des messages entrants, qui marque la frontière du
  système, gagne à vérifier au minimum la présence de `type`.

### FE-10 — accessibilité

`Icon` rend l'image avec `aria-hidden` **et** un `alt`. Dans
`ButtonIcon`, le seul contenu du bouton est donc masqué, et le bouton n'a
aucun nom accessible. Poser `aria-label={alt}` sur le `<button>` et
laisser l'image décorative (`alt=""`).

### FE-11 — configuration

- `tsconfig.json:3` : la cible `es2015` devient `es2017`, la valeur par
  défaut de Next. Retirer `allowJs`, qui ne sert à aucun fichier `.js`.
- Aucune Error Boundary : `CLAUDE.md` en exige une par page. Ajouter
  `app/error.tsx`.
- Le formatage est hétérogène : 2 ou 4 espaces, guillemets `"` ou `'`,
  points-virgules présents ou non selon les fichiers. Un passage de
  Prettier, en un commit dédié, sans aucun autre changement.
