# Le remplacement du pooling à profondeur fixe au TREC Legal Track

> Note de recherche — issue [#17](https://github.com/left-eyebr0w/murphy/issues/17)
> (`wayfinder:research`), rattachée à [#1](https://github.com/left-eyebr0w/murphy/issues/1).
> Ouverte par [ADR-035](../ADR/ADR-035-paradigme-evaluation-trec-legal-track.md), dont
> la **présomption symétrique** exige qu'un trait emprunté à TREC soit rapporté **avec le
> régime dans lequel il a été calibré**.
> Rédigée le 2026-08-02.
>
> **Question.** Comment le Legal Track a-t-il remplacé le pooling à profondeur fixe, et
> sous quelles conditions cette machinerie transfère-t-elle ?
>
> **Régime de vérification.** Sources primaires uniquement : les six *overview papers*
> NIST du track (2006–2011), les deux documents que la §9 de
> [`trec-legal-track.md`](trec-legal-track.md) déclarait *référencés mais non récupérés*
> — **tous deux récupérés et lus pour cette note** —, et les guidelines 2009. Ce qui n'a
> pas pu être vérifié est en **§9 Réserves**.
>
> **Ce que cette note ne fait pas.** Elle ne décide rien et ne recommande rien pour
> Murphy. Elle rapporte et elle **date**. Les arbitrages appartiennent aux tickets
> qu'elle débloque ([#18](https://github.com/left-eyebr0w/murphy/issues/18),
> [#19](https://github.com/left-eyebr0w/murphy/issues/19),
> [#20](https://github.com/left-eyebr0w/murphy/issues/20),
> [#14](https://github.com/left-eyebr0w/murphy/issues/14)).
> Les chiffres **varient par campagne et ne se moyennent pas** : ils sont datés
> partout, y compris dans les phrases de synthèse.

---

## 0. Ce que les deux sources manquantes se sont révélées être

La levée de la réserve commence par une **correction bibliographique**, parce que les
deux textes ne sont pas ce que le dossier antérieur laissait entendre.

**« Some Lessons Learned To Date from the TREC Legal Track (2006-2009) »** n'est pas un
article de la revue *Artificial Intelligence and Law*. C'est un **mémo de trois pages,
daté du 24 février 2010**, signé de **trois** auteurs — Douglas W. Oard, Jason R. Baron
et David D. Lewis — et rédigé en puces assumées :

> « In an effort to be concise, we stick to bullet points – much more could be said about
> any of this. […] we emphasize that these are our personal observations and that others
> might see things differently. »
> ([*Lessons Learned*, §introduction](https://trec-legal.umiacs.umd.edu/other/LessonsLearned.pdf))

Le texte se termine par « Watch for a 2010 special issue on "E-Discovery" in Artificial
Intelligence and Law Journal » — c'est **ce numéro spécial**, distinct, que le dossier
antérieur avait fusionné avec le mémo.

**« Reflections from the Topic Authorities »** n'est pas un document mais **deux**,
tous deux hébergés par le track :

| Document | Date | Auteurs | Portée |
|---|---|---|---|
| [`TAreflections2008.doc`](https://trec-legal.umiacs.umd.edu/other/TAreflections2008.doc) | 2008 | Maura R. Grossman, Conor R. Crowley, Joe Looby | tâche Interactive 2008 |
| [`2009TaReflections.pdf`](https://trec-legal.umiacs.umd.edu/other/2009TaReflections.pdf) | 18 juillet 2010 | Grossman + Bieser, Boehning, Geske, Nicols, Stanton, Krasnow Waterman (7 TA) | tâche Interactive 2009 |

Ce sont des **documents d'opinion de praticiens**, pas des rapports de mesure : ils
n'apportent aucun chiffre d'échantillonnage. Leur contenu portant est rapporté en §6.3
et §7.4.

---

## 1. Le seuil de déclenchement — point opportuniste, ramené sans requête dédiée

> ⚠️ Le point 1 du ticket a été **rétrogradé en opportuniste** le 2 août 2026. Il n'est
> rapporté que sous la forme demandée — **le seuil**, pas le récit — parce qu'il tombait
> dans les sections lues pour les points 2 à 5.

Le Legal Track **n'a jamais fait tourner le pooling à profondeur fixe seul**. Dès l'année
1 il est arrivé avec la défiance et le dispositif de mesure de sa propre panne.

**L'appréhension, importée (2006).** « The complexity of the CDIP documents and topics,
and a report of pooling problems with other large collections (Buckley, et al 2006)
generated some concern about the adequacy of conventional pooling approaches for the
Legal Track. We adopted several strategies for addressing these problems, **though none
were a complete solution**. »
([*TREC-2006 Legal Track Overview*, §4.1](https://trec.nist.gov/pubs/trec15/papers/LEGAL06.OVERVIEW.pdf))

**Le régime où le mur est atteint — les trois chiffres demandés :**

| Grandeur | Valeur 2006 |
|---|---|
| **Volumétrie de corpus** | **6 910 192** documents IIT CDIP 1.0 (OCR, *Master Settlement Agreement*) |
| **Profondeur de pool** | **100** documents du run prioritaire de chaque équipe + **10** de chacun de ses autres runs → **≤ 170 documents par équipe et par topic** |
| **Équipes contributrices** | **6** équipes, **31 runs officiels**, + 2 runs commissionnés = **33 ensembles** par topic |

**Le symptôme, mesuré et chiffré la même année.** Sur le *reference Boolean run*, dont un
échantillon stratifié permettait un estimateur sans biais de `P@B`, les organisateurs
comparent l'estimation poolée et l'estimation stratifiée (§5.3) :

> « pooling and stratified sampling produce the same estimate of P@B **when B is at or
> below 267**. The situation is quite different as B grows, however. **In 10 of the 16
> cases for which B is 528 or higher**, and for which the pooled estimate of P@B is
> nonzero, **the pooled estimate falls below the lower limit of the confidence interval
> on the stratified estimate.** »

Et la conclusion qu'ils en tirent : « our pool-based effectiveness measures do not provide
a measure of the absolute effectiveness of any of the participating systems […] the large
gap between the pool-based P@B and the true value […] means more danger that biases in
pool construction will affect even comparisons of relative effectiveness ». D'où la
conclusion du §6 : « It will therefore be important to revisit both our choice of measures
and our sampling strategies for the 2007 Legal Track. »

**Le seuil est donc un rapport, pas un nombre absolu** : à corpus 6,9 M et pool ≤ 170
documents par équipe (6 équipes), l'accord tient jusqu'à des ensembles de **267**
documents et se rompt à partir de **528**.

Second chiffre, de nature différente, qui a fixé la profondeur du remplaçant : chez
Hummingbird/Open Text, la **précision marginale dépassait encore 4 % en moyenne à la
profondeur 9 000** pour des approches vectorielles standard — rapporté par l'overview
2007, §2.4.2. Il n'y avait donc pas de profondeur fixe raisonnable à choisir.

---

## 2. Le mécanisme de remplacement : l'échantillonnage profond `L07`

### 2.1 La bascule, datée

Le remplacement est **livré en 2007** et porte un nom : la **méthode `L07`**. Sa
généalogie est déclarée : « The L07 method for estimating recall and precision was based
on how the recall and precision components are estimated in the **infAP** calculation.
What distinguishes the L07 method is **support for much deeper pooling by sampling
higher-ranked documents with higher probability**. »
([*Overview of the TREC 2007 Legal Track*, §2.4.2](https://trec.nist.gov/pubs/trec16/papers/LEGAL.OVERVIEW16.pdf))

Elle est explicitement cousine de `statAP` (Million Query Track), « developed
independently […] (The common ancestor was the infAP method) », et s'en distingue sur deux
points énoncés : l'attribution des probabilités, et la grandeur estimée — `L07` estime
**le rappel et la précision d'un ensemble**, `statAP` estime l'*average precision*.

Trois changements simultanés font la bascule :

| | 2006 | 2007 |
|---|---|---|
| Profondeur de soumission | 5 000 | **25 000** |
| Constitution du pool | top-100 / top-10 **par équipe** | **tous** les runs, poolés à **profondeur 25 000** |
| Sélection à juger | quasi-exhaustive sur le pool | **échantillon à probabilité d'inclusion connue** `p(d)` |

Tailles de pool avant échantillonnage : **195 688** (topic 76) à **476 252** (topic 84)
en 2007 ; **618 756** (topic 119) à **1 634 012** (topic 141) en 2008 ; en 2009 le run de
référence `fullset09` fait que « in practice **all 6,910,192 documents** in the collection
were actually in the pool for every topic » (overview 2009, §3.7.1).

### 2.2 Comment l'échantillonnage est stratifié

Ce n'est **pas** une stratification par strates disjointes dans la tâche Ad Hoc : c'est un
**échantillonnage à probabilités inégales**, la probabilité étant une fonction du meilleur
rang atteint par le document dans *n'importe quel* run soumis (`hiRank`).

**2007** (§2.4.3) :

```
si hiRank(d) <= 5      : p(d) = 1.0
sinon si hiRank(d) <= B: p(d) = min(1.0, (5/B)     + C/hiRank(d))
sinon                  : p(d) = min(1.0, (5/25000) + C/hiRank(d))
```

**2008** (§2.5.2) — `B` sort de la formule *parce que* `K` devient libre (voir §3) :

```
si hiRank(d) <= 5 : p(d) = 1.0
sinon             : p(d) = min(1.0, (5/100000) + C/hiRank(d))
```

**2009** (§3.7.2) — le plancher devient uniforme et le sommet perd son exemption :

```
p(d) = min(1.0, (1/5000) + C/hiRank(d))
```

`C` est choisi pour que `Σ p(d)` égale le budget de jugement du topic (500 en 2007–2008,
**2 500** en 2009). Le **plancher** (`5/B`, `5/25000`, `5/100000`, `1/5000`) garantit une
couverture de la queue ; le terme `C/hiRank(d)` densifie la tête.

La distribution obtenue en 2009 est publiée (§3.7.2, topic 138, `C` médian = 6,18) et
montre le profil recherché — dix déciles de profondeur, dont **22 % de documents jamais
soumis par aucun run** :

| Décile | 10 % | 10 % | 10 % | 10 % | 10 % | 10 % | 10 % | 8 % | 22 % |
|---|---|---|---|---|---|---|---|---|---|
| `hiRank` | ≤ 10 | ≤ 100 | ≤ 1 000 | ≤ 20 000 | ≤ 100 000 | ≤ 500 000 | ≤ 1 M | ≤ 1,5 M | non soumis |

**Le binning** est le mécanisme qui rend l'échantillon robuste à un assesseur qui
s'arrête. Les tirages sont **emboîtés** : `C` est calé successivement pour des sommes de
1 000, 900, …, 500, et les documents perdus à chaque étape forment les bins 6, 5, 4, 3, 2 ;
les 500 restants forment le bin 1. « the final p(d) values were based on **how many bins
the assessor had completed** » (2007 §2.4.3, 2008 §2.5.3). Et la sanction est nette :
« **if the 1st bin was not completed, the topic had to be discarded** ».

**Ce que la méthode continue de supposer**, dit sans détour (2008, §2.5.1) : « like
traditional TREC pooling, our deep sampling method **still implicitly assumes that
documents not included in the pool are not relevant** for purposes of the recall
calculation. (The random reference run allows us to separately analyze the accuracy of
this assumption.) »

### 2.3 Ce que devient `R` — l'estimateur

`R` cesse d'être un décompte et devient une **estimation de Horvitz–Thompson plafonnée**
(overview 2007, §2.6.1) :

```
estRel(S) = min(  Σ_{d ∈ JudgedRel(S)}  1/p(d)  ,  |S| − |JudgedNonrel(S)|  )
```

avec `estRel(S) = 0` si aucun document jugé pertinent. `F1@R` est défini sur
`Rceil = ⌈R⌉`, `R` étant fractionnaire (2008, §2.7).

**Avec quel intervalle ? La réponse est asymétrique selon la tâche, et c'est le point le
plus important de cette section.**

**(a) Tâches Ad Hoc / Batch (2007, 2008, 2009) — aucun intervalle publié.** À la place,
un **proxy d'exactitude** : « measures at depths B and 25000 [have] the accuracy of
approximately **5 + C simple random sample points**. Measures at other depths will have
the accuracy of approximately (at least) `C` simple random sample points » (2007 §2.4.3).
Les valeurs de `C` sont publiées année par année :

| Campagne | Budget de jugement / topic | `C` observé |
|---|---|---|
| 2007 | ~500 | **0,34** (topic 82) à **2,42** (topic 76) |
| 2008 | ~500 | **1,70** (topic 113) à **4,41** (topic 105) |
| 2009 (Batch) | **2 500** | **3,9** à **9,5**, médiane ≈ **6** |

Le commentaire des organisateurs en 2008 (§2.5.2) est explicite : « These C values are
fairly low, **indicating that substantial estimation errors are possible on individual
topics**. Mean scores (over 24 or 26 topics) should be somewhat more reliable than the
estimates for individual topics. »

**(b) Tâche Interactive (2008, 2009) — vrai plan stratifié, vrais intervalles à 95 %.**
La stratification y est **par combinaison de soumissions** : « If, for example, there are
5 teams that participated in a topic, the collection will be partitioned into 2⁵ = 32
strata » (2009, §2.1). Sélection aléatoire simple sans remise dans chaque strate ; les
grandes strates (notamment `All-N`, celle qu'aucune équipe n'a soumise) sont
**sous-représentées** par rapport à leur proportion, pour concentrer l'échantillon sur les
désaccords — « for most samples, roughly one third of the sample is allocated to the R
strata and two thirds to the All-N stratum » (2009 §2.3.3).

L'estimateur est stratifié classique (`τ̂ = Σ_h N_h p̂_h`, variance
`N_h(N_h − n_h)s²_h/n_h`), et les intervalles à 95 % sur rappel, précision et `F1` sont
obtenus par **propagation gaussienne des variances**, `± 1,96 √v̂ar` (appendice de
l'overview 2008, éq. 14–25).

Rendement estimé et intervalle, tâche Interactive 2009 (§2.3.5, table 5), corpus
569 034 messages :

| Topic | `R̂` (messages) | IC 95 % | Part du corpus |
|---|---|---|---|
| 201 | 1 524 | (949 – 2 099) | 0,3 % |
| 202 | 3 801 | (3 060 – 4 542) | 0,7 % |
| 203 | 1 685 | (1 550 – 1 820) | 0,3 % |
| 204 | 3 163 | (2 456 – 3 869) | 0,6 % |
| 205 | 26 839 | (23 751 – 29 928) | 4,7 % |
| 206 | 15 695 | (12 042 – 19 348) | 2,8 % |
| 207 | 8 454 | (7 892 – 9 016) | 1,5 % |

**Deux limites déclarées par les auteurs eux-mêmes** (2009, §2.3.5) : (i) ne pas refléter
la corrélation dans le calcul des IC de ratios comme précision et rappel « would reduce
our computed confidence intervals somewhat » (*William Webber, personal communication*) ;
(ii) les intervalles **« reflect sampling error but not assessment error »** — si
l'hypothèse implicite que tout premier jugement non contesté est correct tombe, « that
could in some cases place the actual values **outside** our computed confidence
intervals ».

**(c) 2011 — bootstrap.** Le nombre estimé de documents responsifs est publié avec un IC
95 % « calculated using **100 bootstrap samples** to estimate the standard error of
measurement » ([*Overview of the TREC 2011 Legal Track*, §4](https://trec.nist.gov/pubs/trec20/papers/LEGAL.OVERVIEW.2011.pdf)).

### 2.4 La machinerie de 2007–2009 a elle-même été remplacée en 2010

Ce n'est pas un point d'ornement : le `L07` **n'est pas le point d'arrivée du track**.
En 2010–2011, la tâche *Learning* revient à une **stratification à quatre strates**
construite par pooling à profondeurs emboîtées, plus une strate résiduelle aléatoire
([*Overview of the TREC 2010 Legal Track*, §4.1](https://trec.nist.gov/pubs/trec19/papers/LEGAL10.OVERVIEW.pdf)) :

| Strate | Définition | Taille moyenne | Échantillon | Taux |
|---|---|---|---|---|
| `100` | top-100 de l'un quelconque des 20 runs (« constructed by the TREC pooling method, with pool depth 100 ») | 1 063 | 1 063 | **1,0** |
| `1000` | pooling à profondeur 1 000, hors strate précédente | 7 813 | 552 | 0,07 |
| `10000` | pooling à profondeur 10 000, hors strates précédentes | 73 182 | 552 | 0,007 |
| `1000000` | tout le reste du corpus | 603 534 | 553 | 0,0009 |

Soit **2 720 documents échantillonnés par topic**, chacun jugé par **trois** assesseurs
indépendants, la **majorité** faisant vérité terrain. Le pooling à profondeur fixe n'a
donc pas été aboli : il est **redevenu la définition des strates hautes**, à l'intérieur
d'un plan d'échantillonnage qui couvre le reste du corpus.

---

## 3. `F1@K` avec `K` déclaré par le système

### 3.1 Le dispositif, et sa date exacte

`F1@K` est **introduit en 2008**, pour la tâche Ad Hoc, et le motif est double
([*Overview of the TREC 2008 Legal Track*, §2](https://trec.nist.gov/pubs/trec17/papers/LEGAL.OVERVIEW08.pdf)) :

> « The main evaluation measure this year was F1@K, where **K was specified by the
> participating system for each topic**. This new requirement gave systems the opportunity
> to show that they could produce a closer set to the optimal set of R relevant documents
> than the reference Boolean run (for which K=B) […]. It also **modeled a real operational
> requirement of e-discovery systems to return a set of documents, not just an unbounded
> ranked list**. »

**Comment un système annonce sa coupe.** Mécaniquement, `K` est déclaré **hors du
classement**, en queue de fichier de run : « start with the ranked list, followed by a
blank line, followed by the 10 lines of K values (`topicId whitespace K-value`) », avec
`K` « an integer between 0 and 1,500,000 inclusive », défini comme « the threshold at
which the system believes the competing demands of recall and precision are best balanced
as per the F1@K measure »
([*Batch Task Guidelines — TREC 2009 Legal Track*](https://trec-legal.umiacs.umd.edu/guidelines/batch09a.html)).
Un second seuil `Kh` est déclaré séparément pour les seuls documents *highly relevant*
(2008 §2, 2009 §3.4).

**Comment elle est notée.** `estF1@k = 2·estPrec@k·estRecall@k / (estPrec@k + estRecall@k)`,
avec la convention `0` si les deux composantes sont nulles (2008, §2.7) — donc sur les
grandeurs **estimées** de §2.3, jamais sur des décomptes.

### 3.2 Le comportement stratégique que cela crée — documenté, et par deux fois

**2008.** Le run le mieux classé en `F1@K` moyen ne modélise rien : il sature la borne.

> « The highest scoring run in mean F1@K (`wat7fuse`) **just set K=100,000 (the maximum
> allowed) for all topics**, which probably isn't a generally applicable thresholding
> approach. » (§2.8)

Même schéma sur les *highly relevant* : « the top-scoring run in F1@Kh (`wat6fuse`) **just
set Kh to a constant 12,500 for all topics** (close to the average number of highly
[relevant] documents per topic (11,542)) ».

L'overview identifie lui-même la cause : cette année-là le nombre estimé de pertinents a
explosé — **82 403 en moyenne par topic, presque 5× celui de 2007 (16 904)**, avec six
topics au-delà de 100 000, c'est-à-dire **au-delà de ce que les runs avaient le droit de
retourner** (§2.8.1). Quand `R` dépasse la borne de soumission, déclarer `K = K_max` est
optimal, et la mesure cesse de tester le seuillage : « the submission cutoff of 100,000 may
not have allowed enough flexibility to really test the thresholding ability of the
systems » (§2.8).

**2009.** Le même mécanisme est observé à l'envers, en faveur des systèmes batch : « Part
of why the Batch systems scored higher in F1 on topic #103 is that **they chose a larger K
value** » (§3.10.5). Et le track publie `F1@R` **à côté** de `F1@K` — la valeur qu'on
aurait obtenue en coupant au `R` estimé — en notant l'identité qui la rend lisible :

> « at depth R, precision, recall and F1 are all the same. (Put another way, the popular
> "R-Precision" measure of ranked retrieval is **equivalent to "F1@R" and also
> "Recall@R"**.) » (§3.10.4)

Écart mesuré en 2009 : meilleur `F1@K` moyen = **0,21** (`watstack`), meilleur `F1@R`
moyen = **0,26** (même système). L'écart est le **prix payé pour avoir dû déclarer la
coupe soi-même**. Remarque des organisateurs sur la stabilité de `F1` autour de son
optimum : sur `watstack`/topic 103, passer de 100 000 à 608 807 documents retournés
« shifts its recall by 13 points (from 0.43 to 0.56), but **shifts its F1 by only 3
points** (from 0.54 to 0.57) » (§3.10.5).

### 3.3 2011 : le track décompose lui-même la mesure en deux

C'est le développement le plus directement utile au ticket
[#14](https://github.com/left-eyebr0w/murphy/issues/14). En 2011, `F1@K` est scindé en
**deux mesures nommées** (overview 2011, §5.3) :

| Mesure | Définition | Ce qu'elle isole |
|---|---|---|
| **Hypothetical F1** | le meilleur des 685 592 `F1` possibles, obtenu en énumérant toutes les coupes `c` — « achieved only when the optimal cutoff is used, and **there is no way to determine this cutoff from the submission itself** » | qualité du **classement** seule |
| **Actual F1** | `F1` réel à la coupe `c` qui maximise le `F1` **estimé par le participant** à partir de ses propres probabilités | classement **et** exactitude de l'auto-estimation |
| **AUC** | probabilité qu'un document responsif soit mieux classé qu'un non-responsif | classement seul, sans coupe |

Et le verdict empirique, sur 3 topics et 10 organisations (§6) :

> « **Most runs for most topics dramatically overestimated recall at all cutoff levels.**
> Such an overestimate might lead the manager of a review effort to terminate the review
> prematurely […]. while teams occasionally achieved Actual F1 scores that came close to
> the Hypothetical scores (e.g., on Topic 401, one team (Recommind) achieved an Actual F1
> score of **54 %**, which is reasonably close to their corresponding Hypothetical F1
> score of **58 %**), **no team was able to estimate recall consistently enough** to
> achieve, for all topics, Actual F1 scores near the Hypothetical F1 scores. »

Le même overview note par ailleurs que « Precision and F1 are in fact **mathematically
redundant**, as they may be calculated from recall, given `c` and `Rel` » (§5.1), et que
pour piloter une revue « recall conveys completeness as a function of cutoff much more
directly than the other measures ; […] **F1 sheds no additional light** ».

**Chronologie du statut de `F1@K` — à ne pas résumer en « mesure primaire du track » :**

| Campagne | Mesure principale déclarée |
|---|---|
| 2006 | R-précision, `P@B` (comparaison au booléen) |
| 2007 | **Estimated Recall@B** |
| 2008 | **`F1@K`**, `K` déclaré par le système |
| 2009 | `F1@K` (Batch), `F1` (Interactive) ; `F1@R` publié à côté |
| 2010 | rappel à coupes fixes + *accuracy* de l'estimation du participant |
| 2011 | **Hypothetical F1 / Actual F1 / AUC** |

---

## 4. Le *reference Boolean run* — quelle fonction exacte dans le pool

**Réponse courte : les deux, et la réponse change chaque année.** Sa fonction migre de
*cadre d'échantillonnage privilégié* (2006) à *entrée ordinaire du pool avec un `hiRank`
dégradé* (2008–2009).

| Campagne | Statut dans le pool | Fourni aux participants ? | Fonction |
|---|---|---|---|
| **2006** | **Hors** pool de contribution : run baseline soumis par Hummingbird, « **not counted as an official submission** […] but rather as a track baseline ». C'est **de lui** qu'est tiré un échantillon stratifié à 3 strates | non | baseline **et cadre d'échantillonnage dédié** |
| **2007** | **Exclu du pooling**, pour un motif technique : `refL07B` « was not included in the pooling because it had been created by simply resorting one of the pooled runs (`otL07fb`) alphabetically by docno ». Remplacé au 69ᵉ rang par `randomL07` (100 documents aléatoires/topic) | **oui** — `B` et la liste complète livrés à la sortie des topics | baseline ; **`B` devient le paramètre de la mesure principale** (`Recall@B`) |
| **2008** | **Pleinement dans le pool** : « The **4 Boolean reference runs** were also fully included in the pool, even the plaintiff Boolean run that sometimes matched more than 1 million documents ». Runs non classés → `hiRank` = taille du run | oui | baseline **et contributeur de documents jugés** |
| **2009** | l'un des **4 runs de référence** avec `fullset09`, `oldrel09`, `oldnon09` | oui | idem ; `fullset09` met de fait tout le corpus dans le pool |

**Stratification de 2006, telle que le pool a été enrichi** (§4.1) — trois strates
définies par la co-occurrence dans les 31 runs officiels, puis **100 / 50 / 50** documents
tirés par topic :

- *Stratum 1* : dans le top-5 000 d'au moins un run officiel d'**au moins deux** des six sites ;
- *Stratum 2* : dans le top-5 000 de runs d'**exactement un** site ;
- *Stratum 3* : dans le top-5 000 d'**aucun** run.

Avec un défaut signalé sur-le-champ : « An unexpected downside of the above stratification
was that **Stratum 3 often turned out to be empty**. This may have resulted from use of
terms from the negotiated Boolean query by ranked retrieval systems, which was allowed
(and, indeed, encouraged) by the track guidelines. » Autrement dit : **quand la requête de
référence est donnée aux participants, elle contamine la diversité du pool qu'elle était
censée servir à mesurer.** Le track en tire une conséquence l'année suivante (2008,
§2.6) : les fichiers remis aux **assesseurs** cessent d'inclure les négociations
booléennes, « to reduce the chance that knowledge of the Boolean strings might somehow
influence the assessing ».

**Ce que la baseline a mesuré, par campagne :**

| Campagne | Résultat |
|---|---|
| 2006 | Le booléen de référence trouve **57 %** des pertinents connus (moyenne sur 39 topics) ; le chercheur expert manuel en ajoute **11 %** ; les autres systèmes **32 %** — soit **1 417 pertinents connus sur 39 topics** que ni le booléen ni l'expert n'ont trouvés (§5.1). En R-précision, « the reference Boolean run did about as well […] as the best unconstrained ranked retrieval runs » (§5.2) |
| 2007 | `F1` moyen de la requête finale négociée : **14 %** |
| 2008 | `F1` moyen : **16 %** (min 0,2 % topic 150, max 38 % topic 128) ; **9 %** sur les seuls *highly relevant* |
| 2009 | `F1` moyen : **0,06** ; `B` moyen **27 462** hits, rappel moyen **< 4 %** ; précision moyenne 0,39, battue par plus de la moitié des runs soumis en `Precision@B` (max 0,58) |

Et la synthèse du mémo de 2010, qui est la formulation la plus générale disponible :

> « **For the vast majority of our production requests, fewer than half of all responsive
> documents were retrieved by a Boolean query negotiated by lawyers without interactive
> access to the collection.** This was despite thoughtful keyword choices and the use of
> Boolean, truncation, and proximity operators in a formally correct fashion. »
> (*Lessons Learned*, §« Some Lessons Learned »)

### 4.1 Un couplage à verser à la fog « forme du topic »

Le fait suivant est un **fait de conception de topic**, pas de mesure, et il entre
directement dans le ticket qui porte la forme du topic. L'overview 2008 explique la
multiplication par 5 du nombre de pertinents par la levée d'une contrainte d'authoring
(§2.8.1) :

> « the topic formulators had been instructed in previous years **to try to keep the
> requests narrow because of concerns about the shallow pooling traditionally used at
> TREC**. **With the deeper sampling approach now in use, this concern went away**,
> resulting in more broadly worded topics. However, if this is what happened, **it was not
> a planned change**, and the participants were not advised that this year's topics might
> tend to be broader. »

Le protocole d'échantillonnage contraignait donc la **largeur autorisée d'un topic**, et
son remplacement a déplacé cette contrainte **sans que personne le décide**.

---

## 5. L'évaluation non-résiduelle de 2009

### 5.1 Ce qui a été décidé, et où

La décision est énoncée dans l'overview 2009, §3.4 (tâche Batch) :

> « In contrast with the 2007 and 2008 Relevance Feedback tasks, **residual evaluation was
> not used this year**, so participating teams were advised to include previously judged
> documents in their submitted result sets (if their system considered them possibly
> relevant). If this year's sampling happened to draw documents that were previously
> judged, **this year's assessors would re-assess them (with no knowledge of the previous
> assessment)**, and just this year's assessments would be used in this year's evaluation.
> **Past judgments hence were not considered to be authoritative, but rather as one opinion
> of relevance for a sample of documents.** This was intended to model the real-world issue
> that internally generated training data […] may not perfectly match the final authority's
> conception of relevance. »

Deux précisions de portée, souvent perdues : (i) c'est l'**évaluation résiduelle des
tâches Relevance Feedback 2007–2008** qui est abandonnée, pas un usage général ; (ii) les
jugements passés ne disparaissent pas — ils sont **redistribués comme `training qrels`**
aux participants (`qrelsL09.pass1`), soit 499 à 6 500 jugements selon le topic. Le corpus
de test 2009 est bâti sur une **ascendance explicite** : 3 topics de 2008 Interactive,
3 de 2008 Ad Hoc, 2 de 2007, 2 de 2006.

L'avertissement des coordinateurs sur ce corpus d'entraînement est net : « we note,
however, that **assessors in different years may have had different conceptions of
relevance, and that no attempt had been made to standardize those conceptions** » (§3.3).

### 5.2 À quel coût — chiffré

**(a) Le coût de cohérence, mesuré directement.** Les documents autrefois jugés pertinents
sont reversés au pool sous le run de référence `oldrel09`, donc rééchantillonnés :

> « of documents previously judged relevant (`oldrel09` run), Table 7 shows that the
> **estimated precision was just 0.78 this year**. It also shows that, on average,
> **74 documents per topic** that had previously been judged as relevant were re-assessed,
> with an average of **65 of them again being judged as relevant**. » (§3.10.8)

Soit environ **22 % de renversement** sur des documents antérieurement déclarés pertinents.

**(b) Le coût sur `R`, et donc sur toutes les mesures qui en dépendent.** C'est le chiffre
le plus lourd. Table 12 (§3.10.10) compare, sur les 10 topics, les estimations issues des
anciens jugements et des nouveaux :

| | Anciens jugements | Nouveaux jugements |
|---|---|---|
| `Est. Rel@B` (moyenne) | 14 275 | 15 295 |
| Précision du booléen | 0,33 | 0,39 |
| **`Total Est. Rel` (moyenne)** | **159 949** | **314 527** |
| **Rappel du booléen** | **0,17** | **0,04** |

Les estimations *locales* (ce que le booléen ramène) sont stables et « highly correlated » ;
c'est le **dénominateur global qui double**. Diagnostic des auteurs :

> « We suspect that the **full collection sampling** used this year, in combination with
> the **suspected false positive rate** discussed in Section 3.10.6, has led to total
> number of relevant documents being **overestimated**, and if so the reported recall and
> F1 scores would tend to be **lower than they should be**. However, as the same judgments
> are used for scoring all systems, **the relative scores should still be meaningful**. »

**(c) Le mécanisme d'amplification, énoncé.** §3.10.6, sur le topic #51 (3 faux positifs
apparents, 3 assesseurs, 1 500 jugements) :

> « Even if the assessing was **99 % accurate**, misjudging 1 % of a collection of
> 7 million documents could lead to the estimated number of relevant documents being off
> by **several thousand**. For topics with large numbers of relevant documents (e.g.,
> 100,000+), such errors would likely be just minor noise, but **for "low-density" topics
> […] these errors can be dominant** for measures, such as recall and F1, that are based
> on the estimated total number of relevant documents. »

Et l'aveu de régression : « Our past Ad Hoc evaluations were **less susceptible** to this
issue **because the full collection was not pooled** ». Le coût est donc imputable à la
conjonction *non-résiduel + pooling de la collection entière*, pas au non-résiduel seul.

**(d) Antécédent chiffré (2008 Interactive, topic 103).** Les appels ont fait passer le
nombre estimé de pertinents de **914 528 à 786 862** — « a reduction of **127 666**, which
is almost **2 % of the full collection** » ; et dans la strate `All-N`, **51 des 111**
jugements « pertinent » ont été renversés (§3.10.6, citant l'overview 2008 table 12).

**(e) Le contrefactuel, publié.** §3.10.7 : « If just the relevant documents from the
training qrels had been submitted, the average F1 score would have been just **0.004** […]
average recall of the relevant training examples was just **0.2 %**. This result also
suggests that, **if we had used "residual" evaluation** as in some past years […] **it
would not have affected the scores much**. » Le coût mesuré du choix non-résiduel est donc
**dans la variance de jugement et dans `R`**, pas dans le classement des systèmes.

**(f) Les mitigations achetées, et leur prix.** Trois, toutes coûteuses en assesseur
(§3.8) : dix exemples de chaque catégorie de jugement passé remis aux assesseurs ;
**~5 assesseurs par topic** encouragés à s'écrire ; guidelines détaillées de 2008
rediffusées pour les topics 102–104. Une piste discutée et non retenue : « One suggestion
was to **reassess high-weight relevant documents before releasing the results**, when
overturning a few of them could make a dramatic difference » (§3.10.6).

---

## 6. Le régime de calibration, par campagne

C'est la partie que la présomption symétrique rend non négociable : **aucun trait des §1–5
n'est utilisable sans la ligne du tableau qui le porte.** Les chiffres ne se moyennent pas.

### 6.1 Corpus, participation, topics

| Campagne | Corpus | Volumétrie | Tâches | Équipes | Runs | Topics **jugés** (sur assignés) |
|---|---|---|---|---|---|---|
| **2006** | IIT CDIP 1.0 (OCR, tabac) | **6 910 192** docs | Ad Hoc | **6** + 1 chercheur manuel | 31 officiels + 2 commissionnés | **40 / 43** — 3 abandonnés « due to lack of assessment capacity » |
| **2007** | idem | 6 910 192 | Ad Hoc, Interactive, Relevance Feedback | **13** (dont **12** en Ad Hoc, 3 en RF) | **68** (Ad Hoc) + 8 (RF) | **43 / 50** |
| **2008** | idem | 6 910 192 | Ad Hoc, RF, Interactive | **15** (10 Ad Hoc, 5 RF, 4 Interactive) | **64** (Ad Hoc) + 29 (RF) | **27 / 34** (dont 26 exploitables ; 24 pour les *highly relevant*) |
| **2009** | Batch : IIT CDIP · Interactive : **Enron/EDRM** | 6 910 192 · **569 034 messages / 847 791 docs** | Batch, Interactive | **15** (**4** Batch, **11** Interactive) | **10** (Batch), 24 (Interactive) | **10** Batch, **7** Interactive |
| **2010** | EDRM Enron v2 | **685 592** docs (de 1,3 M messages bruts, 455 449 canoniques + 230 143 pièces jointes) | Learning, Interactive | **17** (8 Learning, 12 Interactive, 3 les deux) | **20** (Learning) | **8** Learning, **4** Interactive |
| **2011** | idem | 685 592 | Learning seule | **10** organisations | — | **3** |

> Note de cohérence : l'overview 2008 annonce « a total of 15 participating research
> teams » (§1) ; l'overview 2009 en compte rétrospectivement **16** pour 2008 (§1). L'écart
> n'est pas expliqué dans les sources.

### 6.2 Effectif, formation et effort des assesseurs

| Campagne | Qui juge | Effectif | Jugements | Volume / topic | Cadence | Budget |
|---|---|---|---|---|---|---|
| **2006** | **35 volontaires** : 8 avocats, 10 étudiants en droit (1ʳᵉ–3ᵉ année), 3 paralégaux expérimentés, 1 archiviste, 1 historien, plusieurs diplômés sciences/finance — issus de la NARA, cabinets, écoles de droit, entreprises. + **12** volontaires en second tour (7 vétérans, 5 recrues) | 35 (+12) | **32 738** | ≈ 818 | **24,7 doc/h** | non publié |
| **2007** | **Étudiants en droit de 2ᵉ et 3ᵉ année**, sollicités nationalement, au titre d'une obligation *pro bono* : **42** étudiants (Loyola-L.A. 23, Indiana-Indianapolis 5, …) + 1 avocat du DoJ + 1 archiviste NARA | 44 | **24 404** (Ad Hoc) + 3 238 (Int./RF) | ≈ 567 | **20 doc/h** (≈ 25 h pour le bin 1) | **≈ 1 400 h**, valorisées **≈ 200 000 $** à 150 $/h (tarif *summer associate*) |
| **2008** | idem, ≥ **17 institutions**, plus quelques jeunes diplômés, paralégaux et *litigation specialists* | non publié | **14 771** (Ad Hoc) | ≈ 547 | **21,5 doc/h** (**631,15 h** déclarées pour 13 543 docs) | non publié |
| **2009 Batch** | volontaires, majoritairement étudiants en droit ; **~5 assesseurs par topic**, 2 bins de 250 chacun | ~50 | **22 750** (2 500 × 8 topics + 1 500 + 1 250) | **2 500** | non publié | non publié |
| **2009 Interactive** | **réviseurs professionnels *et* volontaires individuels**, premier passage ; puis appel devant la **Topic Authority** | **100 bins** répartis | **49 285 docs** / 24 206 messages ; **1 980 (4 %) non jugeables** | 5 710 à 8 658 docs | non publié | non publié ; pour le topic 207 « the assessment […] was carried out by **a firm that offers professional review services** » |
| **2010 Learning** | volontaires « primarily, but not exclusively, law students » ; **3 jugements binaires par document**, **vote majoritaire** = vérité terrain ; « Each reviewer had legal training; the majority were **third-year law students who received pro bono credits** » | non publié | **78 000** | 2 720 docs × 3 | non publié | non publié |
| **2010 Interactive** | **sociétés de review professionnelles** ; 10 % des documents en double pour « estimate and correct for assessor error » | non publié | **50 000** | non publié | non publié | non publié |
| **2011** | **4 sociétés de review professionnelles**, bénévoles (« although, to our knowledge, **the reviewers themselves were paid** ») ; strate 1000 jugée **deux fois** ; conflits arbitrés par la Topic Authority | 4 sociétés | **16 999** | **≈ 5 600** | non publié | non publié |

**Les Topic Authorities forment un corps distinct des assesseurs**, et il est nominatif.
En 2009, **sept** TA, un par topic, tous avocats de cabinets nommés dans l'overview
(Squire Sanders & Dempsey ; Aphelion Legal Solutions ; Pillsbury Winthrop Shaw Pittman ;
Wachtell, Lipton, Rosen & Katz ; Hunton & Williams ; …). Chaque équipe dispose de
**jusqu'à 10 heures** du temps de sa TA par topic (2009, §2.1). En 2011, la ressource TA
est rationnée autrement : « Participants were permitted to request **up to 1,000
responsiveness determinations** from a Topic Authority for each topic » (§abstract).

### 6.3 Ce que les praticiens disent de leur propre régime

Les deux documents *Reflections* n'ajoutent aucun chiffre, mais ils qualifient le régime
de l'intérieur, et deux constats sont directement portants.

**Sur la sous-consommation de la ressource experte** — 2009, §1 : « many of the 2009 TAs
were **surprised by the limited amount of contact** and overall interaction that most
teams had with their TAs. **Very few of the teams used a significant portion of the ten
hours** they were each allotted. […] the teams that understood how to generate such
questions **performed considerably better** than those that did not, even if the team spent
less time interacting with their TA, suggesting that ultimately, **the quality of the
team/TA interaction was more important than the quantity**. » (Constat déjà fait en 2008.)

**Sur la qualité du jugement humain** — 2009, §5, et c'est un renversement énoncé par les
juristes eux-mêmes :

> « Based on the volume and results of the appeals and adjudication process, **some of the
> TAs were less confident than they were before about the quality of human review**. The
> responsiveness determinations rendered by the human assessors included **many flagrant
> errors**, suggesting that **human review may be more flawed than the legal profession
> currently understands and acknowledges**. Although human review for relevance remains the
> "gold standard" by which all other methods are judged, the number and nature of errors by
> human assessors raised questions about whether human reviewers are capable of
> consistently and accurately identifying relevant documents. »

**Sur l'impossibilité déclarée d'un étalon stable** — 2008 : « Relevance determinations
reflect **highly subjective judgment calls**, made by a particular lawyer or legal team,
in light of the demands of a particular information request, **at a particular point in
time**. […] Lawyers can and do draw these lines differently for different types of
opponents, on different matters, and at different times on the same matter. **This makes it
exceedingly difficult to establish a "gold standard" against which to measure
relevance/responsiveness.** »

### 6.4 Bruit d'assessment mesuré dans le track lui-même

Le track a mesuré son propre désaccord inter-assesseurs **dès 2006**, sans recourir à une
source externe (overview 2006, §4.3) : pour chacun des 40 topics jugés, un échantillon de
**50 documents** (25 jugés pertinents, 25 non pertinents) rejugé **à l'aveugle** par un
second assesseur, par **12 volontaires**.

> « The mean value of kappa over the 40 topics was **+0,49**, indicating moderate overall
> agreement between assessors […] although considerable variation was evident across
> topics. »

Avec la mise en garde méthodologique des auteurs eux-mêmes : « The kappa value would have
been different if a random sample from the pool had been judged by both assessors » — le
tirage 25/25 n'est pas un tirage aléatoire du pool, et une approximation stratifiée du
kappa « sur pool » est fournie en table 2, sans être un estimateur sans biais (kappa étant
non linéaire).

### 6.5 Réutilisabilité : le chiffre de dimensionnement publié

Le mémo de 2010 est le seul endroit où le track chiffre ce qu'il faut pour qu'une
collection soit **réutilisable** :

> « An important byproduct of the first four years of Legal Track evaluations is a reusable
> test collection containing about **7 million** scanned business documents […], about
> **100 discovery requests**, and a set of sampled assessments of responsiveness sufficient
> to support evaluation of future systems. In 2009, we started creating a second test
> collection, this one based on several hundred thousand email messages and attachments.
> **The initial collection is not yet large enough for reliable reuse (we now have 7
> production requests; the best estimates are that at least 40 production requests are
> needed).** »

Et la doctrine générale du même mémo sur la fabrication d'une collection : « Experience
across a range of TREC tracks has shown that large, reusable test collections can be
affordably created. **The key idea is to sample and manually assess documents from the
results returned by diverse systems.** In combination with robust effectiveness measures,
this can allow fair evaluation of systems which did not exist at the time of test
collection creation. »

Enfin, sur la nature des résultats produits — utile à qui lit les tables ci-dessus comme
des états de l'art : « **The results truly are baselines, not "best effort" or upper
bounds** », pour trois raisons énumérées (calendrier strict, campagne unique sans reprise,
équipes qui mesurent souvent l'effet d'un paramètre plutôt que d'optimiser) ; « TREC
participants must agree **not to use TREC results in advertising** ».

---

## 7. Corrections et confirmations au dossier `trec-legal-track.md`

Le dossier antérieur reste globalement exact. Neuf points appellent une correction ou une
datation.

| # | §  | Énoncé antérieur | Correction, à la source |
|---|---|---|---|
| 1 | §8 | « Some Lessons Learned To Date » et « Reflections from the Topic Authorities » présentés comme des références de revue, non récupérées | **Récupérées.** Le premier est un **mémo de 3 pages du 24/02/2010** par **Oard, Baron & Lewis** (trois auteurs). Le second est **deux documents** : 2008 (Grossman, Crowley, Looby) et 2009 (Grossman + 6 TA, 18/07/2010). L'article *Artificial Intelligence and Law* (Oard, Baron, Hedin, Lewis, Tomlinson) en est **distinct** et reste non lu → réserve |
| 2 | §3 | « **Assesseurs** : réviseurs juridiques professionnellement formés » | **Inexact pour les tâches Ad Hoc et Batch, 2006–2009.** Ce sont des **volontaires**, majoritairement des **étudiants en droit de 2ᵉ/3ᵉ année** créditant des heures *pro bono*. Les **sociétés de review professionnelles** n'apparaissent que dans l'Interactive (2009 partiellement, 2010, 2011). Le corps professionnellement formé et nominatif est celui des **Topic Authorities**, distinct des assesseurs, et il n'existe **qu'à partir de 2008** |
| 3 | §3 | « **Bruit d'assessment** : désaccord inter-assesseurs documenté (Grossman & Cormack) » | Le track a mesuré le sien **dès 2006** : **kappa de Cohen moyen +0,49** sur 40 topics, 50 documents rejugés par topic, 12 volontaires (overview 2006 §4.3). Grossman & Cormack restent non lus → la citation de leur nom pour ce fait est **superflue et non vérifiée** |
| 4 | §3 | « **Corpus** : IIT CDIP (~7 M documents OCR) » | Exact ; le chiffre publié est **6 910 192**. (L'overview 2007 §2.6.1 écrit `6,910,912` — transposition typographique isolée.) Et il ne vaut que **2006–2009** : 2009 Interactive utilise **569 034 messages / 847 791 documents** Enron, 2010–2011 **685 592 documents** |
| 5 | §3 | « **Mesure primaire F1@K** » | Vrai en **2008 et 2009 seulement**. 2006 : R-précision / `P@B` ; 2007 : *Estimated Recall@B* ; 2010 : rappel à coupes fixes + *accuracy* ; 2011 : **Hypothetical F1 / Actual F1 / AUC**. Sans date, l'énoncé est faux |
| 6 | §3 | « **Deep sampling** : le pooling classique **a cassé** » | À dater et à nuancer. La défiance est **importée dès 2006** (Buckley et al.), la panne est **mesurée en 2006** sur le seul *reference Boolean run* (seuil : accord jusqu'à `B` = 267, rupture à partir de `B` = 528, 10 cas sur 16), et le remplaçant `L07` est **livré en 2007**. Le track n'a jamais fait tourner le pooling à profondeur fixe seul. Et `L07` **n'est pas le point d'arrivée** : 2010–2011 reviennent à un plan **à 4 strates dont trois sont des pools à profondeur fixe** (100 / 1 000 / 10 000) plus une strate résiduelle aléatoire |
| 7 | §4 | « **2009** : batch + interactive ; échantillonnage profond ; adjudication ; *topic authorities* » | **Adjudication et Topic Authorities datent de la tâche Interactive 2008**, pas de 2009 (overview 2008 §4.2.2). 2009 les reconduit à plus grande échelle (11 équipes, 7 topics, 7 TA) |
| 8 | §4 | « **2006** : 6 équipes + 1 chercheur manuel → 33 ensembles de résultats par topic, poolés et **partiellement** évalués » | Confirmé, à préciser : les 33 = **31 runs officiels + 2 runs commissionnés**. Le « partiellement » a un chiffre : **40 topics sur 43** jugés, les 3 autres abandonnés « due to lack of assessment capacity » |
| 9 | §4 | « **2012** : le track ne tourne pas — nouveau jeu de données (~1 M emails Enron) annoncé, mais délais insuffisants » | **Non vérifié à la source primaire** → réserve. NIST ne recense que **2006–2011**. Par ailleurs le corpus Enron n'est pas « annoncé pour 2012 » : il est en service **depuis 2009**, et sa version 2010–2011 fait 685 592 documents (dérivés de 1,3 M messages bruts) |

**Confirmés sans réserve** : le primat du rappel comme trait distinctif du track ; le topic
comme *artefact structuré* (plainte + demande de production + requête booléenne négociée) ;
le caractère « travail en cours » du bilan des organisateurs — le mémo de 2010 le dit
mot pour mot (« "Lessons learned" are, therefore, **a work in progress** ») ; et la
maturation par constat plutôt que par conception, dont le §1 ci-dessus fournit désormais la
mesure datée.

---

## 8. Sources

Toutes consultées directement, PDF ou page NIST/UMIACS d'origine.

**Overview papers, proceedings NIST**

- Jason R. Baron, David D. Lewis, Douglas W. Oard. *TREC-2006 Legal Track Overview.*
  TREC 2006 Proceedings, pp. 79–98.
  <https://trec.nist.gov/pubs/trec15/papers/LEGAL06.OVERVIEW.pdf>
- Stephen Tomlinson, Douglas W. Oard, Jason R. Baron, Paul Thompson. *Overview of the TREC
  2007 Legal Track.* TREC 2007 Proceedings.
  <https://trec.nist.gov/pubs/trec16/papers/LEGAL.OVERVIEW16.pdf>
  *(⚠️ le nom de fichier est `LEGAL.OVERVIEW16.pdf`, non `…07.pdf`)*
- Douglas W. Oard, Bruce Hedin, Stephen Tomlinson, Jason R. Baron. *Overview of the TREC
  2008 Legal Track.* TREC 2008 Proceedings — **appendice : formules d'estimation stratifiée
  et d'intervalles de confiance, éq. 1–29.**
  <https://trec.nist.gov/pubs/trec17/papers/LEGAL.OVERVIEW08.pdf>
- Bruce Hedin, Stephen Tomlinson, Jason R. Baron, Douglas W. Oard. *Overview of the TREC
  2009 Legal Track.* TREC 2009 Proceedings.
  <https://trec.nist.gov/pubs/trec18/papers/LEGAL09.OVERVIEW.pdf>
- Gordon V. Cormack, Maura R. Grossman, Bruce Hedin, Douglas W. Oard. *Overview of the TREC
  2010 Legal Track.* TREC 2010 Proceedings.
  <https://trec.nist.gov/pubs/trec19/papers/LEGAL10.OVERVIEW.pdf>
- Maura R. Grossman, Gordon V. Cormack, Bruce Hedin, Douglas W. Oard. *Overview of the TREC
  2011 Legal Track.* TREC 2011 Proceedings.
  <https://trec.nist.gov/pubs/trec20/papers/LEGAL.OVERVIEW.2011.pdf>

**Les deux sources que la réserve visait**

- Douglas W. Oard, Jason R. Baron, David D. Lewis. *Some Lessons Learned To Date from the
  TREC Legal Track (2006-2009).* 24 février 2010, 3 p.
  <https://trec-legal.umiacs.umd.edu/other/LessonsLearned.pdf>
- Maura R. Grossman *et al.* *Reflections of the Topic Authorities about the 2009 TREC Legal
  Track Interactive Task.* 18 juillet 2010.
  <https://trec-legal.umiacs.umd.edu/other/2009TaReflections.pdf>
- Maura R. Grossman, Conor R. Crowley, Joe Looby. *Reflections of the Topic Authorities*
  (2008). <https://trec-legal.umiacs.umd.edu/other/TAreflections2008.doc>

**Guidelines et données**

- *Batch Task Guidelines — TREC 2009 Legal Track* (format de déclaration de `K`, bornes,
  définition de `F1@K`).
  <https://trec-legal.umiacs.umd.edu/guidelines/batch09a.html>
- NIST, page données du Legal Track (recensement 2006–2011).
  <https://trec.nist.gov/data/legal.html> · données 2009 :
  <https://trec.nist.gov/data/legal09.html>
- Page d'accueil du track (index des guidelines, *reflections*, lettres ouvertes).
  <https://trec-legal.umiacs.umd.edu/>

---

## 9. Réserves

Ce qui **n'a pas été vérifié à la source primaire** et ne doit donc pas être traité comme
acquis (régime du [README](README.md)).

- **Oard, Baron, Hedin, Lewis & Tomlinson, *Evaluation of Information Retrieval for
  E-Discovery*, *Artificial Intelligence and Law*, 2010/2011 — non ouvert.** L'article
  n'est pas en accès libre ; le mémo *Lessons Learned* n'en est pas un substitut, il
  l'annonce (« Watch for a 2010 special issue »). Tout ce que cette note rapporte sur la
  maturation vient des overviews et du mémo, pas de l'article. La réserve du dossier
  antérieur est donc **levée sur les deux textes qu'elle nommait, et maintenue sur
  celui-là**.
- **Grossman & Cormack** (*Technology-Assisted Review…*, Richmond J. Law & Tech 2011 ;
  *Inconsistent Assessment of Responsiveness…*, DESI IV 2011) **restent non lus.** Cette
  note ne s'appuie sur eux nulle part : le bruit d'assessment y est rapporté depuis les
  mesures propres du track (kappa 2006, appels 2008–2009, redondance 2010–2011).
- **Voorhees & Harman (2005)** reste non lu ; il n'est cité nulle part ici.
- **L'arrêt du track après 2011 n'est pas documenté à la source.** NIST ne recense que
  2006–2011 ; aucune page primaire consultée n'énonce de motif d'arrêt, ni ne confirme le
  récit « 2012 annulé faute de délais » du dossier antérieur. À traiter comme **non
  établi**, pas comme faux.
- **Chiffres d'effectif d'assesseurs manquants pour 2008, 2009 (Batch), 2010 et 2011.**
  Les overviews publient le nombre de *jugements* et parfois le nombre de bins, rarement le
  nombre de personnes. Les cases « non publié » du tableau §6.2 sont des absences dans la
  source, pas des omissions de cette note.
- **Budget : un seul chiffre existe dans tout le corpus lu** — les ≈ 1 400 heures / ≈ 200 000 $
  de 2007. Il est **auto-déclaré, partiel (23 retours de questionnaire) et valorisé à un
  tarif conventionnel** (150 $/h, taux *summer associate*), non facturé. Aucune campagne
  ultérieure ne publie d'équivalent. Toute extrapolation d'un coût par jugement sur les
  autres années serait une reconstruction, pas une donnée.
- **Le nombre d'équipes de 2008 est incohérent entre deux sources primaires** (15 selon
  l'overview 2008, 16 selon l'overview 2009). Non arbitré.
- **La formule `p(d)` de 2009 pour la tâche Interactive n'est pas reprise ici** : cette note
  rapporte le plan de stratification (2ⁿ strates par combinaison de soumissions) et
  l'estimateur, mais les allocations exactes par strate ne figurent que dans les appendices
  par topic des proceedings, non consultés.
- **Les appendices « Per-Topic Scores » des proceedings 2009** (documents [4], [5], [6] de
  l'overview) n'ont pas été ouverts. Les valeurs de `C` par topic, les résultats de
  cohérence par topic et les scores détaillés en proviennent et ne sont donc rapportés ici
  que par leurs agrégats publiés dans l'overview.
- **`l07_eval`, l'outil d'évaluation du track, n'a pas été lu.** Les formules rapportées
  viennent des overviews, pas du code.
