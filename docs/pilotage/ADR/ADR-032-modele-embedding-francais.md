# ADR-032 — Un modèle d'embedding qui couvre le droit français

**Statut** : 🟡 Proposé (11 octobre 2026) — le choix du modèle reste à trancher · ferme
le point ouvert d'ADR-028 (Conséquences, limites connues)

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

**À trancher : le modèle.**

Les candidats qui ressortent de la comparaison :

1. **microsoft/harrier-oss-v1-0.6b**
   - premier en français général, à 0,8 point du premier sur le droit français ;
   - 32k tokens de contexte, licence MIT ;
   - une instruction sur la question ;
   - support par TEI à vérifier.
2. **Snowflake/snowflake-arctic-embed-l-v2.0**
   - premier sur le droit français, mais irrégulier ailleurs ;
   - encodeur XLM-R éprouvé dans TEI ;
   - préfixe `query: ` seul.

Écartés en l'état :
- les modèles de plus de 1 B paramètres, pour la VRAM ;
- jina-embeddings-v5-text-small, pour sa licence ;
- embeddinggemma-300m, pour ses CGU et son absence de mesure sur le droit français.

## Ce que le choix entraîne

Ces points sont à trancher avec le modèle :

- **La dimension** : 1024 pour les deux candidats, contre 768 aujourd'hui. Elle est
  écrite dans `index_definition.json` et `index-opensearch.md`, qui doivent rester
  identiques, et citée dans `modele-de-donnees.md`, `configuration.md` et des tests de
  `ragcore`. Seul gte-multilingual-base garderait 768.
- **Le pooling** : `--pooling mean` est fixé dans `docker-compose.base.yml`. harrier
  demande le dernier token, arctic le CLS. Il faut soit le faire suivre le modèle dans
  `.env.dev`, soit laisser TEI lire celui que déclare le modèle.
- **Le préfixe de la question** : le backend et l'ingestion n'embarquent plus le texte
  de la même façon, ce qui fait une règle de plus dans le contrat ingestion ↔ serving
  (ADR-015). Il faut décider qui l'écrit (le backend, ou TEI par `prompt_name`) et où
  vit la consigne.
- **Le découpage** : avec 8k ou 32k tokens de contexte, des passages plus longs que 384
  caractères deviennent possibles. À trancher ici ou à reporter.
- **La réingestion** : complète, après le changement de mapping. Le temps de démarrage
  de TEI et la durée de l'ingestion sont à mesurer avec le nouveau modèle.
- **La documentation** : `CLAUDE.md`, `docs/technical/ARCHITECTURE.md` (contrat « Modèle
  d'embedding »), `docs/technical/data/ARCHITECTURE.md` et
  `docs/technical/backend/ARCHITECTURE.md` citent `all-mpnet-base-v2`, 768 dimensions.

## Références

ADR-015 (contrat ingestion ↔ serving) · ADR-028 (OpenSearch, modèle anglais) · ADR-031
(API de recherche) · ADR-030 (interface du frontend, à écrire)

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
