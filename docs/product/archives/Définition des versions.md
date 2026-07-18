# Chantier 3 — Définition des versions
 
**Principe directeur :** les versions sont définies par des **capacités mesurables**, jamais par un calendrier. Aucune date.
 
**Progression :** v0 → alpha (2 phases) → beta → association → publication.
 
## v0 — « Mesurable » ✅
 
**Objectif :** disposer d'un socle data + un harnais d'évaluation permettant de mesurer et comparer objectivement les configurations de récupération.
 
| | |
|--|--|
| **In** | LEGI (fait) + les **5 bases de jurisprudence** (CASS, INCA, CAPP, JADE, CONSTIT — ADR‑2) ingérées avec identité canonique **vérifiée sur les 3 BDD** ; harnais d'évaluation (strates 1–3 + qrels citation‑minées + set synthétique solo) ; baseline chiffrée et reproductible |
| **Out** | Applicatif web, experts, bases DILA non‑jurisprudentielles, LLM générateur branché à l'évaluation |
| **Critères d'entrée** | Pipeline LEGI stable ; modèle de données tri‑base arrêté |
| **Critères de sortie** | DoD du `CADRAGE_evaluation` (étendu jurisprudence) : identité canonique vérifiée · adapter baseline implémenté · golden‑set v1 figé et versionné · scorer **nDCG@R** (+ diagnostics MAP, R‑Precision, Recall@2R, Doc‑MRR, Doc‑Recall@R — ADR‑7) · test statistique apparié · ≥1 set diagnostique graph‑hop · stratification en 4 types d'action (`texte_applicable`, `jurisprudence_sur_question`, `known_item`, `graph_hop` — ADR‑9) · baseline reproductible |
 
## Alpha phase 1 — « Usage & requêtes réelles » ✅
 
**Objectif :** mettre Murphy entre les mains d'experts pour recueillir le besoin et générer un pool de **requêtes réelles** + notations au fil de l'eau.
 
| | |
|--|--|
| **In** | Réveil de P3 (moteur : sources cliquables + excerpt + score) ; **mode annotation inline** (cascade q1→q3 dérivant les grades 0–3, `origin: inline` — ADR‑5/10) ; accès restreint ; déploiement ; authentification minimale |
| **Out** | Mode campagne poolée (ph.2), A/B, métriques beta complètes |
| **Critères d'entrée** | v0 atteinte (baseline mesurable) |
| **Critères de sortie** | Pool de requêtes réelles constitué ; besoins experts formalisés ; notations inline collectées |
 
## Alpha phase 2 — « Qrels canoniques » ✅
 
**Objectif :** produire le golden‑set **canonique** via campagnes d'annotation poolées sur les requêtes réelles de la ph.1.
 
| | |
|--|--|
| **In** | **Mode campagne** — même composant de jugement que l'inline (ADR‑10), orchestré en file poolée : guide d'annotation affiché, calibration inter‑experts, progression trackée |
| **Out** | Beta (A/B, feedback produit) |
| **Critères d'entrée** | Pool de requêtes réelles disponible |
| **Critères de sortie** | Golden‑set v2 (expert, poolé, calibré) figé et versionné ; baseline **re‑mesurée** sur qrels expertes |
 
## Beta — « Valeur d'usage » 🔶
 
**Objectif :** valider la valeur et l'UX auprès de vrais utilisateurs. Reprend l'esprit de `BETA.md` (**gelé** — à réécrire à la lumière des retours alpha) : A/B aveugle prompt/retrieval, feedback utile/pas utile, métriques sans contenu, OAuth 2.0, streaming. Périmètre données : extension à la **vague 2** DILA (voir séquençage).
 
## Création de l'association ✅ (jalon organisationnel)
 
Se situe **entre beta et publication**. Formalise la structure porteuse avant l'ouverture publique. Déclenche les chantiers non techniques (statuts, IP, modèle d'exploitation, conformité renforcée — cf. `INSTITUTIONNEL.md`).
 
## Publication — « Exhaustivité DILA » ✅
 
**Exhaustivité DILA = critère de publication**, pas de v0. Toutes les bases DILA ingérées ; robustesse et scaling ; conformité (RGPD/RGAA/RGESN) ; modèle d'exploitation durable.
 
## Séquençage d'ingestion DILA (ADR‑3)
 
Ingestion **progressive**, priorisée par valeur pour les experts.
 
| Vague | Bases | Version cible |
|-------|-------|---------------|
| Faite | LEGI | — |
| 1 | CASS, INCA, CAPP, JADE, CONSTIT | v0 |
| 2 | JORF + base(s) à déterminer sur retours alpha (candidates : KALI, CIRCULAIRES) | beta |
| 3 | Solde DILA (DOLE, CIRCULAIRES, CNIL, débats/QR parlementaires, SARDE, protocoles…) | publication |
 
Le choix différé de la vague 2 est assumé, cohérent avec le principe de versions par capacités mesurables.
 
---
 
Il reste deux points à statut non‑final : la **beta** (🔶, à réécrire après l'alpha) et le contenu exact de la **vague 2** (délibérément différé). Tout le reste est tranché.
 
Voulez-vous que je fige ce livrable dans un fichier `VERSIONS.md` (ou en mise à jour propre de `PROGRAM.md` §3–4) que vous pourrez récupérer ?
 
Sources : PROGRAM.md (§3, §4), Synthèse de session.md (ADR‑2, 3, 5, 7, 9, 10), CADRAGE_demarche.md (§3)