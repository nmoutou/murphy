# Description du golden-set ciblé (VIEUX)

> ⚠️ **Statut : jetable, et il doit le rester.** Ce document sert une seule
> séance de critique ([#25](https://github.com/left-eyebr0w/murphy/issues/25)).
> **Précaution tirée de [#13](https://github.com/left-eyebr0w/murphy/issues/13) §9** :
> `WIP/B-08-cadrage.md` s'était lui aussi déclaré éphémère, et **cinq documents
> durables l'ont cité** — il est devenu portant sans que personne le décide, et
> il a fallu un ticket pour le constater. Donc : **aucun document durable ne cite
> celui-ci.** Ce qu'il produit atterrit en ADR-036, ADR-038 ou dans la réécriture
> d'ADR-032 — ou nulle part

---

## 1. Introduction

Ce document décrit le **golden-set tel que la carte
[#1](https://github.com/left-eyebr0w/murphy/issues/1) le spécifie**, jalon par
jalon. Il est écrit avant la clôture de la carte, pour que le
porteur dispose d'un objet **attaquable** : la carte a produit vingt résolutions
et aucune vue d'ensemble, et une spécification qu'on ne peut pas lire d'un bloc
ne peut pas être critiquée d'un bloc.

---

## 2. Périmètre

### 2.1 Les trois blocs

| Bloc | Jalons `VERSIONS.md` | Traitement ici |
|---|---|---|
| **v0** — le presque-maintenant | jalon v0 · alpha ph.1 · alpha ph.2 · beta | **détaillé** (§4.1) |
| **v1** — entre bientôt et le très long terme | association · publication · machine B | **détaillé, plus court** (§4.2) |
| **v2** — l'horizon | — | **nommé, non détaillé** (§4.3) |

### 2.2 Note de lecture — deux mots doubles

1. **`v0` désigne le bloc** ci-dessus. Le jalon homonyme de `VERSIONS.md` s'écrit
   partout ***jalon v0***. (Le mot « pré-alpha » n'est pas employé : il est mort
   dans le dépôt, où il ne subsiste que comme bandeau d'archivage sur
   `ROADMAP.md` et `BETA.md`. Le ressusciter créerait un dixième mot à surveiller
   après les neuf du cimetière.)
2. **`v1` et `v2` nus désignent le produit.** La collection s'écrit toujours
   ***golden-set v1*** / ***golden-set v2***, jamais en abrégé. C'est déjà la
   pratique de `VERSIONS.md` et de la carte.

### 2.3 Ce qui est dehors

- **L'implémentation.** La carte fixe la *forme* des objets, pas leur code
  (`eval/` : classe `Query`, `QueryMetrics`, routage de métrique).
- **Le contenu des questions.** Aucune question n'est écrite ; l'audit porte sur
  le dispositif, pas sur des cas.
- **La construction de la taxonomie** (`docs/droit/taxonomie/`), hors chemin
  critique (ADR-034 §Conséquences).
- **Le second étage du plancher de composition**, reporté hors carte par
  [#24](https://github.com/left-eyebr0w/murphy/issues/24) §2.

---

## 3. Méthode

*(vide — à écrire **après** la description. Le plan fixe l'ordre de **lecture**,
où la méthode précède l'audit ; il ne fixe pas l'ordre de **travail**, où elle le
suit. On ne choisit pas correctement un étalon avant de savoir ce qu'on mesure.)*

> Décision déjà prise, conservée hors de ce document tant qu'il n'est pas temps de
> la rédiger : la méthode retenue est l'**audit de validité de construit sous
> étalon externe**, contre l'audit de conformité et l'audit de transfert, tous
> deux écartés pour **circularité**. Motifs et preuve d'existence dans le ticket
> [#25](https://github.com/left-eyebr0w/murphy/issues/25).

---

## 4. Le système spécifié

> **Deux étages par jalon.** D'abord **ce que le dispositif est** — inventaire des
> organes. Puis **ce qu'il prétend établir** — les assertions que le porteur
> pourra faire *sur la foi de* ces organes. Le second étage est le chaînon qui
> manquait : la méthode retenue demande *« mesure-t-il ce qu'il prétend
> mesurer ? »*, et les prétentions n'étaient écrites nulle part — ni ici, ni dans
> la carte, où elles vivent éparses dans vingt résolutions.
>
> **Discipline maintenue : on énonce, on ne juge pas.** Aucune prétention n'est
> attaquée dans ce §4 ; c'est le travail du §5. C'est la séparation qui rend
> chacun des deux attaquable seul.
>
> **Les non-prétentions sont du même registre et portent le même poids** (marquées
> ⊘). Elles disent ce que le dispositif ne promet **pas** — ce qui protège d'un
> reproche mal adressé autant que ça expose un renoncement contestable.
>
> *Préfixe `PT-` choisi pour ne collisionner ni avec `P-01`–`P-04` (les pièges de
> construction) ni avec `B-nn` (le backlog). Numérotation continue à travers les
> blocs, pour que le §5 y renvoie à plat.*

### 4.1 Bloc v0

#### 4.1.1 Jalon v0 — le golden-set v1

**Ce que l'objet est.** Une **collection de test au sens TREC** : le triplet
*corpus figé + topics + qrels*, soit la **machine A** d'ADR-035. Produite en
solo. Ce n'est pas un artefact terminal mais le **premier incrément** d'une
collection destinée à être reprise, étendue et ouverte.

**Composition — sept mécanismes déclarés, cinq peuplés.** L'axe est **unique**
(les mécanismes de récupération), **fermé** et **fixé a priori** ; un cas porte
un mécanisme et un seul.

| # | Mécanisme | Source du label | En v1 ? |
|---|---|---|---|
| 1 | `resolution_reference` | `identite` | ✅ 30 cas |
| 2 | `known_item_identifiant` | `identite` | ✅ 30 cas |
| 3 | `traversee_simple` (1 saut) | `graphe_g0` | ✅ 30 cas |
| 4 | `traversee_chainee` (profond) | `graphe_g0` | ❌ **0 cas** — déclaré, non peuplé ([#16](https://github.com/left-eyebr0w/murphy/issues/16)) |
| 5 | `absence_attendue` | frontière de **périmètre DILA** | ✅ 30 cas, `R = 0` |
| 6 | `concept_vers_instance` | **aucune — jugé** | ✅ 30 cas, le noyau jugé |
| 7 | `desambiguisation` | — | ❌ hors v1, rappel en alpha ph.2 ([#9](https://github.com/left-eyebr0w/murphy/issues/9), [#20](https://github.com/left-eyebr0w/murphy/issues/20)) |

> ⚠️ **La renumérotation n'est pas écrite.** Elle est due en ADR-036 ; la table
> ci-dessus est **reconstruite depuis les résolutions** (#2, #10, #16, #15, #12).
> Deux **opérations** d'ADR-030 sont par ailleurs sans producteur en v1 —
> `jurisprudence_applicable` (#10) et `fondement_textuel` (#16 §5, faute d'arête
> jurisprudence → article dans `G₀`).

**Volumétrie.**

| Grandeur | Valeur | Dérivation |
|---|---|---|
| Plancher par mécanisme | **30 cas** | règle de trois : zéro échec sur 30 borne l'échec à < 10 % ([#11](https://github.com/left-eyebr0w/murphy/issues/11)) |
| `N_cas` | **150** | somme ascendante de planchers, jamais un total réparti |
| `N_q` | `N_cas` + variantes + `N_pending` (≥ 180) | [#21](https://github.com/left-eyebr0w/murphy/issues/21) |
| Cas **jugés** | 30 (`concept_vers_instance`) | [#9](https://github.com/left-eyebr0w/murphy/issues/9) |
| Cas **comparables** | **120** (90 gratuits à `R ≥ 1` + 30 jugés) | [#14](https://github.com/left-eyebr0w/murphy/issues/14) |
| Jugements | ≈ 600 en **profondeur de départ** | statut changé par #20 : plus un budget, un point de départ |

**Les labels.** Trois **sources de gratuité**, chacune un fait extérieur à
l'opinion qui détermine l'ensemble-réponse ([#2](https://github.com/left-eyebr0w/murphy/issues/2),
amendé par [#15](https://github.com/left-eyebr0w/murphy/issues/15)) :

- **`identite`** — le label vit **hors corpus** ; il *mûrit* (une extension lui
  donne une cible), il ne se périme pas.
- **`graphe_g0`** — dérivé du corpus et **re-dérivable** ; l'ensemble-réponse
  *croît*. D'où une obligation : **les qrels de graphe sont re-dérivées depuis
  `G₀` à chaque version déclarée**.
- **frontière de périmètre DILA** — définition **externe** (`VISION.md` §2,
  ADR-014), pas un état. Elle *se retourne* si elle est fausse — et ce
  retournement est une **alarme**, pas une réparation.

La **règle de confiance** gouverne l'ensemble : la question n'est jamais *« peut-on
juger un cas gratuit ? »* mais *« fait-on confiance au label ? »*. Confiance → on
évalue la totale ; pas confiance → on ne l'utilise pas. **Aucun état
intermédiaire**, et le test s'exerce **à l'admission d'un mécanisme**, jamais par
cas.

**L'enregistrement d'authoring** ([#12](https://github.com/left-eyebr0w/murphy/issues/12)).
Distinct de `Topic(query_id, text)`, qui existe déjà dans `eval/` et en est la
**projection runtime inchangée**.

`case_id` (`gs1-NNNN`, opaque, **immuable, jamais réemployé**) · `mecanisme` ·
`texte` · `narrative` · `germe` (exigé là où le label est gratuit **seulement**) ·
`leurre` (sur `absence_attendue`) · `date_pivot` · `variante_de` · `origin` ·
`origine_notion`.

Deux propriétés qui portent : sur un cas jugé, **l'absence de germe *est* la
preuve du typage** (la requête énonce une situation, vérifiable a priori et sans
run) ; et le **hash suit le coût, pas le fichier** — `narrative` appartient à
`qrels` parce qu'aucun run ne la lit.

**L'identification** ([#18](https://github.com/left-eyebr0w/murphy/issues/18) §0).
`gel` est sorti du vocabulaire : *il ne garantissait la validité de rien.*
Remplacement — **on ne gèle rien, on identifie tout** :

- **trois hashes** — `corpus` (sur les **identités canoniques de document**, donc
  *stable sous `W`*), `cas`, `qrels` — portés par chaque run ;
- **deux runs sont comparables ssi leurs hashes sont égaux**, mécaniquement ;
- une **version de collection** = un triplet de hashes qu'on **nomme** et publie ;
  l'acte est **déclaré**, pas détecté, et ne porte aucune sémantique de mesure ;
- **pas de quatrième hash composé** — il serait plus commode à citer et
  cannibaliserait le diagnostic ;
- **on ne cite jamais un chiffre d'un état antérieur, on re-note** (ADR-032 §2 :
  un run ne dépend pas des qrels).

**L'instrument de mesure.**

| | |
|---|---|
| Grandeur de comparaison | **`RBP(p) + résidu`** sur les **120 cas comparables**. `nDCG@R` retiré (septième mot du cimetière), `F1@K` clos par le négatif |
| `p` de décision | **0,80**, déclaré *ex ante* **depuis le lecteur** (`RETRIEVAL_TOP_K = 5`), publié avec tout score. ⚠️ La règle `p = 0,01^(1/d̄)` est **retirée** : indexer le modèle de lecteur sur l'effort d'annotation épinglait le résidu de queue à 1 % quelle que soit la profondeur |
| Famille sentinelle | **`0,50 / 0,80 / 0,95`**, publiée entière, **sans seuil** — elle *dicte la phrase* au lieu de bloquer |
| `d_min` | **200** — profondeur d'**archive**, découplée de `p`, ne touche aucune mesure |
| Grades | 0–3 (cascade q1–q3, ADR-005), **projection linéaire `g/3`** — l'échelle est un *compte de portes franchies*, pas une intensité |
| Écart apparié | `[a−b−Σ(w_B−w_A)⁺, a−b+Σ(w_A−w_B)⁺]`, largeur **`Σ|w_A−w_B|`**, atteinte à un sommet ([#23](https://github.com/left-eyebr0w/murphy/issues/23)). `r_A+r_B` n'est plus que **majorant** |
| Deux refus | un score dont le top-`k` est **majoritairement non jugé** n'est pas publiable · un intervalle **contenant zéro** n'admet aucun test (*« au budget dépensé, non distinguables »*, jamais *« pas de différence significative »*) |

**Lectures par branche** ([#3](https://github.com/left-eyebr0w/murphy/issues/3),
amendé) : `R = 0` (30 cas) → **précision seule**, aucune métrique de classement,
comparaison propre par **taux de remontée au-delà du seuil** · `R ≥ 1` clos (90
cas) → `Recall@R`, **tout-ou-rien au rapport, continu (`i/R`) à la comparaison** ·
branche **ouverte** (30 cas jugés) → RBP.

> **Toute l'incertitude du dispositif vient des 30 cas jugés.** La couche gratuite
> n'a **aucun trou**, donc résidu nul. Le budget marginal n'achète de la
> résolution qu'au noyau.

**Le protocole de pooling** ([#18](https://github.com/left-eyebr0w/murphy/issues/18)).
Il ne porte que sur le noyau jugé — non par interdiction, mais parce qu'un label
auquel on fait confiance *détermine* son ensemble-réponse.

- **Deux régimes** : un **pilote** (une config, ~5 cas, re-jugement à l'aveugle),
  dont la sortie est un **seuil d'auto-cohérence ≥ +0,49** (ancre Legal Track
  2006, *inter*-assesseur donc conservatrice pour de l'*intra*) ; puis la
  **campagne**.
- **Allocation gloutonne par contribution RBP** — le budget va où les configs
  divergent ; l'arrêt prématuré est **sûr par construction** (préfixe, pas de
  *bins*).
- **`R` n'est pas estimé** (écart à TREC motivé : facteur 25–125 sur le
  budget/cas).
- **Contributeurs au pool** : sweep déclaré · run lexical automatique · **run
  booléen rédigé à la main** — le seul contributeur qui n'est pas une machine, et
  le filtre qualité **non circulaire** que #6 appelait sans le nommer. Run
  aléatoire différé avec déclencheur chiffré.
- **La largeur autorisée d'un cas est une sortie du protocole**, pas une variable
  libre : sous allocation à budget fixe, un cas très large affame les autres.

**Le protocole d'assessment** ([#19](https://github.com/left-eyebr0w/murphy/issues/19),
domicile **ADR-038, non écrit**).

- **Deux objets distincts** : l'*intra* mesure la **stabilité** (résolution de
  l'instrument) ; l'*inter* mesure l'**extériorité du critère** — il est le
  **falsificateur de R-05**. Donc **+0,49 ne transfère pas** de l'un à l'autre.
- **Asymétrie par porte** : **q1** (« même question de droit ? ») est une identité
  topique où le désaccord n'est **pas légitime** → seuil **structurel** : *zéro
  désaccord q1 inattribuable* à une vaguesse réparable. **q2/q3** sont du jugement
  professionnel où deux assesseurs peuvent diverger **en ayant tous deux raison**
  → structure conservée, **sans agrégat**, avec un **troisième compartiment** que
  l'*intra* n'a pas : la **divergence légitime**.
- **Table de réparation pré-enregistrée** : *un compartiment qui se remplit sans
  que sa réparation ne parte est un échec visible.* q1 → réécriture du cas
  (hash `cas`, re-récupération) · q2/q3 qui cède → amendement du guide,
  re-jugement **ciblé** · q2/q3 qui tient → divergence déclarée dans la
  `narrative` (hash `qrels`, re-notation seule).
- **Séparateur : réconciliation à deux, en aveugle**, sur les seuls items en
  désaccord — l'assesseur voit l'item, **jamais l'identité de l'autre**.
  L'adjudication par un tiers est la **machinerie après panne**.
- **Règle de famine** (*toujours le moins jugé*), tourniquet par cas, contribution
  RBP à l'intérieur. **RBP gouverne l'admission, la famine la redondance.** Une
  seule file, ordonnée par *(nombre de jugements détenus, puis rang)* ; plafond
  ≈ 600 items ≈ 24–30 h.
- **Deux critères d'arrêt, aucun budgétaire** : la **porte du résidu**
  (profondeur) et la **table de réparation** (redondance). La famine est ce qui
  rend la porte **non manipulable** — elle interdit l'arrêt optionnel : on
  s'arrête à une **frontière de passe**, pas à un instant.
- **Le guide d'annotation** porte **huit contraintes de rédaction** et devient
  l'instrument de l'assesseur via le champ `narrative`. ⚠️ **Il n'existe pas** :
  `ADR-008.guide_version` pointe vers un document inexistant.

**L'intake des contestations** ([#21](https://github.com/left-eyebr0w/murphy/issues/21),
domicile **ADR-032 réécrit, non écrit**). Porte unique, triage interne, **l'unité
est une contestation, jamais un patch** ; l'intake **ne transporte jamais de
texte**. Périmètre : ***on conteste ce qui est écrit, jamais ce qui manque.***
Motifs en **liste fermée + « autre »**, cinq issues toutes enregistrées, routage
**lu sur la table champ → hash** et non arbitré. **Pas de SLA** — l'arriéré est
une colonne. Trace : un **journal des déplacements de hash à quatre causes
typées** (correction · extension · dérivation · corpus), en ajout seul, non haché,
**déclarant par rôle et non par identité**.

**Le plancher de composition** ([#24](https://github.com/left-eyebr0w/murphy/issues/24)).
Il porte sur le **nom**, pas sur la déclaration : sous le plancher, l'objet se
déclare, se hashe et se publie — mais **pas sous le nom promis**. Deux conditions :
*contenu* (**au moins un composant jugé**) et *monotonie* (composition livrée ⊆
composition déclarée). Lecture **unique, avant déclaration**, sur le lot d'amorce ;
règle **pré-enregistrée**. ⚠️ Obligation critique attachée : **le résidu nul n'est
pas un signal de qualité.**

**Ce que le rapport publie.**

- tout score sous la forme **`score + résidu`**, avec `p` ;
- **`correspondance_litterale` en tête, comme condition de lecture** — son échec
  fait publier le reste **marqué non interprétable** ;
- **taux de réussite ventilé par mécanisme**, sans seuil, direction
  pré-enregistrée — *un taux qui plafonne est un pouvoir discriminant nul, donc un
  défaut du jeu* ;
- **grandeur de transfert par paire** de configurations, avec son intervalle,
  **jamais agrégée** ; une paire non séparée s'affiche **inerte** ;
- **taux d'annulation du résidu** par paire, sans seuil — audit du resserrement.
  **Une seule largeur est publiée, la resserrée** ;
- **taux de rejet à l'authoring**, ventilé **mécanisme × cause**, sans seuil,
  jamais agrégé ;
- **volume de contestations, ventilé motif × issue**, sans seuil, les non
  résolues formant une colonne ;
- le **contrôle d'auto-cohérence** du noyau ;
- pour `traversee_simple` : **jamais le taux seul** — il porte à côté de lui le
  taux propre de `resolution_reference` et le compte des germes remontés sur les
  cas échoués.

**Le régime — solo, et ce que ça veut dire.** « En solo » est une **propriété** de
la machine A et un choix de **prudence**, non une autarcie : un lecteur extérieur
peut intervenir dès la v0, ce qui est exclu étant d'en **dépendre pour livrer**.
Conséquence lourde et écrite : **l'essai de l'appareil d'assessment est
solo-réalisable, porteur à deux casquettes — il exerce la machinerie et ne mesure
pas l'extériorité.** *Une seule tête ne peut pas constater qu'un critère sort
d'elle.* **R-05 tient son constat en puissance, non en acte.**

**Le critère de sortie, et ses deux pièges de lecture.**

1. **Lecture *instrument*** — v0 n'est otage d'**aucun résultat**. Une campagne
   dont **toutes les paires sont inertes** satisfait le critère.
2. **Mais un objet renommé ne clôt pas v0** — piège **inverse et plus dangereux,
   parce que le cadran le récompense**. La clôture est indexée sur le **nom**.

> ***Résultat inerte ≠ appareil inexercé.***

**Ce qui n'est pas écrit au jalon v0** — matériau direct pour §5 : ADR-036
(contenu, cimetière de vocabulaire, P-01–P-04, renumérotation) · ADR-038
(protocole d'assessment, plancher générique) · **ADR-032 réécrit** (intake, règle
champ → hash) · la **table champ → hash** en `GOLDEN-SET.md` §3 · un **marqueur
sur ADR-030** · et **le guide d'annotation**, qui n'existe pas.

##### Ce que le jalon v0 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-01** | **Comparabilité.** Deux runs portant les mêmes trois hashes mesurent le même objet ; deux runs aux hashes différents ne se comparent **jamais par citation** d'un chiffre antérieur, mais par **re-notation** | les trois hashes · ADR-032 §2 |
| **PT-02** | **Ordonnancement.** Au budget dépensé, la configuration A se classe devant B — **ou bien l'instrument déclare qu'on ne peut pas le dire** | `RBP(0,80) + résidu` · écart apparié de largeur `Σ\|w_A−w_B\|` · la porte du zéro |
| **PT-03** | **Pouvoir discriminant constaté.** Si le jeu cesse de discriminer sur un mécanisme, **on le voit** — et on le lit comme un défaut du jeu, jamais comme une réussite du système | taux ventilé par mécanisme, sans seuil, direction pré-enregistrée · plancher de 30 |
| **PT-04** | **Gratuité du label.** Sur quatre des cinq mécanismes peuplés, l'ensemble-réponse est déterminé par un **fait extérieur à l'opinion du porteur** | les trois sources de gratuité · la règle de confiance, exercée **à l'admission** |
| **PT-05** | **Reproductibilité.** Deux exécutions au couple `(W, G, R)` identique rendent les mêmes métriques | E-P2-10 · fingerprint de `W` · ADR-031 |
| **PT-06** | **L'appareil existe et a tourné.** Le protocole d'assessment n'est pas une intention : il a reçu au moins un jugement | [#19](https://github.com/left-eyebr0w/murphy/issues/19) · plancher de composition [#24](https://github.com/left-eyebr0w/murphy/issues/24) |
| **PT-07** | **Interprétabilité conditionnelle.** Si `correspondance_litterale` échoue, le reste du rapport est publié **marqué non interprétable** | [#10](https://github.com/left-eyebr0w/murphy/issues/10), amendé |

**⊘ Ce que le jalon v0 ne prétend pas**

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-08** ⊘ | Le jeu **n'estime pas la performance en production** — un chiffre nu, non pondéré | [#4](https://github.com/left-eyebr0w/murphy/issues/4) (§6.2 mort par YAGNI du porteur) |
| **PT-09** ⊘ | Le jeu **n'échantillonne pas le droit** : il énumère des fonctions. **Aucun cadre d'échantillonnage**, donc aucune capacité de chiffrer un trou | ADR-034 §1 · #4 |
| **PT-10** ⊘ | **`R` n'est pas estimé** — aucun rappel absolu n'est prétendu | [#18](https://github.com/left-eyebr0w/murphy/issues/18) §7b |
| **PT-11** ⊘ | **L'extériorité du critère n'est pas mesurée.** L'essai solo exerce la **machinerie** ; *une seule tête ne peut pas constater qu'un critère sort d'elle*. R-05 reste **en puissance** | #19, amendement du 8 août |
| **PT-12** ⊘ | **Le biais de pool n'est pas mesuré**, et ne **peut** pas l'être en solo mono-système | [#7](https://github.com/left-eyebr0w/murphy/issues/7) |
| **PT-13** ⊘ | **La justesse du chiffre est hors périmètre** — reproductibilité seule | ADR-028 · E-P2-10 |

#### 4.1.2 Alpha ph.1 — « Usage & requêtes réelles »

Le golden-set v1 ne change pas. Quatre choses lui arrivent :

- **`p` devient révisable.** Déclaré *ex ante* depuis le lecteur au jalon v0, il
  se révise ici — **c'est le premier jalon où la persistance réelle s'observe**.
- **Une seconde tête entre.** Les notations `origin: inline` (cascade q1→q3,
  ADR-005/010) font entrer des jugements qui ne viennent pas du porteur.
- **Le pool de requêtes réelles se constitue** : c'est la matière du golden-set
  v2, pas un ajout au v1.
- Le **run archivé daté avant l'ouverture du panel** ([#5](https://github.com/left-eyebr0w/murphy/issues/5) §8c)
  attend ici son consommateur, qui n'arrive qu'en beta.

##### Ce que l'alpha ph.1 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-14** | **`p` cesse d'être déclaré et devient observé** — la persistance du lecteur est mesurée, plus postulée | révision de `p` en ph.1 ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) |
| **PT-15** | Un **pool de requêtes réelles** existe, non dérivé du porteur | critères de sortie ph.1 · ADR-013 |
| **PT-16** | Des **jugements viennent d'une autre tête** que celle qui a écrit les cas | mode inline, `origin: inline` (ADR-005/010) |

**⊘ Ce que l'alpha ph.1 ne prétend pas**

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-17** ⊘ | Ces jugements **ne mesurent toujours pas l'extériorité du critère** : l'inline n'est pas la file poolée, seule à distinguer ses **deux consommateurs** (lecteur *différent* obligatoire pour l'extériorité · *même* lecteur obligatoire pour l'auto-cohérence) | ADR-010 · #19 |

#### 4.1.3 Alpha ph.2 — le golden-set v2

**Qrels canoniques** : expert, poolé, calibré, sur les requêtes réelles de la
ph.1. Baseline **re-mesurée**.

- **`desambiguisation` rentre** — rappel nommé, le jugement y étant financé par
  construction.
- **Le terminal budget se déplace sans toucher la règle** : `p` monte seul,
  `d_min` garde les runs archivés exploitables, **la re-notation répare
  gratuitement**. C'est ici que « rien à jeter » est censé se démontrer.
- **Bascule à `n ≥ 5`** : vote majoritaire, la **divergence légitime devient
  observable** (5 est le premier effectif où un 3-2 se distingue d'un 4-1). Les
  qrels antérieures deviennent le **contrefactuel**.
- **L'*inter* devient mesurable.** C'est le premier jalon où R-05 reçoit un
  falsificateur en acte.

##### Ce que l'alpha ph.2 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-18** | Les qrels sont **canoniques** — expertes, poolées, calibrées | mode campagne (ADR-010) · critères de sortie ph.2 |
| **PT-19** | **R-05 reçoit un falsificateur en acte** : l'*inter* mesure l'**extériorité du critère**, ce que le solo ne pouvait pas | [#19](https://github.com/left-eyebr0w/murphy/issues/19) |
| **PT-20** | La **divergence légitime est observable** — un 3-2 se distingue d'un 4-1 | bascule à `n ≥ 5` |
| **PT-21** | Le passage golden-set v1 → v2 **n'a rien jeté** : `p` monte seul, `d_min` garde les runs, la re-notation répare gratuitement | [#20](https://github.com/left-eyebr0w/murphy/issues/20) · ADR-032 §2 |

#### 4.1.4 Beta — « Valeur d'usage »

**C'est ici que le corpus bouge**, et c'est le seul jalon du bloc v0 où il bouge.
Vague 2 DILA (ADR-003) → **le hash `corpus` se déplace** → classe **chère**
d'ADR-032 §4 : **rejeu, pas re-notation**.

Ce qui s'y teste :

- **Le théorème de stabilité** (#16 §6) : ajouter des arêtes ne peut que
  **raccourcir** des distances, donc un cas *toutes cibles à distance 1* ne peut
  pas être invalidé — le **typage** survit mécaniquement. ⚠️ Mais le théorème
  porte sur le typage, **jamais sur les qrels** : d'où l'obligation de
  **re-dérivation** des qrels de graphe.
- **L'alarme de périmètre** (#15) : un cas `absence_attendue` dont la cible entre
  dans le corpus signifie que **la définition du périmètre était fausse** —
  résultat de premier rang, qui ne devrait jamais se déclencher.
- **`pending` se dégonfle** : des cas en sortent, **avec leur historique déjà
  constitué** (ils étaient interrogés et archivés depuis leur écriture, exclus du
  seul scoring).
- **Le capteur** (ADR-034 §3, #5) s'installe : environnements public/panel
  (ADR-025), verdict **du testeur**, liste fermée d'hypothèses en langue de mode
  d'échec + case « autre », **table déclarée a priori** traduisant vers les
  mécanismes. Il émet une **énumération d'items, jamais un taux**.

##### Ce que la beta prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-22** | Le **typage survit au déplacement du corpus**, mécaniquement et non par vérification | théorème de [#16](https://github.com/left-eyebr0w/murphy/issues/16) §6 |
| **PT-23** | Si la **définition du périmètre était fausse**, on l'apprend — l'alarme ne devrait **jamais** partir, et son déclenchement est un résultat de premier rang | [#15](https://github.com/left-eyebr0w/murphy/issues/15) |
| **PT-24** | Les cas sortis de `pending` **entrent avec leur historique déjà constitué** — un vecteur de croissance sans rejeu | [#21](https://github.com/left-eyebr0w/murphy/issues/21) |
| **PT-25** | Un **échec observé chez un testeur se rattache à un mécanisme** — ou remplit la case « autre », qui désigne un trou dans **l'axe** et non dans l'échantillonnage | capteur ([#5](https://github.com/left-eyebr0w/murphy/issues/5)) · table déclarée *a priori* |

### 4.2 Bloc v1

#### 4.2.1 Association (ADR-015)

Jalon organisationnel, entre beta et publication. Aucun contenu de collection —
mais **c'est la frontière où le porteur cesse d'être structurellement seul**, et
donc où l'enfichabilité conçue par #18 et #21 (*porteur seul → panel ADR-025 →
communauté*) change d'occupant.

#### 4.2.2 Publication — « Exhaustivité DILA » (ADR-014)

Toutes les bases DILA ingérées. Deux conséquences pour la collection :

- **`pending` se vide par construction** — il n'y a plus de « dans DILA, non
  ingéré ».
- **L'alarme de #15 change de sens** : la séparation *`pending` non scoré ↔ hors
  périmètre scoré*, qu'`absence_attendue` porte dans son nom, perd son premier
  terme. Ce que l'alarme signale après publication n'est plus le même événement.

#### 4.2.3 Machine B — la campagne communautaire

Des équipes indépendantes soumettent des runs concurrents, poolés et jugés.
**Structurellement plurielle**, donc **hors machine A**. A précède B ; l'inclusion
`B ⊃ A` a été retirée, la frontière est le **contrat de recevabilité** de #18 §8
(ADR-008 projette de façon déterministe vers les qrels/runs TREC plats).

**Aucun jalon ne l'accueille**, et `VERSIONS.md` §Statuts non finaux l'enregistre
comme troisième point ouvert : ses critères de sortie ne peuvent pas s'énoncer
honnêtement aujourd'hui, aucun effectif d'équipes n'étant fondé une fois le régime
du NIST écarté (R-09).

**C'est le seul jalon où le biais de pool devient mesurable** (§1.2 b).

⚠️ Réserve portée par #17 : au Legal Track, des *Topic Authorities* dotées de
**10 h par équipe et par topic** ont été **sous-consommées** — *« very few of the
teams used a significant portion of the ten hours »*. Même une aide gratuite,
offerte, adossée au NIST, n'a pas été prise.

#### 4.2.4 Ce que le bloc v1 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-26** | Le **périmètre annoncé est atteint** — l'exhaustivité DILA est un critère de **publication**, et c'est ici qu'il se constate | ADR-014 · `VISION.md` §2 |
| **PT-27** | La collection est **réutilisable par un tiers** : un run externe conforme au contrat est **recevable et notable** sans renégociation | ADR-008 (projection déterministe vers qrels/runs TREC plats) · [#18](https://github.com/left-eyebr0w/murphy/issues/18) §8 |
| **PT-28** | Le **biais de pool devient mesurable** — pour la première fois, des systèmes non contributeurs existent | pluralité de la machine B · [#7](https://github.com/left-eyebr0w/murphy/issues/7) *a contrario* |
| **PT-29** | La collection **survit à l'ouverture sans redesign** — le critère « rien à jeter » atteint son **terminal** | ADR-035 §6 |

**⊘ Ce que le bloc v1 ne prétend pas**

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-30** ⊘ | **Aucun effectif d'équipes n'est promis.** Un critère « ≥ N équipes externes » supposerait un `N` que rien ne fonde : le seul disponible est celui du NIST, dont le **pouvoir de convocation ne transfère pas** | `VERSIONS.md` §Statuts non finaux · ADR-035 §3 · R-09 |

### 4.3 Bloc v2 — l'horizon

Nommé, non détaillé. Rien de ce que la carte a décidé ne s'y projette, et rien
n'y est promis. Il est ici pour que le document ne se lise pas comme si la
trajectoire s'arrêtait à la machine B.

**Aucune prétention.** C'est la seule case du registre `PT-` qui soit vide, et
elle l'est par construction, non par oubli.


