# ADR-021 — Relations non formatées : une collection, plus un champ du document

**Statut** : ✅ Accepté (1er octobre 2026)

## Contexte

Un `<LIEN>` dont l'`@id` est vide désigne sa cible en toutes lettres : « code de
l'environnement », « Articles 1103 et 1229 du code civil ». Mesuré sur le corpus le
18 juillet 2026 : 89 liens LEGI sur 16 227, et les 68 liens CASS, tous avec un texte, un
`typelien` et un `sens`.

L'extraction en faisait une `Citation` (`text`, `verb`, `sens`), rangée dans le champ
`citations` du `ParsedDocument`. Ce champ était donc écrit dans `MURPHY_DATA.documents`
et, en prop JSON, sur le nœud Neo4j du document.

Ce rangement posait deux problèmes :

- **Ce n'est pas une propriété du document.** C'est une relation dont la cible n'est pas
  encore résolue, au même titre qu'une pendante (`pending_relations`). La passe de
  résolution qui la transformera en arête devra la lire à côté des autres relations, pas
  la chercher dans chaque document.
- **Le mot « citation » est ambigu.** `CITATION` est aussi une valeur de `typelien`
  (40 des 89 liens LEGI sans `@id`, et le verbe `cites` des arêtes) : une « citation »
  pouvait être une arête `cites` ou une cible décrite.

## Décision

**1. Une collection `MURPHY_DATA.unformatted_relations`.** Une ligne par relation :

| Champ | Contenu |
|---|---|
| `source_id` | identifiant sérialisé du document qui énonce la relation |
| `target_text` | la désignation de la cible, brute et intégrale, jamais normalisée |
| `relation_type` | le verbe, traduit par la table de la source, brut sinon |
| `sens` | le rôle du document dans la relation (`source` / `cible`) |
| `source` | la source du document (`legi`, `cass`…) |
| `first_seen_run`, `last_seen_run` | le premier et le dernier run qui l'ont vue |

Index unique `uq_unformatted_source_text_type_sens` sur (`source_id`, `target_text`,
`relation_type`, `sens`). `sens` fait partie de la clé : « je cite X » et « X me cite »
sont deux faits.

**2. Accumulation, comme les pendantes.** L'écriture est une union idempotente :
`$setOnInsert` fige `first_seen_run`, `$set` avance `last_seen_run`. Rien n'est supprimé
d'un run à l'autre : une relation qu'un document ne déclare plus reste en base, et son
`last_seen_run` cesse d'avancer. `nuke_all` vide la collection avec les autres données.

**3. Écrite par la saga du document, en phase 1.** L'étape `mongo_unformatted_upsert`
suit `mongo_upsert`. Ces relations n'attendent aucun nœud : la phase 2 n'apporterait
rien. Sa compensation ne retire que les lignes de ce document **nées dans ce run**
(`first_seen_run`) : celles d'un run précédent ne lui appartiennent pas. Une ligne déjà
connue garde son `last_seen_run` avancé, le même résiduel que la compensation de
`documents`, rattrapé par le run suivant.

**4. Plus rien dans Neo4j.** Le nœud ne porte plus de prop `citations`.

**5. `Citation` devient `UnformattedRelation`**, calquée sur `Relation` :
`source_identifier`, `target_text`, `relation_type`, `sens`, `source`. Sans
`metadata`, contrairement à `Relation` : aucune donnée de la source ne le remplirait.
`ParsedDocument` perd son champ `citations` ; l'extraction rend ces relations dans
`ExtractionResult.unformatted_relations`, que le workload passe à la saga.

## Alternatives rejetées

- **Garder le champ du document.** Il mélange une relation et le contenu, et éparpille
  dans tout le corpus ce que la résolution devra lire d'un seul tenant.
- **Remplacer les lignes d'un document à chaque run.** Plus fidèle à sa version
  courante, mais la collection perdrait la date d'apparition d'une relation. Choisi :
  la même doctrine que les pendantes.
- **Écrire en phase 2, avec les arêtes.** La phase 2 attend que tous les nœuds du run
  existent ; une cible décrite n'en attend aucun.
- **Une clé sans `sens`.** Le `$set` écraserait le sens d'une relation par celui de la
  relation opposée de même texte.

## Conséquences

- `documents` ne contient plus `citations` : chaque document réécrit perd le champ
  (`replace_one`).
- Un graphe Neo4j déjà ingéré garde ses props `citations` jusqu'au prochain `nuke_all`.
- La future passe de résolution lit une seule collection, et peut cibler les relations
  récentes par `last_seen_run`.

## Références

`data/src/ragcore/core/models/unformatted_relation.py` ·
`data/src/ragcore/adapters/storage/mongo/unformatted_repository.py` ·
[modele-de-donnees.md](../../technical/data/reference/modele-de-donnees.md)
