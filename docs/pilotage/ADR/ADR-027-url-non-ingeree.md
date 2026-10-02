# ADR-027 — L'URL n'est pas ingérée

**Statut** : ✅ Accepté (2 octobre 2026) — amende ADR-025

## Contexte

Chaque fichier DILA porte dans `<URL>` son propre chemin dans l'archive
(`article/LEGI/ARTI/00/00/45/32/82/LEGIARTI000045328204.xml`). Renommée en `url`,
c'était une métadonnée de LEGI et de la jurisprudence, et une clé `list` de LEGI
(ADR-025) : les deux facettes d'un texte donnaient chacune la leur.

Cette valeur ne dit rien du document : elle se déduit de l'identifiant, n'est pas une
adresse consultable, et le chemin du fichier source a déjà son champ (`source_files`,
ADR-011). Elle encombrait pourtant Mongo, le payload Qdrant et le nœud Neo4j, et
remplissait les collisions du bilan (98 textes LEGI sur le corpus de dev).

## Décision

**Un rôle `IGNORED` : la balise est connue, et n'est pas ingérée.** `URL` le porte, chez
LEGI et dans le socle commun de la jurisprudence. Comme une balise `TITLE` (ADR-026),
elle n'est jamais routée par la cascade des balises non configurées, et n'est pas
collectable : elle n'entre ni dans `metadata`, ni dans le signal `tags`, ni dans les
collisions, quel que soit `skip_unconfigured`.

`url` quitte `meta_renames` et les `list_keys` de LEGI.

**`URL_CC` reste une métadonnée** (`url_conseil_constitutionnel`) : c'est l'adresse
publique de la décision sur le site du Conseil constitutionnel.

## Alternatives rejetées

- **Retirer `URL` de la table.** Une balise absente est inconnue : la cascade la
  remettrait en métadonnée, sous sa clé chemin-complet, signalée en `tags`.
- **Garder le rôle `META` sans renommage.** `skip_unconfigured: true` la retirerait en
  prod, mais elle resterait en dev et dans le signal `tags`, comme une donnée à nommer.
- **Filtrer la clé `url` après la collecte.** Une liste de clés interdites à côté de la
  table : la décision ne se lirait plus dans le rôle de la balise.

## Conséquences

- `url` disparaît de Mongo, de Qdrant et de Neo4j au prochain run avec `nuke_all` : un
  run sans purge laisse les documents déjà écrits.
- Les collisions `url` quittent le bilan ; `versions_a_venir` reste la seule clé `list`
  de LEGI.
- Une autre balise à écarter prend le rôle `IGNORED` dans sa table.

## Références

`data/src/ragcore/sources/generic/roles.py` (`IGNORED`) ·
`data/src/ragcore/sources/legislatif/table.py` ·
`data/src/ragcore/sources/jurisprudence/table.py`
