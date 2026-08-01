# B-08 — Prior de pondération : notes de travail et prompts

> ## ⛔ SANS OBJET (1er août 2026)
>
> Ce document dérive un vecteur de pondération **D₁** sur les **douze strates**
> de `GOLDEN-SET.md` §6. Les strates ne survivent pas comme cadre
> d'échantillonnage, et D₁ tombe avec elles. Rien ici n'est à appliquer.
> Conservé le temps que la carte
> [Golden-set v1](https://github.com/left-eyebr0w/murphy/issues/1) statue sur ce
> qui remplace le cadre d'échantillonnage — voir ADR-034 §1 (le paradigme
> *contenu* devient un second instrument, non un cadre).

> Document de travail (`WIP/`), **éphémère par conception** — compagnon de
> [B-08-cadrage.md](B-08-cadrage.md), dont il détaille l'**étape 1** du
> protocole de génération des requêtes. Il vit le temps de l'analyse et
> disparaît quand le tableau de poids est consigné.
>
> Écrit **pour le porteur**, à lire à côté du notebook où sont déposés les
> trois PDF de statistiques judiciaires. Ce qui doit survivre part
> ailleurs : le tableau de poids dans le cadrage B-08, une règle de
> méthode en ADR.

## 1. Ce qu'on cherche exactement

**Un tableau `matière → poids`, daté, sourcé, versionné.** Rien d'autre.
Pas une étude du contentieux français : une clé de pondération défendable,
tenant sur une page.

Il sert à deux choses, et à deux choses seulement :

1. **Aiguiller la récolte** — décider par où commencer et combien de
   questions viser par matière ;
2. **Pondérer les rapports** — publier, à côté de la macro-moyenne, une
   moyenne pondérée par la structure réelle du contentieux.

> ⚠️ **Rappel du principe qui commande tout** (cadrage B-08, étape 1) :
> **les poids sont un paramètre de rapport, pas une contrainte
> d'échantillonnage.** On échantillonne pour le pouvoir diagnostique (un
> plancher par case de la matrice `matière × opération`), on pondère au
> moment du rapport. Conséquence directe : changer d'avis sur la
> représentativité devient un changement de **classe 1** au sens
> d'ADR-032 — re-notation seule, zéro re-récupération. Un poids gravé
> dans l'échantillonnage, lui, est irréversible sans réécrire le jeu.

**Corollaire pratique** : ne cherchez pas la précision. Un poids à ±3 points
ne change rien à une décision d'allocation sur 50 questions. Ce qui compte,
c'est l'**ordre de grandeur** et le fait que le chiffre soit **traçable**.

## 2. Hygiène : cette étape est sans risque de contamination

Elle porte sur des **matières**, jamais sur des documents. Aucun contact
avec une cible, donc **aucun risque P-01** (requête-décalque) : c'est
précisément pourquoi elle peut se faire en premier, à découvert, avant le
scellement de `questions_brutes.jsonl`.

Rien de ce qui est lu ici ne doit servir à **rédiger** une question. Les
statistiques disent *combien* de questions par matière, jamais *lesquelles*.

## 3. Ce que chaque source sait — et ne sait pas

| Source | Ce qu'elle capte | Ce qu'elle ne capte pas |
|---|---|---|
| *Chiffres clés de la Justice* | La vue de synthèse, les grands équilibres | Le détail par nature d'affaire — c'est une plaquette |
| *Références Statistiques Justice* | Le détail fin, les tables ventilées | Rien de l'administratif |
| *Chiffres clés de la justice administrative* | Le contentieux devant TA / CAA / CE | Le judiciaire ; sa nomenclature est **disjointe** de l'autre |

**Le biais commun, et il est structurel** : ces trois documents mesurent
le **litige porté devant un juge**. Ils sur-pondèrent donc massivement le
conflictuel et ignorent le besoin d'information pur — personne ne saisit
un tribunal pour connaître son délai de rétractation, et pourtant c'est
une requête parfaitement légitime pour Murphy.

C'est pour cela que le prior final **n'est pas** la distribution
judiciaire brute : il est un arbitrage entre elle et la volumétrie
d'autocomplétion (étape 2 du protocole), dont le biais est opposé.
L'arbitrage se consigne — c'est lui, l'argument de représentativité.

## 4. Prompts, par phase

Ordre volontaire : **cartographier, puis chiffrer, puis confronter**.
Chiffrer avant d'avoir la nomenclature produit des regroupements inventés.

### Phase A — Cartographier (ne demandez encore aucun chiffre)

```
Inventorie toutes les tables et figures de ces documents qui contiennent une
répartition d'affaires par matière, par nature d'affaire ou par contentieux.
Pour chacune, donne uniquement : intitulé exact, page, document source,
juridiction couverte, année de référence, unité de compte (affaires nouvelles,
terminées, ou stock), et l'effectif total. Ne donne aucune ventilation détaillée
à ce stade.
```

```
Pour la table [intitulé], reproduis la nomenclature complète : la liste exacte
et exhaustive des libellés de matières employés, dans l'ordre du document, sans
les regrouper, sans les renommer, sans en omettre. Indique le niveau
hiérarchique de chaque libellé s'il y en a un.
```

```
Ces documents emploient-ils la même nomenclature de matières ? Dresse un tableau
de correspondance entre la nomenclature du contentieux judiciaire et celle du
contentieux administratif. Signale explicitement les libellés qui n'ont aucun
équivalent dans l'autre nomenclature.
```

> La troisième est celle qui rapporte le plus. Judiciaire et administratif
> ne découpent pas le monde pareil ; toute addition naïve entre les deux
> est fausse. Mieux vaut le savoir avant de construire le tableau que
> pendant.

### Phase B — Chiffrer

```
Pour la table [intitulé], page [n], donne le tableau complet : libellé, effectif,
et part en pourcentage. Pour chaque pourcentage, précise s'il est LU dans le
document ou CALCULÉ par toi à partir de l'effectif et du total. Ne calcule rien
que tu ne puisses rattacher à un effectif figurant dans le document.
```

```
Quel est le périmètre exact de la table [intitulé] ? Précise : quelles
juridictions sont incluses, quelle année, et surtout ce qui est EXCLU du
dénominateur (référés, procédures gracieuses, injonctions de payer, affaires
non ventilées, « autres »). Cite le passage du document qui l'établit.
```

```
La somme des effectifs ventilés de la table [intitulé] est-elle égale au total
annoncé ? Si non, donne l'écart et son motif d'après le document.
```

> La deuxième et la troisième sont des **contrôles**, pas des questions de
> curiosité. Un pourcentage n'a de sens que rapporté à son dénominateur ;
> une catégorie « autres » à 18 % change complètement la lecture d'un
> tableau et ne se voit pas si on ne la cherche pas.

### Phase C — Traquer les pièges de lecture

```
Ces documents signalent-ils des ruptures de série, des changements de
nomenclature, des changements de périmètre, ou des précautions de lecture ?
Liste-les avec leur page. Inclus tout avertissement méthodologique, même en note
de bas de page.
```

```
Que disent ces documents des affaires qui n'arrivent pas devant un juge :
médiation, conciliation, modes alternatifs de règlement, non-recours,
désistements ? Y a-t-il des ordres de grandeur ? Cite les passages.
```

```
Y a-t-il des données sur l'aide juridictionnelle ventilées par matière, ou sur
les demandes d'information juridique reçues par les points-justice, maisons de
justice et du droit ou dispositifs équivalents ? Si oui, extrais-les.
```

> La deuxième et la troisième cherchent à **mesurer le biais du
> conflictuel**, pas à le contourner. Si le document donne un ordre de
> grandeur du non-recours ou du volume d'accès au droit, vous tenez un
> correctif chiffré au lieu d'un correctif à l'estime — et l'aide
> juridictionnelle est un signal de *demande de droit*, pas seulement de
> litige.

### Phase D — Synthétiser

```
À partir des seules tables que tu as extraites, propose un regroupement en 8 à
12 grandes matières couvrant l'essentiel du contentieux, judiciaire et
administratif confondus. Pour chaque regroupement : les libellés d'origine qui
le composent, l'effectif agrégé, la part, et les documents sources. Signale
tout libellé que tu n'as pas su rattacher.
```

```
Pour chaque ligne du tableau de synthèse, donne la référence précise : document,
page, intitulé exact de la table. Si une valeur provient d'une agrégation de
plusieurs tables, dis lesquelles.
```

> Le regroupement est **votre** décision, pas celle du notebook — la
> proposition ne sert qu'à ne pas partir de la page blanche. Le second
> prompt produit la colonne « source » du livrable, qui est ce qui rend
> le prior défendable un an plus tard.

## 5. Ce que le notebook ne peut pas faire

**Confronter la distribution au corpus Murphy.** Le notebook ignore ce que
contiennent LEGI et les cinq bases de jurisprudence. Une matière qui pèse
lourd au contentieux mais dont les sources sont maigres dans le corpus
produirait des questions sans cible — donc jetées (protocole D-01 :
**jeter, jamais reformuler**).

Ce comptage se fait **côté Murphy**, séparément : volumétrie par code pour
LEGI, par base pour la jurisprudence. C'est une petite tâche indépendante,
à faire avant de figer les poids ; elle alimente la colonne « couverture
corpus » du livrable.

## 6. Le livrable

Une table, à consigner dans le cadrage B-08 :

| Matière | Part judiciaire | Part administrative | Couverture corpus | **Poids retenu** | Écart assumé | Source (doc, page, table) |
|---|---|---|---|---|---|---|

Deux colonnes méritent qu'on s'y arrête :

- **Poids retenu** — l'arbitrage, incluant le correctif de biais
  conflictuel. Il n'a aucune raison d'égaler la part judiciaire, et il ne
  le fera pas.
- **Écart assumé** — l'écart entre le poids retenu et la distribution
  observée, **avec son motif**. On ne le corrige pas : on le déclare. Un
  écart déclaré est une limite connue ; un écart tu est un défaut.

Puis, pour passer aux questions : **plancher par case, puis
proportionnel**. Chaque matière retenue reçoit un minimum de questions
(sans quoi le stratum ne dit rien au rapport), le reste s'alloue selon les
poids. Les poids ne sont *pas* la clé d'allocation directe.

## 7. Le seul vrai risque de l'exercice

**Un chiffre halluciné dans le prior est invisible en aval.** Il ne
produira aucune erreur, aucun test rouge, aucune incohérence — il
déplacera silencieusement l'allocation des questions et l'argument de
représentativité reposera sur du vide.

> **Règle** : tout chiffre qui entre dans le tableau final est **vérifié
> à l'œil sur la page du PDF**. Le notebook sert à *trouver* la table et à
> en dégrossir la lecture, jamais à *attester* une valeur. C'est
> exactement la frontière d'ADR-028 : la machine produit un candidat,
> l'humain tranche — appliquée ici à une lecture documentaire.

C'est aussi pourquoi la phase D exige la référence page par ligne : la
vérification doit coûter quelques minutes, pas une relecture intégrale.

## 8. Ce que ce document ne décide pas

- **La taille du jeu** (D-03) — le prior donne des proportions, pas un
  total. Dédramatisé par ADR-032 : commencer petit et profond est sans
  risque.
- **La liste des matières retenues** — elle sort de l'analyse, pas d'ici.
- **La formulation des questions** — étape 2 du protocole, et
  scrupuleusement séparée de celle-ci.

## 9. Références

[B-08-cadrage.md](B-08-cadrage.md) (protocole complet, pièges P-01 à P-04) ·
ADR-005 (guide d'annotation) · ADR-028 (régimes de vérification) ·
ADR-030 (matrice `matière × opération`) · ADR-032 (classes de changement,
re-notation) · `EXIGENCES_v0.md` E-P2-06, E-P2-07
