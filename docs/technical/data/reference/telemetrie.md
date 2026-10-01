# Télémétrie et bilan de run

La doctrine tient en une phrase : **rien en silence**. Tout ce qui est vu est compté, tout
ce qui échoue est compté, et le compteur qui compte est lui-même surveillé. Le statut d'un
run se dérive des compteurs — jamais de l'absence d'exception.

Code : `src/ragcore/core/telemetry_events.py` (le catalogue),
`src/ragcore/adapters/telemetry/` (les backends), `src/ragcore/core/models/run_stats.py`
et `run_summary.py` (l'agrégat et le bilan).

## Le catalogue d'événements — source de vérité unique

Chaque `event_type` déclare son comportement dans `EVENT_CATALOG` (`EventBehavior`) :
niveau de log, et routage vers chacun des deux backends. Le golden test
`tests/golden/test_event_catalog.py` verrouille le catalogue : rien n'y entre ni n'en
sort en silence.

| Événement | Sens | Agrégat |
|---|---|---|
| `pipeline.run.started` / `.completed` / `.failed` | Cycle de vie du run. Hors agrégat : le bilan le dit déjà par `started_at`, `ended_at` et `status`. | — |
| `document.fetched` | Documents vus par le connecteur (1 événement, `count` = lot). **Le dénominateur** de l'équation. | ✓ |
| `document.version_skipped` / `document.unreadable` | Écartés par le connecteur : artefacts d'export (`versions.xml`) / XML illisibles. Un compteur par raison, chacun porte son `count`. **Hors équation** : un fichier écarté n'est pas un document vu. | ✓ |
| `document.parsed` | Parse réussi | ✓ |
| `document.invalidated` | Rejet au parse (validation ou lecture) : `reason`, `uid` (chemin source), `error` | ✓ |
| `document.persisted` | Saga complète | ✓ |
| `document.failed` | **La fuite** : vu, jamais ingéré (saga échouée/compensée). `reason` = type d'exception. | ✓ |
| `chunk.truncated` | Chunks raccourcis par l'embedder pour tenir dans la fenêtre du modèle (1 événement en fin de run, `count`). Pas une fuite — mais la fin de ces chunks n'est pas indexée : `CHUNKING_MAX_CHARS` à corriger. | ✓ |
| `relation.upserted` | Arêtes **réussies** d'un batch (`count`) | ✓ |
| `relation.pending` | Cible absente → cache des pendantes | ✓ |
| `relation.promoted` | Pendante d'un run passé enfin résolue | ✓ |
| `saga.compensation.triggered` / `.completed` / `.failed` | Rollback d'une saga (`.failed` = un écrit partiel subsiste ; `success` du `.completed` dit la vérité : une seule compensation ratée et le rollback n'est pas propre) | ✓ |
| `maintenance.nuke_all.executed` | Maintenance | — |

**Contrat de cardinalité** : la plupart des événements pèsent 1. Cinq — et eux
exactement (`COUNT_CARRYING_EVENTS`) — portent leur poids dans `payload["count"]` :
`document.fetched`, `document.version_skipped`, `document.unreadable`,
`relation.upserted`, `chunk.truncated`.
L'ensemble est nommé et verrouillé par golden : un émetteur qui prétend porter une cardinalité sans y figurer est
un bug visible, pas une dérive muette.

## Les backends

Assemblés par le hook (`adapters/telemetry/factory.py:assemble_telemetry`), routés par le
registre :

1. **Console** (`console_log.py`) — les logs textuels (`telemetry.log`). ⚠️ Son `emit`
   ne fait rien : la colonne `log` du catalogue n'affiche aucun événement.
2. **Agrégateur** (`aggregator.py:RunStatsAggregator`) — les compteurs dont le bilan
   sortira.

Il n'y a pas de trace événement par événement : le bilan ne garde que des compteurs.
Le détail d'un échec (quel document, quelle erreur) est dans les logs console — un
`logger` dédié pour `document.failed`, `document.invalidated` et les compensations
ratées. Brancher un outil d'observabilité, c'est ajouter un backend à `WorkerBackends`
et une colonne de routage à `EventBehavior`.

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
- `unknowns` : catégorie → vocabulaire que le run n'a pas su nommer (ensemble dédupliqué,
  pas un compteur : « la balise foo est inconnue » est vraie une fois pour toutes).
  Catégories : `tag.unconfigured` / `racine` (parse), `typelien` / `sens` /
  `identifiant` (extraction). Vide = la table de rôles a tout couvert.

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

Persistance du bilan : upsert Mongo (`meta_run_summaries`, unique par run_id). Le
document est plat :

```json
{ "run_id": "…", "sources": ["cass", "jade", "legi"], "status": "ok",
  "started_at": "…", "ended_at": "…", "counts": { "document.fetched": 1121, … },
  "unknowns": {} }
```

`sources` est toujours une liste, même pour un run mono-source. `error_message` n'est
écrit que sur un run `failed` : un `degraded` n'a pas d'exception, il se lit dans les
compteurs.
