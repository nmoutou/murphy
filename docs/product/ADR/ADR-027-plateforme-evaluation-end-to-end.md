# ADR-027 — Plateforme d'évaluation end-to-end : le harnais pilote l'ingestion

**Statut** : 🔶 Proposé — 19 juillet 2026 — **étendu par ADR-031**
(22 juillet 2026) : le couple `(W, R)` devient le triplet **`(W, G, R)`**,
`G` = version du graphe, identifiée séparément du fingerprint de `W` (qui ne
couvre que les vecteurs et resterait identique entre deux graphes).
**Version cible** : v0 (harnais P2)

## Contexte

Le cadrage de P2 (`CADRAGE_evaluation`, ADR-016) pose que la récupération
est un composant autonome, évalué seul via un contrat d'adapter unique
(`requête → IDs ordonnés`). Une lecture rapide en tire que le harnais
serait *passif* vis-à-vis de l'ingestion : il consommerait des bases
déjà peuplées et ne balaierait que les paramètres runtime (top-K, seuil,
fusion, rerank, graphe).

Or les leviers les plus structurants de la qualité de récupération —
modèle d'embedding, normalisation, chunking — vivent dans l'ingestion :
ils sont **gravés dans la collection Qdrant** (nommée par empreinte
blake2b du `WorkflowConfig`, cf. modèle de données). Un harnais qui ne
peut pas les faire varier ne peut pas mesurer leur contribution — ce qui
contredit l'exigence même d'un **harnais d'ablations mesurant la
contribution marginale de chaque brique** (`CADRAGE_evaluation` §6).

Il faut lever une confusion sur le mot « agnostique » :

- le **scorer** est agnostique du *comment* (dense/graphe/hybride) — il
  ne voit que des IDs et des qrels : **invariant dur** (ADR-016),
  préservé ;
- le **harnais passif vis-à-vis de l'ingestion** n'était qu'une
  hypothèse de commodité, jamais un invariant : rien dans le cadrage ne
  l'exige.

## Décision

P2 est une **plateforme d'expérimentation end-to-end** : la config
d'évaluation *est* la config du pipeline. Une expérience est décrite par
le couple **`(W, R)`** :

- **`W` (workflow)** — normalisation + chunking + embedding. C'est
  l'objet hashé qui définit la collection Qdrant. Le harnais le passe à
  l'ingestion.
- **`R` (runtime)** — top-K, seuil, fusion, rerank, graphe. Balayé
  par-dessus la collection produite, sans ré-ingestion.

Le pipeline est traité comme une **fonction** que le harnais pilote :

```
ingest(corpus, W)               → collection        [lent, assumé]
retrieve(collection, R, topics) → run               [rapide]
eval = score(retrieve(ingest(corpus, W), R), qrels)
```

Le sweep balaie l'espace **`W × R`**, **séquentiellement** : une seule
ingestion à la fois, `nuke_all` entre deux `W`. Le scorer reste
agnostique.

### Invocation de l'ingestion : sous-processus, pas import

L'ingestion (`data/`) est **pilotée par Kedro** (contexte, catalog,
hooks de télémétrie, publication du pointeur) ; son cœur
(`IngestionRunner`) est enfoui dans cette machinerie et `WorkflowConfig`
est construit depuis les params par une fonction unique
(`_build_workflow_config`, `hooks.py`). P2 invoque donc l'ingestion par
**sous-processus** — `kedro run --params <W>` — Kedro sachant déjà
recevoir des overrides de params en CLI. Couplage réduit à un **contrat
de params + CLI**, sans import profond de `ragcore`.

### Couplage config ↔ collection : contrat répliqué + vérifié

Le bloc `W` sert à la fois d'**entrée d'exécution** (passé à `kedro
run`) et de **clé de traçabilité** : après publication, le harnais
recalcule le fingerprint blake2b de `W` et le compare au pointeur
`MURPHY_META.meta_published_collection`. Divergence = erreur fail-fast.
On **ne partage pas** un `conf/workflow/` physique entre `data/` et
`evaluation/` (ça franchirait la frontière des submodules) ; on réplique
et on vérifie — le schéma répliqué est celui posé par ADR-026. Le calcul
du fingerprint (+ ID de point Qdrant + format `identifier`) est vendored
depuis P1 dans un micro-module partagé, testé des deux côtés.

### Outillage : ranx en ossature

Le scoring, les tests statistiques appariés (ADR-007), la fusion de runs
(ADR-006) et les projections TREC (ADR-008) sont délégués à **`ranx`**.
Restent maison, réduits à l'essentiel : la **coupe adaptative `@R`**
(ADR-007, vérifiée contre `trec_eval`) et l'**agrégation chunk→document**
(ADR-006 : `max` côté qrels, rang du premier chunk côté runs), appliquée
avant `ranx`.

## Alternatives rejetées

- **Harnais passif (sweep runtime seul)** : ne peut pas mesurer la
  contribution de l'embedding/chunking/normalisation — ampute le harnais
  d'ablations exigé par le cadrage.
- **Import de `ragcore` comme lib pour piloter l'ingestion** : obligerait
  P2 à reconstruire le contexte Kedro à la main ; couplage profond et
  fragile à l'API interne de `ragcore`.
- **Socle `conf/workflow/` partagé physiquement** : une source de vérité
  unique, mais franchit la frontière des submodules et recrée un couplage
  config `data`↔`eval` — contraire au client de lecture dédié choisi.
- **Sweep concurrent / parallèle sur plusieurs `W`** : imposerait
  d'isoler Mongo/Neo4j (non partitionnés par empreinte) entre configs
  concurrentes. Le séquentiel + `nuke` l'évite entièrement — lenteur
  assumée (l'embedding est ~99,9 % d'un run ; le temps est disponible).

## Conséquences

- Le harnais gagne un **orchestrateur d'ingestion** (nouvel item
  backlog **B-13**) ; l'ossature (scorer `ranx`, adapter, run store,
  manifest) est inchangée.
- La comparaison de deux `W` se fait sur leurs **runs archivés**
  (immuables — ADR-008), jamais sur des bases coexistantes ;
  `ranx.compare()` compare des runs, rien ne manque.
- Un sweep interrompu est **reprenable** : le manifest de gel dit quels
  `(W, R)` sont déjà évalués.
- **E-P2-10 est étendue** : la reproductibilité couvre désormais `W` (le
  chemin d'ingestion), pas seulement `R`.
- **Dépend d'ADR-026** (restructuration `conf/` en partition
  workflow/ingestion/evaluation) pour le couplage config↔fingerprint.

## Références

`CADRAGE_evaluation` §6-7 · ADR-006 · ADR-007 · ADR-008 · ADR-016
(contrat d'adapter) · ADR-018 (identité, fingerprint) · ADR-026
(restructuration config) · `BACKLOG.md` B-13 · modèle de données
(`data/docs/reference/modele-de-donnees.md`)
