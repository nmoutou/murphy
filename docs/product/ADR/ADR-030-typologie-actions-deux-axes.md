# ADR-030 — Typologie des actions : deux axes, type porté par l'arête

**Statut** : Acté (22 juillet 2026, préparation de B-08) — **amende ADR-009**
(quatre types d'action), **révise E-P2-07**, **prolonge ADR-028** (frontière
observation / dérivation) — ⚠️ **partiellement amendé par
[ADR-033](ADR-033-axes-mecanisme-cardinalite.md)** (31 juillet 2026)

> **Ce qui a changé, et ce qui n'a pas changé.** ADR-033 remplace les **deux
> axes** fixés ici : l'axe primaire devient le **mécanisme de récupération**
> (porté par le cas) et l'axe secondaire la **cardinalité du golden-set**.
> `intention` est rétrogradée en facette ; les **opérations cessent d'être un
> axe** sans cesser d'exister.
>
> **Tout le reste de cet ADR reste en vigueur** : le régime jugée / dérivée, le
> portage du type par l'arête `(requête, source, cible)`, le champ `source` de
> `Judgment`, la dérivation depuis le graphe témoin `G₀`, la règle de tri
> *enregistrer ce qui a coûté une lecture*, et ~~la réserve sur la ventilation
> (restreindre les qrels change `R`, donc la coupe)~~ — **cette dernière est
> dissoute le 2 août 2026** avec le retrait de `nDCG@R`
> ([#14](https://github.com/left-eyebr0w/murphy/issues/14), voir *Conséquences*).
> L'analyse des trois
> défauts d'ADR-009 reste valide — ADR-033 la prolonge, il ne la contredit
> pas.

## Contexte

ADR-009 fixe quatre types d'action — `texte_applicable`,
`jurisprudence_sur_question`, `known_item`, `graph_hop` — et pose un « axe
difficulté orthogonal ». La préparation de B-08 (golden-set v1) a mis trois
défauts au jour.

**1. L'axe difficulté est ininterprétable.** Étiqueter une requête *facile* ou
*difficile* enregistre une impression, non un fait : le seuil n'est pas
constatable, deux annotateurs ne le posent pas au même endroit. Surtout,
l'étiquette **absorbe la question qu'elle prétend documenter** — quand le score
s'effondre sur les requêtes « difficiles », « c'était difficile » n'explique
rien. Ce qui est légitime n'est pas un *degré* mais une **opération** : une
requête n'est pas difficile, elle exige une opération que d'autres n'exigent
pas (complexe, non compliquée).

**2. Les quatre types ne sont pas homogènes.** Trois décrivent *ce que
l'utilisateur veut* ; `graph_hop` décrit *comment la réponse est atteinte*.
Personne ne formule « je veux faire un saut de citation » : on veut la
jurisprudence sur une question, et il se trouve que la réponse exige une
traversée. `graph_hop` est une propriété constatable de la paire, pas une
intention.

**3. Le type ne peut pas être une propriété de la requête.** Une même question
appelle un article *et* une décision, parfois le même document par deux chemins
différents. Contraindre une requête à un type unique force un choix arbitraire
et perd l'information.

## Décision

### Deux axes explicites

| Axe | Porté par | Cardinalité | Nature |
|---|---|---|---|
| **Intention** | la requête | une seule | ce que l'utilisateur veut |
| **Opérations** | l'arête `(requête, source, cible)` | **plusieurs** par requête | comment chaque cible est atteinte |

**L'axe difficulté est supprimé.** Ce qu'il visait est repris par l'axe
opérations, qui est constatable.

### Le type est porté par le triplet `(requête, source, cible)`

L'unité typée n'est ni la requête ni la paire, mais le **triplet**. `source`
est **toujours un document du corpus** ; elle est vide quand la cible est
atteinte directement. Le terme intermédiaire est ce qui rend l'opération
**constatable plutôt que déclarée** : `source` vide = accès direct, `source`
renseignée = il a fallu passer par un document, et on sait lequel.

**Les opérations ne sont pas exclusives.** Une requête porte autant
d'opérations qu'elle a d'arêtes ; deux documents peuvent être liés par
plusieurs opérations à la fois. La non-exclusivité n'est pas une règle ajoutée :
elle découle du portage par l'arête.

### Les huit opérations (liste plate)

| # | Opération | Constat | Régime |
|---|---|---|---|
| 1 | `texte_applicable` | La cible (article) régit la situation décrite | jugée |
| 2 | `jurisprudence_applicable` | La cible (décision) régit la situation décrite | jugée |
| 3 | `definition` | La cible définit un terme employé par la requête ou la `source` | jugée |
| 4 | `known_item` | La requête **désigne** la cible (n°, ECLI, parties, date, intitulé) | dérivée (requête) |
| 5 | `graph_hop` | `source` non vide **et** arête `source → cible` dans le graphe | dérivée (graphe) |
| 6 | `contexte_structurel` | Arête `contains` entre `source` et cible | dérivée (graphe) |
| 7 | `succession_temporelle` | Arête `succeeded_by` entre `source` et cible | dérivée (graphe) |
| 8 | `fondement_textuel` | La `source` (décision) cite la cible (article) comme fondement | dérivée (graphe) |

`jurisprudence_sur_question` (ADR-009) devient **`jurisprudence_applicable`** :
la cible ne se contente pas de traiter la même question, elle **régit** la
situation décrite. Fait système avec `texte_applicable` — les deux répondent à
« qu'est-ce qui s'applique à ma situation ? », l'une par la norme, l'autre par
la jurisprudence.

**`succession_temporelle` ne rouvre pas l'exclusion d'ADR-009.** Cette
exclusion vise la **vigueur temporelle comme capacité produit** (servir la
bonne version à l'utilisateur) ; l'opération 7 type une arête en
**évaluation**, à partir des `succeeded_by` déjà minées. Deux objets
distincts : l'exclusion produit reste entière.

### Régime : jugée / dérivée

**Jugée** = coûte une lecture, entre dans l'artefact gelé. **Dérivée** =
calculée depuis le champ `source`, les arêtes du graphe ou le texte de la
requête ; **jamais annotée, jamais ingérée en base** — abstraite et recalculée
à la demande (ADR-031).

Cinq des huit opérations sont dérivées : le portage par l'arête a pour effet
de **transformer la majorité de la typologie en calcul**. La surface
d'annotation se réduit aux trois opérations sémantiques.

### Les opérations dérivées du graphe se calculent sur le graphe témoin

Quatre opérations (5–8) dépendent du graphe. Si le graphe varie d'une
expérience à l'autre, **la stratification varie avec lui** : on comparerait des
configs dont les strates ne sont pas définies pareil — l'instrument de mesure
suivrait l'objet mesuré. La dérivation se fait donc **toujours depuis le graphe
témoin épinglé** (ADR-031), jamais depuis le graphe de la config sous test. Le
rapport trace la version de graphe ayant servi à la dérivation, comme
`guide_version` trace la dérivation des grades.

### Ce que le golden-set enregistre

Application de la règle d'ADR-028 étendue : *enregistrer ce qui a coûté une
lecture, dériver le reste*. Le test de tri est opérationnel — **« si je change
d'avis là-dessus, dois-je rouvrir les documents ? »** Si oui, c'est une
observation (couche gelée) ; si non, c'est une étiquette (couche dérivée,
versionnée à part).

Ce n'est **pas** la distinction fait/opinion : `q1` (« même question de
droit ? ») est un jugement, non un constat. La ligne de partage est *jugement
qui a exigé de lire* contre *étiquette qui n'a exigé que de choisir un
découpage*. Les deux sont subjectifs ; un seul est cher.

Conséquence directe : le **gel** d'E-P2-06 porte sur la couche d'observation
(jugements + provenance, avec leur hash) ; la couche de dérivation — typologie,
définition des strates — porte sa **propre version**. *Figé* et *révisable*
cessent de s'opposer parce qu'ils ne portent pas sur le même objet.

## Alternatives rejetées

- **Conserver un axe `difficulty`** : jugement d'intensité non falsifiable, qui
  absorbe la question qu'il prétend documenter.
- **Type porté par la requête** (ADR-009 tel quel) : force un type unique là où
  une question appelle légitimement plusieurs natures de réponse.
- **Type porté par la paire `(requête, cible)`** : sans terme intermédiaire,
  la traversée redevient une affirmation invérifiable au lieu d'être lue sur la
  structure.
- **Deux niveaux d'opérations** (génériques × spécifiques au droit) : liste
  plate préférée — la hiérarchie serait un découpage de plus à défendre, sans
  gain diagnostique.
- **`interpretation`** (la cible interprète la `source`) : l'intersection
  texte + jurisprudence qu'elle visait survit par la non-exclusivité (une
  requête porte les deux arêtes). Ce qu'on perd est la *raison* du lien, qui se
  dégrade en `graph_hop` — troc accepté, c'était la seule « jugée » structurelle
  plutôt que sémantique.
- **`analogie`** : « analogue » est un jugement d'intensité déguisé, sans seuil
  constatable — le défaut même de l'axe difficulté.
- **`contradiction`** : heurte ADR-005 de front (pertinence « topique, non
  directionnelle » — un arrêt contraire bien en point est un 3). L'admettre
  rouvrirait cette décision.

## Conséquences

- **E-P2-07 est révisée.** Son critère (« champ type d'action présent sur 100 %
  des *requêtes* ; les 4 strates non vides ») n'a plus de référent unique. Le
  nouveau critère porte sur les arêtes et sur la présence d'une intention par
  requête (`EXIGENCES_v0.md`).
- **Le scorer passe au pluriel.** `QueryMetrics.action_type` est un
  `str | None` et `report.py` reçoit un `dict[str, str]` — un type par
  `query_id`. Le portage par l'arête impose de revoir ces deux signatures.
  L'**injection** reste le bon design (le scorer demeure agnostique du contenu
  de la taxonomie) ; seule la cardinalité change.
- ⛔ ~~**La ventilation par opération n'est pas une sous-partie de la métrique
  globale.**~~ **Réserve dissoute le 2 août 2026**
  ([#14](https://github.com/left-eyebr0w/murphy/issues/14)). Elle disait : nDCG@R
  se calcule sur le classement entier et `R` dépend du nombre de documents
  pertinents, donc restreindre les qrels aux arêtes d'un type **change `R`, donc
  la coupe** — d'où *« deux ventilations ne se comparent pas entre elles, et
  aucune ne se compare à l'agrégat »*.

  **Cette gêne était entièrement un effet de la normalisation par `R`.** `nDCG@R`
  est retiré ; la métrique de comparaison est **RBP(`p`) + résidu**
  ([ADR-007](ADR-007-metrique-rbp-residu.md)), qui se moyenne par cas **sans
  dénominateur global**. Une ventilation redevient donc une **moyenne sur un
  sous-ensemble**, directement comparable à l'agrégat et aux autres
  ventilations. Le rapport n'a plus d'avertissement à porter — il a en revanche
  un résidu à publier avec chaque moyenne, ventilée comprise, et la **porte du
  résidu** s'applique à une ventilation comme à l'agrégat (un intervalle d'écart
  contenant zéro n'admet aucun test — et il est **plus large** sur un
  sous-ensemble, ce qui est le bon comportement).
- **Le modèle de requête reste à créer** — aucune classe `Query` n'existe dans
  `eval/`. L'axe intention est du terrain vierge : aucune migration.
- **`Judgment` (ADR-008) gagne le champ `source`**, nullable. Les opérations
  dérivées n'y sont pas stockées.
- La liste des opérations reste **révisable sans migration** (ADR-009) — et
  cette fois la propriété est *fondée* : la typologie ne vit pas dans les
  qrels, donc un changement de découpage ne coûte aucune ré-annotation. Deux
  taxonomies peuvent être rejouées sur les **mêmes** jugements et comparées.

## Références

ADR-004 (unité document) · ADR-005 (cascade q1–q3, pertinence topique) ·
[ADR-007](ADR-007-metrique-rbp-residu.md) (RBP + résidu ; dissout la réserve de
ventilation) · ADR-008 (format ; champ `source`) ·
ADR-009 (amendé ici) · ADR-028 (régimes de vérification) · ADR-029
(circularité) · ADR-031 (graphe témoin) · `EXIGENCES_v0.md` E-P2-06/07 ·
`BACKLOG.md` B-08
