# Architecture — pipeline d'ingestion

## Ce que c'est

Un pipeline **Kedro** qui ingère les corpus XML de la DILA (LEGIFRANCE et les cinq bases de
jurisprudence) et peuple les trois bases du serving : MongoDB (contenu), OpenSearch
(recherche lexicale et vectorielle), Neo4j (graphe). Il tourne **hors-ligne et hors-bande** :
il n'est pas dans la stack Docker de serving, et le backend ne l'appelle jamais — les deux
ne partagent que les bases.

## Les deux couches du dépôt

```
data/
├── conf/base/            # parameters.yml, catalog.yml (objets runtime)
├── src/data/             # le SHELL Kedro : délègue tout à ragcore
│   ├── pipeline_registry.py   →  ragcore.orchestration.kedro.pipeline_registry
│   └── settings.py            →  enregistre ragcore…hooks.TelemetryHooks
└── src/ragcore/          # le CŒUR : toute la logique vit ici
    ├── core/             # domaine pur : modèles, ports, services — ne connaît AUCUNE base
    ├── application/      # cas d'usage : runner, saga, résolution de relations
    ├── adapters/         # implémentations : Mongo, Neo4j, OpenSearch, embedders, télémétrie
    ├── sources/          # un dossier par FORMAT XML, le registre qui y relie chaque base
    │   ├── legislatif/   #   LEGI
    │   ├── jurisprudence/#   CAPP, CASS, INCA, JADE, CONSTIT
    │   └── generic/      #   parser, chunker et lecture XML communs
    └── orchestration/    # le pont Kedro : hooks, DAG, nœuds, workload
```

`ragcore` est **vendoré dans ce dépôt** (`src/ragcore/`) — ce n'est plus un paquet externe.
Architecture hexagonale stricte : `core/` déclare des **ports** (interfaces), `adapters/`
les implémente, et `orchestration/kedro/` n'est qu'un shell — un CLI ou un test peut
lancer le même pipeline sans Kedro ni YAML.

## Le DAG

Un seul pipeline, enregistré sous `__default__` et `ingestion` (un alias, pas deux
pipelines). L'ordre est exprimé par les **dépendances de données**, jamais par un
`join()` impératif :

```mermaid
flowchart LR
    nukeAll -- nuke_done --> connect
    connect -- raw_documents --> parseDocuments
    parseDocuments -- to_process --> ingest
    parseDocuments -- to_skip --> report
    ingest -- ingestion_outcome --> resolveRelations
    ingest -- ingestion_outcome --> report
    resolveRelations -- resolution_outcome --> report
```

Deux arêtes portent tout le sens :

- **`nuke_done` → `connect`** : on ne lit pas la source pendant qu'on efface les stores.
- **`ingestion_outcome` → `resolveRelations`** : LA barrière phase 1 / phase 2. Une arête
  Neo4j a besoin que ses deux nœuds existent ; tant que la phase 1 n'a pas fini pour
  *tous* les documents, Kedro ne lance pas la phase 2. La barrière est structurelle.

Les objets runtime (connecteur, parser, dépôts, runner, télémétrie…) ne sont pas des
paramètres : ce sont des `MemoryDataset` que `TelemetryHooks.before_pipeline_run`
construit et pose au catalogue (`catalog.yml`, tout en `copy_mode: assign`). Le DAG les
**nomme**, le hook les **fournit**.

Déroulé détaillé nœud par nœud : [reference/pipeline.md](reference/pipeline.md).

## Les deux phases

- **Phase 1 — documents** (`ingest`) : un pool de 4 workers, dispatch par clé document
  (hash blake2b de l'identifiant). Chaque worker a sa boucle asyncio, ses clients Mongo /
  Neo4j / OpenSearch, sa télémétrie et son agrégat local : rien de mutable n'est partagé, donc
  aucun verrou. Le travail d'un document (le *workload*) : extraction des relations
  et des relations non formatées → chunking → embedding → saga d'écriture (Mongo →
  relations non formatées `MURPHY_DATA.unformatted_relations` → OpenSearch → nœud Neo4j).
- **Phase 2 — relations** (`resolveRelations`) : après la barrière, un service unique
  écrit les arêtes en batch, met en attente celles dont la cible n'est pas dans le corpus
  (`MURPHY_DATA.pending_relations`) et **promeut** les pendantes de runs passés dont la cible
  vient d'arriver.

## Les principes qui structurent tout le reste

1. **Fail-fast, jamais de dégradation silencieuse.** Un `parameters.yml` illisible arrête
   le run ; un `.env.dev` absent lève ; une source inconnue échoue au démarrage en nommant
   les valides ; le modèle servi par TEI est vérifié (`GET /info`) avant la moindre écriture.

2. **« Rien en silence ».** Tout ce qui est vu est compté : documents écartés, invalidés,
   échoués, compensations, vocabulaire inconnu. Le statut d'un
   run (`ok`/`degraded`/`failed`) se **dérive des compteurs** — l'équation de complétude
   `vus == ingérés + exclus + échoués` — jamais de l'absence d'exception.
   Voir [reference/telemetrie.md](reference/telemetrie.md).

3. **Un index OpenSearch, un nom fixe.** `OPENSEARCH_INDEX` (`.env.dev`), que le backend
   lira aussi (ADR-018, ADR-028). Un run réécrit l'index en place : après un changement du
   mapping, des analyseurs, du `chunking` ou du modèle d'embedding, tout le corpus se
   réingère. Voir [reference/configuration.md](reference/configuration.md) et
   [reference/index-opensearch.md](reference/index-opensearch.md).

4. **Une source = une ligne de données, pas une classe.** Le parser, le chunker et
   l'extracteur sont **génériques** ; la spécificité d'une source tient dans une table de
   rôles déclarative et un connecteur (`sources/registry.py`). Ajouter une source n'ajoute
   pas une ligne au hook.
   Voir [reference/sources.md](reference/sources.md).

5. **Les garde-fous penchent vers le refus.** Les commodités de dev vivent dans un seul
   bloc, `dev` de `parameters.yml`, et `ENVIRONMENT` absent vaut `prod`. Hors `dev`, le
   bloc est ignoré : rien n'est effacé, l'embedding est toujours calculé, les nœuds
   Neo4j restent maigres, les balises non configurées ne sont pas ingérées. Une commodité
   de dev ne peut pas dégrader une prod par simple oubli d'une variable.

## Frontières avec le serving

| Contrat | Écrit par l'ingestion | Lu par le backend |
|---|---|---|
| Contenu | Mongo `MURPHY_DATA.documents` | documents parents par `identifier`, passage = `content[char_start:char_end]` |
| Recherche | OpenSearch, index `OPENSEARCH_INDEX` (nom fixe, ADR-018, ADR-028) : documents, passages, vecteurs | la requête hybride du backend (ADR-028, ADR-029) |
| Graphe | Neo4j (nœuds + arêtes typées par verbe) | pas encore câblé côté serving |

Le modèle d'embedding et sa dimension (`all-mpnet-base-v2`, 768, Cosine) doivent être les
mêmes des deux côtés — c'est pour ça qu'il n'y a qu'**un** `.env.dev`, à la racine du dépôt,
partagé par le pipeline et le conteneur TEI.
