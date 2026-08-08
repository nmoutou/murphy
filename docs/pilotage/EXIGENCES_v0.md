# EXIGENCES v0 — Cahier des charges interne de la version en cours

> Spécification d'exigences **dérivée mécaniquement** des critères
> d'entrée/sortie v0 de `VERSIONS.md` et de la DoD du
> `CADRAGE_evaluation` (étendue jurisprudence). Audience : le porteur
> du programme. Ce document ne crée **aucun périmètre nouveau** : si
> une exigence ici contredit `VERSIONS.md`, c'est `VERSIONS.md` qui
> fait foi et le présent document qui se corrige.
>
> Format : exigence testable — *le système/programme doit… — vérifié
> par…* Chaque exigence porte un ID stable, référencé par le
> `BACKLOG.md`. Statuts au 19 juillet 2026, alignés `STATUS.md`.

## 1. Périmètre

**In** : socle data (LEGI + 5 bases jurisprudence, vague 1) ; harnais
d'évaluation (strates 1–3, ADR-017) ; baseline chiffrée reproductible.
**Out** (exclusions fermes v0) : applicatif web, experts, bases DILA
non jurisprudentielles, LLM générateur branché à l'évaluation.

> ⚠️ **Tour du 2 août 2026 — ADR-035 (paradigme TREC Legal Track).** Le périmètre
> ci-dessus **ne change pas** : les experts restent hors v0, et la fusion du golden-set
> v1 avec la collection experte v2 a été **explicitement rejetée** pour ne pas rendre la
> sortie de v0 otage d'un recrutement. Ce qui change est le **critère d'acceptation** :
> toute exigence de la famille **E-P2** doit désormais satisfaire « **rien à jeter** » —
> ce qu'elle fixe doit survivre au passage au golden-set v2 (expert, poolé, calibré —
> alpha ph.2) puis à l'ouverture aux runs externes, **sans redesign**. Corollaire : ce
> qui, dans les exigences ci-dessous, dérive d'une **rareté du jugement traitée comme
> permanente** — et non comme la condition actuelle — est rouvert par la carte
> [#1](https://github.com/left-eyebr0w/murphy/issues/1). Concerne principalement les
> chiffres de dimensionnement d'**E-P2-07** (plancher, composition v1) et le statut de
> métrique primaire d'**E-P2-02**. *(Mise à jour du 2 août 2026 :
> [#14](https://github.com/left-eyebr0w/murphy/issues/14) est **clos** — `nDCG@R` est
> retiré, `F1@K` est clos par le négatif, et **E-P2-02 est réécrite** ci-dessous.)*

> **Régime de vérification** (colonne Régime, ADR-028) : **auto** =
> question mécanique, oracle déterministe · **assisté** = la machine
> produit un candidat, l'humain tranche · **humain** = jugement
> sémantique irréductible (porteur v0, experts alpha/beta). Une exigence
> *humaine* ou *assistée* n'est jamais close par un simple « test
> vert » : sa clôture consigne qui a validé et quand.

## 2. Exigences P1 — Data

| ID | Exigence | Vérification | Source | Régime | Statut |
|---|---|---|---|---|---|
| E-P1-01 | Les 5 bases de jurisprudence (CASS, INCA, CAPP, JADE, CONSTIT) doivent être ingérées dans les trois BDD | Comptages d'ingestion archivés, cohérents entre sources DILA et bases cibles | ADR-002, ADR-003 | auto | ✅ |
| E-P1-02 | Chaque décision de jurisprudence doit porter une identité canonique (ECLI primaire, ID DILA en partition, numéro métier en fallback) **cohérente entre MongoDB, Neo4j et Qdrant** | Script de vérification croisée sur les 3 BDD : 0 divergence d'identité sur un échantillon exhaustif ; rapport versionné | ADR-018 | assisté | ✅ |
| E-P1-03 | LEGI doit exposer un `doc_id` stable au niveau article, invariant entre ré-ingestions | Test de ré-ingestion : diff des `doc_id` vide sur corpus témoin | ADR-004 | auto | ✅ |
| E-P1-04 | Le graphe Neo4j doit modéliser les citations entre décisions avec des relations typées, exploitables comme source de qrels | Requête Cypher extrayant les paires (décision citante, décision citée) ; volumétrie archivée | ADR-017 (strate 2) | assisté | ✅ |

## 3. Exigences P2 — Évaluation

| ID | Exigence | Vérification | Source | Régime | Statut |
|---|---|---|---|---|---|
| E-P2-01 | Un adapter baseline doit interroger la configuration de récupération courante et produire des runs au format arrêté | Run produit de bout en bout sur le golden-set v1, conforme au schéma ADR-008 | ADR-008, ADR-016 | auto | ⬜ |
| E-P2-02 | ⚠️ **Réécrite le 2 août 2026** ([#14](https://github.com/left-eyebr0w/murphy/issues/14) clos) — *rédaction antérieure : « le scorer doit calculer **nDCG@R** (métrique primaire) et les diagnostics MAP, R-Precision, Recall@2R, Doc-MRR, Doc-Recall@R ». **`nDCG@R` est retiré**, et avec lui MAP, R-Precision, Recall@2R et Doc-Recall@R — tous normalisés par `R` ou coupés à un multiple de `R`. `Doc-MRR` survit comme **lecture** de `Recall@R` à `R = 1`, non comme métrique.* **Le scorer doit calculer `RBP(p) + résidu`** comme grandeur de comparaison, le résidu **trou par trou sur le run** (jamais depuis une profondeur nominale), ⚠️ **corrigé le 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19), ADR-007 §4 réécrit — *rédaction antérieure : « `p` obtenu par la **règle** `p = 0,01^(1/d̄)` »*, **retirée** : elle faisait dériver le modèle de lecteur de l'effort d'annotation, ce qui épinglait le résidu de queue à 1 % quelle que soit la profondeur) — **`p` de décision déclaré *ex ante* depuis le lecteur** (`RETRIEVAL_TOP_K = 5` ⇒ `p = 0,80`) et **publié avec tout score**, plus la **famille sentinelle `0,50 / 0,80 / 0,95` publiée entière et sans seuil** ; `d_min = 200` ; plus les lectures de rapport par branche (`Recall@R` tout-ou-rien sur ensemble clos, précision seule sur `R = 0`) et les indicateurs de trous `RankUnj` / `%jugés@k`. **Il doit refuser de publier** un score dont le top-`k` est majoritairement non jugé, et refuser un test apparié dont l'intervalle d'écart contient zéro | Tests unitaires du scorer contre valeurs de référence calculées indépendamment (cas jouets vérifiables à la main), **résidu inclus** ; et un test que les deux refus se déclenchent | [ADR-007](../product/ADR/ADR-007-metrique-rbp-residu.md) | auto | ⬜ **rouverte** — la part livrée en B-04 qui survit est l'agrégation (E-P2-03), l'oracle auto-pur et le gain injectable ; le scorer lui-même est à refaire. *Requalification de B-04 non tranchée — décision de pilotage.* |
| E-P2-03 | L'agrégation chunk→document doit suivre la règle arrêtée, appliquée identiquement au scoring et aux runs | Test unitaire d'agrégation ; aucune métrique calculée au niveau chunk | ADR-006 | auto | ✅ |
| E-P2-04 | Les invariants structurels (strate 1) doivent être vérifiables sans annotation | Suite de tests strate 1 exécutable en CI, verte sur la baseline | ADR-017 | auto | ✅ |
| E-P2-05 | Un jeu de **paires de co-citation** (strate 2) doit être miné depuis le graphe de citations, à usage **diagnostique précision-seulement** (non des qrels scorables) | Jeu de paires versionné, volumétrie et méthode (requête Cypher) documentées ; **mesure la précision sur liens connus, jamais le rappel ni un grade** ; hypothèse *citation ≈ pertinence* **rétrogradée** — non un jugement de pertinence (ADR-029, prolonge ADR-028) | ADR-017, ADR-029 | assisté | ✅ |
| E-P2-06 | ⛔ **PÉRIMÉE SUR LE MOT « FIGÉ » — 2 août 2026** ([#18](https://github.com/left-eyebr0w/murphy/issues/18) §0). **`gel` est sorti du vocabulaire** : il ne garantissait la validité de rien, et exigeait de savoir d'avance ce qui mérite d'être scellé. L'exigence **survit en changeant d'objet** — non plus *figer*, mais **identifier** : le golden-set porte **trois hashes** (`corpus` sur les identités canoniques de document donc **stable sous `W`** · `cas` · `qrels`), consignés dans chaque artefact de run ; deux runs sont comparables **ssi** leurs hashes sont égaux, et une **version de collection** est un triplet **nommé** et publié (un nom, jamais un hash). Le « hash de gel » ci-dessous se lit « hash d'identification », et **il y en a trois, pas un**. S'ajoute le champ **`narrative`** (#18 §5) et une **cinquième contrainte de rédaction** au guide : *la largeur autorisée d'un cas est une sortie du protocole de pooling, pas une variable libre*. **Une sixième s'ajoute le 5 août 2026** ([#15](https://github.com/left-eyebr0w/murphy/issues/15)) : *la cible d'un cas **hors périmètre** doit être **lexicalement voisine** du corpus* — droit francophone étranger (belge, suisse, québécois), doctrine et commentaire de droit français, actes privés, sentences arbitrales. Elle n'est pas de confort : #15 re-fonde le mécanisme sur le **périmètre DILA** et lui retire donc la cible non ingérée mais lexicalement proche, qui était le cas **dur** ; sans cette contrainte, la permanence du label s'achète en payant le **pouvoir discriminant** qu'E-P2-07 exige. **Une septième s'ajoute le 7 août 2026** ([#13](https://github.com/left-eyebr0w/murphy/issues/13)) : *le besoin s'écrit dans les mots de celui qui l'a, jamais dans ceux de la norme qui y répond* — ce n'est pas un conseil de style mais **la forme écrite de « besoin d'abord »**, sans laquelle `concept_vers_instance` cesse d'acheter le réalisme qui seul justifie sa présence en v1. **Une huitième s'ajoute le 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) : ***q1 doit être rédigée pour converger*** — deux lecteurs munis de la seule `narrative` doivent y répondre pareil. Elle **ne double pas la cinquième** : la largeur d'un cas borne son **étendue**, celle-ci borne son **identité topique**. Elle est opposable et non exhortative, le seuil *inter* de q1 étant structurel (« zéro désaccord inattribuable ») et un désaccord sur q1 désignant **nommément le cas**, jamais le guide. Rédaction définitive en **ADR-036** (contenu) et **ADR-038** (protocole d'assessment). — *Énoncé antérieur, applicable pour tout le reste :* Un golden-set v1 synthétique solo doit être figé et versionné, avec guide d'annotation et échelle de grades 0–3 — ⚠️ **l'échelle 0–3 vaut pour le noyau *jugé* seul** (`concept_vers_instance`, [#9](https://github.com/left-eyebr0w/murphy/issues/9)) : les quatre mécanismes gratuits portent un label **binaire sans grade**, et [#3](https://github.com/left-eyebr0w/murphy/issues/3) interdit tout grade sur `R = 0` (précision seule, jamais de rappel, jamais de grade) | Fichier golden-set + guide versionnés, hash de gel consigné ; **le gel porte sur chaque version, non sur la suite des versions** — les versions ne sont pas comparables entre elles, la comparabilité s'obtient par **re-notation des runs archivés** (ADR-032) ; **pertinence et grades validés par le porteur** (ADR-028), les grades ne portant que sur le noyau jugé. **Le guide d'annotation porte huit contraintes de rédaction acquises** (les quatre ci-dessous, plus la **largeur d'un cas** — [#18](https://github.com/left-eyebr0w/murphy/issues/18) —, le **voisinage lexical de la cible hors périmètre** — [#15](https://github.com/left-eyebr0w/murphy/issues/15) —, **le besoin dans les mots de celui qui l'a** — [#13](https://github.com/left-eyebr0w/murphy/issues/13) — et **q1 rédigée pour converger** — [#19](https://github.com/left-eyebr0w/murphy/issues/19) —, toutes quatre énoncées en colonne « exigence ») ([#10](https://github.com/left-eyebr0w/murphy/issues/10), [#11](https://github.com/left-eyebr0w/murphy/issues/11)) : `concept_vers_instance` se rédige **besoin d'abord** (#9), la requête `multi_hop` doit être **réaliste** ([#2](https://github.com/left-eyebr0w/murphy/issues/2)), **la difficulté d'un cas se dérive de propriétés de la tâche, jamais d'un run observé** (interdit de circularité, versant authoring de celui d'E-P2-07), et **les cas variés sont des décalages de registre praticien ↔ citoyen, pas des reformulations lexicales** (#11, qui dissout le quota de `GOLDEN-SET.md` §6.3 dans `variante_de` : c'est là que §6.3 localise le premier facteur d'échec) | ADR-005, ADR-017, ADR-032 | humain | ⬜ |
| E-P2-07 | ⚠️ **RÉVISÉE (3ᵉ révision) — contenu arrêté le 1er août 2026 par [#10](https://github.com/left-eyebr0w/murphy/issues/10), rédaction définitive en attente d'ADR-036.** Applicable en l'état ; seule la formulation peut bouger. Le golden-set doit être typé selon l'**axe unique** des mécanismes de récupération — un mécanisme par cas, pris dans la **liste fermée fixée a priori** — et posséder un **pouvoir discriminant constaté** | Les **cinq mécanismes de la composition v1** non vides (⚠️ *la composition* — cinq — **jamais la liste** — ~~six~~ **sept** depuis [#16](https://github.com/left-eyebr0w/murphy/issues/16), qui scinde `multi_hop` par la profondeur : un mécanisme à **un saut** qui occupe la v1, un mécanisme **profond** présent dans la liste et à **zéro cas**) ; le plancher relève du dimensionnement et vaut **30 cas par mécanisme** ([#11](https://github.com/left-eyebr0w/murphy/issues/11) — règle de trois : zéro échec sur 30 borne le taux d'échec à < 10 %, seuil sans lequel le taux ventilé ci-dessous ne borne rien ; **les variantes n'y comptent pas**, elles ne sont pas des observations indépendantes) ; **date pivot** et **doc(s) germe** présents sur 100 % des cas ; **typage jugé par le porteur** (ADR-028) ; **taux de réussite de la baseline, ventilé par mécanisme, publié à chaque run sans seuil**, direction pré-enregistrée — *un taux qui plafonne est un pouvoir discriminant nul, donc un défaut du jeu*, jamais une bonne nouvelle (ADR-034 §4) ; **la difficulté d'un cas se dérive de propriétés de la tâche, jamais d'un run observé** (interdit de circularité, également porté par le guide d'annotation) ; la part mécanique — comptages, non-nullité — est une **précondition, jamais la vérification** (ADR-028). *Ne subsistent plus* : la grille et sa couverture, le routage de métrique (dérivé, [#3](https://github.com/left-eyebr0w/murphy/issues/3)), les facettes `intention` et `matière`, les trous chiffrés, la clause sur les trois opérations jugées | ADR-036 (remplacera ADR-033), ADR-030, ADR-031, ADR-034 | humain | ⬜ |
| E-P2-08 | Au moins un set diagnostique **graph-hop** doit exister | Set versionné ; requêtes nécessitant ≥ 1 traversée de citation documentées comme telles ; **nécessité du hop jugée par le porteur** (ADR-028). **Distinct du mécanisme `multi_hop` du golden-set** (⚠️ numéroté 6 sous ADR-033, obsolète ; **la liste est à sept mécanismes** — sept après [#2](https://github.com/left-eyebr0w/murphy/issues/2), six en retirant `correspondance_litterale`, parti aux instruments diagnostiques par [#10](https://github.com/left-eyebr0w/murphy/issues/10), puis **sept de nouveau** par la scission de `multi_hop` selon la profondeur ([#16](https://github.com/left-eyebr0w/murphy/issues/16)) — et la renumérotation se règle en ADR-036). **La frontière ne porte plus sur le label mais sur la requête** (#10) : le `multi_hop` du golden-set tire son label de `G₀` tout comme le set miné — les deux puisent au même graphe — mais sa **requête est écrite, et doit être réaliste**, là où celle du set diagnostique est **minée**. Ce dernier reste un instrument séparé, jamais une variante du jeu principal (`GOLDEN-SET.md` §1) | ADR-017, ADR-036 (remplacera ADR-033) | humain | ⬜ |
| E-P2-09 | La comparaison de deux configurations doit passer par un test statistique apparié | Test implémenté ; sortie : différence, p-value, intervalle ; démonstration sur deux runs | ADR-007 | auto | ⬜ |
| E-P2-10 | La baseline doit être **chiffrée et reproductible** : deux exécutions au couple de configurations **`(W, R)` identique** — `W` = workflow d'ingestion (normalisation/chunking/embedding), `R` = runtime de récupération — produisent les mêmes métriques. Le **fingerprint de `W`** est tracé dans l'artefact de run et vérifié contre le pointeur de collection publié | Double run archivé, diff des métriques nul ; fingerprint de `W` consigné et concordant. **À version de qrels constante, consignée dans l'artefact de run** (ADR-032) ; identifiant de graphe `G` consigné (ADR-031). Reproductibilité seule — **la justesse du chiffre est hors périmètre v0** (ADR-028) | `CADRAGE_evaluation` DoD, ADR-026, ADR-027, ADR-031, ADR-032 | auto | ⬜ |

> **Note E-P2-04 (portée strate 1, B-06)** : la suite implémentée couvre les
> invariants *purs* (structure des runs/qrels : rangs contigus/uniques, pas de
> doublon, ids non vides, espaces de nommage run↔qrels compatibles), verte en
> CI sans base de données. Les invariants *live* d'ADR-017 (complétude et
> intégrité des liens Neo4j, qui exigent les BDD peuplées) sont **déjà
> acquis** côté data : complétude par l'équation de complétude des runs
> d'ingestion (B-00), identité/liens par B-01/B-03. E-P2-04 est donc ✅ sans
> les re-tester dans le harnais — décision de cadrage, non un trou.

## 4. Exigences transverses

| ID | Exigence | Vérification | Source | Régime | Statut |
|---|---|---|---|---|---|
| E-T-01 | Le harnais P2 doit être découplé de la génération : aucune dépendance à un LLM générateur. ⚠️ **Renvoi, non extension — 7 août 2026** ([ADR-037](../product/ADR/ADR-037-provenance-authoring.md), ticket [#13](https://github.com/left-eyebr0w/murphy/issues/13)) : cette exigence gouverne le **couplage runtime du harnais à la couche générative**, et **elle ne dit rien de la provenance d'authoring** — de ce qui a écrit le texte d'une question. C'est un **autre objet**, traité par ADR-037 (un LLM hors ligne propose des *notions* pour `concept_vers_instance`, le porteur rédige ; aucun texte non relu n'entre dans le jeu ; test de reproductibilité). **L'énoncé et la vérification ci-contre sont inchangés** : le renvoi dit seulement où lire le second objet, il n'élargit pas celui-ci | Revue du code du harnais : périmètre récupération seule. *(La provenance d'authoring ne se vérifie pas ici — elle se vérifie sur l'enregistrement d'un cas, ADR-037 §1.)* | ADR-016 · ADR-037 (renvoi) | auto | ⬜ |
| E-T-02 | Tout artefact d'évaluation (qrels, runs, golden-sets) doit être versionné et rejouable | Artefacts sous contrôle de version ; procédure de rejeu documentée | ADR-008 | auto | ⬜ |

## 5. Sortie de version

La v0 est close quand **toutes les exigences ci-dessus sont ✅**,
preuves à l'appui — constat consigné par mini-ADR de clôture
(`PILOTAGE.md` §3). Toute exigence invérifiable ou obsolète est
révisée par ADR, jamais contournée. Pour les exigences de régime
**humain** ou **assisté** (ADR-028), la preuve inclut **qui a validé et
quand** (porteur v0) — un test vert ne suffit pas.

## 6. Traçabilité

Chaque item du `BACKLOG.md` référence l'exigence qu'il sert. Une
exigence sans item alors qu'elle n'est pas ✅ = trou de backlog ; un
item sans exigence = hors périmètre v0 (à différer ou signe qu'une
exigence manque, cf. `PILOTAGE.md` §2).
