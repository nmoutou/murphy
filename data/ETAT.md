# État des lieux — 14 juillet 2026

> **Document temporaire.** À supprimer une fois son contenu absorbé (dans les artéfacts, ou
> dans un commit qui rend ce texte inutile).
>
> ⚠️ **Ce fichier vieillit mal.** Sa version précédente affirmait « le RunSummary est
> aveugle » (corrigé), « `chunk_size` est une mesure à faire » (faite, tranchée) et ignorait
> le vrai mur de performance. **Le code et les bases répondent ; ce document, lui, se
> souvient.** Vérifier avant de croire.

---

## L'état, mesuré

| | |
|---|---|
| documents | **1121** (769 LEGI + capp 1, cass 92, inca 1, jade 256, constit 2) |
| complétude | `fetched 1121 == persisted 1121` — **0 perdu**, statut `ok` **dérivé** |
| durée d'un run | **150 s** (contre 838 s le 13 juillet) |
| chunks | 18 090 (`chunk_size: 384`) |
| Qdrant | `9424808d…` — 18 090 vecteurs, 766/768 dims non nulles |
| Neo4j | 352 `Document`, 68 `Unknown`, 19 032 relations pendantes |
| tests | **235 verts** |

**Rien n'est commité.** 16 fichiers modifiés.

---

## Ce que la journée a changé

### ✅ `kedro run` nu ingère les SIX sources

Le défaut était `legi` : un `kedro run` nu laissait **cinq bases sur six intactes**, sans le
dire, et se terminait « ok ». `sources/composite.py` : `CompositeConnector` +
`RoutingParser` / `RoutingRelationExtractor` (aiguillent sur `document.source`). Les trois
respectent les ports existants ⇒ **aucun nœud du DAG n'a bougé**. Restriction toujours
possible : `--params source=cass,jade`.

> **La leçon :** changer `InfraSettings.source = "all"` en Python n'a **rien** fait —
> `.env.dev` portait `SOURCE=legi`, et pydantic-settings donne (à raison) priorité à
> l'environnement. *Le vrai défaut vivait dans le `.env`, pas dans le code.*

### ✅ Le RunSummary voit enfin les workers

Les `RunStats` des workers ne remontaient **jamais** au hook : `report_node` les rendait dans
un `MemoryDataset` que personne ne lisait. Le compteur de compensations était donc
**structurellement nul**, et le statut **structurellement `ok`**.

Le node `report` **pousse** désormais l'agrégat dans le hook (`RunStatsSink`). Il ne peut pas
tirer : **Kedro libère un `MemoryDataset` dès son dernier lecteur** (`_release_datasets`) — un
`catalog.load()` en `after_pipeline_run` tombe sur un dataset vide. *Le catalogue est un
tuyau entre nodes, pas un lieu de rendez-vous post-run.*

### ✅ Le statut se dérive de l'ÉQUATION DE COMPLÉTUDE

```
vus == ingérés + exclus + échoués        et        échoués == 0
```

Deux propriétés distinctes, qu'il ne faut pas confondre : **le run est-il honnête ?**
(l'équation tombe-t-elle ?) et **a-t-il tout ingéré ?** (un échec *déclaré* reste un document
perdu). Les deux mènent à `degraded`.

> **Un critère qui nomme UNE cause ne voit pas les autres.** L'ancien ne regardait que
> `SAGA_COMPENSATION_STARTED` — il a laissé passer 98 documents rejetés **avant** la saga.
> L'équation ne nomme aucune cause : elle attrapera la prochaine fuite, celle qu'on n'a pas
> encore rencontrée.

Il manquait la matière : **`document.failed` n'existait pas**. L'échec partait en
`telemetry.log()` — console seulement, *tracé mais jamais compté*. C'est **exactement** pour
ça que la fuite était invisible.

⚠️ Le référentiel est `document.fetched`, **jamais** `parsed` : un document invalidé n'est
*pas* parsé (`compute_idempotence` émet `INVALIDATED` **à la place**, puis `continue`).

### ✅ Le run est 5,6× plus rapide — `chunk_size: 384`

**L'embedding est 99,9 % du temps** (1364 ms/doc contre 0,9 ms de parse, 0,1 ms de chunk).
Tout le reste est du bruit. Le mur est le **GPU** : RTX 3050 Laptop plafonnée à **25 W**,
~90 textes/s au mieux, saturée.

| chunk_size | run | chunks | documents perdus |
|---|---|---|---|
| 128 | 838 s | 61 975 | 0 |
| **384** | **150 s** | 18 090 | **0** |
| 512 | 160 s | 13 469 | **1** |
| 1024 | 153 s | 5 606 | **98** |

384 est **le plus grand qui tienne** : mesuré au tokenizer du modèle sur les six sources,
300 tokens au maximum (fenêtre : 384). Au-delà de 384 on ne gagne presque plus rien (le GPU
travaille **au token**, pas au chunk) — on ne fait que perdre des documents.

Empreinte : `3119c73a…` → **`9424808d…`**. Le golden a refusé le changement (son rôle) ; il
a été **enregistré**, pas contourné. Les vecteurs de 128 restent nommables.

### ✅ Fallback d'embedding — un chunk trop long est SAUVÉ

Le service rejette (`413`) un lot hors fenêtre, sans dire **lequel** déborde. L'embedder
**dichotomise** : couper en deux, réessayer ⇒ en `log(n)` requêtes le coupable est isolé, et
**lui seul** est raccourci de moitié, récursivement. **La récursion termine par
construction**, et surtout : **la garde ne connaît pas la fenêtre du modèle — elle la
découvre.** Elle survivra à un changement de modèle.

Prouvé sur le vrai TEI à `chunk_size=1024` (la config qui perdait 98 documents) :
**0 perdu**, 111 chunks raccourcis, et le bilan **le déclare** (`chunk.truncated: 111`).
Le cas nominal ne paie rien.

---

## ⚠️ Les pièges actifs

### `force_drop` est GLOBAL

Il efface **tout le corpus** en tête de chaque run — pas seulement la source du run. Donc
`--params source=cass` **efface les six sources**. La restriction par paramètre promet un
« rejeu ciblé » qui **n'est pas ciblé**.

**En v0 ce n'est PAS une urgence** (les données sont jetables, le corpus se régénère en
2 min). C'est une gêne, pas une perte. La décision de doctrine reste à prendre : scoper le
drop par source, ou assumer que `force_drop` = « je repars de zéro ».

⚠️ *Corollaire de méthode :* ne **jamais** lancer un `kedro run` sous un `timeout` court —
non pour sauver les données, mais parce qu'un run coupé donne une **mesure fausse**.

### Le tokenizer et le chunker ne parlent pas la même langue

`chunk_size` est en **caractères**, la fenêtre du modèle en **tokens**. Le ratio n'est pas
constant : mesuré, **3,08 car/token en moyenne mais 0,33 au pire** (chunks de sigles et de
ponctuation). **Aucune valeur en caractères n'est sûre par construction.** Le fallback
rattrape ; la cause demeure.

---

## Ce qui reste

### 1. 🔴 Le serving est cassé d'avance — et c'est PIRE qu'avant

Le backend lit `QDRANT_COLLECTION=chunks` — **qui n'existe pas**. Et l'A/B a laissé **quatre
collections** (`3119c73a…` 61 975, `9424808d…` 18 090, `a71d883b…` 6 824, `b3058161…`
13 420) : il n'y a plus *une* candidate mais quatre, et **rien ne dit laquelle fait foi**.

**Correctif décidé :** le pipeline écrit un **document de méta « collection courante »** que
le backend lit au boot. **Seul un run `ok` met à jour le pointeur** — un run `degraded` a
laissé un corpus incomplet, et le publier propagerait la fuite jusqu'à l'utilisateur. C'est
là que l'équation de complétude cesse d'être un outil de diagnostic pour devenir **la
condition de publication**.

### 2. Prouver que la télémétrie ne perd rien

**Il n'y a AUCUNE fuite aujourd'hui** — vérifié event par event. `document.fetched` et
`document.parsed` ont `track_mongo=False` **délibérément** (agrégés, pas archivés ligne à
ligne : 1121 lignes pour dire « j'ai parsé » serait du volume sans information).

Mais le système **compte ce qu'il émet ; il ne vérifie pas que ce qu'il a émis est arrivé**.
`MongoAuditTelemetryAdapter.emit()` **avale ses erreurs d'écriture** dans un
`_LOGGER.warning`. Si Mongo refusait une ligne, rien ne le saurait.

**Proposition :** appliquer l'équation de complétude **à la télémétrie elle-même** — pour les
events `track_mongo=True`, `émis == persisté`, et un écart dégrade le run. Même idée qu'au
niveau des documents, un étage plus bas.

### 3. `on_pipeline_error` rend un bilan pauvre

Les stats des workers ne remontent que par le node `report`, **terminal**. Un pipeline qui
casse avant lui ne persiste que les compteurs du process principal — au moment précis où on a
le plus besoin du détail. Corriger demanderait un point de remontée **par phase**.

### 4. Le chunker devrait compter en TOKENS

Le fallback rattrape les débordements, mais rien ne garantit l'alignement. **Piste :
embarquer le tokenizer localement** (`tokenizers`, quelques Mo, pas de réseau). Le chunker
resterait **pur et synchrone** mais compterait dans la bonne unité — dépendant du **modèle**,
pas du **service**. Et le modèle est *déjà* dans le fingerprint : chunking et embedding
partagent déjà une identité, il est cohérent qu'ils partagent le tokenizer.

### 5. Le lot B — la dette de doctrine

| | État |
|---|---|
| **§1 registre d'alias** (`AliasRegistry`, `CanonicalKey`) | zéro occurrence |
| **§9 MLflow / `ExperimentTracker`** | zéro occurrence (« MLflow dès v0 ») |
| **§12 backends typés** | clés-strings toujours là (`adapters/telemetry/factory.py`) |
| **§8 manifest dans la saga** | il est **après** elle |
| **§8 compensation Neo4j exacte** | pas de tag `run_id`, pas de DETACH conditionnel |
| **§5 `structural_path` → `source_path`** | jamais renommé |
| `tests/contract/` · `nodes/discover.py` | absents |
| deadcode `src/data/pipelines/embedding/` | toujours là |
| **§12 breakdown par SOURCE** | absent — sur un run à six sources, le bilan ne dit pas *laquelle* a échoué |

**Le §1 est le chemin critique de la résolution juri** — et **il ne suffit pas**. Les `<LIEN>`
juri **décrivent** leur cible en français au lieu de l'identifier ⇒ il faut *aussi* un
**extracteur de références juridiques**. Deux briques, pas une. Aucune ré-ingestion
nécessaire : la phrase est déjà dans le graphe.

### 6. Deux questions ouvertes, pas des tâches

- **La pertinence n'est PAS mesurée.** `chunk_size: 384` est un compromis de *performance*.
  Personne n'a vérifié qu'il **retrouve le bon article de loi**. Le fingerprint existe pour
  cet A/B, et les quatre collections sont déjà là, côte à côte. Il manque un jeu de questions
  de référence. *Décision prise : on garde 384 pour l'instant (dev rapide) ; un système de
  benchmark itératif exhaustif viendra.*
- **Le matériel est-il le bon ?** Le GPU est le plafond absolu. Une carte correcte diviserait
  encore le temps par dix et rendrait le débat sur `chunk_size` beaucoup moins contraint.

---

## Recommandation d'ordre

1. **Le pointeur de collection** — c'est ce qui **bloque le produit**, et c'est net.
2. **La preuve de non-fuite télémétrique** — pas une urgence (rien ne fuit), mais c'est
   l'instrument qui garantit tous les autres.
3. **Le chunker en tokens** — supprime la cause plutôt que de la rattraper.
4. Puis le **lot B**.

---

## La leçon de la journée — et elle est sur MOI

**Trois fois** j'ai conclu sur une mesure mal lue, et chaque fois j'ai perdu plus de temps que
le bug ne m'en aurait coûté :

- « les shards sont vides » — ils ne l'étaient pas (le logger Kedro **enveloppe** ses lignes,
  mon `grep` coupait les compteurs) ;
- « le run a tourné pendant que j'éditais » — faux ;
- « `chunk.truncated` fuit » — **il n'y a aucune fuite** : ma requête cherchait 111 lignes sur
  un run qui n'avait eu **aucune** troncature.

> **Ne jamais conclure sur l'absence d'un motif dans un `grep`.** Lire la mesure en entier.

Et celle du code, qui a servi quatre fois :

> **Un correctif validé sur un test unitaire ne prouve rien du chemin réel.** Le test vérifie
> la *fonction* ; seul un run vérifie le *câblage*.
