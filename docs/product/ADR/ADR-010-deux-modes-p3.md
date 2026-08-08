# ADR-010 — Architecture des deux modes d'annotation de P3

**Statut** : acté (chantier 4, 17 juillet 2026)

> ⚠️ **Complété le 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) —
> cet ADR **nommait** la calibration inter-experts sans la spécifier ; c'était le manque
> d'origine de #19. La spécification est en **ADR-038**, et une contrainte architecturale
> sur la file poolée est ajoutée ci-dessous. Aucune décision n'est renversée.

## Contexte

P3 porte deux usages d'annotation : inline (alpha ph.1, au fil de l'eau
sur requêtes réelles) et campagne poolée (ph.2). Risque de divergence
des formats de jugement.

## Décision

Un **composant de jugement unique** (rendu du passage + cascade q1→q3 +
écriture JSONL canonique), **deux orchestrations** :

- **Inline** (ph.1) : collecte opportuniste sur requêtes réelles,
  `origin: inline`.
- **Campagne** (ph.2) : file poolée, guide d'annotation affiché,
  calibration inter-experts (spécifiée en **ADR-038**), progression
  trackée.

**Contrainte sur la file poolée** (8 août 2026, #19) — elle sert **deux
consommateurs aux exigences opposées**, et doit les distinguer
explicitement :

| Consommateur | Contrainte d'affectation |
|---|---|
| Redondance d'**extériorité** (accord inter-assesseurs) | lecteur **différent** obligatoire |
| Rejeu d'**auto-cohérence** (stabilité intra-assesseur) | **même** lecteur obligatoire, après délai, en aveugle |

Sans cette distinction, **l'une des deux mesures est mécaniquement
impossible**. La discipline de service de la file (*toujours présenter ce
qui a été le moins jugé*, tourniquet par cas, contribution RBP à
l'intérieur) relève d'ADR-038 ; ce qui appartient ici est que la
« progression trackée » doit compter les jugements **par item et par
annotateur**, non globalement.

## Alternatives rejetées

- **Deux composants séparés** : deux formats qui divergent, jugements
  non comparables.

## Conséquences

- Risque documenté : si la cascade s'avère trop lourde en inline,
  **réviser la cascade elle-même** (ADR-005) — jamais créer deux formats
  de jugement divergents.

## Références

ADR-005 · ADR-008 · ADR-013 (alpha en deux phases) ·
**ADR-038** (protocole d'assessment — spécifie la calibration
inter-experts nommée ici)
