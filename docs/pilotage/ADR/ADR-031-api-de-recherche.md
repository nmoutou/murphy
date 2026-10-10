# ADR-031 — Une API de recherche paginée : le LLM et le flux partent

**Statut** : ✅ Accepté (10 octobre 2026) — réalise l'étape 2 d'ADR-028 (§9-§10), amende
ADR-028 §7 et ADR-017 §2 et §5

## Contexte

ADR-028 fait de Murphy un moteur de recherche : une question donne des documents classés
et leurs passages. Son étape 1 est faite : OpenSearch sert la recherche hybride derrière
le contrat du chat (`AppUIMessage`), et le LLM reste branché. Son §9 renvoie à une ADR
dédiée l'API qui remplace le flux : ses routes, son contrat, et le retrait du WebSocket,
du SSE et de l'AI SDK. C'est celle-ci.

Depuis l'amendement du 10 octobre d'ADR-028 §10, la page de résultats et toute
l'interface relèvent d'ADR-030, qui suivra le remplacement du modèle d'embedding. Cette
ADR ne touche que le backend et le contrat.

Trois traits du code actuel pèsent sur les choix :

- `requestLogger` journalise `req.url` et `req.query` : une question dans l'URL finirait
  dans les logs, contre la confidentialité structurelle d'ADR-010.
- Un document trouvé sans passage correspondant envoie tous ses passages (ADR-028 §7),
  pour remplir le contexte du LLM. Une décision entière dépasse 140 000 caractères.
- Le limiteur général (100 requêtes par 15 minutes et par IP) couvre toutes les routes :
  une question, sa pagination et les documents ouverts l'épuisent vite.

## Décision

### 1. Deux routes

- **`POST /api/v1/search`**, corps `{ question, page? }`. La question ne passe jamais
  par une URL : ni les logs d'accès, ni un proxy, ni l'historique ne la gardent.
- **`GET /api/v1/documents/:identifier`** renvoie `{ identifier, title, content }`, lus
  dans Mongo seul. Le texte entier n'est servi qu'à la demande. Un identifiant inconnu
  reçoit un 404. Les logs d'accès gardent l'identifiant consulté, pas la question.

Les réponses gardent l'enveloppe de `buildApiResponse` (`status`, `data`, `meta`).

### 2. Une pagination par numéro de page

`page` vaut 1 par défaut. Le backend en tire `from = (page - 1) × PAGINATION_SIZE` ;
`size` et `pagination_depth` ne sortent pas du serveur, et la profondeur reste la même
d'une page à l'autre (ADR-028 §8).

La réponse porte `page` et `pageCount = ⌊PAGINATION_DEPTH / PAGINATION_SIZE⌋` (10 avec
les valeurs actuelles) : `from + size` ne dépasse jamais la profondeur. Une page au-delà
de `pageCount` reçoit un 400 ; une page en deçà mais au-delà des documents trouvés rend
une liste vide.

### 3. Un résultat : le document et ses passages correspondants

```json
{
  "page": 1,
  "pageCount": 10,
  "results": [
    {
      "identifier": "JURITEXT000048123456",
      "title": "Cour de cassation, …",
      "documentType": "decision",
      "nature": "ARRET",
      "passages": [{ "chunkId": "…", "text": "…", "start": 1204, "end": 1580 }]
    }
  ]
}
```

- Les résultats suivent le classement RRF, et leurs passages celui d'ADR-028 §7.
- `start` et `end` sont les offsets UTF-16 du passage dans le `content` du document
  (ADR-015) : le client surligne le texte chargé par la seconde route.
- **Un document trouvé sans passage correspondant** (par son titre, ses métadonnées)
  **a une liste vide.** Envoyer tous ses passages servait le LLM ; son texte se lit
  désormais au clic. Combien de passages afficher relève d'ADR-030.
- Ni score (ADR-028 §7), ni durées : les durées par étape restent dans les logs.

Le pipeline ne change pas : embedding, recherche, lecture du titre et du texte dans
Mongo, découpe des passages. Seuls le LLM et l'écriture du flux disparaissent.

### 4. Une erreur : un statut HTTP et un code

Le code est le `status.message` de l'enveloppe ; ni étape ni message brut ne sortent.
L'étape reste sur la `RagError`, dans les logs.

| Statut | Codes |
|---|---|
| 400 | `VALIDATION_ERROR` (question vide comprise), `INVALID_JSON`, `PAGE_OUT_OF_RANGE` |
| 404 | `DOCUMENT_NOT_FOUND` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 429 | `SEARCH_RATE_LIMIT_EXCEEDED`, `RATE_LIMIT_EXCEEDED` |
| 502 | `EMBEDDING_FAILED`, `SEARCH_FAILED`, `DB_FETCH_FAILED` |
| 504 | `TIMEOUT` |
| 500 | `CONTRACT_VIOLATION`, `INTERNAL` |

Le code `NETWORK` de l'embedding devient `EMBEDDING_FAILED` : sans étape, il ne dirait
plus de quel service il s'agit.

### 5. Des budgets à la mesure d'une recherche

- **Recherche** : 60 par minute et par IP. `STREAM_RATE_LIMIT_*` devient
  `SEARCH_RATE_LIMIT_*` et ne compte que `POST /search`.
- **Général** : 600 par 15 minutes et par IP (`RATE_LIMIT_MAX`). Ouvrir un document
  n'en relève que lui.

Ce sont les valeurs par défaut ; l'environnement les remplace, comme aujourd'hui.

### 6. Plus d'abandon propagé

Sans LLM, une recherche dure quelques centaines de millisecondes. Le signal d'abandon
(ADR-017 §5), `abortOnClose` et les vérifications entre les étapes disparaissent : la
réponse à un client parti est perdue, sans autre effet.

### 7. Un contrat neuf, l'ancien gelé

Un sous-chemin `@murphy/contract/search` porte les schémas zod de la requête, de la
réponse de recherche, du document et la liste des codes d'erreur. `documentTypeSchema`
y vit.

`@murphy/contract/messages` et `@murphy/contract/errors` restent en l'état jusqu'à
ADR-030 : le backend ne les importe plus, mais le frontend compile toujours contre eux.

### 8. Le frontend est hors service jusqu'à ADR-030

Le frontend n'est pas modifié. Il compile et ses tests passent (`npm run check` reste
vert), mais il ne trouve plus de WebSocket une fois lancé. La prod n'est pas déployée :
personne n'en dépend. Les résultats se lisent par l'API, ce qui suffit pour juger le
remplacement du modèle d'embedding.

## Alternatives rejetées

- **`GET /search?q=…`** : l'usage REST et une URL partageable, mais la question entre
  dans les logs d'accès et ceux de chaque proxy. La masquer ferait de la confidentialité
  une affaire de configuration (ADR-010).
- **`from` et `size` fournis par le client** : l'API exposerait un détail d'OpenSearch,
  et une taille de plus serait à borner.
- **Garder ADR-028 §7 pour les documents sans passage correspondant** : une page de dix
  décisions pèserait plus d'un mégaoctet.
- **Plafonner les passages par document** : l'API fixerait une part de l'affichage, qui
  relève d'ADR-030.
- **Un booléen `hasNextPage`**, tiré de `size + 1` documents : écarté au profit d'un
  nombre de pages connu d'avance.
- **L'étape dans l'erreur**, comme ADR-017 : le statut et le code suffisent.
- **Garder le WebSocket pour les seules sources**, sans texte de réponse : du code de
  transition des deux côtés, jeté à ADR-030.
- **Brancher le frontend sur l'API dès maintenant** : empiéterait sur ADR-030.
- **Retirer l'ancien contrat tout de suite** : le frontend ne compilerait plus et
  sortirait de `npm run check` jusqu'à ADR-030.

## Conséquences

- **Backend** : `routes/chat.ts`, `routes/chatWebSocket.ts`, `services/chatService.ts`,
  `infra/llm.ts` et `validation/chatRequest.ts` disparaissent, avec
  `buildContextString` et `MAX_LLM_CONTEXT_CHARS`. Arrivent les routes `search` et
  `documents`, un service de recherche et la validation de leur requête.
  `streamRateLimiter` devient le limiteur de recherche ; la limite de taille ne vaut plus
  que pour les corps HTTP. `toChatError` part ; `RagStage` ne sert plus qu'aux logs. Les
  dépendances `ai` et `ws` quittent le backend.
- **Configuration** : partent `LLM_*` et `SYSTEM_PROMPT`, `STREAM_RATE_LIMIT_*` devient
  `SEARCH_RATE_LIMIT_*` (`docker-compose.base.yml`, `.env.dev`).
- **Contrat** : un troisième sous-chemin (`exports` et `typesVersions`) ; les images de
  dev sont à reconstruire (`npm run build` puis `npm run up`).
- **Santé** : inchangée, elle ne sondait pas le LLM.
- **Documentation** : `CLAUDE.md` et `docs/technical/backend/` décrivent le flux RAG ;
  ils décriront la recherche.
- **ADR-030** retirera `messages` et `errors`, et branchera le frontend sur cette API.

## Références

ADR-010 (stateless, confidentialité) · ADR-015 (contrat ingestion ↔ serving) · ADR-017
(erreurs du chat) · ADR-028 (OpenSearch, sans LLM) · ADR-030 (interface du frontend, à
écrire)
