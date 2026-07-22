# VERSIONS — Définition des versions (chantier 3)

> Livrable du chantier 3, figé après le chantier 4 (17 juillet 2026).
> **Principe directeur** (ADR-012) : les versions sont définies par des
> **capacités mesurables**, jamais par un calendrier. Aucune date.
>
> Progression : **v0 → alpha (2 phases) → beta → association →
> publication**.

---

## v0 — « Mesurable » ✅

**Objectif** : disposer d'un socle data + un harnais d'évaluation
permettant de mesurer et comparer objectivement les configurations de
récupération.

| | |
|--|--|
| **In** | LEGI (fait) + les **5 bases de jurisprudence** (CASS, INCA, CAPP, JADE, CONSTIT — ADR-002) ingérées avec identité canonique **vérifiée sur les 3 BDD** (ADR-018) ; harnais d'évaluation (strates 1–3 + diagnostic de co-citation + set synthétique solo — ADR-017, amendé ADR-029) ; baseline chiffrée et reproductible |
| **Out** | Applicatif web, experts, bases DILA non jurisprudentielles, LLM générateur branché à l'évaluation |
| **Critères d'entrée** | Pipeline LEGI stable ; modèle de données tri-base arrêté |
| **Critères de sortie** | DoD du `CADRAGE_evaluation` (étendu jurisprudence) : identité canonique vérifiée · adapter baseline implémenté · golden-set v1 figé et versionné · scorer **nDCG@R** + diagnostics MAP, R-Precision, Recall@2R, Doc-MRR, Doc-Recall@R (ADR-007) · test statistique apparié · ≥ 1 set diagnostique graph-hop · stratification en 4 types d'action (ADR-009) · baseline reproductible |

## Alpha phase 1 — « Usage & requêtes réelles » ✅ (ADR-013)

**Objectif** : mettre Murphy entre les mains d'experts pour recueillir
le besoin et générer un pool de **requêtes réelles** + notations au fil
de l'eau.

| | |
|--|--|
| **In** | Réveil de P3 (moteur : sources cliquables + excerpt + score) ; **mode annotation inline** (cascade q1→q3 dérivant les grades 0–3, `origin: inline` — ADR-005/010) ; accès restreint ; déploiement ; authentification minimale |
| **Out** | Mode campagne poolée (ph.2), A/B, métriques beta complètes |
| **Critères d'entrée** | v0 atteinte (baseline mesurable) |
| **Critères de sortie** | Pool de requêtes réelles constitué ; besoins experts formalisés ; notations inline collectées |

## Alpha phase 2 — « Qrels canoniques » ✅ (ADR-013)

**Objectif** : produire le golden-set **canonique** via campagnes
d'annotation poolées sur les requêtes réelles de la ph.1.

| | |
|--|--|
| **In** | **Mode campagne** — même composant de jugement que l'inline (ADR-010), orchestré en file poolée : guide d'annotation affiché, calibration inter-experts, progression trackée |
| **Out** | Beta (A/B, feedback produit) |
| **Critères d'entrée** | Pool de requêtes réelles disponible |
| **Critères de sortie** | Golden-set v2 (expert, poolé, calibré) figé et versionné ; baseline **re-mesurée** sur qrels expertes |

## Beta — « Valeur d'usage » 🔶

**Objectif** : valider la valeur et l'UX auprès de vrais utilisateurs.
Reprend l'esprit de `archive/BETA.md` (**gelé** — à réécrire à la
lumière des retours alpha) : feedback utile/pas utile, métriques sans
contenu, OAuth 2.0, streaming. L'ADR-025 fixe le cadre de collecte :
deux environnements d'un même artefact (**public** sans aucune
collecte, **panel** opt-in avec télémétrie d'évaluation) et
**interleaving privilégié sur l'A/B** classique (différé à un volume
suffisant). Périmètre données : extension à la **vague 2** DILA
(ADR-003).

**Critères d'entrée** (à compléter par les exigences de conformité du
chantier 8, `INSTITUTIONNEL.md` §3) : environnements public/panel
opérationnels — même artefact, télémétrie par flag, contrat vérifiable
par test/CI — et **AIPD réalisée** (ADR-025).

## Création de l'association ✅ (jalon organisationnel — ADR-015)

Se situe **entre beta et publication**. Formalise la structure porteuse
avant l'ouverture publique. Déclenche les chantiers non techniques
(statuts, IP, modèle d'exploitation, conformité renforcée —
`INSTITUTIONNEL.md`).

## Publication — « Exhaustivité DILA » ✅ (ADR-014)

**Exhaustivité DILA = critère de publication**, pas de v0. Toutes les
bases DILA ingérées ; robustesse et scaling ; conformité
(RGPD/RGAA/RGESN — critères d'entrée issus du chantier 8) ; modèle
d'exploitation durable.

---

## Séquençage d'ingestion DILA (ADR-003)

Ingestion **progressive**, priorisée par valeur pour les experts.

| Vague | Bases | Version cible |
|-------|-------|---------------|
| Faite | LEGI | — |
| 1 (fait) | CASS, INCA, CAPP, JADE, CONSTIT | v0 |
| 2 | JORF + base(s) à déterminer sur retours alpha (candidates : KALI, CIRCULAIRES) | beta |
| 3 | Solde DILA (DOLE, CNIL, débats/QR parlementaires, SARDE, protocoles…) | publication |

---

## Statuts non finaux

Deux points restent délibérément ouverts : la **beta** (🔶, réécriture
après l'alpha) et le contenu exact de la **vague 2** (mini-ADR de
clôture à l'issue de l'alpha). Tout le reste est tranché.
