# ADR-032 — Golden-set versionné : ~~gel par version~~, comparabilité par re-notation

**Statut** : Acté (22 juillet 2026, préparation de B-08) — **précise E-P2-06**
(gel), **précise E-P2-10** (reproductibilité), **prolonge ADR-029** (garde-fou
de circularité), **clôt D-02** (`WIP/B-08-cadrage.md`)

> ## ⛔ Le mot `gel` est périmé — 2 août 2026
>
> **Le titre et le §1 de cet ADR sont périmés.** Le mot **`gel` est sorti du vocabulaire**
> le 2 août 2026, en session de
> [#18](https://github.com/left-eyebr0w/murphy/issues/18) (§0) — sixième mot retiré par la
> carte [#1](https://github.com/left-eyebr0w/murphy/issues/1), après `cardinalité`,
> `D₁/D₂/D₃`, `N_j`, `registre` et la `carotte`.
>
> **Motif : le gel ne garantissait la validité de rien.** Un grade faux et gelé reste faux.
> Il promettait l'immuabilité, or l'immuabilité n'a jamais été le besoin — le besoin est de
> **pouvoir dire contre quoi on a mesuré**. Et geler exige de savoir d'avance ce qui mérite
> d'être scellé, ce que personne ne sait.
>
> **Remplacement : on ne gèle rien, on identifie tout.** Trois hashes portés par chaque run —
> `corpus` (sur les **identités canoniques de document**, donc *stable sous `W`*), `cas`,
> `qrels` ; deux runs sont comparables **ssi** leurs hashes sont égaux ; une version de
> collection est un triplet de hashes qu'on **nomme** et publie, l'acte étant **déclaré** et
> sans sémantique de mesure.
>
> ### Ce qui, dans cet ADR, **survit intégralement**
>
> - **§2 — la re-notation**, et c'est la pièce maîtresse : *un run ne dépend pas des qrels*,
>   le score est une fonction pure `(run, qrels)`, donc quand les qrels bougent on re-note
>   les runs archivés et **la comparabilité est entièrement restaurée, gratuitement**. Cette
>   propriété appartient au **scoring**, pas au gel, et lui survit sans retouche. La règle
>   opératoire qui en découle : **on ne cite jamais un chiffre d'un état antérieur, on
>   re-note.**
> - **§3** — toute mesure nomme l'état contre lequel elle a été prise (désormais : ses trois
>   hashes).
> - **§4 — les classes de changement**, mais **incomplètes** : la table n'a que des classes
>   *internes au jeu*. La **quatrième — le corpus bouge** (vague d'ingestion, ADR-003) — y
>   manquait, et c'est la seule qui exige **ré-ingestion *et* re-récupération**. #18 §0
>   l'ajoute, et rend la classe **dérivable** (par lequel des trois hashes a bougé) au lieu
>   de déclarée.
> - **§5 — le garde-fou de circularité** : *une modification de qrels ne se justifie jamais
>   par un résultat de run*. Inchangé, et ✅ **il a reçu sa porte d'entrée le 8 août 2026** —
>   [Comment une correction entre dans la collection ?](https://github.com/left-eyebr0w/murphy/issues/21)
>   est **clos**. Mieux : le garde-fou **cesse d'être un contrôle de politesse**. Le motif
>   d'une contestation est tiré d'une **liste fermée** (relecture · erreur de transcription ·
>   incohérence interne · violation d'une contrainte de rédaction · divergence de lecture ·
>   « autre »), dont aucune case ne peut être satisfaite en citant un résultat de run :
>   *« cette config remonte ce document, il doit être pertinent »* **n'a plus d'endroit où
>   s'écrire**. Le §5 devient une propriété du formulaire.
>
> ### Ce qui est périmé
>
> Le **titre**, le **§1** en entier, et les *Alternatives rejetées* qui argumentent entre
> variantes de gel (« pas de gel du tout », « version unique gelée définitivement »). Elles
> restent lisibles comme trace du raisonnement ; elles ne décident plus rien.
>
> ~~**Réécriture d'ensemble : ADR-036**, à la clôture de la carte #1 — pas avant, pour ne pas
> amender trois fois en une semaine.~~
>
> ✅ **Corrigé le 8 août 2026** ([#21](https://github.com/left-eyebr0w/murphy/issues/21) §9) :
> **la réécriture d'ensemble est celle de cet ADR, pas un transfert vers ADR-036.** Motif —
> 032 **est déjà** l'ADR de la collection versionnée, de la correction, de la re-notation et
> du garde-fou de circularité, et il gouverne **au-delà du golden-set** (v1 solo, v2 expert,
> machine B), ce qui l'exclut d'ADR-036 par le test même qui a fait naître ADR-037 et
> ADR-038. Écrire l'intake ailleurs laisserait ici *un critère que personne ne peut exercer
> et un titre faux sans avertissement* — le motif employé par
> [#23](https://github.com/left-eyebr0w/murphy/issues/23) le 8 août pour amender ADR-007
> plutôt qu'écrire ailleurs.
>
> **Ce que la réécriture doit porter**, à la clôture de la carte : le **titre** et le **§1**
> réparés · l'**intake des contestations** (unité = une contestation jamais un patch,
> corrections dérivées en interne · **porte unique, triage interne** · périmètre *on conteste
> ce qui est écrit, jamais ce qui manque* · liste fermée de motifs · **cinq issues** toutes
> enregistrées · routage par classe de coût, qui est le §4 rendu calculable · **journal des
> déplacements de hash à quatre causes typées**, en ajout seul et non haché · déclarant par
> rôle) · la **règle d'attribution champ → hash** (*le hash suit le coût, pas le fichier*,
> [#12](https://github.com/left-eyebr0w/murphy/issues/12) §4) **sous le test d'ADR-030**
> — *« si je change d'avis là-dessus, dois-je rouvrir les documents ? »* —, la table complète
> vivant en `GOLDEN-SET.md` §3 · et le **renvoi croisé dû par
> [#24](https://github.com/left-eyebr0w/murphy/issues/24)** (la monotonie contraint ce qu'un
> nom de version peut désigner), **dans la même passe** — c'était déjà la consigne d'`INDEX.md`,
> et la réécriture l'absorbe au lieu de juxtaposer deux amendements partiels.
>
> *ADR-036 conserve le **cimetière de vocabulaire** — dont l'entrée `gel` et ses traces
> ailleurs — mais **perd la réécriture de cet ADR**.*

## Contexte

E-P2-06 exige un golden-set « **figé et versionné** », hash de gel consigné.
La préparation de B-08 a fait apparaître une tension apparente avec la nature
du livrable.

Le golden-set est un artefact de **régime humain** (ADR-028) sur un problème
qu'on ne sait pas poser d'avance : la typologie, les grades et le guide
évolueront nécessairement à l'usage. Un artefact qu'on doit geler et qu'on doit
faire évoluer semble se contredire.

La sortie couramment envisagée — n'autoriser que des **extensions monotones**
(on ajoute, on ne corrige jamais), afin que les versions restent comparables
entre elles — est **contre-productive** : elle interdit exactement ce qui doit
pouvoir arriver (corriger une erreur de jugement, réviser le guide, re-dériver
les grades) et **ossifie** l'artefact au nom d'une comparabilité qu'on peut
obtenir autrement.

## Décision

### 1. Le gel porte sur chaque version, pas sur la suite des versions

**Chaque version publiée est immuable et porte son hash. La suite des versions
évolue librement.** C'est le modèle d'un dépôt de code : chaque commit est figé,
le dépôt vit ; on n'a jamais eu besoin de geler un dépôt pour obtenir des
builds reproductibles — il suffit de nommer le commit.

E-P2-06 est ainsi satisfaite **à la lettre** (« figé *et* versionné » : les deux
mots ensemble), sans révision de l'exigence.

Cette version d'**ensemble** complète le `guide_version` porté **par jugement**
(ADR-008) : le premier trace la dérivation des grades, la seconde identifie
l'état complet du jeu.

### 2. Les versions ne sont pas comparables entre elles — et n'ont pas à l'être

**Aucune contrainte de compatibilité entre versions.** Un score mesuré sur la
v1 ne se compare pas à un score mesuré sur la v2, et on ne cherchera pas à le
rendre possible.

Le fondement est une propriété structurelle déjà acquise : **un run ne dépend
pas des qrels.** Un run est `question → documents ordonnés` ; il ne contient
aucun jugement de pertinence. Le score est une fonction pure `(run, qrels)`.

Donc quand les qrels changent, **rien n'est perdu — on recalcule** : tous les
runs archivés (immuables, ADR-008) sont **re-notés** contre la version
courante, et la comparaison se fait de nouveau à qrels constantes. L'histoire
n'est pas invalidée, elle est **rejouée**.

C'est l'extension aux qrels du principe déjà posé par ADR-027 pour l'ingestion
(« la comparaison de deux `W` se fait sur leurs **runs archivés** »), et le même
geste qu'ADR-030 et ADR-031 : **ne pas stabiliser l'instrument dans le temps,
rendre la re-mesure gratuite**.

### 3. Toute mesure nomme sa version de qrels

Un rapport, une baseline, un verdict apparié consignent la **version de qrels**
employée. Un chiffre sans version n'est pas interprétable — et la comparaison
de deux chiffres de versions différentes est **interdite**, non pas
approximative.

### 4. Trois classes de changement, une seule coûteuse

| Changement | Re-récupération ? | Historique comparable ? |
|---|---|---|
| Corriger un grade, réviser le guide, re-dériver | Non — re-notation seule | **Oui, entièrement** |
| Juger des documents supplémentaires sur une question existante | Non | **Oui** |
| **Ajouter une question** | **Oui** | Non, sauf à rejouer les configs |

> ⚠️ **Précision du 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) —
> la première ligne est **confirmée, pas contredite**, mais « re-notation seule » s'y lit trop
> largement pour la **révision du guide**. Réviser le guide **ne déplace aucun hash** : le
> guide n'est **pas un composant haché** (les trois hashes portent le corpus, les cas et les
> qrels), sa version voyage sur **chaque jugement** via `guide_version` (ADR-008). Et le
> re-jugement qu'une révision déclenche est **ciblé** — seuls les items dont le désaccord a
> provoqué l'amendement —, jamais la collection entière. Motif : un amendement qui coûterait
> une re-notation générale rendrait le guide **inamendable en pratique**, ce qui annulerait la
> falsifiabilité qu'il a acquise.

Seule la troisième coûte : un run ancien ne contient aucun résultat pour une
question qui n'existait pas à sa production, et la collection Qdrant
correspondante peut avoir été supprimée (`nuke_all` entre deux `W`, ADR-027).

**Ce coût est assumé** — rejouer le processus d'évaluation n'est pas un
obstacle. Il reste une **dépense à minimiser** : les ajouts de questions se
font **par lots, à des moments choisis**, suivis d'un rejeu des configurations
de référence. Les corrections de jugement, elles, se font au fil de l'eau sans
rien casser.

### 5. Garde-fou : une modification de qrels ne se justifie jamais par un résultat

C'est le risque que le versionnement réintroduit, et il est sérieux : re-noter
parce qu'une configuration a perdu, c'est **ajuster l'étalon à l'issue
souhaitée** — la circularité de mesure d'ADR-031 §5, revenue par la porte du
temps.

**Règle** : toute modification des qrels se justifie **sans référence à un
résultat de run**, et est datée. « J'ai relu, ce grade 1 est un 2 » est
recevable. « Cette config remonte ce document, il doit être pertinent » ne l'est
pas. Même discipline que le champ `origin` (ADR-008), appliquée au temps plutôt
qu'à la provenance.

## Alternatives rejetées

- **Extension monotone seule** (ajouter sans jamais corriger, pour garder les
  versions comparables) : interdit la correction d'erreurs et le retour sur le
  guide — ossifie l'artefact au nom d'une propriété obtenable par re-notation.
- **Version unique, gelée définitivement** : la lecture littérale du « hash de
  gel ». Rend le jeu conservateur — il pénalise toute configuration future
  remontant un document jamais jugé, exactement le biais reproché aux qrels
  citation-minées (ADR-029). L'évaluation favoriserait alors le passé, panne
  fatale pour un dispositif censé détecter le progrès.
- **Pas de gel du tout** : détruit la reproductibilité (E-P2-10) et rend tout
  chiffre inauditable.
- **Comparer des scores de versions différentes** avec une correction ou une
  réserve : donne une comparabilité *apparente*, la plus trompeuse des options.

## Conséquences

- **D-02 est close.** Un document jamais jugé qu'une configuration future
  remonterait n'est plus un défaut définitif du jeu : c'est **un jugement à
  ajouter à la version suivante**, suivi d'une re-notation. Le biais du jeu
  incomplet cesse d'être une fatalité pour devenir une **dette rattrapable**.
- **Le pooling change de statut** : il n'est plus le rempart contre
  l'incomplétude (rôle perdu avec ADR-029, cf. ADR-007), mais un
  **ordonnanceur de l'effort d'annotation** — juger d'abord l'union des top-k,
  compléter ensuite.
- **B-08 peut geler la v1 sans chercher à l'anticiper parfaitement**, et
  commencer **petit et profond** : les erreurs se corrigent en v2 sans rien
  invalider, les questions s'ajoutent par lots.
- **E-P2-10 se lit à version de qrels constante** : la reproductibilité (diff
  des métriques nul entre deux exécutions de `(W, G, R)` identique) suppose la
  même version de qrels, désormais consignée dans l'artefact de run au même
  titre que le fingerprint de `W` et l'identifiant de `G` (ADR-031).
- **Trois propriétés d'outillage à garantir** (B-11) — ce sont des exigences de
  tooling, non de méthode : chaque version porte un hash ; chaque rapport nomme
  la version employée ; **la re-notation de tout l'historique est une seule
  commande**. Sans la troisième, la décision ci-dessus n'est pas praticable.

## Références

ADR-007 (complétude, pooling) · ADR-008 (runs immuables, `origin`,
`guide_version`) · ADR-027 (comparaison sur runs archivés) · ADR-028 (régime
humain) · ADR-029 (biais des qrels incomplètes) · ADR-030 (observation /
dérivation) · ADR-031 (circularité de mesure) · `EXIGENCES_v0.md` E-P2-06,
E-P2-10 · `BACKLOG.md` B-08, B-11
