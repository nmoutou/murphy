# Démarche de cadrage — Murphy / programme

> Document de méthode. Décrit **le travail de cadrage à mener**, son ordre de
> dépendance, et ce qui relève de l'arbitrage vs de la rédaction.
> Il ne contient pas les décisions elles-mêmes : celles-ci vivent dans
> `VISION.md`, `PROGRAM.md`, `VERSIONS.md` et le registre `ADR/`.
>
> **État au 18 juillet 2026 : chantiers 1–7 clos. Seul le chantier 8
> reste ouvert** (arbitrages ADR-INST-01/02/03 + livrables 2–4).

## Positionnement

Le cadrage porte sur **l'écosystème complet**, structuré en programme à trois
projets interdépendants (Data, Évaluation, Applicatif). Objectif fédérateur :
une **alpha avec des experts en droit** dans la boucle (recueil du besoin +
production de golden-sets).

Horizon de programme : **publication à l'échelle nationale** d'un service
**subventionné, porté par une structure associative** (positionnement « commun
numérique »). Cet horizon ne modifie pas le programme technique (versions par
capacités mesurables) mais impose un huitième chantier de cadrage, à audience
**externe** (financeurs, administrations), là où les chantiers 1–7 ont pour
audience le porteur du programme.

## Les huit chantiers de cadrage

### 1. Formaliser les invariants → `VISION.md` — ✅ clos
Mission et principes non négociables : sourcer sans raisonner, exhaustivité
visée, identité canonique, découplage récupération / génération, respect de
l'usager. Court, quasi définitif. *Rédaction.*

### 2. Structurer le programme → `PROGRAM.md` — ✅ clos
Trois projets, frontières et **interfaces** contractualisées (IDs canoniques,
schémas de payload, contrat d'adapter). *Arbitrage.*

### 3. Définir les versions → `VERSIONS.md` — ✅ clos
Pour chaque version (v0, alpha ph.1, alpha ph.2, beta, association,
publication) : objectif, périmètre in/out, **critères d'entrée et de sortie
mesurables**, séquençage d'ingestion DILA (ADR-003). Restent 🔶 par
conception : la beta (réécriture post-alpha) et le contenu de la vague 2.
*Arbitrage.*

### 4. Trancher les décisions ouvertes bloquantes — ✅ clos (17 juillet 2026)
Dix décisions tranchées en session : ADR-001 à 010 (statut P4, périmètre
jurisprudentiel v0, séquençage DILA, unité document, échelle de pertinence,
agrégation, métriques nDCG@R, formats qrels/runs, types d'action, deux modes
de P3). *Arbitrage.*

### 5. Consolider le registre de décisions → `ADR/` — ✅ clos
ADR-001 à 010 rédigés + ADR-011 à 020 **rétro-documentés** (cadrage en
programme, versions par capacités, alpha en deux phases, exhaustivité =
publication, association, découplage, strates, ECLI, rejet d'Akoma Ntoso,
tri-base). Format : un fichier par ADR + `INDEX.md`. *Rédaction.*

### 6. Définir le processus de pilotage → `PILOTAGE.md` — ✅ clos
Revue bimensuelle avec checklist, règles de backlog, changement de version
par constat (mini-ADR de clôture), hygiène documentaire. *Rédaction.*

### 7. Nettoyer l'existant — ✅ clos
`ROADMAP.md` et `BETA.md` archivés avec bandeau (« pré-alpha, gelé ») ;
`STATUS.md` aligné sur la structure par projet ; mentions caduques
(« jurisprudence hors scope beta ») corrigées dans `Overview_des_datasets.md`
et `archive/BETA.md`. *Rédaction.*

### 8. Cadrer le volet institutionnel → `INSTITUTIONNEL.md` — 🟡 en cours
Seul chantier à **audience externe**. Squelette validé. Restent :

- **Arbitrages** : ADR-INST-01 (forme juridique : association 1901 / fonds de
  dotation / SCIC), ADR-INST-02 (licence du code), ADR-INST-03 (soutenabilité
  hors subvention), régime des golden-sets, niveau RGAA visé.
- **Livrables** : cadre de KPIs à quatre niveaux (§4.3), mapping conformité →
  critères d'entrée (§3.4), diagramme de contexte C4 niveau 1 (§4.2).

Ces exigences sont des critères d'entrée beta/publication : elles sont déjà
câblées dans `VERSIONS.md`, à préciser quand les arbitrages tomberont.
*Arbitrage + rédaction.*

## Ordre de dépendance (rappel)

```
1. VISION  ─►  2. PROGRAM (frontières)  ─►  3. VERSIONS  ─►  publication
     │                 │                        ▲   ▲
     │                 └──►  4. DÉCISIONS  ─────┘   │
     │                            │                 │
     │          5. REGISTRE ADR ◄─┘  (consolide 4 + l'implicite)
     │                                              │
     └─────►  8. INSTITUTIONNEL  ───────────────────┘
              (contraintes de conformité et d'impact
               = critères d'entrée beta / publication)

6. PILOTAGE   et   7. NETTOYAGE : transverses — faits.
```

## Suite

Le cadrage étant consolidé, le travail retourne à l'**exécution de la v0**
(critères de sortie dans `VERSIONS.md`), rythmée par la revue bimensuelle
(`PILOTAGE.md`). Le chantier 8 avance en parallèle, ses arbitrages n'étant
bloquants qu'à l'approche de la beta.
