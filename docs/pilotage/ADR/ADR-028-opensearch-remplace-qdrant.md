# ADR-028 — OpenSearch remplace Qdrant : un moteur de recherche hybride, sans LLM

**Statut** : ✅ Accepté (2 octobre 2026) — amende ADR-007, ADR-010, ADR-015 §2 à §5 et
ADR-018 §1-§2 · **§2 et §6 amendés par [ADR-029](ADR-029-recherche-hybride-quatre-listes.md)**
(une sous-requête de références, un vecteur de titre pour les documents sans passage)

## Contexte

La récupération est purement vectorielle : une recherche kNN cosinus dans Qdrant, qui
rend `RETRIEVAL_TOP_K` passages au-dessus de `RETRIEVAL_MIN_SCORE`. ADR-010 attribuait à
Qdrant une « recherche hybride » ; le code n'en fait aucune. Trois limites en découlent :

- **Les références exactes échappent à la recherche.** Les utilisateurs tapent
  « article L1234-5 », « n° 21-12.345 » ou un ECLI, mêlés à du langage naturel. Un
  embedding rend mal un numéro, et aucune recherche lexicale ne le rattrape.
- **Les métadonnées ne sont pas cherchables.** Elles vivent à plat dans le payload
  Qdrant, et le serving ne s'y appuie pas (ADR-015 §2).
- **Le modèle d'embedding est anglais.** `all-mpnet-base-v2` est entraîné surtout sur de
  l'anglais ; le corpus est du droit français.

ADR-007 pose par ailleurs que Murphy doit **sourcer, pas raisonner**, et que la
génération est un échafaudage transitoire. Le projet la retire : Murphy devient un
moteur de recherche.

Mesuré sur le corpus de dev le 2 octobre 2026 (1 121 documents, `content` en
caractères) :

| `document_type` | Documents | `content` moyen | `content` max |
|---|---|---|---|
| `decision` | 352 | 14 900 | 141 900 |
| `article` | 384 | 2 500 | 12 000 |
| `texte` | 98 | 1 400 | 6 400 |
| `section` | 287 | 0 | 0 |

- **Un article ne connaît pas son texte.** `LEGIARTI000045938851` a pour titre et pour
  `num` « 3 » ; son lien vers son texte (`contient`) n'existe que dans Neo4j. Un même
  numéro existe dans plusieurs codes, et en plusieurs versions (`L52-8` : deux
  documents).
- **Le document `texte` d'un code n'en porte que l'en-tête** (visas, préambule) ; ses
  articles sont des documents à part. Les sections n'ont pas de texte.
- Les métadonnées comptent **38 clés distinctes**.

## Décision

### 1. OpenSearch remplace Qdrant

OpenSearch 3.x porte les vecteurs, les métadonnées et la recherche. La version 3.0 est
un minimum : c'est la première qui rend les `inner_hits` d'une requête `hybrid`. Mongo
garde le texte (ADR-015 §1), Neo4j ne change pas. Le service `qdrant` quitte la stack ;
un service `opensearch` en nœud unique le remplace, avec ses plugins k-NN et
neural-search.

### 2. Un document OpenSearch par document Mongo, ses passages imbriqués

Le document a pour `_id` son `identifier`. Ses passages sont un champ `nested`. Le
mapping est `dynamic: strict`, sauf sous `metadata` (§3).

| Champ | Type | Rôle |
|---|---|---|
| `identifier` | `keyword` | Clé du document dans Mongo |
| `document_type`, `nature` | `keyword` | ADR-022 |
| `title` | `keyword` + `.texte` + `.ref` | Cherché ; le titre d'un article est son numéro |
| `parent_text_title` | `text` + `.ref` | Titre du texte qui contient un article ou une section (§4) |
| `metadata.*` | dynamic templates | Cherchées (§3) |
| `passages` | `nested` | Un objet par chunk |
| `passages.chunk_id` | `keyword` | Identité du passage |
| `passages.char_start`, `passages.char_end` | `integer` | Bornes dans `content`, en points de code (ADR-015 §1) |
| `passages.text` | `text` + `.ref` | Indexé, **non stocké** |
| `passages.embedding` | `knn_vector` (HNSW, cosinus) | Indexé, **non stocké** ; dimension demandée à TEI |

- **Le texte est indexé, pas stocké** (`_source.excludes`) : Mongo reste son seul
  stockage (ADR-015). En contrepartie, `_reindex` et les mises à jour partielles sont
  impossibles. Un changement de mapping ou d'analyseur passe par une réingestion
  complète, comme un changement de chunking.
- **Les sections sont indexées, sans passage.** Une recherche peut renvoyer un document
  sans texte : il sera le point d'entrée vers ce qu'il contient, ses textes ratifiants,
  ses citations. Sans vecteur, une section n'est trouvée que par la recherche lexicale,
  sur son titre et sur celui de son texte.
- Le plus long document de dev compte environ 400 passages, loin de la limite de 10 000
  objets imbriqués par document (`index.mapping.nested_objects.limit`).

### 3. Les métadonnées : un champ typé par clé

`metadata` reste un dictionnaire plat dans le modèle de l'ingestion. Le mapping le type
par dynamic templates :

- `metadata.date_*`, `derniere_modification` et `versions_a_venir` deviennent des
  `date` ;
- toute autre chaîne devient un `keyword` (égalité, filtres, agrégations), avec deux
  sous-champs : `.texte` (analyseur `fr_juridique`) et `.ref` (analyseur `references`).

`date_detection` est désactivé : le type d'une clé ne dépend jamais de la première
valeur vue. Une date mal formée fait échouer l'écriture du document, donc sa saga. Les
clés `list` (ADR-025) deviennent des tableaux, que tout champ accepte.

Chaque clé compte trois champs ; `index.mapping.total_fields.limit` (1 000 par défaut)
est relevé au besoin. Les clés viennent du vocabulaire fini de la DILA, y compris les
clés chemin-complet des balises non configurées (ADR-023) : le nombre de champs croît
avec les sources, pas avec les données.

### 4. Le titre du texte parent

Un article ou une section reçoit, dans son document OpenSearch seulement, le titre du
texte qui le contient : `parent_text_title`. L'ingestion le lit déjà dans le XML
(`CONTEXTE`, `TITRE_TXT`) pour la relation `contient`. Le XML peut donner plusieurs
titres au texte, un par période : le champ les reçoit tous. Dans « l'article L1234-5 du code
du travail », il départage les L1234-5 des différents codes. Mongo et le contrat du
flux ne changent pas.

### 5. Deux analyseurs

Un analyseur enchaîne des filtres de caractères, un tokenizer et des filtres de jetons.
Il s'applique deux fois : au texte indexé et à la question.

- **`fr_juridique`**, pour la langue naturelle : tokenizer `standard`, puis élision,
  minuscules, `asciifolding`, mots vides français et racinisation `light_french`.
- **`references`**, pour les références : un `pattern_replace` compacte les références
  (« L. 1234-5 » devient `L1234-5`), un tokenizer `pattern` en `group: 0` n'émet que
  les références, puis les minuscules. Un champ `.ref` ne contient que des références ;
  une question sans référence n'y produit aucun jeton.

Les motifs (articles L/R/D/A, pourvois, lois, ECLI) s'écrivent d'après le corpus, et se
vérifient par l'API `_analyze`.

La recherche lexicale est un `multi_match` sur les champs des deux analyseurs : chacun
analyse la question à sa façon. « le code du travail et l'article L1234-5 » donne
`code` et `travail` sur les champs `fr_juridique`, `l1234-5` sur les champs `.ref` : le
code et l'article remontent ensemble.

### 6. Une recherche hybride, fusionnée par RRF

Une requête `hybrid` porte deux sous-requêtes :

- **lexicale** : un `nested` sur `passages.text` et `passages.text.ref`, en
  `score_mode: max`, plus `title`, `parent_text_title` et `metadata.*` par leurs
  sous-champs `.texte` et `.ref` ;
- **vectorielle** : un `nested` kNN sur `passages.embedding`, avec
  `expand_nested_docs`.

La fusion est **RRF** (`score-ranker-processor`). Sans méthode d'évaluation, aucun poids
n'est à régler, et l'échelle des scores de chaque sous-requête n'importe pas. Le
pipeline de recherche relève du serving : le backend le crée au boot, par une écriture
idempotente. L'ingestion crée l'index, son mapping et ses analyseurs.

**`RETRIEVAL_MIN_SCORE` est supprimé** : un score RRF n'est pas une similarité, aucun
seuil n'y a de sens.

### 7. Les passages d'un document trouvé

- **Lexicaux** : tous ceux qui correspondent, par les `inner_hits` de la sous-requête
  lexicale. Le plafond est technique : 100 par document
  (`index.max_inner_result_window`).
- **Vectoriels** : les 3 plus proches, taille par défaut des `inner_hits`. Chaque passage
  a une similarité avec la question : un nombre est inévitable.
- Les deux listes sont dédoublonnées par `chunk_id` et fusionnées par RRF sur leurs
  rangs, dans le backend.
- **Un document trouvé sans passage** (par son titre, ses métadonnées ou son texte
  parent) **est renvoyé avec tous ses passages**, lus dans son `_source`. Une section
  n'en a aucun.

### 8. Une pagination sans état

La requête porte `from`, `size` et `pagination_depth`. Chaque sous-requête récupère au
plus `PAGINATION_DEPTH` documents, RRF les classe, puis `from`/`size` découpe la page.
Chaque page recalcule tout le pipeline : rien n'est gardé entre deux pages (ADR-010).

`PAGINATION_SIZE` (taille de page) et `PAGINATION_DEPTH` remplacent `RETRIEVAL_TOP_K`.
Le backend refuse de démarrer si l'une n'est pas un entier positif, si
`PAGINATION_DEPTH` est inférieure à `PAGINATION_SIZE`, ou si elle dépasse 10 000
(`index.max_result_window`). La profondeur doit rester la même d'une page à l'autre : la
changer change l'ensemble fusionné, donc le classement. Leurs valeurs restent à fixer.

### 9. Le LLM est retiré

Murphy devient un moteur de recherche : une question donne des documents classés et
leurs passages (ADR-007). `LLMProvider`, la section `llm` de la configuration,
`SYSTEM_PROMPT`, les variables `LLM_*`, les parts `text-delta` et l'étape `llm` de
`ChatError` (ADR-017) disparaissent.

Sans LLM, il n'y a plus rien à streamer. La recherche sera servie par une API HTTP
paginée et une page de résultats, qui affiche l'essentiel de chaque résultat et ouvre le
texte entier au clic, chargé à la demande. **Une ADR dédiée décrira cette API** : ses
routes, son contrat, et le retrait du WebSocket, du SSE et de l'AI SDK.

### 10. Deux étapes

1. **OpenSearch derrière le contrat actuel.** L'ingestion et le backend migrent ; le
   flux (`AppUIMessage`) et le frontend ne changent pas, et le LLM reste branché.
   `PAGINATION_SIZE` donne le nombre de documents de l'unique page servie (`from: 0`).
2. **Le LLM part et l'API de recherche arrive**, puis la page de résultats (ADR à
   écrire).

Pendant l'étape 1, une section produit un `data-parentDocument` sans `data-document`.
Le frontend n'affiche que les passages : il ne la montre pas. C'est accepté, elle
apparaîtra avec la page de résultats.

## Alternatives rejetées

- **Garder Qdrant et y ajouter des vecteurs creux (BM25).** Qdrant fusionne vecteurs
  denses et creux, mais n'analyse pas la langue. L'élision, la racinisation et le
  tokenizer des références seraient à écrire deux fois, en Python pour l'ingestion et en
  TypeScript pour la question, et à garder identiques.
- **Deux index, `documents` et `chunks`.** Le classement se ferait par passage, et
  regrouper par document demande `collapse`, dont les `inner_hits` en requête hybride
  sont fragiles (erreur « failed to expand hits » signalée jusqu'en 3.3.2). La
  compensation de la saga redeviendrait une suppression par filtre.
- **Les métadonnées en `flat_object`.** Ni analyse de texte, ni agrégation, ni type :
  c'est un champ pour stocker, pas pour chercher.
- **Le texte stocké dans OpenSearch.** Retire Mongo de la lecture des passages, mais
  stocke le texte deux fois (ADR-015).
- **Les métadonnées recopiées dans chaque passage**, pour qu'un document trouvé par
  elles ait des passages correspondants. Elles seraient dupliquées autant de fois que le
  document a de passages ; renvoyer tous ses passages suffit.
- **Une normalisation min-max et une somme pondérée.** Des poids à régler sans méthode
  d'évaluation.
- **`search_after` et un point in time.** Un contexte ouvert côté serveur entre deux
  pages, contre le serving sans état (ADR-010).
- **Un seuil de score.** Sans objet avec RRF.

## Conséquences

- **Réingestion complète** dans OpenSearch.
- **Côté `data/`** : `QdrantVectorRepository` laisse place à un dépôt OpenSearch, qui
  écrit un document entier, passages compris, par `_bulk`. L'étape Qdrant de la saga
  devient l'étape OpenSearch ; sa compensation est une suppression par `_id`.
  `ensure_collection` devient la création de l'index. L'écriture se fait sans
  rafraîchissement (`refresh_interval: -1`), suivie d'un rafraîchissement en fin de run.
  `nuke_all` supprime l'index. `parent_text_title` est à écrire.
- **Côté `backend/`** : `infra/qdrant.ts` laisse place à un client OpenSearch, qui
  vérifie au boot que l'index existe et crée le pipeline RRF. La sonde de santé
  interroge OpenSearch à la place de Qdrant, toujours sur trois services. Un passage
  incomplet reste une violation de contrat (ADR-015).
- **Configuration** : partent `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_TIMEOUT`,
  `RETRIEVAL_MIN_SCORE` et `RETRIEVAL_TOP_K` ; arrivent `OPENSEARCH_URL`,
  `OPENSEARCH_INDEX`, `OPENSEARCH_TIMEOUT`, `PAGINATION_SIZE` et `PAGINATION_DEPTH`. À
  l'étape 2, `LLM_*` et `SYSTEM_PROMPT` partent à leur tour.
- **Infrastructure** : OpenSearch tourne sur une JVM, avec un heap fixé
  (`OPENSEARCH_JAVA_OPTS`) et `vm.max_map_count=262144` sur l'hôte. Avec TEI (plus de
  4 Go), la machine de dev porte deux services gourmands. Le plugin de sécurité est
  désactivé en dev (`DISABLE_SECURITY_PLUGIN`) ; la prod devra le configurer.
- **Confidentialité (ADR-010)** : aucune trace des questions ne doit persister. Les slow
  logs sont désactivés par défaut ; Query Insights, qui peut conserver le corps des
  requêtes, est à vérifier et à désactiver.
- **Étape 1** : un document trouvé par ses métadonnées envoie tous ses passages au LLM,
  jusqu'à une décision entière (142 000 caractères). C'est transitoire.
- **Limites connues, reportées** :
  - le modèle d'embedding **doit** être remplacé par un modèle qui couvre le français ;
    ce changement impose une réingestion complète, et la dimension des vecteurs peut
    changer ;
  - une section, sans vecteur, échappe à la recherche vectorielle : un vecteur de son
    titre, cherché par une troisième sous-requête, la rattraperait ;
  - les versions d'un même article remontent toutes : un filtre par défaut sur
    `statut` passera par le paramètre `filter` de la requête hybride, qui s'applique à
    toutes ses sous-requêtes ;
  - les synonymes juridiques (« C. civ. » ↔ « code civil ») et le reranking sont les
    chantiers suivants.

## Références

ADR-007 (découplage récupération / génération) · ADR-010 (tri-base, stateless) ·
ADR-015 (contrat ingestion ↔ serving) · ADR-017 (erreurs du chat) · ADR-018 (nom fixe) ·
ADR-022 (typage) · ADR-023 et ADR-025 (métadonnées) · documentation OpenSearch :
*Hybrid query*, *Paginating hybrid query results*, *Using inner hits in hybrid
queries*, *Nested field search* (k-NN)
