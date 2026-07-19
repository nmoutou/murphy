# Démarche de cadrage — Murphy / programme
 
> Document de méthode. Décrit **le travail de cadrage à mener**, son ordre de
> dépendance, et ce qui relève de l'arbitrage vs de la rédaction.
> Il ne contient pas les décisions elles-mêmes : celles-ci vivent dans
> `VISION.md`, `PROGRAM.md` et le registre `ADR/`.
 
## Positionnement
 
Le cadrage porte sur **l'écosystème complet**, structuré en programme à trois
projets interdépendants (Data, Évaluation, Applicatif), plus un volet doctoral
(Ontologie) dont le rattachement reste à confirmer. Objectif fédérateur :
une **alpha avec des experts en droit** dans la boucle (recueil du besoin +
production de golden-sets).
 
Horizon de programme : **publication à l'échelle nationale** d'un service
**subventionné, porté par une structure associative** (positionnement « commun
numérique »). Cet horizon ne modifie pas le programme technique (versions par
capacités mesurables) mais impose un huitième chantier de cadrage, à audience
**externe** (financeurs, administrations), là où les chantiers 1–7 ont pour
audience le porteur du programme.
 
## Les huit chantiers de cadrage
 
### 1. Formaliser les invariants → `VISION.md`
Mission et principes non négociables : sourcer sans raisonner, exhaustivité
visée, identité canonique, découplage récupération / génération. Court, quasi
définitif. *Rédaction.*
 
### 2. Structurer le programme → `PROGRAM.md`
- Définir les 3 projets, leurs frontières et surtout leurs **interfaces**
  (qui fournit quoi à qui : IDs canoniques, schémas de payload, contrat
  d'adapter).
- Statuer sur le volet Ontologie (P4) : hors programme opérationnel avec
  interfaces déclarées, ou intégré. *Cœur — arbitrage.*
### 3. Définir les versions
Pour chaque version (v0, alpha ph.1, alpha ph.2, beta, association,
publication) : objectif en une phrase, périmètre in/out explicite, **critères
d'entrée et de sortie mesurables**. Y intégrer le séquençage d'ingestion DILA
(quelle base à quelle version). *Cœur — arbitrage.*
 
### 4. Trancher les décisions ouvertes bloquantes
Reprendre le §9 du `CADRAGE_evaluation` (unité « document », échelle de
pertinence, règle d'agrégation chunk→document, valeurs de k, formats
qrels/runs) + les décisions programme (séquence DILA, périmètre P4). Chacune
devient un ADR. *Cœur — arbitrage.*
 
### 5. Consolider le registre de décisions → `ADR/`
Rétro-documenter les ADR **implicites** déjà pris : ECLI comme identifiant
primaire, rejet d'Akoma Ntoso, stateless, fail-fast, pertinence graduée,
option C (alpha en deux phases), stratification de l'évaluation… Format
minimal : contexte, décision, alternatives rejetées, conséquences.
*Rédaction.*
 
### 6. Définir le processus de pilotage
Rituel de **revue bimensuelle** (checklist : STATUS à jour, décisions → ADR,
backlog repriorisé, log de 10 lignes max), règles de gestion du backlog,
critère de déclenchement d'un changement de version. *Rédaction.*
 
### 7. Nettoyer l'existant
Archiver `ROADMAP.md` et `BETA.md` (mention « pré-alpha, gelé »), aligner
`STATUS.md` sur la structure par projet. *Rédaction.*
 
### 8. Cadrer le volet institutionnel → `INSTITUTIONNEL.md`
Seul chantier à **audience externe** (financeurs, administrations, futurs
membres). Détaille le jalon « Création association » de `PROGRAM.md` §3,
aujourd'hui réduit à une ligne, et contraint en retour les critères de sortie
des versions beta et publication (chantier 3). Quatre sous-volets :
 
- **Structure juridique** : statuts de l'association, gouvernance, propriété
  intellectuelle (code, données dérivées, golden-sets), positionnement
  « commun numérique », politique de licence (Licence Ouverte Etalab pour les
  données — cohérente avec les sources DILA ; licence du code à trancher → ADR).
- **Modèle économique** : coûts d'exploitation chiffrés (GPU/TEI, hébergement,
  LLM, maintenance), plan de financement, cartographie des guichets de
  subvention (appels à communs, fondations, financements publics du numérique
  d'intérêt général), soutenabilité hors subvention.
- **Conformité réglementaire** : registre des traitements + AIPD (RGPD —
  formalise les contraintes déjà actées dans `BETA.md` : E2EE, aucune analyse
  de contenu), RGAA (accessibilité — exigée pour un service à vocation
  nationale et par la plupart des financeurs publics), RGESN (écoconception).
- **Dossier de présentation** : argumentaire d'impact, diagramme de contexte
  (C4 niveau 1 : Murphy dans l'écosystème DILA / usagers / financeurs),
  **KPIs d'impact** (usagers actifs, requêtes servies, couverture du corpus
  DILA, publics touchés) — distincts des métriques IR internes, qui restent du
  ressort de P2.
Déclencheur opérationnel : le jalon « association » (entre beta et
publication). Le **cadrage**, lui, démarre dès maintenant : ses exigences
(conformité, KPIs d'impact) sont des critères d'entrée de la publication et
doivent être connues avant de figer les versions (chantier 3).
*Arbitrage + rédaction.*
 
## Ordre de dépendance
 
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
 
6. PILOTAGE   et   7. NETTOYAGE : transverses, à faire en parallèle.
```
 
Les versions (3) ne peuvent être finalisées sans les décisions (4), qui
s'appuient elles-mêmes sur les frontières de projets (2). Le chantier 8 dépend
de la vision (1) et **alimente** les versions (3) : ses exigences externes
(RGPD/RGAA/RGESN, KPIs d'impact) deviennent des critères d'entrée de la beta
et de la publication. D'où l'ordre 1 → 8.
 
## Répartition de l'effort
 
| Chantier | Nature | Charge |
|----------|--------|--------|
| 1 Vision | rédaction | faible |
| 2 Programme | **arbitrage** | moyenne |
| 3 Versions | **arbitrage** | moyenne |
| 4 Décisions ouvertes | **arbitrage** | forte |
| 5 Registre ADR | rédaction | moyenne |
| 6 Pilotage | rédaction | faible |
| 7 Nettoyage | rédaction | faible |
| 8 Institutionnel | **arbitrage** + rédaction | forte |
 
Le cœur (2, 3, 4, 8) demande vos arbitrages ; le reste est surtout de la mise
en forme. Le 8 se distingue : ses arbitrages (statuts, licence, modèle
économique) engagent des tiers et sont plus coûteux à réviser que les
arbitrages techniques.