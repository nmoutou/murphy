# Le golden-set Murphy — conception, dimensionnement, cycle de vie

> Document **permanent**. Décrit ce qu'est le golden-set, ce qu'il mesure,
> comment il est dimensionné et comment il vit. Les décisions qu'il applique
> vivent en ADR (004 à 008, 017, 028 à 032) ; les chiffres et leur dérivation
> vivent ici.
>
> **Statut** : v1 en construction (B-08). Les nombres du §7 sont une
> proposition dérivée, pas une décision actée — ils relèvent du régime
> **humain** (ADR-028) et attendent validation du porteur.

---

## 1. Ce que c'est

Une **collection de test de Recherche d'Information** au sens classique : le
triplet `(corpus, questions, jugements de pertinence)`. En découplant
récupération et génération (ADR-016), Murphy n'évalue pas « du RAG » mais un
problème IR ordinaire — toute la méthodologie TREC s'applique, outillage
compris.

Le golden-set est **unique** (ADR-017). On ne multiplie pas les golden-sets par
brique technologique : on mesure le **delta** de chaque brique sur le *même*
jeu. Les sets diagnostiques (graph-hop, co-citation) sont des instruments
séparés, à côté, jamais des variantes du jeu principal.

---

## 2. La doctrine : on spécifie l'usage, pas le stock

Trois distributions coexistent et divergent fortement.

| | Nature | Biais propre |
|---|---|---|
| **D₁ — contentieux réel** | Volume d'affaires portées devant un juge | Dominé par les atteintes aux biens (35,1 % du socle), dont la majorité sans auteur identifié, donc quasiment sans jurisprudence publiée |
| **D₂ — empreinte documentaire** | Volume de documents effectivement ingérés | Reflète les choix d'ingestion et les biais éditoriaux des bases, pas le besoin |
| **D₃ — questions réellement posées** | Besoin de décision des utilisateurs | Non observable avant l'alpha ph.1 ; gouverné par l'enjeu, non par la fréquence |

**Le jeu se construit sur D₃, approché par D₁ corrigé. D₂ est écarté comme
entrée de conception.**

C'est la décision structurante de ce document, et elle a une raison de fond :
dimensionner depuis le corpus laisserait **l'ingestion définir ce qu'on
mesure**. L'instrument suivrait l'objet — la circularité qu'ADR-029 écarte
pour la strate 2, et qu'ADR-031 écarte pour le graphe, revenue par la porte
du corpus.

**Conséquence assumée, et c'est un bénéfice :** le golden-set est écrit
**avant** l'ingestion étendue. Une question dont la cible exige une base non
encore ingérée n'est pas un défaut du jeu — c'est une **exigence adressée à
l'ingestion** (voir §10). Le jeu cesse d'être un miroir du corpus pour devenir
une spécification de ce que Murphy doit savoir répondre.

**Bénéfice secondaire, structurel** : écrire les questions sans avoir les
documents sous les yeux rend le piège de la **requête-décalque** (P-01,
`WIP/B-08-cadrage.md`) matériellement impossible. On ne décalque pas un
document qu'on n'a pas. Le risque résiduel est inverse et bénin — une question
sans cible, qui reste `pending` jusqu'à ce que l'ingestion la serve.

> ⚠️ Le corpus revient en fin de chaîne, et à un seul titre : **ordonnancer
> l'effort d'annotation** (quelles questions sont jugeables aujourd'hui). Le
> même déplacement de rôle que le pooling a subi avec ADR-032 — de levier de
> complétude à ordonnanceur.

---

## 3. Trois couches, trois régimes de gel

Le jeu n'est pas un fichier mais un empilement. La règle de partage est celle
d'ADR-030 : *enregistrer ce qui a coûté une lecture, dériver tout le reste*.
Test opérationnel — **« si je change d'avis là-dessus, dois-je rouvrir les
documents ? »**

| Couche | Contenu | Coût | Gel |
|---|---|---|---|
| **Questions** | Texte, `intention`, `matière`, `registre`, date pivot | Rédaction | Gelée, hashée |
| **Jugements** | `q1/q2/q3` par arête, `grade` dérivé, `source`, `origin`, `annotator` | **Lecture — poste dominant** | Gelée, hashée (ADR-008) |
| **Dérivations** | 5 opérations dérivées, taxonomie, définition des strates | Calcul | **Versionnée à part** |

*Figé* et *révisable* ne s'opposent pas : ils ne portent pas sur le même objet
(ADR-030, ADR-032). Les dérivations se recalculent à la demande depuis le
graphe témoin `G₀` (ADR-031) — jamais ingérées, jamais annotées.

La couche **questions** est propre à ce document : ADR-030 note qu'aucune
classe `Query` n'existe dans `eval/` et que l'axe intention est du terrain
vierge. C'est ici qu'il se peuple.

---

## 4. Les deux axes

ADR-030 fixe la structure, et elle n'est pas celle qu'on attend d'un jeu de
test classique.

| Axe | Porté par | Cardinalité |
|---|---|---|
| **Intention** | la requête | une seule |
| **Opérations** | l'arête `(requête, source, cible)` | plusieurs par requête |

**Le second axe ne partitionne pas les requêtes.** Une question sur le congé
pour vente porte une arête `texte_applicable` *et* une arête
`jurisprudence_applicable` : une requête, deux cases remplies. C'est pourquoi
on ne peut pas dériver un nombre de requêtes en multipliant les axes — voir §7.

Huit opérations, dont **trois seulement sont jugées** :

| Jugées (coûtent une lecture) | Dérivées (calculées depuis `G₀` ou la requête) |
|---|---|
| `texte_applicable` | `known_item`, `graph_hop`, `contexte_structurel`, `succession_temporelle`, `fondement_textuel` |
| `jurisprudence_applicable` | |
| `definition` | |

**La surface d'annotation est donc `matière × 3`, pas `matière × 8`.**

### 4.1 Où sont passés les « types de difficulté »

Une conception antérieure (`docs/droit/stats/`, 23 juillet 2026) proposait six
« types de difficulté de retrieval » T1–T6 comme second axe. Ils ne sont pas
perdus, mais ils ne sont pas un axe : ils mêlent **quatre natures d'objet
différentes**, ce qui explique l'inconfort du croisement.

| Type d'origine | Ce qu'il est réellement | Où il atterrit |
|---|---|---|
| T1 — Identifiant | Une opération **dérivée** | `known_item` (ADR-030 #4), calculée depuis le texte de la requête |
| T2 — Langage courant | Un **registre** | Champ `registre` sur la question (§6.3) |
| T3 — Polysémie | Un **fait constatable** sur le vocabulaire | Flag `polysemique`, avec ses référents concurrents (§8.4) |
| T4 — Temporel | Une opération **dérivée** + une date | `succession_temporelle` + date pivot (§6.4) |
| T5 — Multi-base | Une **propriété émergente** | Non-exclusivité des opérations : la question porte les deux arêtes |
| T6 — Négatif | Une **propriété des qrels** | Sous-ensemble à part, hors métrique primaire (§8.1) |

L'axe *difficulté* comme tel est supprimé (ADR-030) : étiqueter une requête
« difficile » enregistre une impression, et l'étiquette **absorbe la question
qu'elle prétend documenter**. T3 survit précisément parce qu'il est le seul des
six à être **constatable** : « ce terme a trois référents dans les
nomenclatures officielles » est un fait, pas un degré.

---

## 5. Les intentions

Vocabulaire proposé, à valider. Une intention par question, obligatoire
(E-P2-07). Le critère de bonne intention est qu'elle décrive **ce que
l'utilisateur veut**, jamais comment la réponse est atteinte.

| Intention | Ce que l'utilisateur veut | Opérations typiquement portées |
|---|---|---|
| `trouver_la_regle` | Quelle norme régit ma situation | `texte_applicable` |
| `verifier_une_solution` | Comment le juge a tranché ce cas | `jurisprudence_applicable`, souvent + `fondement_textuel` |
| `definir_un_terme` | Que signifie ce mot en droit | `definition` |
| `retrouver_un_document` | J'ai la référence, donne-moi le texte | `known_item` |
| `connaitre_une_procedure` | Comment agir, dans quel délai, devant qui | `texte_applicable` (CPC, CJA, CPP) |

`connaitre_une_procedure` mérite d'exister séparément : la procédure n'est le
sujet d'aucune nomenclature statistique officielle, et elle est pourtant une
part majeure des pourvois et du contentieux administratif. Sans intention
dédiée, elle reste un angle mort par construction.

> Intention et opération se **corrèlent sans se confondre** : une même
> intention `trouver_la_regle` peut être satisfaite par un article ou par une
> décision qui l'interprète. C'est exactement pourquoi il faut deux axes.

---

## 6. Les matières

### 6.1 Douze strates

Reprises de l'analyse statistique (RSJ 2025, Chiffres clés 2025, Chiffres clés
JA 2025), refondues pour l'usage documentaire. La nomenclature d'origine était
exhaustive sur les **affaires** ; elle manquait deux pans entiers.

| # | Strate | Poids D₁ |
|---|---|---|
| S1 | Pénal — atteintes aux personnes et aux biens | 52,31 % |
| S2 | Pénal — routier, santé publique, environnement, ordre public | 16,47 % |
| S3 | Personnes, famille, état civil, protection des majeurs | 11,30 % |
| S4 | Contrats, obligations, responsabilité, consommation | 1,76 % |
| S5 | Biens, baux, copropriété, immobilier, urbanisme | 2,17 % |
| S6 | Travail et protection sociale | 4,13 % |
| S7 | Affaires, sociétés, entreprises en difficulté | 1,84 % |
| S8 | Fiscal et finances publiques | 0,22 % |
| S9 | Étrangers, asile, nationalité | 2,98 % |
| S10 | Fonction publique et droit administratif général | 0,51 % |
| S11 | Libertés publiques, données personnelles, constitutionnel | **0 %** |
| S12 | Procédure et contentieux (civile, pénale, administrative) | **0 %** |
| — | *Résidu non rattachable* | 6,32 % |

Les poids bouclent exactement sur un socle homogène de **6 162 985 affaires
nouvelles 2024** (même unité, même millésime, aucun recoupement entre piliers).
Table de correspondance détaillée : `WIP/analyse.md`.

**S11 et S12 pèsent 0 % et sont pourtant retenues.** C'est la démonstration la
plus nette de la doctrine du §2 : elles sont absentes de la statistique des
affaires parce que personne ne saisit un tribunal pour connaître le RGPD ou le
délai d'un référé — ce sont des besoins d'**information**, pas de litige. Les
omettre reviendrait à laisser la statistique judiciaire définir le produit.

### 6.2 Le tirage est uniforme, la pondération vient au rapport

**On échantillonne pour le pouvoir diagnostique, on pondère au moment du
rapport.** Un plancher par case garantit que chaque strate dit quelque chose ;
les poids D₁ ne sont jamais une clé d'allocation.

Deux chiffres sortent d'un jeu unique :

- un **score de diagnostic**, non pondéré, lisible strate par strate ;
- un **score d'estimation production**, repondéré par les poids ci-dessus.

Ce n'est pas une commodité mais une propriété de coût : un poids gravé dans
l'échantillonnage est irréversible sans réécrire le jeu, alors que changer
d'avis sur la représentativité au rapport est un changement de **classe 1**
(ADR-032) — re-notation seule, zéro re-récupération.

> ⚠️ Une ventilation (par strate, par base, par opération) est une **mesure
> distincte à dénominateur propre**. Restreindre les qrels à un sous-ensemble
> change `R`, donc la coupe adaptative de nDCG@R (ADR-007, ADR-030). Deux
> ventilations ne se comparent ni entre elles ni à l'agrégat. À énoncer dans
> chaque rapport.

### 6.3 Registre

Chaque question porte un registre, `praticien` ou `citoyen`, à parts
approximativement égales. Le registre n'est pas décoratif : l'écart lexical
entre la formulation profane et la rédaction normative est le premier facteur
d'échec d'une recherche vectorielle en droit.

### 6.4 Date pivot

Chaque question porte une **date de référence**, figée. LEGI est versionné :
sans date pivot, les qrels se dégradent silencieusement à chaque modification
législative. C'est le premier poste de dette technique d'un golden-set
juridique, et il ne se rattrape pas — un jugement rendu sans date de référence
n'est pas ré-interprétable après coup.

---

## 7. Dimensionnement

### 7.1 Deux volumes, pas un

C'est le point central de ce document, et la correction principale apportée à
la conception antérieure.

| | Ce que c'est | Ce qui le contraint |
|---|---|---|
| **N_q** | Questions **écrites**, présentes dans l'artefact et interrogées à chaque run | Couverture de la matrice · coût de l'ajout ultérieur |
| **N_j** | Questions **jugées**, donc scorables, dans une version donnée | Budget d'annotation · puissance statistique (B-10) |

`N_j ≤ N_q`, et l'écart n'est pas une dette : c'est le régime normal. Une
question écrite mais non jugée est **utile dès sa rédaction** — elle est
interrogée, ses résultats sont archivés dans chaque run, et le jour où on la
juge, il n'y a rien à re-récupérer.

### 7.2 Pourquoi écrire large et juger étroit

ADR-032 classe les changements par coût. Une quatrième ligne s'en déduit, et
elle commande tout le dimensionnement :

| Changement | Re-récupération ? | Historique comparable ? |
|---|---|---|
| Corriger un grade, réviser le guide, re-dériver | Non | Oui |
| Juger des documents supplémentaires sur une question existante | Non | Oui |
| **Juger une question déjà présente dans les runs** | **Non** | **Oui** |
| **Ajouter une question au jeu** | **Oui** | Non, sauf rejeu des configs |

La troisième ligne ne figure pas telle quelle dans ADR-032 ; elle s'en déduit
de sa prémisse — *un run est `question → documents ordonnés`, il ne contient
aucun jugement*. Si la question était dans le run, ses résultats y sont déjà.

**Conséquence directe : écrire 170 questions maintenant et en juger 60 coûte
strictement moins, sur la durée, qu'en écrire 60 maintenant et 110 plus tard.**
Le premier scénario paie une fois le seul poste cher ; le second le paie deux
fois.

> Réserve honnête : si l'ingestion s'étend entre deux versions, `W` change
> (ADR-027, ADR-031) et un rejeu est de toute façon nécessaire. L'argument ne
> supprime pas ce rejeu — il garantit qu'il reste le **seul** coût, et qu'il
> n'est pas doublé par un lot de questions tardives.

### 7.3 Dériver N_q

L'ancienne conception calculait `12 strates × 6 types × 4 requêtes = 288`. Le
produit est invalide sous ADR-030 : **le second facteur n'est pas une partition
des requêtes** (§4). Une requête porte plusieurs opérations à la fois ;
multiplier suppose qu'elle n'en porte qu'une.

La dérivation correcte alloue sur `matière × intention` — les deux axes qui
sont bien des propriétés de la requête — et **vérifie** ensuite la couverture
en opérations.

```
Allocation      12 matières × 5 intentions × 2 questions     = 120
Isosémantiques  sur sous-ensemble citoyen (S1, S3, S5, S6)   ≈  20
Strate-frontière  questions à cheval sur deux matières       ≈  15
                                                             ─────
N_q (scorables)                                              ≈ 155

+ Négatives / hors-corpus, HORS métrique primaire (§8.1)     ≈  20
```

**Vérification ex post, non allocation** (E-P2-07) : une opération au moins sur
100 % des arêtes ; les trois opérations jugées non vides dans chaque matière.
Si une matière ne produit aucune arête `jurisprudence_applicable`, c'est un
constat à corriger en ajoutant des questions à cette case — pas une case à
remplir mécaniquement.

Le résultat tombe dans le même ordre de grandeur que les 288 d'origine. **Le
chiffre n'était pas absurde ; sa dérivation l'était.** Et la distinction N_q /
N_j, elle, change tout : les 288 étaient présentés comme un objectif
d'annotation.

### 7.4 Dériver N_j — la puissance statistique

C'est le seul plancher qui ne dépende ni du corpus ni du budget, donc le seul
qu'on puisse poser *a priori*. B-10 compare deux configurations par un test
apparié ; sur `n` requêtes, l'effet minimal détectable suit `n ≈ 7,85 / d²`
(α = 5 % bilatéral, puissance 80 %).

| Effet détectable | n requêtes jugées |
|---|---|
| d ≈ 0,5 — net | ~31 |
| d ≈ 0,35 — modéré | ~64 |
| d ≈ 0,25 — fin | ~126 |
| d ≈ 0,2 — très fin | ~196 |

**N_j(v1) ≈ 60–70.** C'est le premier palier qui détecte un effet modéré, soit
le besoin réel quand on départage deux configurations de récupération. En
dessous de 30, le test ne conclut que sur des écarts grossiers ; au-delà de
130, on achète une finesse que le budget d'annotation solo ne peut pas
alimenter et que le bruit d'annotation solo rendrait illusoire.

> Ces valeurs sont des ordres de grandeur. B-10 emploiera vraisemblablement un
> test de permutation, les deltas de nDCG n'étant pas normalement distribués ;
> le calibre reste le même.

**Sélection du sous-ensemble jugé** : une **carotte** à travers la matrice, pas
un bloc. Juger 60 questions concentrées sur trois matières donnerait 60
questions et un jeu qui ne dit rien des neuf autres. Le tirage prend au moins
une question par case `matière × intention`, puis complète.

### 7.5 Croissance

| Version | N_q | N_j | Ce qui change |
|---|---|---|---|
| v1 | ~155 | ~60–70 | Gel initial, jugements sur le corpus disponible |
| v2+ | ~155 | croissant | Jugements supplémentaires — **gratuits** (§7.2), corrections de grades au fil de l'eau |
| v_n | révisé | — | Ajout d'un lot de questions, **à un moment choisi**, suivi d'un rejeu des configurations de référence |

Les corrections de jugement se font au fil de l'eau et n'invalident rien. Les
ajouts de questions se font **par lots**, jamais à l'unité.

---

## 8. Sous-ensembles hors quota

### 8.1 Questions négatives — pourquoi elles sortent du total

Une question dont la bonne réponse est *aucun résultat pertinent* (droit
étranger, hors périmètre DILA) a `R = 0` documents pertinents. Or nDCG@R coupe
le classement à `R` (ADR-007) : **la coupe est indéfinie, la métrique aussi.**

Ces questions ne peuvent donc pas entrer dans le jeu primaire. Elles forment un
**diagnostic de précision séparé**, mesuré autrement (taux de résultats au-delà
d'un seuil de score, sur un jeu où toute remontée est un faux positif) — le
même statut que le diagnostic de co-citation (ADR-029) : précision seulement,
jamais de rappel, jamais de grade.

Sans elles, le jeu ne mesure que le rappel et jamais la précision. C'est le
sous-ensemble le plus souvent omis, et le moins cher à produire.

### 8.2 Paires isosémantiques — sur sous-ensemble

Une même question de droit, **des qrels identiques**, deux formulations : l'une
praticien, l'autre citoyen. Le delta de score entre les deux membres donne **le
coût du décalage de vocabulaire en un seul nombre**, mesurable strate par
strate.

Économiquement, c'est le meilleur rapport du jeu : le poste cher (les
jugements) est **partagé**, seule la rédaction est dupliquée.

Retenues sur un **sous-ensemble** — les matières où l'écart de registre est le
plus large, donc les plus exposées au public : S1 (pénal courant), S3 (famille),
S5 (logement), S6 (travail). Généraliser doublerait N_q pour un gain
décroissant sur les matières purement techniques, où le registre citoyen
n'existe guère.

### 8.3 Strate-frontière

Questions tombant **entre deux matières**. Elles réintroduisent délibérément ce
que la stratification uniforme rend invisible : le résidu de 6,32 % non
rattachable de l'analyse D₁ — « autres » civils, référés, « autres
contentieux » administratifs. Une classification qui n'a jamais de cas limite
n'est pas une bonne classification, c'est une classification qu'on n'a pas
testée.

### 8.4 Matériau adversarial de polysémie

Le corpus statistique fournit **cinq nomenclatures officielles divergentes
décrivant la même réalité**. C'est du matériau de désambiguïsation authentique,
produit par l'administration elle-même — et non fabriqué pour le test.

| Piège | Divergence |
|---|---|
| *« contentieux social »* | Trois référents incompatibles : aide sociale et RSA (TA) ; relations du travail (nomenclature civile) ; sécurité sociale sous « pôle social » (TJ) |
| *Stupéfiants* | Sous-ligne de « santé publique » dans une table, poste autonome dans deux autres |
| *« Atteinte à l'autorité de l'État »* | Devient « atteinte à l'ordre administratif et judiciaire » ailleurs — périmètres non identiques |
| *Nomenclature administrative* | 8 postes en 2024 contre 12 en 2025, même juridiction |

Ces questions portent le flag `polysemique` avec la liste de leurs référents
concurrents. Le flag est **constatable** (le terme a N référents attestés), à la
différence d'une étiquette de difficulté.

---

## 9. Comment on juge

**Échelle 0–3, dérivée d'une cascade de trois tests binaires** (ADR-005) — on
ne saisit jamais un grade directement.

| Test | Question | Si non |
|---|---|---|
| q1 | Même question de droit ? | grade 0 |
| q2 | Citable dans une consultation ? | grade 1 |
| q3 | Support principal de la solution ? | grade 2 (oui → 3) |

Deux conventions qui surprennent et qu'il faut tenir : la pertinence est
**topique, non directionnelle** — un arrêt *contraire* bien en point est un 3 ;
et les trois réponses sont **stockées avec le grade** (ADR-008), ce qui rend
les désaccords localisables à la question près et les grades re-dérivables sans
relecture.

**Granularité : au niveau document** (article LEGI, décision — ADR-004), qui
est l'unité stable. Annoter au chunk casse à chaque re-chunking. Un
sous-ensemble d'une cinquantaine d'items annotés au passage permet de
diagnostiquer le chunking séparément, sans contaminer la référence.

**Complétude — le point de vigilance.** ADR-007 fondait la robustesse de nDCG@R
sur le pooling **et** les citations minées ; ADR-029 ayant retiré les secondes,
elle repose désormais **entièrement sur le pooling et sur ce jeu**. Comme `R`
dépend du nombre de documents jugés pertinents, des qrels incomplètes ne font
pas qu'ajouter du bruit : **elles déplacent la coupe**.

> ⚠️ **Garde-fou, non négociable.** Une modification de qrels ne se justifie
> **jamais** par un résultat de run. « J'ai relu, ce grade 1 est un 2 » est
> recevable ; « cette config remonte ce document, il doit être pertinent » ne
> l'est pas — c'est ajuster l'étalon à l'issue souhaitée (ADR-031 §5, ADR-032
> §5). Toute modification est datée et motivée sans référence à une mesure.

---

## 10. Ce que le jeu exige de l'ingestion

Effet de bord recherché de la doctrine du §2 : construit sur l'usage, le
golden-set **désigne les manques du corpus** au lieu de les épouser.

| Strate | Ce qu'elle réclame | État |
|---|---|---|
| S6 — Travail | KALI, ACCO (conventions et accords collectifs) | Non ingérés |
| S11 — Libertés publiques | CONSTIT en volume, CNIL | CONSTIT ingéré à l'état de trace |
| S12 — Procédure | CPC, CJA, CPP dans LEGI ; CASS et JADE en volume | Partiel |
| Toutes | Volumétrie des 5 bases de jurisprudence | CAPP et INCA à l'état de trace |

Ces lignes alimentent directement le point ouvert d'ADR-003 (contenu de la
vague 2 d'ingestion, candidates KALI et CIRCULAIRES), qui attendait un critère
pour être tranché. **Le golden-set est ce critère** : ce qu'il faut ingérer est
ce sans quoi des questions légitimes restent sans réponse possible.

Une question sans cible disponible reste **`pending`** : écrite, gelée,
interrogée à chaque run, non jugée. Elle devient jugeable sans aucun coût de
re-récupération le jour où sa base arrive (§7.2).

---

## 11. Ce qui reste ouvert

| # | Point | Qui tranche |
|---|---|---|
| 1 | **Méthode de génération des requêtes** (D-01). E-T-01 interdit toute dépendance du *harnais* à un LLM générateur ; employer un LLM **hors ligne** pour fabriquer des requêtes n'est pas exclu, mais la frontière doit être écrite. Règle déjà posée : **jeter, jamais reformuler**. | B-08 |
| 2 | **Vocabulaire d'intentions** (§5) — proposition non validée. | Porteur (ADR-028) |
| 3 | **Nombres du §7** — dérivés, non actés. | Porteur (ADR-028) |
| 4 | **Espace des cibles.** `Section` et `Texte` ne sont pas des unités de citation au sens d'ADR-004 mais pèsent un tiers du graphe. Décision prise : **ne pas restreindre, observer d'abord** — si elles ne remontent jamais, la question se clôt sans qu'on ait rien décidé. | Observation |
| 5 | **Point d'entrée outillage** — la re-notation de tout l'historique doit tenir en **une commande**, sans quoi le modèle de versionnement d'ADR-032 n'est pas praticable. | B-11 |

---

## 12. Références

**Décisions** — ADR-004 (unité document, ventilation par base) · ADR-005
(cascade q1–q3, échelle 0–3) · ADR-006 (agrégation chunk→document) · ADR-007
(nDCG@R, coupe adaptative, complétude) · ADR-008 (format JSONL, provenance) ·
ADR-016 (découplage récupération/génération) · ADR-017 (strates de pérennité) ·
ADR-028 (régimes de vérification) · ADR-029 (garde-fou de circularité) ·
**ADR-030** (deux axes, opérations) · **ADR-031** (graphe témoin `G₀`) ·
**ADR-032** (gel par version, re-notation)

**Exigences** — `EXIGENCES_v0.md` E-P2-06 (gel + guide + grades), E-P2-07 (deux
axes), E-P2-09 (test apparié), E-P2-10 (reproductibilité), E-T-01, E-T-02

**Travaux** — `BACKLOG.md` B-08 (ce jeu), B-09 (set graph-hop), B-10 (test
apparié), B-11 (baseline chiffrée) · `WIP/B-08-cadrage.md` (méthode, pièges
P-01 à P-04) · `WIP/B-08-prior-ponderation.md` (protocole de pondération) ·
`WIP/analyse.md` (socle statistique, rattachements sourcés)
