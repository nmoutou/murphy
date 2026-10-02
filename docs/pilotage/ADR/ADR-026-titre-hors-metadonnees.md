# ADR-026 — Le titre n'entre pas en métadonnée

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-023

## Contexte

Le parser lit le titre d'un document dans les balises de `title_tags` (`TITRE`,
`TITRE_TA`, `NUM` chez LEGI ; `TITRE` en jurisprudence) et le range dans
`ParsedDocument.title`. Ces balises ont aussi le rôle `META` : `collect_metadata` les
recopiait donc dans `metadata`, sous leur clé chemin-complet
(`texte_version_meta_meta_spec_meta_texte_version_titre`).

ADR-023 avait écarté leur exclusion : cette copie est une métadonnée sans renommage
comme les autres, que `skip_unconfigured: true` retire. Mais en dev, avec
`skip_unconfigured: false`, chaque texte et chaque décision porte son titre deux fois,
et la copie remonte dans le signal `tags` du bilan comme une donnée à nommer, alors
qu'elle a déjà sa place.

## Décision

**Le titre a son rôle, `TITLE`**, distinct de `META` : `TITRE` (LEGI et jurisprudence)
et `TITRE_TA` (LEGI) le portent. Une balise `TITLE` est connue de la table, donc jamais
routée par la cascade des balises non configurées, et n'est pas collectable : elle
n'entre ni dans `metadata`, ni dans le signal `tags`. Sa valeur va dans son champ
dédié, `title`, lu par `title_tags`.

**`NUM` garde le rôle `META`.** Il est le titre d'un article, mais le numéro d'un texte
(`2016-1967`), qui n'est pas son titre : renommé en `num`, il reste une métadonnée.

Retirer `TITRE` de la table ne suffit pas : une balise absente est inconnue, et la
cascade la remettrait en métadonnée, signalée en `tags`.

## Alternatives rejetées

- **Exclure de `metadata` les balises de `title_tags` sans renommage, rôle `META`
  conservé.** Écarté : la règle croisait deux champs de la table au lieu de dire ce
  qu'est la balise.
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

`data/src/ragcore/sources/generic/roles.py` (`TITLE`) ·
`data/src/ragcore/sources/generic/metadata.py` ·
`data/src/ragcore/sources/generic/role_table.py` (`title_tags`)
