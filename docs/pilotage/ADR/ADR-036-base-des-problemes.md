# ADR-036 — `MURPHY_PROBLEMS` : une base des problèmes d'ingestion, une ligne par problème

**Statut** : Proposé (15 octobre 2026) — amende ADR-034 §8 (l'amendement
`MURPHY_META.collisions`), ADR-021 §1 (la base de `unformatted_relations`) et les
conséquences d'ADR-035 (une copie écartée n'est plus une collision)

## Contexte

Un run d'ingestion rencontre six sortes de problèmes. Pour quatre d'entre elles, le
détail est aujourd'hui inexploitable ou perdu :

| Problème | Stockage actuel | Ce qui manque |
|---|---|---|
| Collisions (`metadata`, `duplicate_copy`, `facet_root_duplicated`) | `MURPHY_META.collisions` : un document par source et par run, les détails groupés par raison, découpé en parties au-delà de 15 Mio | Une requête sur une collision doit dérouler des tableaux imbriqués, sur plusieurs parties |
| Copies écartées par l'arbitrage (`superseded_copy`) | Une raison parmi les collisions, un enregistrement par racine pour toutes ses copies écartées | La date de chaque copie, dont ADR-035 §3 a besoin |
| Fichiers illisibles (`unreadable`) | Un compteur | Le chemin et l'erreur, que `read_root` avale |
| Fichiers dont l'`<ID>` n'est pas le nom (`id_mismatch`) | Un compteur, et une ligne de log | Le chemin et l'`<ID>` trouvé |
| Documents rejetés au parse (`document.invalidated`) | Un compte par raison, et une ligne de log | L'identifiant, l'erreur, les fichiers |
| Relations non formatées (ADR-021) | `MURPHY_DATA.unformatted_relations`, une ligne par relation | Rien : seule la base change |

Les logs ne remplacent pas une collection : ils ne se requêtent pas, et un run complet en
produit trop pour qu'on y retrouve un fichier.

Les artefacts d'export (`versions.xml` de LEGI, `export_artifact`) ne sont pas des
problèmes : la DILA en livre un par texte, et leur chemin n'apprend rien.

## Décision

**1. Une base `MURPHY_PROBLEMS`.** Elle est nommée par `MONGODB_PROBLEMS_DB_NAME`
(`.env.dev`), comme les deux autres bases. Elle tient le détail des problèmes ;
`run_summaries` en garde les comptes, et le statut du run ne change pas de règle.

**2. Une ligne par problème.** Chaque document Mongo décrit un seul problème, et porte le
`run_id` du run qui l'a rencontré (sauf `unformatted_relations`, §8). Les chemins sont
absolus. Plus aucun document ne regroupe des détails : la limite de 16 Mo d'un document
Mongo ne concerne plus que la ligne elle-même, et le découpage en parties disparaît.

**3. `collisions`.** Une ligne par collision. `superseded_copy` n'en est plus une raison
(§4).

```
{ run_id, source, reason, identifier, key, files }
```

- `reason` : `metadata` (ADR-025), `duplicate_copy` ou `facet_root_duplicated`.
- `key` : la clé de métadonnée, ou la racine XML en double.
- `files` : les fichiers en cause, distincts.
- Index : `(run_id, source, reason)`, `(identifier)`.

Un rejet `facet_root_duplicated` ou `collision` donne aussi une ligne d'`invalidated`
(§7) : celle-ci dit que le document est refusé, les lignes de `collisions` disent sur
quoi. Elles se relient par `identifier`.

**4. `superseded`.** Une ligne par copie écartée par l'arbitrage (ADR-034 §1) : une
racine qui a trois copies anciennes en donne trois.

```
{ run_id, source, identifier, root,
  kept:      { path, mtime },
  discarded: { path, mtime } }
```

- `mtime` est une date Mongo, à la milliseconde. L'arbitrage compare les mtimes en
  nanosecondes avant l'écriture ; la ligne sert à lire et à dater, pas à départager.
- Index : `(run_id, source)`, `(identifier)`.

Une copie écartée n'est plus comptée comme collision. Elle est comptée dans
`run_summaries.counts["document.superseded"]`, hors de l'équation de complétude : comme
un fichier écarté, elle n'est pas un document vu.

**5. `unreadable`.** Une ligne par fichier dont le XML est illisible (tronqué, encodage
cassé).

```
{ run_id, source, key, path, error }
```

- `key` : le nom du fichier sans extension.
- `error` : le message de `ET.ParseError`, avec sa ligne et sa colonne.
- Index : `(run_id, source)`.

**6. `mismatch`.** Une ligne par fichier dont l'`<ID>` n'est pas le nom (ADR-034 §1), y
compris un `versions.xml` qui n'est pas un artefact d'export.

```
{ run_id, source, key, path, found_id }
```

- `found_id` : l'`<ID>` lu dans le fichier, `null` s'il n'en a pas.
- Index : `(run_id, source)`.

**7. `invalidated`.** Une ligne par document rejeté au parse.

```
{ run_id, source, identifier, reason, error, files }
```

- `identifier` : la clé du document dans le flux ; un document rejeté n'a pas
  d'identifiant analysé.
- `reason` : l'une des raisons de rejet au parse (`parse_error`, `identifier_missing`,
  `identifier_malformed`, `undeclared_prefix`, `facet_root_duplicated`,
  `facet_root_undeclared`, `collision`).
- `error` : le message de l'exception, celui que porte déjà l'événement
  `document.invalidated`.
- `files` : les fichiers du document.
- Index : `(run_id, source, reason)`, `(identifier)`.

**8. `unformatted_relations` change de base, pas de schéma.** Ses lignes, son index
unique et son écriture par la saga, avec sa compensation, restent ceux d'ADR-021. Elle
s'accumule toujours d'un run à l'autre, par `first_seen_run` et `last_seen_run`.

**9. L'écriture.** Les collections des §3 à §7 sont écrites à la clôture de la session,
**même en cas d'échec**, comme `statistics` (ADR-034 §8), par lots d'`insert_many`. Les
workers tiennent leurs problèmes en mémoire jusque-là : de l'ordre de 110 000 copies
écartées sur le corpus LEGI complet, extrapolées des 11 du run à 0,01 %, soit quelques
dizaines de Mo.

**10. `nuke_all` vide `MURPHY_PROBLEMS`.** Il droppe chaque collection déclarée de la
base et repose ses index, comme pour `MURPHY_DATA`. Sans `nuke_all`, les lignes des
runs successifs s'accumulent, distinguées par leur `run_id`. `MURPHY_META` reste
préservée.

**11. Les artefacts d'export ne sont que comptés**, par `document.version_skipped`, comme
aujourd'hui.

## Alternatives rejetées

- **Garder les détails dans `MURPHY_META`.** La base méta garde l'histoire des runs et
  survit à `nuke_all` ; le détail des problèmes décrit les données d'un run et doit
  partir avec elles.
- **Un document par source et par run, découpé en parties** (l'amendement d'ADR-034
  §8). Chaque requête doit dérouler les parties et les tableaux, et chaque partie répète
  les comptes de la source.
- **Une collection `skipped_files` pour les illisibles et les `<ID>` différents.** Les
  deux n'ont en commun que d'être écartés avant le parser : l'un porte une erreur de
  lecture, l'autre un `<ID>`, et chacun se lit pour lui-même.
- **Stocker les artefacts d'export.** Une ligne par texte LEGI, pour un fichier attendu
  dont le chemin n'apprend rien.
- **Vider `MURPHY_PROBLEMS` à chaque run**, comme `transit_relations`. Un run sans
  `nuke_all` qui ne relit qu'une partie du corpus effacerait les relations non formatées
  des documents qu'il ne relit pas.
- **Garder `superseded_copy` parmi les collisions.** Une copie écartée n'est pas un
  conflit : l'arbitrage l'a tranché, et ADR-035 en fait une révision.
- **Écrire les problèmes au fil du run.** Un run qui échoue en laisserait une partie,
  et le détail d'un même run serait écrit par deux chemins.

## Conséquences

- Une troisième base Mongo, `MURPHY_PROBLEMS`, et une variable de plus dans `.env.dev`.
- `MURPHY_META.collisions` et `MURPHY_DATA.unformatted_relations` disparaissent ; le
  découpage en parties (`collision_documents.py`) aussi.
- `run_summaries.collisions` perd la raison `superseded_copy`, et
  `run_summaries.counts` gagne `document.superseded`.
- Les connecteurs gardent le chemin et l'erreur de chaque fichier écarté, et non plus
  seulement leur compte.
- En production, sans `nuke_all`, `MURPHY_PROBLEMS` grandit à chaque run.
- ADR-034 §8 est **amendé** : `MURPHY_META.collisions` est remplacée par
  `MURPHY_PROBLEMS.collisions` et `MURPHY_PROBLEMS.superseded`.
- ADR-021 §1 est **amendé** : `unformatted_relations` passe dans `MURPHY_PROBLEMS`.
- Les conséquences d'ADR-035 sont **amendées** : une copie écartée n'est plus comptée
  comme collision, mais comme `document.superseded`.
- `CLAUDE.md` et `docs/technical/data/` (`ARCHITECTURE.md`, `reference/pipeline.md`,
  `reference/modele-de-donnees.md`, `reference/telemetrie.md`,
  `reference/configuration.md`) suivent chaque commit qui les touche.

## Points ouverts

- La purge des lignes des anciens runs en production.

## Mise en œuvre

Chaque commit laisse le pipeline fonctionnel et la CI `python` au vert.

| # | Commit | Contenu |
|---|---|---|
| 1 | Base | `MONGODB_PROBLEMS_DB_NAME`, index, vidage par `nuke_all`, `unformatted_relations` déplacée (§1, §8, §10) |
| 2 | Collisions | Une ligne par collision dans `MURPHY_PROBLEMS`, fin du découpage en parties (§2, §3, §9) |
| 3 | Copies écartées | `superseded` avec les mtimes, `document.superseded`, retrait de `superseded_copy` des collisions (§4) |
| 4 | Fichiers écartés | `unreadable` et `mismatch` (§5, §6, §11) |
| 5 | Documents rejetés | `invalidated` (§7) |

## Références

ADR-021 §1 (amendé) · ADR-025 (collisions de métadonnées) · ADR-034 §1 et §8 (amendé) ·
ADR-035 (amendé) ·
`data/src/ragcore/adapters/storage/mongo/schemas.py` ·
`data/src/ragcore/adapters/storage/mongo/collision_repository.py` ·
`data/src/ragcore/sources/generic/file_connector.py` ·
`data/src/ragcore/sources/generic/copy_arbitration.py` ·
`data/src/ragcore/application/document_parsing.py` ·
`data/src/ragcore/orchestration/kedro/nodes/nuke_all.py`
