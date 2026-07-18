# Document de cadrage d'audit — Programme « Moteur de recherche »

| | |
|---|---|
| **Portefeuille** | Murphy (entité / future association) |
| **Programme audité** | Moteur de recherche (projets P1 Data · P2 Évaluation · P3 Applicatif) |
| **Cible de référence** | v0 « Mesurable » |
| **Type de document** | Cadrage d'audit / Termes de référence (*audit engagement plan*) |
| **Référentiel méthodologique** | ISO 19011:2018 |
| **Version** | 0.2 (remplace la 0.1, rédigée avant lecture du corpus `docs/`) |
| **Date** | 2026-07-17 |
| **Auteur / auditeur** | Nicolas Moutou |
| **Statut** | À valider |
| **Documents sources** | `PROGRAM.md`, `Définition des versions.md`, `CADRAGE_evaluation_recuperation.md`, `ADR registre.md` (001–020), `STATUS.md`, `CADRAGE_demarche.md` |

> **Objet.** Ce document ne contient aucun constat. Il définit **ce qui sera audité, contre quels critères et par quelle méthode**, afin de mesurer l'écart entre l'état réel du programme et la v0 déjà définie. Les constats vivront dans un *rapport d'audit* distinct.

---

## 1. Contexte et enjeux

Murphy est un **programme** — non un projet — porté par une entité (bientôt une association). Il se décompose en trois projets opérationnels interdépendants, plus un volet doctoral tenu **hors** du programme opérationnel :

- **P1 — Data** : ingestion des bases DILA, modèle de données tri-base (MongoDB / Neo4j / Qdrant), **identité canonique stable inter-BDD**. *LEGI fait, jurisprudence en cours.*
- **P2 — Évaluation** : harnais IR agnostique (récupération seule), golden-sets stratifiés, outil d'annotation. *Cadré, non implémenté.*
- **P3 — Applicatif** : service web (moteur sourcé + annotation). *MVP RAG existant, en pause.*
- **P4 — Ontologie** (doctoral) : **hors périmètre** de cet audit — relève du programme « recherche scientifique » (ADR-001).

Les versions sont définies par **capacités mesurables**, jamais par calendrier. La **v0 « Mesurable »** est déjà **définie et tranchée** : elle vise un socle data (P1) + un harnais d'évaluation (P2) permettant de mesurer et comparer objectivement les configurations de récupération. Sa *Definition of Done* est fixée (`CADRAGE_evaluation` §10, `PROGRAM` §3).

**L'audit ne définit donc pas la v0** — elle l'est déjà — **et ne produit pas d'ADR** — le registre 001–020 existe. Sa finalité est plus étroite et plus factuelle : établir, preuve à l'appui, **où en est réellement le code par rapport à la DoD v0**, et en déduire le delta. Ce delta devient le backlog du dernier incrément vers v0.

## 2. Finalité et objectifs

**Finalité.** Produire un état des lieux factuel, coté et tracé du programme, mesuré contre la DoD v0, pour arrêter le reste-à-faire jusqu'à l'atteinte de v0.

Trois questions, dans cet ordre :

1. **État réel** — Quels éléments de la DoD v0 sont effectivement et vérifiablement en place (code, données, BDD) ?
2. **Écart (delta)** — Quels items de la DoD manquent ou sont incomplets ?
3. **Conformité** — Le code réalisé est-il conforme aux décisions actées (ADR 001–020) et aux invariants ?

Hors finalité : (re)définir la v0, produire des ADR rétrospectifs, juger la pertinence scientifique de P4, ou conclure sur la conformité juridique (RGPD) — laquelle relève du volet institutionnel, déclenché plus tard.

## 3. Objet et périmètre

**Objet audité.** Les projets P1, P2 et P3 dans leur état de réalisation au moment de l'audit.

**Inclus :**

- **P1** — ingestion des 5 bases jurisprudentielles (CASS, INCA, CAPP, JADE, CONSTIT — ADR-002) + LEGI ; modèle tri-base ; **couche d'identité canonique inter-BDD** (invariant bloquant, ADR-018).
- **P2** — état d'implémentation du harnais d'évaluation au regard de sa DoD.
- **P3** — inventaire de l'existant (MVP RAG), **noté comme hors DoD v0** : son état ne conditionne pas v0 mais doit être connu (il conditionne l'alpha).

**Exclus :**

- **P4 — Ontologie** (programme recherche scientifique).
- Le **volet institutionnel** (création d'association, statuts, IP, modèle économique — `INSTITUTIONNEL.md`).
- La **conclusion de conformité** RGPD/RGAA/RGESN : l'audit peut *relever* un état, il ne *statue* pas (critère de publication, pas de v0).
- Les capacités des versions **postérieures à v0** (annotation experte, campagnes poolées, A/B, auth) — sauf mention d'un prérequis déjà présent.

**Borne temporelle.** L'audit porte sur un **instantané de référence** (commit / état des BDD) à figer au lancement et à citer dans le rapport.

## 4. Critères d'audit (référentiels)

Le **critère central** est la DoD v0 elle-même ; les référentiels externes ne servent qu'à qualifier la *santé* de ce qui existe.

| Critère | Source | Ce qu'il évalue |
|---|---|---|
| **DoD v0** (critère principal) | `CADRAGE_evaluation` §10, `PROGRAM` §3 | Complétude des livrables v0 : identité canonique vérifiée sur 3 BDD · adapter baseline · golden-set v1 figé/versionné · scorer + diagnostics · test apparié · set graph-hop · baseline reproductible. |
| **Invariant d'identité canonique** | ADR-018, `CADRAGE_evaluation` §2 | Un même chunk/doc porte le **même ID** dans Qdrant, Neo4j et MongoDB. *Sans lui, ni v0 ni évaluation agnostique.* |
| **Métriques** | ADR-007 | **nDCG@R** (coupe adaptative, rejet des k fixes) + diagnostics (MAP, R-Precision, Recall@2R, Doc-MRR, Doc-Recall@R). |
| **Stratification** | ADR-009 | 4 types d'action mesurés séparément : `texte_applicable`, `jurisprudence_sur_question`, `known_item`, `graph_hop`. |
| **Conformité décisionnelle** | ADR 001–020 | Le code réalisé respecte-t-il les décisions actées ? |
| **Qualité du harnais** | ISO 25010 + `CADRAGE_evaluation` (note « code parfait ») | Correct, **reproductible**, golden-set stable, déterminisme (IDs stables, runs immuables, seeds figées). |
| **Données** | DAMA-DMBOK / FAIR | Qualité, complétude, déterminisme, intégrité des liens (strate 1 de l'évaluation). |

> **Attention — dérive documentaire à contrôler, pas à présumer vraie.** `PROGRAM` §3 mentionne encore « nDCG@k » alors qu'ADR-007 rejette les k fixes au profit de nDCG@R : c'est ADR-007 qui fait foi. L'audit prend la **décision actée** comme critère, non la formulation obsolète.

## 5. Axes d'investigation

Les axes suivent la structure réelle du programme (P1/P2/P3) plus deux axes transverses. Chaque axe précise objectif, questions-clés et preuves attendues.

### A1 — P1 Data : ingestion & modèle

*Objectif :* établir ce qui est réellement ingéré et modélisé.

- Les 5 bases jurisprudentielles sont-elles effectivement ingérées (et non « en cours ») ? Volumétrie réelle par base ?
- Les taux de remplissage réels correspondent-ils aux schémas déclarés (*schéma déclaré ≠ remplissage réel*) ? Le typage documentaire multi-champs (cas CASS/INCA à racine commune) est-il correct ?
- Le `doc_id` canonique est-il stable au niveau exigé par ADR-004 (décision/ECLI en juris, **article** pour LEGI — point signalé « à vérifier côté pipeline LEGI ») ?

*Preuves :* comptages sur BDD, échantillons XML, statistiques de remplissage, code du pipeline.

### A2 — P2 Évaluation : harnais IR

*Objectif :* mesurer l'écart entre le harnais réel et sa DoD (projet « cadré, non implémenté » — c'est vraisemblablement ici que se concentre le delta v0).

Item par item de la DoD :

- Adapter baseline (`requête → liste ordonnée d'IDs + scores`) implémenté pour ≥1 config ?
- Golden-set v1 figé et versionné (corpus + topics stratifiés + qrels gradués, pooling + amorçage citations **relu**, garde-fou circularité) ?
- Scorer produisant nDCG@R + diagnostics, **par requête** et agrégés ?
- Test statistique apparié branché ?
- ≥1 set diagnostique graph-hop opérationnel ?
- Baseline chiffrée et **reproductible** (runs immuables, seeds figées) ?

*Preuves :* code du harnais, fichiers qrels/runs JSONL (ADR-008), rapport de baseline reproductible.

### A3 — P3 Applicatif : inventaire (hors DoD v0)

*Objectif :* connaître l'état du MVP sans le faire peser sur v0.

- Le chemin RAG (embedding → retrieval → contexte → réponse streamée + sources) est-il opérationnel, conformément à `STATUS.md` ?
- Neo4j est-il câblé ou seulement provisionné ? (impact direct sur `graph_hop` et l'augmentation graphe).
- Couverture de tests réelle vs seuils déclarés ?

*Preuves :* dépôt `backend/`/`frontend/`, health checks, suite de tests.

### A4 — Transverse : identité canonique inter-BDD

*Objectif :* vérifier empiriquement l'**invariant bloquant** (ADR-018) — le point le plus déterminant de tout l'audit.

- Un même chunk/document porte-t-il réellement le **même ID** dans Qdrant, Neo4j et MongoDB ?
- Compte tenu de `STATUS.md` (« Neo4j provisionné, non câblé »), l'identité est-elle *vraiment* vérifiée sur les **3** BDD, ou seulement 2 ?

*Preuves :* requêtes croisées sur les trois BDD sur un échantillon d'IDs, code de génération des IDs canoniques.

### A5 — Transverse : conformité ADR & cohérence documentaire

*Objectif :* mesurer l'écart entre décisions actées, documentation et code.

- Le code est-il conforme aux ADR (notamment 004, 006, 007, 008, 018, 020) ?
- Les incohérences connues sont-elles isolées : `PROGRAM` §3 « nDCG@k » vs ADR-007 ; `Overview_des_datasets`/`BETA` « jurisprudence hors scope » (caduque) ; `ROADMAP.md` à archiver (chantier 7) ?
- Les décisions **ouvertes** (⬜ `PROGRAM` §6) restent-elles bien ouvertes, ou ont-elles été tranchées implicitement dans le code sans ADR ?

*Preuves :* revue croisée docs ↔ ADR ↔ code.

## 6. Méthodologie de collecte des preuves

### 6.1 Méthodes

Revue documentaire · revue de code (inspection statique de P1/P2/P3) · inspection des données (comptages, remplissage réel, requêtes inter-BDD) · tests de reproductibilité (rejeu d'un traitement / d'une baseline sur échantillon).

### 6.2 Échantillonnage

Échantillonnage **raisonné** quand l'exhaustivité est impraticable : au moins un échantillon par base DILA et par type documentaire distinct (attention au partage de racine CASS/INCA). Taille et sélection consignées dans le rapport.

### 6.3 Preuve suffisante

Une preuve est suffisante si elle est **vérifiable** (rattachée à un artefact réexaminable : fichier, requête, commit, sortie de test) et **reproductible**. Une affirmation reposant sur la mémoire, l'intention, ou un travail « prévu mais non réalisé » n'est pas une preuve.

### 6.4 Règle cardinale et biais d'auto-audit

L'auditeur est le concepteur du programme : l'**indépendance** manque structurellement. Mesure compensatoire, non négociable :

> **Aucun constat n'est inscrit sans artefact vérifiable à l'appui.**

En complément : constats formulés en termes factuels (ce qui est / n'est pas), jamais d'intention ; tout artefact référencé (chemin, commit, requête) ; distinction explicite **Fait / Prévu / Supposé** dans chaque fiche. La dérive documentaire (docs plus avancés que le code) est précisément ce que cette règle neutralise : **le code fait foi, pas la doc.**

## 7. Livrables de l'audit

1. **Rapport d'audit** — synthèse, constats cotés par axe, conclusions.
2. **Registre des constats** — un enregistrement par constat (modèle en annexe B).
3. **Delta v0** — liste priorisée des écarts DoD → devient le backlog de l'incrément final vers v0.
4. **Liste des écarts code ↔ ADR** — et non des ADR rétrospectifs (le registre existe) : points où le code diverge d'une décision actée, ou décision ouverte tranchée sans ADR.

## 8. Cotation des constats

Chaque constat reçoit un **niveau** et une **gravité**, plus un indicateur de **périmètre v0**.

| Niveau | Signification |
|---|---|
| Conforme | Existant vérifié, cohérent avec la DoD et les ADR. |
| Écart mineur | Présent mais incomplet ; ne bloque pas v0. |
| Écart majeur | Manque compromettant l'atteinte de v0. |
| Non couvert | Élément attendu absent ou non démontrable par une preuve. |

| Gravité | Effet sur v0 |
|---|---|
| Bloquant | v0 impossible sans traitement (typiquement A4, identité canonique). |
| Élevé | v0 dégradée ou risquée. |
| Modéré | À traiter, sans blocage. |
| Faible | Amélioration opportuniste. |

**Indicateur de périmètre :** `v0` (gate la version) ou `hors-v0` (inventaire, ex. items P3) — pour ne pas gonfler artificiellement le delta v0 avec de l'existant P3 déjà avancé mais non requis.

## 9. Risques, limites et organisation

### 9.1 Risques et limites

- **Biais d'auto-évaluation** — traité par la règle *evidence-based* (§6.4) ; limite principale.
- **Dérive documentaire** — plusieurs docs sont en avance ou en retard sur le code (§4, §A5) ; l'audit statue sur le code, la doc n'est qu'une piste.
- **Accès et volumétrie** — inspection XML exhaustive impraticable ; échantillonnage raisonné assumé (§6.2).
- *Note :* la **cible v0 est fixe** (tranchée) ; contrairement à la v0.1 de ce cadrage, il n'y a plus de risque de « cible mouvante ».

### 9.2 Organisation

| Rôle | Titulaire |
|---|---|
| Auditeur | Nicolas Moutou |
| Commanditaire | Programme Moteur de recherche (Murphy) |
| Validation du cadrage | Nicolas Moutou |

*Séquence recommandée :* validation du présent cadrage → gel de l'instantané → **A4 en premier** (identité canonique, invariant bloquant) → A1 → A2 → A3 → A5 → rédaction du rapport et du delta.

---

## Annexe A — Glossaire (aligné ISO 19011)

- **Critères d'audit** — référentiels servant de comparaison pour établir les preuves (ici : DoD v0, ADR, invariants).
- **Preuve d'audit** — enregistrement ou fait vérifiable et pertinent au regard des critères.
- **Constat d'audit** — résultat de l'évaluation des preuves par rapport aux critères.
- **Champ de l'audit** — étendue et limites (objet, périmètre, borne).
- **Delta v0** — écart priorisé entre l'existant audité et la DoD v0.

## Annexe B — Modèle de fiche de constat

```
ID du constat        : A?-NN
Axe                  : A1 (P1) | A2 (P2) | A3 (P3) | A4 (identité) | A5 (ADR/doc)
Énoncé (factuel)     : …
Preuve(s)            : chemin / commit / requête / sortie de test
Critère de référence : DoD v0 | ADR-0xx | invariant identité | ISO 25010 | DAMA/FAIR
Niveau               : Conforme | Écart mineur | Écart majeur | Non couvert
Gravité              : Bloquant | Élevé | Modéré | Faible
Périmètre            : v0 | hors-v0
Nature               : Fait | Prévu | Supposé
Conséquence pour v0  : …
Action proposée      : …
```
