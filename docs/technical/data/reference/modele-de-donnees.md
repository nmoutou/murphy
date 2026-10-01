# Le modèle de données

Ce que le pipeline écrit réellement, base par base. Modèles Pydantic :
`src/ragcore/core/models/` (tous `frozen=True`). Dépôts : `src/ragcore/adapters/storage/`.

## L'identité d'un document

Un seul `identifier` (le type `Identifier`) nomme le document partout : clé Mongo,
payload Qdrant, nœud Neo4j, événements de télémétrie. Sa forme sérialisée est la valeur brute
de la DILA, sans rien ajouter : `LEGIARTI000006419264`.

Le format est validé à la construction (`^[A-Z]{8}[0-9]{12}$`) pour toutes les sources.
Les 8 lettres de tête (`Identifier.prefix`) disent le fonds et la nature du document :

| Préfixe | Source | Nature |
|---|---|---|
| `LEGIARTI` / `LEGITEXT` / `LEGISCTA` | LEGI | article, texte, section |
| `JURITEXT` / `CETATEXT` / `CONSTEXT` | les 5 juri | décision judiciaire, administrative, constitutionnelle |
| `JORFTEXT` / `JORFARTI` | — | cible de liens LEGI uniquement (pas de connecteur JORF) |

Pas de hash de contenu nulle part : chaque run **réécrit en place** le document sous son
identifiant (voir [idempotence.md](idempotence.md)).

## Les modèles en mémoire (cycle de vie d'un document)

```
RawDocument ──parse──▶ ParsedDocument ──chunk──▶ Chunk ──embed──▶ EmbeddedChunk
   (connecteur)          (+ citations,             (ordinal, text,     (+ embedding,
    payload=arbre XML     metadata, content,        tag_path,           model, dim)
    transcrit)            structure, source_files)  char_start/end)
```

- `ParsedDocument` : `identifier`, `source`, `title`, `content` (texte
  intégral lisible), `structure` (sections/references/context — **jamais persisté**,
  voir plus bas), `metadata` (clés = chemin complet de balise), `citations` (tuple de
  `Citation`), `source_files` (provenance, persistée seulement en dev avec `include_path`).
- `Chunk` : `chunk_id`, `parent_identifier`, `ordinal`, `text`, `tag_path`,
  `char_start`/`char_end` (offsets **littéraux** dans `content`), `metadata`.
- `Relation` : source → cible (deux identifiants), `relation_type` = **verbe validé**
  (chaîne, pas un enum — un verbe non traduit entre sous son nom brut), `metadata`.
- `Citation` : `text` (brut, intégral — la seule donnée non reconstructible), `verb`,
  `sens` (conservé pour orienter l'arête d'une future résolution).

## MongoDB — base de données `MURPHY_DATA`

### `documents`

Un document par `identifier` — index **unique** `uq_identifier`, plus
`idx_source`. Écrit par `replace_one(upsert=True)` : remplacement atomique, aucun
instant où l'identifiant n'existe pas.

Contenu : le dump JSON du `ParsedDocument`, **sauf** :

- `identifier` est remplacé par sa forme sérialisée (la chaîne brute) — c'est elle qui
  est indexée ;
- `source_files` est exclu (provenance d'inspection, chemins absolus du poste
  d'ingestion), sauf en dev avec `include_path` (`parameters.yml`), qui l'écrit aussi
  sur le nœud Neo4j ;
- `structure` est exclue **entièrement** (ADR-022 §4) : `references`/`context` sont de la
  donnée d'arête (elles vivent dans Neo4j), et `sections` est `content` re-découpé — son
  seul apport propre (`path`) survit sur les chunks (`tag_path` + offsets).

Donc : `identifier` (sérialisé), `source`, `title`, `content`, `metadata`,
`citations`.

### `pending_relations`

Les `PendingRelation` : arêtes différées, dont la cible n'est pas (encore) dans le
corpus — source_id, target_id, relation_type, metadata, first_seen_run, last_seen_run.
Ni TTL ni retry_count : écrite une fois, promue une fois — ou jamais.

Index **unique** `uq_pending_source_target_type` (source_id, target_id, relation_type) —
c'est lui qui fait de l'upsert une union ; `idx_pending_target` (target_id) pour le
rejeu ciblé.

Une pendante dérive des documents : elle vit dans leur base et `nuke_all` l'efface avec
eux.

## MongoDB — base méta `MURPHY_META`

Préservée par `nuke_all` : la mémoire de ce qu'on a fait ne doit jamais partir avec les
données.

| Collection | Contenu | Index |
|---|---|---|
| `run_summaries` | Un `RunSummary` par run, à plat : run_id, `sources` (liste), dates, `status` (`ok`/`degraded`/`failed`), `counts`, `unknowns`, et `error_message` sur un run `failed` seulement. | unique (run_id), (started_at) |

## Qdrant

- **Nom de collection** : `QDRANT_COLLECTION` (`.env.dev`), un nom fixe que le backend
  lit aussi. Une seule collection, réécrite en place à chaque run.
- **Vecteurs** : dimension mesurée auprès de TEI au démarrage (768 pour
  `all-mpnet-base-v2`), distance **Cosine** (codée en
  dur dans le dépôt `QdrantVectorRepository`).
- **ID de point** : SHA-256 du `chunk_id`, replié sur 63 bits — stable entre processus
  (jamais `hash()` natif, resemé par interpréteur).
- **Payload** : les `metadata` du chunk à plat, puis les champs du **contrat de
  serving** (ADR-039), posés en dernier pour qu'aucune métadonnée
  homonyme ne les écrase :

  | Champ | Rôle côté serving |
  |---|---|
  | `chunk_id` | identité du passage, envoyée au client |
  | `identifier` | document parent dans `documents` (sérialisé, = clé de suppression par document) |
  | `char_start`, `char_end` | bornes du passage dans le `content` du parent, en **points de code** |
  | `type_document` (métadonnée, facultatif) | nature du document, affichée comme type de la source |

  Le texte du passage n'est **pas** dans le payload : c'est
  `documents.content[char_start:char_end]`. Les autres métadonnées sont présentes mais le
  serving ne s'y appuie pas. Changer un de ces champs impose une réingestion complète.
- **Écriture** : delete-puis-insert par document (`delete_by_document` puis `upsert`) —
  Qdrant n'a pas de « remplace tous les points de ce document » atomique, et un simple
  upsert laisserait des points orphelins quand la nouvelle version a moins de chunks.

## Neo4j

- **Nœuds documents** : identifiés par `identifier` sérialisé. Le `MERGE`
  porte sur le seul identifiant (jamais le label — `MERGE (d:Article {…})` créerait un
  second nœud si le label a changé), puis le label réel est posé. Le label vient du
  préfixe de l'identifiant, d'après la table que chaque source déclare dans le registre
  (`SourceDefinition.node_labels`) : `LEGIARTI` → `Article`, `LEGITEXT` → `Texte`,
  `LEGISCTA` → `Section`, et `Document` (`DEFAULT_LABEL`) pour tout autre préfixe, dont
  les décisions. L'écriture ajoute le label sans retirer l'ancien : après un changement
  de table, un nœud déjà écrit porte les deux, même réingéré ; repartir de zéro demande
  `nuke_all`. Un nœud cité dont le document manque porte `Pending`.
- **Hydratation** (ADR-022 §2) : en prod, nœud **maigre** (`title`, `source`). En dev (et seulement en dev), `parameters.yml` ouvre les vannes : `metadata`
  en props (clés chemin-complet), `include_path` (les fichiers XML source, écrits aussi
  dans Mongo), `include_content_neo4j` (le texte, prop `_text_content`), les citations. Neo4j est l'outil
  d'inspection de la v0.
- **Arêtes** : écrites en phase 2 uniquement, `MERGE (a)-[r:TYPE]->(b)` avec le **verbe
  comme type d'arête** (type paramétré natif), taguées du `run_id` qui les a posées
  (compensabilité à la maille du run). Une cible absente ne crée pas de nœud fantôme :
  la relation part en pendante.
- **Label `Pending`** : la compensation d'un nœud cité par d'autres le dé-hydrate en
  `:Pending` au lieu de l'arracher (les arêtes entrantes appartiennent à d'autres
  documents) ; un `merge_document_node` ultérieur le ré-hydrate naturellement. Plus de
  label `Unknown` : une cible décrite est une `Citation` sur le document, pas un nœud.
