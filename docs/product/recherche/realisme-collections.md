# Comment les collections de RI achètent leur réalisme — et à quel prix

**Statut** : note de recherche. Ne décide rien, ne modifie aucun ADR. Rapporte des
faits sourcés et chiffrés, pour instruire le dimensionnement de N_j (GOLDEN-SET §7.4)
et le risque pesant sur B-10.

**Ticket** : [#8](https://github.com/left-eyebr0w/murphy/issues/8) (part of #1)
**Date** : 1er août 2026
**Périmètre des sources** : *overview papers* TREC/NIST, actes SIGIR/CIKM/CLEF/FIRE,
papiers d'origine des collections (MS MARCO, ORCAS, NQ, COLIEE, AILA, BEIR),
littérature sur la puissance statistique en RI (Webber/Moffat/Zobel, Sakai, Urbano).
Aucune source secondaire n'est utilisée pour établir un chiffre ; quand un chiffre
n'a pu être lu que rapporté par un tiers primaire, c'est signalé.

---

## 0. Ce que la note établit, en une page

1. **TREC n'achète pas du réalisme, il achète de la *jugeabilité*.** Les topics ne
   viennent pas d'utilisateurs : ils sont écrits par l'assesseur lui-même, et le
   critère de sélection publié est le *nombre estimé de documents pertinents*
   (§1). Le réalisme des besoins n'est jamais revendiqué.
2. **Les collections à requêtes réelles (MS MARCO, ORCAS, NQ) paient le réalisme
   par la profondeur de jugement.** MS MARCO passage : 1,06 passage pertinent par
   requête d'entraînement (§2.1). L'arbitrage a été *mesuré* par TREC Deep
   Learning : le classement des systèmes sous labels épars s'accorde avec le
   classement sous labels NIST profonds à τ = 0,68–0,82 seulement (§2.2).
3. **Les collections de domaine à experts rares ne réduisent pas le nombre de
   requêtes ; elles réduisent la profondeur, ou bien elles suppriment le jugement
   humain.** Deux stratégies distinctes coexistent : payer des experts pour des
   pools peu profonds à budget fixe (TREC-COVID, CLEF eHealth), ou dériver les
   labels de la citation et renoncer au jugement (COLIEE, AILA) — cette seconde
   voie étant explicitement justifiée par le coût (§3).
4. **Oui, il existe des collections publiées, réutilisées, avec moins de
   50 requêtes** — Touché-2020 (49), TREC-NEWS (57), TREC Deep Learning (43),
   TREC Legal Interactive (7). Aucune ne prétend à la puissance statistique ;
   elles sont soit agrégées à d'autres, soit lues comme diagnostic (§4).
5. **La dérivation `n ≈ 7,85 / d²` est formellement correcte mais son entrée
   `d ≈ 0,35` est optimiste d'un facteur ≈ 2,5 en effectif.** La littérature
   publiée place l'effet typiquement recherché autour de `d ≈ 0,22`, ce qui donne
   ~150–165 requêtes, pas 60–70 (§5).

---

## 1. TREC — d'où viennent les topics, et ce qu'ils coûtent

### 1.1 Qui écrit les topics

La source canonique est l'*overview* annuel de NIST. Voorhees, *Overview of TREC
2004*, TREC-13 proceedings, NIST, 2004 —
<https://trec.nist.gov/pubs/trec13/papers/OVERVIEW13.pdf>, §2.1.2 :

> « TREC topic statements are created by the same person who performs the
> relevance assessments for that topic (the assessor). Usually, each assessor
> comes to NIST with ideas for topics based on his or her own interests, and
> searches the document collection using NIST's PRISE system to estimate the
> likely number of relevant documents per candidate topic. The NIST TREC team
> selects the final set of topics from among these candidate topics based on the
> estimated number of relevant documents and balancing the load across
> assessors. »

Trois faits s'en déduisent, et ils sont décisifs pour Murphy :

- **le topic n'est pas un besoin d'utilisateur observé.** Il est l'intérêt propre
  d'un assesseur NIST, formulé par écrit avant tout jugement ;
- **le topic est filtré sur la faisabilité du jugement**, pas sur la
  représentativité. Le critère explicite de sélection est le nombre estimé de
  documents pertinents ;
- **l'auteur du topic est le juge du topic.** Il n'y a pas de séparation entre
  celui qui exprime le besoin et celui qui décide de la pertinence — ce qui
  supprime par construction le coût d'alignement entre les deux, mais interdit de
  parler de « besoin réel ».

Cette conclusion recoupe celle déjà établie par la recherche du ticket #6 : la
justification de B-08 par TREC (« TREC prouve que des requêtes fabriquées
suffisent ») porte sur un dispositif qui ne revendique pas le réalisme.

### 1.2 Combien de topics, combien de jugements

Le standard historique est **50 topics par piste ad hoc**. Le seul chiffre de
*profondeur* publié systématiquement est la taille des pools.

- **Robust 2004** (Voorhees, *Overview of the TREC 2004 Robust Retrieval Track*,
  TREC-13, NIST — <https://trec.nist.gov/pubs/trec13/papers/ROBUST.OVERVIEW.pdf>) :
  jeu de 250 topics (249 exploitables), dont 50 nouveaux. Pour les nouveaux :
  pools construits à partir de trois runs par groupe, profondeur 100, et
  **« an average of 704 documents judged for each new topic »**. Les 200 anciens
  topics ne reçoivent aucun jugement nouveau ; en repoolant, NIST constate que
  **70,8 % en moyenne** (min 36,6 %, max 93,7 %) des documents des nouveaux pools
  étaient déjà jugés.
- **TREC 2019 Deep Learning** (Craswell, Mitra, Yilmaz, Campos, Voorhees,
  *Overview of the TREC 2019 Deep Learning Track*, arXiv 2003.07820 —
  <https://arxiv.org/abs/2003.07820>), §5 : 200 requêtes de test diffusées, mais
  **43 seulement retenues** « based on budget constraints ». Document ranking :
  20 157 documents jugés, 16 258 retenus au qrels final → **≈ 378 jugements par
  topic**. Passage ranking : 11 904 jugés, 9 260 retenus → **≈ 215 par topic**.

### 1.3 Le coût publié

TREC ne publie pas de coût monétaire. Il publie un **coût-temps unitaire**, dans
le même *overview* 2004 (§2.1.3) :

> « with 800,000 documents, it would take over 6500 hours to judge the entire
> document set for one topic, assuming each document could be judged in just
> 30 seconds »

C'est l'ancre de référence : **30 secondes par jugement**. Appliquée à Robust 2004,
704 documents × 50 nouveaux topics ≈ 35 200 jugements ≈ **293 heures-assesseur**
pour 50 topics, soit ≈ 6 heures par topic.

C'est aussi le seul chiffre dont Murphy a réellement besoin : à 30 s le jugement,
un budget d'annotation solo se convertit directement en profondeur.

---

## 2. Les collections à requêtes réelles — le réalisme est acquis, la profondeur est vendue

### 2.1 MS MARCO — la contrepartie est écrite noir sur blanc

Nguyen, Rosenberg, Song, Gao, Tiwary, Majumder, Deng, *MS MARCO: A Human Generated
MAchine Reading COmprehension Dataset*, arXiv 1611.09268, 2016 —
<https://arxiv.org/abs/1611.09268>.

Provenance : « we begin by sampling queries from Bing's search logs. We filter out
any non-question queries from this set. » 1 010 916 questions. Le réalisme est
donc **gratuit et total** : ce sont des requêtes réellement tapées.

La contrepartie est déclarée par les auteurs eux-mêmes, §3.1 :

> « To identify the relevant passages, we use the `is_selected` annotation
> provided by the editors. As the editors were not required to annotate every
> passage that were retrieved for the question, **this annotation should be
> considered as incomplete** — i.e., there are likely passages in the collection
> that contain the answer to a question but have not been annotated as
> `is_selected: 1`. »

Le mécanisme exact de l'arbitrage : l'éditeur humain ne juge pas pour évaluer, il
juge **pour rédiger une réponse**. Le label « pertinent » n'est qu'un sous-produit
de la tâche de rédaction — il marque le passage *utilisé*, pas les passages
*utilisables*. C'est le cas d'école du « label gratuit » : gratuit parce que
parasitaire d'une autre tâche, et incomplet pour la même raison.

Le chiffre de profondeur est lisible dans la Table 1 de l'*overview* TREC DL 2019
(source citée §1.2) : passage ranking, 502 940 requêtes d'entraînement pour
532 761 qrels → **1,06 passage pertinent par requête**. Les mêmes auteurs le
qualifient explicitement (§3) : « These are sparse, with no negative labels and
often only one positive label per query ».

### 2.2 La conséquence mesurée de la faible profondeur

C'est le point le plus utile de tout le dossier, parce qu'il chiffre l'arbitrage
plutôt que de le déplorer. TREC DL 2019 possède, sur les mêmes 43 requêtes, deux
jeux de qrels : les labels épars MS MARCO et les labels NIST profonds. Les auteurs
comparent les classements de systèmes obtenus avec chacun (Figures 7 et 8) :

| Tâche | τ(RR épars MS MARCO, RR NIST) | τ(RR épars, nDCG@10 NIST) | τ(RR NIST, nDCG@10 NIST) |
|---|---|---|---|
| Document ranking | 0,68 | 0,69 | 0,73 |
| Passage ranking | 0,82 | 0,68 | 0,77 |

Lecture : passer de qrels profondes à des qrels à un seul positif par requête
**dégrade le classement des systèmes jusqu'à τ ≈ 0,68**. À comparer au τ ≈ 0,82–0,86
que le ticket #6 a relevé pour la dérivation descendante des requêtes (Rahmani et
al., SIGIR 2024) : *l'incomplétude des jugements abîme le classement au moins
autant que l'artificialité des requêtes.*

Les organisateurs tranchent d'ailleurs en faveur des jugements profonds :

> « if there is any disagreement we believe the NDCG results are more valid, since
> they evaluate the ranking more comprehensively and a ranker that can only
> perform well on labels with exactly the same distribution as the training set is
> not robust enough for use in real-world applications »

### 2.3 ORCAS — le réalisme poussé à sa limite : plus aucun humain

Craswell, Campos, Mitra, Yilmaz, Billerbeck, *ORCAS: 18 Million Clicked
Query-Document Pairs for Analyzing Search*, arXiv 2006.05324, 2020 —
<https://arxiv.org/abs/2006.05324>.

- **10 405 342 requêtes**, **18 823 602 paires requête-document** positives
  (≈ 1,81 par requête), dérivées d'un sous-échantillon de 26 mois de logs Bing.
- **Zéro jugement humain.** Le signal est le clic, filtré des clics à *dwell time*
  court.
- Le prix payé est double, et les auteurs l'exposent :
  - **filtre de k-anonymat** — « keeping only queries that were typed by k
    different users, for a high value of k ». Conséquence directe : la longue
    traîne, c'est-à-dire précisément les requêtes rares et difficiles, est
    éliminée par construction ;
  - **pas de rangs, pas de négatifs, pas de correction du biais de position** —
    « ORCAS does not provide the rankings of clicked and unclicked URLs that users
    saw ». Sans les non-cliqués, aucune profondeur de jugement n'est
    reconstructible.
- Les auteurs notent enfin que les requêtes ORCAS et TREC DL « have somewhat
  different characteristics » (longueur, mots interrogatifs initiaux : 3,5 % de
  « what » contre 39,4 %) — le réalisme brut et le réalisme *filtré pour une
  tâche* ne sont pas la même population.

### 2.4 Natural Questions — le réalisme de la requête, pas celui de la recherche

Kwiatkowski et al., *Natural Questions: a Benchmark for Question Answering
Research*, TACL 7, 2019 — <https://aclanthology.org/Q19-1026/>.

- Requêtes : « real anonymized, aggregated queries issued to the Google search
  engine ».
- Volumétrie : **307 373** exemples d'entraînement en annotation **simple**,
  **7 830** de développement et **7 842** de test en annotation **5-way**, plus
  **302** exemples en **25-way** pour étudier la variabilité humaine.
- Coût déclaré : « a pool of around 50 annotators, with an average annotation time
  of **80 seconds** ».
- **La contrepartie structurelle**, souvent oubliée : « An annotator is presented
  with a question along with a Wikipedia page **from the top 5 search results** ».
  L'annotateur ne cherche pas dans le corpus — il lit une page déjà retrouvée par
  Google. NQ n'est donc pas une collection de RI *ad hoc* : le rappel n'y est pas
  définissable, et ses labels ne bornent rien sur ce qui n'a pas été présenté.

**Conclusion de la section.** Les trois collections achètent le réalisme au même
guichet : le label est un sous-produit d'une activité qui n'est pas le jugement de
pertinence (rédiger une réponse, cliquer, lire une page fournie). Le réalisme est
gratuit ; la profondeur ne l'est jamais.

---

## 3. Domaines spécialisés à experts rares — le comparable le plus proche

Deux stratégies, radicalement différentes, coexistent. Il faut les nommer
séparément car elles n'ont pas le même statut épistémique.

### 3.A — Payer les experts, et rationner la profondeur

#### 3.A.1 TREC-COVID

Roberts, Alam, Bedrick, Demner-Fushman, Lo, Soboroff, Voorhees, Wang, Hersh,
*Searching for scientific evidence in a pandemic: An overview of TREC-COVID*,
Journal of Biomedical Informatics 121, 2021 — arXiv 2104.09632 —
<https://arxiv.org/abs/2104.09632>. Complété par Voorhees et al., *TREC-COVID:
Constructing a Pandemic Information Retrieval Test Collection*, SIGIR Forum 54(1),
2020 — arXiv 2005.04474 — <https://arxiv.org/abs/2005.04474>.

Chiffres publiés :

- **50 topics** au terme du dispositif (30 au *round* 1, +5 par *round*, 5 rounds),
  écrits **par les organisateurs** ayant une formation biomédicale, « inspired by
  consumer questions submitted to the National Library of Medicine, discussions by
  medical influencers on social media, and suggestions solicited on Twitter via
  the #COVIDSearch tag ». Là encore : les topics ne viennent pas d'utilisateurs
  observés, mais d'organisateurs qui *modélisent* des utilisateurs à partir de
  traces publiques.
- **69 318 jugements manuels cumulés** → **≈ 1 386 jugements par topic**.
- **Équipe d'annotation** : 17 indexeurs MeSH de la NLM (« up to 100 articles per
  week » chacun), 10 étudiants en médecine d'OHSU, et **40 personnes recrutées**
  (« All were required to have a medical degree or an appropriate biomedical
  science degree ») financées par AI2, jusqu'à 1 000 articles chacune. Soit
  **≈ 67 annotateurs experts**.
- **Débit** : « It is assumed an assessor can judge 50 articles for a topic in one
  hour ». 69 318 jugements ≈ **1 386 heures-assesseur**, soit ≈ 0,8 année-personne
  à temps plein, étalées sur **avril–juillet 2020**.
- **Profondeur par round, très faible** : au *round* 1, « only one of the maximum
  of three runs per team was a judged run and **λ=7** ». Les organisateurs
  écrivent eux-mêmes : « With only about 300 documents judged per topic in a given
  round, the relevance judgments for that round are incomplete to the point that
  run comparisons are likely unstable for many measures. »
- **Réponse méthodologique à l'incomplétude** : concentrer sur Bpref, nDCG@10 et
  P@5 — « Bpref was designed for collections with incomplete judgments […] P@5 and
  NDCG@10 are each affected by only the most highly ranked documents ». Et, en
  conclusion : « When the number of unjudged is skewed, it is best to take
  precautions such as using incompleteness-tolerant measures or **requiring larger
  differences in scores before concluding that runs are actually different**. »

Cette dernière phrase est la jonction exacte entre le ticket #7 (incomplétude) et
le point 5 de celui-ci : **l'incomplétude ne se paie pas seulement en biais, elle
se paie en seuil de détection relevé**, donc en effectif requis.

#### 3.A.2 CLEF eHealth

Zuccon, Palotti, Goeuriot, Kelly, Lupu, Pecina, Mueller, Budaher, Deacon, *The IR
Task at the CLEF eHealth Evaluation Lab 2016: User-centred Health Information
Retrieval*, CLEF 2016 Working Notes, CEUR-WS Vol-1609 —
<https://ceur-ws.org/Vol-1609/16090015.pdf>.

- **50 scénarios de recherche × 6 variantes de requête = 300 requêtes**. Les
  scénarios sont issus de posts réels de forums de santé (« mining health web
  forums »), donc de besoins réellement exprimés — mais reformulés par des tiers.
- **Budget d'annotation fixé *ex ante*, pas la profondeur** : « A Pool of
  **25 000 documents** was created using the RBP-based Method A (Summing
  contributions) by Moffat et al. […] This strategy was chosen because it was
  shown that it should be preferred over traditional fixed-depth or stratified
  pooling when deciding upon the pooling strategy to be used to evaluate systems
  **under fixed assessment budget constraints** ». Soit **≈ 500 jugements par
  scénario**, ≈ 83 par requête.
- **Annotateurs** : « paid final year medical students who had access to queries,
  documents, and relevance criteria drafted by a junior medical doctor ». Le
  critère de pertinence est rédigé par un médecin ; le jugement est délégué à des
  étudiants payés.
- Jugements gradués (Highly / Somewhat / Not relevant), plus deux dimensions
  supplémentaires (compréhensibilité, fiabilité) sur curseur 0–100.

**Ce que CLEF eHealth démontre et qui est directement transposable** : quand le
budget est la contrainte première, on ne fixe pas la profondeur, on fixe le
**budget total** et on laisse une règle de pondération (ici RBP) décider où les
jugements vont. C'est exactement l'instrument que le ticket #7 identifiait comme
seul calculable en solo.

#### 3.A.3 TREC Legal Track (voie interactive)

Hedin, Tomlinson, Baron, Oard, *Overview of the TREC 2009 Legal Track*, TREC-18,
NIST — <https://trec.nist.gov/pubs/trec18/papers/LEGAL09.OVERVIEW.pdf>.

C'est le dispositif juridique le plus coûteux jamais publié, et il vaut surtout
comme borne haute.

- **7 topics seulement** (tâche interactive, collection Enron de 847 791
  documents). Sur toute l'histoire de la piste (2006–2009) : « relevance judgments
  for a total of **109 richly structured topics** » sur la collection de documents
  scannés.
- **Un « Topic Authority » par topic**, avocat en exercice nommément identifié
  (Wachtell Lipton, Squire Sanders, Pillsbury, Paul Weiss…), qui *définit* la
  pertinence : « it is the Topic Authority who […] is to be the source » de la
  cible. Chaque équipe participante dispose de « up to **10 hours** of a Topic
  Authority's time for purposes of clarifying a topic ».
- **Jugement en deux étages, sur échantillon stratifié** (pas de pooling) :
  premier passage par des cabinets de revue documentaire professionnels (3 topics)
  ou par **48 volontaires** — « primarily law students, but also practicing
  attorneys and other legal professionals » (4 topics) ; puis phase d'**appel** où
  les équipes contestent les jugements devant le Topic Authority, qui tranche
  définitivement.
- **Volumétrie** : « a total of 100 bins were reviewed; these bins, collectively,
  contained **49 285 documents** » → **≈ 7 040 jugements par topic**, l'ordre de
  grandeur le plus profond de toute cette note.
- **Le fait le plus instructif pour Murphy** : le taux de succès des appels. « No
  set of appeals had a success rate lower than **0,7** and ten had a success rate
  greater than **0,9**. » Autrement dit, quand une équipe conteste un jugement de
  premier passage rendu par un juriste ou un étudiant en droit, **elle obtient
  gain de cause 7 à 9 fois sur 10** devant l'autorité de référence. L'annotation
  juridique de premier niveau est massivement faillible ; ce n'est pas une opinion,
  c'est un taux publié.

### 3.B — Ne pas payer les experts : dériver le label de la citation

#### 3.B.1 COLIEE

Goebel, Kano, Kim, Rabelo, Satoh, Yoshioka, *Overview of Benchmark Datasets and
Methods for the Legal Information Extraction/Entailment Competition (COLIEE)
2024* — <https://coliee.org/documents/waivers/overview_COLIEE2024.pdf>.

- Tâche 1 (*Case Law Retrieval*), édition 2024 : **400 requêtes de test**,
  1 734 documents candidats, **1 562 cas « noticed » au total → 3,90 par requête**.
  Entraînement : 1 278 requêtes, ≈ 4,16 par requête.
- **Le label n'est pas un jugement** : « `noticed(si, q)` denotes a relationship
  which is true when `si` is a noticed case with respect to `q` », c'est-à-dire un
  cas **cité** par la décision-requête. Aucun expert ne juge quoi que ce soit ; la
  vérité-terrain est extraite du texte des décisions.
- Les organisateurs sont conscients de la fuite et la colmatent : « To prevent
  competitors from merely using existing embedded conventional legal citations in
  historical cases to identify cited cases, citations are suppressed from all
  candidate cases and replaced by a `FRAGMENT_SUPPRESSED` tag ».
- **La requête n'est pas une requête** : c'est une décision de justice entière.
  Il n'y a pas d'utilisateur, pas de besoin d'information formulé, pas de question.

#### 3.B.2 AILA (FIRE)

Bhattacharya, Ghosh, Ghosh, Pal, Mehta, Bhattacharya, Majumder, *Overview of the
FIRE 2019 AILA Track: Artificial Intelligence for Legal Assistance*, CEUR-WS
Vol-2517 — <https://ceur-ws.org/Vol-2517/T1-1.pdf>.

- **50 requêtes** (10 fournies en entraînement, **évaluation sur 40**), 2 914
  documents de jurisprudence de la Cour suprême de l'Inde, 197 articles de loi.
- **Fabrication des requêtes, descendante et assumée** : 50 décisions sont tirées
  au sort ; leurs *faits* sont extraits manuellement puis anonymisés (noms
  remplacés par « P », lieux par « L », dates et mentions d'articles supprimées).
- **Labels = citations** : « the gold standard results consisted of prior cases
  […] and statutes […] that were **actually cited by the lawyers arguing those
  cases** ».
- **La justification du choix est publiée textuellement** — c'est la citation la
  plus directement pertinente de tout ce dossier :

  > « We followed this automated methodology in creating the dataset, since
  > **actually involving legal experts** (e.g., to find relevant prior cases /
  > statutes) **would have required a significant amount of financial resources
  > and time**. »

  Les auteurs qualifient malgré tout leur gold standard de « curated by law
  experts » au motif que les citations ont été posées par les avocats plaidants.
  C'est un glissement : le juriste a cité ce qui servait son argumentation, il n'a
  pas jugé la pertinence d'un corpus au regard d'un besoin. **AILA est le
  précédent exact du raisonnement qu'ADR-029 a écarté chez Murphy** — et il est
  utile de constater qu'une piste d'évaluation publiée l'a assumé, faute de
  budget, tout en le déclarant.

---

## 4. Les petites collections — moins de 50 requêtes, ça existe

### 4.1 L'inventaire

Thakur, Reimers, Rücklé, Srivastava, Gurevych, *BEIR: A Heterogeneous Benchmark
for Zero-shot Evaluation of Information Retrieval Models*, NeurIPS 2021 Datasets &
Benchmarks — arXiv 2104.08663 — <https://arxiv.org/abs/2104.08663>, Table 1.
BEIR agrège 18 collections publiées et réutilisées ; plusieurs sont minuscules :

| Collection BEIR | Requêtes de test | Docs pertinents / requête (Avg. D/Q) |
|---|---|---|
| Touché-2020 | **49** | 19,0 |
| TREC-NEWS | **57** | 19,6 |
| Signal-1M (RT) | 97 | 19,6 |
| TREC-COVID | 50 | 493,5 |
| SciFact | 300 | 1,1 |
| NFCorpus | 323 | 38,2 |
| Robust04 | 249 | 69,9 |

À quoi s'ajoutent, hors BEIR : **TREC Deep Learning 2019** (43 requêtes jugées, §1.2)
et **TREC Legal Interactive 2009** (7 topics, §3.A.3).

Réponse au point 4 : **oui, sans ambiguïté**. Des collections de 43 à 57 requêtes
sont publiées, réutilisées pendant des années, et servent de socle à des
publications SIGIR/NeurIPS.

### 4.2 Comment elles gèrent la puissance — trois réponses, dont deux honnêtes

1. **L'agrégation.** C'est la recommandation explicite de Webber, Moffat, Zobel,
   *Statistical Power in Retrieval Experimentation*, CIKM 2008 —
   <https://doi.org/10.1145/1458082.1458158>, PDF auteur :
   <http://www.williamwebber.com/research/papers/wmz08_cikm.pdf> :

   > « the 50-topic TREC collections are distinctly unpromising from a
   > power-analysis point of view […] The experimenter should therefore
   > **aggregate as many such collections together as possible to boost test
   > power**, as has been done with the Robust test collection. »

   C'est précisément ce que fait BEIR : aucune de ses 18 collections n'est
   présentée comme suffisante isolément ; le score BEIR est une moyenne sur
   18 jeux.

2. **Le renoncement au test, au profit du diagnostic.** TREC-COVID *round* 1 et
   TREC Legal Interactive ne prétendent pas départager statistiquement deux
   systèmes proches ; ils produisent des jugements réutilisables et des constats
   qualitatifs.

3. **Le sous-ensemble « bien choisi » — et pourquoi il ne marche pas.** Guiver,
   Mizzaro, Robertson, *A Few Good Topics: Experiments in Topic Set Reduction for
   Retrieval Evaluation*, TOIS 27(4), 2009 —
   <https://doi.org/10.1145/1629096.1629099>, ont montré qu'il **existe** des
   sous-ensembles de très petite taille qui reproduisent le classement complet.
   Les travaux de suivi (Robertson, *On the Contributions of Topics to System
   Evaluation*, ECIR 2011 ; Berto, Mizzaro, Robertson, ICTIR 2013), synthétisés
   avec leurs propres extensions par Roitero, *Cheap IR Evaluation: Fewer Topics,
   No Relevance Judgements, and Crowdsourced Assessments*, thèse de doctorat,
   Università di Udine, 2020 — arXiv 2011.00479 —
   <https://arxiv.org/abs/2011.00479>, concluent que ces sous-ensembles ne sont
   **pas identifiables a priori** : « choosing a good topic subset is not just a
   matter of selecting good individual topics », et les critères de sélection
   praticables (hubness, clustering, aléatoire) ne battent pas le tirage aléatoire
   de manière fiable. **Le petit jeu performant existe, mais on ne peut pas le
   construire ; on ne peut que le reconnaître après coup.**

---

## 5. Tableau comparatif — le livrable central

Toutes les valeurs sont issues des sources citées ci-dessus. « Profondeur » =
nombre de documents **jugés** par requête (et non nombre de pertinents), quand
c'est publié ; sinon nombre de pertinents par requête, signalé par *(pert.)*.

| Collection | Requêtes (jugées) | Profondeur de jugement | Provenance des requêtes | Annotation : qui, combien, combien de temps |
|---|---|---|---|---|
| **TREC ad hoc / Robust 2004** | 249 (dont 50 nouvelles) | **704 docs/topic** (pools depth-100, 3 runs/groupe) | Écrites par l'assesseur NIST lui-même, filtrées sur le nb estimé de pertinents | Assesseurs NIST (ex-analystes) ; auteur du topic = juge du topic ; **30 s/document** (ancre NIST) ≈ 6 h/topic |
| **TREC DL 2019 — document** | **43** (sur 200 diffusées) | **≈ 378 docs/topic** (16 258 qrels) | Logs Bing (MS MARCO), présélectionnées ; 43 retenues « based on budget constraints » | Assesseurs NIST + HiCAL (sélection active) ; budget = critère de coupe explicite |
| **TREC DL 2019 — passage** | **43** | **≈ 215 passages/topic** (9 260 qrels) | idem | idem |
| **MS MARCO passage (train)** | 502 940 | **1,06 pertinent/requête** *(pert.)*, qrels déclarées incomplètes | **Logs Bing réels** (requêtes interrogatives filtrées) | Éditeurs rédigeant une réponse ; le label est un sous-produit — coût non publié |
| **ORCAS** | 10 405 342 | **1,81 positif/requête** *(pert.)*, aucun négatif, aucun rang | **Logs de clic Bing** (26 mois), filtre k-anonymat | **Aucun annotateur humain.** Coût ≈ 0, longue traîne éliminée |
| **Natural Questions** | 307 373 (1-way) + 7 830 dev / 7 842 test (**5-way**) + 302 (**25-way**) | 1 page Wikipédia du **top-5 Google** par question (pas de rappel sur corpus) | **Requêtes Google réelles** | ≈ **50 annotateurs**, **80 s/annotation** |
| **TREC-COVID (complet)** | **50** | **≈ 1 386 jugements/topic** (69 318 au total) ; **λ=7** au round 1, ≈ 300/topic/round | Écrites par les organisateurs biomédicaux, d'après questions NLM + réseaux sociaux | **≈ 67 experts** (17 indexeurs MeSH NLM, 10 étudiants en médecine OHSU, 40 recrutés MD/PhD financés AI2) ; **50 articles/h** → **≈ 1 386 h**, sur 4 mois |
| **CLEF eHealth 2016 (IR)** | **300** (= 50 scénarios × 6 variantes) | **≈ 83 docs/requête** (≈ 500/scénario) — **budget fixé à 25 000 jugements**, répartis par pondération RBP | Posts réels de forums de santé, reformulés | Étudiants en médecine de dernière année **payés** ; critères rédigés par un jeune médecin |
| **TREC Legal 2009 (interactive)** | **7** (109 topics cumulés sur la piste) | **≈ 7 040 docs/topic** (49 285 jugés) — échantillonnage stratifié + appel | Requêtes de production issues d'une plainte fictive rédigée pour l'exercice | **1 avocat « Topic Authority » par topic** (10 h/équipe) + cabinets de revue pro + **48 volontaires juristes** ; **taux de succès des appels 0,7–0,9+** |
| **COLIEE 2024 — Task 1** | **400** (test) | **3,90 cas « noticed »/requête** *(pert.)*, aucun jugement de non-pertinence | La « requête » est **une décision de justice entière** | **Aucune.** Label = citation extraite du texte ; citations masquées dans les candidats |
| **AILA 2019 — Task 1** | **50** (40 évaluées) | citations effectives *(pert.)*, corpus de 2 914 décisions | Faits extraits **manuellement** de 50 arrêts puis anonymisés | **Aucune.** Justification publiée : recourir à des experts « would have required a significant amount of financial resources and time » |
| **Touché-2020 / TREC-NEWS** (via BEIR) | **49 / 57** | 19,0 / 19,6 pertinents/requête *(pert.)* | topics de piste TREC/CLEF | n.p. — utilisées **agrégées** dans BEIR, jamais seules |

### Lecture transversale du tableau

- **Aucune collection n'obtient à la fois des requêtes réelles et des jugements
  profonds.** Les deux colonnes « provenance » et « profondeur » sont en
  opposition mécanique dans toutes les lignes. C'est la confirmation empirique la
  plus large qu'on puisse donner au constat d'ADR-034.
- **Le domaine spécialisé ne réduit pas le nombre de requêtes : il éclate en deux
  régimes.** Soit on paie (TREC-COVID : 67 experts, 1 386 h pour 50 topics ;
  TREC Legal : 7 topics et des avocats), soit on ne juge pas du tout (COLIEE,
  AILA). Il n'existe pas de troisième voie publiée où un petit nombre
  d'annotateurs produirait des qrels profondes sur beaucoup de requêtes.
- **La profondeur du domaine spécialisé n'est pas basse.** C'est une erreur de
  lecture fréquente : TREC-COVID atteint 1 386 jugements/topic, TREC Legal 7 040.
  Ce qui est bas, c'est la profondeur **par round**, sous contrainte de délai
  (λ=7). L'incomplétude y est un phénomène de *calendrier*, pas de doctrine.
- **Le budget, quand il est la contrainte, se fixe en jugements totaux et non en
  profondeur par requête** (CLEF eHealth : 25 000, alloués par contribution RBP).
  C'est la seule construction du corpus qui soit directement transposable à un
  budget d'annotation solo.

---

## 6. Point 5 — la puissance statistique en pratique, et le verdict sur `n ≈ 7,85 / d²`

### 6.1 La formule est correcte

Pour un test apparié (t de Student sur les différences par requête), la taille
nécessaire pour détecter un effet standardisé `d = δ/σ_D` avec α bilatéral et
puissance 1−β est :

```
n ≈ (z_{1−α/2} + z_{1−β})² / d²
```

À α = 5 % et puissance 80 % : `(1,96 + 0,8416)² = 7,849`. Donc `n ≈ 7,85/d²`.
**La dérivation de GOLDEN-SET §7.4 est formellement juste** — c'est la formule
classique de Cohen, appliquée correctement au cas apparié. Elle sous-estime
marginalement (l'approximation normale ignore que `t` a des degrés de liberté
finis ; l'usage est d'ajouter ~2), mais ce n'est pas là que se trouve le problème.

### 6.2 Le problème est l'entrée `d`, et la littérature le chiffre

Le seul travail publié qui calibre `d` sur des données TREC réelles est Webber,
Moffat, Zobel, CIKM 2008 (référence complète §4.2). Leurs résultats :

**(a) La variabilité des deltas par topic.** Table 1 du papier, écart-type des
différences de score AP entre systèmes, par collection :

| Jeu de test | σ moyen | σ au 95ᵉ centile | δ détectable à 50 topics (σ moyen) | δ détectable (σ 95ᵉ) |
|---|---|---|---|---|
| TREC-3 AdHoc | 0,144 | 0,198 | 0,058 | 0,080 |
| TREC-6 AdHoc | 0,196 | 0,259 | 0,079 | 0,105 |
| TREC-8 AdHoc | 0,160 | 0,226 | 0,065 | 0,091 |
| TREC 2005 TB | 0,142 | 0,191 | 0,057 | 0,077 |
| **Moyenne** | **0,157** | — | **0,064** | — |

> « These suggest that the standard 50 topic TREC collection can only be relied on
> to detect true AP deltas in the range **0,06–0,08**. »

**(b) L'effet qu'on cherche réellement à détecter.** C'est ici que tout se joue.
Webber et al. posent la question dans les termes du praticien :

> « A reasonable figure for trying to improve upon an established baseline is the
> size of the difference between the mean of the second quartile system AP scores
> and the mean of the first quartile, which for the test set is **0,033**. To have
> power 0.8 given σ = 0,15 on δ = 0,033 requires **164 topics**. One notes
> immediately that the traditional 50-topic TREC collection is inadequate to
> reliably detect such a true difference. That is, **an experiment should contain
> at least 150 topics if a typical top-quartile system is to be reliably
> distinguished from a typical second-quartile baseline**. »

Traduit en effet standardisé : `d = 0,033 / 0,15 = 0,22`. Et `7,85 / 0,22² = 162`,
ce qui reproduit leur 164 à l'arrondi près. **La formule interne et la littérature
disent exactement la même chose ; elles ne sont pas alimentées par le même `d`.**

**(c) Le verdict.** `d = 0,35` correspond, à σ = 0,157 (moyenne Webber), à un écart
absolu `δ = 0,055` — soit **1,7 fois** l'écart typique entre un système du premier
quartile et un du deuxième quartile TREC, et un peu au-dessus du seuil que Webber
et al. décrivent comme la limite d'un jeu de 50 topics. Autrement dit :

> **Un jeu de 60–70 requêtes ne départage pas « deux configurations de
> récupération », il départage une configuration nettement meilleure d'une
> configuration nettement moins bonne.** Pour l'usage annoncé de B-10 — comparer
> deux variantes proches d'un même pipeline — l'effectif conforme à la pratique
> publiée est de l'ordre de **150–165 requêtes jugées**, soit un facteur ≈ 2,5.

La dérivation est donc **optimiste**, non par erreur de calcul, mais par choix
d'un effet cible plus grand que celui que la littérature considère comme
l'amélioration typique à détecter.

### 6.3 Quatre aggravations, toutes publiées

Chacune pousse dans le même sens : il en faut plus, pas moins.

**(i) Estimer σ à l'avance coûte cher.** Webber et al., §5.1 : « In each case, the
95th percentile standard deviation is 25 % to 40 % more than the mean, leading
under Equation 2 to **60 % to 100 % more topics** than in the mean case ». Se
fonder sur un σ moyen revient à accepter ≈ 50 % de chances de rater la puissance
visée. Se prémunir double l'effectif.

**(ii) Il n'existe pas *un* σ.** « there is no single population of AP score
deltas, and therefore no single σ » : chaque paire de systèmes a sa propre
population de deltas. Un `d` posé a priori est donc une hypothèse, pas une mesure.

**(iii) L'itération (« j'ajoute des requêtes jusqu'à ce que ce soit
significatif ») est biaisée.** Webber et al., §5.3, démontrent empiriquement que
cette procédure — la plus naturelle en solo — « leads to a bias in favour of
finding both power and significance ». Si Murphy juge par lots successifs jusqu'à
obtenir un résultat, le résultat est surestimé. Les auteurs exigent, si l'on
procède ainsi, une déclaration explicite de la méthodologie.

**(iv) Une métrique à coupe courte augmente la variance, donc l'effectif.** Sakai,
*Topic Set Size Design with Variance Estimates from Two-Way ANOVA*, EVIA 2014 —
<https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings11/pdf/EVIA/01-EVIA2014-SakaiT.pdf>.
Ses tables de dimensionnement (ANOVA, α = 0,05, β = 0,20, `minD` = écart absolu
minimal détectable, `m` = nombre de systèmes comparés), tâche adhoc/news :

| Profondeur de mesure | minD | n requis (AP / Q / nDCG / nERR), m = 10 |
|---|---|---|
| md = 1000 | 0,10 | **166 / 168 / 176 / 377** |
| md = 1000 | 0,20 | 42 / 43 / 45 / 95 |
| md = 1000 | 0,25 | 27 / 28 / 29 / 61 |
| **md = 10** | 0,10 | **725 / 557 / 631 / 1 026** *(m = 100)* |

Sakai commente : « a typical TREC adhoc/news test collection with n = 50 topics is
good enough for guaranteeing a minimum detectable range of **0,20** » — pas 0,10.
Et surtout : « **As reducing md causes higher variances […] this also means we
need more topics.** » Murphy évalue au nDCG@10, donc à `md` court : c'est le
régime **le plus** coûteux en requêtes, pas le moins.

Sakai note enfin que les estimateurs de variance par ANOVA sont « substantially
larger than the 95 %-percentile method » de Webber et al., et recommande, avec
Ellis, d'« err on the side of over-sampling ».

**(v) Aucun test ne rattrape un manque de puissance.** Urbano, Lima, Hanjalic,
*Statistical Significance Testing in Information Retrieval: An Empirical Analysis
of Type I, Type II and Type III Errors*, SIGIR 2019 — arXiv 1905.11096 —
<https://arxiv.org/abs/1905.11096>. Plus de 500 millions de p-values simulées, à
n = 25, 50, 100 topics. Conclusions utiles ici :

- « all tests except the sign test behave very similarly, with very small
  differences in practice. […] it seems clear that they [le t-test et le test de
  permutation] are the best choice » — le choix du test de permutation annoncé par
  GOLDEN-SET §7.4 est le bon, mais **il n'achète pas de puissance** ;
- les erreurs de **type III** (conclure dans le mauvais sens après un rejet
  correct) « are not negligible » et diminuent avec la taille d'échantillon — un
  petit `n` ne produit pas seulement des non-conclusions, il produit des
  conclusions inversées ;
- « differences in P@10 or RR have between 2 and 4 times the standard deviation of
  the other measures » — la métrique choisie change l'effectif d'un facteur 4 à 16
  (σ² au dénominateur).

### 6.4 Ce qui, à l'inverse, plaide *pour* un petit jeu

L'honnêteté exige de nommer ce qui va dans l'autre sens.

- **Peu profond et large bat profond et étroit, à budget d'annotation constant.**
  C'est le résultat le plus directement actionnable de Webber et al., §6. À budget
  fixe de ~5 000 jugements : « This many judgments represent **33 topics at
  depth 100, 161 topics at depth 20, and 617 topics at depth 5** », et la
  proportion d'effets réellement détectables est de **0 % à profondeur 100, 23 % à
  profondeur 20, et 56 % à profondeur 5**. Conclusion des auteurs : « **shallow
  evaluation of many topics is preferable to deep evaluation of a few** ». Le seul
  contre-argument qu'ils retiennent est la **réutilisabilité** : « the deeper the
  initial assessment, the less likely it is that new systems will return
  unassessed documents […] In a private lab, however, it might be more efficient
  to perform shallow assessments initially, then optionally perform supplementary
  assessments when new documents are returned at high ranks ». **Murphy est
  exactement ce « private lab ».**
- **Le classement des systèmes est plus robuste que le test.** Le ticket #6 a
  établi τ ≈ 0,82–0,86 pour la dérivation descendante ; §2.2 ci-dessus montre
  τ = 0,68–0,82 pour l'appauvrissement des qrels. **Ordonner n'exige pas la
  puissance qu'exige trancher.** Si B-10 se contente de dire « la configuration A
  est devant B », un petit jeu peut suffire ; si B-10 doit dire « A est
  significativement meilleure que B », il ne suffit pas.
- **Sakai valide 50 topics — pour minD = 0,20.** Un jeu de 45–50 requêtes est
  publiquement défendable si, et seulement si, l'écart visé est déclaré comme
  grossier (≈ 0,20 absolu en nDCG). Ce qui n'est pas défendable est d'annoncer
  60–70 requêtes **et** un effet « modéré ».

### 6.5 Réponse frontale

**La dérivation `n ≈ 7,85 / d²` est conforme à la pratique publiée ; l'effectif de
60–70 qu'on en tire ne l'est pas.**

Trois formulations équivalentes du même verdict :

1. **En effectif** : pour l'effet que Webber, Moffat et Zobel identifient comme
   l'amélioration typiquement recherchée (d ≈ 0,22), il faut **~165 requêtes
   jugées**. 60–70 est optimiste d'un facteur ≈ 2,5.
2. **En effet détectable** : avec 60–70 requêtes appariées, Murphy détecte
   `d ≈ 0,34`, soit — à σ ≈ 0,157 — un écart absolu de **~0,053** en AP/nDCG.
   C'est un grand écart, du même ordre que la limite d'un jeu TREC de 50 topics
   (0,06–0,08). Ce n'est pas un « effet modéré » au sens de la pratique RI.
3. **En risque projet** : à 60–70, un B-10 qui ne conclut pas ne prouvera rien, et
   un B-10 qui conclut aura une probabilité non négligeable de conclure dans le
   mauvais sens (Urbano et al. sur les erreurs de type III à petit n).

Aggravations propres à Murphy, toutes documentées ci-dessus : coupe courte
(nDCG@10 → variance plus élevée, Sakai) ; qrels incomplètes (→ « requiring larger
differences in scores before concluding », TREC-COVID) ; jugement solo, donc
tentation de l'ajout itératif de requêtes jusqu'à significativité (biais démontré
par Webber et al.).

**Les trois issues empruntées par d'autres, par ordre de transposabilité :**

| Issue | Précédent | Ce qu'elle coûte à Murphy |
|---|---|---|
| **Élargir en peu profond** — plus de requêtes, jugées à profondeur 5–20 plutôt que 60–70 à profondeur 100 | Webber et al. §6 (33@100 < 161@20 < 617@5) ; TREC-COVID λ=7 ; CLEF eHealth budget-RBP | Réutilisabilité dégradée ; à compenser par jugements supplémentaires au fil des runs, ce que GOLDEN-SET §7.5 prévoit déjà |
| **Fixer un budget total, pas une profondeur** — allouer les jugements par contribution RBP | CLEF eHealth 2016 : 25 000 jugements alloués par pondération RBP | Rien, méthodologiquement ; c'est déjà l'instrument identifié par le ticket #7 |
| **Renoncer au test et déclarer un ordre** — B-10 produit un classement borné (résidus RBP) plutôt qu'un p | TREC-COVID rounds 1–4 ; TREC Legal Interactive | La carte B-10 doit être requalifiée : « départager » devient « ordonner sous incertitude bornée » |

**Ce qui n'est pas une issue** : choisir a posteriori un sous-ensemble de requêtes
qui donne le bon résultat. Guiver et al. (TOIS 2009) montrent que de tels
sous-ensembles existent ; Robertson (2011), Berto et al. (2013) et Roitero (2020)
montrent qu'ils ne sont **pas identifiables a priori** par aucun critère
praticable.

---

## 7. Sources

**TREC / NIST**

- Voorhees, *Overview of TREC 2004*, TREC-13, NIST, 2004 —
  <https://trec.nist.gov/pubs/trec13/papers/OVERVIEW13.pdf>
- Voorhees, *Overview of the TREC 2004 Robust Retrieval Track*, TREC-13, NIST,
  2004 — <https://trec.nist.gov/pubs/trec13/papers/ROBUST.OVERVIEW.pdf>
- Craswell, Mitra, Yilmaz, Campos, Voorhees, *Overview of the TREC 2019 Deep
  Learning Track*, arXiv 2003.07820, 2020 — <https://arxiv.org/abs/2003.07820>
- Hedin, Tomlinson, Baron, Oard, *Overview of the TREC 2009 Legal Track*, TREC-18,
  NIST, 2009 — <https://trec.nist.gov/pubs/trec18/papers/LEGAL09.OVERVIEW.pdf>
- Voorhees, Alam, Bedrick, Demner-Fushman, Hersh, Lo, Roberts, Soboroff, Wang,
  *TREC-COVID: Constructing a Pandemic Information Retrieval Test Collection*,
  SIGIR Forum 54(1), 2020 — arXiv 2005.04474 — <https://arxiv.org/abs/2005.04474>
- Roberts, Alam, Bedrick, Demner-Fushman, Lo, Soboroff, Voorhees, Wang, Hersh,
  *Searching for scientific evidence in a pandemic: An overview of TREC-COVID*,
  J. Biomed. Inform. 121, 2021 — arXiv 2104.09632 —
  <https://arxiv.org/abs/2104.09632>

**Collections à requêtes réelles**

- Nguyen et al., *MS MARCO: A Human Generated MAchine Reading COmprehension
  Dataset*, arXiv 1611.09268, 2016 — <https://arxiv.org/abs/1611.09268>
- Craswell, Campos, Mitra, Yilmaz, Billerbeck, *ORCAS: 18 Million Clicked
  Query-Document Pairs for Analyzing Search*, arXiv 2006.05324, 2020 —
  <https://arxiv.org/abs/2006.05324>
- Kwiatkowski et al., *Natural Questions: a Benchmark for Question Answering
  Research*, TACL 7, 2019 — <https://aclanthology.org/Q19-1026/>

**Domaine spécialisé**

- Zuccon, Palotti, Goeuriot, Kelly, Lupu, Pecina, Mueller, Budaher, Deacon, *The
  IR Task at the CLEF eHealth Evaluation Lab 2016*, CEUR-WS Vol-1609 —
  <https://ceur-ws.org/Vol-1609/16090015.pdf>
- Goebel, Kano, Kim, Rabelo, Satoh, Yoshioka, *Overview of Benchmark Datasets and
  Methods for the Legal Information Extraction/Entailment Competition (COLIEE)
  2024* — <https://coliee.org/documents/waivers/overview_COLIEE2024.pdf>
- Bhattacharya, Ghosh, Ghosh, Pal, Mehta, Bhattacharya, Majumder, *Overview of the
  FIRE 2019 AILA Track*, CEUR-WS Vol-2517 — <https://ceur-ws.org/Vol-2517/T1-1.pdf>

**Petites collections**

- Thakur, Reimers, Rücklé, Srivastava, Gurevych, *BEIR: A Heterogeneous Benchmark
  for Zero-shot Evaluation of Information Retrieval Models*, NeurIPS 2021 D&B —
  arXiv 2104.08663 — <https://arxiv.org/abs/2104.08663>
- Guiver, Mizzaro, Robertson, *A Few Good Topics: Experiments in Topic Set
  Reduction for Retrieval Evaluation*, TOIS 27(4), 2009 —
  <https://doi.org/10.1145/1629096.1629099>
- Roitero, *Cheap IR Evaluation: Fewer Topics, No Relevance Judgements, and
  Crowdsourced Assessments*, thèse, Università di Udine, 2020 — arXiv 2011.00479 —
  <https://arxiv.org/abs/2011.00479> (synthétise Robertson ECIR 2011 et Berto,
  Mizzaro, Robertson ICTIR 2013)

**Puissance statistique**

- Webber, Moffat, Zobel, *Statistical Power in Retrieval Experimentation*, CIKM
  2008 — <https://doi.org/10.1145/1458082.1458158> ; PDF auteur :
  <http://www.williamwebber.com/research/papers/wmz08_cikm.pdf>
- Sakai, *Topic Set Size Design with Variance Estimates from Two-Way ANOVA*, EVIA
  2014 —
  <https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings11/pdf/EVIA/01-EVIA2014-SakaiT.pdf>
  (reprend et corrige Sakai, *Topic Set Size Design*, Information Retrieval
  Journal 19(3), 2016)
- Sakai, *Statistical Reform in Information Retrieval?*, SIGIR Forum 48(1), 2014 —
  <https://sigir.org/files/forum/2014J/2014J_sigirforum_Article_TetsuyaSakai.pdf>
- Urbano, Lima, Hanjalic, *Statistical Significance Testing in Information
  Retrieval: An Empirical Analysis of Type I, Type II and Type III Errors*, SIGIR
  2019 — arXiv 1905.11096 — <https://arxiv.org/abs/1905.11096>
- Voorhees, Buckley, *The Effect of Topic Set Size on Retrieval Experiment Error*,
  SIGIR 2002, p. 316–323 — <https://doi.org/10.1145/564376.564432>. **Non consulté
  en texte intégral** : cité ici uniquement pour sa méthode (taux d'erreur par
  taille de jeu et par écart observé), telle que décrite par Webber et al. (2008,
  §2). Aucun chiffre n'en est repris.

---

## 8. Ce que cette note ne dit pas

- Elle ne décide pas de N_j. Elle établit que 60–70 n'est pas justifiable par
  l'argument de puissance tel qu'il est écrit, et donne les trois issues publiées.
- Elle ne mesure rien sur le corpus de Murphy. Les σ cités sont ceux d'AP sur des
  collections TREC de presse et de web ; le σ du corpus juridique français est
  inconnu et ne peut être estimé qu'après un premier lot de jugements.
- Elle ne traite pas du biais de pool, instruit par le ticket #7, ni de la
  dérivation des requêtes, instruite par le ticket #6. Les trois notes se lisent
  ensemble.
