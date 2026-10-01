# ADR-047 — Une balise sans renommage est non configurée

**Statut** : ✅ Accepté (1er octobre 2026) — amende ADR-022 §1 · **amendé par ADR-048** (signal par clé chemin-complet en `tags`, `unconfigured_keys` supprimé)

## Contexte

ADR-022 §1 définit une balise non configurée comme une balise « non mappée ». Le code
lisait « absente de la table de rôles ». Or les tables ont été construites en relevant
toutes les balises du corpus : aucune n'en est absente. Sur un run réel, le signal
`tag.unconfigured` restait donc vide, et le curseur `skip_unconfigured` ne retirait rien.

Pourtant, beaucoup de balises de rôle `META` n'ont pas de renommage dans
`meta_renames` (`NUM_SEQUENCE`, `DERNIERE_MODIFICATION`, `AUTORITE`, `TITRE`…). Elles
entraient dans les métadonnées sous leur clé chemin-complet
(`textelr_meta_meta_spec_meta_texte_chronicle_num_sequence`), sans signal et sans que le
curseur puisse les retirer.

## Décision

**Une balise est non configurée si elle est absente de la table de rôles, ou si elle y
figure sans renommage.** Le rôle dit comment traiter la balise ; seul le renommage en
fait une métadonnée configurée, avec un nom choisi.

Une feuille `META` ou `VERSION` sans renommage :

- entre dans `metadata` sous sa clé chemin-complet, comme avant ;
- est signalée dans `ParseResult.unconfigured_tags`, puis dans `tag.unconfigured` au
  bilan de run ;
- donne sa clé à `ParseResult.unconfigured_keys`, que `skip_unconfigured: true` retire.

Les balises qui ont un champ dédié et ne vont pas dans `metadata` (l'identifiant, la
nature) ne sont pas concernées. Les balises de titre le sont : `title` est lu à part,
et leur copie dans `metadata` n'a pas de renommage.

## Alternatives rejetées

- **Garder « absente de la table ».** Le signal ne se déclenche que sur une balise
  nouvelle de la DILA. Il ne dit rien de ce qui reste à nommer, et le curseur est sans
  effet.
- **Exclure les balises de titre de `metadata`, comme l'identifiant.** Écarté : leur
  copie est une métadonnée sans renommage comme les autres.

## Conséquences

- En prod (`skip_unconfigured` forcé à `true`), les métadonnées sans renommage ne sont
  plus écrites. Pour en garder une, il faut lui donner un renommage dans la table de la
  source.
- Les cliquets « aucune balise sans rôle » (`test_role_table.py`, `test_juri.py`)
  filtrent le signal par `RoleTable.knows` : ils vérifient toujours que chaque balise a
  un rôle.

## Références

`data/src/ragcore/sources/generic/metadata.py` ·
`data/src/ragcore/sources/generic/unconfigured.py` ·
`data/src/ragcore/orchestration/kedro/nodes/parse_documents.py`
