# Collections de test à requêtes générées — ce que dit la littérature

**Statut** : note de recherche. Ne décide rien, ne modifie aucun ADR. Rapporte des
faits sourcés, pour alimenter la réécriture du protocole de génération de B-08 et
pour éprouver le constat central d'ADR-034.

**Ticket** : [#6](https://github.com/left-eyebr0w/murphy/issues/6) (part of #1)
**Date** : 1er août 2026
**Périmètre des sources** : publications RI primaires (SIGIR, ECIR, ICLR, EMNLP,
TREC/NIST), pages officielles des méthodes. Aucun billet de blog, aucune
documentation commerciale d'outil RAG.

---

## 0. Avertissement de lecture — trois objets qu'on confond

La littérature citée dans `WIP/B-08-cadrage.md` mélange trois objets qui n'ont ni
le même but ni le même statut épistémique. Les distinguer est le préalable à toute
lecture utile.

| Objet | Ce qui est produit | Usage revendiqué par les auteurs |
|---|---|---|
| **Expansion de documents** (doc2query, docTTTTTquery) | des requêtes *ajoutées au document* avant indexation | ingénierie d'index. **Jamais** une collection de test |
| **Génération de données d'entraînement** (InPars, Promptagator, pseudo test collections) | des paires (requête, document) synthétiques | **entraînement / fine-tuning**. L'évaluation se fait sur des requêtes réelles |
| **Collection de test synthétique** (Rahmani et al. 2024, SynDL) | requêtes *et* jugements synthétiques, évalués comme une collection | évaluation — c'est le seul des trois qui revendique le statut de golden-set |

Trois des quatre méthodes citées par B-08 (doc2query, InPars, Promptagator) ne
sont **pas** des méthodes de construction de collection de test, et leurs auteurs
ne les présentent pas comme telles. La quatrième (RAGAS) n'est pas non plus une
collection de test : c'est un cadre d'évaluation *sans référence*, qui ne produit
aucun qrel. Une seule ligne de travaux — récente, 2024–2025 — revendique
explicitement l'évaluation.

---

## 1. Les méthodes elles-mêmes

### 1.1 doc2query / docTTTTTquery — expansion, pas évaluation

Nogueira, Yang, Lin, Cho, *Document Expansion by Query Prediction*, arXiv
1904.08375, 2019 — <https://arxiv.org/abs/1904.08375>.

> « we propose a simple method that predicts which queries will be issued for a
> given document and then expands it with those predictions with a vanilla
> sequence-to-sequence model, trained using datasets consisting of pairs of query
> and relevant documents »

Points à retenir :

- le modèle de génération est **entraîné sur des requêtes réelles** (paires
  requête/document pertinent, typiquement MS MARCO). Les requêtes générées sont
  des imitations d'une distribution réelle observée, pas des requêtes inventées
  ex nihilo ;
- les requêtes produites sont **concaténées au document et indexées**. Elles ne
  sont jamais posées à un système, jamais jugées, jamais utilisées comme cas de
  test. La sortie de doc2query est un *index*, pas une collection ;
- docTTTTTquery (Nogueira & Lin, rapport technique, 2019 —
  <https://cs.uwaterloo.ca/~jimmylin/publications/Nogueira_Lin_2019_docTTTTTquery-v2.pdf>,
  code : <https://github.com/castorini/docTTTTTquery>) remplace le transformeur
  seq2seq par T5 et n'introduit aucun changement de statut méthodologique.

**Conséquence pour B-08** : citer doc2query comme précédent d'une collection de
test à requêtes générées est un contresens. C'est un précédent d'*ingénierie
d'index*.

### 1.2 InPars — données d'entraînement, évaluation sur requêtes réelles

Bonifacio, Abonizio, Fadaee, Nogueira, *InPars: Unsupervised Dataset Generation
for Information Retrieval*, SIGIR 2022 — <https://arxiv.org/abs/2202.05144>,
DOI [10.1145/3477495.3531863](https://dl.acm.org/doi/10.1145/3477495.3531863).

Ce qui est généré : à partir d'un document échantillonné du corpus, GPT-3 (Curie)
produit une question en few-shot (prompt « vanilla » ou « GBQ », guidé par de
bonnes questions). Le document source devient le positif ; le négatif est tiré au
hasard parmi 1000 documents ramenés par BM25 sur la requête générée.

Ce qui est fait des données : **entraînement uniquement**. L'évaluation se fait
sur MS MARCO, TREC-DL, Robust04, Natural Questions, TriviaQA — des collections à
requêtes **réelles**.

Deux chiffres qui comptent plus que le reste :

- **90 % du matériau généré est jeté.** « Of the 100,000 questions generated (and
  their respective input documents), we use the top K=10,000 pairs w.r.t to p_q
  as positive examples for finetuning our models » (§3). Le filtre est la
  log-probabilité de la question sous le modèle générateur ;
- **ne pas filtrer coûte 4 points de MRR@10** : « Finetuning on all 100,000
  synthetic examples leads to a 4 MRR@10 points decrease on MS MARCO when compared
  to the top K filtering approach » (§6.2).

Et une observation des auteurs qui vise directement le tirage aléatoire de germes :

> « we sample passages from the MS MARCO corpus to generate questions that do not
> often appear in the original relevant passage set (e.g., footnotes, texts about
> advertisements, passages with multiple topics, etc.) » (§ discussion MS MARCO)

C'est le constat empirique que **tout chunk n'est pas un germe de question**, et
que le tirage uniforme dans le corpus produit majoritairement des germes dont
personne ne dérive de besoin. Les auteurs l'invoquent pour expliquer pourquoi
leurs exemples synthétiques *dégradent* un modèle déjà entraîné sur 530 k exemples
annotés manuellement.

### 1.3 Promptagator — le filtre de qualité est un test de retrouvabilité

Dai, Zhao, Ma, Luan, Ni, Lu, Bakalov, Guu, Hall, Chang, *Promptagator: Few-shot
Dense Retrieval From 8 Examples*, ICLR 2023 — <https://arxiv.org/abs/2209.11755>.

Trois composants : génération de requêtes par prompt few-shot (8 exemples de la
tâche cible), **filtrage par cohérence aller-retour**, puis entraînement du
retriever. Là encore : **entraînement**, évaluation sur BEIR (requêtes réelles).

Le point le plus important de tout ce dossier est la définition du filtre :

> « The filtering step improves the quality of generated queries by ensuring the
> round-trip consistency (Alberti et al., 2019): a query should be answered by the
> passage from which the query was generated. **In our retrieval case, the query
> should retrieve its source passage.** » (§3.2)

> « We keep q only when d occurs among the Top-K passages returned by the
> retriever. […] We show this filter substantially reduces the number of synthetic
> queries and significantly improves retrieval performance. » (§3.2)

Autrement dit : le critère de qualité d'une requête générée depuis un document
est, littéralement, **que le document soit retrouvable depuis elle**. Le filtre
est un test de retrouvabilité de cardinalité 1, appliqué par un retriever.

Deux conséquences, et elles tirent en sens opposés :

- **pour l'entraînement**, c'est légitime et ça marche ;
- **pour l'évaluation**, c'est circulaire par construction : le filtre conserve
  exactement les cas qu'un retriever réussit déjà, et écarte les cas durs. Une
  collection de test filtrée ainsi ne peut pas mesurer ce qu'elle a servi à
  sélectionner. Aucun des auteurs ne propose de l'utiliser pour évaluer.

### 1.4 RAGAS — sans référence, donc sans qrels

Es, James, Espinosa-Anke, Schockaert, *RAGAS: Automated Evaluation of Retrieval
Augmented Generation*, EACL 2024 (démo) — <https://arxiv.org/abs/2309.15217>.

RAGAS **n'est pas une collection de test** et ne produit aucun jugement de
pertinence réutilisable. C'est un jeu de trois métriques *reference-free*
calculées par LLM sur des triplets (question, contexte, réponse) :

- **faithfulness** — les affirmations de la réponse sont-elles étayées par le
  contexte ;
- **answer relevance** — on prompte le LLM pour **régénérer n questions à partir
  de la réponse**, puis on moyenne la similarité cosinus (embeddings
  `text-embedding-ada-002`) entre ces questions et la question d'origine ;
- **context relevance** — le contexte ramené est-il concentré.

Ce qu'il faut noter sur la validation : le jeu de validation **WikiEval** est
lui-même construit en mode document-d'abord — 50 pages Wikipédia postérieures à
2022, ChatGPT formule la question à partir de l'introduction, ChatGPT y répond.
Deux annotateurs jugent ensuite (accord ≈ 95 % sur faithfulness et context
relevance, ≈ 90 % sur answer relevance). Les auteurs rapportent que la *context
relevance* est « the hardest quality dimension to evaluate » et que ChatGPT
« often struggles with the task of selecting the sentences from the context that
are crucial, especially for longer contexts ».

Trois limites structurelles pour notre usage :

1. la métrique de récupération de RAGAS (*context relevance*) est celle que ses
   propres auteurs déclarent la moins fiable ;
2. RAGAS ne mesure **pas le rappel** : sans qrels, on ne sait pas ce qu'on a
   manqué. Pour un besoin recall-oriented — et le juridique l'est —
   c'est disqualifiant comme instrument unique ;
3. `answer relevance` est une auto-cohérence : question → réponse → question.
   Elle ne dit rien de l'utilité de la réponse.

### 1.5 La suite : collections de test entièrement synthétiques (2024–2025)

C'est la seule ligne de travaux qui revendique l'évaluation.

Rahmani, Craswell, Yilmaz, Mitra, Campos, *Synthetic Test Collections for
Retrieval Evaluation*, SIGIR 2024 — <https://arxiv.org/abs/2405.07767>,
code : <https://github.com/rahmanidashti/SyntheticTestCollections>.

Voir §3 : c'est la pièce centrale du dossier, et elle contredit partiellement
ADR-034.

Voir aussi SynDL (Rahmani et al., 2025), passage à l'échelle du même dispositif —
<https://www.microsoft.com/en-us/research/wp-content/uploads/2024/09/3701716.3715311.pdf>.

---

## 2. Les modes d'échec documentés

### 2.1 Hallucination — le document ne répond pas à la requête qu'il a engendrée

Gospodinov, MacAvaney, Macdonald, *Doc2Query--: When Less is More*, ECIR 2023 —
<https://arxiv.org/abs/2301.03266>,
DOI [10.1007/978-3-031-28238-6_31](https://doi.org/10.1007/978-3-031-28238-6_31).

> « sequence-to-sequence models are known to be prone to "hallucinating" content
> that is not present in the source text. We argue that Doc2Query is indeed prone
> to hallucination, which ultimately harms retrieval effectiveness and inflates
> the index size. »

Effet du filtrage par un modèle de pertinence : **+16 % d'efficacité**, −23 % de
temps d'exécution, −33 % de taille d'index. Le gain est celui du *retrait* de
requêtes générées. Le papier ne publie pas de taux d'hallucination global ; ce
qu'il établit, c'est qu'une part de la génération est nuisible et **détectable
par un modèle de pertinence indépendant du générateur**.

Le fait convergent d'InPars (90 % jeté, 4 points de MRR@10 perdus sans filtre) et
de Promptagator (« substantially reduces the number of synthetic queries ») dit la
même chose depuis trois angles : **la génération brute est majoritairement
inexploitable, et tout le monde filtre.**

### 2.2 L'expansion générative dégrade les systèmes forts

Weller, Chang, MacAvaney, Lo, Cohan, Van Durme, Lawrie, Soldaini, *When do
Generative Query and Document Expansions Fail? A Comprehensive Study Across
Methods, Retrievers, and Datasets*, EACL 2024 (Findings) —
<https://arxiv.org/abs/2309.08541>.

> « We find that there exists a strong negative correlation between retriever
> performance and gains from expansion: expansion improves scores for weaker
> models, but generally harms stronger models. »

Portée : 11 techniques d'expansion, 12 jeux de données, 24 modèles de
récupération. Explication proposée par les auteurs :

> « query and document expansions introduce new terms, potentially weakening the
> relevance signal of the original text » (RQ3)

et, sur les résultats en domaine :

> « after a certain score threshold these expansions generally hurt performance
> (as they blur the relevance signal from the original documents) »

Exception documentée : le *long query shift*, où l'expansion aide parce qu'elle
**raccourcit** la requête pour la rapprocher de la distribution d'entraînement des
modèles. Autrement dit, le gain observé vient d'un rapprochement vers la
distribution du modèle, pas d'un gain sémantique.

**Lecture pour Murphy** : le bénéfice d'un artefact génératif est
anticorrélé à la qualité du système. Un dispositif validé sur un retriever faible
n'est pas transportable vers un retriever fort. C'est un argument contre le fait
de figer un protocole de génération avant de savoir où se situe le système.

### 2.3 Les requêtes générées produisent des collections *plus faciles*

Rahmani et al., SIGIR 2024 (op. cit.), constat explicite :

> « systems consistently achieve higher performance on synthetic test collections
> when compared to real queries, suggesting that synthetic test collections tend
> to be easier. »

C'est la mesure la plus directe de l'écart requêtes générées / requêtes réelles
qu'on ait trouvée : **le niveau absolu est biaisé vers le haut**, même quand
l'ordre des systèmes est préservé (voir §3).

### 2.4 Les jugements générés, eux, sont franchement peu fiables

Toujours Rahmani et al. : accord GPT-4 / humain sur les jugements de pertinence
**κ de Cohen ≈ 0,24–0,26** (0,24 sur requêtes réelles, 0,26 sur requêtes
synthétiques), le modèle « consistently underestimates "Perfectly relevant" and
"Highly relevant" labels », et ne retrouve le label humain *Perfectly relevant*
que dans **28 %** des cas. Et le corollaire quantifié : utiliser des jugements
synthétiques **épars** fait s'effondrer l'accord d'ordonnancement des systèmes à
**τ = 0,157**.

### 2.5 Diversité : les requêtes générées ne couvrent pas la variété humaine

Alaofi, Gallagher, Sanderson, Scholer, Thomas, *Can Generative LLMs Create Query
Variants for Test Collections? An Exploratory Study*, SIGIR 2023 (short) —
DOI [10.1145/3539618.3591960](https://doi.org/10.1145/3539618.3591960),
préprint <https://arxiv.org/abs/2501.17981>.

Protocole notable : **besoin d'abord**. On donne à GPT-3.5 les 100 *backstories*
(descriptions de besoin) de la collection UQV100, et on compare ses variantes de
requêtes à celles produites par des humains sur les mêmes besoins. Les variantes
LLM ramènent des ensembles de documents proches (jusqu'à **71,1 % de recouvrement
à profondeur de pool 100**) mais les auteurs concluent qu'elles « may not fully
capture the wide variety of human-generated variants ».

À retenir : même en partant du besoin — donc sans aucun des défauts de la
dérivation descendante — le LLM **sous-couvre la variété d'expression humaine**.
Ce mode d'échec est indépendant du sens de dérivation, et il ne se corrige donc
pas en changeant de sens.

### 2.6 Le plafond de mesure (argument NIST)

Soboroff, *Don't Use LLMs to Make Relevance Judgments*, Information Retrieval
Research, 2025 (keynote LLM4Eval @ SIGIR 2024) —
<https://arxiv.org/abs/2409.15133>, notice NIST :
<https://www.nist.gov/publications/dont-use-llms-make-relevance-judgments>.

> « letting the LLM write your truth data handicaps the evaluation by setting that
> LLM as a ceiling on performance. There are ways to use LLMs in the relevance
> assessment process, but just generating relevance judgments with a prompt isn't
> one of them. »

Le *théorème du classement idéal* (§6 du papier) : quelle que soit la source de la
vérité terrain,

> « Whatever we use as the answer key represents both an ideal solution and a
> ceiling on measurable performance. No system can outperform the evaluation's
> answer key. »

et donc

> « We cannot measure a system that is better than the relevance judgments. »

avec le cas aggravant qui nous concerne :

> « the most advanced LLMs are used as components of systems that may be
> hypothetically measured by relevance judgments generated from the same models.
> Those systems cannot perform better than the model generating the relevance
> judgments. »

**Nuance importante et souvent perdue** : cet argument porte sur les **jugements**
(R dans le triplet C = {D, S, R}), pas sur les **besoins de recherche** (S).
Soboroff ne dit nulle part qu'une requête générée invalide une collection ; il dit
qu'une *clé de réponse* générée plafonne la mesure. Il concède explicitement qu'« il
y a des façons d'utiliser les LLM dans le processus d'évaluation de la
pertinence ». Un dispositif où le label est un **fait d'authoring** (le document
germe est la cible par construction, sans qu'aucun modèle ne prononce de jugement)
ne tombe pas sous cette critique — mais il tombe sous celle du §3.

---

## 3. Le constat d'ADR-034, éprouvé

> « Toute collection de test construite en dérivant les requêtes des documents
> mesure la *retrouvabilité*, pas l'*utilité* — c'est la raison pour laquelle la
> méthodologie TREC pose les *topics* d'abord et constitue les jugements ensuite
> par pooling. »

L'affirmation a deux moitiés. Elles ne tiennent pas également.

### 3.1 Ce qui est soutenu — la première moitié, à un terme près

**« Retrouvabilité » est un terme technique établi en RI, et il désigne bien
ceci.** Azzopardi & Vinay, *Retrievability: An Evaluation Measure for Higher Order
Information Access Tasks*, CIKM 2008, p. 561–570 —
DOI [10.1145/1458082.1458157](https://dl.acm.org/doi/10.1145/1458082.1458157).
La retrouvabilité est la facilité avec laquelle un document *peut* être ramené par
un système : plus il y a de requêtes qui le ramènent, et plus il est ramené haut,
plus il est retrouvable. La mesure est explicitement conçue comme
**indépendante des jugements de pertinence**, et présentée comme pertinente pour
les domaines *recall-oriented* — brevets et **droit** sont les deux exemples que
les auteurs citent. Elle se calcule justement sur un ensemble de requêtes
**simulées à partir de la collection**.

Le vocabulaire d'ADR-034 est donc correct, et pas seulement métaphorique : une
collection à requêtes dérivées des documents *est* un dispositif de mesure de
retrouvabilité au sens de la littérature.

**Et le filtre de qualité de Promptagator le confirme mécaniquement** : le
critère par lequel la communauté valide une requête générée depuis un document est
« la requête doit retrouver son passage source » (§1.3). Ce n'est pas une lecture
interprétative : c'est le critère opérationnel, écrit tel quel.

**Le mode d'échec est mesuré** : les collections synthétiques sont plus faciles
(§2.3) ; les germes tirés au hasard sont souvent des notes de bas de page, des
publicités et des passages multi-sujets qui n'appartiennent pas à l'ensemble des
passages réellement pertinents (§1.2, InPars). L'alternative rejetée d'ADR-034 sur
le tirage aléatoire des germes reçoit ici un appui empirique direct.

### 3.2 Ce qui est contredit — la seconde moitié, sur TREC

**La description de la méthodologie TREC est inexacte sur un point non
accessoire.** Source primaire, Voorhees & Harman, *Overview of TREC 2002*, NIST —
<https://trec.nist.gov/pubs/trec11/papers/OVERVIEW.11.pdf>, §2.1.2 :

> « TREC topic statements are created by the same person who performs the relevance
> assessments for that topic (the assessor). Usually, each assessor comes to NIST
> with ideas for topics based on his or her own interests, **and searches the
> document collection using NIST's PRISE system to estimate the likely number of
> relevant documents per candidate topic. The NIST TREC team selects the final set
> of topics from among these candidate topics based on the estimated number of
> relevant documents** and balancing the load across assessors. »

Ce que ça dit :

- l'*idée* du topic précède effectivement le corpus (elle vient des intérêts de
  l'assesseur) — ADR-034 a raison sur ce point ;
- mais **le jeu de topics retenu est conditionné par le corpus**. Un topic dont le
  corpus ne contient presque rien, ou beaucoup trop, est écarté. TREC ne pose donc
  pas les topics « d'abord » au sens strict : il pose des candidats, les confronte
  au corpus, et **filtre sur la retrouvabilité estimée**. La pratique est
  documentée et durable : dans le TREC NeuCLIR (Lawrie et al., *Overview of the
  TREC 2022 NeuCLIR Track*, <https://arxiv.org/abs/2304.12367>), les assesseurs
  examinent trente documents trouvés par recherche interactive pendant le
  développement du topic, et tout topic dépassant vingt documents pertinents est
  jugé « too productive » et écarté — motif explicite : la réutilisabilité de la
  collection.

Il y a donc une **boucle corpus → topics** dans TREC que l'ADR décrit comme
absente. Le pooling n'est pas non plus un choix de pureté méthodologique : c'est
une réponse à un problème de coût, énoncée comme telle par les mêmes auteurs —
juger 800 000 documents pour un seul topic prendrait plus de 6500 heures, donc
« TREC uses a technique called pooling to create a subset of the documents (the
"pool") to judge for a topic », et « Documents that are not in the pool are
assumed to be irrelevant to that topic ». Invoquer TREC comme *le* précédent d'une
séparation stricte besoin/corpus surinterprète la méthode.

### 3.3 Ce qui contredit frontalement — la mesure existe et elle est plutôt bonne

C'est le point qu'il faut regarder en face.

Rahmani, Craswell, Yilmaz, Mitra, Campos, *Synthetic Test Collections for
Retrieval Evaluation*, SIGIR 2024 — <https://arxiv.org/abs/2405.07767>.

Protocole : 1000 passages échantillonnés du corpus MS MARCO v2, filtrés en qualité
par GPT-4 (8,9 % de passages retirés, puis 14,6 % de plus sous le seuil 50) ;
requêtes générées **à partir de ces passages** par deux voies (modèle T5 BeIR de
génération de requêtes, et GPT-4 zero-shot) ; filtrage manuel par des experts (13
requêtes T5 sur 48 retenues, 18 GPT-4 sur 49) ; les 31 requêtes synthétiques
retenues sont **injectées dans la collection officielle du TREC Deep Learning
Track 2023** aux côtés des 51 requêtes réelles, et jugées par les assesseurs NIST
selon le protocole habituel (pooling à profondeur 10, échelle graduée à 4 niveaux).

Résultats, en τ de Kendall sur l'**ordre des systèmes** :

| Comparaison | τ |
|---|---|
| requêtes réelles vs requêtes **synthétiques** (jugements **humains**) | **0,8151** |
| requêtes réelles vs collection **entièrement synthétique** (requêtes + jugements) | **0,8568** |
| requêtes réelles vs jugements synthétiques **épars** | 0,157 |

Conclusion des auteurs :

> « By using fully synthetic test collections consisting of synthetically generated
> queries and judgments, it is possible to obtain evaluation results that are
> similar to evaluation results obtained using the traditional test collection
> approach. »

Et sur la crainte d'auto-favoritisme :

> « synthetic test collections based on GPT-4 do not systematically overestimate
> the performance of systems based on GPT. »

**Ce que ça contredit dans ADR-034** : le mot « **toute** ». Une collection dont
les requêtes sont dérivées des documents a ici classé les systèmes dans
essentiellement le même ordre qu'une collection à requêtes réelles. Si la seule
chose qu'un golden-set doit produire est un **classement comparatif** — « la
version B est-elle meilleure que la version A ? » — alors la dérivation
descendante n'invalide pas l'instrument, et l'affirmation « on ne mesure pas
l'utilité » est trop forte.

Réserves à porter au même compte, énoncées par les auteurs eux-mêmes :

- « our results are based on one test collection we have constructed and further
  experiments are needed to analyse potential biases » ;
- les niveaux absolus sont biaisés vers le haut (§2.3) ;
- **et surtout, le protocole comporte deux passages humains** : le filtrage expert
  des requêtes (≈ 27 % et ≈ 37 % de retenues, soit près de deux tiers écartés) et
  les jugements NIST. Le τ de 0,8151 est celui d'une collection à requêtes
  générées **et jugements humains**. Ce n'est pas une collection gratuite.

Second contre-exemple, sur la famille d'exception d'ADR-034 : He, Kim, Diaz,
Arguello, Mitra, *Tip of the Tongue Query Elicitation for Simulated Evaluation*,
SIGIR 2025 — <https://arxiv.org/abs/2502.17776>. Des requêtes *tip-of-the-tongue*
suscitées par LLM classent les systèmes de recherche du domaine « film » avec
τ = 0,7573 (MRR) et 0,7194 (nDCG) contre la référence issue de vraies questions de
forums — **au-dessus** des requêtes suscitées auprès d'humains recrutés
(τ = 0,6111 / 0,6438). Là où la tâche réelle est descendante, la simulation tient.
Cela conforte l'exception d'ADR-034 (`resolution_reference`,
`known_item_identifiant`) plutôt que de la contredire.

Contexte historique qui va dans le même sens, et qui est la référence ancienne du
sujet : Azzopardi, de Rijke, Balog, *Building simulated queries for known-item
topics: an analysis using six European languages*, SIGIR 2007, p. 455–462,
DOI [10.1145/1277741.1277820](https://doi.org/10.1145/1277741.1277820) — dont le
résumé pose le problème dans les termes exacts d'ADR-034 :

> « there are still many unaddressed issues regarding their usage and impact on
> evaluation because their quality, in terms of retrieval performance, is unlike
> real queries »

Donc : la communauté sait depuis 2006–2007 que les requêtes simulées ne se
comportent pas comme les vraies, et elle a passé vingt ans à **valider** des
simulateurs au lieu de les interdire. La ligne de validation est constituée
(voir aussi Breuer et al., *Validating Simulations of User Query Variants*, ECIR
2022 — <https://arxiv.org/abs/2201.07620>).

### 3.4 Verdict

L'affirmation d'ADR-034 est **partiellement corroborée, et plus forte que ce que
la littérature soutient.**

| Composante de l'affirmation | Statut |
|---|---|
| Le terme « retrouvabilité » désigne bien ce dispositif | **Corroboré** (Azzopardi & Vinay 2008) |
| Une collection à requêtes dérivées des documents est plus facile / biaisée en niveau | **Corroboré et mesuré** (Rahmani 2024) |
| Le critère de qualité des requêtes générées est un critère de retrouvabilité | **Corroboré textuellement** (Promptagator §3.2) |
| Les germes tirés au hasard produisent des questions non représentatives | **Corroboré** (InPars §6) |
| « **Toute** » telle collection ne mesure **pas** l'utilité | **Non soutenu**, contredit sur le classement des systèmes (τ ≈ 0,82–0,86, Rahmani 2024) |
| TREC pose les topics **d'abord**, indépendamment du corpus | **Inexact** — les topics sont filtrés sur le nombre estimé de documents pertinents (TREC 2002 §2.1.2, NeuCLIR 2022) |
| Le pooling est motivé par la séparation besoin/corpus | **Inexact** — il est motivé par le coût des jugements exhaustifs (TREC 2002 §2.1.3) |

Aucune source primaire trouvée n'énonce le constat d'ADR-034 sous cette forme
générale. **C'est une dérivation interne** — bien construite, alignée sur un
vocabulaire technique existant, appuyée par plusieurs faits convergents, mais dont
la portée universelle (« toute collection ») et la justification par TREC ne sont
pas dans la littérature. La justification par TREC est même partiellement fausse.

---

## 4. La pratique acceptée aujourd'hui

Position de la communauté RI, telle qu'elle ressort des sources primaires :

1. **Entraînement : accepté sans réserve.** InPars (SIGIR 2022), Promptagator
   (ICLR 2023), les *pseudo test collections* de Berendsen et al. (*Pseudo test
   collections for training and tuning microblog rankers*, SIGIR 2013,
   DOI [10.1145/2484028.2484063](https://dl.acm.org/doi/10.1145/2484028.2484063))
   sont tous positionnés comme du matériau d'entraînement/réglage. Le nom même de
   « pseudo test collection » marque la distance.

2. **Évaluation : accepté sous conditions nommées, depuis ~2024, et sans
   consensus.** Rahmani et al. (SIGIR 2024) montrent que c'est faisable, avec :
   filtrage qualité des passages germes, **filtrage expert des requêtes**,
   **jugements humains**, et validation de l'ordre des systèmes contre une
   collection de référence. Ils s'arrêtent à « encouraging » et demandent d'autres
   expériences.

3. **Jugements générés : position tranchée contre, du côté du NIST.** Soboroff
   (2025) : « don't use LLMs to create relevance judgments for TREC-style
   evaluations ». Le désaccord est ouvert dans la communauté (l'article est issu
   d'une keynote au workshop LLM4Eval de SIGIR 2024, précisément consacré à la
   question) — mais l'argument du plafond de mesure n'a pas de réfutation.

4. **Validation contre un référentiel réel : c'est la norme méthodologique.**
   Depuis Azzopardi et al. (2007) jusqu'à He et al. (2025), le geste attendu est
   toujours le même : montrer que la collection simulée **ordonne les systèmes
   comme** une référence réelle. Une collection synthétique non validée contre du
   réel n'a, dans cette littérature, aucun statut.

Il n'y a **pas** de position unique. Il y a un partage net entre *entraînement*
(consensus favorable) et *jugements* (opposition NIST argumentée), et une zone
grise active sur les *requêtes* d'évaluation, où la faisabilité est démontrée sur
un cas et l'exigence de validation est universelle.

---

## Ce que ça change pour Murphy

### Réponse frontale au point 3

**L'affirmation d'ADR-034 est plus forte que ce que la littérature soutient, et sa
justification par TREC est inexacte.**

Ce qui doit être corrigé dans l'ADR :

- **le quantificateur.** « Toute collection […] mesure la retrouvabilité, pas
  l'utilité » est réfuté par un résultat publié : Rahmani et al. (SIGIR 2024)
  obtiennent τ ≈ 0,82–0,86 sur l'ordre des systèmes entre une collection à
  requêtes dérivées des documents et le TREC DL 2023 réel. Si l'usage du
  golden-set est **comparatif** — comparer deux versions de Murphy — l'instrument
  descendant n'est pas disqualifié. La formulation défendable est : *une
  collection à requêtes dérivées des documents mesure la retrouvabilité ; son
  transfert vers l'utilité n'est pas garanti et doit être validé, pas postulé* ;
- **la référence à TREC.** TREC ne pose pas les topics indépendamment du corpus :
  les assesseurs recherchent la collection et les topics sont **retenus ou écartés
  sur le nombre estimé de documents pertinents** (Overview of TREC 2002, §2.1.2 ;
  seuil de 20 documents pertinents dans NeuCLIR 2022). Et le pooling est une
  réponse au coût des jugements exhaustifs (6500 h pour un topic), pas un principe
  de séparation besoin/corpus. Cette phrase de l'ADR doit être retirée ou
  reformulée : elle invoque comme précédent une méthode qui fait, à petite échelle,
  exactement ce qu'elle prétend proscrire.

Ce qui **survit intact**, et qu'il faut au contraire renforcer par les sources :

- le **vocabulaire** est juste : « retrouvabilité » est un concept RI établi
  (Azzopardi & Vinay, CIKM 2008), explicitement destiné aux domaines
  *recall-oriented* dont le droit fait partie ;
- le **rejet du tirage aléatoire des germes** reçoit un appui empirique direct
  d'InPars : les passages tirés au hasard sont souvent des notes de bas de page,
  des publicités et des passages multi-sujets qui n'appartiennent pas à l'ensemble
  des passages réellement pertinents ;
- la **famille d'exception** (`resolution_reference`, `known_item_identifiant`)
  est le cas le mieux soutenu du dossier : c'est le seul régime où la simulation
  est validée depuis vingt ans (Azzopardi & de Rijke 2006–2007) et où elle bat les
  requêtes suscitées auprès d'humains (He et al., SIGIR 2025, τ = 0,757 vs 0,611) ;
- le **capteur du §3 d'ADR-034** est exactement le geste que la littérature exige.
  Toute la ligne de validation des simulateurs consiste à comparer l'ordre produit
  par l'instrument simulé à celui d'une référence réelle. Le capteur de Murphy est
  cette validation, appliquée à un référentiel de panel plutôt qu'à une collection
  TREC. C'est le point le plus solide de l'ADR, et il ne dépend d'aucune des deux
  formulations à corriger.

### Les trois faits les plus conséquents pour la conception du golden-set

**1. Personne ne conserve la génération brute — le filtre humain n'est pas un
raffinement, c'est le dispositif.** InPars jette 90 % (100 k → 10 k) et perd 4
points de MRR@10 s'il ne filtre pas ; Doc2Query-- gagne 16 % en retirant des
requêtes ; Promptagator filtre par cohérence aller-retour ; Rahmani et al. ne
gardent que 13/48 et 18/49 requêtes après revue experte. Un protocole B-08 qui
génère N requêtes et en garde N est hors de toute pratique publiée. Le taux de
rejet attendu est de l'ordre de **60 à 90 %**, et il faut le budgéter comme tel :
le coût du golden-set n'est pas le coût de la génération, c'est le coût de la
sélection. Corollaire pour ADR-034 : le label descendant n'est jamais totalement
gratuit — il est gratuit *par cas retenu*, pas *par cas produit*.

**2. Le filtre de qualité standard est un test de retrouvabilité, donc il est
circulaire pour un usage d'évaluation.** Promptagator : « the query should
retrieve its source passage », on ne garde q que si d est dans le top-K du
retriever. Appliqué à un golden-set, ce filtre conserve précisément les cas que le
système réussit déjà et écarte les cas durs — ce qui produit un golden-set qui
« échoue en rassurant », le mode d'échec qu'ADR-034 §3 nomme. **Le filtrage des
requêtes de Murphy ne doit donc jamais passer par le retriever de Murphy.** Si un
filtre automatique est utilisé, il doit être un modèle indépendant du système
évalué (c'est le choix de Doc2Query--, qui filtre avec un modèle de pertinence
distinct), et le mieux reste la revue humaine.

**3. Le juridique est un domaine recall-oriented, et deux instruments du dossier
n'y mesurent pas ce qu'il faut.** RAGAS est *reference-free* : sans qrels, il ne
mesure aucun rappel — il ne peut pas dire ce qu'on a manqué, ce qui est
exactement la question en droit (Azzopardi & Vinay citent la recherche juridique
comme cas d'école du besoin de rappel). Et les jugements de pertinence générés par
LLM plafonnent la mesure au niveau du LLM (Soboroff, NIST 2025 : « we cannot
measure a system that is better than the relevance judgments »), avec un accord
mesuré à κ ≈ 0,25 seulement. Conséquence de conception : **le rappel de Murphy ne
peut pas être établi par un LLM juge ni par RAGAS.** Il exige des ensembles-réponse
de cardinalité > 1 constitués autrement — pooling humain sur les cas du panel, ou
labels structurels dérivés du corpus (citations, versions, renvois) qui ne
dépendent d'aucun jugement de modèle.

*Fait mineur mais opérationnel* : l'efficacité des artefacts génératifs est
**anticorrélée** à la force du système (Weller et al., EACL 2024). Un protocole
calibré sur le système d'aujourd'hui ne se transporte pas au système de demain —
argument supplémentaire pour la suite restreinte et re-dérivable
qu'ADR-034 retient en conséquence, plutôt qu'un gros investissement d'authoring
figé.

---

## Sources

**Méthodes**

- Nogueira, Yang, Lin, Cho — *Document Expansion by Query Prediction*, arXiv:1904.08375, 2019. <https://arxiv.org/abs/1904.08375>
- Nogueira, Lin — *From doc2query to docTTTTTquery*, rapport technique, 2019. <https://cs.uwaterloo.ca/~jimmylin/publications/Nogueira_Lin_2019_docTTTTTquery-v2.pdf> — code : <https://github.com/castorini/docTTTTTquery>
- Bonifacio, Abonizio, Fadaee, Nogueira — *InPars: Unsupervised Dataset Generation for Information Retrieval*, SIGIR 2022. <https://arxiv.org/abs/2202.05144> · [10.1145/3477495.3531863](https://dl.acm.org/doi/10.1145/3477495.3531863)
- Dai, Zhao, Ma, Luan, Ni, Lu, Bakalov, Guu, Hall, Chang — *Promptagator: Few-shot Dense Retrieval From 8 Examples*, ICLR 2023. <https://arxiv.org/abs/2209.11755>
- Es, James, Espinosa-Anke, Schockaert — *RAGAS: Automated Evaluation of Retrieval Augmented Generation*, EACL 2024 (demo). <https://arxiv.org/abs/2309.15217>
- Berendsen, Tsagkias, Weerkamp, de Rijke — *Pseudo test collections for training and tuning microblog rankers*, SIGIR 2013. [10.1145/2484028.2484063](https://dl.acm.org/doi/10.1145/2484028.2484063)

**Modes d'échec**

- Gospodinov, MacAvaney, Macdonald — *Doc2Query--: When Less is More*, ECIR 2023. <https://arxiv.org/abs/2301.03266> · [10.1007/978-3-031-28238-6_31](https://doi.org/10.1007/978-3-031-28238-6_31)
- Weller, Chang, MacAvaney, Lo, Cohan, Van Durme, Lawrie, Soldaini — *When do Generative Query and Document Expansions Fail?*, EACL 2024 Findings. <https://arxiv.org/abs/2309.08541>
- Alaofi, Gallagher, Sanderson, Scholer, Thomas — *Can Generative LLMs Create Query Variants for Test Collections? An Exploratory Study*, SIGIR 2023. [10.1145/3539618.3591960](https://doi.org/10.1145/3539618.3591960) · <https://arxiv.org/abs/2501.17981>
- Soboroff — *Don't Use LLMs to Make Relevance Judgments*, Information Retrieval Research, 2025 (NIST). <https://arxiv.org/abs/2409.15133> · <https://www.nist.gov/publications/dont-use-llms-make-relevance-judgments>

**Collections synthétiques et validation**

- Rahmani, Craswell, Yilmaz, Mitra, Campos — *Synthetic Test Collections for Retrieval Evaluation*, SIGIR 2024. <https://arxiv.org/abs/2405.07767> · <https://github.com/rahmanidashti/SyntheticTestCollections>
- Rahmani et al. — *SynDL: A Large-Scale Synthetic Test Collection for Passage Retrieval*, 2025. <https://www.microsoft.com/en-us/research/wp-content/uploads/2024/09/3701716.3715311.pdf>
- He, Kim, Diaz, Arguello, Mitra — *Tip of the Tongue Query Elicitation for Simulated Evaluation*, SIGIR 2025. <https://arxiv.org/abs/2502.17776>
- Azzopardi, de Rijke — *Automatic construction of known-item finding test beds*, SIGIR 2006, p. 603–604.
- Azzopardi, de Rijke, Balog — *Building simulated queries for known-item topics: an analysis using six European languages*, SIGIR 2007, p. 455–462. [10.1145/1277741.1277820](https://doi.org/10.1145/1277741.1277820)
- Breuer, Fuhr, Schaer — *Validating Simulations of User Query Variants*, ECIR 2022. <https://arxiv.org/abs/2201.07620>

**Méthodologie TREC et retrouvabilité**

- Voorhees, Harman — *Overview of TREC 2002*, NIST. <https://trec.nist.gov/pubs/trec11/papers/OVERVIEW.11.pdf> (§2.1.2 création des topics, §2.1.3 pooling)
- Lawrie et al. — *Overview of the TREC 2022 NeuCLIR Track*. <https://arxiv.org/abs/2304.12367> (développement des topics, seuil de 20 documents pertinents)
- Azzopardi, Vinay — *Retrievability: An Evaluation Measure for Higher Order Information Access Tasks*, CIKM 2008, p. 561–570. [10.1145/1458082.1458157](https://dl.acm.org/doi/10.1145/1458082.1458157)
