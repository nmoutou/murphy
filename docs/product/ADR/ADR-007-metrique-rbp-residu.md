# ADR-007 — Métrique de comparaison : RBP(p) + résidu

**Statut** : acté (chantier 4, 17 juillet 2026) — **réécrit le 2 août 2026**
([ticket #14](https://github.com/left-eyebr0w/murphy/issues/14)) — **§6.2 amendé
le 8 août 2026** ([ticket #23](https://github.com/left-eyebr0w/murphy/issues/23))

> ⚠️ **Cet ADR a été réécrit, pas amendé.** Sa décision de 2026-07-17 était
> `nDCG@R` ; elle est **retirée**. Ce qui survit est son **argument** — le refus
> des coupes constantes — et il survit intact. La rédaction antérieure est
> conservée en fin de document. **Le fichier a changé de nom** :
> `ADR-007-metriques-ndcg-r.md` → `ADR-007-metrique-rbp-residu.md`.

## Contexte

`CADRAGE_evaluation` §9 demandait de fixer des valeurs de `k`. Or les `k` fixes
relèvent du modèle web search (affichage top-k), incompatible avec l'invariant
d'exhaustivité des sources. La rédaction de 2026-07-17 en avait conclu qu'il
fallait une **coupe adaptative**, et `R` était la seule grandeur adaptative
disponible.

Deux faits établis depuis renversent la conclusion sans toucher à la prémisse.

**1. `nDCG@R` ne s'applique qu'où `R` est indisponible.** Le routage de métrique
([#3](https://github.com/left-eyebr0w/murphy/issues/3)) envoie `nDCG@R` sur la
seule branche des **ensembles ouverts**. Cette branche est peuplée uniquement
par `concept_vers_instance` ([#9](https://github.com/left-eyebr0w/murphy/issues/9)),
c'est-à-dire par les **30 cas jugés** — le seul endroit du dispositif où `R`
n'est ni connu ni estimable. Les 120 cas gratuits, dont l'ensemble-réponse est
déterminé par un fait, ont un `R` **exact** et ne passent pas par `nDCG@R`.

`R` n'y est pas seulement inconnu : il n'est pas **estimable**. Le TREC Legal
Track l'estime par Horvitz-Thompson à 500–2 500 jugements par topic, et concède
encore que *« substantial estimation errors are possible on individual
topics »*. Le budget de Murphy est de ≈ **20 jugements par cas**
([#11](https://github.com/left-eyebr0w/murphy/issues/11)), d'où la décision du
protocole de pooling : **on n'estime pas `R`, on borne le score**
([#18](https://github.com/left-eyebr0w/murphy/issues/18) §6).

**2. La littérature primaire disqualifie nommément la famille.** Moffat & Zobel,
*Rank-Biased Precision*, ACM TOIS 27(1) art. 2, 2008, §4.6 : *« to calculate a
normalized discounted cumulative gain (NDCG) score in this way, all relevant
documents (and thus the value of R) must be identified. **That is, NDCG has the
same issues as AP and P@R.** »* Trois conséquences documentées : traiter les
non-jugés comme non pertinents **ne donne pas une borne inférieure** pour une
métrique normalisée par `R` (§4.2) ; **juger plus n'améliore pas mécaniquement
la mesure** (Lu, Moffat & Culpepper, IRJ 2016, §4) ; et **aucun résidu n'est
calculable** pour une métrique fondée sur le rappel (*ibid.* §2).

## Décision

### 1. `nDCG@R` est retiré

Retrait **sec** : ni métrique primaire, ni diagnostic publié à côté. Un nombre
nu publié auprès d'un intervalle serait cité comme un nombre, parce qu'il est
plus commode à citer.

### 2. Métrique de comparaison unique : **RBP(`p`) + résidu**

```
RBP = (1 − p) · Σ_{i=1..d}  g_i · p^(i−1)
```

sur **les 120 cas où une comparaison a un sens** — les 90 cas gratuits de
cardinalité `R ≥ 1` et les 30 cas du noyau jugé, sur 150 au total. RBP ne
demande pas `R` : il couvre donc aussi les cas gratuits, où il n'y a d'ailleurs
**aucun trou**, l'ensemble-réponse étant exact et tout document remonté étant
jugé par construction.

**Conséquence, et elle est forte : le résidu de la couche gratuite est nul.**
Pas de trous, et une queue de `0,75¹⁰⁰ ≈ 3·10⁻¹³` sous le `d_min` du §4. **Toute
l'incertitude du dispositif vient donc des 30 cas jugés.** C'est un effet du
découplage de `d_min`, qui n'ouvre pas seulement l'avenir de `p` : il annule le
résidu là où les qrels sont complètes par construction.

**Exception, et elle est structurelle** : sur les 30 cas `absence_hors_corpus`
(`R = 0`), tous les gains valent 0, donc `RBP = 0` pour tout run quel que soit
le bruit remonté. La métrique y est définie mais **identiquement nulle, donc
sans pouvoir discriminant**. Cette branche reste **précision seule** (statut
ADR-029) — ce qu'elle était déjà, pour la même raison de fond : sans document
pertinent, il n'y a pas de classement à évaluer.

**Elle n'est pas inerte pour autant.** Sa lecture propre — *le taux de résultats
au-delà du seuil de score, sur un jeu où toute remontée est un faux positif*
(`GOLDEN-SET.md` §8.1) — **se compare entre configurations** : moins de
remontées vaut mieux, et une régression du *fail-fast* s'y voit. Ce qui n'existe
pas sur cette branche est une métrique de **classement**, et cette lecture ne se
compare pas aux deux autres branches, faute de dénominateur commun.

**Le refus des coupes constantes tient, et il est mieux servi.** RBP n'est pas
une coupe mais une **pondération géométrique** : il n'a pas à choisir où couper,
donc il n'a plus besoin d'une coupe adaptative pour réaliser ce refus.

### 3. Lectures de rapport, par branche

| Condition | Cas v1 | Rapport / couverture | **Comparaison** |
|---|---|---|---|
| `R = 0` | 30 | précision seule, statut ADR-029 | **taux de remontée au-delà du seuil** — `RBP` y est identiquement nul |
| `R ≥ 1`, ensemble clos | 90 | `Recall@R` tout-ou-rien (`R = 1` se *lit* success@1) | RBP(`p`) + résidu |
| ensemble ouvert | 30 | — | RBP(`p`) + résidu |

`Recall@R` reste **exact** sur les 90 cas clos, et y est identique à la
R-précision et à `F1@R` (TREC Legal Track 2009 §3.10.4 : *« at depth R,
precision, recall and F1 are all the same »*).

### 4. `p` est fixé par une **règle**, jamais par une valeur

> `p` est le plus grand `p` tel que le **résidu de queue** à la profondeur de
> jugement médiane atteinte reste sous la précision qu'on prétend publier :
> `p^d̄ ≤ 0,01`, soit **`p = 0,01^(1/d̄)`**.

*On achète le modèle d'utilisateur le plus persistant que le budget sache
mesurer.* Le droit est orienté rappel et pousse vers un `p` élevé ; le budget
l'interdit, et la règle dit de combien.

| `p` | Poids top 10 | Docs examinés `1/(1−p)` | Résidu de queue à `d̄ = 16` |
|---|---|---|---|
| 0,50 | 99,9 % | 2 | 0,000015 |
| **0,750** | **94 %** | **4,0** | **0,010** |
| 0,80 | 89 % | 5 | 0,028 |
| 0,90 | 65 % | 10 | 0,185 |
| 0,95 | 40 % | 20 | 0,440 |

- **Au pilote la règle se résout en forme close.** Un seul run : l'allocation
  gloutonne dégénère en « juger dans l'ordre de rang »
  ([#18](https://github.com/left-eyebr0w/murphy/issues/18) §6), le poids au rang
  `i` vaut `(1−p)·p^(i−1)` pour tous les cas, donc la profondeur atteinte est
  **uniforme quel que soit `p`** — il n'y a ni valeur provisoire ni circularité.
  **`d̄` compte les jugements *neufs*, non les jugements *rendus*** : le
  **contrôle d'auto-cohérence** (≈ 20 % du budget,
  [#9](https://github.com/left-eyebr0w/murphy/issues/9) condition 2, inscrit au
  budget par [#11](https://github.com/left-eyebr0w/murphy/issues/11)) re-juge des
  couples *(cas, document)* **déjà jugés** et n'ajoute donc **aucune
  profondeur**. Sur ≈ 600 jugements dont 20 % de re-jugement :
  `480 / 30 = 16`, d'où **`p = 0,01^(1/16) = 0,750`**.
- **C'est une valeur de *planification*, pas le mot de la fin.** `d̄` est une
  profondeur **mesurée** : le pilote la rendra, et `p` s'y ajustera. Ce que 0,750
  fixe est l'allocation *pendant* le pilote — donc ce qui produira `d̄`.
- **En campagne**, `p` est **déclaré par génération de pool**, calculé sur la
  profondeur médiane réalisée de la génération précédente.
- **`p` est publié avec tout score.** Deux runs notés à des `p` différents ne
  sont pas comparables ; la re-notation (ADR-032 §2) restaure la comparabilité.
- **Identité à ne pas manquer** : sous cette règle, la formule d'origine
  `d_min = ⌈ln(0,01)/ln(p)⌉` rend **exactement `d̄`** — soit 16. Le découplage du
  §4 n'ajoute donc pas de la marge à une marge : il en crée là où il n'y en avait
  **aucune**.
- **Le résidu de queue n'est employé que pour ce qu'il sait faire.** `p^d` n'est
  **pas** le résidu total — le terme des trous s'y ajoute, rang par rang — donc
  il ne borne aucun score. Il est en revanche la seule part connaissable *avant*
  expérimentation, donc l'instrument exact pour choisir `p` *ex ante*.

### 5. Les grades entrent par **projection linéaire** `g/3`

L'échelle 0–3 d'ADR-005 est un **compte de portes franchies** dans une cascade
de trois tests binaires, non une échelle d'intensité — ADR-005 a nommément
rejeté l'intensité. Un compte se projette linéairement. La pertinence graduée
étant un **invariant** (ADR-016), la binarisation est écartée.

### 6. Un résultat publié n'est plus un nombre nu

1. **Tout score est `score + résidu`**, le résidu calculé **trou par trou sur le
   run**, jamais depuis une profondeur nominale.
2. L'écart apparié entre deux configurations hérite d'une **borne
   déterministe**, et elle est **atteignable** — ⚠️ **amendé le 8 août 2026**
   ([#23](https://github.com/left-eyebr0w/murphy/issues/23)), voir l'encadré
   ci-dessous pour la rédaction antérieure et son motif de retrait.

   Soit `w_A(d) = (1−p)·p^(rang_A(d)−1)` le poids du document non jugé `d` dans
   le classement de `A`, nul si `d` n'est pas dans le top-`d_min` de `A`. Le gain
   `g(d)` est celui **du document**, donc le même des deux côtés — les deux
   enclos individuels ne sont **pas** indépendants. D'où

   ```
   RBP_A − RBP_B  ∈  [ a − b − Σ_d (w_B−w_A)⁺ ,  a − b + Σ_d (w_A−w_B)⁺ ]

   largeur  =  Σ_d | w_A(d) − w_B(d) |
   ```

   **atteinte** à un sommet (`g(d) ∈ {0,1}`), donc atteignable sur l'échelle 0–3
   projetée en `g/3`. Le terme de **queue** fait exception et reste additif : les
   documents au-delà du rang `d_min` ne sont pas identifiés, donc ne s'apparient
   pas (`0,75¹⁰⁰ ≈ 3·10⁻¹³`).

   `r_A + r_B` **majore** cette largeur au lieu de lui être égal, avec égalité au
   seul cas où les ensembles de non-jugés sont disjoints. **L'allocation
   gloutonne de [#18](https://github.com/left-eyebr0w/murphy/issues/18) §6 ne
   bouge pas** : elle reste **monotone** sur la largeur resserrée — juger `d` le
   retire des non-jugés des deux côtés — donc l'arrêt prématuré reste sûr et le
   préfixe exact. Ce qui tombe est l'**identité de fonctions** : on achète sur
   l'agrégat, on lit sur la structure. Une part du budget n'achète donc rien pour
   la comparaison courante ; c'est le prix de l'agnosticité aux paires, et il est
   assumé — un jugement est permanent et agnostique au run, une largeur de paire
   est dérivée à la lecture.

   **Sentinelle publiée avec l'intervalle**, par paire et sans seuil :
   `taux d'annulation = 1 − Σ|w_A−w_B| / (r_A + r_B)`, le recouvrement **pondéré**
   des non-jugés. Elle n'est pas la résolution de l'instrument — c'est la largeur
   qui l'est, et elle a ses deux terminaux depuis
   [#20](https://github.com/left-eyebr0w/murphy/issues/20) — elle **audite** le
   resserrement. **Une seule largeur est publiée, la resserrée** : en publier deux
   ferait citer la plus commode, motif du quatrième hash refusé en #18 §0.

   **Portée réelle** : le resserrement ne mord que sur les **30 cas jugés**, les
   90 cas gratuits comparables étant à résidu nul (§2). Il porte donc sur toute
   l'incertitude du dispositif, mais ne touche pas les trois quarts des cas
   comparables.

   **Conditions d'emploi** — chacune désigne ce qu'il faut rouvrir si elle tombe :
   les qrels portent sur des **identités de document**
   ([#9](https://github.com/left-eyebr0w/murphy/issues/9) §4 — sur des chunks,
   `g(d)` n'est pas le même objet des deux côtés et l'appariement n'existe pas) ·
   l'échelle de gain **contient 0 et 1** (sinon la borne reste valide et cesse
   d'être atteignable) · la queue reste négligeable **relativement** à une largeur
   qui, elle, rétrécit (à `p` = 0,955 elle vaut ≈ 1 % : à rouvrir si `p` monte
   en v2) · il y a **plusieurs** configurations comparées et des contributeurs qui
   ne sont pas comparés (#18 §4), ce qui interdit une allocation par paire.

   > ⚠️ **Rédaction antérieure (2 août 2026, [#14](https://github.com/left-eyebr0w/murphy/issues/14)), retirée le 8 août.**
   >
   > > « L'écart apparié entre deux configurations hérite d'une **borne
   > > déterministe** : si `RBP_A ∈ [a, a+r_A]` et `RBP_B ∈ [b, b+r_B]`, l'écart
   > > vrai est dans **`[a − b − r_B, a − b + r_A]`**. Sa largeur `r_A + r_B` est
   > > exactement ce que l'allocation gloutonne de #18 §6 minimise à budget
   > > donné : **la règle d'achat des jugements et le critère de décision sont la
   > > même fonction.** »
   >
   > **L'enclos était valide ; la seconde phrase est fausse.** Les deux extrémités
   > ne sont atteintes que si les non-jugés de `A` valent tous 1 *pendant que* ceux
   > de `B` valent tous 0 — or `A` et `B` classent le même corpus, et un document
   > partagé monte les deux scores ensemble. La borne était donc **plus large que
   > l'ensemble des écarts possibles**, d'autant plus que les configurations sont
   > proches — c'est-à-dire le plus là où B-10 sert. Sens de faute
   > **conservateur** (la porte refusait trop, elle ne déclarait rien de faux),
   > donc **aucune décision antérieure n'est à défaire**. Le défaut n'était pas la
   > gradation mais une **somme prise trop tôt** : `r_A + r_B` jette l'identité des
   > documents sur lesquels le résidu est assis. Sixième instance de *cesser
   > d'agréger plutôt que baisser le seuil*.
3. **Porte** : si cet intervalle contient zéro, **aucun test n'est recevable**.
   La phrase à écrire est *« au budget de jugement dépensé, ces deux
   configurations ne sont pas distinguables »* — jamais *« pas de différence
   significative »*.
4. Le **test apparié** ne s'exerce que sur les écarts dont l'intervalle exclut
   zéro. Il répond à l'autre question : cet écart survit-il au changement de jeu
   de cas.
5. **Refus de publication** si le top-`k` d'un run est majoritairement non jugé
   (Lu et al. 2016 §2) ; `RankUnj` et `%jugés@k` publiés à côté de chaque score.

## Alternatives rejetées

- **`nDCG@k` / `Recall@k` à `k` constants** : cohérents avec un affichage top-k
  que Murphy n'a pas. *(Rejet de 2026-07-17, maintenu.)*
- **`nDCG@R`** : voir Contexte. Rejeté d'abord pour une raison **interne** — sa
  seule branche d'emploi est la seule où `R` est indisponible — la littérature
  ne faisant que confirmer.
- **Conserver `nDCG@R` en diagnostic** : un nombre nu à côté d'un intervalle
  cannibalise le diagnostic.
- **`F1@K` avec `K` déclaré par le système** (Legal Track 2008–2009) : **non
  calculable** — `estF1@k` se calcule sur les grandeurs estimées d'un plan de
  sondage à 500–2 500 jugements/topic. Subsidiairement : `K` déclaré présuppose
  un adversaire (saturé à `K_max` dès 2008) ; le track l'a retiré en 2011
  (*« F1 sheds no additional light »*). `F1@R` survit sous le nom `Recall@R`.
- **infAP / xinfAP / infNDCG** : estimateurs de sondage, non définis sur un
  échantillon de commodité mono-système.

## Conséquences

- **Le corollaire de ventilation est dissous.** La rédaction antérieure posait
  que restreindre les qrels à un sous-ensemble change `R`, donc la coupe, donc
  qu'*« une ventilation est une mesure distincte, à dénominateur propre — elle
  ne se compare ni à l'agrégat ni à une autre ventilation »* (ADR-030). Cette
  gêne était **entièrement** un effet de la normalisation par `R`. RBP se
  moyenne par cas sans dénominateur global : **une ventilation redevient une
  moyenne sur un sous-ensemble, directement comparable** à l'agrégat et aux
  autres ventilations.
- **L'unicité de la métrique de décision redevient atteignable** : une seule
  grandeur de comparaison couvre les 120 cas comparables, là où le routage de
  [#3](https://github.com/left-eyebr0w/murphy/issues/3) l'avait cassée en trois.
  Elle n'est pas totale — la branche `R = 0` n'a pas de comparaison du tout —
  mais l'irréductibilité y est **structurelle**, non un artefact de métrique.
- **`d_min` se découple de `p`** et passe à **100** (amendement à
  [#18](https://github.com/left-eyebr0w/murphy/issues/18) §8 clause 1). La
  profondeur d'**archive** n'est pas une grandeur de mesure ; sans ce
  découplage, une hausse de `p` rendrait inexploitables les runs déjà archivés.
- **Le dimensionnement reçoit une seconde dérivation.** La porte du §6.3 donne
  un critère là où [#11](https://github.com/left-eyebr0w/murphy/issues/11)
  n'avait qu'une règle de trois : *on juge jusqu'à ce que l'intervalle d'écart
  exclue zéro pour l'effet qu'on veut détecter*
  ([#20](https://github.com/left-eyebr0w/murphy/issues/20)).
- **Sensibilité à la complétude des qrels : le sens du problème change.** La
  rédaction antérieure la subissait (`R` dépend des jugements). RBP la **mesure**
  et la publie ; et contrairement à `nDCG@R`, augmenter la profondeur de
  jugement ne fait que **réduire** l'incertitude (Lu et al. 2016 §4).
- **Le protocole d'ablation de qrels** (Buckley & Voorhees 2004 §4), retenu pour
  chiffrer la sensibilité propre de `nDCG@R`, **devient sans objet**.
- **Réserve ouverte** : la borne du résidu sous **gains gradués** n'a pas été
  vérifiée à la source →
  [#22](https://github.com/left-eyebr0w/murphy/issues/22). Repli connu si elle
  ne tient pas : binarisation à `g ≥ 2`.

## Références

ADR-005 (échelle 0–3, cascade q1–q3) · ADR-006 (agrégation) · ADR-008 (format
qrels/runs) · ADR-016 (pertinence graduée, invariant) · ADR-029 (strate 2
rétrogradée) · ADR-030 (ventilation — réserve dissoute) · ADR-032 (re-notation)
· ADR-035 (paradigme TREC) · `docs/product/recherche/incompletude-qrels.md`
§4–§7 · `docs/product/recherche/deep-sampling-legal-track.md` §3 ·
`VERSIONS.md` (DoD v0)

---

<details><summary><strong>Rédaction antérieure (17 juillet – 2 août 2026)</strong></summary>

> ## Décision
>
> **Rejet des k fixes.**
>
> - Métrique de décision **unique** : **nDCG@R** (coupe adaptative = nombre
>   de pertinents de la requête), **test statistique apparié** dessus.
> - Diagnostics : MAP, R-Precision, Recall@2R (passage) ; Doc-MRR,
>   Doc-Recall@R (document).
> - Côté produit : listes de longueur variable par **seuil de score** — le
>   seuil est une stratégie de config.
> - Seule profondeur opérationnelle restante : le **pooling** (paramètre de
>   collecte, définissable en multiple de R).
>
> ## Conséquences
>
> - Sensibilité accrue à la **complétude des qrels** (R dépend des
>   jugements) → importance renforcée du **pooling**. *(Amendé par
>   ADR-029 : les citations minées, initialement citées ici comme second
>   levier, ne sont plus une source de qrels — la strate 2 est un
>   diagnostic de précision. La complétude des qrels repose donc
>   entièrement sur le pooling et sur le golden-set humain, B-08.)*
>
> - **Corollaire pour toute ventilation** (par opération, par base) :
>   restreindre les qrels à un sous-ensemble **change R, donc la coupe**. Une
>   ventilation est une **mesure distincte**, à dénominateur propre — elle ne se
>   compare ni à l'agrégat ni à une autre ventilation (ADR-030).

*Les diagnostics MAP / R-Precision / Recall@2R / Doc-Recall@R sont normalisés
par `R` ou coupés à un multiple de `R` : ils tombent avec la décision
principale. `Doc-MRR` survit comme lecture de `Recall@R` à `R = 1`
([#3](https://github.com/left-eyebr0w/murphy/issues/3) §4), non comme branche de
routage.*

</details>
