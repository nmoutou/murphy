# Débit de l'ingestion : où passe le temps

Mesures du 14 octobre 2026, sur la machine de développement : RTX 3050 Laptop (4 Go de
VRAM), 12 cœurs, 14 Go de RAM. TEI 1.8.1 sert `microsoft/harrier-oss-v1-0.6b` en
`float16`. Le chunking est réglé à 384 caractères, avec un recouvrement de 25. Il y a
4 workers en phase 1.

**Le constat** : le débit plafonne à environ 25 documents/s, et tombe parfois à 5.

**Le verdict** : un seul goulot, le GPU qui calcule les embeddings. Il est saturé en
permanence et bridé par sa température. Le reste du pipeline l'attend.

## Méthode

1. **`MURPHY_META.statistics`** : les durées par étape et par document, et les attentes
   de la file, que le pipeline enregistre déjà à chaque run (ADR-034 §8).
2. **Un banc d'essai sur TEI seul**, sans écrire en base : 7 385 vrais passages du corpus
   (377 caractères en moyenne), envoyés avec plusieurs tailles de lots et plusieurs
   niveaux de concurrence. Le GPU est relevé toutes les 200 ms.
3. **Un run complet** sur le corpus local (1 121 documents, 18 023 passages, `nuke_all`
   actif), pendant lequel on relève chaque seconde le GPU (utilisation, horloge,
   puissance, température, causes de bridage), le CPU de chaque conteneur et celui du
   process Kedro. Les compteurs Prometheus de TEI (`/metrics`) sont relevés avant et
   après le run.
4. **Un échantillon de 0,1 % du dump LEGI complet** (2 117 documents tirés par
   `ingestion_ratio`), passé dans les vraies briques (connecteur, `GenericParser`,
   `StructuralChunker`), puis dans TEI. Rien n'est écrit en base.

## Le run complet (phase 1 : 308 s)

| Indicateur | Valeur | Ce qu'il signifie |
|---|---|---|
| Temps des workers passé à l'embedding | 1 148 s sur 1 193 s (**96 %**) | Mongo 6,2 s, OpenSearch 31,2 s, Neo4j 4,7 s, lecture 1,9 s, parse 1,4 s |
| Temps où les workers attendent un document | **0 s** | Ils sont toujours occupés |
| Temps où la lecture attend une place dans la file | **288 s sur 308 s** | La lecture attend les workers, qui attendent TEI |
| Utilisation du GPU | **100 %** sur 90 % du run, 99,8 % en moyenne | Le GPU est saturé |
| Bridage thermique logiciel (`sw_thermal_slowdown`) | actif sur **292 échantillons sur 299** | Le GPU est à 88 °C en moyenne |
| Horloge SM, par tiers du run | 1 301 → 1 066 → 1 013 MHz (2 100 au maximum) | Le GPU ralentit en chauffant |
| CPU du process Kedro | environ 5 % d'un cœur | Python est presque inactif : le GIL n'est pas en cause |
| CPU des conteneurs (moyenne, en % d'un cœur) | TEI 96, OpenSearch 10, Mongo 2, Neo4j 2 | Les bases ont peu de travail |

Ce que montrent les compteurs de TEI pendant le run :

| Mesure | Valeur |
|---|---|
| Requêtes | 1 396 |
| Textes | 18 334 |
| Tokens | 1 982 640, soit 108 par texte |
| Lots formés pour le GPU | 1 325, de 13,8 textes et 1 496 tokens en moyenne |
| Temps d'une requête en file d'attente | 800 ms en moyenne |
| Temps de calcul d'une requête | 652 ms en moyenne |
| Temps de tokenisation d'une requête | 0,6 ms en moyenne |

Le débit tenu est d'environ **6 400 tokens/s**, soit environ **60 passages/s**.

Le run de 18 h 57 sur le même corpus avait mis 254 s en phase 1 au lieu de 308. Le
GPU était plus frais.

## Le banc d'essai TEI

| Taille des lots × requêtes en parallèle | Passages/s | Latence p50 | Horloge SM | Puissance |
|---|---|---|---|---|
| 32 × 1 | 73,7 | 445 ms | 1 416 MHz | 41,2 W |
| 32 × 4 | 67,4 | 1 898 ms | 1 226 MHz | 32,3 W |
| 32 × 16 | 62,4 | 7 169 ms | 1 117 MHz | 30,0 W |
| 4 × 4 | 55,8 | 288 ms | 1 112 MHz | 28,7 W |
| 4 × 32 | 56,8 | 2 248 ms | 1 043 MHz | 28,0 W |

- Le GPU est à 99-100 % **dès une seule requête à la fois**. Ajouter des requêtes en
  parallèle n'allonge que la latence.
- Le débit est proportionnel à l'horloge, quelle que soit la configuration : environ
  0,052 passage/s par MHz. Les scénarios ont tourné l'un après l'autre et le GPU
  chauffait de plus en plus : c'est ce qui fait baisser le débit, pas la configuration.
- Un lot de 32 passages prend 445 ms sur un GPU libre, et ce temps est entièrement du
  calcul. Le commentaire de `tei_embedder.py` qui parle de « ~800 ms de frais fixes »
  par requête prend pour un coût fixe le temps d'attente en file.

## Pourquoi tantôt 25 doc/s, tantôt 5

Le nombre de documents par seconde n'est pas la bonne unité. Ce qui reste constant,
c'est le nombre de tokens traités par seconde. Le débit en documents dépend donc surtout
du nombre de passages par document :

| Source | Passages par document | Embedding d'un document | Débit avec 4 workers |
|---|---|---|---|
| `legi` | 4,3 | 170 ms | ≈ 24 doc/s |
| `cass` | 32 | 1 490 ms | ≈ 2,7 doc/s |
| `jade` | 45 | 2 580 ms | ≈ 1,5 doc/s |

Les mélanges de sources donnent les valeurs intermédiaires, autour de 5 doc/s.

## Le dump LEGI complet

`Freemium_legi_global_20250713` contient **2 116 313 documents** (2 559 609 fichiers
XML) :

| Type | Documents | Passages par document (échantillon) |
|---|---|---|
| Articles (`LEGIARTI`) | 1 737 280 | 3,64 |
| Sections (`LEGISCTA`) | 234 979 | 0 : nœuds de structure, sans contenu |
| Textes (`LEGITEXT`) | 144 054 | 3,89 |

Mesures sur l'échantillon de 0,1 % :

| Étape | Mesure | Projection sur tout LEGI |
|---|---|---|
| Découverte (`rglob` sur toute l'arborescence) | **384 s** | 6,4 min, avant que la phase 1 commence |
| Lecture d'un document | 1,05 ms en moyenne, 3,5 ms au 99e centile | — |
| Parse + chunking d'un document | 0,53 ms en moyenne | lecture + parse + chunking : **≈ 1 h**, en parallèle de l'embedding |
| Passages | 3,24 par document, 96 tokens par passage | **≈ 6,9 millions de passages, ≈ 660 millions de tokens** |
| Embedding | 9 740 tokens/s, sur un GPU reposé par la découverte | **≈ 19 h** |
| Embedding, au débit tenu sur un GPU chaud | 6 400 tokens/s | **≈ 29 h** |
| Rejets au parse | 11 sur 2 117 (`ValidationError`) | ≈ 11 000 documents |

Un run qui calcule pendant une journée garde le GPU chaud tout du long : il faut compter
**environ 30 h pour ingérer LEGI**. La lecture et le parse ne sont pas en cause : ils
fournissent environ 600 documents/s, alors que les workers en traitent environ 20.

## Le run à 1 % de LEGI (`ingestion_ratio: 0.01`)

Run du 14 octobre à 22 h 54, avec `nuke_all` et l'embedding actifs. Il retient
21 171 documents : 21 164 de LEGI, plus 7 des autres sources. Le relevé est le même
que pour le run complet, avec en plus, toutes les 15 s, les compteurs d'indexation
d'OpenSearch. Le run dure 1 824 s et se termine sans erreur.

| Étape | Durée | Remarque |
|---|---|---|
| Découverte | **530 s** (8,8 min) | Kedro à 54 % d'un cœur, iowait 3,4 % : le parcours de l'arborescence coûte du CPU Python, pas du disque |
| Phase 1 | **1 230 s** | 21 028 documents écrits, soit 17,1 doc/s, dont 85 s où les workers n'ont rien à faire (voir plus bas) |
| Phase 2 | 58 s | 12 529 composantes ; à 1 %, la plupart des arêtes restent pendantes : la durée n'est pas représentative |

Ce que montrent les mesures de la phase 1 :

| Indicateur | Valeur |
|---|---|
| Embedding, par document LEGI | 187 ms en moyenne, **3 928 s** de temps des workers en tout |
| OpenSearch, Mongo, Neo4j, par document LEGI | 13,0 ms, 3,8 ms, 4,0 ms |
| Lecture et parse, par document LEGI | 2,3 ms et 0,7 ms |
| Passages | 66 210, soit 3,15 par document, de 96 tokens en moyenne |
| GPU | 98 % d'utilisation ; bridage thermique sur 1 049 échantillons sur 1 098 ; 80 °C en moyenne |
| Horloge SM, par tiers de la phase | 1 423 → 1 370 → 1 289 MHz |
| TEI | 21 450 requêtes, 68 787 textes, 6,58 M tokens ; **lots GPU de 2,3 textes** (221 tokens) ; 115 ms en file et 101 ms de calcul par requête |
| CPU moyen des conteneurs | TEI 92 %, OpenSearch 12 %, Neo4j 3 %, Mongo 2 % ; Kedro 19 % |

L'embedding représente encore environ 90 % du temps des workers : **le goulot reste
le GPU.** Le débit est d'environ 5 750 tokens/s, soit 60 passages/s.

### Trois constats nouveaux

**1. Des lots trop petits coûtent environ 15 % de débit sur LEGI.** Un document LEGI
compte environ 3 passages. Comme chaque worker envoie une requête par document, il n'y
a jamais plus d'une douzaine de textes en vol, et TEI forme des lots de 2,3 textes,
contre 13,8 sur le corpus du run complet. Un banc d'essai court, sur 1 257 passages du
corpus, le mesure ; le débit est rapporté à l'horloge parce qu'elle varie avec la
température :

| Taille des lots × requêtes en parallèle | Passages/s | Horloge SM | Passages/s par GHz |
|---|---|---|---|
| 3 × 4 | 91,3 | 1 802 MHz | 50,7 |
| 3 × 16 | 103,0 | 1 762 MHz | 58,5 |
| 32 × 4 | 103,8 | 1 741 MHz | 59,6 |
| 3 × 4 (à nouveau) | 88,0 | 1 726 MHz | 51,0 |
| 3 × 32 | 94,2 | 1 577 MHz | 59,7 |

Avec une quarantaine de textes en vol, le GPU retrouve son rendement, que ces textes
arrivent en gros lots ou en beaucoup de petites requêtes.

**2. Les `versions.xml` sont lus quel que soit `ingestion_ratio`.** À la fin de son
flux, le connecteur LEGI relit un par un les 282 633 `versions.xml` mis à part par la
découverte, pour les classer comme artefacts d'export. Cela prend 85 s, pendant
lesquelles les 4 workers attendent. C'est négligeable sur un run complet, mais cela
représente 7 % de la phase 1 d'un run à 1 %.

**3. Le dump global contient des articles en double.** Les 143 rejets du run, soit
0,7 % des documents LEGI, sont tous des `facet_root_duplicated`. Dans le cas examiné
(`LEGIARTI000006201477`), le même article est rangé à la fois sous
`TNC_en_vigueur` et sous `TNC_non_vigueur`. Sur tout LEGI, cela ferait environ
14 000 documents rejetés.

### OpenSearch quand l'index grossit

- **Le coût par document ne bouge pas** : 2,1 à 3,4 ms d'indexation par document côté
  serveur, sur chaque cinquième de la phase, et 13 ms vus du worker, contre 14 ms sur
  1 121 documents.
- **La taille, elle, est à surveiller** : l'index pèse 804 Mo pour 66 210 passages,
  soit environ 12 Ko par passage. Pour tout LEGI, les projections sont les suivantes :

| Base | À 1 % | Projection sur tout LEGI |
|---|---|---|
| OpenSearch | 804 Mo | ≈ 80 Go |
| Mongo | 349 Mo | ≈ 35 Go |
| Neo4j (base seule, hors journaux de transactions) | 47 Mo | ≈ 5 Go |

Le disque `/data`, qui porte les volumes Docker, a 162 Go de libre. Cela suffit, mais
les fusions de segments d'OpenSearch demandent temporairement de la place en plus.

### Projection révisée pour tout LEGI

La phase 1 a pris 54 ms par document (sans compter les 85 s des `versions.xml`). Pour
2,1 millions de documents, cela donne **≈ 32 h**, plus 9 min de découverte. C'est
cohérent avec l'estimation d'environ 30 h.

## Ce qui n'est pas encore mesuré

- **La mémoire de la recherche k-NN à l'échelle.** 6,9 millions de vecteurs de 1 024
  dimensions représentent environ 28 Go bruts, alors que la machine a 14 Go de RAM.
  L'ingestion ne charge pas les graphes k-NN : ce run ne dit rien de leur coût en
  recherche.
- **La phase 2 à l'échelle.** Sa durée dépend de la taille des plus grosses
  composantes du graphe, qu'un run partiel ne reproduit pas.
- **L'ancien échantillon `LEGI_20250712`** est toujours rangé sous `LEGI/`. Ses 769
  identifiants se trouvent aussi dans le dump global : ces documents recevront des
  fichiers des deux dumps à la fois.

## Les leviers

**Ce qui n'aidera pas** : d'autres valeurs pour `EMBEDDING_BATCH_SIZE` ou
`max-batch-tokens`, le réglage de Mongo, d'OpenSearch ou de Neo4j, un parse plus
rapide. Ensemble, ces postes pèsent moins de 10 % du temps, et ce travail se fait déjà
pendant que le GPU calcule.

**Plus de textes en vol, pour LEGI seulement.** Pour `cass` ou `jade`, dont un document
compte plusieurs dizaines de passages, ajouter des workers n'apporte rien. Pour LEGI,
avec environ 3 passages par document, passer de 4 à 16 workers, ou regrouper les
passages de plusieurs documents dans une même requête, rendrait au GPU les **≈ 15 %**
mesurés plus haut, soit environ 4 h sur un run complet.

**Ce qui peut aider**, du plus fort au plus faible :

1. **Calculer moins d'embeddings.** Avec `nuke_all`, chaque run recalcule tous les
   vecteurs.
   - Pour les itérations de développement qui n'ont pas besoin de vecteurs,
     `embedding_enabled: false` existe déjà (ADR-012).
   - Garder les vecteurs d'un run à l'autre, indexés par le modèle et une empreinte du
     texte du passage, limiterait un nouveau run aux passages qui ont changé. C'est un
     choix d'architecture, à décider par ADR.
2. **Refroidir le GPU.** Il passe de 74 passages/s au frais à 57 une fois chaud : il y a
   20 à 30 % à gagner sans toucher au code.
3. **Un GPU plus puissant pour l'ingestion complète.** Le banc d'essai permet de le
   comparer en quelques minutes.
4. **Un modèle plus petit ou quantifié.** Cela change la qualité de la recherche : à
   évaluer avant de décider.
