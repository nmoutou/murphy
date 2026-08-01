# Mesurer l'incomplétude et le biais de pool en Recherche d'Information

> Note de recherche — issue #7 (`wayfinder:research`), rattachée à #1.
> Sources primaires uniquement : actes TREC/NIST, SIGIR/ECIR/TOIS/IRJ, papiers
> d'origine des métriques, code de `trec_eval`.
> Rédigée le 2026-08-01.

---

## 0. Ce que la discipline appelle « incomplétude », et pourquoi ce n'est pas notre mot

Le paradigme de Cranfield suppose que **tout document a été jugé pour tout topic**.
Buckley & Voorhees le formulent explicitement : « A basic assumption of the Cranfield
paradigm is that the relevance judgments are complete, i.e., that every document is
judged for every topic »
([Buckley & Voorhees, *Retrieval Evaluation with Incomplete Information*, SIGIR 2004,
§1](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=150469)).

Aucune collection moderne ne satisfait cette hypothèse. Le *pooling* (Sparck Jones &
van Rijsbergen 1975, opérationnalisé par TREC) la remplace par une hypothèse plus
faible : on juge l'union des top-λ de plusieurs systèmes, on déclare non pertinent tout
ce qui n'est pas jugé, et **on parie que l'échantillon de pertinents ainsi trouvé est
non biaisé vis-à-vis des approches de recherche**. Buckley, Dimmick, Soboroff & Voorhees
sont nets sur ce point : « The crucial assumption of pooling is that the sample of
relevant documents found by judging just the pool is unbiased with respect to different
retrieval approaches »
([*Bias and the Limits of Pooling for Large Collections*, NIST / IRJ 10(6), 2007,
§1](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=51236)).

D'où deux grandeurs distinctes, souvent confondues :

| Grandeur | Question | S'estime par |
|---|---|---|
| **Incomplétude** | combien de pertinents manquent ? | extrapolation de profondeur, échantillonnage |
| **Biais de pool** | les manquants manquent-ils *au hasard* ? | leave-one-out, tests de composition |

L'incomplétude est un problème de dénominateur. Le biais est un problème de
représentativité. **Un pool peut être très incomplet et quasi non biaisé** (c'est la
thèse historique de TREC), **ou modérément incomplet et gravement biaisé** (c'est ce que
Buckley et al. 2007 démontrent sur AQUAINT et GOV2). Les instruments ne sont pas les
mêmes.

---

## 1. Le biais de pool : comment on le mesure, et son ampleur publiée

### 1.1 Le test *leave-out-uniques* (LOU)

L'instrument canonique vient de Zobel
([*How Reliable are the Results of Large-Scale Information Retrieval Experiments?*,
SIGIR 1998, §4](https://people.eng.unimelb.edu.au/jzobel/fulltext/sigir98.pdf)) :

> « we selected a run, formed a pool using all runs, then removed from the pool those
> documents contributed only by the selected run. By comparing performance on the
> original pool and the modified pool we can measure the degree to which contributing to
> the pool improves perceived effectiveness. »

On répète pour chaque run et on moyenne. Le delta simule ce qu'un **système extérieur au
pool** subirait. Buckley et al. 2007 en utilisent une variante plus sévère (retirer tout
ce qui n'a été apporté que par les runs *d'un même groupe*), et notent la limite
structurelle du test : « if all the runs use the same or very similar systems, then the
overlap among them will be very high and the LOU test will not detect any bias that may
be present » (§2). **C'est déjà l'aveu que le LOU ne s'applique pas à une collection
mono-système** — voir §6.

### 1.2 Ampleur publiée

Valeurs de LOU (écart moyen de MAP, en % relatif), compilées depuis les sources
primaires :

| Collection | Écart moyen LOU | Max | Source |
|---|---|---|---|
| TREC-5 ad hoc (pool d=100) | **0,5 %** | 3,5 % | [Zobel 1998, §4](https://people.eng.unimelb.edu.au/jzobel/fulltext/sigir98.pdf) |
| TREC-5, 10 requêtes les plus fournies | **7 %** | — | Zobel 1998, §4 |
| TREC-3 | **2,2 %** | 19 % (10 requêtes les plus fournies) | Zobel 1998, §4 |
| TREC-5, pool d=10 | 2,3 % | — | Zobel 1998, §4 |
| TREC-3, pool d=10 | **14 %** | — | Zobel 1998, §4 |
| TREC-8 ad hoc | 0,8 % | — | [Buckley et al. 2007, tab. 1 et §2](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=51236) |
| TREC-8 small web | 1,8 % | — | Buckley et al. 2007, tab. 1 |
| TREC-9 web | 1,1 % | — | Buckley et al. 2007, §2 |
| TREC-8 cross-language | **6,3 %** | — | Buckley et al. 2007, §2 |
| TREC 2001 cross-language | **8,0 %** | — | Buckley et al. 2007, §2 |
| AQUAINT (TREC 2005, pool d=55) | 3,2 % | **23 %** (run `sab05ror1`) | Buckley et al. 2007, §3.2 et tab. 1 |
| TREC 2004 Terabyte (GOV2, d=85) | **9,6 %** | **45,5 %** | Buckley et al. 2007, §5 |
| TREC 2005 Terabyte (GOV2, d=100) | 3,9 % | 17,7 % | Buckley et al. 2007, §5 |

Le seuil d'interprétation retenu par NIST : « Since evaluation scores can change by this
amount by using different relevance assessors or topic subsets, this level of difference
has been considered to be in the noise and the collections deemed reusable »
(Buckley et al. 2007, §2) — c'est-à-dire qu'un LOU **autour de 1 % est jugé négligeable,
6–10 % appelle la prudence**.

### 1.3 La faille du LOU : il ne détecte pas un biais que tous les systèmes partagent

C'est le résultat le plus important de Buckley et al. 2007, et il est contre-intuitif.
Sur les collections Terabyte, le LOU semblait acceptable (3,9 %), et MAP et bpref
classaient les systèmes quasi identiquement — « Perhaps pooling was working just fine
after all » (§5). Faux.

Les auteurs introduisent `titlestat`, la proportion moyenne de documents d'un ensemble
contenant un mot du titre du topic (§3.2), et montrent :

- `titlestat_rel` (calculé sur les pertinents connus) vaut **0,588 pour Disks4&5** et
  **0,719 pour AQUAINT** *sur le même jeu de 50 topics* ; la valeur par topic est plus
  grande pour AQUAINT dans **48 topics sur 50** (t-test apparié, p = 6,25·10⁻¹⁰, §3.2) ;
- le run `sab05ror1` (routing, requêtes construites depuis les pertinents d'une autre
  collection, donc **sans dépendance aux mots du titre**) a un `titlestat` de 0,388
  contre 0,600 en moyenne pour les 49 autres runs, et a apporté **405 pertinents uniques
  sur 2750 documents versés au pool** — « the ratio […] is higher than any other run in
  TREC's history for the major ad hoc collections » (§3.2) ;
- pour GOV2, `titlestat_rel` = 0,889 (2004) et 0,898 (2005) : « any single title word
  occurred in nearly 9 out of 10 judged relevant documents on average » (§5).

Diagnostic : à taille de collection croissante et profondeur de pool constante, **le pool
se remplit d'un seul type de document** (ceux qui contiennent les mots de la requête),
et les autres pertinents n'y entrent jamais. « For sufficiently large document sets
relative to the pool depth, the available space in the pool is filled with this one
document type, violating the assumption of an unbiased judgment set » (§4). Les auteurs
concluent que **la profondeur minimale de pool n'est pas un nombre absolu mais un ratio à
la taille du corpus** (§4).

Deuxième indicateur de biais proposé : **le pourcentage du pool jugé pertinent**. Pour
les collections ad hoc TREC après TREC-4, ≈ 6 % ; pour AQUAINT 17,4 %, pour Terabyte 2004
18,3 % et 2005 **23,0 %** (tab. 1). Un taux anormalement élevé signale que le pool ne
capture plus que la partie « facile » de l'ensemble pertinent.

### 1.4 Ampleur de l'incomplétude proprement dite

Zobel 1998 estime le nombre total de pertinents en ajustant la courbe d'arrivée de
nouveaux pertinents en fonction de la profondeur de pool. La fonction est
`n = C·p^s − 1`, ajustée par régression linéaire sur `log p` et `log(n+1)` (§5) ; pour
TREC-5 il obtient C = 396,3 et s = −0,6304 sur les profondeurs 1–100. Résultats :

- passer d'une profondeur 100 à 200 identifierait **+35 pertinents par requête, soit
  +32 %** ; à profondeur 500, 9358 pertinents contre 5040 observés à d=100 (§5) ;
- validation croisée du procédé : ajusté sur les profondeurs 1–50, il prédit 1296
  nouveaux pertinents (intervalle 1104–1519 à ±1 erreur type) pour les profondeurs
  51–100 ; **1350 ont réellement été observés** (§5) ;
- **≈ 85 % de ces pertinents supplémentaires proviennent des 10 requêtes qui en avaient
  déjà le plus** à d=100 (§5).

Conclusion de l'abstract : « recall is overestimated: it is likely that many relevant
documents have not been found » ; et dans le corps, « it is likely that at best 50 %–70 %
of the relevant documents have been discovered » (§1 et §4).

Vingt ans plus tard, sur ClueWeb, c'est bien pire : Lu, Moffat & Culpepper estiment
« it seems likely that a further one-fifth of the unjudged documents that occur in the
top 50 of the contributing runs could be relevant, **doubling the number of known
answers** »
([*The Effect of Pooling and Evaluation Depth on IR Metrics*, Information Retrieval
Journal 19(4):416–445, 2016,
§2](https://people.eng.unimelb.edu.au/ammoffat/abstracts/lmc16irj.pdf)).

### 1.5 L'annotateur unique — une source de variance séparée, et rassurante

Distincte de l'incomplétude mais souvent invoquée avec elle : la variabilité
inter-annotateurs. Voorhees a mesuré sur TREC un recouvrement (|∩ pertinents| / |∪
pertinents|) entre assesseurs **de l'ordre de 0,30 à 0,49**, avec des ratios de précision
0,605–0,819 et de rappel 0,528–0,695
([Voorhees, *Variations in Relevance Judgments and the Measurement of Retrieval
Effectiveness*, Information Processing & Management 36(5):697–716,
2000](https://www.nist.gov/publications/variations-relevance-judgments-and-measurement-retrieval-effectiveness)).
Sa conclusion est pourtant que « very high correlations were found among the rankings of
systems produced using different relevance judgment sets » : le **classement relatif**
des systèmes est stable malgré un désaccord massif sur les jugements individuels.

**Ce que ça implique pour Murphy** : l'annotateur unique n'est pas le problème principal.
Il dégrade la valeur absolue et interdit de comparer nos scores à ceux d'autrui, mais
n'empêche pas les comparaisons internes (v_n vs v_n+1) si l'annotateur reste le même.
C'est **l'incomplétude et le mono-système** qui mordent.

---

## 2. bpref — la métrique qui ignore les non-jugés

Motivation : « The idea is to measure the effectiveness of a system on the basis of
judged documents only » (Buckley & Voorhees 2004, §2.1). MAP, P@10 et R-précision ne font
aucune différence entre « jugé non pertinent » et « non jugé » ; bpref si.

Définition (§2.1) — pour un topic à `R` pertinents, `r` un pertinent, `n` un membre des
`R` premiers non-pertinents jugés retournés par le système :

```
bpref = (1/R) · Σ_r [ 1 − |n classés au-dessus de r| / R ]
```

Variante `bpref-10`, utilisée dans leurs expériences pour éviter l'effondrement quand
`R` est très petit (dénominateur `10 + R`, sur les `10 + R` premiers non-pertinents
jugés). `trec_eval` implémente les deux, et la variante générale ; le fichier
[`m_bpref.c`](https://github.com/usnistgov/trec_eval/blob/main/m_bpref.c) documente le
traitement : mesure « dependent on only judged docs; no assumption of non-relevance if
not judged » — les non jugés sont **sautés**, pas comptés comme non pertinents.

Protocole d'évaluation de la robustesse (§4) — utile à connaître car **c'est le protocole
que nous pourrons rejouer** : on part des qrels officielles (100 %), on tire pour chaque
topic un ordre aléatoire des pertinents et un des non-pertinents jugés, puis on construit
16 qrels réduites à 90, 80, …, 5, 4, 3, 2, 1 % en prenant les `P × R` premiers pertinents
et `P × N` premiers non-pertinents. Les qrels réduites sont emboîtées et **non biaisées
par construction** (« Since we take random subsets of a qrels that is assumed to be fair,
the reduced qrels are also unbiased with respect to systems »).

Résultats (§4, fig. 2–3, TREC-8/10/12) :

- MAP, P(10) et R-précision **décroissent monotonement** quand les qrels rétrécissent ;
  bpref-10 **croît lentement** et reste comparable en valeur absolue — propriété
  essentielle en pratique, puisque des topics différents ont des niveaux d'incomplétude
  différents ;
- corrélation de Kendall entre le classement système sous qrels 100 % et sous qrels
  réduites : bpref-10 reste **au-dessus de τ = 0,9 jusqu'à 50 %** des jugements sur la
  collection la plus bruitée (TREC-10) et **jusqu'à 25 %** sur TREC-8 ;
- avec jugements complets, bpref-10 vs MAP : τ = 0,934 (TREC-8), 0,895 (TREC-10), 0,942
  (TREC-12) — donc « with complete judgments bpref-10 and MAP will in general agree ».

Limite explicitement posée par les auteurs (§6), et directement pertinente pour nous :
bpref n'est valide que si « given a system and a retrieval rank, the chance of that
document being in the judged pool is independent of whether the document is relevant or
nonrelevant ». C'est-à-dire : **bpref traite l'incomplétude, pas le biais**. Si le
processus de jugement a une chance différente de faire entrer un pertinent qu'un
non-pertinent, bpref est faussé comme les autres.

### 2.1 Les mesures à listes condensées la battent

Sakai montre que filtrer les non jugés de la liste (« condensed list ») puis appliquer
AP, Q-measure ou nDCG est meilleur que bpref
([*Alternatives to Bpref*, SIGIR 2007, pp. 71–78](https://dl.acm.org/doi/10.1145/1277741.1277756)) ;
prolongé dans
[Sakai & Kando, *On information retrieval metrics designed for evaluation with incomplete
relevance assessments*, Information Retrieval 11(5):447–470,
2008](https://link.springer.com/article/10.1007/s10791-008-9059-7).
Lu, Moffat & Culpepper résument le verdict : « Sakai (2007) compares BPref with condensed
recall-based metrics AP′, NDCG′, and QM′, and concludes that applying the condensing
process to existing recall-based metrics gives more discriminative power than BPref.
Among all of the condensed metrics considered, Sakai concluded that NDCG′ and QM′ were
the most suitable choice » (Lu et al. 2016, §2).

**C'est le résultat le plus directement actionnable de tout ce dossier** : on n'a pas
besoin de changer de métrique pour gagner en robustesse, il suffit de **retirer les non
jugés du classement avant de scorer**. Attention néanmoins : condenser ne corrige aucun
biais, et une liste condensée trop courte perd du sens (voir §5.2).

---

## 3. infAP / xinfAP / infNDCG — estimer la métrique au lieu de la calculer

Famille distincte : au lieu d'être robuste à l'incomplétude, on **fait de l'inférence
statistique** sur la valeur qu'aurait la métrique avec des jugements complets. Papier
d'origine : Yilmaz & Aslam, *Estimating Average Precision with Incomplete and Imperfect
Judgments*, CIKM 2006, pp. 102–111 — trois mesures (*induced AP*, *subcollection AP*,
*inferred AP*), égales à AP quand les jugements sont complets et **estimateurs
statistiques d'AP quand les jugements jugés sont un sous-ensemble aléatoire des jugements
complets**. `infAP` est implémentée dans `trec_eval` ; `xinfAP` l'est dans `sample_eval`.

L'extension de 2008 est celle qui nous intéresse le plus
([Yilmaz, Kanoulas & Aslam, *A Simple and Efficient Sampling Method for Estimating AP and
NDCG*, SIGIR 2008](https://www.ccs.neu.edu/home/ekanou/research/papers/mypapers/sigir08b.pdf)),
pour trois raisons, énoncées dans son propre résumé de contributions :

1. **« we derive confidence intervals for infAP »** — donc une **borne d'incertitude**,
   pas un nombre nu (§2) ;
2. échantillonnage **aléatoire stratifié** au lieu d'uniforme, ce qui permet des densités
   de jugement différentes selon les strates ;
3. **« we describe how this approach can be utilized to estimate nDCG from incomplete
   judgments »** (§4).

Le point 3 mérite d'être détaillé, parce qu'il attaque exactement notre problème de coupe
adaptative. Pour estimer nDCG il faut estimer `DCG_I`, le DCG du classement idéal, qui
suppose de connaître **combien de documents existent à chaque grade de pertinence** :

> « the estimation of DCG_I can be derived in a two-step process: (1) For each relevance
> grade ℓ such as gain(ℓ) > 0, estimate the number of documents with that relevance
> grade; (2) Calculate the DCG value of an optimal list by assuming that in an optimal
> list the estimated number of documents would be sorted (in descending order) by their
> relevance grades. » (§4.1)

**Estimer le nombre de documents par grade, c'est exactement estimer `R`.** La discipline
a donc bien traité le cas « la normalisation dépend elle-même des jugements » — mais
elle le résout par **un plan d'échantillonnage probabiliste** : le pool est découpé en
strates disjointes et on tire aléatoirement dans chaque strate avec une probabilité
connue. Sans probabilité d'inclusion connue, l'estimateur n'existe pas. Les auteurs
signalent d'ailleurs une approximation résiduelle : ils supposent
`E[nDCG] = E[DCG]/E[DCG_I]`, c'est-à-dire l'indépendance de DCG et DCG_I, « which is not
necessarily the case. This assumption may result in a small bias » (§4, note 3).

Résultat empirique : sur TREC-8 avec 12,7 % des jugements, xinfAP obtient RMS = 0,0126 et
τ = 0,9345 sur les systèmes pooled, 0,0133 / 0,8678 sur les non-pooled ; à 3,5 % des
jugements, RMS = 0,0206 / τ = 0,8699 (§3, fig. 2). Et « extended infAP (xinfAP) and
infNDCG consistently outperform infAP and nDCG on random judgments » (§5) — le nDCG brut
calculé sur jugements incomplets a une erreur RMS élevée « due to the fact that nDCG is
computed on these judgments as [if they were complete] ».

---

## 4. RBP et ses résidus — la seule métrique qui rapporte nativement une borne

C'est la réponse frontale à la question « laquelle rapporte une borne d'incertitude
plutôt qu'un nombre nu ».

RBP repose sur un modèle d'utilisateur : il examine toujours le 1ᵉʳ document, le 2ᵉ avec
probabilité `p`, le i-ᵉ avec probabilité `p^(i−1)` ; `p` est la **persistance**
([Moffat & Zobel, *Rank-Biased Precision for Measurement of Retrieval Effectiveness*, ACM
TOIS 27(1), art. 2, décembre 2008,
§4.1](https://people.eng.unimelb.edu.au/jzobel/fulltext/acmtois08.pdf)). Le nombre moyen
de documents examinés est `1/(1−p)`, d'où

```
RBP = (1 − p) · Σ_{i=1..d}  r_i · p^(i−1)
```

### 4.1 Le résidu

§4.4, « Bounding the Residual Error » :

> « In the RBP measure it is straightforward to accumulate an uncertainty value, or
> residual, that captures the unknown component of the effectiveness metric. »

Deux contributions au résidu :

- **queue** : si le classement s'arrête à la profondeur `d`, l'incertitude vaut
  exactement `p^d` ;
- **trous** : chaque document non jugé au rang `i` ajoute `(1−p)·p^(i−1)`, c'est-à-dire
  « the weight they would have had if they were relevant ».

Exemple donné par les auteurs pour le classement `$$---$----$-??--?---` (non jugés aux
rangs 13, 14, 17) : incertitude = `p^20 + (1−p)(p^12 + p^13 + p^16)`, d'où

| `p` | RBP borné entre |
|---|---|
| 0,50 | **0,7661 et 0,7663** |
| 0,80 | **0,447 et 0,489** |
| 0,95 | **0,17 et 0,60** |

C'est le comportement recherché : **plus l'utilisateur modélisé est persistant, plus la
mesure dépend de zones non jugées, et plus l'intervalle s'ouvre**. Un résidu large est un
signal de non-mesurabilité, pas un défaut de la métrique.

Le résidu se calcule aussi *a priori*, avant toute expérimentation : avec `p = 0,8` et une
profondeur de jugement `d = 20`, le résidu de queue vaut `0,8^20 = 0,012`, « which implies
that calculated RBP figures should be quoted to at most two decimal places » (§4.4). Pour
quatre décimales il faut `p^d < 0,0001`, soit `d ≳ 9,21/(1−p)` : d = 14 pour p = 0,5,
d = 42 pour p = 0,8, **d = 180 pour p = 0,95**. Autrement dit, un pool de profondeur 100
ne supporte 4 chiffres significatifs que si `p ≤ 0,91`.

Récapitulatif des auteurs (§5) : « In the presence of uncertainty (partial rankings, or
unjudged documents), an error bound can be precisely determined. »

### 4.2 Contre-résultat important : AP n'est *pas* une borne inférieure

Le folklore TREC veut que traiter les non jugés comme non pertinents donne une estimation
pessimiste, donc une borne inférieure. **C'est faux pour AP** (§4.4) :

> « Figure 2 clearly shows that, when average precision is used as the effectiveness
> metric, the default assumptions do not lead to a lower bound being calculated. That is,
> assuming that unjudged documents are irrelevant is not necessarily pessimistic in the
> context of AP. »

Démonstration (§3) : sur `$--$------??????????` avec R = 2 pertinents jugés, AP = 0,75 ;
si **un seul** des 10 non jugés est en fait pertinent, AP **ne peut plus dépasser
0,5909** — parce que découvrir un pertinent augmente `R`, donc le dénominateur. Mais sur
`-------$--??????????` la découverte fait *monter* AP. « on addition of more information
AP can take any value at all between the limiting values of 0 and 1 ».

**C'est le mécanisme exact qui nous menace.** Toute métrique normalisée par le nombre de
pertinents — AP, R-précision, nDCG@R — a un dénominateur qui bouge quand les jugements
bougent, et le sens du mouvement du score n'est pas prévisible.

### 4.3 Moffat & Zobel disqualifient nommément nDCG et P@R pour cette raison

§4.6, sur la normalisation de Järvelin & Kekäläinen :

> « From our point of view, this approach is unsatisfactory, since, to calculate a
> normalized discounted cumulative gain (NDCG) score in this way, all relevant documents
> (and thus the value of R) must be identified. **That is, NDCG has the same issues as AP
> and P@R.** A similar assumption weakens the Q-measure of Sakai (2004). »

Il n'y a pas de formulation plus directe de notre problème dans la littérature primaire.
`nDCG@R` cumule les deux défauts : la normalisation exige `R`, **et** la coupe est `R`.

---

## 5. Les *holes* : le taux de non-jugés dans le top-k

### 5.1 Ce qu'on mesure

Lu, Moffat & Culpepper (IRJ 2016) instrumentent l'incomplétude côté run plutôt que côté
qrels, avec deux statistiques (§2, tab. 4) :

- **`RankUnj`** — rang moyen du **premier** document non jugé ;
- **`NumRelPast`** — nombre moyen de pertinents apparaissant **au-delà** de la profondeur
  de pooling.

| Collection | Profondeur pool | RelInPool | RankUnj | NumRelPast |
|---|---|---|---|---|
| ClueWeb09 | d = 10 | 2,4 ± 3,0 | **12,9 ± 2,6** | 13,6 ± 12,7 |
| ClueWeb09 | d = 12 | 3,0 ± 3,5 | 15,1 ± 2,9 | 15,5 ± 14,5 |
| ClueWeb10 | d = 10 | 3,3 ± 3,2 | **12,3 ± 2,1** | 17,2 ± 13,2 |
| ClueWeb10 | d = 20 | 6,3 ± 6,0 | 22,7 ± 3,0 | 29,1 ± 22,0 |

Lecture : sur ClueWeb10 poolée à d=20, **le premier trou apparaît en moyenne au rang 23**,
et il reste en moyenne 29 pertinents au-delà — soit 4× plus que ce que le pool a trouvé.

Le seuil qualitatif que les auteurs posent (§2) : « if a new non-contributing system is
generating runs in which only a minority of the top-k documents are judged, then the
mismatch between system and test-bed must be regarded as being meaningful, and any scores
that are computed must be handled very carefully. » **Moins de 50 % de jugés dans le
top-k = le score n'est pas défendable.**

### 5.2 Les quatre traitements possibles d'un trou

Taxonomie complète, Lu et al. 2016 §2 (« Dealing with the Unknown ») :

| # | Traitement | Coût | Limite |
|---|---|---|---|
| 1 | **non-pertinence assumée** (`G(i) = 0`) | nul | « at odds with an underlying expectation of new systems » — pénalise précisément l'innovation |
| 2 | **pertinence prédite** (infAP, xinfAP) | plan d'échantillonnage | ne rend pas la collection réutilisable pour des runs post-hoc trop clairsemés |
| 3 | **plages de score / résidu** (Moffat & Zobel) | nul | « significantly more complex to compute for recall-based metrics […] because of the normalization by R » |
| 4 | **listes condensées** (bpref, AP′, nDCG′, QM′) | nul | ne corrige aucun biais |

Le §3 est celui qui répond à la question de l'issue. Version générique de la borne : on
score une fois en donnant gain 0 aux non jugés (**score pessimal**), une fois en leur
donnant gain 1,0 (**score optimiste**), et « these two overall scores are reported as
lower and upper bounds on the true value. In cases where there are few judged documents in
a run, this procedure gives rise to a wide score range, and raises a clear signal that the
evaluation desired was incompatible with the underlying experimental framework. »

Mais l'avertissement qui suit immédiatement est décisif pour nous :

> « Score ranges are significantly more complex to compute for recall-based metrics than
> for utility-based metrics, because of the normalization by R that is involved, which
> means that **the maximum possible score for a run is unlikely to correspond to the
> situation in which all unjudged documents are deemed to be fully relevant**. Moreover,
> the ranges that emerge are typically very broad if anything other than a very small
> minority of the documents in each run are unjudged, regardless of how deep in the
> ranking those unjudged documents appear. »

Et, sans ambiguïté (§4, tab. 9) : « While it is not possible to compute residuals for
recall-based metrics, all of AP, NDCG, and QM are likely to be subject to score
uncertainties **to at least the same extent as RBP(0,95)**. »

Ordres de grandeur des résidus RBP (tab. 9, TREC-8 Robust poolée à d=100, ClueWeb10
poolée à d=20), notation `score+résidu` :

| Collection / p | k = 5 | k = 10 | k = 20 | k = 100 |
|---|---|---|---|---|
| ClueWeb10, RBP(0,95) | 0,019 + **0,950** | 0,063 + **0,815** | 0,133 + 0,599 | 0,265 + 0,190 |
| ClueWeb10, RBP(0,8) | 0,074 + 0,800 | 0,203 + 0,410 | 0,301 + 0,107 | 0,332 + 0,005 |

Sur ClueWeb10 avec p = 0,95, **le résidu est cinquante fois le score mesuré à k = 5**.
Les auteurs commentent : « the residuals are uncomfortably high » (§4). Propriété
structurelle utile : le résidu **ne peut pas croître** quand `k` croît (éq. 4).

### 5.3 Recommandation opérationnelle publiée

Les guidelines finales (§5), dont trois nous concernent directement :

- « in the case of recall-based metrics, those depths should be fixed **in advance** of
  the experimentation being commenced, and should not be revisited as conclusions are
  drawn » ;
- « utility-based metrics should be featured **alongside** recall-based ones if the latter
  are being regarded as the primary point of comparison » ;
- « careful attention should be paid to the number and rank positions of the unjudged
  documents in the corresponding runs, **preferably via the computation of a residual or
  some other indicator of score imprecision** ».

---

## 6. Le cas particulier qui nous concerne : une coupe qui dépend des jugements

L'issue demandait si la littérature traite le cas d'une métrique dont le **paramètre de
coupe dépend lui-même des jugements**. Réponse : **oui, et le verdict est défavorable.**
Trois sources primaires convergent.

**(a) Moffat & Zobel 2008 §4.6** disqualifient nDCG et P@R au motif exact que `R` doit
être connu (cité en §4.3 ci-dessus).

**(b) Buckley & Voorhees 2004 §4** ont *mesuré* le phénomène sans le nommer. Leur
protocole réduit les qrels à `P × R` pertinents par topic ; **la R-précision voit donc sa
coupe se déplacer** à chaque palier, exactement comme nDCG@R chez nous. Résultat : la
R-précision décroît monotonement en valeur absolue (fig. 2) et son τ de Kendall se
dégrade nettement plus vite que celui de bpref-10 (fig. 3). C'est la mesure empirique la
plus proche de notre situation.

**(c) Lu, Moffat & Culpepper 2016 §4** analysent explicitement la confusion des rôles :

> « In the case of NDCG_a@k and AP_b@k, the conflation of the two concepts – with k
> serving both as a top-weightedness parameter, and also a limit governing the summation –
> means that **there is no sense of increasing k to get a "better" approximation of the
> metric**. Increasing k changes the metric to make it less top-focused, and in doing so
> shifts weight further down the ranking; perversely, that shift may then make the
> approximation that is computed less accurate, since a greater fraction of the metrics'
> weighting might consist of unjudged documents. »

Et, plus loin : « A similar complex relationship exists with NDCG_a@k when k ≤ R_d –
increasing the pooling depth d in order to obtain a more comprehensive evaluation makes
the scores less top-weighted and hence **risks increasing the amount of uncertainty that
is implicit in the measured scores** ». Alors qu'avec RBP/ERR, « increasing the evaluation
depth k and/or the pooling depth d serve **only to reduce** the uncertainty ».

**Traduction pour nDCG@R.** Juger davantage de documents produit trois effets simultanés
et de signes différents :

1. `R` augmente → la coupe descend dans le classement ;
2. le dénominateur (DCG idéal) augmente → le score baisse ;
3. la coupe descendue englobe une zone moins jugée → l'incertitude implicite **augmente**.

Il n'existe donc pas de sens dans lequel « juger plus » améliore mécaniquement la mesure
nDCG@R. C'est un point à porter tel quel dans GOLDEN-SET §9 et ADR-007.

**Un instrument publié existe pour borner nDCG malgré tout** :
[Moffat, *Estimating Measurement Uncertainty for Information Retrieval Effectiveness
Metrics*, ACM Journal of Data and Information Quality 10(3), art. 10, septembre
2018](https://dl.acm.org/doi/10.1145/3239572). Le principe, d'après le résumé : ajuster
le paramètre `φ` de RBP de façon à **maximiser la similarité entre le classement système
induit par AP/nDCG et celui induit par RBP**, puis lire le résidu RBP à ce `φ` comme
**estimation de l'incertitude de score attachée à AP et nDCG**. C'est un résidu par
procuration : indirect, mais publié, et c'est la seule voie connue pour attacher une
borne d'incertitude à nDCG.

---

## 7. Ce qui est transposable à une collection solo

Réponse courte : **rien de l'appareil de mesure du biais ; une partie de l'appareil de
mesure de l'incomplétude ; et une seule famille de métriques qui rapporte une borne.**

### 7.1 Ce qui n'est pas transposable — et pourquoi

| Instrument | Pourquoi il tombe |
|---|---|
| **Leave-one-out / leave-one-group-out** | Le test consiste à retirer les pertinents apportés *uniquement* par un run donné. Avec un run, il n'existe aucun apport non unique : le pool réduit est vide et le delta vaut 100 %. Buckley et al. 2007 le posent eux-mêmes : « if all the runs use the same or very similar systems […] the LOU test will not detect any bias that may be present ». **Le LOU n'est pas dégradé par le mono-système, il est indéfini.** |
| **`titlestat_rel` (Buckley et al. 2007)** | Le diagnostic AQUAINT ne repose *pas* sur la valeur absolue mais sur la **comparaison de la même mesure sur deux collections partageant le jeu de topics** : « the problem with the AQUAINT collection is indicated by the difference between AQUAINT titlestat_rel and the Disks4&5 titlestat_rel on the same topic set, not the absolute value » (§5). Sans seconde collection de référence, un `titlestat` isolé n'est pas interprétable. |
| **`infAP` / `xinfAP` / `infNDCG`** | Ce sont des **estimateurs de sondage**. Ils exigent que les documents jugés soient un tirage aléatoire (ou stratifié à probabilités connues) *dans un pool défini*. Des jugements top-k d'un seul système sont un échantillon de commodité de probabilité d'inclusion inconnue : les estimateurs ne sont pas définis. |
| **Extrapolation par nombre de systèmes (Zobel 1998 §5)** | Suppose de pouvoir faire varier le nombre de runs contributeurs. |
| **`% du pool jugé pertinent` comme signal de biais** | Utilisable numériquement, mais le seuil de référence (≈ 6 % pour les collections ad hoc TREC) est calibré sur des pools profonds multi-systèmes en corpus de news. Le transposer à un pool top-k mono-système sur du droit français n'a aucune validité établie. À ne pas utiliser comme seuil ; éventuellement comme série temporelle interne. |

### 7.2 Ce qui est transposable

**(1) L'extrapolation par profondeur de jugement — Zobel 1998 §5. Le meilleur candidat.**
La méthode ajuste `n = C·p^s − 1` sur la courbe des *nouveaux pertinents découverts à
chaque incrément de profondeur*. Cette courbe ne demande **ni plusieurs systèmes, ni
plusieurs annotateurs** : elle demande seulement qu'on ait jugé en descendant le
classement et qu'on ait gardé la profondeur à laquelle chaque pertinent est apparu. Sur
un run unique on ajuste la même loi de puissance et on extrapole vers `R∞`.
Elle est validée en prédiction chez Zobel (prédit 1104–1519 nouveaux pertinents,
1350 observés).

*Caveat honnête à documenter si on l'implémente* : la courbe n'extrapole que les
pertinents **atteignables par le classement de notre système**. Zobel le dit de la
méthode duale : elle « may underestimate the total number of relevant documents, as some
will not be brought into the top 100 of the ranking of any likely retrieval system ».
En solo cette sous-estimation est structurelle et non bornable. Ce qu'on obtient est donc
un **plancher sur `R`**, pas une estimation de `R`. C'est déjà beaucoup : `R̂ ≥ R_connu`
donne une borne sur le déplacement possible de notre coupe.

**(2) Le taux de trous — Lu et al. 2016 §2. Trivialement calculable, à instrumenter.**
`RankUnj` (rang du premier non jugé), `%jugés@k`, et le nombre de non jugés dans le top-k
ne demandent que le run et les qrels. Le seuil publié (**minorité de jugés dans le
top-k ⇒ score non défendable**) est directement applicable. À ajouter à côté de chaque
score, systématiquement.

**(3) Les résidus RBP — Moffat & Zobel 2008 §4.4. La seule borne d'incertitude native.**
Le calcul du résidu est **local à un run** : il additionne `(1−p)·p^(i−1)` sur les rangs
non jugés, plus `p^d`. Aucun pool, aucun autre système, aucun `R`. C'est précisément la
propriété qui le rend transposable : le résidu ne dépend d'aucune grandeur inconnue du
corpus (« does not rely on unknowns such as collection size, or the number of documents
relevant to each query », §5).

**(4) Les listes condensées — Sakai 2007.** Retirer les non jugés puis appliquer nDCG
(`nDCG′`) est sans coût et documenté comme supérieur à bpref. Attention : condenser
raccourcit la liste, donc si notre `R` est déjà petit, `nDCG′@R` scorera sur une liste
condensée dont la longueur peut tomber sous `R`.

**(5) Le protocole d'ablation de qrels — Buckley & Voorhees 2004 §4.** Réplicable seul :
on tire des sous-ensembles aléatoires emboîtés de nos propres qrels (90 %, 80 %, … 10 %)
et on regarde comment nDCG@R bouge. On n'obtient pas de τ de Kendall inter-systèmes
(il faut plusieurs systèmes), mais on obtient **la sensibilité de notre score à
l'ablation de jugements** — c'est-à-dire une mesure directe de « de combien la coupe se
déplace-t-elle si j'avais jugé 20 % de moins ». C'est un capteur, et il est gratuit.
C'est aussi la seule des cinq propositions qui produise un chiffre interprétable comme
une **borne d'erreur sur nDCG@R lui-même**, obtenue empiriquement plutôt qu'analytiquement.

**(5 bis) Un précédent publié pour la construction solo elle-même.** Sanderson & Joho ont
examiné trois façons de bâtir une collection **sans pooling de systèmes**, dont
« assessing the ranked output from a single automatic search with no pooling », et
concluent que « test collections are formed that are as good as TREC » au sens des
métriques de qualité de collection usuelles
([*Forming Test Collections with No System Pooling*, SIGIR 2004, pp. 33–40, résumé
déposé](https://eprints.whiterose.ac.uk/4585/)). C'est le seul appui direct dont nous
disposions pour affirmer que la collection solo n'est pas disqualifiée par principe.
Attention à ne pas sur-lire ce résultat : leur meilleure variante s'appuie sur du
**retour de pertinence manuel** (l'assesseur relance des recherches en cours
d'annotation), pas sur un simple top-k figé — et Carterette rappelle que les jugements
produits par ces méthodes à budget réduit « can significantly bias the evaluation of a
new set of systems »
([*Robust Test Collections for Retrieval Evaluation*, SIGIR 2007,
§1](https://ciir-publications.cs.umass.edu/getpdf.php?id=711)). Autrement dit : bon pour
évaluer *notre* système, douteux pour être réutilisé par un autre. Ce qui est exactement
notre usage.

**(6) Le résidu par procuration — Moffat, JDIQ 2018.** Ajuster `φ` pour que le classement
RBP colle au classement nDCG, puis lire le résidu RBP comme incertitude de nDCG. Suppose
plusieurs systèmes pour faire l'ajustement de `φ` sur des *classements de systèmes* ;
**donc non transposable tel quel**, sauf à remplacer les systèmes par nos versions
successives (v_n) une fois qu'on en aura assez. À garder en réserve.

### 7.3 Métriques rapportant une borne d'incertitude plutôt qu'un nombre nu

Récapitulatif — c'est la question directe posée par l'issue.

| Métrique | Rapporte | Type de borne | Exige un pool multi-systèmes ? |
|---|---|---|---|
| **RBP + résidu** (Moffat & Zobel, TOIS 2008) | `score + résidu` | **borne déterministe** : intervalle exact contenant la vraie valeur | **Non** |
| **infAP / xinfAP** (Yilmaz, Kanoulas & Aslam, SIGIR 2008) | estimation + **intervalle de confiance à 95 %** | borne **statistique** | Non, mais exige un **plan d'échantillonnage aléatoire** |
| **Plages pessimal/optimiste** (Lu et al. 2016 §2) | `[borne inf, borne sup]` | déterministe, mais **très large** et mal définie pour les métriques à rappel | Non |
| **nDCG via résidu RBP** (Moffat, JDIQ 2018) | incertitude estimée de nDCG | indirecte | Oui (ajustement de `φ`) |
| bpref, nDCG′, AP′, nDCG@R | nombre nu | — | — |

**Une seule métrique rapporte nativement une borne d'incertitude liée à l'incomplétude,
et elle est calculable sur une collection solo : RBP avec son résidu.** C'est aussi la
seule qui n'ait besoin ni de `R`, ni du pool, ni d'un second système.

### 7.4 Recommandation

1. **Ne pas remplacer nDCG@R.** Le score primaire reste ce qu'ADR-007 a décidé ; le
   problème n'est pas la métrique mais l'absence d'indicateur d'imprécision à côté d'elle.
2. **Publier RBP(p) + résidu à côté de chaque nDCG@R.** C'est exactement la guideline de
   Lu et al. 2016 §5 (« utility-based metrics should be featured alongside recall-based
   ones »). Le résidu est le capteur d'incomplétude que l'ADR-034 §3 cherchait à
   inventer : il est publié, exact, et calculable sur un run isolé. Choisir `p` bas
   (0,8) si on veut des résidus lisibles à faible profondeur de jugement.
3. **Instrumenter les trous** (`RankUnj`, `%jugés@R`) et refuser de publier un nDCG@R dont
   le top-`R` est majoritairement non jugé.
4. **Rejouer l'ablation de qrels de Buckley & Voorhees 2004 §4** sur notre golden-set pour
   chiffrer la sensibilité propre de nDCG@R au déplacement de coupe. C'est le seul chiffre
   qui répondra vraiment à « de combien nos qrels incomplètes déplacent-elles la coupe ».
5. **Envisager l'extrapolation de Zobel** pour obtenir un plancher sur `R`, en documentant
   qu'il s'agit d'un plancher atteignable-par-notre-système, pas d'une estimation de `R`.
6. **Ne pas prétendre mesurer le biais de pool.** Nous ne le pouvons pas, et le prétendre
   serait plus dommageable que de l'assumer. La position défendable est : « collection
   mono-système, biais de pool non mesurable par construction, incomplétude bornée par le
   résidu RBP et signalée par le taux de trous ».

---

## Sources

Toutes consultées directement ; lien vers l'exemplaire primaire quand il est en accès
libre.

- Justin Zobel. *How Reliable are the Results of Large-Scale Information Retrieval
  Experiments?* SIGIR 1998, pp. 307–314.
  <https://people.eng.unimelb.edu.au/jzobel/fulltext/sigir98.pdf>
- Ellen M. Voorhees. *Variations in Relevance Judgments and the Measurement of Retrieval
  Effectiveness.* Information Processing & Management 36(5):697–716, 2000.
  <https://www.nist.gov/publications/variations-relevance-judgments-and-measurement-retrieval-effectiveness>
- Chris Buckley, Ellen M. Voorhees. *Retrieval Evaluation with Incomplete Information.*
  SIGIR 2004, pp. 25–32.
  <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=150469>
- Mark Sanderson, Hideo Joho. *Forming Test Collections with No System Pooling.*
  SIGIR 2004, pp. 33–40. Fiche et résumé :
  <https://eprints.whiterose.ac.uk/4585/> — notice dblp :
  <https://dblp.org/rec/conf/sigir/SandersonJ04.html>
- Emine Yilmaz, Javed A. Aslam. *Estimating Average Precision with Incomplete and
  Imperfect Judgments.* CIKM 2006, pp. 102–111.
  <https://dl.acm.org/doi/10.1145/1183614.1183633>
- Tetsuya Sakai. *Alternatives to Bpref.* SIGIR 2007, pp. 71–78.
  <https://dl.acm.org/doi/10.1145/1277741.1277756>
- Ben Carterette. *Robust Test Collections for Retrieval Evaluation.* SIGIR 2007,
  pp. 55–62. <https://ciir-publications.cs.umass.edu/getpdf.php?id=711>
- Chris Buckley, Darrin Dimmick, Ian Soboroff, Ellen Voorhees. *Bias and the Limits of
  Pooling for Large Collections.* NIST, 2007 ; Information Retrieval 10(6):491–508.
  <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=51236>
- Tetsuya Sakai, Noriko Kando. *On Information Retrieval Metrics Designed for Evaluation
  with Incomplete Relevance Assessments.* Information Retrieval 11(5):447–470, 2008.
  <https://link.springer.com/article/10.1007/s10791-008-9059-7>
- Emine Yilmaz, Evangelos Kanoulas, Javed A. Aslam. *A Simple and Efficient Sampling
  Method for Estimating AP and NDCG.* SIGIR 2008, pp. 603–610.
  <https://www.ccs.neu.edu/home/ekanou/research/papers/mypapers/sigir08b.pdf>
- Alistair Moffat, Justin Zobel. *Rank-Biased Precision for Measurement of Retrieval
  Effectiveness.* ACM TOIS 27(1), article 2, décembre 2008.
  <https://people.eng.unimelb.edu.au/jzobel/fulltext/acmtois08.pdf>
- Xiaolu Lu, Alistair Moffat, J. Shane Culpepper. *The Effect of Pooling and Evaluation
  Depth on IR Metrics.* Information Retrieval Journal 19(4):416–445, 2016.
  <https://people.eng.unimelb.edu.au/ammoffat/abstracts/lmc16irj.pdf>
- Alistair Moffat. *Estimating Measurement Uncertainty for Information Retrieval
  Effectiveness Metrics.* ACM Journal of Data and Information Quality 10(3), article 10,
  septembre 2018. <https://dl.acm.org/doi/10.1145/3239572>
- NIST. `trec_eval`, code source — implémentation de bpref et traitement des non-jugés.
  <https://github.com/usnistgov/trec_eval/blob/main/m_bpref.c>
