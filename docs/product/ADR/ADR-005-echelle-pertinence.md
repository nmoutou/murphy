# ADR-005 — Échelle de pertinence et guide d'annotation

**Statut** : acté (chantier 4, 17 juillet 2026) — **complété le 2 août 2026**
([#14](https://github.com/left-eyebr0w/murphy/issues/14) : projection des grades
dans la métrique)

## Contexte

La pertinence graduée est un invariant (ADR-016). Restait à figer
l'échelle, utilisable en solo (v0) comme par les experts (alpha).

## Décision

Grades **0–3 dérivés d'une cascade de trois tests binaires** :

| Test | Question | Si non |
|---|---|---|
| Q1 | Même question de droit ? | grade 0 |
| Q2 | Citable dans une consultation ? | grade 1 |
| Q3 | Support principal de la solution ? | grade 2 (oui → 3) |

Conventions :

- Pertinence **topique, non directionnelle** : un arrêt contraire bien
  en point est un 3.
- Citations minées à **grade 2 par défaut, surclassables**.
- **Guide d'annotation** = documentation des trois questions avec cas
  limites, écrit **dès la v0** pour servir tel quel en alpha ph.2.

## Décision complémentaire — projection dans la métrique (2 août 2026)

`nDCG` était le consommateur de l'échelle ; il a été retiré
([ADR-007](ADR-007-metrique-rbp-residu.md)). Les grades entrent désormais dans
**RBP** comme gains normalisés, par **projection linéaire** :

| Grade | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Gain `g/3` | 0 | 0,33 | 0,67 | **1** |

**Motif — l'échelle est un compte, pas une intensité.** Elle est *dérivée d'une
cascade de trois tests binaires* : chaque porte franchie vaut donc le même
incrément, et c'est exactement ce qu'une projection linéaire écrit. La
convention exponentielle `(2^g − 1)/7`, usuelle pour nDCG, rapatrierait les
**démarcations d'intensité** que cet ADR a nommément rejetées — au nom d'une
convention appartenant à la métrique retirée. RBP discount déjà par le rang :
empiler une seconde non-linéarité sur le gain composerait deux choix arbitraires
au lieu d'un.

**Conséquence de rédaction du guide** : la métrique s'appuie maintenant sur le
fait que **chaque porte se franchit ou non sans demi-mesure**. Le guide doit
être écrit pour cette propriété, et non plus seulement pour la localisabilité
des désaccords.

**Portée** : l'échelle ne vaut que pour le **noyau jugé** (30 cas). Les 120 cas
gratuits ont un label binaire — un fait détermine l'ensemble-réponse, un
document est dedans ou dehors — et entrent dans RBP avec des gains `{0, 1}`.

**Réserve ouverte** : la borne du résidu RBP suppose un gain maximal de 1 pour
tout document non jugé, ce qui rend la projection compatible avec la borne.
**Non vérifié à la source** → [#22](https://github.com/left-eyebr0w/murphy/issues/22).
Repli si elle ne tient pas : binarisation à `g ≥ 2` — écartée ici parce que la
pertinence graduée est un **invariant** (ADR-016), non par préférence.

## Alternatives rejetées

- **Échelle à démarcations d'intensité** (« directement applicable /
  support / périphérique / hors-sujet ») : arbitraire, désaccords non
  localisables.
- **Projection exponentielle `(2^g − 1)/7`** dans RBP : voir ci-dessus.
- **Binarisation des grades** à `g ≥ 2` (défaut du TREC Legal Track,
  `responsive / non responsive` + seuil `Kh` séparé) : écartée par ADR-016.

## Conséquences

- q1–q3 stockées avec le grade (ADR-008) : désaccords localisables à la
  question près, grades re-dérivables.
- Le composant de jugement (ADR-010) implémente la cascade, pas une
  saisie directe du grade.
- **La projection est un fait de *scorer*, pas un champ d'authoring** : rien
  n'est écrit dans l'enregistrement, les grades restent stockés en `0–3`.
- ⛔ **« Citations minées à grade 2 par défaut » est périmé** — ADR-029 a retiré
  les citations minées de la source de qrels ; la strate 2 est un diagnostic de
  précision, sans grade.

## Références

ADR-007 ([RBP + résidu](ADR-007-metrique-rbp-residu.md)) · ADR-008 (format) ·
ADR-010 (composant de jugement) · ADR-016 (pertinence graduée, invariant) ·
ADR-029 (strate 2 rétrogradée)
