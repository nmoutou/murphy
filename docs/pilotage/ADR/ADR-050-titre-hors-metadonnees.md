# ADR-050 — Le titre n'entre pas en métadonnée

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-047

## Contexte

Le parser lit le titre d'un document dans les balises de `title_tags` (`TITRE`,
`TITRE_TA`, `NUM` chez LEGI ; `TITRE` en jurisprudence) et le range dans
`ParsedDocument.title`. Ces balises ont aussi le rôle `META` : `collect_metadata` les
recopiait donc dans `metadata`, sous leur clé chemin-complet
(`texte_version_meta_meta_spec_meta_texte_version_titre`).

ADR-047 avait écarté leur exclusion : cette copie est une métadonnée sans renommage
comme les autres, que `skip_unconfigured: true` retire. Mais en dev, avec
`skip_unconfigured: false`, chaque texte et chaque décision porte son titre deux fois,
et la copie remonte dans le signal `tags` du bilan comme une donnée à nommer, alors
qu'elle a déjà sa place.

## Décision

**Une balise de titre que la table ne renomme pas n'entre pas en métadonnée**, comme
l'identifiant et la nature : elle a son champ dédié (`title`).

**Une balise de titre renommée reste une métadonnée.** `NUM` → `num` est le titre d'un
article, mais le numéro d'un texte (`2016-1967`), qui n'est pas son titre. Le renommage
est une promotion explicite : la table a choisi d'en faire une métadonnée.

Les balises de titre gardent leur rôle `META` dans les tables. Retirer `TITRE` de la
table en ferait une balise inconnue : la cascade des balises non configurées la
remettrait en métadonnée, et les cliquets « aucune balise sans rôle » échoueraient.

## Alternatives rejetées

- **Exclure toutes les balises de `title_tags`.** Écarté : le numéro d'un texte
  (`num`) disparaîtrait.
- **N'exclure que la balise qui a fourni le titre du document.** Écarté : l'article
  perdrait `num`, une métadonnée configurée, et la règle dépendrait du document au lieu
  de la table.
- **S'en remettre à `skip_unconfigured: true`.** Écarté : le curseur retire aussi toutes
  les autres métadonnées sans renommage, que le dev veut voir.

## Conséquences

- `TITRE` et `TITRE_TA` ne sont plus dans `metadata`, ni dans le signal `tags`, quel que
  soit `skip_unconfigured`.
- `num` est inchangé.

## Références

`data/src/ragcore/sources/generic/metadata.py` ·
`data/src/ragcore/sources/generic/role_table.py` (`title_tags`)
