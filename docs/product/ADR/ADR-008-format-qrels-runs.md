# ADR-008 — Format de stockage qrels/runs

**Statut** : acté (chantier 4, 17 juillet 2026)

> ⚠️ **Complété le 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) —
> la liste des champs était **incomplète** : rien n'y disait *comment* un grade avait été
> obtenu. Un champ `mode_resolution` est ajouté ci-dessous. Aucune suppression, aucun
> renversement : le reste de l'ADR tient.

## Contexte

Le format doit servir le harnais v0 et l'outil d'annotation expert
(alpha), et conserver la provenance des jugements.

## Décision

Stockage canonique **JSONL versionné**, un jugement par ligne :
`query_id`, `doc_id`, `chunk_id`, `q1/q2/q3`, `grade` (dérivé —
redondance assumée), `origin`, `annotator`, `timestamp`,
`guide_version`, **`mode_resolution`**. Les réponses q1–q3 permettent de
localiser les désaccords et de re-dériver les grades. **Projections
déterministes** vers qrels/runs TREC plats pour l'outillage standard
(trec_eval, pytrec_eval, ranx).

### `mode_resolution` — comment le grade a été obtenu (8 août 2026)

| Valeur | Cas |
|---|---|
| `unique` | un seul jugement rendu, aucune redondance |
| `concordant` | plusieurs jugements, accord d'emblée |
| `reconcilie` | désaccord levé par la **réconciliation** entre assesseurs |
| `regle` | désaccord tenu, grade obtenu par la **règle déclarée** (`max` à `n = 2`, vote majoritaire à `n ≥ 3`) |
| `arbitre` | désaccord tenu, grade rendu par une **autorité** (adjudication) |

**Le champ est dénormalisé**, comme `grade` l'est déjà : le mode de résolution est une
propriété du **couple `(query_id, doc_id)`**, pas d'un jugement isolé, mais il est porté par
chaque ligne du couple plutôt que réservé à la projection dérivée. Motif : suivre le
compromis que cet ADR assume explicitement pour `grade` (*« dérivé — redondance assumée »*)
plutôt que d'en introduire un second, incompatible, dans le même fichier.

Spécification du protocole qui produit ces valeurs : **ADR-038**.

## Alternatives rejetées

- **TREC plat comme format canonique** : perd q1–q3, la provenance et le
  versionnement du guide.

## Conséquences

- L'outillage IR standard reste utilisable sans adaptation.
- Le JSONL canonique reste la seule source de vérité.
- **Sans `mode_resolution`, l'adjudication efface le désaccord qu'elle
  répare** : un item arbitré ressortirait avec un grade unique et rien
  d'autre, ce qui détruit la mesure d'accord inter-assesseurs par son
  propre remède. C'est le constat du TREC Legal Track 2009 — ce sont
  *« the volume and results of the appeals and adjudication process »*
  qui ont instruit les Topic Authorities, **pas les qrels finales**
  ([#19](https://github.com/left-eyebr0w/murphy/issues/19)).

## Références

ADR-005 (cascade q1–q3) · ADR-010 (composant de jugement) ·
**ADR-038** (protocole d'assessment — producteur de `mode_resolution`)
