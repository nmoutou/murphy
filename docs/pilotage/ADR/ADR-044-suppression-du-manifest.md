# ADR-044 — Suppression du manifest d'ingestion

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-022 §4-§5 et ADR-043 (§2 et §4)

## Contexte

L'ingestion tenait un registre append-only, la collection Mongo `LEGIFRANCE.manifest`.
Chaque document y recevait une entrée par run : `insert` s'il était inconnu, `update`
s'il était connu, ou `excluded` s'il était rejeté au parse.

Ce classement ne servait à rien :

- la saga écrit de la même façon un document nouveau ou un document connu
  (`replace_one` Mongo, delete-puis-insert Qdrant, `MERGE` Neo4j) ;
- les rejets sont déjà tracés par l'événement `document.invalidated` (raison, chemin
  source, erreur), écrit dans l'audit `MURPHY_META` ;
- dans le bilan de run, `insert` et `update` n'alimentaient qu'une ventilation de
  `document.persisted` qu'aucun code ne lisait.

Le projet payait donc une collection, deux index, un port, un adaptateur, une lecture
Mongo par document et une écriture par document, sans aucun usage.

## Décision

**1. Plus de manifest.** `ManifestEntry`, le port `ManifestRepository`, son adaptateur
Mongo, ses index et la purge par `nuke_all` sont supprimés.

**2. Plus d'opération.** L'enum `Operation` et `determine_operation` sont supprimés. Le
pipeline transporte des `ParsedDocument`, pas des paires `(document, opération)`.
`document.parsed` et `document.persisted` ne portent plus de payload `operation`, et le
bilan de run ne ventile plus `document.persisted`.

**3. Le nœud `computeIdempotence` devient `parseDocuments`**, puisqu'il ne calcule plus
d'idempotence : il parse, déclare les signaux et rejette.

## Alternatives rejetées

- **Déduire INSERT/UPDATE de la collection `documents`.** Une lecture Mongo par document
  pour une statistique qui ne pilote rien.
- **Garder le manifest pour les seuls rejets.** Il doublerait `document.invalidated`,
  déjà dans l'audit.

## Conséquences

- L'idempotence repose sur les écritures elles-mêmes : rejouer un run réécrit chaque
  document en place.
- Le compteur `document.persisted` et l'équation de complétude du bilan ne changent pas.
- La collection `LEGIFRANCE.manifest` des runs précédents n'est plus lue ni écrite. Un
  run `nuke_all` ne la supprime pas, puisqu'il ne connaît plus que `documents` : il faut
  la supprimer à la main (`db.manifest.drop()`).

## Références

ADR-022 (régimes dev/prod, §4-§5) · ADR-043 (§2 et §4, `include_path`)
