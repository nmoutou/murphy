# ADR-039 — Contrat ingestion ↔ serving : le texte d'un passage vit dans Mongo, désigné par ses offsets

**Statut** : ✅ Accepté (25 septembre 2026)

## Contexte

L'ingestion (`data/`) et le serving (`backend/`) partagent des bases, mais pas de code.
Leur contrat n'était écrit nulle part, et il a divergé. Le constat a été vérifié le 25
septembre 2026 sur la collection publiée `9424808d…` (3 303 points, 769 documents LEGI) :

| | L'ingestion écrit | Le backend lit |
|---|---|---|
| Payload Qdrant | `chunk_id`, `identifier`, `owner_id` + métadonnées à plat (`type_document`, `num`…) | `chunkId`, `title`, `type` |
| Mongo `LEGIFRANCE` | `documents` : un document **entier** par `(identifier, owner_id)` | `chunks`, par `chunkId` — la collection n'existe pas |
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

Le payload Qdrant porte `char_start` et `char_end`. Le texte d'un passage est
`documents.content[char_start:char_end]`, lu dans le document parent par
`(identifier, owner_id)`, clé déjà indexée.

Les offsets sont comptés en **points de code Unicode** (le `str` de Python). Le backend
doit découper dans la même unité : `String.prototype.slice` compte en unités UTF-16 et
se décalerait sur tout caractère hors du plan multilingue de base. `$substrCP` côté Mongo,
ou un découpage par points de code côté Node, satisfait le contrat.

### 2. Le contrat, version 1

**Payload Qdrant** : ce que le serving lit, et rien de plus.

| Champ | Type | Rôle |
|---|---|---|
| `chunk_id` | string | Identité du passage, envoyée au client |
| `identifier` | string | Clé du document parent dans Mongo |
| `owner_id` | string | Complète la clé du document parent |
| `char_start`, `char_end` | int | Bornes du passage dans `content`, en points de code |
| `type_document` | string, facultatif | Nature du document (LEGI et JURI), affichée comme type de la source |

Les autres métadonnées restent à plat dans le payload, mais le serving ne s'y appuie pas.

**Mongo `documents`** : `identifier`, `owner_id`, `title`, `content`, déjà écrits
aujourd'hui.

**Pointeur `MURPHY_META.meta_published_collection`** : il gagne un champ
`serving_contract_version` (entier, `1`).

### 3. Le backend vérifie la version au boot

L'ingestion publie la version du contrat qu'elle a écrite. Le backend attend une version
précise et **refuse de démarrer** si le pointeur en porte une autre ou n'en porte pas,
comme il refuse déjà une collection absente (`infra/collectionPointer.ts`).

Deux conséquences :

- **le repli `QDRANT_COLLECTION` est retiré.** Une collection que personne n'a publiée
  n'a pas de version connue : la servir, c'est parier sur son format ;
- **un changement de contrat est un bump de version, qui impose un run complet.** Un run
  restreint (`--params source=…`) ne réécrit que ses sources : s'il publiait la nouvelle
  version, la collection mêlerait deux formats. Il ne publie donc que si le pointeur en
  place porte déjà la même version.

### 4. Le serving : ce que chaque étape lit

- **Contexte LLM** : le texte **du passage seul**. Donner le document parent, ou une
  fenêtre élargie, est une stratégie de génération à évaluer (ADR-016), pas une
  réparation de contrat.
- **Ordre** : les documents sont lus dans Mongo **avant** d'envoyer les sources, parce
  que le titre et le texte vivent dans le document. Les sources précèdent toujours le
  LLM ; elles attendent en plus une lecture indexée de quelques documents.

### 5. Les sources envoyées au client : passages et documents parents, séparés

Le client doit pouvoir afficher le texte entier d'un document et y surligner le passage
retrouvé. Le flux porte donc **deux types de parts**, chacun envoyé une fois :

| Part | Type (`types/messages.ts`) | Envoyée | Contenu |
|---|---|---|---|
| `data-parentDocument` | `ParentDocument` | une fois par document distinct | `identifier`, `title`, `type?`, `content` (texte entier) |
| `data-document` | `DocumentChunk` | une fois par résultat Qdrant | `chunkId`, `identifier`, `highlightStart`, `highlightEnd`, `score`, `title?`, `type?` |

- **Un passage renvoie à son document par `identifier`.** Deux passages d'un même article
  donnent deux `data-document` et **un seul** `data-parentDocument` : le texte n'est
  jamais envoyé deux fois dans une réponse.
- **Le document précède ses passages.** En parcourant les résultats dans l'ordre du
  classement, le backend envoie le `data-parentDocument` d'un document avant son premier
  passage. Le client n'a jamais à attendre un document qu'un passage désigne déjà.
- **`highlightStart`/`highlightEnd` sont en unités UTF-16**, celles des chaînes
  JavaScript : `content.slice(highlightStart, highlightEnd)` rend le passage. Le backend
  convertit une fois les offsets du payload, comptés en points de code (§1) ; le client
  n'a pas à connaître cette différence.
- **`title` et `type` restent sur `DocumentChunk`** tant que le frontend les y lit : le
  nom `data-document` et ces deux champs gardent le client actuel intact. Ils quittent
  `DocumentChunk` quand le frontend lit `ParentDocument`, et cette migration fait partie
  du chantier d'affichage, pas d'un après indéfini.
- **Violation du contrat** : un point sans document parent, ou dont les offsets sortent
  de `content`, lève une `RagError` (étape `retrieval`) qui cite le `chunk_id`. Pas
  d'écart silencieux (ADR-020) : un passage faux dans le contexte du LLM est pire qu'une
  erreur affichée.

## Alternatives rejetées

- **Texte dans le payload Qdrant.** Retire Mongo du chemin de requête, mais stocke le
  texte deux fois, contre la répartition tri-base (ADR-020 : Qdrant porte les vecteurs et
  les métadonnées, Mongo le texte) et contre l'épuration d'ADR-022 §4, qui a justement
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
- **Version du contrat dans le fingerprint.** Un bump créerait une nouvelle collection,
  et un run restreint publierait une collection ne contenant que ses sources. Le
  fingerprint nomme une configuration de **recherche** (normalisation, découpage,
  embedding) ; la forme du payload n'en fait pas partie.

## Conséquences

- **Réingestion complète**, une fois. Le fingerprint ne change pas : la collection
  `9424808d…` est réécrite en place, puisqu'un run retraite tous les documents (pas de
  SKIP).
- **Côté `data/`** : `QdrantVectorRepository.upsert` écrit `char_start` et `char_end` ; une
  constante `SERVING_CONTRACT_VERSION` est publiée avec le pointeur ; la publication
  applique la règle du run restreint (§3) ; `docs/technical/data/reference/modele-de-donnees.md` décrit
  le contrat.
- **Côté `backend/`** : `collectionPointer.ts` vérifie la version et perd son repli ;
  `mongodb.ts` lit `documents` par `(identifier, owner_id)` et découpe les passages ;
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
  la saga (`docs/technical/data/reference/idempotence-et-publication.md`). Une empreinte du
  `content` dans le payload la fermerait, si elle devient un problème.

## Références

ADR-004 (unité document) · ADR-016 (découplage récupération/génération) · ADR-020
(tri-base, fail-fast) · ADR-022 §4 (épuration Mongo)
