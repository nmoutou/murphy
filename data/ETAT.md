# État des lieux — 14 juillet 2026

> **Document temporaire.** À supprimer une fois son contenu absorbé (dans les artéfacts, ou
> dans un commit qui rend ce texte inutile).
>
> ⚠️ **Ce fichier vieillit mal — et il l'a encore prouvé.** Sa version du matin annonçait
> « 235 tests verts » (il y en a **208**, dont **4 rouges**), « le GPU plafonne à 25 W »
> (**59,5 W** mesurés) et « rien n'est commité » (le lot A l'était). Les versions d'avant
> affirmaient « le RunSummary est aveugle » et « `chunk_size` est une mesure à faire » —
> corrigés tous les deux.
>
> **Le code et les bases répondent ; ce document, lui, se souvient.** Vérifier avant de croire.

---

## L'état, mesuré

| | |
|---|---|
| documents | **1121** (769 LEGI + capp 1, cass 92, inca 1, jade 256, constit 2) |
| complétude | `fetched 1121 == persisted 1121` — **0 perdu**, statut `ok` **dérivé** |
| durée d'un run | **188 s** (dont ~150 s d'ingestion ; 838 s le 13 juillet) |
| chunks | 18 090 (`chunk_size: 384`) |
| Qdrant | `9424808d…` — 18 090 vecteurs, 766/768 dims non nulles |
| Neo4j | 352 `Document`, 68 `Unknown`, 19 032 relations pendantes |
| audit Mongo | **20 156 lignes — `émis == persisté`, event par event** (voir plus bas) |
| tests | **208** (185 unitaires + 23 d'intégration) — ⚠️ **4 échouent**, voir §pièges |

Le lot A est **commité et poussé** (`bf6d717`). La non-fuite télémétrique ne l'est pas encore.

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
Tout le reste est du bruit. Le mur est le **GPU** : RTX 3050 Laptop, ~90 textes/s au mieux,
**saturée** (mesuré pendant le run du 14 juillet : **100 % d'utilisation, 59,5 W** — la
mention « plafonnée à 25 W » était fausse ; la conclusion, elle, ne change pas).

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

### ✅ La télémétrie s'observe ELLE-MÊME — `audit.write.failed`

Le système comptait ce qu'il **émettait** ; il ne vérifiait pas que ce qu'il avait émis était
**arrivé**. Quatre points avalaient une écriture d'audit ratée. Tous la logguaient en
`warning` — **aucun ne la comptait** :

| # | Où | Ce qui se passait |
|---|---|---|
| 1 | `AsyncioRuntime._drain` | `gather(return_exceptions=True)` → résultat **jeté** |
| 2 | `MongoAuditTelemetryAdapter.emit` | `except` → `warning` (branche sync) |
| 3 | `RegistryAwareTelemetry.emit` | un `except` par backend |
| 4 | `RegistryAwareTelemetry.close` | idem à la fermeture |

Le principe « la télémétrie ne fait jamais échouer l'ingestion » **ne bouge pas** : ces
exceptions restent isolées. Ce qui change : ***ne pas casser* ne signifie plus *ne pas dire*.**
Chaque perte émarge à `audit.write.failed` (breakdown **par backend** : qui a lâché), donc au
bilan, donc au statut.

**Un audit troué DÉGRADE le run** — et il se teste **avant** l'équation de complétude :

```python
if stats.counts.get(AUDIT_WRITE_FAILED, 0):   # ⚠️ AVANT le court-circuit « rien vu »
    return RunStatus.DEGRADED
```

> **Pourquoi cet ordre.** Un audit mort peut avoir emporté jusqu'à `document.fetched`. Tester
> la complétude d'abord verrait « rien vu » et conclurait « run à vide, donc `ok` » : un run
> **aveugle** passerait pour un run complet. La propriété la plus faible — *mes compteurs
> sont-ils fiables ?* — se vérifie en premier, parce que **toutes les autres en dépendent**.
> Un audit qui fuit ne dit pas *qu'il manque des documents* ; il dit qu'on **ne peut plus
> savoir** s'il en manque.

Deux garde-fous non négociables, tous deux dictés par la nature du problème :
`audit.write.failed` porte **`track_mongo=False`** (écrire en Mongo qu'on n'a pas su écrire en
Mongo est un serpent qui se mord la queue), et le compteur va **droit à l'agrégat** — jamais
réémis par le fan-out, sinon l'échec d'une écriture déclencherait une écriture.

### 🔍 Le CINQUIÈME trou — celui que le plan ne prévoyait pas

Le correctif « faire lire à `_drain` le résultat de `gather` » était vert sur trois trous et
**aveugle sur le cas le plus courant**. Un test l'a dit, pas une relecture :

> **`asyncio.all_tasks()` ne rend que les tâches NON TERMINÉES.**

Une écriture d'audit qui rate **vite** (Mongo refuse la ligne — le cas normal d'un backend en
panne) est **déjà finie** quand le drain regarde : elle a disparu du registre de la boucle.
**Aucun drain, si bien écrit soit-il, n'aurait pu la voir.** Son exception partait dans le
néant, avec pour seule trace le `Task exception was never retrieved` d'asyncio.

D'où `AsyncRuntime.spawn()` : **le runtime RETIENT ses tâches** et draine sa propre liste. Ça
règle au passage un piège classique — asyncio ne tient qu'une référence **faible** aux tâches,
donc le GC peut en ramasser une **en plein vol** : une écriture d'audit pouvait simplement ne
jamais s'exécuter.

Le port se scinde en conséquence : **`drain() -> DrainReport`** (idempotent, *dit* ce qui a
raté) et `close()` (ferme ; draine encore de lui-même, sûr par défaut). L'ordre devient un
invariant : **`drain()` → compter → persister le bilan → `close()`**. Draine-t-on seulement
dans `close()`, et l'échec arrive **après** le bilan qu'il aurait dû dégrader.

### ✅ Prouvé sur le vrai run — `émis == persisté`

Le bilan du run `59418315…` (statut `ok`) confronté à la collection `MURPHY_META.meta_audit_events` :

| event | émis (`RunStats`) | persisté (Mongo) |
|---|---|---|
| `relation.pending` | 19 032 | 19 032 |
| `document.persisted` | 1 121 | 1 121 |
| `pipeline.run.started` / `completed` | 1 / 1 | 1 / 1 |

**20 156 écritures, zéro perdue.** `audit.write.failed` est **absent** du bilan — et c'est le
résultat attendu : sur un run sain, ce travail doit être **invisible**. *Un cliquet qui se
déclencherait tout seul serait pire qu'inutile.* (`document.fetched` / `parsed` restent hors
Mongo : `track_mongo=False` **délibéré**, pas une perte.)

⚠️ **Ce run ne prouve pas que le compteur se déclenche** — un run sain ne peut pas le montrer.
Ce sont les **16 tests unitaires** qui l'établissent, en *provoquant* l'échec (backend qui
lève, tâche qui rate avant le drain). **Les deux sont nécessaires** : le run vérifie le
*câblage*, les tests vérifient le *comportement en panne*. Ni l'un ni l'autre seul ne suffit.

---

## ⚠️ Les pièges actifs

### `nuke_all` (ex-`force_drop`) efface TOUT — et c'est désormais assumé

**Renommé et re-scopé le 15 juillet.** `force_drop` était trois booléens par store, au sens
ambigu (« scopé à CETTE collection », disait le YAML pour Qdrant). C'est maintenant **un seul
interrupteur** `maintenance.nuke_all`, dont le contrat est explicite : **efface TOUTES les
données de TOUTES les bases** en tête de run — Mongo `documents`+`manifest`, graphe Neo4j
entier, **et toutes les collections Qdrant du store** (`drop_all_collections`, pas seulement
celle du fingerprint courant). **La base méta `MURPHY_META` est PRÉSERVÉE** (audit, bilans,
pendantes — un nuke ne doit jamais emporter la mémoire de ce qu'on a fait).

Ce qui était un **piège** (`--params source=cass` effaçait les six sources sans le dire) est
donc devenu le **comportement voulu et nommé** : `nuke_all` = « je repars de zéro, entièrement ».
La décision de doctrine (« scoper le drop par source ») est **tranchée par le renommage** : on
assume le tout-ou-rien.

🔒 **Garde-fou d'environnement.** Le node `nukeAll` **lève `NukeAllOutsideDevError` avant toute
écriture** si `ENVIRONMENT != "dev"`. `InfraSettings.environment` défaut = `"prod"` : **absence
de `ENVIRONMENT` ⇒ prod ⇒ refus** (un garde-fou qui s'ouvre par défaut ne protège rien).
⚠️ **Conséquence opérationnelle :** `nuke_all: true` étant actif par défaut dans
`parameters.yml`, le prochain `kedro run` **échouera** tant que `ENVIRONMENT=dev` n'est pas dans
le `.env.dev` racine.

⚠️ *Corollaire de méthode :* ne **jamais** lancer un `kedro run` sous un `timeout` court —
non pour sauver les données, mais parce qu'un run coupé donne une **mesure fausse**.

### Le tokenizer et le chunker ne parlent pas la même langue

`chunk_size` est en **caractères**, la fenêtre du modèle en **tokens**. Le ratio n'est pas
constant : mesuré, **3,08 car/token en moyenne mais 0,33 au pire** (chunks de sigles et de
ponctuation). **Aucune valeur en caractères n'est sûre par construction.** Le fallback
rattrape ; la cause demeure.

### ✅ Les 4 tests d'intégration Qdrant sont RÉPARÉS

Ils échouaient sur `Collection 'chunks_test' doesn't exist` : la fixture n'appelait pas
`ensure_collection()`, alors que la création de collection avait été **délibérément sortie**
d'`upsert` (un check-then-act depuis N workers produit une course 409 que la saga prend pour
un échec métier). Les tests exerçaient donc un contrat **volontairement abandonné**.

Corrigé dans `1d68f21` (même commit que la non-fuite) : la fixture appelle désormais
`ensure_collection()`, comme le vrai pipeline. **Vérifié le 15 juillet contre un vrai Qdrant
(testcontainers `v1.12.4`) : 6/6 verts.** Lancer avec `pytest -m integration` (le `addopts`
porte `-m 'not integration'`, exclu par défaut). NB : `qdrant-client 1.18.0` râle contre le
serveur `1.12.4` du conteneur — cosmétique, côté test uniquement.

### La stack d'ingestion se lance par `npm run ingest:up`, JAMAIS à la main

Un `docker compose up` nu **omet `--env-file .env.dev`** ⇒ `${EMBEDDING_MODEL}` se résout en
chaîne vide ⇒ TEI démarre avec `--model-id ""` et meurt sur un 404
(`https://huggingface.co//resolve/main/config.json` — **double slash**, le nom du modèle est
absent). Rencontré en vrai. Les scripts `npm` du parent portent le `--env-file` ; la commande
nue, non.

---

## Ce qui reste

### 1. 🔴 Le serving est cassé d'avance — LE seul point qui bloque le produit

Le backend lit `QDRANT_COLLECTION=chunks` — **qui n'existe pas**. Et l'A/B a laissé **quatre
collections**, *re-mesurées le 14 juillet, toujours là* :

| empreinte | vecteurs |
|---|---|
| `3119c73a…` | 61 975 |
| **`9424808d…`** | **18 090** ← celle que le run courant écrit |
| `a71d883b…` | 6 824 |
| `b3058161…` | 13 420 |

Il n'y a plus *une* candidate mais quatre, et **rien ne dit laquelle fait foi**.

> ⚠️ **Mis à jour le 15 juillet.** L'ancien `force_drop` ne nettoyait *pas* les collections
> orphelines (il vidait le corpus **dans** la collection de l'empreinte courante). Le nouveau
> **`nuke_all` les efface toutes** (`drop_all_collections`) : un run `nuke_all` en `dev`
> repart désormais d'un store Qdrant **vide**, donc les quatre empreintes ci-dessus
> disparaissent au prochain run nuké. **Cela ne résout PAS le point** — ça supprime les
> orphelines, mais la question « quelle collection le backend doit-il lire ? » reste entière
> tant qu'aucun pointeur n'est écrit. Un run laisse *une* collection (celle du fingerprint
> courant) ; encore faut-il que le backend sache que c'est elle.

**Correctif décidé :** le pipeline écrit un **document de méta « collection courante »** que
le backend lit au boot. **Seul un run `ok` met à jour le pointeur** — un run `degraded` a
laissé un corpus incomplet, et le publier propagerait la fuite jusqu'à l'utilisateur. C'est
là que l'équation de complétude cesse d'être un outil de diagnostic pour devenir **la
condition de publication**.

> **Ce que la non-fuite télémétrique vient de changer pour ce point.** La condition de
> publication est `status == ok`. Ce statut ne valait que ce que valaient ses compteurs — et
> rien ne garantissait qu'ils étaient complets. Maintenant si. **La brique de confiance est
> posée ; la brique de publication reste à poser.**

### 2. `on_pipeline_error` rend un bilan pauvre

Les stats des workers ne remontent que par le node `report`, **terminal**. Un pipeline qui
casse avant lui ne persiste que les compteurs du process principal — au moment précis où on a
le plus besoin du détail. Corriger demanderait un point de remontée **par phase**.

*Inchangé par la non-fuite* : `on_pipeline_error` draine désormais lui aussi (donc un run
cassé **dit** si sa trace est trouée), mais les compteurs *des workers* restent absents du
bilan d'un run qui casse tôt. La télémétrie est honnête sur ce qu'elle a ; elle n'a toujours
pas tout.

### 3. Le chunker devrait compter en TOKENS → **DÉPLACÉ dans le Lot C**

Le fallback rattrape les débordements, mais rien ne garantit l'alignement. Ce point **n'est
plus autonome** : son tokenizer d'autorité est *celui qui embed*, donc il dépend de quel
service d'embedding on utilise. Il devient un **livrable du Lot C** (embedding maison), acté
le 15 juillet — voir l'artéfact de cadrage. Décisions déjà prises : tokeniser **avec offsets**
(jamais re-décoder, pour préserver l'invariant char_start/char_end), port `TokenCounter`
injecté (chunker pur/sync). Le service maison exposera `/tokenize` rendant les offsets.

### 4. Le lot B — la dette de doctrine

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

### 5. Deux questions ouvertes, pas des tâches

- **La pertinence n'est PAS mesurée.** `chunk_size: 384` est un compromis de *performance*.
  Personne n'a vérifié qu'il **retrouve le bon article de loi**. Le fingerprint existe pour
  cet A/B, et les quatre collections sont déjà là, côte à côte. Il manque un jeu de questions
  de référence. *Décision prise : on garde 384 pour l'instant (dev rapide) ; un système de
  benchmark itératif exhaustif viendra.*
- **Le matériel est-il le bon ?** Le GPU est le plafond absolu. Une carte correcte diviserait
  encore le temps par dix et rendrait le débat sur `chunk_size` beaucoup moins contraint.

---

## Recommandation d'ordre

~~2. La preuve de non-fuite télémétrique~~ — ✅ **faite** (et elle a révélé un cinquième trou
que le plan ne voyait pas). C'était l'instrument qui garantit tous les autres : **le statut
d'un run vaut désormais ce que valent ses compteurs, et ses compteurs se surveillent.**

~~2. Réparer les 4 tests Qdrant~~ — ✅ **fait** (corrigé dans `1d68f21`, 6/6 verts contre un
vrai Qdrant le 15 juillet).

~~3. Le chunker en tokens~~ — **déplacé dans le Lot C** (son tokenizer d'autorité dépend du
service d'embedding).

Reste, dans l'ordre :

1. **Le pointeur de collection** — le **seul point qui bloque le produit**. Côté ingestion il
   est **déjà câblé** (`1d68f21` : le hook publie l'empreinte si `status == ok`, via
   `PublishedCollection` + `MongoPublishedCollectionRepository`). Reste **le backend** qui doit
   le lire au boot au lieu de `QDRANT_COLLECTION=chunks` — *hors de ce repo* (submodule
   `backend/`).
2. Le **lot B** (dont le **§1 registre d'alias**, seul élément de la liste qui débloque une
   *capacité* — la résolution juri — au lieu de consolider l'existant).
3. Le **Lot C** — embedding maison (+ chunker en tokens). Nouveau chantier, cadré le
   15 juillet ; ne bloque pas le produit.

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

**Une quatrième fois, le 14 juillet au soir** : « le lot A n'est pas commité » — il l'était.
J'avais lu le hash en tête (`bf6d717`) **sans regarder la date** (72 minutes), et son message
ressemblait aux précédents. *Le même défaut, sur la même journée, après l'avoir écrit ici.*

Et celle du code, qui a servi quatre fois :

> **Un correctif validé sur un test unitaire ne prouve rien du chemin réel.** Le test vérifie
> la *fonction* ; seul un run vérifie le *câblage*.

---

## La leçon de la non-fuite — l'inverse de la précédente

Le cinquième trou (`asyncio.all_tasks()` oublie les tâches terminées) n'a **pas** été trouvé
par un run : le run est vert, il l'est toujours, et il le serait resté. Il a été trouvé par un
**test qui a échoué** — un test qui *provoquait* la panne qu'aucun run sain ne produit.

> **Le run prouve le câblage ; seul un test peut prouver le comportement en PANNE.**
> Un chemin d'erreur que rien n'exerce est un chemin d'erreur qu'on n'a jamais écrit. Les deux
> vérifications sont **complémentaires, pas redondantes** — et c'est celle qu'on saute qui
> cache le bug.

Corollaire, valable au-delà de ce lot : **un `except` qui logge est un `except` qui ment.**
Les quatre trous logguaient tous consciencieusement en `warning`. Le défaut n'a jamais été
qu'on ne *disait* rien — c'est qu'on ne **comptait** rien, donc qu'aucun bilan ne pouvait en
tenir compte. *Un échec qui ne compte pas est un échec qui n'existe pas.*
