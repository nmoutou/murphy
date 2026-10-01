# ADR-048 — Les inconnus du bilan : `tags`, `roots`, `links`

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-047 · **amendé par ADR-049** (catégorie `collisions`, sortie ensuite des inconnus)

## Contexte

Après ADR-047, `run_summaries.unknowns` portait cinq catégories : `tag.unconfigured`,
`racine`, `typelien`, `sens` et `identifiant`. Trois défauts :

- une balise y était nommée par son nom (`NUM_SEQUENCE`), alors que la donnée vit en
  `metadata` sous sa clé chemin-complet
  (`textelr_meta_meta_spec_meta_texte_chronicle_num_sequence`) ;
- une balise inconnue dont la valeur est un identifiant DILA devient un lien
  (heuristique), mais elle était signalée comme une balise, et `skip_unconfigured` ne
  retirait pas son arête ;
- `sens` et `identifiant` ne décrivent pas un type de lien : ils signalent un lien
  qu'on n'a pas pu écrire.

## Décision

**Trois catégories plates**, chacune `clé → {count, example}` :

- `tags` : les métadonnées non configurées, sous leur clé chemin-complet ;
- `roots` : les racines XML que la source ne déclare pas ;
- `links` : les types de lien non configurés — un `typelien` non traduit, ou la clé
  chemin-complet d'une balise absente de la table dont la valeur est un identifiant
  DILA.

Le signal naît des **valeurs** : une balise sans texte ni attribut n'en émet aucun.

**Un lien qu'on ne sait pas écrire est compté, pas listé.** `sens` inconnu, `@id`
illisible, `typelien` qui ne peut pas être un verbe : l'arête n'existe pas, et le
compteur `relation.unknown` (porteur de `count`, un événement par document) le dit. Il
ne change pas le statut du run.

**`skip_unconfigured: true` retire tout ce que listent `tags` et `links`** : les
métadonnées au site de parse, comme avant ; les arêtes heuristiques et celles d'un
`typelien` inconnu à l'extraction (`GenericRelationExtractor`). Les signaux sont émis
dans les deux régimes ; un lien retiré par le curseur n'est pas compté en
`relation.unknown`.

## Alternatives rejetées

- **Un niveau de plus dans `links`** (`typelien`, `sens`, `source_id`, `target_id`,
  balises). Le bilan dit quels types de lien restent à configurer, il ne décrit pas un
  lien précis. Et le rôle d'un `@id` illisible dépend du `sens`, lui-même parfois
  inconnu.
- **Retirer `sens` et `identifiant` sans compteur.** Ces liens disparaîtraient en
  silence.

## Conséquences

- `ParseResult.unconfigured_keys` disparaît : les clés de `unconfigured_tags` sont la
  poignée du curseur. `ParseResult.unconfigured_links` porte les liens heuristiques.
- Les cliquets « aucune balise sans rôle » parcourent eux-mêmes l'arbre XML : le signal
  ne nomme plus les balises.
- En prod (`skip_unconfigured` forcé à `true`), une arête de `typelien` inconnu n'est
  plus écrite. Pour la garder, il faut traduire le mot dans la table de la source.

## Références

`data/src/ragcore/core/services/unknown_categories.py` ·
`data/src/ragcore/core/links/extraction.py` ·
`data/src/ragcore/sources/generic/relations.py` ·
`data/src/ragcore/orchestration/kedro/workload.py`
