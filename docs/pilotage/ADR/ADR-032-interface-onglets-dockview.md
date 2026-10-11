# ADR-032 — L'interface du moteur de recherche : un espace d'onglets Dockview

**Statut** : ✅ Accepté (11 octobre 2026) — réalise ADR-028 §10 côté frontend, amende
ADR-030 §2 et §3 et ADR-017 §2 à §4 · ferme le point ouvert « Interface du frontend
adaptée au pivot »

## Contexte

Depuis ADR-030, le backend est une API de recherche paginée. Le frontend est resté un
chat : il compile, mais il cherche un WebSocket qui n'existe plus (ADR-030 §8). Son
apparence ne correspond pas non plus à ce que doit être Murphy.

Les maquettes v0.3 (`docs/pilotage/WIP/maquettes - v0.3.png`) décrivent l'interface :

- **L'accueil** : le logo ASCII et une barre de recherche centrée (« Nul n'est censé
  ignorer la loi »).
- **L'espace de travail** : un en-tête (logo, barre de recherche, sélecteur « Résultats
  par page »), puis un espace d'onglets : Résultats, Graphe, Explication. Chaque groupe
  d'onglets porte un bouton de scission et un menu « … ».
- **Un résultat** : un menu « … », une pastille, une icône, le titre en police mono, un
  extrait de quelques lignes.
- **La pagination**, au pied du panneau Résultats :
  `|<  ‹ Précédent  1 2 3 … X  Suivant ›  >|`.
- **La vue scindée** : Résultats et Explication à gauche, Graphe à droite, avec des
  contrôles de zoom.
- **Le mobile et la tablette** : la même structure ; sur mobile, la scission est
  horizontale.

Les maquettes ne montrent pas l'ouverture d'un document, que prévoit ADR-028 §9 (« le
texte entier au clic »). Elle fait partie de cette ADR.

Cinq contraintes pèsent sur les choix :

- **La question ne passe jamais par l'URL** (ADR-010, ADR-030 §1) : ni route
  `/recherche?q=`, ni état de recherche dans l'historique.
- **Le système est sans état et sans cache** (ADR-010) : chaque recherche et chaque
  ouverture de document interroge le backend.
- **La taille de page est fixée par le serveur** (ADR-030 §2), alors que les maquettes
  laissent l'utilisateur la choisir.
- **L'API ne dit pas si un texte est en vigueur**, alors que la pastille l'affiche.
- **Les limites de l'ESLint du frontend** : 200 lignes par `.tsx`, 30 par fonction,
  profondeur 3.

## Décision

### 1. Deux écrans, une seule route

`/` affiche l'**accueil** tant qu'aucune recherche n'a été lancée, puis l'**espace de
travail**. Les deux sont deux états d'un même écran, pas deux routes : la question ne
peut pas passer par l'URL.

- La première recherche ouvre l'espace de travail, même si elle échoue : la modale
  s'affiche sur une liste vide.
- Un rechargement ramène à l'accueil. Le bouton « retour » du navigateur ne revient pas
  de l'espace de travail à l'accueil.
- L'en-tête de l'espace de travail porte la barre de recherche ; une nouvelle question
  remplace la précédente, sans quitter l'espace de travail.
- Les polices restent Geist et Geist Mono.

### 2. Dockview porte la disposition

L'espace de travail est un `DockviewReact`, du paquet `dockview-react` : depuis la v8,
`dockview` ne porte plus les liaisons React. C'est un simple composant client : Dockview
ne touche au DOM qu'au montage, son rendu serveur est un `<div>` vide, et `next/dynamic`
n'est pas nécessaire. Son thème reprend les couleurs du `@theme` de `globals.css`.

- **Un registre de types de panneaux** : `results`, `graph`, `explanation`, `document`.
  Chaque type déclare son composant, son titre et son icône. C'est le seul module, avec
  l'espace de travail, qui connaît Dockview ; les panneaux l'ignorent.
- **La disposition par défaut** : un groupe, trois onglets (Résultats, Graphe,
  Explication), Résultats actif.
- **Chaque état a un seul détenteur** :
  - Dockview détient la disposition : les panneaux ouverts, leurs groupes, l'onglet actif ;
  - les paramètres d'un panneau portent ses propres données (pour un document :
    `{ identifier, passage }`) ;
  - le store de recherche (§7) détient le reste.
- **Rien n'est retenu** d'une visite à l'autre : ni la disposition, ni la recherche.

### 3. Les actions d'un groupe

- **Scinder** déplace l'onglet actif dans un nouveau groupe, à droite, ou en dessous sur
  un écran étroit. Le bouton est désactivé quand le groupe n'a qu'un onglet.
- **Le menu « … »** liste les panneaux fixes (Résultats, Graphe, Explication) qui ne sont
  ouverts nulle part, et les rouvre dans ce groupe. Tous les onglets se ferment, Résultats
  compris.
- **Un espace vide** : quand le dernier onglet est fermé, il ne reste plus de groupe, donc
  plus de menu. Le `watermark` de Dockview prend le relais et propose la même liste.

### 4. L'onglet Résultats

Une liste dans l'ordre du classement, puis la pagination. Chaque résultat se compose de
cinq éléments :

- **Un menu « … »**, sans option pour l'instant.
- **Une pastille** : verte si `isInForce` vaut `true`, rouge s'il vaut `false`, aucune
  s'il est absent (§9).
- **Une icône**, choisie par la nature quand elle en a une, par `documentType` sinon. La
  table des natures est partielle et se complète au fil de l'eau ; celle des types est
  exhaustive, et le compilateur la vérifie. Une nature inconnue prend l'icône de son type.
- **Le titre**, qui ouvre l'onglet du document (§5).
- **Le premier passage**, le mieux classé, coupé à quelques lignes. L'API continue
  d'envoyer tous les passages : le poids est négligeable, et le contrat ne bouge pas. Un
  document sans passage correspondant n'affiche que son titre.

**La pagination** affiche la première et la dernière page, la page courante et ses
voisines, avec une ellipse pour les trous. Changer de page relance la recherche.

**Le sélecteur « Résultats par page »**, dans l'en-tête, propose les tailles que
transmet la réponse (§8). En changer relance la recherche à la page 1.

### 5. L'onglet document

- **L'ouverture** : un clic sur le titre d'un résultat ouvre un panneau `document`, dans
  le groupe de l'onglet Résultats, ou dans le groupe actif si Résultats est fermé. Son identifiant est `document:<identifier>` : un second
  clic active l'onglet déjà ouvert.
- **L'onglet** porte le titre du document, tronqué (le titre complet en infobulle), et
  l'icône du §4.
- **Le contenu** : `GET /api/v1/documents/:identifier` à chaque ouverture, sans cache.
  Le passage affiché dans le résultat est surligné, grâce à ses offsets `start`/`end`
  (UTF-16, ADR-030 §3), et l'onglet défile jusqu'à lui.
- **Une nouvelle recherche** laisse les onglets document ouverts.
- **Une erreur** (404 `DOCUMENT_NOT_FOUND`, backend injoignable…) affiche la modale (§10),
  puis l'onglet se ferme.

### 6. Graphe et Explication : deux amorces vides

Les deux panneaux existent dans le registre et dans la disposition par défaut, mais
n'affichent rien.

- **Le Graphe** lira les relations de Neo4j, que le backend ne lit pas encore.
- **L'Explication** réintégrera un LLM, plus contrôlé que celui qu'a retiré ADR-028 §9.

Chacun aura sa propre ADR.

### 7. L'état : un store Zustand en mémoire

Zustand entre dans le frontend, sans `persist`. La persistance côté client viendra plus
tard, sous la forme d'un middleware, sans réécrire le store.

- **Le store de recherche** détient la question, la page, la taille de page, le statut
  (`idle`, `loading`, `success`, `error`) et la réponse ; l'erreur va au store d'erreurs
  (§10). Ses actions sont
  `submit(question)`, `goToPage(page)` et `setPageSize(size)`.
- **Une requête chasse la précédente** : un `AbortController` côté client empêche une
  réponse en retard d'écraser la plus récente. Le backend n'en sait rien (ADR-030 §6).
- **Les couches** : les composants lisent le store ; le store appelle `lib/api`, qui fait
  les `fetch` et valide les réponses avec les schémas de `@murphy/contract/search`. Aucun
  composant n'appelle `fetch`.
- **Un panneau** lit le store et ses propres paramètres, jamais l'état de Dockview.

### 8. La taille de page vient de la requête (amende ADR-030 §2)

- **La configuration** : `PAGINATION_SIZES` (par défaut `10,25,50`) remplace
  `PAGINATION_SIZE`. La première taille sert par défaut. Chaque taille doit être un
  entier positif inférieur ou égal à `PAGINATION_DEPTH`, sinon le démarrage est refusé.
- **La requête** : `{ question, page?, pageSize? }`. Un `pageSize` absent prend la taille
  par défaut ; un `pageSize` hors de la liste reçoit un 400 `VALIDATION_ERROR` (champ
  `pageSize`).
- **La réponse** transmet `pageSize` et `pageSizes`. Le sélecteur n'apparaît qu'après une
  première recherche : il a toujours ses valeurs à temps, sans route de plus.
- **`pageCount = ⌈PAGINATION_DEPTH / pageSize⌉`**, et la dernière page est tronquée :
  `size = min(pageSize, PAGINATION_DEPTH − from)`. `from + size` ne dépasse toujours pas
  la profondeur, et aucun document n'est perdu : avec 30 par page et une profondeur de
  100, la page 4 contient les 10 derniers. `PAGE_OUT_OF_RANGE` dépend désormais de
  `pageSize`.
- La profondeur, et donc le `k` du k-NN, ne change pas d'une taille à l'autre : le
  classement reste le même.

### 9. Un résultat dit s'il est en vigueur (amende ADR-030 §3)

Un résultat gagne le champ optionnel `isInForce`, tiré du `metadata.statut` du document
dans Mongo (le `ETAT` de la DILA) :

- `true` si le statut est `VIGUEUR` ;
- `false` pour tout autre statut : `VIGUEUR_DIFF` (vigueur à venir), `ABROGE`, `MODIFIE`…
- absent quand le document n'a pas de statut, comme une décision de justice.

Le backend interprète le statut, parce que c'est une règle métier ; le frontend
n'affiche qu'une couleur. La lecture dans Mongo existe déjà (étape 4 du pipeline) : sa
projection gagne `metadata.statut`.

### 10. Les erreurs restent dans une modale (amende ADR-017 §2 à §4)

La modale générique d'ADR-017 §1 reste. Elle ne nomme plus une étape, mais traduit le
code d'erreur de l'API (ADR-030 §4) :

| Codes | Message |
|---|---|
| `VALIDATION_ERROR`, `INVALID_JSON`, `INVALID_REQUEST_BODY`, `PAYLOAD_TOO_LARGE`, `PAGE_OUT_OF_RANGE` | La recherche n'a pas pu être lancée. |
| `SEARCH_RATE_LIMIT_EXCEEDED`, `RATE_LIMIT_EXCEEDED` | Trop de recherches : réessayez dans une minute. |
| `DOCUMENT_NOT_FOUND`, `NOT_FOUND` | Ce document est introuvable. |
| `EMBEDDING_FAILED`, `SEARCH_FAILED`, `DB_FETCH_FAILED`, `TIMEOUT` | Le service de recherche est indisponible. |
| `CONTRACT_VIOLATION`, `INTERNAL` | Une erreur interne est survenue. |
| `NETWORK` (frontend seul) | Le serveur est injoignable. |

- La table est un `Record<SearchErrorCode, string>` : un code ajouté au contrat casse le
  build tant qu'il n'a pas de message. Une réponse illisible, ou qui viole le schéma,
  donne `INTERNAL`.
- Une seule modale, alimentée par un store d'erreurs, sert la recherche et les documents.
- Le code et le détail partent dans `console.error`. Il n'y a pas de bouton
  « Réessayer » : l'utilisateur relance sa recherche.
- **Après une erreur de recherche**, la liste est vidée et la question reste dans la
  barre. **Après une erreur de document**, l'onglet se ferme (§5).

### 11. Le chat part, et l'ancien contrat avec lui

Disparaissent :

- `components/chat/*`, `ChatBox`, `MainPanel`, `layouts/` ;
- `useRagChat`, `useChatInput`, `webSocketChatTransport`, `chatSocketUrl`,
  `chatErrorStage`, `messageText` ;
- `__tests__/fakeWebSocket.ts` et les tests de ces modules ;
- les dépendances `ai`, `@ai-sdk/react`, `react-markdown` et `remark-gfm` ;
- les sous-chemins `@murphy/contract/messages` et `@murphy/contract/errors`, qu'ADR-030
  §7 gardait gelés pour le frontend.

`documentTypeLabels` importe désormais `DocumentType` de `@murphy/contract/search`.
`NEXT_PUBLIC_API_URL` reste l'unique configuration du frontend.

### 12. L'arborescence

Le code est rangé par domaine fonctionnel. Les dépendances vont de l'interface vers le
store, puis vers `lib/api`, jamais dans l'autre sens.

```
src/
  app/
    layout.tsx
    page.tsx                  écran d'accueil ou espace de travail
  lib/api/                    fetch, validation zod, code d'erreur
  stores/                     Zustand : searchStore (§7), errorStore (la modale, §10)
  features/
    home/                     HomeScreen
    workspace/                WorkspaceScreen, WorkspaceHeader, Workspace (Dockview),
                              panelRegistry, defaultLayout, onglet, actions du groupe,
                              watermark
    results/                  ResultsPanel, ResultList, ResultItem, InForceDot,
                              DocumentIcon, Pagination, PageSizeSelect
    document/                 DocumentPanel, surlignage du passage
    graph/                    GraphPanel (vide)
    explanation/              ExplanationPanel (vide)
    errors/                   ErrorDialog, messages par code
  components/
    ui/                       SearchBar, Modal : des briques sans métier
    icons/                    Icon, ButtonIcon, AnimatedIcon, Logo (déjà en place)
```

- Seul `features/workspace/` importe Dockview.
- **Le registre adapte les panneaux.** Pour chaque type, un adaptateur reçoit les props
  de Dockview et rend le panneau avec des props simples : ses paramètres et ses rappels (`onOpenDocument`, `onError`). Les panneaux
  n'importent ni Dockview, ni `features/workspace/`, ni un autre panneau : les
  dépendances vont de `workspace/` vers les panneaux, jamais l'inverse.
- **Un résultat ouvre un document** par `onOpenDocument(result)`. L'adaptateur le relie
  à `openDocument`, avec l'API de Dockview qu'il reçoit dans ses props (`containerApi`) :
  aucun contexte React n'est nécessaire. `openDocument` tire du résultat les paramètres
  du panneau `document` (`{ identifier, documentType, nature, passage }`).
- Les tests suivent l'arborescence dans `src/__tests__/`. Les panneaux se testent hors de
  Dockview ; `Workspace` se teste a minima, avec un `ResizeObserver` simulé (jsdom n'en
  a pas).

## Alternatives rejetées

- **Des onglets faits maison** : pas de scission, pas de glisser-déposer, et tout à
  maintenir.
- **FlexLayout, react-mosaic, Golden Layout** : react-mosaic découpe l'espace mais n'a
  pas d'onglets ; Golden Layout n'est pas écrit pour React ; FlexLayout conviendrait, mais
  Dockview fournit en plus les actions de groupe et le `watermark` dont le §3 a besoin.
- **Deux routes, `/` et `/recherche`** : sans question dans l'URL, `/recherche` chargée
  directement serait vide.
- **Un contexte React maintenant, Zustand plus tard** : le store serait écrit deux fois.
- **TanStack Query** : son cache va contre le principe sans état (ADR-010), et une seule
  recherche à la fois n'en a pas besoin.
- **Une route `GET /search/options`** pour les tailles de page : un appel de plus à
  l'accueil, qui n'affiche pas le sélecteur.
- **Garder `⌊profondeur / taille⌋`, avec des tailles qui divisent la profondeur** : une
  contrainte de plus au démarrage, pour un problème que la dernière page tronquée résout.
- **Une taille libre, bornée par un maximum** : le sélecteur a besoin d'une liste.
- **Le statut DILA brut dans le contrat** : le frontend interpréterait une règle métier.
- **Un seul passage dans l'API** : un contrat de plus à changer, pour un gain de poids
  négligeable.
- **Les erreurs affichées dans le panneau** : la modale reste cohérente avec ADR-017.
- **L'onglet document dans un groupe à part** : la vue scindée resterait au choix de
  l'utilisateur.
- **Interdire la fermeture du dernier onglet** : le `watermark` laisse l'utilisateur
  libre, sans cas particulier.
- **Retenir la disposition dès maintenant** : elle viendra avec la persistance de
  Zustand.
- **Les polices des maquettes** : celles en place conviennent.

## Conséquences

La migration se fait en cinq lots, commités chacun à part. `npm run check` reste vert
après chacun.

**Lot 1 — L'API : taille de page et vigueur.**
- `config.ts` lit `PAGINATION_SIZES` et la valide ; `PAGINATION_SIZE` disparaît
  (`docker-compose.base.yml`, et `.env.dev`, à la charge du développeur).
- `searchService` calcule `pageCount` et la taille de la dernière page à partir de
  `pageSize`.
- La projection Mongo lit `metadata.statut` ; `toSearchResult` en tire `isInForce`.
- `@murphy/contract/search` : `pageSize` dans la requête, `pageSize`, `pageSizes` et
  `isInForce` dans la réponse.
- Tests du backend ; `docs/technical/backend/` et `index-opensearch.md` (la taille de
  page) suivent.

**Lot 2 — Le chat part, l'espace de travail arrive.**
- Les retraits du §11. Les dépendances `dockview-react` et `zustand` entrent.
- Accueil, en-tête, `Workspace`, registre, disposition par défaut, actions de groupe,
  `watermark`. Les quatre panneaux sont vides.
- Store de recherche, `lib/api`, modale d'erreur.

**Lot 3 — L'onglet Résultats.**
- Liste, pastille, icône, premier passage, pagination, sélecteur de taille.

**Lot 4 — L'onglet document.**
- Ouverture, chargement, surlignage, défilement, fermeture sur erreur.

**Lot 5 — Documentation.**
- `CLAUDE.md`, `docs/technical/ARCHITECTURE.md`, `docs/technical/frontend/` décrivent
  l'espace de travail ; les mentions du frontend gelé disparaissent.
- `INDEX.md` : le point ouvert est fermé ; les statuts d'ADR-017 et d'ADR-030 citent les
  amendements.
- Vérification dans le navigateur : une recherche, la pagination, un changement de
  taille, l'ouverture d'un document, une scission, la fermeture puis la réouverture
  d'un onglet, une erreur (backend arrêté).

**Restent ouverts** :
- la liste complète des icônes par nature, qui se complète au fil de l'eau ;
- les options du menu « … » d'un résultat ;
- le contenu des onglets Graphe et Explication (§6).

## Références

ADR-010 (stateless, confidentialité) · ADR-017 (erreurs en modale) · ADR-028 (OpenSearch,
sans LLM) · ADR-030 (API de recherche)

- Maquettes v0.3 : `docs/pilotage/WIP/maquettes - v0.3.png`
- [Dockview](https://dockview.dev) — `DockviewReact`, `watermarkComponent`,
  `rightHeaderActionsComponent`
- [Zustand](https://zustand.docs.pmnd.rs)
