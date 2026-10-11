# ADR-032 — Un modèle d'embedding qui couvre le droit français

**Statut** : ✅ Accepté (11 octobre 2026) — amende ADR-015 §2 · ferme le point ouvert
d'ADR-028 (Conséquences, limites connues)

## Contexte

ADR-028 pose que le modèle d'embedding est anglais : `all-mpnet-base-v2` est entraîné
surtout sur de l'anglais, et le corpus est du droit français. Son remplacement suit
l'étape 2 de la migration (ADR-031) et précède l'interface du frontend (ADR-030).

Cette ADR compare les candidats sur leurs spécifications et sur les benchmarks publiés.
Aucun jeu d'évaluation propre à Murphy n'est constitué : la comparaison s'appuie sur les
résultats publics.

### Les contraintes du système

- **Le GPU** : la machine de dev a une RTX 3050 Laptop, **4 Go de VRAM**. TEI charge le
  modèle en `float16`. Restent les modèles de 0,3 à 0,7 B de paramètres (environ 1,2 Go
  de poids pour 0,6 B). Qwen3-Embedding-4B/8B, harrier-oss-v1-27b ou
  BGE-multilingual-gemma2 (9 B) n'y tiennent pas.
- **TEI** : `text-embeddings-inference:cuda-1.8.1`. Le backend et l'ingestion appellent
  la route `/v1/embeddings`. Le pooling est fixé à `mean` dans `docker-compose.base.yml`.
- **L'index** : la dimension des vecteurs (768) est écrite deux fois dans
  `index_definition.json` (passages et titres). L'ingestion vérifie au démarrage que TEI
  rend cette dimension.
- **Le découpage** : `CHUNKING_MAX_CHARS` 384 et `CHUNKING_OVERLAP_CHARS` 25, réglés pour
  le modèle actuel.
- **La réingestion** : tout changement de modèle impose une réingestion complète
  (`index-opensearch.md`).

## Les benchmarks

### Méthode

Les moyennes multilingues (MMTEB) couvrent plus de 250 langues et disent peu du
français. Les scores ci-dessous sont extraits des résultats bruts de MTEB
(`embeddings-benchmark/results`, commit `b64a5db` du 9 octobre 2026). Chaque tâche de
recherche est réduite à son sous-ensemble en français. Quand un modèle a plusieurs
révisions évaluées, la meilleure est retenue. Métrique : nDCG@10, la métrique principale
de ces tâches.

- **Droit FR** (`FrenchLegal1Retrieval`, RTEB) : questions de droit administratif, sur
  des décisions de justice et des procédures. C'est le plus proche du corpus. Le jeu est
  **privé** : l'équipe MTEB exécute les modèles, et leurs auteurs ne peuvent pas s'y
  être entraînés.
- **FR général** (`French1Retrieval`, RTEB) : jeu privé, en français général.
- **MIRACL fr** (`MIRACLRetrievalHardNegatives`, sous-ensemble `fr`, split `dev`),
  **Belebele fr** (`fra_Latn-fra_Latn`), **Statcan fr** (`StatcanDialogueDatasetRetrieval`,
  `french`, split `test`) : tâches publiques.
- **MMTEB recherche** : la colonne Retrieval de MMTEB, telle que la publient les rapports
  de Qwen3 Embedding, jina-embeddings-v5 et Granite R2. Elle couvre toutes les langues.

### Résultats en recherche française (nDCG@10)

| Modèle | **Droit FR** | FR général | MIRACL fr | Belebele fr | Statcan fr | MMTEB recherche |
|---|---|---|---|---|---|---|
| all-mpnet-base-v2 *(actuel)* | 24,0 | 66,6 | 14,6 | 67,6 | 0,9 | — |
| microsoft/harrier-oss-v1-0.6b | 83,3 | **85,9** | 57,9 | 93,4 | 45,5 | n. c. |
| Snowflake/snowflake-arctic-embed-l-v2.0 | **84,1** | 76,7 | 57,4 | 94,6 | 13,3 | 58,4 |
| microsoft/harrier-oss-v1-270m | 75,0 | 83,5 | 50,9 | 91,6 | 31,8 | 66,4 |
| Qwen/Qwen3-Embedding-0.6B | 73,4 | 84,5 | 55,0 | 93,8 | 27,2 | 64,6 |
| BAAI/bge-m3 | 63,0 | 82,8 | **59,4** | 94,3 | 18,5 | 54,6 |
| Alibaba-NLP/gte-multilingual-base | 54,4 | 83,4 | 55,7 | — | 20,6 | 57,2 |
| intfloat/multilingual-e5-large-instruct | 51,1 | 80,7 | 40,7 | 94,6 | 26,6 | 57,1 |
| google/embeddinggemma-300m | — | — | 58,0 | **95,4** | 45,2 | 62,5 |
| jinaai/jina-embeddings-v5-text-small | — | — | 58,6 | **95,4** | 40,2 | 64,9 |
| ibm-granite/granite-embedding-311m-multilingual-r2 | — | — | 52,1 | 92,5 | **55,9** | 65,2 |

« — » : non évalué sur la tâche. « n. c. » : score non publié à notre connaissance
(la fiche de harrier-oss-v1-0.6b ne donne que sa moyenne MTEB v2, 69,0).

**Écartés des mesures** :
- BSARD (articles de loi belges, en français) : MTEB le note en rappel@100, sa première
  version rend des valeurs aberrantes, et quatre candidats seulement y sont évalués.
- Solon-embeddings-large-0.1 : modèle français de 2024, n'a pas de score sur les jeux
  privés, et il est en retrait sur les tâches publiques (MIRACL fr 43,4).

### Ce que montrent les chiffres

- `all-mpnet-base-v2` est loin derrière partout : 24,0 sur le droit français, contre plus
  de 80 pour les deux premiers.
- Sur le droit français, deux modèles se détachent : **arctic-embed-l-v2.0** (84,1) et
  **harrier-oss-v1-0.6b** (83,3).
  - harrier est aussi le premier en français général.
  - arctic chute sur Statcan (13,3).
- harrier-oss-v1-0.6b dépasse Qwen3-Embedding-0.6B sur toutes les tâches françaises, à
  architecture et taille égales.
- bge-m3, souvent cité comme choix par défaut, perd 20 points sur le droit français.
- embeddinggemma, jina-v5 et Granite R2 ne sont pas mesurés sur le droit français.

## Les spécifications

| Modèle | Param. | Dim. | Contexte (tokens) | Pooling | Préfixe | Licence |
|---|---|---|---|---|---|---|
| all-mpnet-base-v2 | 110 M | 768 | 384 | mean | aucun | Apache 2.0 |
| harrier-oss-v1-0.6b | 0,6 B | 1024 | 32 768 | dernier token | instruction sur la question | MIT |
| snowflake-arctic-embed-l-v2.0 | 568 M | 1024 | 8 192 | CLS | `query: ` sur la question | Apache 2.0 |
| harrier-oss-v1-270m | 268 M | 640 | 32 768 | dernier token | instruction sur la question | MIT |
| Qwen3-Embedding-0.6B | 0,6 B | 1024 | 32 768 | dernier token | instruction sur la question | Apache 2.0 |
| bge-m3 | 568 M | 1024 | 8 192 | CLS | aucun | MIT |
| gte-multilingual-base | 305 M | 768 | 8 192 | CLS | aucun | Apache 2.0 |
| multilingual-e5-large-instruct | 560 M | 1024 | 512 | mean | instruction sur la question | MIT |
| embeddinggemma-300m | 308 M | 768 | 2 048 | mean | sur la question et le document | Gemma (CGU) |
| jina-embeddings-v5-text-small | 677 M | 1024 | 32 768 | dernier token | adaptateur par tâche | CC BY-NC 4.0 |
| granite-embedding-311m-multilingual-r2 | 311 M | 768 | 32 768 | non documenté | aucun | Apache 2.0 |

- **Instruction sur la question** : la question est précédée d'une consigne d'une phrase
  (pour harrier et Qwen3 : `Instruct: {tâche}\nQuery: {question}`), les passages ne le
  sont pas. Sans elle, Qwen annonce une perte de 1 à 5 % en recherche.
- **harrier-oss-v1** reprend l'architecture de Qwen3, avec la recette d'entraînement de
  Microsoft. Sa fiche Hugging Face porte l'étiquette `text-embeddings-inference`. Son
  chargement par TEI 1.8.1 n'est pas vérifié.
- **embeddinggemma** ne supporte pas le `float16` : TEI passerait en `bfloat16`.
- **jina-embeddings-v5-text-small** est sous licence non commerciale.

## Décision

### 1. Le modèle : `microsoft/harrier-oss-v1-0.6b`

`microsoft/harrier-oss-v1-0.6b` remplace `all-mpnet-base-v2`, pour l'ingestion comme
pour le backend.

- **Le droit français** : 83,3, à 0,8 point du premier (arctic-embed-l-v2.0), contre 24,0
  pour le modèle actuel.
- **La régularité** : premier en français général (85,9), et sans chute sur les autres
  tâches françaises, quand arctic tombe à 13,3 sur Statcan.
- **Le contexte** : 32 768 tokens, contre 384 ; le découpage n'est plus contraint par la
  fenêtre du modèle.
- **La licence** : MIT.
- **Le GPU** : 0,6 B de paramètres, 1,19 Go de poids, dans les 4 Go de VRAM.

Ce que le modèle impose, d'après sa fiche :

- des vecteurs de **1024 dimensions**, normalisés (L2), comparés en cosinus ;
- un pooling sur le **dernier token** (`1_Pooling/config.json`) ;
- une **consigne d'une phrase devant chaque question**, au format
  `Instruct: {tâche}\nQuery: {question}`, et rien devant les passages. La fiche avertit
  que sans elle les performances se dégradent. Le modèle déclare trois consignes
  (`config_sentence_transformers.json`), dont `web_search_query` : « Given a web search
  query, retrieve relevant passages that answer the query ».

Son architecture est `Qwen3Model`, en `bfloat16`. TEI la charge depuis la 1.7.2 et la
sert sur CUDA par FlashQwen3 depuis la 1.8.0 ; la 1.8.1 de la stack en fait partie. Le
chargement reste à constater sur la machine.

### 2. La consigne de la question, écrite par le backend

- **Le backend place la consigne devant la question**, et l'envoie à `/v1/embeddings`
  comme aujourd'hui. C'est le calcul que ferait TEI : avec `prompt_name`, il colle la
  consigne devant le texte avant de le découper en tokens (`core/src/tokenization.rs`).
  Mais sa route `/v1/embeddings` n'accepte pas ce paramètre, et sa route `/embed` ne
  connaît que les trois consignes déclarées par le modèle.
- **Les passages et les titres n'ont pas de consigne** : l'ingestion ne change pas.
  Harrier est entraîné et évalué ainsi (`apply_instruction_to_passages=False` dans MTEB).
- **La consigne vit dans `.env.dev`** : `EMBEDDING_QUERY_INSTRUCTION` porte le préfixe
  complet, que le backend colle tel quel. Le gabarit `Instruct: …\nQuery:` est propre à la
  famille Qwen3 : dans la variable, il change avec le modèle sans toucher au code. Il n'y
  a pas de variable pour les documents, qui resterait vide avec harrier.
- **Sa valeur** : `Instruct: Retrieve text based on user query.\nQuery:`, sans espace
  final, comme le gabarit de MTEB. C'est la consigne par défaut de MTEB pour une tâche de
  recherche (`abstasks/retrieval.py`). MTEB l'applique à `FrenchLegal1Retrieval` et
  `French1Retrieval`, qui n'en ont pas de propre : les scores du §1 ont été obtenus avec
  elle. Cela se lit dans le code actuel de MTEB ; la version 2.13.1, qui a produit ces
  résultats, n'a pas été vérifiée.

Une consigne propre au droit français attendra une méthode d'évaluation qui puisse la
comparer à celle-ci.

### 3. TEI suit le modèle : ni pooling ni précision imposés

La commande de TEI devient `["--model-id", "${EMBEDDING_MODEL}"]`.

- **`--pooling` est retiré.** Le pooling réduit les vecteurs des tokens à un vecteur du
  texte ; chaque modèle est entraîné avec le sien. Sans l'option, TEI lit celui que
  déclare le modèle (`1_Pooling/config.json` : `last-token` pour harrier, `mean` pour
  `all-mpnet-base-v2`). Si ce fichier manque, TEI refuse de démarrer, sauf pour un modèle
  de type BERT, qu'il passe en CLS. Un pooling imposé à tort rendrait des vecteurs de la
  bonne dimension mais faux, sans aucune erreur.
- **`--dtype` est retiré.** Sur GPU NVIDIA, TEI ne propose que `float16` et `float32`, et
  prend `float16` par défaut (`backends/src/dtype.rs`), sauf pour les modèles
  `gemma3_text`. Il ne lit pas la précision déclarée par le modèle (`bfloat16` pour
  harrier). Retirer l'option ne change donc rien : elle répétait la valeur par défaut.
- **TEI reste en 1.8.1.** La 1.9 n'apporte rien à harrier.

La précision et le pooling effectifs se lisent sur la route `GET /info` de TEI
(`model_dtype`, `model_type`). Si des vecteurs contiennent des `null` ou des `NaN` en
`float16`, la stack passera `--dtype float32`.

### 4. La dimension vient de TEI

- **`index_definition.json` ne porte plus de dimension.** L'ingestion mesure déjà celle
  de TEI au démarrage de chaque run, embedding activé ou non. À la création de l'index,
  elle injecte cette dimension dans `title_embedding` et `passages.embedding`.
- **Le garde-fou compare à l'index réel.** Sur un index qui existe déjà, la dimension
  mesurée est comparée à celle de l'index, lue dans OpenSearch, et le run s'arrête si
  elles diffèrent. Il remplace `check_vector_dimension`, qui comparait au fichier :
  `ensure_index` ne modifie jamais un index existant, si bien qu'un index resté en 768
  passait la vérification d'un fichier passé à 1024, et OpenSearch rejetait ensuite
  chaque document, un par un.

Changer de modèle reste un acte délibéré : il passe par `EMBEDDING_MODEL` et une
réingestion complète.

### 5. Le découpage ne change pas

`CHUNKING_MAX_CHARS` reste à 384 et `CHUNKING_OVERLAP_CHARS` à 25 : on ne change qu'une
variable à la fois.

La justification de 384 ne tient plus. Elle était la plus grande taille qui tenait dans
la fenêtre de 384 tokens d'`all-mpnet-base-v2` (300 tokens au plus, mesurés). Avec les
32 768 tokens d'harrier, 384 devient une valeur héritée, sans fondement, et la
documentation le dit. La longueur des passages se reverra avec l'affichage (ADR-030) ou
une méthode d'évaluation.

### 6. Le contrat ingestion ↔ serving (amende ADR-015 §2)

Les vecteurs des passages, des titres et de la question viennent du même modèle,
`EMBEDDING_MODEL`, servi par le même TEI. La question porte la consigne
`EMBEDDING_QUERY_INSTRUCTION`, les passages et les titres n'en portent pas. Changer de
modèle impose une réingestion complète ; changer la consigne ne touche que le backend.

### 7. On vérifie que le système fonctionne, pas ses résultats

La migration se vérifie par le fonctionnement : TEI démarre et sert des vecteurs de 1024
dimensions sans `NaN`, l'ingestion indexe le corpus, l'API répond. La qualité des
résultats relève d'un chantier d'évaluation à part, qui viendra plus tard.

## Alternatives rejetées

- **Snowflake/snowflake-arctic-embed-l-v2.0** : premier sur le droit français (84,1),
  encodeur XLM-R éprouvé dans TEI, préfixe `query: ` seul. Mais il est irrégulier
  ailleurs (76,7 en français général, 13,3 sur Statcan), et son contexte est de 8k
  tokens.
- **Qwen/Qwen3-Embedding-0.6B** : même architecture et même taille qu'harrier, en
  dessous sur toutes les tâches françaises.
- **BAAI/bge-m3** : le plus simple à brancher (aucun préfixe), mais 20 points de moins
  sur le droit français.
- **Alibaba-NLP/gte-multilingual-base** : le seul à garder 768 dimensions, donc le
  mapping ; 54,4 sur le droit français.
- **Les modèles de plus de 1 B paramètres** (Qwen3-Embedding-4B/8B, harrier-oss-v1-27b,
  BGE-multilingual-gemma2) : ils ne tiennent pas dans 4 Go de VRAM.
- **jinaai/jina-embeddings-v5-text-small** : licence non commerciale.
- **google/embeddinggemma-300m** : CGU Gemma, pas de `float16`, et aucune mesure sur le
  droit français.
- **La route `/embed` avec `prompt_name`** : même calcul que le §2, mais limitée aux
  trois consignes du modèle, dont aucune n'est celle des scores retenus, et avec un
  autre format de requête et de réponse.
- **`--default-prompt` au démarrage de TEI** : la consigne irait aussi devant les
  passages. Il faudrait un second conteneur TEI pour l'ingestion, soit deux fois le
  modèle dans 4 Go de VRAM.
- **Une seconde variable pour la consigne des documents** : elle resterait vide avec
  harrier. Elle viendra si un modèle l'exige.
- **La phrase seule dans la variable, avec le gabarit dans le code** : le code serait lié
  à la famille Qwen3.
- **La consigne `web_search_query` du modèle** : documentée par la fiche, mais sans
  mesure sur nos tâches.
- **Le pooling dans une variable ou en dur** : une valeur de plus à garder synchronisée
  avec le modèle, et une erreur silencieuse si elle ne l'est pas.
- **`float32` ou TEI 1.9** : rien ne le justifie tant que `float16` rend des vecteurs
  sains.
- **La dimension écrite dans le mapping** : elle répète ce que TEI mesure à chaque run,
  et ne protège pas contre un index existant d'une autre dimension.
- **Des passages plus longs dès maintenant** : deux variables changeraient à la fois.

## Conséquences

La migration se fait en cinq lots, commités chacun à part. Entre les lots 1 et 4, la
recherche échoue (502 `SEARCH_FAILED`) : TEI rend des vecteurs de 1024 dimensions, et
l'index est encore en 768. Seul le dev est touché, la prod n'est pas déployée.

**Lot 1 — TEI sert harrier.**
- `docker-compose.base.yml` : la commande de TEI perd `--pooling` et `--dtype`.
- `.env.dev`, à la charge du développeur :
  `EMBEDDING_MODEL=microsoft/harrier-oss-v1-0.6b`.
- Vérification : TEI démarre ; `GET /info` donne le modèle, le pooling `last_token` et la
  précision `float16` ; un appel à `/v1/embeddings` rend 1024 nombres, sans `null` ni
  `NaN`, de norme 1. Le temps de démarrage et la mémoire sont mesurés.

**Lot 2 — L'ingestion prend la dimension de TEI.**
- `index_definition.json` sans dimension. `ensure_index` reçoit la dimension mesurée,
  l'injecte à la création, et la compare à celle d'un index existant.
  `check_vector_dimension` disparaît ; les tests suivent.
- `index-opensearch.md` reste identique au fichier, avec une phrase sur l'origine de la
  dimension ; `modele-de-donnees.md` et `configuration.md` ne citent plus 768.
- `configuration.md`, la documentation de l'ingestion et la docstring de `_embed_batch`
  présentent 384 comme une valeur héritée (§5).
- Vérification : le job `python` de la CI passe.

**Lot 3 — Le backend écrit la consigne.**
- `config.ts` lit `EMBEDDING_QUERY_INSTRUCTION`. C'est une variable critique, comme
  `MONGODB_URI` : son absence est journalisée en erreur, sans bloquer le démarrage.
- `EmbeddingClient` la place devant la question. `docker-compose.base.yml` la transmet
  au backend.
- `.env.dev`, à la charge du développeur :
  `EMBEDDING_QUERY_INSTRUCTION="Instruct: Retrieve text based on user query.\nQuery:"`.
- Vérification : Compose transmet le retour à la ligne (`npm run config`) ; les tests et
  `npm run check` passent.

**Lot 4 — Réingestion et vérification.**
- Un `kedro run` sur l'index resté en 768 doit s'arrêter avec le garde-fou du §4.
- Puis réingestion complète (`nuke_all`) : sa durée est mesurée, à comparer aux 173 s
  d'avant (`configuration.md`).
- Vérification par l'API, comme pour ADR-031 : recherche et pagination, document
  inconnu, découpe exacte des passages dans le `content`, aucun `CONTRACT_VIOLATION`, des
  vecteurs de 1024 dimensions dans les logs. Pas d'évaluation des résultats (§7).

**Lot 5 — Documentation.**
- `CLAUDE.md`, `docs/technical/ARCHITECTURE.md` (le contrat « Modèle d'embedding » et la
  consigne), `docs/technical/backend/` (la variable, la consigne), et
  `docs/technical/data/ARCHITECTURE.md` citent harrier, la dimension mesurée et la
  consigne.
- Le temps de démarrage et la mémoire de TEI sont mis à jour avec les mesures des lots 1
  et 4.

## Références

ADR-015 (contrat ingestion ↔ serving) · ADR-028 (OpenSearch, modèle anglais) · ADR-031
(API de recherche) · ADR-030 (interface du frontend, à écrire)

- [TEI v1.8.1](https://github.com/huggingface/text-embeddings-inference/tree/v1.8.1) —
  `core/src/tokenization.rs` (consigne), `router/src/lib.rs` (pooling, précision),
  `backends/src/dtype.rs`, `docs/openapi.json`
- [MTEB, `harrier_models.py`](https://github.com/embeddings-benchmark/mteb/blob/main/mteb/models/model_implementations/harrier_models.py)
  et [`abstasks/retrieval.py`](https://github.com/embeddings-benchmark/mteb/blob/main/mteb/abstasks/retrieval.py)
  — les consignes de l'évaluation
- [harrier : `mteb_v2_eval_prompts.json`](https://huggingface.co/microsoft/harrier-oss-v1-0.6b/blob/main/mteb_v2_eval_prompts.json)

- [embeddings-benchmark/results](https://github.com/embeddings-benchmark/results) —
  résultats bruts de MTEB
- [FrenchLegal1Retrieval](https://github.com/embeddings-benchmark/mteb/blob/main/mteb/tasks/retrieval/fra/french_legal1_retrieval.py)
  — définition de la tâche
- [microsoft/harrier-oss-v1-0.6b](https://huggingface.co/microsoft/harrier-oss-v1-0.6b)
- [QwenLM/Qwen3-Embedding](https://github.com/QwenLM/Qwen3-Embedding) — tableau MMTEB
- [jina-embeddings-v5-text (arXiv 2602.15547)](https://arxiv.org/html/2602.15547) —
  tableaux MMTEB et recherche
- [google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
- [Granite Embedding Multilingual R2](https://huggingface.co/blog/ibm-granite/granite-embedding-multilingual-r2)
- [MTEB-French (arXiv 2405.20468)](https://arxiv.org/html/2405.20468v1)
