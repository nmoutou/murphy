# Télémétrie et bilan de run

La doctrine tient en une phrase : **rien en silence**. Tout ce qui est vu est compté, tout
ce qui échoue est compté, et le compteur qui compte est lui-même surveillé. Le statut d'un
run se dérive des compteurs — jamais de l'absence d'exception.

Code : `src/ragcore/core/telemetry_events.py` (le vocabulaire),
`src/ragcore/adapters/telemetry/` (les backends), `src/ragcore/core/models/run_stats.py`
et `run_summary.py` (l'agrégat et le bilan).

## Le vocabulaire des événements

Tout événement émis est compté au bilan. `EVENT_TYPES` en donne la liste complète, et
le golden test `tests/golden/test_event_catalog.py` la verrouille : rien n'y entre ni
n'en sort en silence.

| Événement | Sens |
|---|---|
| `document.fetched` | Documents vus par le connecteur (1 événement, `count` = lot). **Le dénominateur** de l'équation. |
| `document.version_skipped` / `document.unreadable` / `document.id_mismatch` / `document.superseded` | Écartés par le connecteur : artefacts d'export (`versions.xml`) / XML illisibles / fichiers dont l'`<ID>` n'est pas le nom (ADR-034 §1) / copies d'une racine écartées par une plus récente (ADR-036 §4). Un compteur par raison, chacun porte son `count`. **Hors équation** : un fichier écarté n'est pas un document vu. |
| `document.parsed` | Parse réussi |
| `document.invalidated` | Rejet au parse : `reason` (une règle métier, `parse_error` ou `collision`, ADR-025), `uid` (chemin source), `error`. Détaillé par raison dans `document.invalidated.<raison>` (voir [Les compteurs par raison](#les-compteurs-par-raison)). |
| `document.persisted` | Saga complète |
| `document.failed` | **La fuite** : vu, jamais ingéré (saga échouée/compensée). `reason` = type d'exception. |
| `chunk.truncated` | Chunks raccourcis par l'embedder pour tenir dans la fenêtre du modèle (1 événement en fin de run, `count`). Pas une fuite — mais la fin de ces chunks n'est pas indexée : `CHUNKING_MAX_CHARS` à corriger. |
| `relation.upserted` | Arêtes **réussies** d'un batch (`count`) |
| `relation.pending` | Source ou cible absente → cache des pendantes |
| `relation.promoted` | Pendante d'un run passé enfin résolue |
| `relation.unknown` | Liens qu'on ne sait pas écrire (`sens` inconnu, `@id` illisible, `typelien` ou balise heuristique qui ne peut pas être un verbe) : 1 événement par document, `count` = liens perdus. L'arête n'existe pas ; un lien retiré par `skip_unconfigured` n'est pas compté. Ne change pas le statut du run (ADR-024). |
| `saga.compensation.triggered` / `.completed` / `.failed` | Rollback d'une saga (`.failed` = un écrit partiel subsiste ; `success` du `.completed` dit la vérité : une seule compensation ratée et le rollback n'est pas propre) |

**Contrat de cardinalité** : la plupart des événements pèsent 1. Huit — et eux
exactement (`COUNT_CARRYING_EVENTS`) — portent leur poids dans `payload["count"]` :
`document.fetched`, `document.version_skipped`, `document.unreadable`,
`document.id_mismatch`, `document.superseded`,
`relation.upserted`, `relation.unknown`, `chunk.truncated`.
L'ensemble est nommé et verrouillé par golden : un émetteur qui prétend porter une cardinalité sans y figurer est
un bug visible, pas une dérive muette.

## Les backends

Assemblés par `adapters/telemetry/factory.py:assemble_telemetry` dans une
`WorkerTelemetryStack` (`worker_stack.py`) :

1. **Console** (`console_log.py`) — les logs textuels (`telemetry.log`) ; elle ne reçoit
   aucun événement.
2. **Agrégateur** (`aggregator.py:RunStatsAggregator`) — reçoit chaque événement ; les
   compteurs dont le bilan sortira.
3. **Mesures** (`measures.py:MeasuresAggregator`) — reçoit les `record_measure` ; les
   distributions dont `statistics` sortira. Il ne reçoit aucun événement.

Il n'y a pas de trace événement par événement : le bilan ne garde que des compteurs.
Le détail d'un échec (quel document, quelle erreur) est dans les logs console — un
`logger` dédié pour `document.failed`, `document.invalidated` et les compensations
ratées. Brancher un outil d'observabilité, c'est ajouter un backend à `WorkerBackends`
et le livrer dans `WorkerTelemetryStack.emit`.

**Un stack par worker.** Les workers de la phase 1 ne partagent pas la pile du hook :
`WorkerTelemetryFactory` construit la sienne pour chacun. Chaque worker tient son
`RunStats` local.

## `RunStats` — l'agrégat mergeable

Un **monoïde de fusion** : élément neutre `empty()`, opérateur `merge` associatif **et
commutatif** (les workers finissent dans un ordre non déterministe — une fusion non
commutative ferait dépendre le bilan de l'ordonnancement). Deux champs :

- `counts` : event_type, ou compteur par raison (ci-dessous) → occurrences (fusion :
  somme). ⚠️ Dette ouverte : pas de
  compteurs par **source**, un run multi-sources rend un bilan où l'échec est anonyme
  quant à sa provenance ;
- `unknowns` : catégorie → mot que le run n'a pas su nommer → `{count, example}`.
  `count` est un nombre de **documents** (un document déclare un mot une fois) ;
  `example` (`identifier`, `source_file`) est un document qui le porte. Fusion : somme
  des comptes, **plus petit** exemple — « le premier vu » dépendrait de l'ordre des
  workers. `source_file` est le fichier de la facette pour les inconnus de parse, le
  premier fichier du document pour ceux d'extraction.
  Trois catégories plates (ADR-024) :
  - `tags` : les métadonnées non configurées (balise absente de la table ou sans
    renommage, ADR-023), sous leur **clé chemin-complet** — la clé même qu'elles ont
    dans `metadata` ;
  - `roots` : les racines XML que la source ne déclare pas ;
  - `links` : les types de lien non configurés — un `typelien` non traduit, ou la clé
    chemin-complet d'une balise absente de la table dont la valeur est un identifiant
    DILA (lien heuristique).

  Une balise sans valeur n'y apparaît pas : elle n'a rien à ingérer. Un lien qu'on ne
  sait pas écrire n'est pas un type de lien : il est compté par `relation.unknown`.

**La remontée passe par le DAG, pas par le hook** : le nœud `ingest` remet les agrégats
des workers (compteurs et mesures) aux `RunAggregates` du run (`run_sink`, que le hook
clôt) — Kedro libère un `MemoryDataset` dès son dernier lecteur, un `catalog.load()`
d'après-run tomberait sur du vide. Chaque worker dépose les siens en sortant, dans un
`finally` : un run qui casse, en phase 1 comme plus loin, les garde. La phase 2 n'est pas
poussée (elle a tourné sur la télémétrie du hook, ses compteurs y sont déjà — les pousser
les compterait deux fois).

### Les compteurs par raison

Deux familles de clés de `counts` ne sont pas des événements : elles comptent par raison
ce que `MURPHY_PROBLEMS` détaille (ADR-036 §1). Leurs clés sont formées par
`telemetry_events.py` (`collision_count_key`, `invalidation_count_key`), et figées par le
test golden : les bilans de `MURPHY_META` se comparent d'un run à l'autre par elles.

- `collision.<raison>` : nombre de (document, clé) en collision (`record_collision`).
  Ce n'est pas un inconnu : la table sait nommer ce qui entre en collision. Les raisons
  sont celles de `collision_reasons.py`. Hors équation de complétude. Le détail vit dans
  `MURPHY_PROBLEMS.collisions` (voir [Les problèmes d'un run](#les-problèmes-dun-run)).
- `document.invalidated.<raison>` : nombre de documents rejetés au parse
  (`record_invalidation`, un appel par `document.invalidated`). Ils détaillent
  `document.invalidated` : leur somme vaut ce total et ne s'y ajoute pas, donc on
  n'additionne jamais tout `counts`. Les raisons sont celles de `exclusion_reasons.py` :
  `identifier_missing`, `identifier_malformed`, `undeclared_prefix`,
  `facet_root_duplicated`, `facet_root_undeclared`, `collision`, `parse_error`. Le détail
  vit dans `MURPHY_PROBLEMS.invalidated`.

## Le statut d'un run

`RunSummary` = l'identité du run (run_id, `sources`, dates) + les `counts` et les
`unknowns` de l'agrégat, recopiés à plat + le `status` + la part du
corpus lue : par source, `sampling` (`{ratio, total, retained}`, de la passe 1 ; vide si
le run a cassé avant elle, et sans les sources écartées à `0`, qui ne sont pas du run). Un run `ok` à 10 % ne doit pas passer pour
un run complet (ADR-034 §9). Le statut annoncé « ok » par le hook est **re-dérivé des compteurs**
(`_status_from`) — deux propriétés :

1. **Complet ?** `fetched == persisted + invalidated + failed` — **l'équation de
   complétude**. Si elle ne tombe pas juste (dans les deux sens : un excédent est un
   double comptage), des documents ont disparu sans que rien ne les compte.
2. **Sans perte ?** `failed == 0`. Un document échoué est déclaré et rejouable — mais pas
   ingéré.

| Statut | Sens |
|---|---|
| `ok` | Tout ce qui a été vu a été ingéré ou écarté sciemment. |
| `degraded` | Le run est allé au bout mais ne peut pas se déclarer complet (une des trois propriétés a cassé). |
| `failed` | Le pipeline a levé ; rien ne garantit l'état des stores. Si la casse précède la phase 1, le bilan est pauvre — le statut reste vrai. |

Le référentiel est `document.fetched`, jamais `document.parsed` (un invalidé n'est pas
parsé — le prendre pour total exclurait du dénominateur ceux qu'il faut compter). Et le
critère ne nomme aucune cause : l'ancienne version ne regardait que les compensations de
saga et a laissé passer « ok » un run qui avait perdu 98 documents à l'embedding, avant
toute saga. L'équation attrape toutes les causes, y compris celles qu'on n'a pas encore
rencontrées.

Persistance du bilan : upsert Mongo (`run_summaries`, unique par run_id). Le
document est plat :

```json
{ "run_id": "…", "sources": ["cass", "jade", "legi"], "status": "ok",
  "started_at": "…", "ended_at": "…",
  "counts": { "document.fetched": 1121, "document.invalidated": 4,
    "document.invalidated.facet_root_duplicated": 3,
    "document.invalidated.parse_error": 1,
    "collision.metadata": 14, "collision.facet_root_duplicated": 3, … },
  "unknowns": {
    "tags": { "textelr_meta_meta_spec_meta_texte_chronicle_num_sequence": { "count": 92,
      "example": { "identifier": "LEGITEXT…", "source_file": "/…/LEGITEXT….xml" } } },
    "roots": {},
    "links": { "ZORGLUB": { "count": 1, "example": { … } } } },
  "sampling": { "legi": { "total": 2116313, "retained": 211632, "ratio": 0.1 } } }
```

`sources` est toujours une liste, même pour un run mono-source. `error_message` n'est
écrit que sur un run `failed` : un `degraded` n'a pas d'exception, il se lit dans les
compteurs.

## Les problèmes d'un run

`MURPHY_PROBLEMS` détaille ce que le bilan compte (ADR-036) : une ligne Mongo par
problème, sous le `run_id` du run qui l'a rencontré, écrite à la clôture de la session,
**même en cas d'échec**, par lots de 1 000 (`MongoProblemRepository.insert_run`). Les
runs successifs s'accumulent ; `nuke_all` vide la base. Le détail s'accumule dans le
`ProblemsAggregator` du hook : lecture et parse tournent dans le thread du nœud
`ingest`, jamais dans un worker.

### `collisions`

Ce que les compteurs `collision.<raison>` comptent, une ligne par (document, clé),
document refusé compris :

```json
{ "run_id": "…", "source": "legi", "reason": "facet_root_duplicated",
  "identifier": "LEGIARTI…", "key": "ARTICLE",
  "files": ["/…/TNC_en_vigueur/…/LEGIARTI….xml", "/…/TNC_non_vigueur/…/LEGIARTI….xml"] }
```

Ni les valeurs en conflit, ni les dates des fichiers : la clé et les chemins suffisent à
retrouver la collision. Index `(run_id, source, reason)` et `(identifier)`. Les raisons
sont celles de `collision_reasons.py` :

| Raison | `key` | `files` |
|---|---|---|
| `metadata` | La clé de métadonnée qui a reçu plusieurs valeurs distinctes (ADR-025), rangée en liste ou refusée (`document.invalidated.collision`) | Les fichiers d'où viennent les valeurs, distincts, dans l'ordre des facettes |
| `duplicate_copy` | La racine XML portée par plusieurs copies identiques ; le connecteur n'en garde qu'une | La copie gardée (la plus récente), puis les autres |
| `facet_root_duplicated` | La racine XML portée par des copies différentes de même date, que le connecteur n'a pas su départager ; le document est aussi rejeté (`document.invalidated.facet_root_duplicated`) | Les seuls fichiers de cette racine |

Les copies départagées par le connecteur (`connector.collisions`) sont déclarées en fin
de flux, avec ses écarts (`SourceReading.declare_counts`) : leur document est émis,
elles ne touchent pas l'équation de complétude.

### `superseded`

Une ligne par copie qu'écarte l'arbitrage du connecteur (ADR-034 §1) : une racine qui a
trois copies anciennes en donne trois. Ce n'est pas une collision : l'arbitrage a
tranché. Comptée `document.superseded`, hors équation de complétude comme un fichier
écarté.

```json
{ "run_id": "…", "source": "legi", "identifier": "LEGIARTI…", "root": "ARTICLE",
  "kept":      { "path": "/…/TNC_non_vigueur/…/LEGIARTI….xml", "mtime": ISODate("…") },
  "discarded": { "path": "/…/TNC_en_vigueur/…/LEGIARTI….xml",  "mtime": ISODate("…") } }
```

`mtime` est une date Mongo, à la milliseconde : l'arbitrage a comparé les nanosecondes
avant l'écriture, la ligne sert à lire et à dater (ADR-035). Index `(run_id, source)` et
`(identifier)`.

### `unreadable` et `mismatch`

Une ligne par fichier que le connecteur écarte avant le parser, comptée
`document.unreadable` ou `document.id_mismatch`. Index `(run_id, source)`.

```json
{ "run_id": "…", "source": "legi", "key": "LEGIARTI…", "path": "/…/LEGIARTI….xml",
  "error": "no element found: line 12, column 0" }
{ "run_id": "…", "source": "legi", "key": "versions", "path": "/…/versions.xml",
  "found_id": "LEGIARTI…" }
```

`key` est le nom du fichier sans extension ; `error` le message du parseur XML ;
`found_id` l'`<ID>` lu dans le fichier, `null` s'il n'en a pas. Les artefacts d'export
(`document.version_skipped`) ne sont que comptés : la DILA en livre un par texte, et leur
chemin n'apprend rien.

### `invalidated`

Une ligne par document rejeté au parse, ce que les compteurs
`document.invalidated.<raison>` comptent :

```json
{ "run_id": "…", "source": "legi", "identifier": "LEGIARTI…",
  "reason": "facet_root_duplicated", "error": "…",
  "files": ["/…/TNC_en_vigueur/…/LEGIARTI….xml", "/…/TNC_non_vigueur/…/LEGIARTI….xml"] }
```

`identifier` est la clé du document dans le flux (un document rejeté n'a pas
d'identifiant analysé), `error` le message que porte déjà l'événement
`document.invalidated`, `files` les fichiers du document. Un rejet `collision` ou
`facet_root_duplicated` a aussi ses lignes dans `collisions` : celle-ci dit que le
document est refusé, celles-là sur quoi ; elles se relient par `identifier`. Index
`(run_id, source, reason)` et `(identifier)`.

## Les statistiques d'un run

`MURPHY_META.statistics` mesure ce que le bilan compte (ADR-034 §8) : un document par
run, unique par `run_id`, écrit à la clôture de la session, **même en cas d'échec**.

| | `run_summaries` | `statistics` |
|---|---|---|
| Question | Le run a-t-il tout fait, et sinon, quoi ? | Combien ça pèse, combien de temps ça prend ? |
| Contenu | Une comptabilité : ce qui est arrivé aux objets | Des mesures : tailles et durées, en distributions |
| Usage | Le statut du run s'en dérive | Le diagnostic et le réglage ; jamais lue pour décider |

Toute mesure est une `Distribution` (`core/models/distribution.py`) :
`{count, sum, min, max, mean, max_ref}`. `max_ref` nomme ce qui a donné le
maximum (un identifiant de document).
Comme `RunStats`, les mesures (`RunMeasures`) se fusionnent dans n'importe quel ordre :
à maximum égal, `max_ref` est la plus petite référence.

Le vocabulaire est `core/statistics_measures.py` :

```json
{ "run_id": "…", "started_at": ISODate("…"),
  "stages_s": { "discovery": 95.2, "phase1": 812.4, "components": 12.0,
                "phase2_write": 41.0 },
  "queues": { "producer_blocked_s": {…}, "worker_idle_s": {…} },
  "components": { "nodes": {…}, "relations": {…} },
  "documents": {
    "legi": {
      "xml_bytes": {…}, "facets": {…}, "content_chars": {…}, "chunks": {…},
      "relations": {…},
      "step_ms": { "read": {…}, "parse": {…}, "embed": {…}, "mongo": {…},
                   "opensearch": {…}, "neo4j": {…} } } } }
```

- `stages_s` : la durée de chaque étape, en secondes (`StageClock`, une étape mesurée
  plusieurs fois s'additionne). `discovery` est la passe 1 des connecteurs ; `phase1`
  couvre leur passe 2, le parse et le pool de `ingest` ; `components`, la passe de la
  phase 2 qui trouve les composantes connexes ; `phase2_write`, le reste de
  `resolveRelations`.
- `components` : une valeur par composante connexe de la contenance (ADR-034 §5), en
  nœuds et en relations lues. `components.nodes.count` est leur nombre, et `max_ref`
  nomme la plus grande (par son plus petit nœud) : elle borne la mémoire de la phase 2.
- `queues` : les attentes devant la file de la phase 1, en secondes.
  `producer_blocked_s`, une par document déposé : une lecture souvent bloquée désigne
  les workers ; `worker_idle_s`, une par document pris (et une par fin de flux) : des
  workers souvent inactifs désignent la lecture.
- `documents.<source>` : par document, sa taille XML (facettes sommées), son nombre de
  facettes, de caractères, de chunks et de relations, et la durée de chaque étape en
  millisecondes. `mongo` additionne l'écriture du document et celle de ses relations non
  formatées. `embed` est absent quand l'embedding est coupé (ADR-012).

Une section n'apparaît que si une mesure l'a remplie.
