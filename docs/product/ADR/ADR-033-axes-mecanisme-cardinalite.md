# ADR-033 — Axes du golden-set : mécanisme de récupération × cardinalité

**Statut** : ⛔ **OBSOLÈTE** (1er août 2026) — **remplacé par ADR-035**, en cours
de rédaction. Acté le 31 juillet 2026 ; **amendait ADR-030** (remplace ses deux
axes, conserve sa machinerie), **révisait E-P2-07** pour la seconde fois,
**confirmait ADR-007** contre une proposition concurrente.

> ## ⛔ Ne pas appliquer ce document
>
> Une session de cadrage du 1er août 2026 a démoli l'essentiel de cette
> décision. **Seul survit son axe primaire** — les mécanismes de récupération,
> qui restent la structure du golden-set. Sont tombés :
>
> - **la cardinalité comme second axe**, et avec elle la grille des quatorze
>   cellules valides (§*Décision*) ;
> - **les douze strates** comme cadre d'échantillonnage, et le vecteur de
>   pondération D₁ ;
> - **le re-tagage des 72 questions** de `eval/artifacts/questions/raw/` prescrit
>   en §*Conséquences* — elles sont rebutées, pas re-taguées.
>
> S'y ajoute, depuis le 1er août, un changement dans l'axe survivant lui-même :
> **la liste passe de huit mécanismes à sept** (`robustesse_paraphrase` devient
> une variante applicable à tout cas), et `concept_vers_instance` cesse d'être
> de régime *détenu* — son label asserté est une opinion, pas un fait
> d'authoring.
>
> **ADR-007 n'est plus confirmé par ce document**, puisqu'il est obsolète ; la
> validité de `nDCG@R` est rouverte.
>
> Le nouveau socle se construit sur la carte
> [Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1),
> et atterrira en **ADR-035**. Ce document est conservé comme **archive** : son
> raisonnement sur le renversement contenu → mécanisme (§*Contexte*, §4.4 de
> `GOLDEN-SET.md`) reste le fondement de l'axe survivant.

## Contexte

Une session de travail menée **sans accès au corpus ADR** a produit une
synthèse indépendante du cadre d'évaluation (note de session, supprimée après
reversement — **cet ADR en est le seul enregistrement**). Elle déclarait
bloquante la réconciliation avec les quatre types d'action d'ADR-009 — déjà
tranchée par ADR-030 neuf jours plus tôt.

L'absence d'accès au corpus n'est pas un accident de méthode : elle fait de
cette synthèse une **dérivation indépendante**, et c'est ce qui donne du poids
à ses convergences.

La confrontation des deux cadres a donné une **convergence** et trois
**divergences**.

La convergence est le fait le plus solide du dossier : les deux cadres
suppriment l'axe difficulté, avec le même argument — *l'étiquette absorbe la
question qu'elle prétend documenter*. Deux dérivations indépendantes, une seule
conclusion. Ce point cesse d'être une préférence.

Les divergences ont été arbitrées une à une :

| Divergence | ADR-030 | Note | Retenu |
|---|---|---|---|
| Axe primaire | intention (requête) | **mécanisme de récupération** | **la note** |
| Axe secondaire | opérations (arête) | **cardinalité du golden-set** | **la note** |
| Métriques | nDCG@R, refus des coupes constantes | `Recall@k` par cellule | **ADR-030 / ADR-007** |

## Le problème que le renversement résout

ADR-030 organisait le jeu par **ce que l'utilisateur veut**. C'est un axe de
besoin, et il hérite du défaut que la note nomme correctement : l'espace des
besoins est adossé au **contenu** du droit — domaines, institutions, logiques —
donc non borné, sans complétion naturelle, et combinatoire.

L'axe **mécanisme de récupération exercé** est d'une autre nature : c'est un
ensemble *énumérable et petit* de fonctions testables au sens logiciel. On
n'évalue plus un contenu, on évalue une fonction. Le contenu descend au rang de
facette qu'on **tague et qu'on slice**, jamais qu'on énumère.

Ce que ça gagne, et qui n'était pas acquis : la wickedness reste confinée à une
seule dimension, et cette dimension devient de l'**échantillonnage stratifié**
plutôt qu'une exigence d'exhaustivité.

## Décision

### Axe primaire — huit mécanismes de récupération

Portés par le **cas de test**, un seul par cas. Chaque mécanisme nomme son
régime au sens de la hiérarchie de provenance (§ *Tags* ci-dessous) : aucun
n'est *jugé*.

| # | Mécanisme | Nature du test | Régime |
|---|---|---|---|
| 1 | `correspondance_litterale` | Requête = texte source verbatim | détenu (authoring) |
| 2 | `resolution_reference` | « article 1240 du Code civil » → l'article (ELI) | dérivé (requête) |
| 3 | `known_item_identifiant` | ECLI, n° de pourvoi → la décision | dérivé (requête) |
| 4 | `robustesse_paraphrase` | Reformulation → même cible | détenu (paire fabriquée) |
| 5 | `concept_vers_instance` | Notion juridique → l'article qui la fonde | détenu (authoring) |
| 6 | `multi_hop` | Cible atteignable seulement via une citation | dérivé (graphe `G₀`) |
| 7 | `desambiguisation` | Terme à référents concurrents attestés | détenu + constatable |
| 8 | `absence_hors_corpus` | Besoin hors corpus → *fail-fast*, pas de pertinence hallucinée | détenu (authoring) |

**Continuité avec ADR-017** : les mécanismes 1–3 et 8 sont proches de la
strate 1 (invariants structurels), le 6 relève des sets graph-hop (E-P2-08).
L'apport propre est de nommer une famille *cheap* supplémentaire — les
**known-item auto-étiquetés** — dont le label est un **fait d'authoring** et
non un jugement de pertinence. R-05 (biais golden-set solo) y est esquivé par
construction, pas atténué.

### Axe secondaire — la cardinalité, à quatre niveaux

Portée par le cas, un seul niveau par cas. Le second axe **ne change pas le
comportement du système, il change la mesure** : il détermine quelle métrique
est valide dans chaque cellule, ce qui interdit mécaniquement l'erreur
« nDCG@R partout ».

| Cardinalité | Nature du besoin | Métrique de la cellule |
|---|---|---|
| **0 — vide attendu** | Hors corpus, hors périmètre | **Diagnostic de précision seule**, statut ADR-029 : jamais de rappel, jamais de grade |
| **1 — cible unique** | Known-item, référence résolue | **Doc-MRR**, lecture *success@1* |
| **n — ensemble borné** | Conjonctif (principe + exception) | **Recall@R**, tout-ou-rien |
| **ouvert — topique** | Pertinence graduée | **nDCG@R** |

**Le niveau 0 est un ajout de cet ADR**, et il est ce qui rend l'arbitrage
cohérent. Sans lui, le mécanisme 8 serait une valeur d'axe *à couvrir*
(§ *Discipline d'axe*) alors que ses cas ont `R = 0` : la coupe de nDCG@R est
indéfinie, la métrique aussi (GOLDEN-SET §8.1). Toute une colonne de la grille
aurait été non scorable par construction. Le niveau 0 la rend first-class en
déclarant sa propre métrique — exactement ce pour quoi l'axe cardinalité
existe.

**`Recall@k` de la note est corrigé en `Recall@R`.** Dans la cellule « ensemble
borné », la cardinalité est **connue par authoring** : `R` est écrit avec le
cas. La coupe y est donc adaptative comme partout ailleurs, et le refus des
coupes constantes (ADR-007) reste entier. La contradiction apparente se
dissout ; elle ne se négocie pas.

### Cellules valides — quatorze, toutes à couvrir

Les deux axes se **croisent et se couvrent** : c'est le coût engageant. La
grille brute fait 32 cellules, dont 18 sont vides par construction (un
known-item par identifiant n'est pas de cardinalité ouverte).

| Mécanisme | 0 | 1 | n | ouvert |
|---|:-:|:-:|:-:|:-:|
| 1 `correspondance_litterale` | | ✓ | ✓ | |
| 2 `resolution_reference` | | ✓ | | |
| 3 `known_item_identifiant` | | ✓ | | |
| 4 `robustesse_paraphrase` | | ✓ | ✓ | ✓ |
| 5 `concept_vers_instance` | | | ✓ | ✓ |
| 6 `multi_hop` | | ✓ | ✓ | |
| 7 `desambiguisation` | | | ✓ | ✓ |
| 8 `absence_hors_corpus` | ✓ | | | |

**Le vide impossible est de l'information, le vide non observé est un défaut.**
Cette table les sépare : une cellule non cochée n'est jamais à peupler ; une
cellule cochée et vide est un manque de couverture, chiffré au rapport.

### Discipline d'axe — un seul axe secondaire engageant

Un axe se *croise et se couvre* (coût combinatoire d'authoring) ; une facette
se *tague et se slice* (quasi gratuit). Un deuxième axe engageant recréerait la
grille infinie qu'on vient d'éviter.

Filtres pour mériter le statut d'axe : **orthogonalité** au primaire ·
**interaction** forte · **bornage** · **localité diagnostique** (un échec
pointe une réparation).

**Réserve d'orthogonalité, assumée.** La cardinalité corrèle partiellement avec
le mécanisme — un known-item *est* de cardinalité 1. Elle n'est donc pas
parfaitement orthogonale. C'est acceptable : la corrélation n'annule pas la
validité métrique de chaque cellule, et la table ci-dessus la rend explicite au
lieu de la laisser produire des doublons.

### Rétrogradations — matière et intention deviennent des facettes

**La matière (12 strates) cesse d'être un axe engageant.** Elle reste le cadre
d'**échantillonnage stratifié** et conserve son vecteur de repondération D₁,
mais seules les cellules `mécanisme × cardinalité` sont obligatoires. La
matière est équilibrée au mieux ; **ses trous sont permis et chiffrés**, ce qui
est précisément l'information que la couverture forcée détruisait.

**L'intention (5 valeurs, GOLDEN-SET §5) est rétrogradée en facette.** Elle
est *détenue par construction*, son vocabulaire est clos, et elle répond à une
question de slice nommable — « le mécanisme dégrade-t-il selon ce que
l'utilisateur veut ? ». Elle reste donc taguée sur 100 % des questions, mais
n'est plus couverte.

### Les opérations d'ADR-030 survivent, sans être un axe

**Lecture retenue, à corriger si elle ne l'est pas.** Les huit opérations
d'ADR-030 et les huit mécanismes ci-dessus ne portent pas sur le même objet :
l'opération type une **arête** `(requête, source, cible)` — *pourquoi ce
document-ci est pertinent* — quand le mécanisme qualifie un **cas** — *quelle
fonction de récupération est exercée*. L'arbitrage retire aux opérations leur
statut d'axe ; il ne les supprime pas.

Ce qui survit intégralement d'ADR-030, et qu'il aurait été coûteux de perdre :

- le **régime jugée / dérivée** — la surface d'annotation reste les trois
  opérations sémantiques (`texte_applicable`, `jurisprudence_applicable`,
  `definition`) ;
- le **portage par l'arête** et le champ `source` de `Judgment` (ADR-008) ;
- la **dérivation depuis le graphe témoin `G₀`** (ADR-031) pour les quatre
  opérations de graphe ;
- la règle de tri *enregistrer ce qui a coûté une lecture, dériver le reste*
  (ADR-028 étendue) et les trois couches de gel qui en descendent ;
- la réserve sur la **ventilation** : restreindre les qrels aux arêtes d'un
  type change `R`, donc la coupe — deux ventilations ne se comparent pas entre
  elles, ni à l'agrégat.

Les opérations deviennent des **facettes dérivées**, au sens de la hiérarchie
ci-dessous — le meilleur régime disponible.

### Tags — hiérarchie de provenance et règle d'admission

La bonne question n'est pas « ce tag est-il pertinent ? » (tout l'est
vaguement) mais **d'où vient sa valeur ?** — car la source détermine le coût
*et* le risque R-05.

| Rang | Source | Coût | Statut |
|---|---|---|---|
| 1 | **Dérivé de l'identité canonique** — lu depuis l'ECLI, l'ELI, la structure, `G₀` | gratuit, objectif, **permanent** (survit à la ré-ingestion) | le tag idéal |
| 2 | **Détenu par construction** — connu parce qu'on a fabriqué le cas | gratuit, objectif | admis |
| 3 | **Jugé** — arbitrage de pertinence ou de difficulté | cher, R-05 | **banni en v0** |

**Règle d'admission.** Un tag mérite sa place **ssi** (1) il est dérivé ou
détenu, jamais jugé ; (2) on peut **nommer la question** de diagnostic ou de
couverture qu'on répondrait en *slice*-ant dessus — pas de question, pas de
tag ; (3) son **vocabulaire est clos** et le **null est permis**.

**Le soulagement, et il est structurel :** les trois angles *wicked* du départ
— thématiques, domaines, institutions — sont **déjà encodés dans la structure
du corpus DILA**, donc dérivables. La juridiction est dans l'ECLI, la
chambre dans les métadonnées, le domaine se lit sur le code (LEGI) ou la
chambre (CASS). On ne les énumère pas : **on les lit sur l'identité
canonique.** La wickedness de contenu disparaît non parce qu'on l'épuise, mais
parce que DILA l'a déjà étiquetée.

### Le null est une valeur de première classe

Pas un trou. Le droit non codifié → domaine `null`, jamais deviné. Le rapport
affiche « X % des cas portent un domaine », **et ce pourcentage est lui-même
une information**. Forcer une valeur pour éviter un trou réintroduit
exactement le jugement arbitraire que R-05 interdit.

### La difficulté est un label calculé en sortie

Jamais tagué en entrée. **Un cas que la baseline rate est *de facto*
difficile** : la difficulté devient un label produit par le harnais, pas
asserté par l'annotateur. C'est ADR-012 poussé jusqu'au tag — mesurer plutôt
qu'affirmer.

### Discipline d'authoring — écrire des cas qu'on s'attend à rater

La suite doit contenir des cas **conçus pour échouer**. Une suite réussie à
100 % par la baseline a un pouvoir discriminant nul et ne mesure aucune marge
de progression. On écrit délibérément des cas de stress — paraphrase agressive,
graph-hop profond, homonymes — *à côté* des cas triviaux.

C'est une exigence de conception, pas un conseil : sans elle, la baseline de
B-11 ne prouve rien.

## Alternatives rejetées

- **Conserver les axes d'ADR-030.** Le défaut identifié est réel : un axe de
  besoin est adossé au contenu, donc non bornable. Ce que la note apporte n'est
  pas une préférence de découpage mais un changement de nature de l'axe.
- **Garder la matière comme axe engageant** (12 × 14 = 168 cellules
  obligatoires). Réintroduit le contenu comme axe — ce que tout le renversement
  vise à éviter — et donne trois facteurs engageants là où la discipline en
  admet deux.
- **Conserver l'intention comme troisième axe de couverture.** Viole la règle
  d'un seul axe secondaire engageant et fait exploser la grille.
- **`Recall@k` par cellule** (la note, §3.2). Heurte ADR-007 de front. La
  cardinalité étant écrite par authoring, `Recall@R` obtient le même résultat
  sans coupe constante.
- **Laisser le mécanisme 8 hors quota** (statut actuel des questions négatives,
  GOLDEN-SET §8.1). Cohérent, mais laisse la précision hors de la structure
  alors que c'est la moitié de ce qu'on mesure. Le niveau de cardinalité 0
  l'intègre à coût nul.
- **Porter le mécanisme par l'arête**, comme les opérations. Le mécanisme
  qualifie ce qui est *exercé par le cas* ; plusieurs mécanismes sur une même
  question rendraient la couverture de la grille ininterprétable. La
  multiplicité légitime que ce portage visait est déjà servie par le niveau
  « n — ensemble borné » de la cardinalité.

## Conséquences

- **E-P2-07 est révisée pour la seconde fois.** Nouveau critère : mécanisme et
  cardinalité présents sur 100 % des cas ; les 14 cellules valides non vides ;
  intention et matière taguées à 100 % mais **non couvertes**, trous chiffrés
  au rapport.
- **La dérivation de N_q change de facteurs** (GOLDEN-SET §7.3) :
  `mécanisme × cardinalité`, matière équilibrée. Les nombres restent une
  proposition en régime **humain** (ADR-028).
- **Trois sous-ensembles hors quota sont absorbés.** §8.1 (négatives) devient
  la cellule `(8, cardinalité 0)` ; §8.2 (paires isosémantiques) devient le
  dispositif du mécanisme 4 ; §8.4 (matériau adversarial de polysémie) devient
  le matériau du mécanisme 7. Seule §8.3 (strate-frontière) reste hors quota,
  comme facette `matière = null`.
- **Le tag « cas négatif » de la note disparaît** : redondant avec la
  cardinalité 0.
- **Les questions déjà générées restent valides comme matériau.** Les 72
  questions d'`eval/artifacts/questions/raw/` ont été écrites sous un cadrage
  `intention × registre` ; elles peuplent une à deux cellules sur quatorze et
  demandent un re-tagage, pas une réécriture. Le prompt de génération doit
  gagner un cadrage `MÉCANISME` et `CARDINALITÉ`.
- **`QueryMetrics` gagne `mecanisme` et `cardinalite`**, tous deux non
  nullables. La révision de signature annoncée par ADR-030 (`action_type` au
  pluriel) reste à faire et se fait maintenant en une passe.
- **Le scorer doit sélectionner sa métrique par cellule.** C'est le seul coût
  d'implémentation neuf de cet ADR : Doc-MRR et Recall@R existent déjà comme
  lectures (ADR-007), mais leur **routage par cardinalité** est à écrire.
- **E-P2-08 gagne une frontière explicite.** Le mécanisme 6 `multi_hop` et le
  set diagnostique graph-hop de B-09 se ressemblent mais ne sont pas le même
  objet : le premier est **écrit** et entre dans la grille scorable, le second
  est **miné** depuis `G₀` (B-07 → B-09) et reste un instrument séparé,
  précision-seulement. La distinction est celle d'ADR-029 — elle n'est pas
  neuve, elle devait juste être dite.
- **La note de session est supprimée**, son contenu utile étant reversé ici
  (§ *Décision*) et dans `GOLDEN-SET.md` §4.2, §5.1 et §5.3. Ce qui a été
  écarté est tracé dans les *Alternatives rejetées* — notamment le `Recall@k`,
  seul point où l'arbitrage a tranché contre elle.

## Références

ADR-005 (cascade q1–q3) · ADR-007 (**confirmé** — coupe adaptative, refus des
coupes constantes) · ADR-008 (format ; champ `source`) · ADR-009 (amendé par
ADR-030) · ADR-012 (constat sur preuves, pas pré-décision) · ADR-017 (strates)
· ADR-018 (identité canonique — support des tags dérivés) · ADR-028 (frontière
vérification / validation) · ADR-029 (diagnostic précision-seulement — statut
de la cardinalité 0) · **ADR-030 (amendé ici : axes remplacés, machinerie
conservée)** · ADR-031 (graphe témoin `G₀`) · ADR-032 (versionnement) ·
`EXIGENCES_v0.md` E-P2-06/07/08 · `GOLDEN-SET.md` §4, §5, §7, §8 ·
`BACKLOG.md` B-08 · R-05 (`RISQUES.md`)
