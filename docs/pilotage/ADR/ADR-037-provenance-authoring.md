# ADR-037 — Provenance d'authoring : qui écrit une question, et ce que la machine reçoit

**Statut** : Acté (7 août 2026, session de la carte
[#1](https://github.com/left-eyebr0w/murphy/issues/1), ticket
[#13](https://github.com/left-eyebr0w/murphy/issues/13)) — renverse le
*« pas d'ADR »* de `WIP/B-08-generation-requetes.md` §11 (fichier supprimé
le 7 août, cet ADR et la [résolution de #13](https://github.com/left-eyebr0w/murphy/issues/13)
en sont la stèle).

> **Numérotation.** ADR-036 reste **réservé au contenu du golden-set**, à la clôture de la
> carte. Cet ADR est **distinct** : il porte la provenance, qui vaut **au-delà** du
> golden-set. L'écart de numéros n'est pas un trou — c'est une réservation.

## Contexte

`WIP/B-08-generation-requetes.md` §2 posait une question (D-01) — *l'emploi hors ligne
d'un LLM pour produire des questions contrevient-il à **E-T-01** ?* — et concluait
*« pas d'ADR : une note sous E-T-01, la réponse clarifie une exigence existante et
n'arbitre aucune architecture »*.

**Deux raisons indépendantes que ça ne tient pas.**

**(a) Le test déborde l'exigence qu'il prétendait clarifier.** Le critère employé pour
répondre à D-01 — *« un run devient-il irreproductible si le fournisseur change de modèle
demain ? »* — a **déjà servi ailleurs** : [#5](https://github.com/left-eyebr0w/murphy/issues/5)
§2 l'applique pour **écarter un LLM classificateur** du capteur de modes d'échec, un
chantier hors de cette carte. Or E-T-01 dit *« aucune dépendance à un LLM **générateur** »* :
un classificateur n'en est pas un. Le test a donc tranché un cas **hors de la lettre**
d'E-T-01, avec le verdict **inverse** du premier usage. Une règle à deux applications, deux
chantiers, deux verdicts opposés n'est pas une note d'éclaircissement.

**(b) Et c'est la raison décisive — E-T-01 ne parle pas de ce sujet.** Sa source est
**ADR-016**, dont l'invariant est *« sourcer, ne pas raisonner »* et dont la conséquence
écrite est *« la récupération peut tourner et progresser sans qu'aucun LLM ne soit
branché »*. E-T-01 gouverne le **couplage runtime du harnais à la couche générative du
produit**. La provenance d'authoring d'un texte de question est un **autre objet**. La
réponse honnête à D-01 est que **E-T-01 n'en dit rien** — pas qu'il l'autorise.

S'y ajoute le critère « **rien à jeter** » d'ADR-035 §6 : un participant externe voudra
savoir **ce qui a écrit les questions**. Ça ne se lit pas dans une note de bas de page d'un
fichier d'exigences.

Le §2 du document mort faisait donc deux choses en croyant n'en faire qu'une :

| Ligne du §2 | Relève de | Sort |
|---|---|---|
| « `eval/` appelle un LLM » = interdit | genuinement E-T-01 / ADR-016 | survit, rien de neuf |
| Le LLM hors ligne produit des candidats, le porteur tranche | provenance d'authoring — **hors E-T-01** | règle neuve, §2 ci-dessous |
| Aucun texte non relu n'entre dans le jeu | provenance d'authoring — **hors E-T-01** | règle neuve, §2 ci-dessous |
| Le test de reproductibilité | critère général, **déjà employé hors périmètre** | règle neuve, la plus portante — §3 |

## Décision

### 1. Deux objets distincts : couplage **runtime** ≠ provenance d'**authoring**

E-T-01 et sa source ADR-016 gouvernent le premier : le harnais `eval/` n'a aucune
dépendance à une couche générative, et la récupération s'évalue sans qu'aucun LLM ne soit
branché. **Cet ADR gouverne le second** : ce qui a produit le texte d'un cas, et ce qu'une
machine a reçu pour le produire.

**E-T-01 reçoit un renvoi vers cet ADR, jamais son contenu.** Les deux exigences ne se
vérifient pas au même endroit : E-T-01 se vérifie par revue du code du harnais, la
provenance se vérifie sur l'**enregistrement d'un cas** et sur la discipline du porteur.

### 2. La frontière — un LLM propose des **notions**, le porteur **rédige**

**Interdits, conservés verbatim du document mort :**

1. **`eval/` n'appelle jamais un LLM.** Aucune dépendance, à aucun moment du chemin
   d'évaluation. C'est le versant qui relevait bien d'E-T-01, et il ne change pas.
2. **Aucun texte non relu n'entre dans le jeu.** Il n'existe pas de cas dont le texte soit
   sorti d'une machine et entré tel quel dans la collection.

**Autorisé, et strictement restreint :** un LLM, **hors ligne**, propose des **notions
juridiques candidates** pour `concept_vers_instance`. Le porteur en retient, **rédige
lui-même le besoin** — *besoin d'abord*, dans les mots de celui qui a le besoin et jamais
dans ceux de la norme qui y répond (7ᵉ contrainte de rédaction) — puis cherche la cible.

> **Ce n'est pas le protocole en deux temps sous un autre cartouche, c'est un autre acte.**
> Le document mort parlait de *« textes candidats »* ; il n'a jamais couvert la proposition
> d'un **germe conceptuel**.

Deux motifs portent la restriction :

- `concept_vers_instance` est **le seul endroit de la v1 où « produire des candidats sans
  document sous les yeux » a un sens**. Sur les quatre mécanismes gratuits, le germe est
  exigé à 100 % et *la requête désigne le germe* : on écrit **avec le document sous les
  yeux**. C'est l'inversion de prémisse qui a tué le protocole en deux temps.
- **30 cas tirés d'une seule tête clusterisent**, et #20 §3 a déjà armé le déclencheur
  *« `concept_vers_instance` peu discriminant »*. L'auteur unique le rend plus probable,
  pas moins.

> ⚠️ **Risque assumé, non mitigé par la décision elle-même** : le répertoire de notions
> d'un LLM penche vers les notions **célèbres**, donc lexicalement bien couvertes. C'est un
> biais de **facilité** sur le seul mécanisme qui porte le score continu. Il ne viole pas
> l'interdit de circularité de #10 — qui vise la dérivation depuis un **run observé** —
> mais il mord sur le **pouvoir discriminant** qu'E-P2-07 exige. Trois dispositifs le
> surveillent, tous acquis ailleurs : l'**interdit d'hygiène** de §4(1), la **sentinelle du
> taux de rejet à l'authoring** ventilé par cause, et le champ **`origine_notion`**
> (ADR-036).

### 3. Le **test de reproductibilité** — critère général, réutilisable

> **Un run devient-il irreproductible si le fournisseur change de modèle demain ?**

C'est la formulation utile de la règle — pas *« pas de LLM »*. Elle se lit ainsi : **une
provenance est licite si et seulement si le retrait du fournisseur ne change rien à ce qui
est archivé.**

- Ce qu'une machine produit et qui est **consommé tel quel** par le dispositif → **interdit**.
  Le modèle devient une dépendance silencieuse d'un résultat, et sa disparition rend le
  résultat irreproductible.
- Ce qu'une machine **suggère**, que le porteur relit, réécrit et archive → **licite**. Ce
  qui vit dans le dépôt est le texte du porteur ; le modèle ne laisse **aucune trace dans
  l'artefact**.

**Deux applications, deux verdicts opposés, et c'est cohérent** — c'est ce contraste qui a
justifié un ADR plutôt qu'une note :

| Application | Ce que la machine produirait | Verdict |
|---|---|---|
| Classificateur du capteur de modes d'échec (#5 §2, hors carte) | un **routage** consommé tel quel à chaque exécution | ⛔ écarté |
| Proposition de notions pour `concept_vers_instance` (§2 ci-dessus) | une **suggestion**, jetée après rédaction | ✅ licite |

**Portée : au-delà du golden-set.** La règle a déjà servi sur un chantier que cette carte ne
couvre pas ; elle s'applique à tout artefact durable du programme, pas aux seules questions.

### 4. Hygiène de prompt — **ne jamais dire au modèle ce que la mesure attend de lui**

C'est le principe réel de l'hygiène, et **ce n'est pas « pas de chiffres »**.

**Ce qui meurt sans remplaçant** : l'interdit *« aucun poids D₁ »* visait une
**distribution** — un modèle à qui l'on annonce que le pénal pèse 52 % équilibre de
lui-même. La cible a disparu avec le vocabulaire D₁/D₂/D₃, et #4 a tranché que **rien ne la
remplace** (*aucun cadre d'échantillonnage*). **Il n'y a pas de « nouveau D₁ ».** En
particulier, ne se transportent pas :

- **le plancher de 30 est un compte, pas une distribution** — rien à équilibrer, aucune
  proportion à reproduire, un seul mécanisme concerné ;
- **nommer le mécanisme est obligatoire et licite** — #10 autorise explicitement de dériver
  la difficulté **de propriétés de la tâche**, et décrire la tâche *est* la tâche.

**Ce qui prend sa place — deux interdits neufs.** Sous la v1, ce qu'on attend de
`concept_vers_instance` est son **pouvoir discriminant** ; c'est là que la contamination se
reloge :

1. **Ne pas dire que la notion doit avoir un fondement textuel identifiable.** Le dire
   pousse vers les notions **codifiées**, celles qui ont un ancrage lexical propre —
   exactement le biais de facilité du §2. Et le mécanisme est **jugé** : rien n'exige qu'une
   cible préexiste, c'est l'assesseur qui constitue les qrels. Annoncer l'exigence, c'est la
   **fabriquer sans en avoir besoin**.
2. **Ne pas annoncer que le cas sera jugé, ni combien de documents pertinents on espère.**
   C'est le filtre que #6 a démasqué chez TREC — *les topics y sont filtrés sur le nombre
   estimé de documents pertinents* — et dont #6 a établi qu'il rendait la justification du
   jeu par TREC **inexacte**. On ne réintroduit pas par le prompt ce qu'une résolution a
   retiré du fondement.

**Rappel d'un interdit connexe, acquis et non négociable** (#6, également porté par le guide
d'annotation, cité ici parce qu'il gouverne *ce que la machine reçoit et rend*) : **aucun
filtrage de cas ne passe par le retriever de Murphy.** Le filtre de qualité standard
(*« the query should retrieve its source passage »*) est un test de **retrouvabilité** :
appliqué à un golden-set, il conserve précisément les cas que le système réussit déjà et
écarte les cas durs — le jeu « échoue en rassurant ». Si un filtre automatique est employé,
il doit être **indépendant du système évalué**.

## Alternatives rejetées

- **Une note sous E-T-01** — la position du document mort. Rejetée par les deux raisons du
  *Contexte* : le test déborde l'exigence, et E-T-01 ne parle pas de ce sujet.
- **Interdire tout LLM à l'authoring.** Position par défaut, apparemment la plus sûre. Son
  coût est réel et il tombe **au pire endroit** : 30 cas écrits d'une seule tête sur le seul
  mécanisme porteur du score continu, avec un déclencheur *« peu discriminant »* déjà armé
  par #20 §3. La prudence apparente achète un risque de mesure.
- **Le protocole en deux temps** (le LLM produit des textes candidats, le porteur
  sélectionne). Mort **par inversion de prémisse**, pas par axe périmé : il supposait
  *« aucun document, aucun extrait — on ne décalque pas ce qu'on n'a pas »*, or sur quatre
  des cinq mécanismes de la v1 **on l'a**. Il n'était donc pas à re-cartoucher, il était
  **sans objet**.
- **Porter l'hygiène au guide d'annotation.** Le guide s'adresse aux humains qui **jugent**.
  La frontière ne dit pas seulement *qui tranche*, elle dit **ce que la machine reçoit** :
  séparer les deux laisserait la moitié portante de la règle dans un document qui ne
  s'adresse pas à celui qui la met en œuvre.

## Conséquences

- **E-T-01 reçoit un renvoi** vers cet ADR (`EXIGENCES_v0.md` §4). Son énoncé et sa
  vérification sont **inchangés** — le renvoi dit seulement qu'un second objet existe et où
  il est traité.
- **La surveillance du risque de §2 est déjà financée**, et cet ADR n'en crée aucune :
  `origine_notion` (`porteur` | `llm`, rempli sur `concept_vers_instance` seul) est défini
  en **ADR-036** avec le reste de l'enregistrement ; le **taux de rejet à l'authoring**,
  publié sans seuil et ventilé par cause, est une **sentinelle** du rapport.
- **`origin` reste à variance nulle en v1** : sous cet ADR le porteur écrit **tous** les
  textes. ~~La dérogation qui le conserve est suspendue à
  [#21](https://github.com/left-eyebr0w/murphy/issues/21) — *si le texte d'un cas est
  immuable, `origin` redevient reconstituable depuis la version et la dérogation est à
  reprendre.*~~
  ✅ **Tranché le 8 août 2026, et pas dans le sens anticipé**
  ([#21](https://github.com/left-eyebr0w/murphy/issues/21) §1c et §0). **Le texte d'un cas
  n'est pas immuable** : une réécriture **sans changement de sujet** (coquille, formulation
  qui viole une contrainte de rédaction) garde son `case_id`, déplace le hash `cas` et
  laisse les qrels valides ; seul le **changement de sujet** cesse d'être une correction pour
  devenir un **retrait + ajout** sous id neuf. **La dérogation tombe quand même, et sur un
  motif plus solide** : l'unité de l'intake est une **contestation, jamais un patch**, et les
  corrections sont **dérivées et proposées en interne** — donc **l'intake ne transporte
  jamais de texte**. Un texte corrigé est toujours écrit par le porteur : `origin` reste à
  variance nulle **sous toutes les ères** (porteur seul, panel ADR-025, communauté), donc
  **reconstituable depuis la version**, et la dérogation de
  [#12](https://github.com/left-eyebr0w/murphy/issues/12) §7 est **à reprendre à l'écriture
  d'ADR-036**. Le motif anticipé ici dépendait du régime d'authoring de la v1 ; celui-ci est
  **stable sous l'enfichabilité des acteurs**. *(`origine_notion` n'est pas concerné : il
  relève de la **couche de dérivation** d'ADR-030, pas d'un hash.)*
- ⚠️ **Réserve assumée — la monoculture stylistique empire.** Le document mort la donnait
  comme *« le seul risque qu'aucune parade interne ne traite »*. Sous cet ADR elle
  s'aggrave : le porteur écrit **seul les 30 textes** du seul mécanisme jugé, là où le
  document supposait un LLM produisant de la variété. **Actée telle quelle, sans parade
  fabriquée** — sa parade est le **mélange des plumes en v2**.
- **Aucune conséquence sur `eval/`.** Cet ADR n'autorise aucun appel de modèle depuis le
  code ; il ne décrit pas un composant, il décrit une discipline de rédaction.

## Prémisses

- **#13** §2 (la décision elle-même) et §3 (les deux interdits neufs) — cet ADR en est la
  rédaction, pas une extension.
- **#5** §2 — le test appliqué au capteur avec le verdict inverse ; **appui décisif** de la
  raison (a). Tombe si le capteur cessait d'être hors périmètre d'E-T-01.
- **ADR-016 / E-T-01** — couplage *runtime*, jamais provenance d'authoring ; **appui
  décisif** de la raison (b).
- **#9** — `concept_vers_instance` est le seul mécanisme *besoin d'abord* et le seul jugé.
  **Condition d'emploi** : le §2 se restreint à ce mécanisme *parce qu'il est le seul de son
  espèce*. S'il en entrait un second, la restriction serait à réinstruire, pas à étendre par
  défaut.
- **#12** §1 (germe exigé à 100 % des cas à label gratuit) et **#16** §9c (*la requête
  désigne le germe*) — c'est **tout l'appui** de l'inversion de prémisse. Tombe si le germe
  cessait d'être exigé.
- **#10** §5 — interdit de circularité, et l'autorisation de dériver la difficulté de
  propriétés de la tâche (§4).
- **#6** — le filtre de qualité standard est circulaire s'il passe par le retriever évalué ;
  les topics TREC sont filtrés sur le nombre estimé de documents pertinents (§4(2)).
- **#4** — aucun cadre d'échantillonnage, donc les poids D₁ meurent **sans remplaçant**.
- **#20** §3 — le déclencheur *« `concept_vers_instance` peu discriminant »* est déjà armé.
- **ADR-035** §6 — critère « rien à jeter » : un participant externe demandera ce qui a
  écrit les questions.

## Références

`docs/pilotage/EXIGENCES_v0.md` (E-T-01) · ADR-016 · ADR-035 §6 · ADR-036 (contenu du
golden-set — `origin`, `origine_notion`, enregistrement) ·
[carte #1](https://github.com/left-eyebr0w/murphy/issues/1) ·
[résolution de #13](https://github.com/left-eyebr0w/murphy/issues/13) ·
`docs/product/recherche/requetes-generees.md`
