# EXIGENCES v0 — Cahier des charges interne de la version en cours

> Spécification d'exigences **dérivée mécaniquement** des critères
> d'entrée/sortie v0 de `VERSIONS.md` et de la DoD du
> `CADRAGE_evaluation` (étendue jurisprudence). Audience : le porteur
> du programme. Ce document ne crée **aucun périmètre nouveau** : si
> une exigence ici contredit `VERSIONS.md`, c'est `VERSIONS.md` qui
> fait foi et le présent document qui se corrige.
>
> Format : exigence testable — *le système/programme doit… — vérifié
> par…* Chaque exigence porte un ID stable, référencé par le
> `BACKLOG.md`. Statuts au 18 juillet 2026, alignés `STATUS.md`.

## 1. Périmètre

**In** : socle data (LEGI + 5 bases jurisprudence, vague 1) ; harnais
d'évaluation (strates 1–3, ADR-017) ; baseline chiffrée reproductible.
**Out** (exclusions fermes v0) : applicatif web, experts, bases DILA
non jurisprudentielles, LLM générateur branché à l'évaluation.

## 2. Exigences P1 — Data

| ID | Exigence | Vérification | Source | Statut |
|---|---|---|---|---|
| E-P1-01 | Les 5 bases de jurisprudence (CASS, INCA, CAPP, JADE, CONSTIT) doivent être ingérées dans les trois BDD | Comptages d'ingestion archivés, cohérents entre sources DILA et bases cibles | ADR-002, ADR-003 | ✅ |
| E-P1-02 | Chaque décision de jurisprudence doit porter une identité canonique (ECLI primaire, ID DILA en partition, numéro métier en fallback) **cohérente entre MongoDB, Neo4j et Qdrant** | Script de vérification croisée sur les 3 BDD : 0 divergence d'identité sur un échantillon exhaustif ; rapport versionné | ADR-018 | 🔶 |
| E-P1-03 | LEGI doit exposer un `doc_id` stable au niveau article, invariant entre ré-ingestions | Test de ré-ingestion : diff des `doc_id` vide sur corpus témoin | ADR-004 | 🔶 |
| E-P1-04 | Le graphe Neo4j doit modéliser les citations entre décisions avec des relations typées, exploitables comme source de qrels | Requête Cypher extrayant les paires (décision citante, décision citée) ; volumétrie archivée | ADR-017 (strate 2) | 🔶 |

## 3. Exigences P2 — Évaluation

| ID | Exigence | Vérification | Source | Statut |
|---|---|---|---|---|
| E-P2-01 | Un adapter baseline doit interroger la configuration de récupération courante et produire des runs au format arrêté | Run produit de bout en bout sur le golden-set v1, conforme au schéma ADR-008 | ADR-008, ADR-016 | ⬜ |
| E-P2-02 | Le scorer doit calculer **nDCG@R** (métrique primaire) et les diagnostics MAP, R-Precision, Recall@2R, Doc-MRR, Doc-Recall@R | Tests unitaires du scorer contre valeurs de référence calculées indépendamment (ex. trec_eval) | ADR-007 | ⬜ |
| E-P2-03 | L'agrégation chunk→document doit suivre la règle arrêtée, appliquée identiquement au scoring et aux runs | Test unitaire d'agrégation ; aucune métrique calculée au niveau chunk | ADR-006 | ⬜ |
| E-P2-04 | Les invariants structurels (strate 1) doivent être vérifiables sans annotation | Suite de tests strate 1 exécutable en CI, verte sur la baseline | ADR-017 | ⬜ |
| E-P2-05 | Des qrels citation-minées (strate 2) doivent être générées depuis le graphe de citations | Fichier qrels versionné, format ADR-008, volumétrie et méthode documentées | ADR-017 | ⬜ |
| E-P2-06 | Un golden-set v1 synthétique solo doit être figé et versionné, avec guide d'annotation et échelle de grades 0–3 | Fichier golden-set + guide versionnés, hash de gel consigné | ADR-005, ADR-017 | ⬜ |
| E-P2-07 | Le golden-set doit être stratifié selon les 4 types d'action | Champ type d'action présent sur 100 % des requêtes ; les 4 strates non vides | ADR-009 | ⬜ |
| E-P2-08 | Au moins un set diagnostique **graph-hop** doit exister | Set versionné ; requêtes nécessitant ≥ 1 traversée de citation documentées comme telles | ADR-017 | ⬜ |
| E-P2-09 | La comparaison de deux configurations doit passer par un test statistique apparié | Test implémenté ; sortie : différence, p-value, intervalle ; démonstration sur deux runs | ADR-007 | ⬜ |
| E-P2-10 | La baseline doit être **chiffrée et reproductible** : deux exécutions au couple de configurations **`(W, R)` identique** — `W` = workflow d'ingestion (normalisation/chunking/embedding), `R` = runtime de récupération — produisent les mêmes métriques. Le **fingerprint de `W`** est tracé dans l'artefact de run et vérifié contre le pointeur de collection publié | Double run archivé, diff des métriques nul ; fingerprint de `W` consigné et concordant | `CADRAGE_evaluation` DoD, ADR-026, ADR-027 | ⬜ |

## 4. Exigences transverses

| ID | Exigence | Vérification | Source | Statut |
|---|---|---|---|---|
| E-T-01 | Le harnais P2 doit être découplé de la génération : aucune dépendance à un LLM générateur | Revue du code du harnais : périmètre récupération seule | ADR-016 | ⬜ |
| E-T-02 | Tout artefact d'évaluation (qrels, runs, golden-sets) doit être versionné et rejouable | Artefacts sous contrôle de version ; procédure de rejeu documentée | ADR-008 | ⬜ |

## 5. Sortie de version

La v0 est close quand **toutes les exigences ci-dessus sont ✅**,
preuves à l'appui — constat consigné par mini-ADR de clôture
(`PILOTAGE.md` §3). Toute exigence invérifiable ou obsolète est
révisée par ADR, jamais contournée.

## 6. Traçabilité

Chaque item du `BACKLOG.md` référence l'exigence qu'il sert. Une
exigence sans item alors qu'elle n'est pas ✅ = trou de backlog ; un
item sans exigence = hors périmètre v0 (à différer ou signe qu'une
exigence manque, cf. `PILOTAGE.md` §2).
