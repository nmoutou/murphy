# Description du golden-set ciblé (NOUVEAU) — document de travail

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

> ⚠️ **Ce document n'est plus une restitution neutre de la carte.** Cinq décisions
> prises en séance de critique s'en écartent, et **aucune n'est encore portée par
> une résolution ni par un ADR** :
>
> 1. **La renumérotation des collections** — le « golden-set v1 » de la carte
>    devient `0.0.1`, sous une règle de coïncidence avec les versions produit
>    (§2.2). Le mot v2 est libéré.
> 2. **Le contrat de la machine B remonte au jalon v0**, sa campagne restant au
>    majeur 1 (§3.1.1, §3.2.3).
> 3. **Le guide d'annotation et ADR-038 deviennent bloquants** pour la clôture du
>    jalon v0 (§3.1.1).
> 4. **La campagne *inter* poolée remonte à l'alpha ph.1** (§3.1.2), PT-19 avec
>    elle.
> 5. **Le registre `PT-` passe de deux à trois colonnes** — ⊙ *en puissance*
>    s'ajoute, avec une porte d'admission stricte (§4).
>
> Les quatre premières relèvent du même geste : **déplacer un test vers l'endroit
> où l'échouer coûte le moins.** La cinquième est la conséquence des trois
> précédentes sur le registre. Atterrissage prévu : ADR-036, ADR-038, ADR-032
> réécrit — **pas ici.**

---

## 2. Périmètre

### 2.1 Les trois majeurs

| Majeur | Jalons `VERSIONS.md` | Collections | Traitement ici |
|---|---|---|---|
| **0** — le presque-maintenant | jalon v0 · alpha ph.1 · alpha ph.2 · beta | `0.0.n` · `0.a.n` · `0.b.n` | **détaillé** (§3.1) |
| **1** — l'ouverture | association · publication · campagne communautaire | `1.…` | **détaillé, plus court** (§3.2) |
| **2** — l'horizon | — | — | **nommé, non détaillé** (§3.3) |

### 2.2 La numérotation des collections

**Règle : le numéro de collection est celui de la version produit avec laquelle
elle est livrée.** Le projet d'évaluation est livré et publié en même temps que
le moteur ; deux compteurs distincts n'auraient rien de différent à compter.
D'où le nom de la première collection — **golden-set v0**, et non « v1 » comme la
carte l'écrit encore partout.

**La coïncidence est verrouillée au majeur seulement.** Sous le majeur, le
golden-set branche sur son axe propre :

> `majeur . lettre de phase . compteur` — `0.0.1`, `0.0.2`, `0.a.1`, `0.b.1`, `1.…`

| Élément | Ce qu'il porte |
|---|---|
| **majeur** | verrouillé sur le produit. `0` = pré-public · `1` = à partir de l'ouverture |
| **lettre** | la phase, **et rien d'autre** — `0` avant l'alpha (porteur solo) · `a` alpha · `b` beta |
| **compteur** | les **publications nommées**, jamais les déplacements de hash |

Trois propriétés à ne pas perdre :

- **La lettre ne dit pas la classe de coût.** Lui faire encoder aussi la
  re-notation *vs* le rejeu (ADR-032 §4) aurait obligé, le jour où le corpus
  bouge hors beta, à **changer de lettre ou à mentir** — ce n'est pas un
  encodage, c'est un pari. La classe se lit sur le **journal des déplacements de
  hash** de [#21](https://github.com/left-eyebr0w/murphy/issues/21), qui est déjà
  l'endroit prévu pour elle.
- **Un numéro nomme une lignée, jamais un état.** *golden-set v0* désigne un
  ensemble d'états partageant une **intention de livraison** ; `0.a.1` un
  sous-ensemble plus étroit. Entre deux publications nommées les hashes bougent —
  l'intake n'a pas de SLA, et *on ne gèle rien*.
- **Donc PT-01 repose sur les trois hashes, jamais sur le nom.** Deux runs « sur
  `0.a.1` » peuvent porter des hashes différents et ne pas se comparer. Le numéro
  est une **étiquette de livraison** ; l'unité de comparabilité reste le triplet.
  La **porte d'accès au nom promis** est le plancher de composition de
  [#24](https://github.com/left-eyebr0w/murphy/issues/24), qui sait déjà séparer
  *déclarer un état* de *lui donner le nom promis*.

*Propriété utile : en ASCII `0` < `a` < `b`, donc `0.0.3 < 0.a.1 < 0.b.1` se trie
correctement sans outil dédié.*

### 2.3 Note de lecture — le chiffre 0 a trois référents

Le verrouillage **supprime** l'ancienne homonymie (`v1`/`v2` nus désignant le
produit pendant que la collection portait les mêmes chiffres). Il en **aggrave**
une autre, qu'il faut désormais tenir explicitement :

1. **jalon v0** — le jalon de `VERSIONS.md`, écrit partout ***jalon v0*** ;
2. **majeur 0** — tout le bloc jusqu'à l'ouverture publique (§2.1) ;
3. **`0.0.n`** — la collection livrée au jalon v0.

Ce n'est pas une pinaillerie de vocabulaire. La propriété **solo** de la machine A
(ADR-035) vit au **jalon v0**, pas dans tout le majeur : *« des gens participent
en v0 »* est **vrai du majeur, faux du jalon**. Un lecteur qui confond les deux
conclut que la propriété solo a été abandonnée, alors qu'elle est intacte.

*(Le mot « pré-alpha » n'est pas ressuscité : il est mort dans le dépôt, où il ne
subsiste que comme bandeau d'archivage sur `ROADMAP.md` et `BETA.md`. La phase du
jalon v0 porte la lettre `0`, pas un mot.)*

### 2.4 Ce qui est dehors

- **L'implémentation.** La carte fixe la *forme* des objets, pas leur code
  (`eval/` : classe `Query`, `QueryMetrics`, routage de métrique).
- **Le contenu des questions.** Aucune question n'est écrite ; l'audit porte sur
  le dispositif, pas sur des cas.
- **La construction de la taxonomie** (`docs/droit/taxomonie/`), hors chemin
  critique (ADR-034 §Conséquences).
- **Le second étage du plancher de composition**, reporté hors carte par
  [#24](https://github.com/left-eyebr0w/murphy/issues/24) §2.

---

## 3. Le système spécifié

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
> **Trois registres, pas deux**, et les deux seconds portent le même poids que le
> premier :
>
> - **⊘ non-prétention** — ce que le dispositif ne promet **pas**, *par décision*.
>   Protège d'un reproche mal adressé autant que ça expose un renoncement
>   contestable. **Rien n'attend** : personne ne peut arriver et la retourner.
> - **⊙ prétention en puissance** — l'appareil est construit, écrit et exercé ;
>   **il ne manque qu'un acte d'un autre que le porteur**. Le vocabulaire n'est pas
>   inventé ici : PT-11 portait déjà *« R-05 tient son constat **en puissance**,
>   non **en acte** »* en prose dans une cellule. Il devient structurel.
>
> **Porte d'admission, stricte.** Une prétention est *en puissance* **ssi la seule**
> chose qui manque est un acte d'un tiers. **S'il reste quoi que ce soit à
> construire ou à décider par le porteur, c'est ⊘.** Sans cette porte, ⊙ devient la
> benne du « on aimerait bien mais on n'a pas fait » — c'est le travail de ⊘, et on
> aurait détruit le sens de deux colonnes au lieu d'une.
>
> **Chaque ⊙ nomme son déclencheur** — l'événement qui la fait basculer *en acte*.
> D'où un sous-produit qui vaut à lui seul la colonne : *la liste des ⊙ est la
> liste de ce qu'on gagne en faisant entrer une personne*. Et le §5 hérite d'une
> question qu'il n'avait pas : **ce déclencheur est-il atteignable ?** Un appareil
> armé pour un déclencheur qui n'arrive jamais est une pathologie **distincte**
> d'un renoncement.
>
> *Préfixe `PT-` choisi pour ne collisionner ni avec `P-01`–`P-04` (les pièges de
> construction) ni avec `B-nn` (le backlog). Numérotation continue à travers les
> majeurs, pour que le §5 y renvoie à plat.*

### 3.1 Majeur 0

#### 3.1.1 Jalon v0 — la collection `0.0.1`

**Ce que l'objet est.** Une **collection de test au sens TREC** : le triplet
*corpus figé + topics + qrels*, soit la **machine A** d'ADR-035. Produite en
solo. Ce n'est pas un artefact terminal mais le **premier incrément** d'une
collection destinée à être reprise, étendue et ouverte.

**Composition — sept mécanismes déclarés, cinq peuplés.** L'axe est **unique**
(les mécanismes de récupération), **fermé** et **fixé a priori** ; un cas porte
un mécanisme et un seul.

| # | Mécanisme | Source du label | En `0.0.1` ? |
|---|---|---|---|
| 1 | `resolution_reference` | `identite` | ✅ 30 cas |
| 2 | `known_item_identifiant` | `identite` | ✅ 30 cas |
| 3 | `traversee_simple` (1 saut) | `graphe_g0` | ✅ 30 cas |
| 4 | `traversee_chainee` (profond) | `graphe_g0` | ❌ **0 cas** — déclaré, non peuplé ([#16](https://github.com/left-eyebr0w/murphy/issues/16)) |
| 5 | `absence_attendue` | frontière de **périmètre DILA** | ✅ 30 cas, `R = 0` |
| 6 | `concept_vers_instance` | **aucune — jugé** | ✅ 30 cas, le noyau jugé |
| 7 | `desambiguisation` | — | ❌ hors `0.0.1`, rappel en `0.a.2` ([#9](https://github.com/left-eyebr0w/murphy/issues/9), [#20](https://github.com/left-eyebr0w/murphy/issues/20)) |

> ⚠️ **La renumérotation n'est pas écrite.** Elle est due en ADR-036 ; la table
> ci-dessus est **reconstruite depuis les résolutions** (#2, #10, #16, #15, #12).
> Deux **opérations** d'ADR-030 sont par ailleurs sans producteur en `0.0.1` —
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
domicile **ADR-038 — désormais livrable bloquant du jalon v0**, voir *Les deux
livrables promus* plus bas).

- **Deux objets distincts** : l'*intra* mesure la **stabilité** (résolution de
  l'instrument) ; l'*inter* mesure l'**extériorité du critère** — il est le
  **falsificateur de R-05**. Donc **+0,49 ne transfère pas** de l'un à l'autre.
  ⚠️ Conséquence de la campagne *inter* avancée en `0.a.1` (§3.1.2) : **ADR-038
  doit trancher l'ancre propre de l'*inter*** — le +0,49 du Legal Track 2006 est
  nativement un chiffre *inter*, employé ici comme borne conservatrice pour de
  l'*intra*. Le seuil doit être **fixé avant la campagne**, pas découvert pendant.
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
  l'instrument de l'assesseur via le champ `narrative`. Il **n'existe pas** —
  `ADR-008.guide_version` pointe vers un document inexistant — et c'est
  précisément pourquoi il devient **livrable bloquant du jalon v0**.

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

**Le contrat de la machine B — avancé ici.** La machine B se coupe en deux moitiés
qui n'ont pas les mêmes prérequis, et **seule la première remonte** :

| Moitié | Ce qu'elle exige | Domicile |
|---|---|---|
| **le contrat** — un run étranger est recevable, notable, poolable | ADR-008, **déjà écrit** | **jalon v0** |
| **la campagne** — équipes plurielles, *call for participation*, accord de diffusion, outils partagés | l'association (ADR-015) et le chantier 8 | majeur 1 (§3.2.3) |

`VERSIONS.md` l'autorisait déjà en toutes lettres : *« ce qui, côté B, n'a besoin
que du **contrat**, peut se construire **dès maintenant** »*. Trois motifs le
placent ici plutôt qu'ailleurs :

- **« Rien à jeter » cesse d'être terminal.** ADR-035 demande à la collection de
  survivre à l'ouverture sans redesign. Tant que le contrat arrive en fin de
  trajectoire, ce critère est une **promesse invérifiable jusqu'au moment où
  l'échouer coûte le plus cher**. Au jalon v0 il devient une **contrainte de
  conception** : rien ne peut plus être décidé solo-only, il y a un tiers dans la
  pièce à chaque décision. *Un critère terminal ne peut qu'être échoué tard ; une
  contrainte de conception ne peut pas être échouée du tout.*
- **L'ordre du pooling.** La composition du pool doit être arrêtée **avant** de
  dépenser le budget d'assessment — et ce budget se dépense **ici**. Un run externe
  arrivant après les qrels remonterait des documents non jugés, déclencherait le
  refus *« top-`k` majoritairement non jugé »*, et obligerait à refinancer une
  campagne.
- **Le hash `corpus` ne bouge pas encore.** Il bouge en beta (§3.1.4). Faire
  démarrer la réception de runs étrangers à cheval sur un rejeu ferait perdre sa
  comparabilité au premier tiers en cours de route.

**Exercé solo, porteur à deux casquettes** : on produit un run, on le fait entrer
par le chemin externe, on le note. C'est exactement la structure déjà retenue pour
l'essai de l'appareil d'assessment.

⚠️ **Le contrat bloque, la fréquentation jamais.** Bloquer sur *« un run externe
réel a été reçu »* ferait **dépendre la livraison d'un tiers**, et la propriété
solo de la machine A tomberait (ADR-035). Bloquer sur *« le contrat existe et a été
exercé »* ne dépend que du porteur.

**Les deux livrables promus.** Deux artefacts que la carte laissait « non écrits »
deviennent **bloquants pour la clôture du jalon** :

- **le guide d'annotation** — à écrire *ex nihilo*, avec ses huit contraintes de
  rédaction ;
- **ADR-038** — la machinerie *inter* (troisième compartiment, séparateur, table de
  réparation q2/q3) **et son ancre propre**.

S'y ajoute l'exigence que l'**appareil *inter* ait été exercé à blanc**, porteur à
deux casquettes.

Ce qu'on achète : qu'un assesseur **s'enfiche sans redesign**. C'est le critère
« rien à jeter » appliqué à un **second consommateur** — on l'avait pour les runs
étrangers, on l'a pour les assesseurs. *Même critère, deux portes.* Sans ces deux
documents, des candidats disponibles n'ont **rien où se brancher** au jalon v0 et
devraient être accueillis dans un appareil improvisé — précisément le redesign que
le critère interdit.

⚠️ **Là encore : l'appareil bloque, la participation jamais.** Le jalon ne peut pas
exiger qu'un second assesseur soit venu, pour la même raison qu'il ne peut pas
exiger un run étranger.

> **L'invariant, posé pour la troisième fois.** *« v0 n'est otage d'aucun
> résultat »* (lecture instrument, #20 §6) · *« l'appareil existe **et a tourné** »*
> (PT-06) · *« le contrat bloque, la fréquentation jamais »*. Trois cas, une seule
> règle : **on ne conditionne jamais une clôture à ce qu'on ne contrôle pas.** Elle
> mérite d'être énoncée une fois en ADR-036 plutôt que re-dérivée à chaque jalon.

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
peut intervenir dès le jalon v0, ce qui est exclu étant d'en **dépendre pour
livrer**. ⚠️ **Cette propriété vit au *jalon*, pas dans tout le majeur 0** (§2.3) :
des gens jugent dès `0.a.1`, et la propriété n'en tombe pas — elle ne portait
jamais que sur ce dont la **livraison du jalon v0** dépend.
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

**Ce qui n'est pas écrit au jalon v0** — matériau direct pour §5, désormais en
**deux tas de statuts opposés** :

| | Artefacts | Statut |
|---|---|---|
| **Bloquants** | **le guide d'annotation** (inexistant) · **ADR-038** (machinerie *inter* + ancre propre) | la clôture du jalon en dépend |
| **Dus, non bloquants** | ADR-036 (contenu, cimetière, P-01–P-04, renumérotation) · **ADR-032 réécrit** (intake, règle champ → hash) · la **table champ → hash** en `GOLDEN-SET.md` §3 · un **marqueur sur ADR-030** | dus sans l'être |

*Deux des six artefacts dus passent bloquants. C'est un élargissement assumé du
jalon, et le §5 doit l'attaquer comme tel.*

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
| **PT-31** | **Le contrat de recevabilité existe et a été exercé.** Un run étranger est projetable, notable et poolable — démonstration solo, porteur à deux casquettes | ADR-008 · [#18](https://github.com/left-eyebr0w/murphy/issues/18) §8 |
| **PT-32** | **L'appareil d'assessment *inter* existe, est écrit et a tourné à blanc** — il n'est pas une intention | ADR-038 · guide d'annotation · PT-06 appliqué à l'*inter* |

**⊙ Ce que le jalon v0 tient en puissance** — *l'appareil est là, il ne manque
qu'un acte d'un tiers*

| id | Énoncé | Déclencheur | Bascule *en acte* |
|---|---|---|---|
| **PT-11** ⊙ | **L'extériorité du critère.** *Une seule tête ne peut pas constater qu'un critère sort d'elle* — mais le protocole, le guide et l'ancre existent | un **second assesseur** juge les mêmes items en file poolée | `0.a.1` (§3.1.2) |
| **PT-12** ⊙ | **Le biais de pool est mesurable** — le leave-one-out n'attend qu'un contributeur qui ne soit pas le porteur | **une** soumission externe reçue | date non promise |
| **PT-27** ⊙ | **Réutilisable par un tiers *sans renégociation*.** PT-31 établit la recevabilité ; que personne n'ait à renégocier ne s'établit que si quelqu'un essaie | un tiers réel soumet et note | majeur 1 (§3.2.4) |

> ⚠️ **PT-11 aurait échoué à la porte hier.** Le guide n'existait pas, donc il
> restait du travail au porteur, donc c'était un ⊘ ordinaire. C'est la promotion
> des deux livrables qui le fait basculer — **la porte discrimine, elle n'est pas
> décorative.**

**⊘ Ce que le jalon v0 ne prétend pas** — *par décision ; rien n'attend*

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-08** ⊘ | Le jeu **n'estime pas la performance en production** — un chiffre nu, non pondéré | [#4](https://github.com/left-eyebr0w/murphy/issues/4) (§6.2 mort par YAGNI du porteur) |
| **PT-09** ⊘ | Le jeu **n'échantillonne pas le droit** : il énumère des fonctions. **Aucun cadre d'échantillonnage**, donc aucune capacité de chiffrer un trou | ADR-034 §1 · #4 |
| **PT-10** ⊘ | **`R` n'est pas estimé** — aucun rappel absolu n'est prétendu | [#18](https://github.com/left-eyebr0w/murphy/issues/18) §7b |
| **PT-13** ⊘ | **La justesse du chiffre est hors périmètre** — reproductibilité seule | ADR-028 · E-P2-10 |

> **Les quatre survivants sont tous des décisions**, pas des attentes : aucun tiers
> ne peut arriver et les retourner. C'est le gain de la troisième colonne — ⊘
> retrouve **un** sens.

#### 3.1.2 Alpha ph.1 — « Usage & requêtes réelles » — `0.a.1`

Les cas ne changent pas. **Cinq** choses leur arrivent :

- **`p` devient révisable.** Déclaré *ex ante* depuis le lecteur au jalon v0, il
  se révise ici — **c'est le premier jalon où la persistance réelle s'observe**.
- **Une seconde tête entre.** Les notations `origin: inline` (cascade q1→q3,
  ADR-005/010) font entrer des jugements qui ne viennent pas du porteur.
- **La campagne *inter* poolée tourne ici** — remontée de l'alpha ph.2, parce que
  l'appareil est livré au jalon v0 (PT-32) et que les assesseurs sont disponibles
  dès ici. **C'est le déclencheur de PT-11.** Ce que ça achète : si le critère
  n'est **pas** extérieur, on l'apprend quand la collection fait 150 cas et se
  réécrit encore — au lieu de l'apprendre après avoir financé la campagne
  canonique. *Troisième application du même geste : déplacer un test vers
  l'endroit où l'échouer coûte le moins.*
- **Le pool de requêtes réelles se constitue** : c'est la matière de `0.a.2`, pas
  un ajout aux cas d'ici.
- Le **run archivé daté avant l'ouverture du panel** ([#5](https://github.com/left-eyebr0w/murphy/issues/5) §8c)
  attend ici son consommateur, qui n'arrive qu'en beta.

> **Deux bornes sur la campagne *inter* d'ici, à ne pas franchir en la lisant.**
>
> 1. **Elle tourne à `n = 2`.** On mesure le désaccord, on exerce le séparateur, on
>    remplit le troisième compartiment — mais on **ne peut pas distinguer une
>    divergence professionnelle légitime d'une erreur d'assesseur**. Ça exige
>    `n ≥ 5`, et ça reste en `0.a.2` (PT-20). *L'extériorité se mesure ici, la
>    légitimité de la divergence attend.*
> 2. **Elle porte sur les 30 cas jugés du jalon v0**, pas sur les requêtes réelles
>    — celles-ci se collectent pendant la phase, elles n'existent pas encore quand
>    la campagne tourne. PT-19 doit donc nommer sa population, faute de quoi il
>    prétend **plus** ici qu'il ne prétendait en ph.2.

##### Ce que l'alpha ph.1 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-14** | **`p` cesse d'être déclaré et devient observé** — la persistance du lecteur est mesurée, plus postulée | révision de `p` en ph.1 ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) |
| **PT-15** | Un **pool de requêtes réelles** existe, non dérivé du porteur | critères de sortie ph.1 · ADR-013 |
| **PT-16** | Des **jugements viennent d'une autre tête** que celle qui a écrit les cas | mode inline, `origin: inline` (ADR-005/010) |
| **PT-19** | **R-05 reçoit un falsificateur en acte** : l'*inter* mesure l'**extériorité du critère** **sur le noyau jugé du jalon v0**, ce que le solo ne pouvait pas. PT-11 bascule ⊙ → en acte | campagne *inter* poolée ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) · ADR-038 |

**⊘ Ce que l'alpha ph.1 ne prétend pas**

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-17** ⊘ | **L'inline n'est pas ce qui mesure l'extériorité** — c'est la file poolée d'à côté, au même jalon. Seule elle distingue ses **deux consommateurs** (lecteur *différent* obligatoire pour l'extériorité · *même* lecteur obligatoire pour l'auto-cohérence). Une non-prétention **de l'inline**, non du jalon | ADR-010 · #19 |
| **PT-33** ⊘ | La **légitimité** d'une divergence n'est pas établie ici : à `n = 2`, un désaccord q2/q3 survivant à la réconciliation est **enregistré, non qualifié** | bascule `n ≥ 5` en `0.a.2` (PT-20) |

#### 3.1.3 Alpha ph.2 — `0.a.2`

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
- **L'*inter* change d'échelle, il ne naît pas ici.** Il a reçu son premier
  falsificateur en `0.a.1` (PT-19), à `n = 2` et sur le noyau jugé du jalon v0. Ce
  que ph.2 ajoute : **`n ≥ 5`** et la **population des requêtes réelles**.

##### Ce que l'alpha ph.2 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-18** | Les qrels sont **canoniques** — expertes, poolées, calibrées | mode campagne (ADR-010) · critères de sortie ph.2 |
| **PT-20** | La **divergence légitime est observable** — un 3-2 se distingue d'un 4-1. C'est ce que `0.a.1` ne pouvait pas (PT-33 ⊘) | bascule à `n ≥ 5` |
| **PT-21** | Le passage `0.0.1` → `0.a.2` **n'a rien jeté** : `p` monte seul, `d_min` garde les runs, la re-notation répare gratuitement | [#20](https://github.com/left-eyebr0w/murphy/issues/20) · ADR-032 §2 |
| **PT-34** | L'extériorité est constatée **sur la population des requêtes réelles**, et non plus sur le seul noyau jugé du jalon v0 | qrels canoniques sur le pool de ph.1 |

#### 3.1.4 Beta — « Valeur d'usage » — `0.b.1`

**C'est ici que le corpus bouge**, et c'est le seul jalon du majeur 0 où il bouge.
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

### 3.2 Majeur 1

#### 3.2.1 Association (ADR-015)

Jalon organisationnel, entre beta et publication. Aucun contenu de collection —
mais **c'est la frontière où le porteur cesse d'être structurellement seul**, et
donc où l'enfichabilité conçue par #18 et #21 (*porteur seul → panel ADR-025 →
communauté*) change d'occupant.

#### 3.2.2 Publication — « Exhaustivité DILA » (ADR-014)

Toutes les bases DILA ingérées. Deux conséquences pour la collection :

- **`pending` se vide par construction** — il n'y a plus de « dans DILA, non
  ingéré ».
- **L'alarme de #15 change de sens** : la séparation *`pending` non scoré ↔ hors
  périmètre scoré*, qu'`absence_attendue` porte dans son nom, perd son premier
  terme. Ce que l'alarme signale après publication n'est plus le même événement.

#### 3.2.3 Machine B — la **campagne** communautaire

⚠️ **Ce jalon a perdu une moitié.** Le **contrat** de recevabilité est remonté au
jalon v0 (§3.1.1, PT-31). Ce qui reste ici est la **campagne** : des équipes
indépendantes soumettent des runs concurrents, poolés et jugés.
**Structurellement plurielle**, donc **hors machine A**. A précède B ; l'inclusion
`B ⊃ A` a été retirée, la frontière est le contrat — désormais déjà bâti.

**Ce que la coupe résout, et ce qu'elle ne résout pas.** `VERSIONS.md` §Statuts non
finaux enregistre comme point ouvert que les critères de sortie de B ne peuvent pas
s'énoncer honnêtement, aucun effectif d'équipes n'étant fondé une fois le régime du
NIST écarté (R-09). **Cette objection portait sur un critère d'affluence, jamais
sur un appareil** : le contrat, qui ne dépend que du porteur, part donc en v0, et
le point ouvert reste ouvert — mais il ne concerne plus que la campagne, et il ne
retient plus rien d'autre en otage. **La machine B cesse d'être un événement à
caser ; il ne reste à placer que sa moitié plurielle.**

**Le biais de pool ne naît plus ici** : il est mesurable dès la première soumission
externe reçue (PT-12 ⊙, jalon v0). Ce que la campagne ajoute est **l'échelle** —
plusieurs systèmes non contributeurs au lieu d'un.

⚠️ Réserve portée par #17 : au Legal Track, des *Topic Authorities* dotées de
**10 h par équipe et par topic** ont été **sous-consommées** — *« very few of the
teams used a significant portion of the ten hours »*. Même une aide gratuite,
offerte, adossée au NIST, n'a pas été prise.

#### 3.2.4 Ce que le majeur 1 prétend établir

| id | Énoncé | Porté par |
|---|---|---|
| **PT-26** | Le **périmètre annoncé est atteint** — l'exhaustivité DILA est un critère de **publication**, et c'est ici qu'il se constate | ADR-014 · `VISION.md` §2 |
| **PT-27** | **Bascule ⊙ → en acte.** Un tiers réel a soumis et noté **sans renégociation** — ce que PT-31 ne pouvait qu'armer | contrat exercé par un tiers · [#18](https://github.com/left-eyebr0w/murphy/issues/18) §8 |
| **PT-28** | Le biais de pool est mesurable **à l'échelle** — plusieurs systèmes non contributeurs, non plus un seul | pluralité de la campagne · [#7](https://github.com/left-eyebr0w/murphy/issues/7) *a contrario* |
| **PT-29** | La collection **survit à l'ouverture sans redesign**. ⚠️ Ce n'est plus un **terminal** : le contrat étant bâti au jalon v0, « rien à jeter » y est devenu une **contrainte de conception**, vérifiée en continu. Ce qui se constate ici est qu'elle a **tenu** | ADR-035 §6 · PT-31 |

**⊘ Ce que le majeur 1 ne prétend pas**

| id | Énoncé | Source du renoncement |
|---|---|---|
| **PT-30** ⊘ | **Aucun effectif d'équipes n'est promis.** Un critère « ≥ N équipes externes » supposerait un `N` que rien ne fonde : le seul disponible est celui du NIST, dont le **pouvoir de convocation ne transfère pas**. La réserve #17 (des *Topic Authorities* gratuites, adossées au NIST, **sous-consommées**) en est le précédent | `VERSIONS.md` §Statuts non finaux · ADR-035 §3 · R-09 |

> ⚠️ **Le majeur 1 s'est aminci, et c'est assumé.** PT-27, PT-28 et PT-29 n'y
> **naissent** plus : ils y **basculent** ou y **changent d'échelle**. Reste PT-26
> comme seule prétention native — *« on a ingéré le reste de DILA »*. Ce n'est pas
> malhonnête, c'est mince, et tout le schéma de nommage (§2.2) suspend le majeur 1
> à ce jalon. **Point d'attaque prioritaire pour le §5.**

### 3.3 Majeur 2 — l'horizon

Nommé, non détaillé. Rien de ce que la carte a décidé ne s'y projette, et rien
n'y est promis. Il est ici pour que le document ne se lise pas comme si la
trajectoire s'arrêtait à la campagne communautaire.

**Aucune prétention** — ni positive, ni ⊙, ni ⊘. C'est la seule case du registre
`PT-` qui soit vide, et elle l'est par construction, non par oubli.


