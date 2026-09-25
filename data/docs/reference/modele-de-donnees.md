# Le modèle de données

Ce que le pipeline écrit réellement, base par base. Modèles Pydantic :
`src/ragcore/core/models/` (tous `frozen=True`). Dépôts : `src/ragcore/adapters/storage/`.
Version de schéma : `SCHEMA_VERSION = 3` (`core/models/document.py` — l'historique des
bumps est documenté sur la constante ; un bump = une ré-ingestion complète).

## L'identité d'un document

Un seul `identifier` (union discriminée Pydantic sur le champ `kind`) nomme le document
partout : clé Mongo, payload Qdrant, nœud Neo4j, événements d'audit. Forme sérialisée :
`{kind}:{raw}` (ex. `eli:LEGIARTI000006419264`), réversible par `deserialize_identifier`.

| Type | `kind` | Source | Note |
|---|---|---|---|
| `ELI` | `eli` | LEGI | Format validé à la construction (`^[A-Z]{8}[0-9]{12}$`) ; préfixe → `document_type` (`article`/`texte`/`section`). |
| `DecisionId` | `decision` | les 5 juri | Même motif, type distinct (une décision n'est pas un texte de loi) ; préfixe → ordre de juridiction. |
| `JorfId` | `jorf` | — | Squelette, pas de connecteur. |
| `UploadId` | `upload` | — | Squelette (SHA-256 de contenu). |

Pas de hash de contenu nulle part : l'idempotence se joue sur la **présence de
l'identifiant** dans le manifest.

## Les modèles en mémoire (cycle de vie d'un document)

```
RawDocument ──parse──▶ ParsedDocument ──chunk──▶ Chunk ──embed──▶ EmbeddedChunk
   (connecteur)          (+ citations,             (ordinal, text,     (+ embedding,
    payload=arbre XML     metadata, content,        tag_path,           model, dim)
    transcrit)            structure, source_files)  char_start/end)
```

- `ParsedDocument` : `identifier`, `source`, `owner_id`, `title`, `content` (texte
  intégral lisible), `structure` (sections/references/context — **jamais persisté**,
  voir plus bas), `metadata` (clés = chemin complet de balise), `citations` (tuple de
  `Citation`), `source_files` (provenance, jamais persistée en Mongo).
- `Chunk` : `chunk_id`, `parent_identifier`, `ordinal`, `text`, `tag_path`,
  `char_start`/`char_end` (offsets **littéraux** dans `content`), `metadata`.
- `Relation` : source → cible (deux identifiants), `relation_type` = **verbe validé**
  (chaîne, pas un enum — un verbe non traduit entre sous son nom brut), `metadata`.
- `Citation` : `text` (brut, intégral — la seule donnée non reconstructible), `verb`,
  `sens` (conservé pour orienter l'arête d'une future résolution).

## MongoDB — base de données `LEGIFRANCE`

### `documents`

Un document par (identifier, owner_id) — index **unique** `uq_identifier_owner`, plus
`idx_source_owner`. Écrit par `replace_one(upsert=True)` : remplacement atomique, aucun
instant où l'identifiant n'existe pas.

Contenu : le dump JSON du `ParsedDocument`, **sauf** :

- `identifier` est remplacé par sa forme sérialisée (`eli:…`) — c'est elle qui est
  indexée ;
- `source_files` est exclu (provenance d'inspection, chemins absolus du poste
  d'ingestion) ;
- `structure` est exclue **entièrement** (ADR-022 §4) : `references`/`context` sont de la
  donnée d'arête (elles vivent dans Neo4j), et `sections` est `content` re-découpé — son
  seul apport propre (`path`) survit sur les chunks (`tag_path` + offsets).

Donc : `schema_version`, `identifier` (sérialisé), `source`, `owner_id`, `title`,
`content`, `metadata`, `citations`.

### `manifest`

Le registre **append-only** des tentatives de traitement (`ManifestEntry`) — jamais de
mise à jour, une entrée par tentative. Deux formes :

- **valide** : `identifier_serialized` rempli, `operation` ∈ {`insert`, `update`},
  `targets_written = ["mongo", "qdrant", "neo4j:node"]` (le nœud, pas ses arêtes — dire
  « neo4j » affirmerait une complétude que la phase 1 ne livre pas), `processed_at` ;
- **rejet** : `identifier=None`, `operation=excluded`, `source_path` + `reason`
  obligatoires (invariant validé par le modèle).

Index de lookup (pas uniques — plusieurs entrées par document, une par run) :
`(identifier_serialized, owner_id)` sparse, `(source_path, owner_id)`.

## MongoDB — base méta `MURPHY_META`

Préservée par `nuke_all` : la mémoire de ce qu'on a fait ne doit jamais partir avec les
données.

| Collection | Contenu | Index |
|---|---|---|
| `meta_audit_events` | Les événements d'audit (`AuditEvent` : event_type, run_id, owner_id, source, document_id, payload, success, error_message, occurred_at). Rétention infinie. | (owner_id, occurred_at), (document_id, occurred_at), (run_id), (event_type) |
| `meta_run_summaries` | Un `RunSummary` par run : identité (run_id, owner, source, dates), `status` (`ok`/`degraded`/`failed`), `stats` (counts, breakdowns, unknowns), `error_message`. | unique (run_id), (started_at) |
| `meta_pending_relations` | Les `PendingRelation` : arêtes différées (source_id, target_id, relation_type, metadata, first_seen_run, last_seen_run). Ni TTL ni retry_count : écrite une fois, promue une fois — ou jamais. | **unique** (owner_id, source_id, target_id, relation_type) — c'est lui qui fait de l'upsert une union ; (owner_id, target_id) pour le rejeu ciblé |
| `meta_published_collection` | **Le pointeur** (`PublishedCollection`, singleton clé `current`) : `collection_name` (l'empreinte), `fingerprint`, `run_id`, `document_count`, `published_at`, `serving_contract_version` (absent des pointeurs antérieurs à l'ADR-039). Mis à jour par les seuls runs `ok`, et par un run restreint seulement si la version en place est déjà la sienne ; lu par le backend au boot. | — |

`fingerprint` et `collection_name` sont identiques aujourd'hui **par décision** : le jour
où le nom gagne un préfixe, le serving continue de lire un NOM et la traçabilité une
EMPREINTE.

## Qdrant

- **Nom de collection** : le fingerprint blake2b (32 hex) de la `WorkflowConfig` — jamais
  configuré à la main. Deux configs ⇒ deux collections qui coexistent, chacune droppable
  indépendamment (la condition de l'A/B).
- **Vecteurs** : dimension du workflow (768), distance **Cosine** (codée en dur dans le
  dépôt `QdrantVectorRepository`).
- **ID de point** : SHA-256 du `chunk_id`, replié sur 63 bits — stable entre processus
  (jamais `hash()` natif, resemé par interpréteur).
- **Payload** : les `metadata` du chunk à plat, puis les champs du **contrat de
  serving** (ADR-039,
  version `SERVING_CONTRACT_VERSION` = 1), posés en dernier pour qu'aucune métadonnée
  homonyme ne les écrase :

  | Champ | Rôle côté serving |
  |---|---|
  | `chunk_id` | identité du passage, envoyée au client |
  | `identifier` | document parent dans `documents` (sérialisé, = clé de suppression par document) |
  | `owner_id` | complète la clé du document parent |
  | `char_start`, `char_end` | bornes du passage dans le `content` du parent, en **points de code** |
  | `type_document` (métadonnée, facultatif) | nature du document, affichée comme type de la source |

  Le texte du passage n'est **pas** dans le payload : c'est
  `documents.content[char_start:char_end]`. Les autres métadonnées sont présentes mais le
  serving ne s'y appuie pas. Changer un de ces champs est un bump de version.
- **Écriture** : delete-puis-insert par document (`delete_by_document` puis `upsert`) —
  Qdrant n'a pas de « remplace tous les points de ce document » atomique, et un simple
  upsert laisserait des points orphelins quand la nouvelle version a moins de chunks.

## Neo4j

- **Nœuds documents** : identifiés par `identifier` sérialisé + `owner_id`. Le `MERGE`
  porte sur le seul identifiant (jamais le label — `MERGE (d:Article {…})` créerait un
  second nœud si le label a changé), puis le label réel est posé : `Article`, `Texte`,
  `Section` (dérivé de `document_type`), `Decision`, ou `Document` par défaut. Index sur
  `identifier` pour chaque label connu + `Pending`.
- **Hydratation** (ADR-022 §2) : en prod, nœud **maigre** (`title`, `source`,
  `schema_version`). En dev (et seulement en dev), le hook ouvre les vannes : `metadata`
  en props (clés chemin-complet), `include_path` (les fichiers XML source),
  `include_content` (le texte, prop `_text_content`), les citations. Neo4j est l'outil
  d'inspection de la v0.
- **Arêtes** : écrites en phase 2 uniquement, `MERGE (a)-[r:TYPE]->(b)` avec le **verbe
  comme type d'arête** (type paramétré natif), taguées du `run_id` qui les a posées
  (compensabilité à la maille du run). Une cible absente ne crée pas de nœud fantôme :
  la relation part en pendante.
- **Label `Pending`** : la compensation d'un nœud cité par d'autres le dé-hydrate en
  `:Pending` au lieu de l'arracher (les arêtes entrantes appartiennent à d'autres
  documents) ; un `merge_document_node` ultérieur le ré-hydrate naturellement. Plus de
  label `Unknown` : une cible décrite est une `Citation` sur le document, pas un nœud.

## Fichiers locaux (`data/08_reporting/`)

- `events/{iso}_{run_id}.jsonl` — la trace événementielle complète du run (backend JSONL
  de la télémétrie).
- `stats/{iso}_{run_id}.json` — le `RunSummary` sérialisé (le même que dans
  `meta_run_summaries`).
