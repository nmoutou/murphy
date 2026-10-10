# INDEX — Registre des décisions (ADR)

> Un fichier par ADR (format Nygard). **Prochain numéro : ADR-030**, réservé à l'adaptation de l'interface du frontend (ADR-028 §10).

## Registre

| ADR | Titre | Statut |
|---|---|---|
| [ADR-001](ADR-001-perimetre-jurisprudentiel-v0.md) | Périmètre jurisprudentiel de la v0 | Acté (constaté) |
| [ADR-002](ADR-002-sequencage-dila.md) | Séquençage d'ingestion DILA | Acté — clôture vague 2 différée |
| [ADR-003](ADR-003-unite-document.md) | Définition de l'unité « document » | Acté |
| [ADR-004](ADR-004-versions-par-capacites.md) | Versions par capacités mesurables | Rétro-documenté |
| [ADR-005](ADR-005-exhaustivite-dila-publication.md) | Exhaustivité DILA = critère de publication | Rétro-documenté |
| [ADR-006](ADR-006-association-avant-publication.md) | Association entre beta et publication | Rétro-documenté |
| [ADR-007](ADR-007-decouplage-recuperation-generation.md) | Découplage récupération / génération | Rétro-documenté — amendé par ADR-028 (génération retirée) |
| [ADR-008](ADR-008-identite-ecli-primaire.md) | Identité : ECLI primaire | Rétro-documenté |
| [ADR-009](ADR-009-rejet-akoma-ntoso.md) | Rejet d'Akoma Ntoso comme format de travail | Rétro-documenté |
| [ADR-010](ADR-010-tri-base-stateless-failfast.md) | Architecture tri-base + serving stateless/fail-fast | Rétro-documenté — amendé par ADR-028 (OpenSearch, LLM retiré) |
| [ADR-011](ADR-011-regimes-ingestion-dev-prod.md) | Régimes d'ingestion dev/prod : exhaustif vs sélectif | Acté — §5 amendé par ADR-012, ADR-019 et ADR-020, §2 et §6 par ADR-019, §4 par ADR-019 et ADR-020, §7 par ADR-013, §1 par ADR-023, §3 corrigé par ADR-025 |
| [ADR-012](ADR-012-interrupteur-embedding-dev.md) | Un interrupteur d'embedding, pas trois interrupteurs de store | Acté — amende ADR-011 §5, amendé par ADR-019 |
| [ADR-013](ADR-013-retrait-echantillonnage-corpus.md) | Retrait de l'échantillonnage de corpus | Acté — amende ADR-011 §7 |
| [ADR-014](ADR-014-restructuration-configuration.md) | Restructuration de la configuration en partition workflow / ingestion | ❌ Remplacé par ADR-018 |
| [ADR-015](ADR-015-contrat-ingestion-serving.md) | Contrat ingestion ↔ serving : le texte d'un passage vit dans Mongo, désigné par ses offsets | ✅ Accepté (25 septembre 2026) — s'appuie sur ADR-010 et ADR-011 §4, §3 amendé par ADR-018, §2 par ADR-022, §1 à §5 par ADR-028 |
| [ADR-016](ADR-016-depot-unique.md) | Un seul dépôt : fin des sous-modules, contrat du flux dans un paquet partagé | ✅ Accepté (25 septembre 2026) |
| [ADR-017](ADR-017-erreurs-du-chat-en-modale.md) | Erreurs du chat : une modale, l'étape en cause, un arrêt propagé au backend | ✅ Accepté (26 septembre 2026) — étend le contrat d'ADR-016 (`@murphy/contract/errors`) |
| [ADR-018](ADR-018-collection-qdrant-nom-fixe.md) | Une collection Qdrant au nom fixe : fin de l'empreinte, du pointeur et du tracking | ✅ Accepté (30 septembre 2026) — remplace ADR-014, amende ADR-015 §3, §3 amendé par ADR-019, §1-§2 par ADR-028 |
| [ADR-019](ADR-019-configuration-ingestion-environment.md) | Configuration de l'ingestion : un fichier, un bloc `dev`, `ENVIRONMENT` seul arbitre | ✅ Accepté (30 septembre 2026) — amende ADR-011 §5-§6, ADR-012, ADR-018 §3 ; §3 et §4 amendés (labels Neo4j déclarés par les sources ; découpe dans l'environnement ; bloc `dev` aplati), §4 par ADR-020, amendement du §3 par ADR-022 |
| [ADR-020](ADR-020-suppression-du-manifest.md) | Suppression du manifest d'ingestion | ✅ Accepté (1er octobre 2026) — amende ADR-011 §4-§5 et ADR-019 §2 et §4 |
| [ADR-021](ADR-021-relations-non-formatees.md) | Relations non formatées : une collection, plus un champ du document | ✅ Accepté (1er octobre 2026) |
| [ADR-022](ADR-022-typage-des-documents.md) | Typage des documents : `document_type` fait foi, Neo4j le reflète | ✅ Accepté (1er octobre 2026) — amende ADR-015 §2 et l'amendement du §3 d'ADR-019 |
| [ADR-023](ADR-023-balise-non-configuree.md) | Une balise sans renommage est non configurée | ✅ Accepté (1er octobre 2026) — amende ADR-011 §1, amendé par ADR-024, ADR-025 et ADR-026 |
| [ADR-024](ADR-024-inconnus-tags-roots-links.md) | Les inconnus du bilan : `tags`, `roots`, `links` | ✅ Accepté (1er octobre 2026) — amende ADR-023, amendé par ADR-025 |
| [ADR-025](ADR-025-collisions-de-metadonnees.md) | Collisions de métadonnées : une liste, un ordre déclaré, un refus | ✅ Accepté (1er octobre 2026) — amende ADR-023 et ADR-024, corrige ADR-011 §3 · collection `MURPHY_META.collisions` retirée · `collisions` au premier niveau du bilan · amendé par ADR-027 |
| [ADR-026](ADR-026-titre-hors-metadonnees.md) | Le titre n'entre pas en métadonnée | ✅ Accepté (1er octobre 2026) — amende ADR-023 |
| [ADR-027](ADR-027-url-non-ingeree.md) | L'URL n'est pas ingérée | ✅ Accepté (2 octobre 2026) — amende ADR-025 |
| [ADR-028](ADR-028-opensearch-remplace-qdrant.md) | OpenSearch remplace Qdrant : un moteur de recherche hybride, sans LLM | ✅ Accepté (2 octobre 2026) — amende ADR-007, ADR-010, ADR-015 §1-§5 et ADR-018 §1-§2 · §2 et §6 amendés par ADR-029 · §7, §8 et §10 amendés le 5 octobre 2026 (aucun score servi ; pagination à 10 et 100 ; contexte du LLM plafonné) · §10 amendé le 10 octobre 2026 (la page de résultats passe à ADR-030) |
| [ADR-029](ADR-029-recherche-hybride-quatre-listes.md) | Recherche hybride : une liste de références et un vecteur de titre | ✅ Accepté (4 octobre 2026) — amende ADR-028 §2 et §6 |

## Points ouverts rattachés

| Point ouvert | Rattaché à | Échéance de clôture |
|---|---|---|
| Contenu de la vague 2 d'ingestion (JORF + candidates KALI, CIRCULAIRES) | ADR-002 | Mini-ADR à l'issue de l'alpha |
| `doc_id` stable au niveau article pour LEGI | ADR-003 | v0 |
| Forme juridique · licence du code · soutenabilité | ADR-006 | Approche de la beta |
| API de recherche paginée : retrait du LLM, du WebSocket, du SSE et de l'AI SDK, texte servi à la demande | ADR-028 §9-§10 | ADR dédiée, étape 2 de la migration |
| Remplacement du modèle d'embedding par un modèle qui couvre le français | ADR-028 | Après l'étape 2 de la migration |
| Interface du frontend adaptée au pivot (moteur de recherche), page de résultats comprise | ADR-028 §9-§10 | ADR-030, après le remplacement du modèle d'embedding |
