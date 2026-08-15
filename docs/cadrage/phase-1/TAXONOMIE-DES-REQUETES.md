# Taxonomie des requêtes - Murphy

## 0. Objet

**La taxonomie classe des requêtes, pas des utilisateurs.** La règle de non-personalisation (**D-06**) l'impose : le système ne voit d'un usager que ce que sa requête porte. Toute propriété qui ne se lit pas dans la requête est inopérante ici : le profil, le métier, le dossier. Ce qui ressemblerait à un niveau d'expertise n'est légitime qu'à la condition d'être inclus dans la
formulation elle-même, en temps que propriété de la requête.

**Critère d'admission d'une classe :** Deux requêtes appartiennent à des classes différentes si, et seulement si, **le système doit se comporter différemment, ou
échouer différemment**. 

**Deux espèces de discriminant :** Presque tous se lisent dans la requête seule -
forme d'identifiant, dimension nommée, singularité de la visée, marqueur
d'inflexion. Un seul de tout le document fait exception : la frontière des crans
2 et 3 (§1.1) lit la requête **et** le corpus. Elle est admise, parce qu'elle
reste décidable - savoir si une chaîne figure dans un texte ne demande ni
l'intention de l'usager, ni ce qu'on aurait dû trouver.

Ce qui reste interdit est le discriminant **circulaire** : celui qui exige de
connaître la réponse pour classer la question, soit le travers de §1 reproduit à
l'intérieur de notre propre instrument. C'est lui qui a fait tomber la
distinction des crans 4 et 5, et lui seul. La règle générale se lit donc ainsi :
un discriminant doit être décidable **avant** que la requête soit servie, non
qu'il doive tenir dans la requête.

**Le discriminant est donc daté.** « Décidable » se lit *contre un état daté du
corpus*. Une requête change de cran sans changer d'un mot quand le corpus
s'étend : le terme qui n'y figurait pas s'y trouve désormais, la recherche
l'atteint, la table devient inutile. Ce n'est pas un défaut - la population du
cran 3 **décroît** à mesure que le corpus s'élargit, ce qui en fait une mesure de
progrès plutôt qu'une instabilité. Mais il suit qu'un jeu d'annotations constitué
en T0 porte des étiquettes de cran **fausses en T1**, sans que rien ne le
signale. Soit la phase 3 date ses annotations, soit elle recalcule le cran au
moment de noter ; ne rien faire est la seule option qui perde la donnée en
silence.

**L'anonymisation est en amont de la taxonomie.** Le refus d'anonymisation
(**D-09**) n'est pas une classe de requête : c'est une propriété du contenu, et
D-09 place le module *à l'entrée du système, avant tout autre traitement*. Il
s'applique donc à toutes les classes sans en distinguer aucune, et n'apparaît sur
aucun axe.

**Ce que le corpus ne porte pas.** L'usager peut nommer un objet qui n'est pas
dans le corpus. Comme l'anonymisation, cela vaut pour toutes les classes, ne
fonde aucune frontière et n'apparaît sur aucun axe - mais rien ailleurs ne le
dit, et le silence sur ce point est plus dangereux que le manque lui-même.

Deux espèces de trou, et une seule en est un.

- **Provisoire** - les bases publiées par le producteur que l'ingestion n'a pas
  encore reprises, **KALI** en tête. Ce n'est pas un hors-périmètre : la note de
  cadrage (§4) met dedans *la récupération de sources juridiques françaises
  publiées, toutes matières*, et ne met dehors que le droit **non publié par le
  producteur**. C'est un pas-encore, et ça lègue une échéance, pas une limite de
  conception.
- **Définitif** - ce qui n'est pas un texte normatif et n'entrera dans aucune
  base : le formulaire Cerfa, la notice, l'imprimé. La substitution y est
  permanente.

**La règle est la même dans les deux cas : le système peut rendre l'entourage
juridique de l'objet nommé plutôt que l'objet, et doit alors déclarer qu'il l'a
fait.** Sans cette déclaration, l'usager croit que ce qu'il cherchait est dans le
lot. Le registre des risques porte déjà la doctrine, en **R-37** - *« la perte
d'une base doit être un périmètre en moins, jamais un service arrêté »* : le trou
provisoire en est le cas symétrique, à ceci près qu'il est connu d'avance, donc
déclarable d'avance.

Le cas grave n'est pas le Cerfa mais la **convention collective**. « Ce que dit
ma convention collective sur le préavis » est une requête de groupe B banale, et
lui rendre le code du travail seul, c'est rendre le principe sans sa dérogation -
le pire échec du projet selon §1.2 et Q-05. La différence avec les autres
silences est que ce manque-là n'est pas dans le graphe mais dans l'état du
corpus : on le connaît, donc on l'annonce.

**Limite de validité.** Les spécimens sont produits par une seule tête. Le risque
n'est pas que leur provenance soit mal documentée, il est que la taxonomie classe
des usagers **imaginés** plutôt que des usagers réels (**R-05**).

---

## 1. Axes

### 1.1 La clé d'accès dont l'usager dispose

L'axe primaire. Il met en gradient la phrase qui porte le problème : *le moteur public exige le vocabulaire de la réponse comme clé
d'accès à la réponse.* L'axe mesure la distance entre **ce que l'usager a déjà**
et **les mots que le corpus porte**. Il se lit comme un gradient de *qui nomme* :
l'identifiant du producteur, puis les mots des textes eux-mêmes, puis le nom
qu'un tiers leur a donné, puis ceux de l'usager - on s'éloigne du texte par
cercles concentriques jusqu'à celui qui cherche.

| Cran | Registre | Spécimen | Écart à franchir |
|---|---|---|---|
| **1** | **La référence** - l'identifiant canonique | « article L1234-5 du code du travail » · « Cass. soc. 25 nov. 2015, n° 14-24.444 » | aucun : l'usager ne cherche pas, il récupère |
| **2** | **Les mots du corpus** - un terme que les textes visés portent | « préavis de démission » · « vice caché » · « rupture conventionnelle » | de la notion à ses supports |
| **3** | **Le nom que d'autres lui donnent** - éponyme, surnom, étiquette absente du texte | « la prime Macron » · « la loi Badinter » | une correspondance vers le nom légal : elle existe et se tabule |
| **4** | **Les mots de l'usager** - aucun terme repris | « mon patron me fait travailler plus que prévu et ne me paie pas plus » · « mon père est décédé et il y a une maison » | une qualification, qu'aucune correspondance ne fournit - et parfois l'objet juridique lui-même n'est pas délimité |

**Le mode d'échec bascule le long du gradient.** En haut (1–2), l'échec est du
**bruit** : on trouve, et autre chose avec. En bas (3–4), l'échec est du
**silence** - et le silence reproduit exactement le problème de §1 : l'usager
« n'a aucun moyen de distinguer *cette règle n'existe pas* de *je n'ai pas su la
nommer* ». Un système qui échoue en silence en bas du gradient n'améliore pas le
moteur public, il le déguise.

**Le cran 1 exige une capacité que la recherche sémantique ne fournit pas.** Une
référence est un identifiant, pas un sens : la similarité vectorielle ne la
retrouve pas de façon fiable. Or c'est le cas où l'usager sait exactement ce
qu'il veut et constatera l'échec immédiatement. Le cran où Murphy n'apporte rien
de plus que le moteur public est donc aussi celui qu'il lui est techniquement le
plus facile de rater. Il est retenu à ce titre : non pour la valeur qu'il ajoute,
mais parce qu'un système qui rate le plus facile n'est pas crédible sur le reste.

**C'est le seul axe qui mesure la valeur du projet.** Le cran 1 est résolu depuis
longtemps ; le cran 4 ne l'est par personne, à aucun prix. La valeur de Murphy
croît avec le cran. L'axe n'est donc pas seulement un instrument de classement :
c'est l'échelle sur laquelle le projet se juge - et celle sur laquelle la phase 3
devra échantillonner sans se concentrer là où c'est facile.

**Quatre crans, et non cinq.** Les faits et l'événement seul ont d'abord été
distingués, puis fondus, pour deux raisons dont la seconde est la vraie. La
première : la décision ci-dessous les traite à l'identique - même récupération
large, aucune qualification, aucune désambiguïsation, même échec en silence. Le
critère d'admission (§0) tranche alors tout seul. La seconde : le discriminant
proposé n'était **pas observable**. Séparer la situation *qualifiable* de
l'événement *non délimité* suppose de savoir ce qu'on aurait trouvé - c'est
exiger le vocabulaire de la réponse pour classer la question, soit le travers de
§1 reproduit à l'intérieur de notre propre instrument. Une classe dont on ne peut
pas dire à l'entrée si une requête y appartient n'est pas une classe.

**Règle de frontière, crans 2 et 3.** Le discriminant n'est pas la façon dont le
texte se nomme, mais **la présence du terme dans les textes qu'il désigne**.

- **Il y figure** → **cran 2**. Chercher suffit ; aucune ressource extérieure au
  corpus. « Rupture conventionnelle » est un mot d'usage courant *et* le terme du
  code du travail (art. L1237-11) : cran 2, quel que soit l'usage qu'en fait le
  locuteur. De même le sigle que le texte définit lui-même - le CASF écrit
  « l'allocation aux adultes handicapés (AAH) » - et l'étiquette héritée d'une
  partie à l'instance, « l'arrêt Baby-Loup ».
- **Il n'y figure pas** → **cran 3**. Il faut d'abord établir de quel texte on
  parle, par une correspondance que le corpus ne porte pas. C'est l'éponyme
  politique - « la loi Badinter », « la loi Toubon » - et le surnom médiatique :
  les textes disent « prime exceptionnelle de pouvoir d'achat », « Macron » n'y
  est nulle part.

**Le test porte sur la machine**, comme le §0 l'exige. Le cran 3 est le seul cran
de l'axe qui **ajoute une étape**, et c'est cette étape qui lui donne son mode
d'échec propre : la correspondance fausse, qui n'est ni du bruit ni du silence
mais une réponse bien formée et fausse. Le cran 2 n'en demande aucune, le cran 4
n'en admet pas. Qu'une recherche vectorielle retrouve mal un sigle de trois
lettres est vrai et sans effet ici : c'est une faiblesse d'implémentation, donc
une question de phase 4, et la taxonomie n'a pas à porter les défauts d'une
architecture qu'elle ne connaît pas encore.

**Le cran 3 est étroit, et il est retenu quand même.** La règle le réduit aux
noms propres collés à un texte qui ne les porte pas. La population est petite ;
ce n'est pas un critère - dimensionner un cran sur son effectif serait l'erreur
que le §2.1 écarte pour le nombre de classes. Il est retenu sur trois raisons qui
ne dépendent pas de sa taille : un mode d'échec qu'aucun autre cran ne porte ; le
vocabulaire du **groupe B**, qui apprend les dispositifs par la presse et non par
le Journal officiel ; une ressource identifiée, ce qui vaut mieux qu'un besoin
diffus.

**La frontière ne se tranche pas à l'entrée.** Elle ne commande aucun aiguillage :
la correspondance peut être une étape de rattrapage, tentée après la recherche
plutôt qu'avant elle - quand et comment la déclencher est une question de phase 4.
La taxonomie n'a besoin de la frontière que pour nommer deux comportements et deux
échecs, et c'est la **phase 3** qui s'en sert, corpus sous les yeux. L'entorse à
l'observabilité (§0) est donc confinée au travail d'annotation et ne coûte rien à
l'exécution.

#### Le cran 4 est dans le périmètre

Il est traité comme une **récupération large**. Le système ne délimite pas
l'objet à la place de l'usager : il restitue, et l'usager qualifie seul
(**D-07**). Deux conséquences suivent, et elles ne sont pas facultatives.

**Aucune désambiguïsation n'est possible.** Ce qui est exclu est la question de
clarification - le système demande, l'usager répond, le système récupère alors.
Elle l'est deux fois : par **D-06**, parce qu'un tel échange suppose de retenir
le tour précédent alors que chaque équation est neuve ; et par **D-03**, parce
que proposer « voulez-vous dire X ou Y ? » est déjà une première qualification,
faite par le système et non par l'usager.

**L'ensemble restitué doit être lisible comme ensemble.** Ce qui n'est pas exclu,
en revanche, c'est que l'ensemble donne à voir sa propre dispersion : l'usager ne
répond à rien, il constate l'étendue de ce qu'il tient et pose une équation plus
étroite. Sans cela, le cran 5 est une impasse - quarante pièces en liste plate ne
se jugent ni ne se concentrent, et **D-07** confie les deux à l'usager.
Récupération large et liste plate sont incompatibles. **C'est la première
exigence que la taxonomie lègue au cahier des charges fonctionnel.**

**Le refus explicite n'est pas disponible ici.** Il est réservé au hors-périmètre
- une demande d'interprétation (**D-03**) - jamais à une requête jugée trop
vague. Une requête vague est une requête légitime dont l'ensemble est large.

**Le geste correctif est une requête entière.** Chaque tour est neuf et porte son
contexte (**D-06**) : concentrer n'est pas envoyer un delta à un état conservé,
c'est reposer une équation.

### 1.2 La forme de l'ensemble visé

L'axe 1 décrit l'**entrée** : ce que l'usager tient. Celui-ci décrit la
**sortie** : quel ensemble le satisferait. C'est lui qui donne son contenu à la
note de cadrage, §3 - *l'unité de valeur n'est pas seulement l'ensemble restitué
mais surtout l'ensemble atteignable : lequel, et en combien de gestes.*

| Valeur | Ce qui satisferait la requête | Cardinalité | Mode d'échec propre |
|---|---|---|---|
| **La pièce** | une pièce identifiée | 1, connue de l'usager | on ne l'a pas - total, et constaté immédiatement |
| **L'ensemble** | la règle et ce qui la borne : le principe et sa dérogation, l'article et ses exceptions | déterminée par le droit, **inconnue de l'usager** | il manque l'exception, et rien ne signale qu'elle manque |
| **La série** | une extension exhaustive sur une dimension nommée du corpus | déterminée par le corpus, **calculable** | un trou dans l'exhaustivité, localisable **sur la dimension** |

**Cet axe rend « bruit / silence » opérable.** La note de cadrage pose le couple
(§3) sans dire ce qu'il signifie ; c'est ici qu'il le devient, et les
significations ne se ressemblent pas. Sur **la pièce**, le bruit est presque
gratuit : la bonne pièce est là, le reste s'ignore. Sur **l'ensemble**, le
silence est le pire échec du projet - l'usager repart avec une règle vraie et
incomplète, plus confiant qu'avant, et c'est la seule configuration où Murphy
peut nuire à quelqu'un qui n'aurait rien trouvé sans lui. Sur **la série**, un
résultat à 95 % n'est pas une approximation, c'est un échec.

**Il décide de ce qu'un `top-K` peut vouloir dire.** Un K fixe tronque la série
par construction, et sur l'ensemble il n'a aucune raison de tomber juste : la
cardinalité y est fixée par le droit, pas par une constante de configuration.

#### L'ensemble ouvert n'est pas une valeur de cet axe

Une quatrième valeur a été envisagée puis écartée : l'**ensemble ouvert**, « tout
ce qui s'applique à… », sans cardinalité correcte, où l'usager s'arrête quand il
a assez. Elle est écartée sur le critère d'admission (§0), et sur son second
membre : elle n'a **pas de mode d'échec propre** - on ne manque pas ce qui n'a
pas de borne. Une classe qui ne peut pas rater est une classe que la phase 3 ne
peut pas noter.

**Ce qui est écarté est la forme, pas le besoin.** Le besoin exploratoire existe,
et la décision prise au cran 4 engage déjà le système à produire de grands
ensembles. Ceux-ci ne disparaissent pas ; ils cessent d'être une forme
**garantie** : le système n'en promet ni la cardinalité ni la complétude, et n'y
reconnaît aucun échec distinct. **Ce cas ne se note pas sur collection de test.**
Il ne sort pas de l'évaluation pour autant - il bascule sur l'autre plan,
**D-02(b)** : taux de tâches abouties et temps jusqu'à la première source
pertinente, que la note de cadrage tient de rang égal. La limite est un
aiguillage, pas un renoncement.

**Le système se comporte alors toujours comme s'il était sur l'ensemble** : il ne
rompt jamais un principe de sa dérogation. Cette exigence ne demande pas de
savoir ce que l'usager voulait - inaccessible - mais ce que **le droit lie**,
qui est une propriété des documents : renvois, textes pris pour l'application,
place dans le plan, chaînes d'abrogation. Elle se déplace donc du côté connaissable, au prix d'une charge
léguée à la **phase 2** (schéma de métadonnées, stratégie de parsing) et d'une
exposition à **R-08** : si le corpus ne porte pas la liaison, elle ne se fabrique
pas. Son incomplétude, au moins, se mesure - ce que deviner une intention ne
permet jamais.

#### Règle de frontière : sans dimension nommée, pas de série

Une série n'existe que si l'usager **nomme la dimension** sur laquelle elle
s'étend - une période, une juridiction, une nature de texte, « toutes les
versions ». « Toutes les règles sur le préavis » porte le mot *toutes* mais ne
nomme aucune dimension : c'est un ensemble. Le discriminant reste observable
dans la seule requête, puisque la dimension doit y être énoncée pour que la
requête soit une série.

Ce qui sépare la série de l'ensemble n'est pas la taille. Dans l'ensemble,
l'appartenance est décidée par le droit et se **découvre** ; dans la série, elle
est décidée par le critère de l'usager et s'**énumère**. Il suit que la
pertinence n'y est pas individuelle : une version que personne n'invoquerait fait
partie de la série *parce qu'elle est une version*.

**Certaines séries ont une vérité de référence qui se constate au lieu de se
juger** - pas toutes, et la distinction décide de ce que la phase 3 peut se
payer. Partout ailleurs, dire ce qui aurait dû être restitué demande un jugement
de pertinence, donc un annotateur, et **R-05** est à 🟥 en T0.

Ce qui tranche est le **critère d'appartenance**, et il se lit sur trois degrés :

| Degré | L'appartenance | Coût de la vérité de référence | Classes |
|---|---|---|---|
| **Mécanique** | la dimension la détermine entièrement, depuis une ancre donnée | nul : soit les onze versions y sont, soit il en manque une, et un comptage tranche | **Q-03** |
| **Ancrée** | mécanique une fois les ancres établies, mais chacune demande un jugement - quels textes ce nom désigne-t-il ? | un jugement par **nom porté**, puis rien | **Q-09** |
| **Mixte** | la dimension, **plus** un critère de fond - « sur le harcèlement moral » | un jugement par document candidat, comme partout ailleurs | **Q-06**, **Q-11** |

La porte de sortie existe donc, mais elle est étroite : grande ouverte sur Q-03,
entrouverte sur Q-09, fermée sur Q-06 et Q-11. C'est assez pour que la phase 3
**commence** par ce qui se constate et n'engage d'annotateurs qu'ensuite - ce qui
est déjà un ordre de travail.

#### Les deux axes sont indépendants

**La pièce** n'est pas le cran 1 déguisé. On peut viser une pièce sans tenir de
référence - « l'arrêt qui a posé que le silence ne vaut pas acceptation » est un
cran 2 qui vise une pièce unique - et tenir une référence en visant un ensemble
- « l'article L1234-5 et ce qui le borne ». Le croisement a donc des cases
peuplées, ce qui est la condition pour qu'il produise des classes.

### 1.3 L'opération demandée

Les deux premiers axes disent ce que l'usager tient et ce qu'il vise. Celui-ci
dit ce qu'il demande au système de **faire**.

Il ne porte pas sur le **geste**, qui n'est pas observable : le système est sans
état, il ne voit jamais l'ensemble précédent, donc jamais qu'on l'élargit. Ce
qu'il voit est l'**inflexion que la requête porte en elle-même**.

| Valeur | Ce que la requête porte | Ce que le système doit privilégier |
|---|---|---|
| **Constituer** | aucune inflexion ; l'équation est posée à plat | l'équilibre |
| **Élargir** | une relaxation explicite - « y compris », « et aussi », « tous les cas de » | le **rappel**, au prix de la précision |
| **Resserrer** | une restriction explicite - « uniquement », « seulement lorsque », une condition ajoutée | la **précision**, au prix du rappel |
| **Qualifier** | aucune visée d'ensemble : une conclusion est demandée | rien - refus explicite (**D-03**) |

**« Déplacer » n'est pas une valeur.** La note de cadrage (§3) en fait un geste à
part, aux côtés d'élargir et de concentrer. Mais pour un système sans état, une
requête qui corrige le tir est indiscernable d'une constitution neuve : ôtez le
« non, plutôt… », il reste une équation posée à plat. Le critère du §0 le fond
dans *constituer*, comme il a fondu l'événement seul dans les mots de l'usager.

**La demande de qualification se reconnaît à sa valeur vide sur l'axe 2.** C'est
la seule requête qui ne décrit aucun ensemble de documents : elle demande une
conclusion. « Ai-je le droit de licencier pour absences répétées » porte bien un
registre de vocabulaire (cran 4), mais ne vise ni pièce, ni ensemble, ni série.
La signature est donc positive et lisible dans la formulation seule - il n'y a
pas d'intention à deviner. Le refus qui s'ensuit porte **sur la phrase, jamais
sur le besoin** : il ne dit pas « vous n'avez pas le droit de vouloir ça », il
dit « ainsi formulée, cette requête me ferait qualifier ». Le remède est la
reformulation, et la porte est franchissable par là - volontairement. Qui veut
une qualification l'obtiendra en posant une requête de récupération puis en
tirant lui-même la conclusion : c'est exactement ce que **D-03** organise, le
système ne qualifie pas, l'usager qualifie.

**C'est l'axe dont le cahier des charges hérite le plus directement** - le README
lui fixe pour premier objet les gestes de pilotage, et cet axe en est la face
observable. Il lui lègue une contrainte : si l'inflexion doit se lire dans la
phrase, l'interface doit rendre ces inflexions **formulables**. Un usager qui ne
sait pas qu'il peut écrire « uniquement » ne pilote rien.

**Réserve assumée.** Ces marqueurs sont lexicaux, donc fragiles. La taxonomie n'a
pas à dire comment on les détecte - c'est une question d'architecture, phase 4 -
mais elle établit que la classe existe et que le système s'y comporte
différemment.

---

## 2. Les classes

### 2.1 Ce qui se croise et ce qui ne se croise pas

Trois axes donneraient quarante-huit cases. Ils n'interagissent pas de la même
façon, et le critère du §0 impose de le constater plutôt que de multiplier.

**Les axes 1 et 2 interagissent.** *Référence × pièce* et *mots de l'usager ×
ensemble* ne sont pas le même travail : l'un résout un identifiant, l'autre
franchit un écart de vocabulaire puis suit des liens juridiques. Le croisement y
produit de vraies classes.

**L'axe 3 ne multiplie pas les classes.** *Élargir* veut dire la même chose sur
« le préavis de démission » (cran 2) et sur « les règles de la loi Badinter »
(cran 3) :
privilégier le rappel. Ce qui distingue ces deux classes est en **amont** de
l'inflexion - l'étape de correspondance du cran 3 - et l'inflexion s'y compose
sans interagir. Multiplier affirmerait trente-trois comportements distincts quand
on n'en observe que treize ; les vingt autres seraient de la redondance
littérale. Une taxonomie qui revendique des distinctions qu'elle ne peut pas
soutenir est **moins** rigoureuse, pas plus - c'est le défaut du classement par
matière, en plus discret.

**Le nombre de classes ne se dimensionne sur aucune ressource.** Ni sur le fait
qu'on soit seul en T0, ni sur les assesseurs qu'on espère en T1. La taxonomie
définit une population ; c'est le golden set qui échantillonne selon ce qu'on
peut payer. Faire l'inverse mettrait l'instrument au service du calendrier de
mesure.

**L'axe 3 est enregistré comme attribut de chaque spécimen.** Rien n'oblige une
valeur à être une frontière de classe pour être notée. Les fiches restent au
niveau du croisement 1 × 2 ; chaque spécimen, lui, porte ses trois valeurs. La
phase 3 pourra donc trancher ses mesures par inflexion si elle en a besoin, sans
qu'on ait figé aujourd'hui des distinctions qu'on ne sait pas encore réelles.
C'est l'asymétrie décisive : l'attribut rend le bénéfice de la multiplication **au
moment où l'on peut s'en servir**, là où la multiplication demande de trancher
maintenant, avec moins d'information qu'on n'en aura alors.

### 2.2 La grille

|  | **La pièce** | **L'ensemble** | **La série** |
|---|---|---|---|
| **1. Référence** | **Q-01** | **Q-02** | **Q-03** |
| **2. Mots du corpus** | **Q-04** | **Q-05** | **Q-06** |
| **3. Nom d'emprunt** | **Q-07** | **Q-08** | **Q-09** |
| **4. Mots de l'usager** | *structurellement vide* | **Q-10** | **Q-11** |

**La case vide n'est pas un manque de spécimens.** *Mots de l'usager × pièce* ne
peut pas se peupler : viser une pièce unique suppose de savoir qu'elle existe et
qu'elle est unique, donc d'en tenir déjà quelque chose - un nom, une référence,
une étiquette. Qui n'a que ses propres mots ne sait pas qu'il y a une pièce à
viser. Le vide est une propriété du gradient, et il le confirme.

### 2.3 Les douze classes

| Code | Croisement | Nom | Spécimen |
|---|---|---|---|
| **Q-01** | référence × pièce | la résolution d'identifiant | « article L1234-5 du code du travail » |
| **Q-02** | référence × ensemble | l'identifiant et ses liens | « l'article L1234-5 et ce qui le borne » |
| **Q-03** | référence × série | l'identifiant dans le temps | « toutes les versions de l'article L1234-5 depuis 2008 » |
| **Q-04** | mots du corpus × pièce | la pièce nommée sans référence | « l'arrêt qui a posé que le silence ne vaut pas acceptation » |
| **Q-05** | mots du corpus × ensemble | la règle et ses bornes | « le préavis de démission » |
| **Q-06** | mots du corpus × série | la série juridiquement nommée | « les arrêts sur le harcèlement moral depuis 2015 » |
| **Q-07** | nom d'emprunt × pièce | le texte derrière le nom | « la loi Badinter » |
| **Q-08** | nom d'emprunt × ensemble | le régime derrière le nom | « les règles de la loi Badinter » |
| **Q-09** | nom d'emprunt × série | le nom dans le temps | « les versions successives de la prime Macron » |
| **Q-10** | mots de l'usager × ensemble | la situation décrite | « mon patron me fait travailler plus que prévu et ne me paie pas plus » |
| **Q-11** | mots de l'usager × série | le matériau sériel sans vocabulaire | « les jugements depuis 2020 où le patron n'a pas payé tout ce qu'il devait » |
| **Q-12** | *aucune forme visée* | la demande de conclusion | « ai-je le droit de licencier pour absences répétées ? » |

**Q-05 et Q-10 sont les deux classes centrales**, et elles ne servent pas les
mêmes gens : Q-05 est le cas courant du groupe A, Q-10 celui du groupe B (note de
cadrage, §2). Elles visent la même forme - l'ensemble - par des chemins que tout
sépare. C'est sur leur écart que se lit ce que Murphy ajoute au moteur public.

**Q-12 n'est pas une classe de récupération** mais la sortie de refus. Elle est
retenue comme classe parce qu'elle doit être **reconnue**, et un périmètre qu'on
ne sait pas reconnaître à l'entrée n'est pas un périmètre.

### 2.4 L'axe 3 par forme d'ensemble

*Constituer* est la valeur neutre et vaut partout. Les deux inflexions, elles,
n'ont pas le même sens selon la forme visée - c'est la seule interaction que
l'axe 3 entretienne, et elle est avec l'axe 2, jamais avec l'axe 1.

| Forme | **Élargir** | **Resserrer** |
|---|---|---|
| **La pièce** | dégénéré : sortir de la pièce, c'est changer de forme visée | dégénéré : on tient la pièce ou on ne la tient pas |
| **L'ensemble** | relâcher la contrainte sémantique - rappel au prix de la précision | ajouter une condition - précision au prix du rappel |
| **La série** | **étendre la dimension** - plus d'années, plus de juridictions : un changement de filtre, pas un curseur | **restreindre la dimension** - de même |

La ligne « série » est celle qui justifie ce tableau : l'inflexion n'y est pas un
arbitrage rappel/précision mais une redéfinition du critère d'appartenance. Sur
une série, élargir ne rend pas la recherche plus tolérante ; il change la série
demandée.

---

## 3. Les fiches

Chaque fiche porte sept champs. Ce qu'une classe lègue aux phases suivantes n'y
figure pas : les legs sont rassemblés au §4, pour être lus ensemble.

Les **spécimens** illustrent la classe ; les **frontières** disent où elle
s'arrête et vers laquelle la requête bascule. Les deux sont séparés parce qu'ils
ne font pas le même travail : mélangé aux spécimens, un cas-frontière se lit
comme un exemple de la classe, soit l'inverse de ce qu'il dit.

---

### Q-01 - la résolution d'identifiant

*référence × pièce*

**Définition.** L'usager tient l'identifiant du producteur et veut la pièce qu'il
désigne. Il ne cherche pas : il va chercher.

**Critère discriminant.** La requête porte un identifiant de forme reconnaissable
- article et code, numéro de pourvoi, numéro de décret, juridiction et date. Elle
ne demande rien autour de la pièce (sinon Q-02) et ne nomme aucune dimension
(sinon Q-03).

**Spécimens.**
- « article L1234-5 du code du travail »
- « Cass. soc. 25 nov. 2015, n° 14-24.444 »
- « décret n° 2020-1310 »
- « L. 1234-5 » - forme abrégée, sans le code : l'identifiant reste reconnaissable

**Frontières.**
- « l'article L1234-5 et ce qui le borne » → **Q-02**
- « toutes les versions de L1234-5 » → **Q-03**
- « l'article sur le préavis de démission » → aucun identifiant : **Q-04** ou
  **Q-05** selon la forme visée

**Comportement attendu.** Résoudre, et non chercher. Un identifiant est une
chaîne, pas un sens : la similarité vectorielle ne le retrouve pas de façon
fiable, et rendre l'article voisin n'est pas une approximation acceptable mais
une erreur. En l'absence de date, le défaut est la **version en vigueur** ; toute
autre demande nomme une date et devient Q-03.

**Mode d'échec dominant : le bruit**, et c'est la seule classe où il est plus
grave que le silence. Ne rien rendre est constaté immédiatement - l'usager sait
ce qu'il voulait. Rendre une pièce **voisine** en la présentant comme la bonne ne
l'est pas : celui qui tient déjà l'identifiant a par là même accordé sa confiance
à la résolution, et ne revérifie pas.

**Statut au périmètre.** Dedans - non pour la valeur ajoutée, qui est nulle, mais
parce qu'un système qui rate le plus facile n'est pas crédible sur le reste
(§1.1).

---

### Q-02 - l'identifiant et ses liens

*référence × ensemble*

**Définition.** L'usager tient l'identifiant et veut la pièce **avec ce qui la
borne**. Il sait où commencer, pas où la règle s'arrête.

**Critère discriminant.** Un identifiant, plus une demande d'extension juridique
non dimensionnée - « et ce qui le borne », « avec les exceptions », « et les
dérogations ». Aucune dimension nommée, sinon Q-03.

**Spécimens.**
- « l'article L1234-5 et ce qui le borne »
- « L1237-11 avec ses exceptions »
- « l'article 1112-1 du code civil et les dérogations »

**Frontières.**
- « article L1234-5 » seul → **Q-01**
- « tous les décrets pris en application de L3121-1 » → une dimension est nommée,
  la nature du texte : **Q-03**

**Comportement attendu.** Résolution exacte, **puis** parcours des liens
juridiques. La classe compose deux opérations que rien d'autre ne compose : le
point d'entrée est certain, l'étendue ne l'est pas.

**C'est le banc d'essai du suivi de liens.** L'ancre étant exacte, un manque
s'impute au graphe et non à la récupération. Si le suivi de liens échoue ici, il
échouera partout - et nulle part ailleurs le diagnostic ne sera aussi net.

**Mode d'échec dominant : le silence** - l'exception manquante, comme Q-05, mais
**diagnosticable**, pour la raison ci-dessus.

**Statut au périmètre.** Dedans.

---

### Q-03 - l'identifiant dans le temps

*référence × série*

**Définition.** L'usager tient l'identifiant et demande son extension sur une
dimension nommée : versions successives, état à une date, textes pris en
application.

**Critère discriminant.** Un identifiant, plus une dimension explicitement
nommée. Sans dimension, c'est Q-01 ou Q-02.

**Spécimens.**
- « toutes les versions de l'article L1234-5 depuis 2008 »
- « l'article L1234-5 dans sa version applicable au 3 mars 2014 »
- « tous les décrets pris en application de l'article L3121-1 »

**Frontières.**
- « l'article L1234-5 » → version en vigueur par défaut : **Q-01**
- « L1234-5 et ce qui le borne » → extension juridique, non dimensionnée :
  **Q-02**

**Comportement attendu.** Résolution exacte, puis énumération **complète** sur la
dimension. L'exhaustivité est le critère, non la pertinence : une version que
personne n'invoquerait est dedans parce qu'elle est une version. Le corpus doit
porter le versionnage - c'est une condition d'existence de la classe, pas une
amélioration.

**Mode d'échec dominant : le trou**, localisable et comptable.

**C'est la classe la plus facile à noter du document** : l'appartenance y est
entièrement mécanique, donc la vérité de référence se **constate** au lieu de se
juger. Aucun annotateur n'est requis, ce qui la rend disponible même sous **R-05**.

**Statut au périmètre.** Dedans, sous réserve que le corpus porte les versions.
S'il ne les porte pas, la classe existe et n'est pas servie - ce qui se déclare
plutôt que se cache.

---

### Q-04 - la pièce nommée sans référence

*mots du corpus × pièce*

**Définition.** L'usager vise une pièce unique, et sait qu'elle est unique, mais
la désigne par ce qu'elle a posé ou par l'intitulé qu'elle porte - jamais par son
identifiant.

**Critère discriminant.** La requête désigne une pièce **singulière** - un arrêt,
une loi, une décision - par une caractérisation, sans porter d'identifiant. La
singularité doit être dans la formulation : un pluriel ou une catégorie fait
basculer en Q-05.

**Spécimens.**
- « l'arrêt Baby-Loup »
- « l'arrêt qui a posé que le silence ne vaut pas acceptation »
- « la loi de 1978 sur l'informatique et les libertés »
- « la décision du Conseil constitutionnel sur la loi Hadopi »

**Frontières.**
- « les arrêts sur le port du voile en entreprise » → aucune singularité :
  **Q-05**
- « Cass. ass. plén. 25 juin 2014, n° 13-28.369 » → identifiant : **Q-01**
- « l'arrêt qui dit qu'on n'est pas obligé quand on n'a rien répondu » → la même
  visée, mais dans les mots de l'usager : **Q-10**. La frontière tient au
  spécimen ci-dessus - *le silence ne vaut pas acceptation* est la formule du
  corpus (art. 1120 du code civil), et c'est elle qui met la requête au cran 2.
  Une paraphrase tomberait au cran 4 × pièce, la case structurellement vide du
  §2.2 : sans les mots du corpus, on ne sait pas qu'il y a une pièce unique à
  viser, et la requête décrit un ensemble.

**Comportement attendu.** Identifier une pièce **par sa description** -
l'opération inverse de Q-01, où l'on résolvait un identifiant ; ici il faut en
produire un. La sortie utile de la classe est donc l'**identité canonique**
(périmètre, §4) : l'usager repart avec de quoi citer, ce qu'il ne pouvait pas
faire en arrivant.

**Mode d'échec dominant : le bruit non discriminé** - rendre cinq arrêts
plausibles sans que l'usager puisse dire lequel il visait. C'est la classe où le
bruit coûte le plus cher : n'ayant pas la référence, il n'a rien pour arbitrer.
L'exact inverse de Q-05, où le bruit est presque gratuit.

**Statut au périmètre.** Dedans.

---

### Q-05 - la règle et ses bornes

*mots du corpus × ensemble · classe centrale du groupe A*

**Définition.** L'usager tient le nom sous lequel le texte se désigne lui-même,
et vise la règle **avec ce qui la borne** : le principe et sa dérogation,
l'article et ses exceptions. Il ne connaît pas la cardinalité de ce qu'il
cherche, et ne peut donc pas constater qu'il en manque une part.

**Critère discriminant.** Trois conditions, toutes lisibles dans la seule
requête. La requête emploie un terme qui figure dans les textes qu'il désigne
(règle de frontière 2/3, §1.1). Elle ne nomme aucune dimension d'extension - sinon c'est
Q-06. Elle ne désigne pas une pièce unique identifiable - sinon c'est Q-04.

**Spécimens.**
- « le préavis de démission »
- « la garantie des vices cachés »
- « la prescription de l'action en paiement du salaire »
- « les règles de la rupture conventionnelle » - le terme est d'usage courant,
  mais c'est celui du code du travail (art. L1237-11) : cran 2, donc Q-05 et non
  Q-08

**Frontières.**
- « l'arrêt Baby-Loup » → une pièce unique nommée : **Q-04**
- « le préavis de démission, toutes les versions depuis 2008 » → une dimension
  est nommée : **Q-06**
- « puis-je démissionner sans préavis dans mon cas ? » → aucune forme visée, une
  conclusion demandée : **Q-12**

**Comportement attendu.** Restituer la règle et ce qui la borne, sans jamais
rompre un principe de sa dérogation. L'opération n'est pas seulement une
similarité sémantique : elle suppose de **suivre les liens juridiques** - renvois,
exceptions, place dans le plan, chaînes d'abrogation. La cardinalité est
déterminée par le droit et non par une constante de configuration : un `top-K`
fixe n'a aucune raison d'y tomber juste.

**Mode d'échec dominant : le silence** - et c'est le pire échec du projet. Une
exception manquante ne se signale pas. L'usager repart avec une règle **vraie et
incomplète**, plus confiant qu'avant de chercher : c'est la seule configuration
où Murphy peut nuire à quelqu'un qui n'aurait rien trouvé sans lui. Le bruit, à
l'inverse, y est presque gratuit - une pièce en trop se juge et s'écarte, et
**D-07** confie ce jugement à l'usager.

**Statut au périmètre.** Dedans.

---

### Q-06 - la série juridiquement nommée

*mots du corpus × série*

**Définition.** L'usager tient le vocabulaire juridique et demande une extension
exhaustive sur une dimension nommée.

**Critère discriminant.** Un terme que les textes visés portent, plus une
dimension explicitement énoncée - période, juridiction, nature de texte.

**Spécimens.**
- « les arrêts sur le harcèlement moral depuis 2015 »
- « toutes les décisions de la chambre sociale sur la clause de non-concurrence
  entre 2018 et 2022 »
- « l'état du droit sur le préavis de démission au 1er janvier 2020 »

**Frontières.**
- « les arrêts sur le harcèlement moral » → aucune dimension : **Q-05**
- « toutes les versions de L1152-1 depuis 2015 » → identifiant : **Q-03**

**Comportement attendu.** Filtrer sur les métadonnées **et** franchir l'écart
sémantique du cran 2. C'est la classe qui compose les deux opérations les plus
dissemblables du document : un filtre exact et une recherche approchée.

**L'appartenance y est mixte, et c'est ce qui la sépare de Q-03.** En Q-03,
l'appartenance est entièrement mécanique. Ici, elle combine un critère mécanique
- la période - et un critère de **fond** - « sur le harcèlement moral » - qui
demande un jugement. **Q-06 n'est donc pas notable sans annotateur**, à la
différence de Q-03 : la porte de sortie ouverte au §1.2 ne vaut que pour les
séries à appartenance mécanique.

**Mode d'échec dominant : le trou, partiellement localisable seulement.** Un
manque sur la dimension se compte ; un manque sur le fond ne se voit pas.

**Statut au périmètre.** Dedans.

---

### Q-07 - le texte derrière le nom

*nom d'emprunt × pièce*

**Définition.** L'usager tient le nom d'emprunt et cherche **la** pièce que ce
nom recouvre - celle qu'il pourra citer.

**Critère discriminant.** Un nom d'usage absent des textes qu'il désigne (règle
de frontière 2/3), plus une visée singulière.

**Spécimens.**
- « la loi Badinter »
- « le texte qui fonde la prime Macron »
- « quel décret a créé la prime de Noël »
- « la loi Toubon »

**Frontières.**
- « les règles de la loi Badinter » → le régime entier : **Q-08**
- « la loi du 5 juillet 1985 sur les accidents de la circulation » → le même
  texte, désigné cette fois par son intitulé, qui est dans le corpus : cran 2,
  donc **Q-04**

**Comportement attendu.** Une **correspondance** nom d'emprunt → nom légal, puis la
résolution d'une pièce. La correspondance est l'opération propre du cran 3 : elle
se tabule, donc elle se construit et se vérifie. Comme en Q-04, la sortie utile
est l'identité canonique.

**La correspondance est plurielle.** Un nom d'emprunt peut désigner plusieurs
textes sans rapport entre eux : « la loi Pinel » est la loi du 18 juin 2014 sur
l'artisanat et le commerce **et** le dispositif fiscal d'investissement locatif de
la loi de finances pour 2015 - deux textes, une ministre en commun. Le système
rend alors les deux, et l'usager restreint au tour suivant (**D-07**). La forme
visée reste **la pièce** : c'est la correspondance qui est plurielle, pas la visée
de l'usager. La table va donc d'un nom vers un **ensemble énuméré**, jamais vers
un texte - c'est une spécification pour la phase 2, et l'énumération est ce qui
rend la classe notable.

**Mode d'échec dominant : la correspondance fausse** - rendre le texte d'un
objet voisin. Le silence y est trompeur : l'usager n'a aucun moyen de
distinguer un nom qui ne recouvre aucun texte unique - ce qui arrive
- d'une correspondance qui a manqué.

**Statut au périmètre.** Dedans.

---

### Q-08 - le régime derrière le nom

*nom d'emprunt × ensemble*

**Définition.** L'usager tient le nom d'emprunt et veut le régime : conditions,
montants, procédure, voies de recours.

**Critère discriminant.** Un nom d'emprunt, une visée d'ensemble, aucune
dimension nommée.

**Spécimens.**
- « les règles de la loi Badinter »
- « les conditions du chèque inflation »
- « ce que prévoit la loi Toubon »
- « à quoi sert le Cerfa 14952 » - un numéro Cerfa est un nom donné par
  l'administration à une procédure, donc un nom d'emprunt. Le formulaire lui-même
  n'est pas dans le corpus : c'est le régime qu'il sert qui est rendu, et la
  substitution se déclare (**§0**)

**Frontières.**
- « les règles de la rupture conventionnelle » → cran 2 : **Q-05**
- « le texte qui fonde la prime Macron » → une pièce : **Q-07**

**Comportement attendu.** La correspondance du cran 3, puis l'opération de Q-05.
La complétude de l'ensemble (§1.2) y prend une forme fréquente et reconnaissable :
**certains objets répartissent leur régime sur deux étages** - la loi ou le code
d'un côté, le décret ou l'arrêté de l'autre, où se trouvent barèmes et montants.
C'est le gestionnaire de paie du §2, qui « articule deux étages de norme, jamais
un texte isolé ».

**C'est une propriété de l'objet, non du cran.** Les prestations et les
dispositifs à barème ont deux étages ; la loi Toubon n'en a qu'un. Le cran ne
prédit pas lequel - il ne dit que d'où vient le nom. Cette ligne n'est donc pas
une particularité de Q-08, mais l'exigence du §1.2 appliquée, dont l'intensité
varie avec ce que le nom recouvre. C'est aussi pourquoi elle ne réintroduit pas un
classement par matière (**D-05**) : elle ne fonde aucune frontière de classe, elle
décrit une charge inégalement répartie à l'intérieur d'une classe.

**L'homonymie vaut ici aussi** (Q-07) : « les règles de la loi Pinel » vise deux
régimes sans rapport, et les deux sont rendus. Avec une exigence que la forme
*ensemble* ajoute - ils doivent rester **séparés à la lecture**. Deux régimes
fondus en une liste plate sont pires qu'un seul choisi au hasard : l'usager y
lirait comme un tout des conditions qui ne vont pas ensemble.

**Mode d'échec dominant : le silence de l'ensemble**, comme en Q-05, et sa forme
la plus tranchante est l'**étage manquant**. Restituer le code sans le barème
produit une réponse complète en apparence et inutilisable en fait - la condition
et le montant ne sont pas dans le même texte. La correspondance fausse menace la
classe elle aussi, mais c'est le risque de tout le cran, décrit en Q-07.

**Statut au périmètre.** Dedans.

---

### Q-09 - le nom dans le temps

*nom d'emprunt × série*

**Définition.** L'usager tient le nom d'emprunt et demande l'extension sur une
dimension : versions successives, montant à une date, textes annuels.

**Critère discriminant.** Un nom d'emprunt, plus une dimension nommée.

**Spécimens.**
- « les versions successives de la prime Macron »
- « le montant de la prime de Noël en 2019 »
- « la loi Badinter dans sa version applicable en 1995 »

**Frontières.**
- « le montant de la prime Macron » → sans date, le défaut est la version en
  vigueur : **Q-08**
- « toutes les versions de l'article L845-1 » → identifiant : **Q-03**

**Comportement attendu.** Correspondance, puis énumération datée. C'est la classe
de l'agent instructeur et du gestionnaire de paie, qui doivent appliquer le droit
**à la date des faits** et non à celle du jour.

**Le nom peut durer alors que le texte change de titre.** La prime Macron a porté
deux noms légaux - *prime exceptionnelle de pouvoir d'achat* jusqu'en 2022, puis
*prime de partage de la valeur*. La série est alors l'**union** des chaînes, et
c'est l'union qui définit l'exhaustivité : une version manque si elle manque à
l'union, quel que soit le nom sous lequel elle a été prise. L'homonymie de Q-07
produit le même geste par une autre cause.

**Ce que l'union coûte.** Décider que deux noms portent le même objet est une
décision **éditoriale**, que rien dans le corpus ne tranche. Elle reste bon marché
- une par nom porté, non une par document - ce qui maintient Q-09 au degré
**ancré** du §1.2. Mais elle peut être fausse, et sa fausseté ne se constate pas :
c'est un legs à la **phase 2**, avec l'exposition à **R-08**.

**Mode d'échec dominant : le silence déguisé en réponse.** Rendre la version
courante quand une version passée était demandée n'est ni du bruit ni un trou :
c'est une réponse bien formée et fausse, qu'aucun signal ne distingue d'une bonne.
C'est le seul mode d'échec du document qui échappe au couple bruit/silence, et
c'est le plus dangereux de tous - un barème périmé est faux sans en avoir l'air.

**Statut au périmètre.** Dedans, sous la même réserve de versionnage que Q-03.

---

### Q-10 - la situation décrite

*mots de l'usager × ensemble · classe centrale du groupe B*

**Définition.** L'usager décrit ce qui lui arrive, dans ses mots, sans reprendre
aucun terme du texte ni du dispositif, et vise l'ensemble des règles qui s'y
appliquent.

**Critère discriminant.** Aucun terme qui **nomme** l'objet juridique visé,
aucune dimension nommée, et une visée d'ensemble - des règles, non une
conclusion, sinon c'est Q-12. La condition porte sur les termes d'art, non sur
le lexique : toute phrase française emploie des mots que le corpus contient, et
« j'ai acheté une voiture qui tombe en panne » reste au cran 4 parce qu'elle ne
nomme ni le vice caché ni la garantie de conformité.

**Spécimens.**
- « mon patron me fait travailler plus que prévu et ne me paie pas plus »
- « le propriétaire ne me rend pas l'argent que j'avais versé en entrant »
- « mon père est décédé et il y a une maison »
- « j'ai acheté une voiture qui tombe en panne au bout d'une semaine »

**Frontières.**
- « ai-je le droit de refuser ? » → une conclusion est demandée : **Q-12**
- « le dépôt de garantie » → un terme du texte : **Q-05**

**Comportement attendu.** C'est ici que s'applique la décision de **récupération
large** (§1.1) : le système ne délimite pas l'objet à la place de l'usager, ne
désambiguïse pas, ne qualifie pas. Il restitue - et l'ensemble doit être
**lisible comme ensemble**, sa dispersion perceptible, faute de quoi l'usager ne
peut pas exercer le jugement que **D-07** lui confie.

**Mode d'échec dominant : le silence**, et il est ici **indistinguable de
l'absence de règle** : exactement le problème de §1, reconduit. C'est la classe
sur laquelle Murphy est jugé, parce que c'est celle que le moteur public ne sert
pas du tout.

**Statut au périmètre.** Dedans.

---

### Q-11 - le matériau sériel sans vocabulaire

*mots de l'usager × série*

**Définition.** L'usager décrit un phénomène dans ses mots et en demande
l'extension exhaustive sur une dimension nommée. C'est le chercheur non juriste
et le journaliste du §2 : le texte est un matériau, voulu en série et daté.

**Critère discriminant.** Aucun terme qui nomme l'objet juridique visé (Q-10),
mais une dimension explicitement énoncée.

**Spécimens.**
- « les jugements depuis 2020 où le patron n'a pas payé tout ce qu'il devait »
- « toutes les décisions de 2019 à 2023 où des gens ont été mis dehors de chez
  eux »
- « combien de procès par an depuis 2015 entre voisins d'un même immeuble »

**Frontières.**
- « les jugements où le patron n'a pas payé tout ce qu'il devait » → aucune
  dimension : **Q-10**
- « les arrêts sur le harcèlement moral depuis 2015 » → cran 2 : **Q-06**

**Comportement attendu.** Un filtre exact sur la dimension, et l'écart de
vocabulaire maximal sur le fond. **C'est la classe la plus dure du document** :
elle cumule l'exigence d'exhaustivité de la série et l'écart du cran 4, et les
deux se contrarient - l'exhaustivité demande une frontière nette, l'écart de
vocabulaire interdit qu'on en trace une.

**Mode d'échec dominant : le trou non localisable**, doublé d'un risque propre à
la classe, la **fausse précision** : un dénombrement porté sur un ensemble dont
l'appartenance est incertaine a l'apparence d'un fait. C'est la seule classe où
le résultat peut être republié comme une donnée.

**Statut au périmètre.** Dedans, avec réserve explicite : c'est la classe dont la
complétude est la moins garantissable. Un plancher de service plus bas y est
envisageable - à trancher en phase 3, pas ici.

---

### Q-12 - la demande de conclusion

*aucune forme visée · hors périmètre*

**Définition.** La requête ne décrit aucun ensemble de documents : elle demande au
système de conclure sur un cas - un droit, une obligation, une qualification, une
conduite à tenir.

**Critère discriminant.** **La valeur vide sur l'axe 2.** La requête porte un
registre de vocabulaire, souvent le cran 4, parfois le cran 2 - mais ne vise ni
pièce, ni ensemble, ni série. La signature est positive et lisible dans la
formulation seule : il n'y a aucune intention à deviner.

**Spécimens.**
- « ai-je le droit de licencier pour absences répétées ? »
- « est-ce que mon licenciement est abusif ? »
- « dois-je payer ces charges ? »
- « que dois-je faire ? »

**Frontières.**
- « les règles du licenciement pour absences répétées » → **Q-05**
- « mon patron me met dehors parce que j'ai été malade » → une situation décrite,
  pas une conclusion demandée : **Q-10**. C'est la frontière la plus délicate du document,
  et le §0 la tranche : on classe la formulation, jamais le besoin qu'on lui
  suppose.

**Comportement attendu.** Le **refus explicite** (**D-03**), qui dit ce qui est
hors de portée et **ce qu'il faut reformuler**. Le refus porte sur la phrase,
jamais sur le besoin. La porte est franchissable par reformulation, et
volontairement : qui veut une qualification l'obtiendra en posant une requête de
récupération puis en concluant lui-même - c'est ce que D-03 organise.

**Mode d'échec dominant : deux, symétriques et tous deux graves.** Le **faux
négatif** - traiter une demande de conclusion comme une récupération - fait
qualifier le système, et c'est **R-04**, la requalification en conseil juridique.
Le **faux positif** - refuser une requête de récupération légitime - ferme le
service à celui qui formule maladroitement, c'est-à-dire précisément au groupe B,
celui pour qui le projet existe. Un refus trop large trahit le §1 aussi sûrement
qu'un silence.

**Statut au périmètre.** **Dehors.** Seule classe hors périmètre du document, et
retenue à ce titre : un périmètre qu'on ne sait pas reconnaître à l'entrée n'est
pas un périmètre.

---

## 4. Ce qui est légué

Chaque fiche a signalé au passage ce que sa classe demande à une phase
ultérieure. Ils sont rassemblés ici pour être lus ensemble : dispersés, ils se
perdent ; groupés, ils se comptent. **Rien n'y est nouveau** - tout est déjà
énoncé au-dessus, et c'est la condition pour que cette section reste un
inventaire et non une décision de plus.

### 4.1 À la phase 2 - le corpus

**Les liens juridiques.** Q-02, Q-05 et Q-08 ne se servent pas sans eux :
renvois, exceptions, dérogations, place dans le plan, chaînes d'abrogation, et
les **textes pris pour l'application**, qui portent le second étage des
dispositifs à barème. Le §1.2 a déplacé cette exigence du côté connaissable - ce
que *le droit lie* est une propriété des documents, non une intention à deviner -
mais au prix d'une dépendance entière : si le corpus ne porte pas la liaison,
elle ne se fabrique pas.

**Le versionnage.** Q-03 et Q-09 en sont des conditions d'existence, non des
améliorations. Sans versions, les deux classes existent et ne sont pas servies -
ce qui se déclare plutôt que se cache.

**La table des noms d'emprunt.** Elle va d'un nom vers un **ensemble énuméré**,
jamais vers un texte unique : l'homonymie (Q-07, « la loi Pinel ») et le
renommage (Q-09, la prime Macron) l'exigent l'un et l'autre. C'est elle qui fait
exister le cran 3 ; sans elle, Q-07, Q-08 et Q-09 se traitent comme du cran 4.

**La décision d'identité entre noms successifs.** Dire que la *prime de partage
de la valeur* est la même prime que la *prime exceptionnelle de pouvoir d'achat*
est une décision **éditoriale**, que rien dans le corpus ne tranche. Bon marché -
une par nom porté, non une par document - mais faillible, et sa fausseté ne se
constate pas.

**L'inventaire des trous** (§0), provisoires et définitifs, avec une échéance
pour les premiers.

**Une charge à déclarer plutôt qu'à glisser.** La table et la décision d'identité
sont de la **matière éditoriale** - la couche que la note de cadrage (§1) décrit
comme privée, payante, et dont l'inaccessibilité *est* le problème traité. Les
construire ne contredit pas **D-03** : une correspondance n'est pas une
interprétation. Mais c'est un engagement de production et de maintenance
qu'aucun document ne porte aujourd'hui.

Tout ce tas est exposé à **R-08**.

### 4.2 À la phase 3 - la mesure

**Un ordre de travail, donné par les trois degrés d'appartenance du §1.2.**
Commencer par ce qui se **constate** - Q-03, où l'exhaustivité se compte et où
aucun annotateur n'est requis. Puis l'**ancré** - Q-09, un jugement par nom
porté, puis rien. N'engager d'annotateurs que sur le **mixte** - Q-06 et Q-11, où
l'appartenance combine une dimension et un critère de fond. **R-05** étant à 🟥 en
T0, cet ordre n'est pas une commodité : c'est ce qui permet de commencer.

**Q-02 est le banc d'essai du suivi de liens.** L'ancre y étant exacte, un manque
s'impute au graphe et non à la récupération. Si le suivi échoue là, il échouera
partout, et nulle part ailleurs le diagnostic ne sera aussi net.

**Le mode d'échec de Q-09 est à instrumenter** - *le silence déguisé en réponse*,
une réponse bien formée et fausse qu'aucun signal ne distingue d'une bonne. C'est
le seul mode d'échec du document qui échappe au couple bruit/silence.

**Le plancher de service de Q-11 est à trancher**, et plus bas qu'ailleurs : sa
complétude est la moins garantissable du document.

**Les annotations de cran doivent être datées**, ou le cran recalculé au moment
de noter (§0).

**L'axe 3 est déjà enregistré comme attribut de chaque spécimen** (§2.1) : la
phase 3 pourra trancher ses mesures par inflexion si elle en a besoin, sans qu'on
ait figé aujourd'hui des distinctions qu'on ne sait pas encore réelles.

### 4.3 Au cahier des charges fonctionnel

**L'ensemble doit être lisible comme ensemble.** C'est la première exigence
énoncée du document (§1.1) : sans dispersion perceptible, la récupération large
de Q-10 est une impasse, et **D-07** confie pourtant à l'usager un jugement
qu'une liste plate lui interdit d'exercer. L'homonymie l'a redoublée : en Q-07 et
Q-08, deux objets sans rapport peuvent revenir ensemble, et ils doivent rester
**séparés à la lecture**.

**Les inflexions doivent être formulables.** Si l'élargissement et le
resserrement se lisent dans la phrase (§1.3), l'interface doit rendre ces gestes
disponibles : un usager qui ne sait pas qu'il peut écrire « uniquement » ne
pilote rien.

**Le refus doit dire quoi reformuler** (Q-12). Il porte sur la phrase, jamais sur
le besoin, et la porte reste franchissable par reformulation - volontairement.

**La cardinalité est déterminée par le droit** (Q-02, Q-05), non par une
constante de configuration : un `top-K` fixe tronque la série par construction et
n'a aucune raison de tomber juste sur l'ensemble.

**La substitution doit se déclarer** (§0) : quand le système rend l'entourage
juridique d'un objet qu'il n'a pas, il doit dire qu'il l'a fait.
