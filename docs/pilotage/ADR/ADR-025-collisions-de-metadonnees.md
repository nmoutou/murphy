# ADR-025 — Collisions de métadonnées : une liste, un ordre déclaré, un refus

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-023 et ADR-024, corrige ADR-011 §3 ·
**amendé le 1er octobre 2026** : la collection `MURPHY_META.collisions` est retirée ; les
collisions sortent des inconnus du bilan · **amendé par ADR-027** (`url` n'est plus
ingérée, ni déclarée en `list`)

## Contexte

Une clé de métadonnée peut recevoir plusieurs valeurs dans un même document :

- **entre facettes** : un texte LEGI fusionne `TEXTELR` et `TEXTE_VERSION`, qui
  répètent `META_COMMUN` et `META_TEXTE_CHRONICLE` ;
- **dans une facette** : des balises sœurs répétées (`NUMERO_AFFAIRE`,
  `VERSION_A_VENIR`).

`collect_metadata` et la cascade des balises non configurées gardaient la première valeur
et jetaient les autres en silence. L'ordre des facettes venait du tri des chemins de
fichiers (`TEXTELR` avant `TEXTE_VERSION`) : il était accidentel. La clé chemin-complet
d'ADR-011 §3 était dite injective. Elle ne l'est pas : deux balises sœurs homonymes ont
le même chemin.

Mesuré sur le corpus de dev (1 121 documents) :

- `url` diffère entre les facettes des 98 textes LEGI (chaque facette donne le chemin de
  son propre fichier) ;
- `VERSION_A_VENIR` porte plusieurs dates dans une même facette (14 textes) ;
- `numero_affaire` porte plusieurs valeurs dans 4 décisions CASS ;
- 7 balises LEGI non renommées (`NUM_SEQUENCE`, `DERNIERE_MODIFICATION`…) entraient deux
  fois, sous la clé chemin-complet de chaque facette, avec la même valeur.

## Décision

**Une collision est une clé qui reçoit au moins deux valeurs distinctes.** Les valeurs
sont comparées strictement, après `strip()`. Des valeurs identiques sont dédoublonnées et
ne font pas de collision.

**Une seule stratégie : `list`.** La table déclare ses clés `list` (`RoleTable.list_keys`).
Une clé `list` est toujours une liste, même avec une seule valeur. Une clé non renommée
qui entre en collision devient une liste, sans déclaration.

**L'ordre des valeurs est déclaré.** `RoleTable.roots` est un tuple ordonné : c'est
l'ordre de fusion des facettes. Les valeurs suivent le rang de leur facette, puis l'ordre
du document. LEGI déclare `TEXTE_VERSION` avant `TEXTELR`. Un document à plusieurs
facettes dont une racine n'est pas déclarée, ou dont deux facettes ont la même racine,
n'a pas d'ordre : il est refusé (`validation_error`).

**Une collision non configurée refuse le document.** Une clé renommée, hors `list_keys`,
qui reçoit deux valeurs distinctes fait refuser le document avec la raison `collision`
(`document.invalidated`). Il n'y a pas de différence entre dev et prod.

**Toute collision est visible.** Le bilan la compte dans son champ de premier niveau
`collisions` : clé → `{count, example}`. `count` est un nombre de documents ; `example`
est la liste des fichiers distincts d'où viennent les valeurs d'un de ces documents, dans
l'ordre déclaré des facettes.

**Amendement — la collection est retirée.** Une collection `MURPHY_META.collisions`
gardait le détail de chaque collision (un enregistrement par document et clé, toutes les
occurrences avec leur balise, leur chemin et leur facette). C'était un échafaudage
d'analyse, vidé et réécrit à chaque run ; un échec d'écriture émettait
`collision.unrecorded` et passait le run en `degraded`. L'analyse est faite : toutes les
collisions du corpus sont rangées par la table. La collection, son dépôt et l'événement
`collision.unrecorded` sont supprimés ; le bilan reste.

**Amendement — les collisions sortent des inconnus.** Le bilan les comptait d'abord dans
`unknowns.collisions`, avec l'exemple des inconnus (`identifier`, `source_file`). Une
collision n'est pas un mot inconnu : la table la nomme, la range ou refuse le document.
Et un seul fichier ne montrait pas une collision entre deux facettes. Elle a donc son
champ, au premier niveau, et son exemple donne tous les fichiers en jeu ; l'identifiant
se lit dans leur nom.

**Une cible de renommage n'apparaît qu'une fois par table.** Le renommage reste
injectif ; le cliquet `tests/golden/test_meta_renames.py` le vérifie, avec l'absence de
champ réservé parmi les cibles et la non-redéfinition des renommages communs de la
jurisprudence.

LEGI renomme ses 7 balises répétées entre facettes (`derniere_modification`,
`num_sequence`, `num_parution`, `page_debut_publication`, `page_fin_publication`,
`origine_publication`, `versions_a_venir`) et déclare `url` et `versions_a_venir` en
`list` ; JUDI déclare `numero_affaire`. *Amendé par ADR-027 : `url` n'est plus
ingérée.*

## Alternatives rejetées

- **Stratégies `first` et `last`.** L'ordre de départ était accidentel ; garder une
  valeur, c'est choisir sans savoir.
- **Arrêter le pipeline sur une collision non configurée.** Un document fautif ne doit
  pas priver le run de tous les autres : il est refusé et compté.
- **Un champ `facet_order` à côté de `roots`.** Il devrait couvrir exactement les mêmes
  racines : le même ensemble, écrit deux fois.
- **Plusieurs balises renommées vers une même cible.** Les cas rencontrés étaient la même
  balise dans deux facettes, que le renommage par balise fusionne déjà.

## Conséquences

- `ParseResult.collisions` porte les collisions d'un document parsé ; `CollisionError`
  (sous-classe de `ValidationError`) celles d'un document refusé.
- Une métadonnée peut être une liste de chaînes dans Mongo, Qdrant et Neo4j. Le backend
  ne lit aucune métadonnée.
- `url` d'un texte LEGI vaut `[version, struct]`. *Caduc depuis ADR-027.*
- Les 7 clés chemin-complet LEGI quittent `unknowns.tags` et entrent en prod.
- `RunStats` et `RunSummary` portent `collisions` à côté de `unknowns` ; la télémétrie
  les reçoit par `record_collision`.

## Références

`data/src/ragcore/sources/generic/occurrences.py` ·
`data/src/ragcore/sources/generic/parser.py` ·
`data/src/ragcore/orchestration/kedro/nodes/parse_documents.py`
