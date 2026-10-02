# ADR-022 — Typage des documents : `document_type` fait foi, Neo4j le reflète

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-015 §2 et l'amendement du §3
d'ADR-019

## Contexte

Deux typages coexistaient, et ils ne disaient pas la même chose :

- le **label Neo4j** venait du préfixe de l'identifiant, par une table que chaque source
  déclarait (`SourceDefinition.node_labels`) : `Article`, `Texte`, `Section`, et
  `Document` pour tout préfixe non déclaré, donc pour toutes les décisions. Il n'existait
  que dans Neo4j ;
- **`type_document`** était la balise `NATURE` recopiée telle quelle. Il allait dans
  Mongo et dans le payload Qdrant, et le frontend l'affichait comme type de la source.

Une requête sur le graphe (`UNWIND labels(n)`, puis `collect(DISTINCT n.type_document)`)
montrait l'écart :

| Label | `type_document` |
|---|---|
| `Texte` | `ARRETE`, `LOI`, `DECRET`, `LOI_ORGANIQUE`, `ORDONNANCE`, `CODE` |
| `Article` | `Article` |
| `Section` | (aucun) |
| `Document` | `ARRET`, `Texte`, `QPC` |

`NATURE` mêle deux axes : la forme du document (`Article`) et sa qualification juridique
(`LOI`, `QPC`). Mesurée sur le corpus le 1er octobre 2026, elle manque sur les sections,
vaut toujours `Texte` dans JADE (sans information) et `Article` sur les articles LEGI
(redondant avec la forme). Aucun des deux champs ne pouvait typer les documents de la
même façon dans Mongo et dans Neo4j.

Par ailleurs, aucune requête Neo4j ne portait de label : sans label, pas d'index, et
chaque recherche par `identifier` parcourait tous les nœuds.

## Décision

**1. `document_type`, un type fermé du domaine.** `DocumentType` vaut `article`,
`section`, `texte` ou `decision`. Il se déduit du préfixe de l'identifiant, la seule
donnée présente et validée sur tous les documents, d'après la table de rôles de la
source (`RoleTable.document_types`). Un préfixe que la table ne déclare pas refuse le
document (`ValidationError`, compté par le run). C'est un champ de `ParsedDocument` et
de `Chunk`, écrit à l'identique dans Mongo et dans le payload Qdrant.

**2. `nature`, un attribut secondaire.** La balise `NATURE` devient le champ `nature`,
en majuscules. Il vaut `None` si la balise manque ou si la table la déclare sans
information (`uninformative_natures` : `ARTICLE` pour LEGI, `TEXTE` pour JADE). Il
quitte les métadonnées : une seule source de vérité.

**3. Un seul type `decision`** pour les trois ordres de juridiction (`JURITEXT`,
`CETATEXT`, `CONSTEXT`). `source` distingue déjà la juridiction.

**4. Neo4j : `:Document:<Type>`.** Tout nœud porte `Document`, plus le label de son
`document_type` (`Article`, `Section`, `Texte`, `Decision`). Une contrainte d'unicité
porte sur `(:Document).identifier`, posée avec les index Mongo (`ensure_indexes`). Le
`MERGE` et tous les `MATCH` par identifiant passent par `Document`, donc par l'index.
Le label de type ne change jamais pour un identifiant, puisqu'il vient du préfixe : la
table `NodeLabels` et `SourceDefinition.node_labels` disparaissent.

**5. Le contrat du payload (ADR-015 §2).** `type_document` (facultatif) est remplacé
par `document_type` (obligatoire, l'une des quatre valeurs) et `nature` (facultatif).
Le backend refuse un point sans `document_type` connu (`CONTRACT_VIOLATION`). Les parts
`data-document` et `data-parentDocument` portent `documentType` et `nature`
(`@murphy/contract/messages`).

## Alternatives rejetées

- **Un seul label par nœud, celui du type.** Correspondance stricte avec
  `document_type`, mais quatre contraintes, et toute recherche devrait connaître le type
  pour profiter d'un index. Le futur serving, qui lira Neo4j à partir des identifiants
  de Qdrant, aurait dû recopier en TypeScript la règle qui donne le label. `Document` fait
  aussi le parallèle avec Mongo : la collection `documents` et son champ `document_type`.
- **Trois types de décision.** La juridiction est déjà dans `source`.
- **Garder `NATURE` comme type, en la normalisant.** Elle manque sur les sections et
  mêle la forme et la qualification juridique.

## Conséquences

- Un `nuke_all` et une réingestion complète : les documents, les points Qdrant et les
  nœuds déjà écrits n'ont pas les nouveaux champs ni les nouveaux labels.
- Jusqu'à cette réingestion, le backend refuse les anciens points (pas de
  `document_type`).
- Un nouveau type de document s'ajoute à l'enum, dans `TYPE_LABELS` (Neo4j) et dans les
  libellés du frontend : les tests et le compilateur signalent l'oubli.

## Références

`data/src/ragcore/core/models/enums.py` · `data/src/ragcore/sources/generic/classification.py` ·
`data/src/ragcore/adapters/storage/neo4j/node_properties.py` ·
`data/src/ragcore/adapters/storage/neo4j/schema.py` · `packages/contract/src/messages.ts` ·
[modele-de-donnees.md](../../technical/data/reference/modele-de-donnees.md)
