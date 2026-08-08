# B-08 — Cadrage du golden-set v1

> ## ⚠️ Cadrage du 22 juillet 2026 — largement dépassé
>
> Ce document précède ADR-033 et ADR-034. Le cadrage courant de B-08 vit sur la
> carte [Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1),
> et atterrira en **ADR-036**. À lire comme une trace, pas comme un plan.

> ## ⛔ Ce statut est faux — constaté le 7 août 2026 ([#13](https://github.com/left-eyebr0w/murphy/issues/13) §8)
>
> **Ce document n'est pas éphémère : il est portant, et il ne peut pas être supprimé en
> l'état.** Il est le **seul lieu de définition de P-01 à P-04** (§*Pièges de construction*),
> que `GOLDEN-SET.md` §2.3 invoque **par sigle**, et **six documents durables le citent** —
> `GOLDEN-SET.md`, ADR-032, ADR-035, `ADR/INDEX.md`, `recherche/requetes-generees.md`,
> `droit/taxomonie/SOURCES.md`. Son homonyme `B-08-generation-requetes.md`, lui, avait
> **zéro** lien durable entrant : il a été supprimé le 7 août, et **confondre les deux
> ferait le dégât**.
>
> **Obligation d'écriture ouverte, non une décision** : **P-01 à P-04 migrent en ADR-036**,
> et `GOLDEN-SET.md` §2.3 se repointe. Ce fichier ne redevient supprimable **qu'après** cette
> migration. ⚠️ **P-01 change de statut en migrant** : sa portée déclarée (`known_item`,
> `graph_hop`) et son symptôme annoncé (« bon marché à peupler ») désignent **exactement le
> design retenu pour la v1** — il se requalifie de **piège en propriété déclarée**, sauf sur
> `concept_vers_instance`, P-02 traitant déjà son observation.
>
> *Rédaction antérieure, conservée pour la trace :* « Document de travail (`WIP/`),
> **éphémère par conception** : il vit le temps de B-08 et disparaît à sa clôture. Ce qui
> doit survivre part ailleurs — une décision en ADR, une dette en `BACKLOG.md` §4, un statut
> en `STATUS.md`. »
>

> Session de cadrage du 22 juillet 2026, en amont de toute écriture de
> code. Consigne ici ce qui a été établi **et n'a pas trouvé place**
> dans ADR-030 / ADR-031 : l'analyse par opération, les pièges de
> construction, ce qu'implique le corpus entier, et les décisions
> restées ouvertes. Redondance assumée avec les ADR quand elle sert
> l'intelligibilité.

## 1. Où en est B-08

**Tirable** (B-01 et B-02 ✅ : identité canonique croisée, `doc_id` LEGI
stable — sans eux, annoter des `doc_id` n'aurait aucun sens). **Alimente
B-11.** Sert E-P2-06 et E-P2-07, les deux de régime **humain** (ADR-028) :
aucun test vert ne les clôt, la preuve consigne **qui a validé et quand**.

Acté ce jour, et sorti d'ici : **ADR-030** (deux axes, type porté par
l'arête, huit opérations), **ADR-031** (graphe témoin, triplet
`(W, G, R)`, passage témoin) et **ADR-032** (gel par version,
comparabilité par re-notation). E-P2-07 réécrite, E-P2-06 et E-P2-10
précisées.

Ce qui **reste** au périmètre B-08 : le jeu lui-même, le guide
d'annotation (ADR-005 — les trois questions **avec cas limites**, écrit
pour servir tel quel en alpha ph.2, donc livrable à durée de vie longue),
et le gel versionné avec hash.

## 2. La méthode : construire sur un problème *wicked*

Le constat qui a structuré la session : **la typologie ne peut pas être
validée avant d'être utilisée**. Il n'existe pas de test qui dirait « ce
découpage est le bon » — le découpage *est* une prise de position sur ce
que le produit doit savoir faire. C'est ce qu'ADR-028 nomme déjà en
régime humain : *produire l'oracle, ce serait répondre à la question*.

Deux échecs symétriques guettent, et E-P2-06 (**hash de gel**) pousse
structurellement vers le premier :

| Échec | Mécanisme |
|---|---|
| **Figer trop tôt** | Le choix devient trop cher à changer, on le défend au lieu de l'éprouver |
| **Rester fluide** | Rien n'est jamais mesuré, aucune comparaison n'est possible |

**La règle retenue** — le projet la pratiquait déjà deux fois sans
l'avoir nommée :

> **Enregistrer ce qui a coûté une lecture. Dériver tout le reste au
> moment du rapport.**

Test de tri, opérationnel : *« si je change d'avis là-dessus, dois-je
rouvrir les documents ? »* Si oui → observation, couche gelée. Si non →
étiquette, couche dérivée versionnée à part.

Ce n'est **pas** la distinction fait / opinion : `q1` (« même question de
droit ? ») est un jugement, non un constat. La ligne est *jugement qui a
exigé de lire* contre *étiquette qui n'a exigé que de choisir un
découpage*. Les deux sont subjectifs ; **un seul est cher**.

**Les deux précédents du projet** (à citer, ils fondent la règle) :

| Précédent | Couche coûteuse | Couche révisable |
|---|---|---|
| ADR-005 | `q1/q2/q3` (avoir lu et répondu) | La dérivation du `grade` |
| Scorer | Les jugements | La taxonomie (`action_types` **injecté**, [report.py:13](../../../eval/src/murphy_eval/core/services/report.py#L13)) |

**Ce que la règle rend, et qui est rare sur un problème wicked.** Rittel
pose qu'on n'a pas droit à l'essai-erreur : chaque tentative engage. Ici,
la typologie vivant hors des qrels, on peut **rejouer deux taxonomies sur
les mêmes jugements et comparer**. Ça ne résout pas le problème wicked —
ça rend les tentatives **réversibles et comparables**, ce qui est le
maximum accessible.

Corollaire qui dissout la tension gel / révisabilité : le **gel porte sur
la couche d'observation** (jugements + provenance, avec leur hash) ; la
couche de dérivation porte sa **propre version**. *Figé* et *révisable*
ne portent pas sur le même objet.

## 3. Ce que mesure chaque opération

Analyse conservée ici : ADR-030 fixe la liste, pas l'intention
diagnostique de chaque item.

| Opération | Ce qu'elle mesure | Régime |
|---|---|---|
| `texte_applicable` | Le pont **fait → norme** (registre profane vers registre normatif) | jugée |
| `jurisprudence_applicable` | Le pont **fait → jurisprudence** | jugée |
| `definition` | Résoudre le vocabulaire d'entrée | jugée |
| `known_item` | **Plancher** d'identification — voir §4 | dérivée (requête) |
| `graph_hop` | La valeur de l'augmentation Neo4j | dérivée (graphe) |
| `contexte_structurel` | **Rien de positif** — sert à *neutraliser* | dérivée (graphe) |
| `succession_temporelle` | Servir la bonne version | dérivée (graphe) |
| `fondement_textuel` | Remonter du cas à la norme | dérivée (graphe) |

**Partage interne aux dérivées**, qui compte pour ADR-031 : quatre
dépendent du **graphe** (`graph_hop`, `contexte_structurel`,
`succession_temporelle`, `fondement_textuel`) et bougent si le graphe
bouge ; `known_item` dépend du **texte de la requête** et reste stable
quoi qu'il arrive au graphe.

**Écartés, et pourquoi** (rappel — détail en ADR-030) :
`interpretation` (l'intersection texte + jurisprudence survit par la
non-exclusivité ; on ne perd que la *raison* du lien, dégradée en
`graph_hop`), `analogie` (jugement d'intensité déguisé), `contradiction`
(heurte la pertinence « topique, non directionnelle » d'ADR-005).

## 4. Pièges de construction identifiés

> ⚠️ **Section portante — c'est elle qui interdit la suppression du fichier.** Seul lieu de
> définition de P-01 à P-04, cités par sigle ailleurs. **Migre en ADR-036**, et deux entrées
> y arrivent modifiées :
>
> - **P-01 se retourne** — de *piège* il devient **propriété déclarée** de la v1
>   ([#13](https://github.com/left-eyebr0w/murphy/issues/13) §4). Sa portée et son symptôme
>   décrivent le design retenu. Le décalque reste un **défaut** sur le seul mécanisme
>   *besoin d'abord*, `concept_vers_instance` — et il siège dans la **dérivation**, pas dans
>   la sélection.
> - ⛔ **P-04 raisonne sur `nDCG@R`, métrique retirée** le 2 août
>   ([#14](https://github.com/left-eyebr0w/murphy/issues/14)). **Son fond survit et se
>   renforce** : la complétude repose entièrement sur le pooling, et c'est précisément
>   pourquoi tout score se publie désormais en **`score + résidu`** — mais l'énoncé ci-dessous
>   est à réécrire, pas à recopier.
>
> ⛔ **Vocabulaire mort dans le tableau** : `known_item`, `graph_hop` et `texte_applicable`
> sont des **opérations** d'ADR-030 sous leurs noms de juillet ; la liste des mécanismes est
> arrêtée à **sept**, et `multi_hop` a été **scindé** le 5 août — un document antérieur qui
> l'emploie désigne le mécanisme à **un** saut.

| ID | Piège | Portée |
|---|---|---|
| P-01 | **Requête-décalque.** Fabriquer la requête *à partir* de la cible produit une requête qui recopie le document : on mesure alors la capacité du moteur à retrouver un texte par ses propres mots, pas une performance de récupération. Structurellement le même défaut que le `contains` de B-07 — une paire triviale qui gonfle le score. **Le fait qu'un type soit bon marché à peupler en est souvent le symptôme.** | `known_item`, `graph_hop` |
| P-02 | **Confondre plancher et performance.** `known_item` teste qu'un moteur ne rate pas un document que l'utilisateur **nomme** : un échec y est disqualifiant, mais un succès ne prouve rien. À ne jamais agréger comme s'il pesait autant que les opérations jugées. | Analyse des résultats |
| P-03 | **Dimensionner par le coût d'annotation.** Les deux opérations les moins chères (`known_item`, `graph_hop`) sont celles qui portent le moins de valeur produit ; les plus chères (`texte_applicable`, `jurisprudence_applicable`) sont celles dont dépend l'utilité réelle. Laisser la commodité décider de la taille des strates inverserait la priorité. | Construction du jeu |
| P-04 | **Complétude des qrels — un levier a disparu.** ADR-007 fondait la robustesse de nDCG@R sur « le pooling **et les citations minées** » ; ADR-029 ayant retiré les citations comme source de qrels, la complétude repose **entièrement sur le pooling et sur B-08**. Corrigé dans ADR-007 ce jour ; conséquence à porter dans la construction du jeu. | Construction du jeu |

## 5. Ce qu'implique « tout le jeu de données »

Le golden-set portera sur le corpus entier : **1121 nœuds** — `Article`
384, `Document` 352, `Section` 287, `Texte` 98.

**C'est petit pour de l'IR, et c'est une bonne nouvelle.** Sur un corpus
de millions de documents, on ne peut pas savoir si l'on a trouvé *tous*
les documents pertinents — d'où le pooling, qui est un pis-aller. Sur
1121, le **rappel devient réellement mesurable** : un humain peut
examiner l'ensemble des candidats plausibles d'une requête. Le garde-fou
de complétude (P-04) redevient tenable **par la taille du corpus**, pas
seulement par le pooling.

**Le pooling change alors de rôle** : de levier de complétude, il devient
**ordonnanceur de l'effort** (juger d'abord l'union des top-k, compléter
ensuite). ADR-032 achève ce déplacement — un document jamais jugé n'est
plus un défaut définitif du jeu, mais **une dette rattrapable** en
version suivante.

**Espace des cibles — décision prise : ne pas restreindre.** `Section`
(287) et `Texte` (98) ne sont pas des unités de citation au sens
d'ADR-004 (« ce qu'un juriste cite » = la décision ou l'article) : ils
pèsent **385 sur 1121, un tiers du corpus**. Deux voies existaient —
restreindre l'espace des cibles, ou observer d'abord. **Retenu :
observer.** La ventilation est de l'observation, la restriction est une
décision ; observer avant de décider est le bon ordre — c'est la leçon de
B-07, où le run réel a montré ce que les tests ne voyaient pas.
Conséquence : si les `Section` ne remontent jamais, la question se clôt
sans avoir rien restreint ; si elles remontent, on aura un **fait**.

**La ventilation par base est déjà exigée** — ADR-004 : « métriques
document rapportées **par base** en plus de l'agrégé ». Techniquement
gratuite : `report.py` ventile par un dictionnaire **injecté**, la même
mécanique accepte n'importe quelle clé.

> ⚠️ **Rappel valable pour toute ventilation** (ADR-030, ADR-007) :
> restreindre les qrels à un sous-ensemble **change R, donc la coupe
> adaptative**. Une ventilation est une **mesure distincte, à
> dénominateur propre** — elle ne se compare ni à l'agrégat, ni à une
> autre ventilation. À énoncer dans les rapports.

## 6. Obsolescences corrigées ce jour

Six passages, cinq fichiers — tous des survivances d'ADR-029 (strate 2
rétrogradée) non propagées.

| Fichier | Correction |
|---|---|
| `PROGRAM.md` | Strate 2 de la table · « Conséquence » de la baseline · contrat P1→P2 |
| `VERSIONS.md` | Périmètre **In** de la v0 |
| `STATUS.md` | Libellé B-03 |
| `ADR-007` | Conséquence « complétude des qrels » — voir **P-04**, le plus sérieux |
| `archives/CADRAGE_evaluation` | En-tête d'archive listant les points périmés |

**Le cas de l'archive mérite mémoire.** `CADRAGE_evaluation` n'était
marquée **nulle part** comme non normative, et son §3.3 recommande
l'« amorçage par le graphe de citations » pour pré-remplir les qrels —
soit précisément ce qu'ADR-029 a explicitement écarté. Un en-tête a été
ajouté plutôt qu'une réécriture : une archive doit rester lisible comme
le raisonnement qu'elle était. Restent valides dans ce document : le
reframing IR (§0), le **pooling** (§3.3), le **garde-fou
représentativité** du synthétique (§8).

## 7. Décisions ouvertes

| ID | Décision | Bloquant pour |
|---|---|---|
| ~~D-01~~ | **Méthode de génération des requêtes — ✅ CLOSE par [ADR-037](../../product/ADR/ADR-037-provenance-authoring.md)** (7 août 2026, ticket [#13](https://github.com/left-eyebr0w/murphy/issues/13)). *« La frontière doit être écrite »* : **elle l'est**. Et la réponse est double. **(a)** La question posée ici — *l'emploi hors ligne contrevient-il à E-T-01 ?* — reçoit **« E-T-01 n'en dit rien »**, pas « il l'autorise » : sa source ADR-016 gouverne le couplage *runtime*, jamais la **provenance d'authoring**, qui est un autre objet. **(b)** Un LLM hors ligne entre en v1 mais **pour un autre acte que celui envisagé ici** — il propose des **notions**, jamais des textes, et sur `concept_vers_instance` seul ; le porteur rédige. ⛔ *doc2query / InPars / Promptagator sont hors sujet* : le protocole de génération de textes est mort **par inversion de prémisse** — sur quatre des cinq mécanismes de la v1, on **a** le document sous les yeux. | ~~Démarrage effectif de B-08~~ |
| ~~D-02~~ | **Gel vs extensibilité — ✅ CLOSE par ADR-032** (voir §7 bis). ⚠️ *Le mot `gel` est lui-même sorti du vocabulaire le 2 août 2026 — trois hashes identifient au lieu de sceller ; le titre et le §1 d'ADR-032 sont périmés, sa mécanique survit.* | — |
| ~~D-03~~ | **Taille du jeu — ✅ CLOSE par [#11](https://github.com/left-eyebr0w/murphy/issues/11)** (1er août 2026) : dérivation **ascendante**, plancher **30 cas/mécanisme** par la règle de trois, **v1 = 150 cas** (dont 30 jugés), `N_q ≥ 180`. La consigne *« ne pas trancher par le coût »* a **tenu** — et [#20](https://github.com/left-eyebr0w/murphy/issues/20) l'a confortée en figeant la **largeur** sur les seuls critères insensibles au budget, la **profondeur** absorbant l'incertitude. | ~~Construction~~ |

## 7 bis. Le modèle de versionnement (résolution de D-02)

Détail en **ADR-032** ; l'essentiel, parce qu'il commande la façon de
travailler au quotidien.

**Le point de départ était une fausse contrainte** : chercher à rendre
les versions successives du golden-set compatibles entre elles. La seule
façon d'y parvenir serait de n'autoriser que des ajouts, jamais de
corrections — ce qui interdit exactement ce qui doit pouvoir arriver
(corriger un grade, réviser le guide) et **ossifie** l'artefact.

**La sortie** tient à une propriété structurelle déjà acquise : **un run
ne dépend pas des qrels**. Un run est `question → documents ordonnés`,
sans aucun jugement de pertinence ; le score est une fonction pure
`(run, qrels)`. Donc quand les qrels changent, on ne perd rien — on
**re-note** tous les runs archivés contre la version courante et l'on
compare de nouveau à qrels constantes.

| Ce qu'on retient | |
|---|---|
| Gel | Par **version**, pas sur la suite des versions (git : chaque commit figé, le dépôt vit) |
| Comparabilité entre versions | **Aucune**, et on ne la cherche pas |
| Comparabilité dans le temps | Par **re-notation** de l'historique |
| Toute mesure | **Nomme sa version de qrels** — un chiffre sans version n'est pas interprétable |

**Coût, seul point de vigilance** — trois classes de changement, une
seule chère :

| Changement | Re-récupération ? | Historique comparable ? |
|---|---|---|
| Corriger un grade, réviser le guide | Non | **Oui** |
| Juger plus de documents sur une question existante | Non | **Oui** |
| **Ajouter une question** | **Oui** | Non, sauf rejeu des configs |

Rejouer le processus n'est **pas un obstacle** (position du porteur,
22 juillet 2026), mais reste une dépense à minimiser : **ajouts de
questions par lots**, à des moments choisis ; corrections de jugement au
fil de l'eau.

> ⚠️ **Garde-fou.** Une modification de qrels ne se justifie **jamais**
> par un résultat de run. Re-noter parce qu'une config a perdu, c'est
> ajuster l'étalon à l'issue souhaitée — la circularité de mesure
> (ADR-031 §5) revenue par la porte du temps. « J'ai relu, ce grade 1 est
> un 2 » est recevable ; « cette config remonte ce document, il doit être
> pertinent » ne l'est pas.

**Ce que ça change pour la construction** : geler la v1 **sans chercher à
l'anticiper parfaitement**, et commencer **petit et profond**. Les
erreurs se corrigent sans rien invalider.

## 8. Chantiers induits (hors périmètre B-08)

Consignés au `BACKLOG.md`, rappelés ici parce qu'ils **précèdent
matériellement** l'annotation :

- **Modèle de requête** — aucune classe `Query` n'existe dans `eval/`.
  Terrain vierge, donc aucune migration, mais il faut le schéma (intention,
  et le champ `source` sur `Judgment`) **avant** d'annoter.
- **Scorer au pluriel** — `QueryMetrics.action_type` est un `str | None`,
  `report.py` reçoit un `dict[str, str]` : un type par requête. L'injection
  reste le bon design ; seule la **cardinalité** change.

- **Re-notation de l'historique en une commande** (ADR-032) — sans elle, le
  modèle de versionnement n'est pas praticable. Avec, au plus tard, **B-11**.

Et deux dettes voisines, sans lien avec B-08 mais à ne pas perdre :
**B-05 n'a pas de point d'entrée** (à solder en B-11) ; **`W` ne trace pas
le graphe** (traité par ADR-031, à poser avant B-13).

## 9. Références

ADR-004 (unité document, ventilation par base) · ADR-005 (cascade,
guide) · ADR-007 (coupe adaptative, complétude) · ADR-008 (format) ·
ADR-009 (amendé par ADR-030) · ADR-017 (strates) · ADR-027
(environnement d'évaluation) · ADR-028 (régimes) · ADR-029
(circularité) · **ADR-030** (typologie) · **ADR-031** (graphe témoin) ·
**ADR-032** (versionnement, re-notation) · `EXIGENCES_v0.md`
E-P2-06/07/10 · `BACKLOG.md` B-08, B-11
