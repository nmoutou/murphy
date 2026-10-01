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
| `document.version_skipped` / `document.unreadable` | Écartés par le connecteur : artefacts d'export (`versions.xml`) / XML illisibles. Un compteur par raison, chacun porte son `count`. **Hors équation** : un fichier écarté n'est pas un document vu. |
| `document.parsed` | Parse réussi |
| `document.invalidated` | Rejet au parse (validation ou lecture) : `reason`, `uid` (chemin source), `error` |
| `document.persisted` | Saga complète |
| `document.failed` | **La fuite** : vu, jamais ingéré (saga échouée/compensée). `reason` = type d'exception. |
| `chunk.truncated` | Chunks raccourcis par l'embedder pour tenir dans la fenêtre du modèle (1 événement en fin de run, `count`). Pas une fuite — mais la fin de ces chunks n'est pas indexée : `CHUNKING_MAX_CHARS` à corriger. |
| `relation.upserted` | Arêtes **réussies** d'un batch (`count`) |
| `relation.pending` | Cible absente → cache des pendantes |
| `relation.promoted` | Pendante d'un run passé enfin résolue |
| `relation.unknown` | Liens qu'on ne sait pas écrire (`sens` inconnu, `@id` illisible, `typelien` qui ne peut pas être un verbe) : 1 événement par document, `count` = liens perdus. L'arête n'existe pas ; un lien retiré par `skip_unconfigured` n'est pas compté. Ne change pas le statut du run (ADR-048). |
| `saga.compensation.triggered` / `.completed` / `.failed` | Rollback d'une saga (`.failed` = un écrit partiel subsiste ; `success` du `.completed` dit la vérité : une seule compensation ratée et le rollback n'est pas propre) |

**Contrat de cardinalité** : la plupart des événements pèsent 1. Six — et eux
exactement (`COUNT_CARRYING_EVENTS`) — portent leur poids dans `payload["count"]` :
`document.fetched`, `document.version_skipped`, `document.unreadable`,
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

- `counts` : event_type → occurrences (fusion : somme). ⚠️ Dette ouverte : pas de
  compteurs par **source**, un run multi-sources rend un bilan où l'échec est anonyme
  quant à sa provenance ;
- `unknowns` : catégorie → mot que le run n'a pas su nommer → `{count, example}`.
  `count` est un nombre de **documents** (un document déclare un mot une fois) ;
  `example` (`identifier`, `source_file`) est un document qui le porte. Fusion : somme
  des comptes, **plus petit** exemple — « le premier vu » dépendrait de l'ordre des
  workers. `source_file` est le fichier de la facette pour les inconnus de parse, le
  premier fichier du document pour ceux d'extraction.
  Trois catégories plates (ADR-048) :
  - `tags` : les métadonnées non configurées (balise absente de la table ou sans
    renommage, ADR-047), sous leur **clé chemin-complet** — la clé même qu'elles ont
    dans `metadata` ;
  - `roots` : les racines XML que la source ne déclare pas ;
  - `links` : les types de lien non configurés — un `typelien` non traduit, ou la clé
    chemin-complet d'une balise absente de la table dont la valeur est un identifiant
    DILA (lien heuristique).

  Une balise sans valeur n'y apparaît pas : elle n'a rien à ingérer. Un lien qu'on ne
  sait pas écrire n'est pas un type de lien : il est compté par `relation.unknown`.

**La remontée passe par le DAG, pas par le hook** : le node terminal `report` pousse
`ingestion_outcome.stats` dans l'agrégat du run (`run_stats_sink`, que le hook finalise) — Kedro libère un `MemoryDataset` dès
son dernier lecteur, un `catalog.load()` d'après-run tomberait sur du vide. La phase 2
n'est pas poussée (elle a tourné sur la télémétrie du hook, ses compteurs y sont déjà —
les pousser les compterait deux fois).

## Le statut d'un run

`RunSummary` = l'identité du run (run_id, `sources`, dates) + les `counts` et les
`unknowns` de l'agrégat, recopiés à plat + le `status`. Le statut annoncé « ok » par le hook est **re-dérivé des compteurs**
(`_status_from`) — deux propriétés :

1. **Complet ?** `fetched == persisted + invalidated + failed` — **l'équation de
   complétude**. Si elle ne tombe pas juste (dans les deux sens : un excédent est un
   double comptage), des documents ont disparu sans que rien ne les compte.
2. **Sans perte ?** `failed == 0`. Un document échoué est déclaré et rejouable — mais pas
   ingéré.

| Statut | Sens |
|---|---|
| `ok` | Tout ce qui a été vu a été ingéré ou écarté sciemment. |
| `degraded` | Le run est allé au bout mais ne peut pas se déclarer complet (une des deux propriétés a cassé). |
| `failed` | Le pipeline a levé ; rien ne garantit l'état des stores. Si la casse précède le node `report`, le bilan est pauvre (les stats des workers ne remontent que par lui) — le statut reste vrai. |

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
  "started_at": "…", "ended_at": "…", "counts": { "document.fetched": 1121, … },
  "unknowns": {
    "tags": { "textelr_meta_meta_spec_meta_texte_chronicle_num_sequence": { "count": 92,
      "example": { "identifier": "LEGITEXT…", "source_file": "/…/LEGITEXT….xml" } } },
    "roots": {},
    "links": { "ZORGLUB": { "count": 1, "example": { … } } } } }
```

`sources` est toujours une liste, même pour un run mono-source. `error_message` n'est
écrit que sur un run `failed` : un `degraded` n'a pas d'exception, il se lit dans les
compteurs.
