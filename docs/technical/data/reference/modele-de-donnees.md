# Le modèle de données

Ce que le pipeline écrit réellement, base par base. Modèles Pydantic :
`src/ragcore/core/models/` (tous `frozen=True`). Dépôts : `src/ragcore/adapters/storage/`.

## L'identité d'un document

Un seul `identifier` (le type `Identifier`) nomme le document partout : clé Mongo,
payload Qdrant, nœud Neo4j, événements de télémétrie. Sa forme sérialisée est la valeur brute
de la DILA, sans rien ajouter : `LEGIARTI000006419264`.

Le format est validé à la construction (`^[A-Z]{8}[0-9]{12}$`) pour toutes les sources.
Les 8 lettres de tête (`Identifier.prefix`) disent le fonds et le type du document
(`document_type`, ADR-046), que la table de rôles de la source déclare
(`RoleTable.document_types`) :

| Préfixe | Source | `document_type` |
|---|---|---|
| `LEGIARTI` / `LEGITEXT` / `LEGISCTA` | LEGI | `article`, `texte`, `section` |
| `JURITEXT` / `CETATEXT` / `CONSTEXT` | les 5 juri | `decision` (judiciaire, administrative, constitutionnelle : `source` les distingue) |
| `JORFTEXT` / `JORFARTI` | — | cible de liens LEGI uniquement (pas de connecteur JORF) |

Un préfixe que la table ne déclare pas refuse le document (`ValidationError`). La nature
juridique (`LOI`, `ARRET`, `QPC`…) est un autre champ, `nature` : la balise `NATURE` en
majuscules, `None` si elle manque ou n'apporte rien (`Article` en LEGI, `Texte` dans
JADE).

Pas de hash de contenu nulle part : chaque run **réécrit en place** le document sous son
identifiant (voir [idempotence.md](idempotence.md)).

## Les modèles en mémoire (cycle de vie d'un document)

```
RawDocument ──parse──▶ ParsedDocument ──chunk──▶ Chunk ──embed──▶ EmbeddedChunk
   (connecteur)          (metadata, content,       (ordinal, text,     (+ embedding,
    payload=arbre XML     structure,                tag_path,           model, dim)
    transcrit)            source_files)             char_start/end)
```

- `ParsedDocument` : `identifier`, `source`, `document_type`, `nature`, `title`, `content` (texte
  intégral lisible), `structure` (sections/references/context — **jamais persisté**,
  voir plus bas), `metadata` (clés = chemin complet de balise), `source_files`
  (provenance, persistée seulement en dev avec `include_path`).
- `Chunk` : `chunk_id`, `parent_identifier`, `ordinal`, `text`, `tag_path`,
  `char_start`/`char_end` (offsets **littéraux** dans `content`), `metadata`.
- `Relation` : source → cible (deux identifiants), `relation_type` = **verbe validé**
  (chaîne, pas un enum — un verbe non traduit entre sous son nom brut), `metadata`.
- `UnformattedRelation` (ADR-045) : la relation d'un lien à `@id` vide —
  `source_identifier`, `target_text` (brut, intégral — la seule donnée non
  reconstructible), `relation_type` (traduit, brut sinon ; pas un verbe validé, il ne
  devient pas un type d'arête), `sens` (conservé pour orienter l'arête d'une future
  résolution), `source`. Extraite avec les relations, elle n'est pas portée
  par le document.

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

Donc : `identifier` (sérialisé), `source`, `document_type`, `nature`, `title`, `content`,
`metadata`.

### `pending_relations`

Les `PendingRelation` : arêtes différées, dont la cible n'est pas (encore) dans le
corpus — source_id, target_id, relation_type, metadata, first_seen_run, last_seen_run.
Ni TTL ni retry_count : écrite une fois, promue une fois — ou jamais.

Index **unique** `uq_pending_source_target_type` (source_id, target_id, relation_type) —
c'est lui qui fait de l'upsert une union ; `idx_pending_target` (target_id) pour le
rejeu ciblé.

Une pendante dérive des documents : elle vit dans leur base et `nuke_all` l'efface avec
eux.

### `unformatted_relations`

Les `UnformattedRelation` (ADR-045) : les relations d'un lien à `@id` vide, dont la cible
est décrite en toutes lettres (« code de l'environnement ») au lieu d'être identifiée —
source_id, target_text, relation_type, sens, source, first_seen_run, last_seen_run.
Écrites par la saga du document (étape `mongo_unformatted_upsert`, juste après
`mongo_upsert`), elles **s'accumulent** comme les pendantes : rien n'est supprimé
d'un run à l'autre, seul `last_seen_run` avance. La compensation de la saga ne retire que
les lignes du document nées dans le run qui échoue.

Index **unique** `uq_unformatted_source_text_type_sens` (source_id, target_text,
relation_type, sens) — l'union de l'upsert ; `sens` en fait partie, car « je cite X » et
« X me cite » sont deux faits. Son préfixe `source_id` sert aussi la compensation.

Comme les pendantes, elles dérivent des documents et `nuke_all` les efface avec eux.

## MongoDB — base méta `MURPHY_META`

Préservée par `nuke_all` : la mémoire de ce qu'on a fait ne doit jamais partir avec les
données.

| Collection | Contenu | Index |
|---|---|---|
| `run_summaries` | Un `RunSummary` par run, à plat : run_id, `sources` (liste), dates, `status` (`ok`/`degraded`/`failed`), `counts`, `unknowns` (`tags` / `roots` / `links` / `collisions` → clé → `{count, example: {identifier, source_file}}`, ADR-048, ADR-049), et `error_message` sur un run `failed` seulement. | unique (run_id), (started_at) |

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
  | `document_type` | type du document (`article`, `section`, `texte`, `decision`), affiché comme type de la source |
  | `nature` | nature juridique ou `null`, affichée après le type |

  Le texte du passage n'est **pas** dans le payload : c'est
  `documents.content[char_start:char_end]`. Les autres métadonnées sont présentes mais le
  serving ne s'y appuie pas. Changer un de ces champs impose une réingestion complète.
- **Écriture** : delete-puis-insert par document (`delete_by_document` puis `upsert`) —
  Qdrant n'a pas de « remplace tous les points de ce document » atomique, et un simple
  upsert laisserait des points orphelins quand la nouvelle version a moins de chunks.

## Neo4j

- **Nœuds documents** (ADR-046) : identifiés par `identifier` sérialisé. Chaque nœud
  porte deux labels : `Document`, et celui de son `document_type` (`TYPE_LABELS` :
  `Article`, `Section`, `Texte`, `Decision`). Une contrainte d'unicité,
  `document_identifier`, porte sur `(:Document).identifier` ; elle est posée avec les
  index Mongo (`schema.ensure_graph_constraints`), et `nuke_all` la laisse en place. Le
  `MERGE` et tous les `MATCH` par identifiant passent par `Document`, donc par son index.
  Le label de type ne change jamais pour un identifiant : il vient du préfixe.
- **Hydratation** (ADR-022 §2) : en prod, nœud **maigre** (`title`, `source`). En dev (et seulement en dev), `parameters.yml` ouvre les vannes : `metadata`
  en props (clés chemin-complet), `include_path` (les fichiers XML source, écrits aussi
  dans Mongo), `include_content_neo4j` (le texte, prop `_text_content`). Neo4j est l'outil
  d'inspection de la v0.
- **Arêtes** : écrites en phase 2 uniquement, `MERGE (a)-[r:TYPE]->(b)` avec le **verbe
  comme type d'arête** (type paramétré natif), taguées du `run_id` qui les a posées
  (compensabilité à la maille du run). Une cible absente ne crée pas de nœud fantôme :
  la relation part en pendante. Une cible décrite est une ligne
  d'`unformatted_relations`, pas un nœud.
