# ADR-015 — Contrat ingestion ↔ serving : le texte d'un passage vit dans Mongo, désigné par ses offsets

**Statut** : ✅ Accepté (25 septembre 2026), amendé le 30 septembre 2026 · **§2 amendé par [ADR-022](ADR-022-typage-des-documents.md)** (typage des documents)
· **§1 à §5 amendés par [ADR-028](ADR-028-opensearch-remplace-qdrant.md)** (OpenSearch
remplace Qdrant)

> **Amendement du 30 septembre 2026.** `owner_id` et la version du contrat sont retirés :
> le projet est mono-utilisateur et en développement, aucun des deux n'avait d'usage. Un
> document se lit par son seul `identifier`, et le backend ne vérifie plus de version au
> boot. Le texte ci-dessous décrit le contrat après cet amendement.
>
> **Amendement par ADR-018 (30 septembre 2026).** Le pointeur de collection est retiré :
> la collection Qdrant porte un nom fixe, `QDRANT_COLLECTION`. Le contrat (§2) et le §3
> ci-dessous sont réécrits en conséquence.
>
> **Amendement par ADR-022 (1er octobre 2026).** `type_document` est remplacé par
> `document_type` (obligatoire) et `nature` (facultatif). Le §2 est réécrit en
> conséquence ; le tableau du contexte garde l'état constaté le 25 septembre.
>
> **Amendement par ADR-028 (2 octobre 2026).** OpenSearch remplace Qdrant. Le payload
> d'un point devient un passage imbriqué dans le document OpenSearch de son parent ; le
> texte reste dans Mongo seul, indexé mais non stocké dans OpenSearch. Les §1 à §5
> sont réécrits en conséquence ; le contexte et les alternatives gardent l'état du 25
> septembre. Le LLM est retiré à l'étape 2 de la migration : le §4 ne vaut que
> jusque-là, et l'ADR de l'API de recherche remplacera le §5. Sans LLM, l'argument qui
> écartait une route servant le texte à la demande (alternatives) tombe : cette ADR
> la rouvrira.

## Contexte

L'ingestion (`data/`) et le serving (`backend/`) partagent des bases, mais pas de code.
Leur contrat n'était écrit nulle part, et il a divergé. Le constat a été vérifié le 25
septembre 2026 sur la collection publiée `9424808d…` (3 303 points, 769 documents LEGI) :

| | L'ingestion écrit | Le backend lit |
|---|---|---|
| Payload Qdrant | `chunk_id`, `identifier` + métadonnées à plat (`type_document`, `num`…) | `chunkId`, `title`, `type` |
| Mongo `MURPHY_DATA` | `documents` : un document **entier** par `identifier` | `chunks`, par `chunkId` — la collection n'existe pas |
| Texte d'un passage | jamais persisté : `text`, `char_start`, `char_end` ne vivent qu'en mémoire | attendu dans `content` |

Conséquence : le backend écarte tous les résultats Qdrant. Aucune source n'atteint le
client, et le LLM répond sans contexte. L'interface affiche une réponse qui ne s'appuie
jamais sur le corpus, **sans rien signaler**.

Deux faits rendent les offsets exploitables :

- le chunker les calcule sur le `content` du document, et le refuse plutôt que de poser
  un offset faux (`sources/generic/chunking.py`) ;
- la normalisation typographique s'applique au parsing (`sources/generic/parser.py`),
  donc le `content` persisté dans Mongo est **le texte même** que les offsets désignent.

## Décision

### 1. Le texte d'un passage vit dans Mongo, désigné par ses offsets

Chaque passage du document OpenSearch porte `char_start` et `char_end`. Le texte d'un
passage est `documents.content[char_start:char_end]`, lu dans le document parent par
son `identifier`, clé déjà indexée.

Les offsets sont comptés en **points de code Unicode** (le `str` de Python). Le backend
doit découper dans la même unité : `String.prototype.slice` compte en unités UTF-16 et
se décalerait sur tout caractère hors du plan multilingue de base. `$substrCP` côté Mongo,
ou un découpage par points de code côté Node, satisfait le contrat.

### 2. Le contrat

**Document OpenSearch** : ce que le serving lit, et rien de plus. Le mapping complet,
champs de recherche compris, est celui d'ADR-028 §2.

| Champ | Type | Rôle |
|---|---|---|
| `identifier` | keyword (`_id`) | Clé du document dans Mongo |
| `document_type` | keyword : `article`, `section`, `texte` ou `decision` | Forme du document, affichée comme type de la source |
| `nature` | keyword ou absent | Nature juridique (`LOI`, `ARRET`, `QPC`…), affichée après le type |
| `passages[].chunk_id` | keyword | Identité du passage, envoyée au client |
| `passages[].char_start`, `passages[].char_end` | integer | Bornes du passage dans `content`, en points de code |

Un document peut n'avoir aucun passage : une section, qui n'a pas de texte, est
indexée pour être trouvée par son titre. Les métadonnées sont des champs cherchés
(ADR-028 §3), mais le serving ne les lit pas.

**Mongo `documents`** : `identifier`, `title`, `content`, déjà écrits aujourd'hui.

**Index OpenSearch** : un seul, nommé par `OPENSEARCH_INDEX`, la variable que les deux
côtés lisent dans `.env.dev` (ADR-018).

### 3. Le backend ne sert qu'un index qui existe

Le backend **refuse de démarrer** si l'index `OPENSEARCH_INDEX` n'existe pas dans
OpenSearch.

**Un changement de contrat impose une réingestion complète.** Rien ne le vérifie au
boot : un index dans un ancien format se révèle à la première requête, par une
violation de contrat (§5).

### 4. Le serving : ce que chaque étape lit

- **Contexte LLM**, jusqu'au retrait du LLM (ADR-028 §10) : le texte **des passages
  retenus** (ADR-028 §7). Un document trouvé sans passage correspondant donne tous
  ses passages.
- **Ordre** : les documents sont lus dans Mongo **avant** d'envoyer les sources, parce
  que le titre et le texte vivent dans le document. Les sources précèdent toujours le
  LLM ; elles attendent en plus une lecture indexée de quelques documents.

### 5. Les sources envoyées au client : passages et documents parents, séparés

Le client doit pouvoir afficher le texte entier d'un document et y surligner le passage
retrouvé. Le flux porte donc **deux types de parts**, chacun envoyé une fois :

| Part | Type (`types/messages.ts`) | Envoyée | Contenu |
|---|---|---|---|
| `data-parentDocument` | `ParentDocument` | une fois par document distinct | `identifier`, `title`, `type?`, `content` (texte entier) |
| `data-document` | `DocumentChunk` | une fois par passage retenu (ADR-028 §7) | `chunkId`, `identifier`, `highlightStart`, `highlightEnd`, `score`, `title?`, `type?` |

- **Un passage renvoie à son document par `identifier`.** Deux passages d'un même article
  donnent deux `data-document` et **un seul** `data-parentDocument` : le texte n'est
  jamais envoyé deux fois dans une réponse.
- **Le document précède ses passages.** En parcourant les résultats dans l'ordre du
  classement, le backend envoie le `data-parentDocument` d'un document avant son premier
  passage. Le client n'a jamais à attendre un document qu'un passage désigne déjà.
  Un document sans passage (une section) n'a que son `data-parentDocument`.
- **`score` est le score RRF du document** : ses passages, ordonnés entre eux par la
  fusion d'ADR-028 §7, le partagent.
- **`highlightStart`/`highlightEnd` sont en unités UTF-16**, celles des chaînes
  JavaScript : `content.slice(highlightStart, highlightEnd)` rend le passage. Le backend
  convertit une fois les offsets du payload, comptés en points de code (§1) ; le client
  n'a pas à connaître cette différence.
- **`title` et `type` restent sur `DocumentChunk`** tant que le frontend les y lit : le
  nom `data-document` et ces deux champs gardent le client actuel intact. Ils quittent
  `DocumentChunk` quand le frontend lit `ParentDocument`, et cette migration fait partie
  du chantier d'affichage, pas d'un après indéfini.
- **Violation du contrat** : un passage sans document parent, ou dont les offsets sortent
  de `content`, lève une `RagError` (étape `retrieval`) qui cite le `chunk_id`. Pas
  d'écart silencieux (ADR-010) : un passage faux dans le contexte du LLM est pire qu'une
  erreur affichée.

## Alternatives rejetées

- **Texte dans le payload Qdrant.** Retire Mongo du chemin de requête, mais stocke le
  texte deux fois, contre la répartition tri-base (ADR-010 : Qdrant porte les vecteurs et
  les métadonnées, Mongo le texte) et contre l'épuration d'ADR-011 §4, qui a justement
  retiré `sections` de Mongo parce qu'il doublait `content`.
- **Collection Mongo `chunks`.** Même duplication, plus une quatrième écriture dans la
  saga, donc une compensation de plus.
- **Texte entier dans chaque source** (`content` ajouté à `DocumentChunk`). Plus simple,
  mais envoie le même texte autant de fois que le document a de passages retrouvés, et
  mêle deux objets distincts, le passage et le document, dans un même type. Le jour où
  des arrêts longs remontent en plusieurs passages, il faudrait défaire ce mélange sur un
  contrat déjà consommé.
- **Texte entier servi par une route à la demande** (`GET /documents/:id`). Ajoute un
  aller-retour par source affichée et rouvre une route supprimée ; le flux porte
  déjà tout ce que la réponse a utilisé.
- **Contrôle par point à la requête** (écarter les points incomplets et journaliser).
  Rattrape une collection mêlée, mais l'utilisateur reçoit une réponse appauvrie sans le
  savoir : c'est le défaut même que cet ADR corrige.

## Conséquences

- **Réingestion complète**, une fois. Le fingerprint ne change pas : la collection
  `9424808d…` est réécrite en place, puisqu'un run retraite tous les documents (pas de
  SKIP).
- **Côté `data/`** : `QdrantVectorRepository.upsert` écrit `char_start` et `char_end` ;
  `docs/technical/data/reference/modele-de-donnees.md` décrit le contrat.
- **Côté `backend/`** : `collectionPointer.ts` perd son repli ;
  `mongodb.ts` lit `documents` par `identifier` et découpe les passages ;
  `chatService.ts` suit les §4 et §5. `MONGODB_COLLECTION` et
  `QDRANT_COLLECTION` disparaissent de la configuration. Le type `Document` est renommé
  d'après ce qu'il est désormais, un document parent. `types/messages.ts` gagne
  `ParentDocument` et les champs de §5 ; la ligne « le contenu n'est jamais envoyé au
  client » de `CLAUDE.md` et d'`ARCHITECTURE.md` devient fausse et doit être réécrite.
- **Côté `frontend/`** : **aucun changement d'affichage imposé**. Le client actuel lit
  `data-document` et ses champs `chunkId`, `title`, `type`, `score`, tous conservés ; il
  ignore la part `data-parentDocument` et les champs ajoutés. Sa copie de
  `types/messages.ts` doit néanmoins être alignée, pour que l'affichage du texte
  surligné n'ait plus qu'à lire ce qui arrive déjà. Le titre d'un article LEGI est son
  numéro (`L2122-22`) : un titre plus parlant est une évolution à part.
- **Poids des réponses** : chaque réponse transporte le texte entier des documents
  retrouvés, au plus `RETRIEVAL_TOP_K` documents distincts (1,4 k caractères en moyenne,
  12 k au plus sur LEGI aujourd'hui). La jurisprudence, plus longue, sera à mesurer.
- **Résiduel assumé** : pendant un run **incrémental**, entre l'écriture Mongo et celle de
  Qdrant (saga, steps 1 et 2), les anciens offsets d'un document désignent son nouveau
  `content`. Si ce passage reste dans les bornes, rien ne le détecte. La fenêtre est celle
  d'un document, hors du chemin `nuke_all` ; elle rejoint les résiduels déjà assumés de
  la saga (`docs/technical/data/reference/idempotence.md`). Une empreinte du
  `content` dans le payload la fermerait, si elle devient un problème.

## Références

ADR-003 (unité document) · ADR-007 (découplage récupération/génération) · ADR-010
(tri-base, fail-fast) · ADR-011 §4 (épuration Mongo)
