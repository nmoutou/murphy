# INDEX — Registre des décisions (ADR)

> Un fichier par ADR (format Nygard). **Prochain numéro : ADR-050.**

## Registre

| ADR | Titre | Statut |
|---|---|---|
| [ADR-002](ADR-002-perimetre-jurisprudentiel-v0.md) | Périmètre jurisprudentiel de la v0 | Acté (constaté) |
| [ADR-003](ADR-003-sequencage-dila.md) | Séquençage d'ingestion DILA | Acté — clôture vague 2 différée |
| [ADR-004](ADR-004-unite-document.md) | Définition de l'unité « document » | Acté |
| [ADR-012](ADR-012-versions-par-capacites.md) | Versions par capacités mesurables | Rétro-documenté |
| [ADR-014](ADR-014-exhaustivite-dila-publication.md) | Exhaustivité DILA = critère de publication | Rétro-documenté |
| [ADR-015](ADR-015-association-avant-publication.md) | Association entre beta et publication | Rétro-documenté |
| [ADR-016](ADR-016-decouplage-recuperation-generation.md) | Découplage récupération / génération | Rétro-documenté |
| [ADR-018](ADR-018-identite-ecli-primaire.md) | Identité : ECLI primaire | Rétro-documenté |
| [ADR-019](ADR-019-rejet-akoma-ntoso.md) | Rejet d'Akoma Ntoso comme format de travail | Rétro-documenté |
| [ADR-020](ADR-020-tri-base-stateless-failfast.md) | Architecture tri-base + serving stateless/fail-fast | Rétro-documenté |
| [ADR-022](ADR-022-regimes-ingestion-dev-prod.md) | Régimes d'ingestion dev/prod : exhaustif vs sélectif | Acté — §5 amendé par ADR-023, ADR-043 et ADR-044, §2 et §6 par ADR-043, §4 par ADR-043 et ADR-044, §7 par ADR-024, §1 par ADR-047, §3 corrigé par ADR-049 |
| [ADR-023](ADR-023-interrupteur-embedding-dev.md) | Un interrupteur d'embedding, pas trois interrupteurs de store | Acté — amende ADR-022 §5, amendé par ADR-043 |
| [ADR-024](ADR-024-retrait-echantillonnage-corpus.md) | Retrait de l'échantillonnage de corpus | Acté — amende ADR-022 §7 |
| [ADR-026](ADR-026-restructuration-configuration.md) | Restructuration de la configuration en partition workflow / ingestion | ❌ Remplacé par ADR-042 |
| [ADR-039](ADR-039-contrat-ingestion-serving.md) | Contrat ingestion ↔ serving : le texte d'un passage vit dans Mongo, désigné par ses offsets | ✅ Accepté (25 septembre 2026) — s'appuie sur ADR-020 et ADR-022 §4, §3 amendé par ADR-042, §2 par ADR-046 |
| [ADR-040](ADR-040-depot-unique.md) | Un seul dépôt : fin des sous-modules, contrat du flux dans un paquet partagé | ✅ Accepté (25 septembre 2026) |
| [ADR-041](ADR-041-erreurs-du-chat-en-modale.md) | Erreurs du chat : une modale, l'étape en cause, un arrêt propagé au backend | ✅ Accepté (26 septembre 2026) — étend le contrat d'ADR-040 (`@murphy/contract/errors`) |
| [ADR-042](ADR-042-collection-qdrant-nom-fixe.md) | Une collection Qdrant au nom fixe : fin de l'empreinte, du pointeur et du tracking | ✅ Accepté (30 septembre 2026) — remplace ADR-026, amende ADR-039 §3, §3 amendé par ADR-043 |
| [ADR-043](ADR-043-configuration-ingestion-environment.md) | Configuration de l'ingestion : un fichier, un bloc `dev`, `ENVIRONMENT` seul arbitre | ✅ Accepté (30 septembre 2026) — amende ADR-022 §5-§6, ADR-023, ADR-042 §3 ; §3 et §4 amendés (labels Neo4j déclarés par les sources ; découpe dans l'environnement ; bloc `dev` aplati), §4 par ADR-044, amendement du §3 par ADR-046 |
| [ADR-044](ADR-044-suppression-du-manifest.md) | Suppression du manifest d'ingestion | ✅ Accepté (1er octobre 2026) — amende ADR-022 §4-§5 et ADR-043 §2 et §4 |
| [ADR-045](ADR-045-relations-non-formatees.md) | Relations non formatées : une collection, plus un champ du document | ✅ Accepté (1er octobre 2026) |
| [ADR-046](ADR-046-typage-des-documents.md) | Typage des documents : `document_type` fait foi, Neo4j le reflète | ✅ Accepté (1er octobre 2026) — amende ADR-039 §2 et l'amendement du §3 d'ADR-043 |
| [ADR-047](ADR-047-balise-non-configuree.md) | Une balise sans renommage est non configurée | ✅ Accepté (1er octobre 2026) — amende ADR-022 §1, amendé par ADR-048 et ADR-049 |
| [ADR-048](ADR-048-inconnus-tags-roots-links.md) | Les inconnus du bilan : `tags`, `roots`, `links` | ✅ Accepté (1er octobre 2026) — amende ADR-047, amendé par ADR-049 |
| [ADR-049](ADR-049-collisions-de-metadonnees.md) | Collisions de métadonnées : une liste, un ordre déclaré, un refus | ✅ Accepté (1er octobre 2026) — amende ADR-047 et ADR-048, corrige ADR-022 §3 · collection `MURPHY_META.collisions` retirée |

## Points ouverts rattachés

| Point ouvert | Rattaché à | Échéance de clôture |
|---|---|---|
| Contenu de la vague 2 d'ingestion (JORF + candidates KALI, CIRCULAIRES) | ADR-003 | Mini-ADR à l'issue de l'alpha |
| `doc_id` stable au niveau article pour LEGI | ADR-004 | v0 |
| Forme juridique · licence du code · soutenabilité | ADR-015 | Approche de la beta |
