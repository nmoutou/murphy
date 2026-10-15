# Projection : ingérer tous les dumps des sources gérées

Une projection faite le 15 octobre 2026. Elle part des mesures de
[`debit-ingestion.md`](debit-ingestion.md) : même machine, même modèle, même chunking
(384 caractères, recouvrement de 25), 4 workers. Elle couvre les six sources du
registre (`ragcore/sources/registry.py`) : LEGI et les cinq bases de jurisprudence, CASS,
CAPP, INCA, JADE et CONSTIT. Pour chacune, elle prend tous les dumps publiés sur
`https://echanges.dila.gouv.fr/OPENDATA/` au 14 octobre 2026.

**Le constat** : les six sources représentent environ **3,4 millions de documents,
35 millions de passages et 3,7 milliards de tokens**. Il faut compter **environ 7 jours**
de phase 1 sur le GPU de développement.

**Ce qui bloque** : la place sur le disque. Et les dumps ne peuvent pas être simplement
empilés : le connecteur rejetterait environ 370 000 documents.

**La machine qu'il faudrait** : 2 To de NVMe. Pour la RAM, 256 Go avec les vecteurs en
`float32` comme aujourd'hui, ou 64 Go avec des vecteurs compressés en mémoire.

## Les dumps disponibles

Chaque source a un dump global, `Freemium_<source>_global_20250713-140000`, puis des
incrémentaux quotidiens ou hebdomadaires :

| Source | Global (compressé) | Incrémentaux | Taille des incrémentaux (compressés) | Du … au … |
|---|---|---|---|---|
| LEGI | 1,1 Go | 462 | 1,9 Go | 12/07/2025 → 14/10/2026 |
| JADE | 1,2 Go | 347 | 234 Mo | 12/07/2025 → 14/10/2026 |
| INCA | 655 Mo | 59 | 9,3 Mo | 07/07/2025 → 09/10/2026 |
| CAPP | 279 Mo | 20 | 0,1 Mo | 26/08/2025 → 08/10/2026 |
| CASS | 248 Mo | 56 | 11,5 Mo | 07/07/2025 → 30/09/2026 |
| CONSTIT | 12 Mo | 22 | 2,1 Mo | 16/07/2025 → 05/10/2026 |

Les incrémentaux de LEGI pèsent plus lourd que son global : chaque texte modifié est
relivré en entier, avec ses `versions.xml`. Ils contiennent 3,3 millions de fichiers,
dont 1,9 million de `versions.xml`, pour seulement 434 567 clés.

## Méthode

1. **Les documents.** Chaque dump est listé en flux (`curl | tar tvz`), sans rien
   extraire. Le global de LEGI, déjà présent dans `/data`, est listé sur place. Une clé
   est un nom de fichier sans extension (ADR-034 §1). Elle n'est comptée qu'une fois,
   dans sa version la plus récente.
2. **Les passages de la jurisprudence.** On les tire de la taille des XML, avec un
   modèle linéaire. Il est ajusté sur les 352 décisions locales, passées dans les vraies
   briques (`GenericParser`, puis `StructuralChunker` à 384/25) : un passage pour
   395 octets, après environ 1,6 Ko d'en-tête par fichier. L'erreur quadratique moyenne
   est de 4 passages par document. Le modèle retrouve les 32 passages par document de
   `cass` et les 45 de `jade` du corpus local.
3. **Les passages de LEGI.** On reprend les chiffres de l'échantillon à 0,1 % : 3,64 par
   article, 3,89 par texte, 0 par section.
4. **Les tokens.** 108 par passage pour la jurisprudence (mesuré sur le run du corpus
   local) et 96 pour LEGI.
5. **La durée.** Le débit tenu par un GPU chaud est de 6 400 tokens/s. Pour LEGI, on
   prend les 54 ms par document mesurées sur le run à 1 %, qui comptent déjà la perte
   due aux petits lots.

## La projection

| Source | Documents (dont nouveaux depuis le global) | Passages par document | Passages | Tokens | Embedding, GPU chaud |
|---|---|---|---|---|---|
| LEGI | 2 241 929 (+125 616) | 3,3 | 7,3 M | 0,70 G | ≈ 34 h |
| JADE | 572 361 (+19 825) | ≈ 26 | 14,7 M | 1,59 G | ≈ 69 h |
| INCA | 387 902 (+5 422) | ≈ 19 | 7,3 M | 0,79 G | ≈ 34 h |
| CASS | 145 408 (+1 254) | ≈ 17 | 2,5 M | 0,27 G | ≈ 12 h |
| CAPP | 73 050 (+0) | ≈ 37 | 2,7 M | 0,29 G | ≈ 13 h |
| CONSTIT | 7 408 (+296) | ≈ 20 | 0,15 M | 0,02 G | ≈ 0,7 h |
| **Total** | **3 428 058** | | **34,7 M** | **3,66 G** | **≈ 165 à 170 h** |

Les documents de LEGI se répartissent en 1 836 719 articles, 250 953 sections et
154 257 textes.

- **Environ 7 jours de phase 1**, en ajoutant les 5 à 10 % de temps que les workers
  passent hors de l'embedding. Avec un GPU frais (9 740 tokens/s), la borne basse est
  d'environ 4,5 jours. Mais un run de cette durée garde le GPU chaud tout du long.
- **La jurisprudence représente 80 % du temps**, et JADE à lui seul 40 %. LEGI, le cas
  étudié jusqu'ici, n'en représente qu'un cinquième.
- **Les décisions des globaux sont plus courtes que celles du corpus local** : 8 à
  16 Ko de XML par décision, contre 15 à 19 Ko pour les incrémentaux récents. Les
  32 passages par document de `cass` et les 45 de `jade` surestimeraient donc les
  passages d'environ 70 %.
- **La découverte reste négligeable.** LEGI passe à environ 5,9 millions de fichiers,
  ce qui donne 20 à 25 min de parcours. La jurisprudence ajoute 1,2 million de
  fichiers. La relecture des 2,2 millions de `versions.xml` prend environ 11 min,
  pendant lesquelles les workers attendent.

## Ce qui bloque

### Le disque et la RAM

Ces estimations sont des règles de trois à partir du run à 1 % de LEGI :

| Poste | Projection | Disponible |
|---|---|---|
| OpenSearch (12 Ko par passage) | **≈ 415 Go** | 162 Go libres sur `/data` |
| Vecteurs bruts des passages seuls (1 024 × 4 octets) | ≈ 142 Go | 14 Go de RAM pour le k-NN |
| Mongo | ≈ 80 Go (estimation grossière) | |
| Neo4j | ≈ 8 Go | |
| Sources XML ajoutées dans `/data` | ≈ 30 à 40 Go | |

L'index ne tient pas sur ce disque, même avant les fusions de segments. Les 12 Ko par
passage ont été mesurés avant ces fusions, sur des passages LEGI : le chiffre réel peut
être plus bas, mais les vecteurs seuls pèsent déjà 142 Go.

### Les dumps ne s'empilent pas

`KeyedFileConnector` regroupe en facettes d'une même clé tous les fichiers de même nom
rangés sous le dossier d'une source. Quand un document est livré par plusieurs dumps, ses
facettes ont la même racine. Le parser rejette alors le document en entier
(`facet_root_duplicated`).

Si l'on décompresse tous les dumps côte à côte, voici combien de clés sont livrées par
plus d'un dump :

| Source | Documents rejetés |
|---|---|
| LEGI | 348 490 (16 %) |
| JADE | 19 031 |
| CASS | 1 412 |
| INCA | 329 |
| CONSTIT | 168 |
| CAPP | 19 |

Ces documents sont justement ceux qui ont été modifiés le plus récemment. Par ailleurs,
les listes de suppression (`liste_suppression_*.dat`) ne sont pas appliquées : un
document retiré par la DILA resterait dans la base.

La projection suppose donc que **les dumps sont fusionnés avant l'ingestion** :

1. appliquer les incrémentaux sur le global, dans l'ordre de leurs dates ;
2. garder la dernière version de chaque document ;
3. appliquer les suppressions.

Les incrémentaux datés d'avant le global (07/07/2025 et 12/07/2025) sont à écarter.
Aucune de ces étapes n'existe aujourd'hui.

## La machine qu'il faudrait

### Disque : 2 To de NVMe

| Poste | Projection |
|---|---|
| OpenSearch | ≈ 415 Go |
| Mongo | ≈ 80 Go |
| Sources XML | ≈ 30 à 40 Go |
| Neo4j | ≈ 8 Go |
| **Régime établi** | **≈ 550 Go** |

Une fusion de segments d'OpenSearch peut temporairement doubler la place d'un gros
segment. Il faut aussi de la place pour une ingestion de rechange ou une deuxième version
de l'index. 1 To passerait de justesse ; avec 2 To, on est à l'aise.

Le disque doit être un NVMe : en mode compressé (voir plus bas), chaque recherche relit
sur le disque des vecteurs complets.

### RAM : elle dépend de la façon dont OpenSearch garde les vecteurs

L'index utilise du HNSW `faiss` en `float32`, sans quantification
(`index_definition.json`). Pour qu'une recherche k-NN soit rapide, les graphes doivent
tenir en mémoire, en dehors du tas Java. Il y a environ 38 millions de vecteurs de
1 024 dimensions : 34,7 millions de passages et 3,4 millions de titres.

| Stockage des vecteurs | Graphes en RAM | RAM confortable pour la machine |
|---|---|---|
| `float32`, comme aujourd'hui | ≈ 160 à 180 Go | **256 Go** |
| `fp16` (quantification scalaire de faiss) | ≈ 80 à 90 Go | 128 Go |
| `on_disk`, compression ×32, avec rescoring | ≈ 5 à 10 Go | **64 Go** (32 Go au minimum) |

Avec 64 Go, il reste de la place pour le reste de la pile :

- le cache de Mongo (WiredTiger) ;
- Neo4j ;
- TEI, jusqu'à 4 Go pendant son chargement ;
- l'index des chemins de la découverte : environ 7 millions de chaînes, 1 à 2 Go ;
- la phase 2 ;
- le cache de pages, que le rescoring sur disque utilise beaucoup.

### À savoir avant de choisir

- **Ces besoins sont ceux de la recherche, pas de l'ingestion.** L'ingestion construit
  les graphes segment par segment, et 32 Go lui suffisent. Mais l'index produit ne
  servira pas de recherche correcte avec si peu de mémoire.
- **Changer la quantification modifie la qualité de la recherche.** Il faut la mesurer
  avant de décider : c'est le levier 4 de [`debit-ingestion.md`](debit-ingestion.md).
  Il faut ensuite tout ré-ingérer, et modifier ensemble le mapping et ses deux documents
  de référence.
- **Le tas d'OpenSearch est à `-Xmx1g`** (`docker-compose.base.yml`). Avec environ
  38 millions de documents Lucene, en comptant les passages imbriqués, il faudra
  probablement 4 à 8 Go, à prendre en plus des graphes.

## Ce qui reste incertain

- **Les passages de la jurisprudence** sont déduits de la taille des fichiers, sur un
  modèle ajusté avec des décisions récentes. L'en-tête des décisions anciennes peut
  être plus court : le nombre de passages serait alors un peu sous-estimé. Il faut
  compter environ ±15 %.
- **La taille d'OpenSearch** (12 Ko par passage) a été mesurée avant les fusions de
  segments. La mémoire des vecteurs, elle, se calcule exactement : ce sont les chiffres
  les plus sûrs de ce document.
- **La taille de Mongo** est extrapolée à partir de LEGI, dont les documents sont plus
  courts et ont des métadonnées différentes.
- **Le contenu des listes de suppression** n'a pas été lu : le nombre de documents
  supprimés n'est pas déduit des totaux.
- **La phase 2 à l'échelle** n'est toujours pas mesurée (voir
  [`debit-ingestion.md`](debit-ingestion.md)).
