# Golden-set RAG · Bases documentaires DILA

> ⚠️ **ARCHIVE — document historique, non normatif.** Conservé pour la
> traçabilité du raisonnement de conception (passages 1 et 2 de l'analyse
> statistique). **Repris et corrigé dans `docs/product/GOLDEN-SET.md`**, qui
> est le document normatif. En cas de contradiction avec un ADR, avec
> `EXIGENCES_v0.md` ou avec `GOLDEN-SET.md`, **ce document a tort.** Points
> périmés connus, à ne pas reprendre :
>
> - **§5 « second axe — 6 types de difficulté »** — **révoqué par ADR-030**.
>   L'axe difficulté est supprimé : étiqueter une requête *difficile*
>   enregistre une impression, non un fait, et l'étiquette absorbe la question
>   qu'elle prétend documenter. Les deux axes sont désormais une **intention**
>   par requête et une ou plusieurs **opérations** portées par l'arête
>   `(requête, source, cible)`. T1–T6 ne sont pas perdus mais mêlent quatre
>   natures d'objet distinctes — table de traduction en `GOLDEN-SET.md` §4.1.
> - **§6 dimensionnement `12 × 6 × 4 = 288`** — dérivation invalide sous
>   ADR-030 : le second facteur **n'est pas une partition des requêtes** (une
>   requête porte plusieurs opérations à la fois). Le calcul confond en outre
>   les **questions écrites** et les **questions jugées**, qui obéissent à des
>   contraintes différentes. Dérivation corrigée en `GOLDEN-SET.md` §7.
> - **§7 point 2, échelle « 3 = norme directement applicable / 2 =
>   jurisprudence d'application / 1 = contexte utile »** — remplacée par la
>   **cascade de trois tests binaires** q1/q2/q3 d'**ADR-005**, où l'échelle
>   par démarcations d'intensité est explicitement rejetée (arbitraire,
>   désaccords non localisables).
> - **§7 point 4, « recall@10, @20 et @50 »** — contraire à **ADR-007**, dont
>   le fondement est le **refus des coupes constantes** : la métrique primaire
>   est **nDCG@R**, à coupe adaptative au nombre de documents pertinents.
> - **§4 colonne « masse documentaire attendue » et §9 « point ouvert »** —
>   **sans objet**. La volumétrie DILA (D₂) est écartée comme entrée de
>   conception : dimensionner depuis le corpus laisserait l'ingestion définir
>   ce qu'on mesure. Le jeu se construit sur l'usage (D₃, approché par D₁
>   corrigé) et **précède** l'ingestion étendue, qu'il spécifie
>   (`GOLDEN-SET.md` §2 et §10). Le corpus ne revient qu'à un titre :
>   ordonnancer l'effort d'annotation.
> - **§8 étape 1, « mesurer l'accord inter-annotateurs »** — hors périmètre
>   v0 : le golden-set v1 est **synthétique solo** (E-P2-06, ADR-017 strate 4).
>   L'accord inter-annotateurs relève de l'alpha ph.2 et des campagnes poolées.
>
> Restent valides et repris : la **stratification uniforme + repondération a
> posteriori** (§1.1–1.2), les **trois distributions** D₁/D₂/D₃ (§2), les
> **12 strates** et leur table de correspondance bouclant sur le socle de
> 6 162 985 affaires (§4 et §4.1), le **matériau adversarial de polysémie**
> (§5.1), les **paires isosémantiques** (§6.1), la **strate-frontière** (§6.2),
> la **date pivot** (§7 point 1) et la **granularité document** (§7 point 3).

**Spécification de conception — strates et sous-strates validées**

| | |
|---|---|
| Objet | Jeu d'évaluation pour moteur de recherche RAG sur LEGI, JORF, CASS, INCA, JADE, KALI, CONSTIT, CNIL et bases associées |
| Date | 23 juillet 2026 |
| Statut | Strates et types de difficulté validés · paramètres de conception ouverts |
| Fondement statistique | Analyse du corpus RSJ 2025 · Chiffres clés 2025 · Chiffres clés JA 2025 (passage 1) |

---

## 1. Décisions de cadrage

Trois arbitrages structurants ont été tranchés en amont.

| Paramètre | Décision retenue |
|---|---|
| Cible de mesure | **Retrieval seul** — recall et précision sur les documents restitués, hors génération |
| Registre des requêtes | **Mixte, praticien et citoyen à parts égales** |
| Stratégie de couverture | **Stratifiée uniforme par matière** |

### 1.1 Conséquences de la stratification uniforme

Le tirage uniforme retire au volume contentieux son rôle de quota. Deux implications doivent être assumées explicitement :

1. **Le score global cesse d'estimer la performance en production.** Il devient un score de diagnostic, comparable d'une strate à l'autre mais non représentatif du trafic réel.
2. **La définition des strates devient la totalité du design.** Si l'on tire uniformément dans douze cases, ce sont les frontières des cases — et non les effectifs — qui déterminent ce qui est testé et ce qui reste hors du champ de mesure.

### 1.2 Repondération a posteriori

L'analyse volumétrique du passage 1 ne devient pas caduque : elle change de fonction. Les parts par matière constituent un **vecteur de repondération** applicable après mesure. Un jeu unique produit alors deux chiffres :

- un **score de diagnostic**, non pondéré, lisible strate par strate ;
- un **score d'estimation production**, obtenu en repondérant les scores de strate par les poids contentieux réels.

Les poids sont donnés au § 4.

---

## 2. Problématique directrice

> **Dans quelle mesure la structure du contentieux réel peut-elle servir de plan d'échantillonnage pour un golden-set interrogeant les bases DILA — et où faut-il s'en écarter délibérément ?**

Trois distributions coexistent et divergent fortement :

| Distribution | Nature | Biais propre |
|---|---|---|
| **D₁ — contentieux réel** | Volume d'affaires (mesuré au passage 1) | Dominé par les atteintes aux biens : 35,1 % du socle, dont 83 % sans auteur identifié, donc quasiment sans jurisprudence publiée |
| **D₂ — empreinte documentaire DILA** | Volume de documents interrogeables | LEGI largement orthogonal au volume contentieux ; JADE écrasé par le contentieux des étrangers ; CASS et INCA subissent le filtre de la cassation, qui surreprésente les matières à droit instable |
| **D₃ — questions réellement posées** | Besoin de décision des utilisateurs | Non observable a priori ; gouvernée par l'enjeu, non par la fréquence |

Échantillonner sur D₁ produirait un jeu qui teste massivement le vol simple et ignore le droit des étrangers. Échantillonner sur D₂ reproduirait les biais éditoriaux des bases. **C'est l'écart entre les trois qui est informatif**, et c'est ce que la stratification uniforme permet d'exploiter.

### Sous-questions opérationnelles

1. **Facteur de conversion** — pour chaque strate, quel rapport entre volume d'affaires et volume de documents interrogeables ? Où est-il extrême ?
2. **Angles morts** — quelles strates un échantillonnage volumétrique naïf laisserait-il non testées ?
3. **Ruptures terminologiques** — où le vocabulaire des nomenclatures officielles diverge-t-il de celui des bases ?

---

## 3. Pourquoi la partition du passage 1 ne peut pas servir de stratification

La nomenclature en 12 matières du passage 1 a été construite pour être exhaustive sur les **affaires**. Pour un RAG sur DILA, elle présente trois défauts rédhibitoires.

| Défaut | Illustration | Conséquence |
|---|---|---|
| **Absence de strate procédurale** | La procédure n'est le sujet d'aucune des cinq nomenclatures officielles du corpus. Elle est pourtant une part majeure des pourvois en cassation et du contentieux administratif : recevabilité, délais, référés, moyens d'ordre public. | Un pan entier de CASS, INCA et JADE non testé |
| **Absence de strate normative pure** | KALI, CONSTIT, CNIL, CIRCULAIRES n'ont aucun répondant dans la statistique des affaires. Masse documentaire considérable, empreinte contentieuse quasi nulle. | Bases entières hors golden-set |
| **Asymétrie volume / masse documentaire** | Atteintes aux biens : 35,1 % des affaires, presque aucune décision publiée. Contentieux des étrangers : 3,0 % des affaires, mais 43 % des enregistrements TA et 55 % des CAA. | Rapport documentaire inversé d'un ordre de grandeur voisin de 50 entre ces deux matières |

---

## 4. Stratification retenue — 12 strates

| # | Strate | Bases DILA dominantes | Poids contentieux D₁ | Masse documentaire attendue* | Verdict volumétrique |
|---|---|---|---|---|---|
| **S1** | Pénal — atteintes aux personnes et aux biens | LEGI (CP, CPP), CASS et INCA (chambre criminelle) | 52,31 % | Moyenne | Fortement surreprésenté |
| **S2** | Pénal — routier, santé publique, environnement, ordre public | LEGI (C. route, CSP, C. env.) | 16,47 % | Faible à moyenne | Surreprésenté |
| **S3** | Personnes, famille, état civil, protection des majeurs | LEGI (C. civ. livre I), CASS (1re civ.) | 11,30 % | Moyenne | Cohérent |
| **S4** | Contrats, obligations, responsabilité, consommation | LEGI (C. civ. livre III, C. conso.), CASS (1re et 2e civ.) | 1,76 % | **Très forte** | Fortement sous-représenté |
| **S5** | Biens, baux, copropriété, immobilier, urbanisme | LEGI (loi de 1989, C. urb.), CASS (3e civ.), JADE | 2,17 % | Forte | Sous-représenté |
| **S6** | Travail et protection sociale | LEGI (C. trav., CSS), **KALI**, **ACCO**, CASS (soc.) | 4,13 % | **Très forte** | Fortement sous-représenté |
| **S7** | Affaires, sociétés, entreprises en difficulté | LEGI (C. com.), CASS (com.) | 1,84 % | Forte | Sous-représenté |
| **S8** | Fiscal et finances publiques | LEGI (CGI, LPF), JADE, CASS (com.) | 0,22 % | **Très forte** | Fortement sous-représenté |
| **S9** | Étrangers, asile, nationalité | LEGI (CESEDA), JADE, CNDA | 2,98 % | **Très forte** | Sous-représenté |
| **S10** | Fonction publique et droit administratif général | LEGI (CGFP, CRPA), JADE | 0,51 % | Forte | Fortement sous-représenté |
| **S11** | Libertés publiques, données personnelles, constitutionnel | **CONSTIT**, **CNIL**, CEDH | 0 % | Moyenne | **Absent de D₁** |
| **S12** | Procédure et contentieux (civile, pénale, administrative) | LEGI (CPC, CJA), CASS, JADE | 0 % | **Très forte** | **Absent de D₁** |
| — | *Résidu non rattachable* | — | 6,32 % | — | *voir § 6* |

\* La colonne « masse documentaire » est une **hypothèse à valider** sur la volumétrie réelle des bases. C'est la seule colonne du tableau qui ne soit pas fondée sur le corpus statistique analysé.

**Lecture.** Sur douze strates, six sont fortement sous-pondérées par un échantillonnage volumétrique et deux sont totalement absentes de la statistique des affaires. Ce constat valide le choix de l'uniformité, tout en montrant que la partition de départ devait être refaite.

### 4.1 Table de correspondance passage 1 → strates

Cette table permet la repondération du § 1.2. Elle boucle exactement sur le socle de 6 162 985 affaires nouvelles 2024.

| Strate | Matières du passage 1 rattachées | Effectif | Poids |
|---|---|---|---|
| S1 | Atteintes aux biens ; Atteintes à la personne et indemnisation des victimes | 3 223 652 | 52,31 % |
| S2 | Circulation et transports ; Santé publique, stupéfiants et environnement ; Ordre public, autorité de l'État et police | 1 014 922 | 16,47 % |
| S3 | Personnes, famille et protection des majeurs et mineurs | 696 518 | 11,30 % |
| S4 | Contrats, crédit, impayés et exécution civile | 108 437 | 1,76 % |
| S5 | Logement, baux, biens et urbanisme | 133 485 | 2,17 % |
| S6 | Prud'hommes (117 137) + Pôle social (95 365) + Contentieux social TA (41 845) | 254 347 | 4,13 % |
| S7 | Atteinte économique, financière ou sociale (106 374) + Redressements et liquidations judiciaires civils (6 769) | 113 143 | 1,84 % |
| S8 | Contentieux fiscal TA (11 159) + CAA (2 522) | 13 681 | 0,22 % |
| S9 | Étrangers | 183 828 | 2,98 % |
| S10 | Fonction publique TA et CAA (25 154) + Marchés et contrats TA et CAA (6 209) | 31 363 | 0,51 % |
| S11 | *aucune* | 0 | 0 % |
| S12 | *aucune* | 0 | 0 % |
| Résidu | « Autres » civils (185 544) ; Référés (150 337) ; « Autres contentieux » TA et CAA (53 728) | 389 609 | 6,32 % |
| | **Total** | **6 162 985** | **100 %** |

> **Note de révision.** Ces poids affinent les valeurs approchées données lors de la discussion préparatoire. Trois corrections notables : S2 vaut 16,47 % et non 16,6 % ; S6 vaut 4,13 % et non 4,5 % ; S10 vaut 0,51 % et non 2,3 % — l'écart provenant du rattachement de la fonction publique à S10 et non à la strate travail.

---

## 5. Second axe — 6 types de difficulté de retrieval

En retrieval pur, la matière ne suffit pas à structurer un jeu de test. Ce qui fait varier le recall est le **type de décalage entre la requête et le document**. Chaque strate est croisée avec six archétypes.

| Type | Ce qu'il teste | Exemple |
|---|---|---|
| **T1 — Identifiant** | Résolution d'alias : numéro d'article, de pourvoi, ECLI, NOR, numérotation ancienne et nouvelle | *« art. L. 521-1 CJA »* ; *« ancien art. 1382 »* (praticien) |
| **T2 — Topique en langage courant** | Écart lexical pur entre formulation profane et rédaction normative | *« mon propriétaire veut me virer parce que j'ai pas payé »* (citoyen) |
| **T3 — Polysémie et faux-amis** | Désambiguïsation d'un terme à référents multiples | *« contentieux social »* → aide sociale (TA) ? relations du travail ? pôle social (TJ, sécurité sociale) ? |
| **T4 — Temporel et versionné** | État du droit à une date, texte abrogé, article renuméroté | *« rédaction applicable au 1er janvier 2023 »* |
| **T5 — Multi-base** | Restitution conjointe de la norme et de son application jurisprudentielle | *« que dit le texte, et comment le juge l'interprète »* |
| **T6 — Négatif et hors-corpus** | Précision : la bonne réponse est l'absence de résultat pertinent | Question de droit étranger, ou hors périmètre DILA |

**T6 est le type le plus souvent omis.** Sans lui, le jeu ne mesure que le recall et jamais la précision.

### 5.1 Matériau adversarial disponible pour T3

Le corpus statistique analysé au passage 1 contient **cinq nomenclatures officielles divergentes décrivant la même réalité** (RSJ tables A10, A12, B4 ; Chiffres clés B2 ; Chiffres clés JA B5 et C1). C'est du matériau de désambiguïsation authentique, produit par l'administration elle-même.

| Piège | Nature de la divergence |
|---|---|
| *« contentieux social »* | Trois référents incompatibles : aide sociale et RSA devant le TA ; relations du travail dans la nomenclature civile ; sécurité sociale sous l'intitulé « pôle social » devant le TJ |
| *Stupéfiants* | Sous-ligne de « santé publique » dans A10 ; poste autonome dans A12 et B4 |
| *« Atteinte à l'autorité de l'État »* (A10) | Devient « atteinte à l'ordre administratif et judiciaire » dans A12 — périmètres non identiques |
| *« Atteinte à l'ordre public ou à l'environnement »* (A12) | Fusionne deux catégories que A10 sépare |
| *Nomenclature administrative* | 8 postes dans B5 (2024) contre 12 dans C1 (2025), pour la même juridiction |

Ces divergences cassent la recherche vectorielle et constituent une strate adversariale prête à l'emploi.

---

## 6. Dimensionnement

```
12 strates × 6 types × 4 requêtes = 288 requêtes
    dont 144 en registre praticien
    dont 144 en registre citoyen
    dont 48 paires isosémantiques (96 requêtes)

+ strate-frontière hors quota          ≈ 20 requêtes
                                       ─────────────
                          TOTAL        ≈ 308 requêtes
```

### 6.1 Paires isosémantiques

Dispositif central pour exploiter le registre mixte : **une même question juridique, des qrels identiques, deux formulations** — l'une praticien, l'autre citoyen.

Le delta de recall entre les deux membres de la paire donne **le coût du décalage de vocabulaire en un seul nombre**, mesurable strate par strate. C'est la métrique la plus actionnable qu'un golden-set bilingue puisse produire.

### 6.2 Strate-frontière

Environ 20 requêtes hors quota, portant sur des questions qui tombent entre deux strates. Elle constitue l'analogue du résidu « non rattaché » de 6,32 % identifié au passage 1 : la stratification uniforme rend ce résidu invisible, il faut donc le réintroduire délibérément.

---

## 7. Paramètres de conception à trancher

| # | Décision | Recommandation | Motif |
|---|---|---|---|
| **1** | **Date de référence** | Figer une date pivot et l'inscrire dans chaque item | LEGI est versionné. Sans date pivot, les qrels se dégradent à chaque modification législative. Premier poste de dette technique d'un golden-set juridique. |
| **2** | **Échelle de pertinence** | Graduée sur 4 niveaux : 3 = norme directement applicable · 2 = jurisprudence d'application · 1 = contexte utile · 0 = non pertinent | Sans gradation, pas de nDCG ; le binaire pénalise injustement un moteur qui remonte le bon code mais pas le bon alinéa |
| **3** | **Granularité des qrels** | Annotation au **niveau document** (article LEGI, décision) comme référence stable, plus un sous-ensemble d'environ 50 items annotés au passage | Annoter au chunk coûte cher et casse à chaque re-chunking ; le sous-ensemble permet de diagnostiquer le chunking séparément |
| **4** | **Profondeur de mesure** | recall@10, @20 **et** @50 | En droit le besoin de rappel est élevé : manquer un arrêt de revirement est plus grave que remonter trois textes inutiles. Un k unique masque ce comportement. |

---

## 8. Séquence de mise en œuvre

### Étape 1 — Pilote (36 requêtes)

Trois strates contrastées × 12 requêtes, choisies pour couvrir les trois configurations extrêmes :

| Strate pilote | Configuration testée |
|---|---|
| **S1** — Pénal personnes et biens | Fort volume contentieux, masse documentaire moyenne |
| **S8** — Fiscal et finances publiques | Faible volume contentieux, masse documentaire très forte |
| **S12** — Procédure et contentieux | Absente de la statistique des affaires |

Objectifs : calibrer les consignes d'annotation, mesurer l'accord inter-annotateurs, estimer le coût réel par item.

**Justification.** La construction des qrels est le poste dominant du coût, très au-delà de la rédaction des requêtes. Il vaut mieux le découvrir sur 36 items que sur 288.

### Étape 2 — Extension

Généralisation aux douze strates après stabilisation des consignes, puis constitution de la strate-frontière.

### Étape 3 — Instrumentation

Mise en place du double calcul : score de diagnostic non pondéré et score d'estimation production repondéré par le vecteur du § 4.1.

---

## 9. Point ouvert

La colonne « masse documentaire attendue » du § 4 repose sur des hypothèses, non sur des mesures. Les trois documents statistiques du corpus ne disent rien de la volumétrie DILA.

**Donnée manquante prioritaire :** comptages par base et par matière ou juridiction, même approximatifs. Ils permettraient d'établir le facteur de conversion de la sous-question 1 du § 2, et de valider ou corriger l'affectation des strates aux bases.
