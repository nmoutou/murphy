# Registre de décisions — `decisions/`
 
## Index
 
| ADR | Titre | Statut |
|---|---|---|
| 001 | Statut de P4 (Ontologie) | acté (ch. 4) |
| 002 | Périmètre jurisprudentiel v0 | acté (constaté) |
| 003 | Séquençage DILA | acté |
| 004 | Unité « document » | acté |
| 005 | Échelle de pertinence (cascade) | acté |
| 006 | Agrégation chunk→document | acté |
| 007 | Métriques sans coupes constantes (nDCG@R) | acté |
| 008 | Format qrels/runs (JSONL canonique) | acté |
| 009 | Types d'action (stratification v0) | acté |
| 010 | Architecture des deux modes de P3 | acté |
| 011–020 | Décisions rétro-documentées | rétro |
 
---
 
## ADR-001 — Statut du volet Ontologie (P4)
 
**Contexte.** Trois projets opérationnels (P1 Data, P2 Évaluation, P3 Applicatif) + un volet doctoral (P4). Intégré au programme, ou extérieur ?
 
**Décision.** P4 est **hors programme opérationnel, interfaces déclarées**. P4→P1 documenté comme **influence** (FRBR Work/Expression/Manifestation, citations typées informant le modèle Neo4j), non comme dépendance : **aucun jalon n'attend un livrable doctoral**.
 
**Alternatives rejetées.** Intégration de P4 : couplerait les versions opérationnelles au rythme et aux critères doctoraux.
 
**Conséquences.** Le programme avance indépendamment ; P4 consomme les artefacts de P1 sans les bloquer. **Point ouvert** : formaliser ou non un contrat de stabilité inverse P1→P4 (non-régression sur le graphe de citations typées).
 
## ADR-002 — Périmètre jurisprudentiel de la v0
 
**Contexte.** PROGRAM §4 laissait ouvert : les 5 bases, ou un sous-ensemble couvrant les deux ordres.
 
**Décision.** **Les 5 bases** (CASS, INCA, CAPP, JADE, CONSTIT). Décision **constatée** — déjà implémentée. Justification a posteriori : réplicabilité prouvée sur toute la variété structurelle DILA (dont le cas piégeux CASS/INCA à racine XML commune) et socle judiciaire complet pour l'alpha.
 
**Alternatives rejetées.** Sous-ensemble CASS + JADE : suffisant pour la réplicabilité, mais socle incomplet pour les experts ; l'économie était caduque, le travail étant fait.
 
**Conséquences.** DoD v0 applicable aux 5 bases (identité canonique vérifiée sur les 3 BDD pour chacune) ; métriques rapportées par base (cf. ADR-004).
 
## ADR-003 — Séquençage d'ingestion DILA
 
**Contexte.** L'exhaustivité DILA est un critère de publication (ADR-017) ; il fallait ordonner l'ingestion, priorisée par valeur pour les experts.
 
**Décision.** **Vague 1** (v0) : les 5 bases juris — *fait*. **Vague 2** (→ beta) : **JORF** + base(s) **à déterminer sur les retours alpha** (candidates : KALI, CIRCULAIRES). **Vague 3** (→ publication) : solde DILA. Le choix différé de la vague 2 est assumé, cohérent avec les versions par capacités mesurables.
 
**Alternatives rejetées.** Séquence figée dès maintenant (JORF + KALI, proposition initiale de PROGRAM §4) : fige un arbitrage que l'alpha informera mieux.
 
**Conséquences.** PROGRAM §4 à mettre à jour ; mini-ADR de clôture du choix vague 2 à l'issue de l'alpha.
 
## ADR-004 — Définition de l'unité « document »
 
**Contexte.** L'évaluation à deux niveaux (passage + document) exige une définition stable (CADRAGE_evaluation §2, §9). Candidats : arrêt entier, article, section, fichier XML.
 
**Décision.** Définition **fonctionnelle, non géométrique** : l'unité de **citation juridique canonique de chaque base** — la **décision** (ECLI) en jurisprudence, l'**article** pour LEGI. Règle d'extension aux vagues suivantes : ce qu'un juriste cite.
 
**Alternatives rejetées.** Définitions géométriques (fichier, section) : dépendent de l'archivage DILA, instables entre bases. Unité unique inter-bases : la pratique de citation diffère par nature.
 
**Conséquences.** Métriques document rapportées **par base** en plus de l'agrégé ; l'identité canonique doit exposer un **`doc_id` stable à ce niveau** — à vérifier côté pipeline LEGI pour l'article.
 
## ADR-005 — Échelle de pertinence et guide d'annotation
 
**Contexte.** Pertinence graduée = invariant (ADR-016). Restait à figer l'échelle, utilisable en solo (v0) comme par les experts (alpha).
 
**Décision.** Grades **0–3 dérivés d'une cascade de trois tests binaires** : **Q1** même question de droit ? non → 0 · **Q2** citable dans une consultation ? non → 1 · **Q3** support principal de la solution ? non → 2, oui → 3. Conventions : pertinence **topique, non directionnelle** (un arrêt contraire bien en point est un 3) ; citations minées à **grade 2 par défaut, surclassables** ; **guide d'annotation** = documentation des trois questions avec cas limites, écrit **dès la v0** pour servir tel quel en alpha ph.2.
 
**Alternatives rejetées.** Échelle à démarcations d'intensité (« directement applicable / support / périphérique / hors-sujet ») : arbitraire, désaccords non localisables.
 
**Conséquences.** q1–q3 stockées avec le grade (ADR-008) : désaccords localisables à la question près, grades re-dérivables. Le composant de jugement (ADR-010) implémente la cascade, pas une saisie directe du grade.
 
## ADR-006 — Agrégation chunk→document
 
**Contexte.** Un seul jeu de qrels niveau chunk doit produire les métriques passage **et** document (CADRAGE_evaluation §4).
 
**Décision.** Côté **qrels** : **max** — le document vaut son meilleur chunk (pas de biais de taille). Côté **runs** : **rang du premier chunk** du document. Les fusions de scores sophistiquées sont des **stratégies de config évaluées**, jamais des règles du harnais.
 
**Alternatives rejetées.** `sum` plafonné ou moyennes : introduisent un biais de taille de document ; fusion dans le harnais : contaminerait la mesure par un choix de pipeline.
 
**Conséquences.** Le scorer reste trivial et neutre ; toute intelligence d'agrégation se mesure comme n'importe quelle config.
 
## ADR-007 — Métriques sans coupes constantes (nDCG@R)
 
**Contexte.** CADRAGE_evaluation §9 demandait des valeurs de k. Or les k fixes relèvent du modèle web search, incompatible avec l'invariant d'exhaustivité des sources.
 
**Décision.** **Rejet des k fixes.** Métrique de décision **unique** : **nDCG@R** (coupe adaptative = nombre de pertinents de la requête), **test statistique apparié** dessus. Diagnostics : MAP, R-Precision, Recall@2R (passage) ; Doc-MRR, Doc-Recall@R (document). Côté produit : listes de longueur variable par **seuil de score** — le seuil est une stratégie de config. Seule profondeur opérationnelle restante : le **pooling** (paramètre de collecte, définissable en multiple de R).
 
**Alternatives rejetées.** nDCG@k / Recall@k à k constants : cohérents avec un affichage top-k que Murphy n'a pas.
 
**Conséquences.** Sensibilité accrue à la **complétude des qrels** (R dépend des jugements) → importance renforcée du pooling et des citations minées.
 
## ADR-008 — Format de stockage qrels/runs
 
**Contexte.** Le format doit servir le harnais v0 et l'outil d'annotation expert (alpha), et conserver la provenance des jugements.
 
**Décision.** Stockage canonique **JSONL versionné**, un jugement par ligne : `query_id`, `doc_id`, `chunk_id`, `q1/q2/q3`, `grade` (dérivé — redondance assumée), `origin`, `annotator`, `timestamp`, `guide_version`. Les réponses q1–q3 permettent de localiser les désaccords et de re-dériver les grades. **Projections déterministes** vers qrels/runs TREC plats pour l'outillage standard (trec_eval, pytrec_eval, ranx).
 
**Alternatives rejetées.** TREC plat comme format canonique : perd q1–q3, la provenance et le versionnement du guide.
 
**Conséquences.** L'outillage IR standard reste utilisable sans adaptation ; le canonique reste la seule source de vérité.
 
## ADR-009 — Types d'action (stratification v0)
 
**Contexte.** La stratification des requêtes par type d'action (CADRAGE_evaluation §3.2, §9) devait être fixée pour la v0.
 
**Décision.** **Quatre types = quatre capacités mesurées séparément** : `texte_applicable`, `jurisprudence_sur_question`, `known_item`, `graph_hop` (intègre le set diagnostique exigé par la DoD). **Exclus de la v0** : vigueur temporelle, multi-tours. Axe difficulté orthogonal inchangé. Liste **révisable en alpha ph.1 sans migration**.
 
**Alternatives rejetées.** Typologie plus fine d'emblée : spéculative avant les requêtes réelles de l'alpha.
 
**Conséquences.** Les rapports d'évaluation ventilent par type ; `graph_hop` mesure directement la valeur de l'augmentation Neo4j.
 
## ADR-010 — Architecture des deux modes de P3
 
**Contexte.** P3 porte deux usages d'annotation : inline (alpha ph.1, au fil de l'eau) et campagne poolée (ph.2). Risque de divergence des formats de jugement.
 
**Décision.** Un **composant de jugement unique** (rendu du passage + cascade q1→q3 + écriture JSONL canonique), **deux orchestrations** : **inline** (ph.1, collecte opportuniste sur requêtes réelles, `origin: inline`) et **campagne** (ph.2, file poolée, guide affiché, calibration inter-experts, progression trackée).
 
**Alternatives rejetées.** Deux composants séparés : deux formats qui divergent, jugements non comparables.
 
**Conséquences.** Risque documenté : si la cascade s'avère trop lourde en inline, **réviser la cascade elle-même** — jamais créer deux formats de jugement divergents.
 
---
 
## Décisions rétro-documentées
 
**ADR-011 — Cadrage en programme.** L'écosystème complet est structuré en **programme à trois projets** (P1/P2/P3) + volet doctoral, avec **interfaces contractualisées** (PROGRAM §2.2) — plutôt qu'un projet unique. Conséquence : les frontières passent par des contrats (IDs canoniques, payloads, adapter), condition de l'évaluation agnostique.
 
**ADR-012 — Versions par capacités mesurables.** Aucune date : chaque version est définie par des critères d'entrée/sortie mesurables. v0 = « mesurable » (data + éval, **sans** applicatif). Rejeté : roadmap calendaire (`ROADMAP.md`, à archiver).
 
**ADR-013 — Alpha en deux phases (option C).** Ph.1 : usage réel + annotation inline → pool de requêtes réelles. Ph.2 : campagnes poolées → golden-set canonique. Rejeté : alpha monophase (usage seul, ou campagne d'emblée sans requêtes réelles).
 
**ADR-014 — Exhaustivité DILA = critère de publication.** Pas de v0 ni de beta. Ingestion progressive priorisée par valeur pour les experts (cf. ADR-003).
 
**ADR-015 — Association entre beta et publication.** Structure associative (positionnement « commun numérique », service subventionné) créée avant l'ouverture publique ; déclenche les chantiers non techniques (statuts, IP, conformité — voir `INSTITUTIONNEL.md`).
 
**ADR-016 — Découplage récupération/génération + pertinence graduée.** Le moteur **source sans raisonner** ; les réponses générées sont destinées à disparaître. L'évaluation porte sur la récupération seule → problème IR classique (méthodologie TREC, outillage standard). Pertinence **graduée**, jamais binaire (précisée par ADR-005). Conséquence : contrat d'adapter unique `requête → liste ordonnée d'IDs (+ scores)`.
 
**ADR-017 — Évaluation en strates de pérennité (T2).** Quatre strates : invariants structurels · qrels citation-minées (avec garde-fou circularité) · métriques appariées relatives · qrels humaines. **Un seul golden-set** + harnais d'ablations + mini-sets diagnostiques. Le synthétique v0 est **relégué** (`origin: synthetic`), pas jeté.
 
**ADR-018 — Identité : ECLI primaire.** ECLI = identifiant stable primaire ; IDs internes DILA (JURITEXT…) = clés techniques de partition ; numéros métier (pourvoi, requête…) = fallback. ELI non retenu strictement. Invariant bloquant : **même ID inter-BDD** (Qdrant, Neo4j, MongoDB).
 
**ADR-019 — Rejet d'Akoma Ntoso comme format de travail.** Trop verbeux, trop permissif, mal adapté aux pipelines de retrieval. Ses distinctions ontologiques (FRBR, relations de citation typées) sont **conservées conceptuellement** et informent le modèle Neo4j (via P4, cf. ADR-001).
 
**ADR-020 — Architecture tri-base + P3 stateless/fail-fast.** MongoDB (texte intégral brut) · Neo4j (nœuds/arêtes typés — **références, pas de texte**) · Qdrant (embeddings + métadonnées, recherche hybride). P3 : **stateless** (pas d'historique serveur, seule la dernière question compte), **fail-fast** (pas de retry/fallback LLM).