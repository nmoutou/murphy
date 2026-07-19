# INDEX — Registre des décisions (ADR)

> Un fichier par ADR (format Nygard). ADR-001 à 010 : arbitrages du
> chantier 4 · ADR-011 à 020 : rétro-documentation des décisions
> implicites (chantier 5) · ADR-021 et suivants : au fil de l'exécution.
> **Prochain numéro : ADR-029.**

## Registre

| ADR | Titre | Statut |
|---|---|---|
| [ADR-001](ADR-001-statut-p4-ontologie.md) | Statut du volet Ontologie (P4) | Acté — P4 abandonné |
| [ADR-002](ADR-002-perimetre-jurisprudentiel-v0.md) | Périmètre jurisprudentiel de la v0 | Acté (constaté) |
| [ADR-003](ADR-003-sequencage-dila.md) | Séquençage d'ingestion DILA | Acté — clôture vague 2 différée |
| [ADR-004](ADR-004-unite-document.md) | Définition de l'unité « document » | Acté |
| [ADR-005](ADR-005-echelle-pertinence.md) | Échelle de pertinence et guide d'annotation | Acté |
| [ADR-006](ADR-006-agregation-chunk-document.md) | Agrégation chunk→document | Acté |
| [ADR-007](ADR-007-metriques-ndcg-r.md) | Métriques sans coupes constantes (nDCG@R) | Acté |
| [ADR-008](ADR-008-format-qrels-runs.md) | Format de stockage qrels/runs | Acté |
| [ADR-009](ADR-009-types-action.md) | Types d'action (stratification v0) | Acté — liste révisable en alpha ph.1 |
| [ADR-010](ADR-010-deux-modes-p3.md) | Architecture des deux modes d'annotation de P3 | Acté |
| [ADR-011](ADR-011-cadrage-en-programme.md) | Cadrage en programme | Rétro-documenté |
| [ADR-012](ADR-012-versions-par-capacites.md) | Versions par capacités mesurables | Rétro-documenté |
| [ADR-013](ADR-013-alpha-deux-phases.md) | Alpha en deux phases (option C) | Rétro-documenté |
| [ADR-014](ADR-014-exhaustivite-dila-publication.md) | Exhaustivité DILA = critère de publication | Rétro-documenté |
| [ADR-015](ADR-015-association-avant-publication.md) | Association entre beta et publication | Rétro-documenté |
| [ADR-016](ADR-016-decouplage-recuperation-generation.md) | Découplage récupération/génération + pertinence graduée | Rétro-documenté |
| [ADR-017](ADR-017-evaluation-en-strates.md) | Évaluation en strates de pérennité (T2) | Rétro-documenté — **amendé par ADR-025** (strate 5) |
| [ADR-018](ADR-018-identite-ecli-primaire.md) | Identité : ECLI primaire | Rétro-documenté |
| [ADR-019](ADR-019-rejet-akoma-ntoso.md) | Rejet d'Akoma Ntoso comme format de travail | Rétro-documenté |
| [ADR-020](ADR-020-tri-base-stateless-failfast.md) | Architecture tri-base + P3 stateless/fail-fast | Rétro-documenté |
| [ADR-021](ADR-021-tailoring-pm2-agile.md) | Tailoring PM² + exécution agile | Accepté (18 juillet 2026) |
| [ADR-022](ADR-022-regimes-ingestion-dev-prod.md) | Régimes d'ingestion dev/prod : exhaustif vs sélectif | Acté — §5 amendé par ADR-023, §7 par ADR-024 |
| [ADR-023](ADR-023-interrupteur-embedding-dev.md) | Un interrupteur d'embedding, pas trois interrupteurs de store | Acté — amende ADR-022 §5 |
| [ADR-024](ADR-024-retrait-echantillonnage-corpus.md) | Retrait de l'échantillonnage de corpus | Acté — amende ADR-022 §7 |
| [ADR-025](ADR-025-environnement-panel-consenti.md) | Environnement panel consenti pour métriques comportementales | 🔶 Proposé (19 juillet 2026) — amende ADR-017 |
| [ADR-026](ADR-026-restructuration-configuration.md) | Restructuration de la configuration en partition workflow/ingestion/evaluation | ✅ Accepté (19 juillet 2026, implémenté par B-14) — prérequis P1 d'ADR-027 |
| [ADR-027](ADR-027-plateforme-evaluation-end-to-end.md) | Plateforme d'évaluation end-to-end : le harnais pilote l'ingestion | 🔶 Proposé (19 juillet 2026) — dépend d'ADR-026 |
| [ADR-028](ADR-028-frontiere-verification-automatique-humaine.md) | Frontière vérification automatique / validation humaine | Acté (19 juillet 2026) — s'appuie sur ADR-017 |

## Points ouverts rattachés

| Point ouvert | Rattaché à | Échéance de clôture |
|---|---|---|
| Contenu de la vague 2 d'ingestion (JORF + candidates KALI, CIRCULAIRES) | ADR-003 | Mini-ADR à l'issue de l'alpha |
| `doc_id` stable au niveau article pour LEGI | ADR-004 | v0 (E-P1-03) |
| ADR-INST-01 (forme juridique) · ADR-INST-02 (licence du code) · ADR-INST-03 (soutenabilité) | `INSTITUTIONNEL.md` §6 (chantier 8) | Approche de la beta |
| Contrat de stabilité inverse P1→P4 (non-régression du graphe de citations typées) | ADR-001 | Non planifié |
| ~~Architecture deux modes de P3 (public/panel)~~ | — | **Clos par ADR-025** |
