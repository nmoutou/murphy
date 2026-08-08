# ADR-034 — Paradigmes d'évaluation : fonctionnel, contenu, usage — séparation et triangulation

**Statut** : Acté (1er août 2026, session de cadrage) — ~~**prolonge ADR-033**
(qui fixe l'axe, celui-ci fixe le cadre d'échantillonnage)~~, **amende la
direction** de `GOLDEN-SET.md` §7, ~~**ne touche à aucun axe**~~

> ## ⚠️ Les deux clauses barrées du statut sont fausses — marqueur posé le 7 août 2026
>
> Ce fichier ne portait **aucun marqueur** jusqu'ici, alors que ses amendements étaient
> enregistrés depuis le 1er août dans [`INDEX.md`](INDEX.md). Un lecteur arrivant
> directement sur l'ADR lisait donc un texte périmé sans avertissement. Réparé ici ;
> la **réécriture d'ensemble reste ADR-036**, à la clôture de la carte
> [#1](https://github.com/left-eyebr0w/murphy/issues/1).
>
> - ⛔ **« prolonge ADR-033 » est caduque** : ADR-033 est **obsolète** depuis le 1er août.
>   Seul survit son axe primaire — les mécanismes. La grille des quatorze cellules, la
>   cardinalité comme second axe et les douze strates sont tombées.
> - ⛔ **« ne touche à aucun axe » est faux dans ses effets** : le §Constat ci-dessous
>   **commandait** le tri des mécanismes, et son amendement par
>   [#2](https://github.com/left-eyebr0w/murphy/issues/2) a redécoupé la liste.
>
> **Ce qui survit, et c'est l'essentiel** : le §Constat — *le label gratuit et le besoin
> réaliste s'excluent* — est **indépendant de la grille disparue** et il tient. C'est le
> §1 et le §5 qui s'appuient sur elle. **Vocabulaire** : cet ADR emploie des noms de
> mécanismes dont trois sont morts depuis — voir le cimetière en tête de chaque section
> concernée.

## Contexte

ADR-033 a fixé ce qu'on teste — le mécanisme de récupération exercé. Il laisse
ouvert ce qu'il ne pouvait pas fixer : **le cadre d'échantillonnage**. Un axe
dit quoi écrire ; il ne dit pas si ce qu'on a écrit représente quoi que ce soit.

Le chantier `docs/droit/taxomonie/`, repris de zéro le 31 juillet 2026, visait
exactement ce cadre : une taxonomie du droit fournirait le dénominateur qui
manque. La question posée en session était donc : **peut-on s'en passer ?**

La réponse est oui pour la v0 — mais pas gratuitement, et le prix a un nom.

## Le constat qui commande le reste

> ⚠️ **Amendé, non renversé — 1er août 2026**
> ([#2](https://github.com/left-eyebr0w/murphy/issues/2)). Le **test unique** de cette
> section est remplacé par **deux propriétés indépendantes** : la **source de gratuité du
> label** (quel fait extérieur à l'opinion détermine l'ensemble-réponse — `identite` ou
> `graphe_g0` ; un blanc est un défaut) et le **réalisme de la requête** (le test ci-dessous,
> rendu à son objet propre). **L'exclusion ne vaut que pour la source `identite`** : elle
> n'est pas une loi générale, et c'est ce qui a permis à quatre mécanismes d'être gratuits
> *sans* être artefactuels. Le constat lui-même **tient** et ne dépend d'aucune grille.
>
> ⛔ **Vocabulaire mort dans cette section** : la troisième source de gratuité,
> `frontiere_corpus`, a été **retirée** le 5 août ([#15](https://github.com/left-eyebr0w/murphy/issues/15)) —
> elle s'indexait sur un **état** (le corpus ingéré) là où le rang 1 exige une
> **définition** ; le mécanisme qu'elle portait tire désormais son label du **périmètre
> DILA** et s'appelle `absence_attendue`
> ([#12](https://github.com/left-eyebr0w/murphy/issues/12)).
>
> ⚠️ **Le corollaire final est dépassé** : `correspondance_litterale` échoue bien ce test,
> mais il a **quitté le golden-set** le 1er août pour les instruments diagnostiques
> ([#10](https://github.com/left-eyebr0w/murphy/issues/10)) — il n'est plus un mécanisme à
> requalifier, il est dehors, et son résultat se publie **en tête du rapport comme condition
> de lecture**.

> **Le label gratuit et le besoin réaliste s'excluent.**

Le coût du label est fixé par une seule chose : le **sens de dérivation** du cas
de test.

| Sens | Ce qu'on gagne | Ce qu'on perd |
|---|---|---|
| **Document d'abord** — la requête descend de la cible | Le label est un **fait d'authoring** : gratuit, objectif, R-05 esquivé | Rien ne garantit que quiconque poserait cette question. Le réalisme n'est pas établi |
| **Besoin d'abord** — la requête vient en premier | Le réalisme est acquis par construction | L'ensemble-réponse doit être **jugé** : coût d'expertise, R-05 revient |

Ce n'est pas un arbitrage qu'on pourrait contourner par une meilleure ingénierie
d'authoring : les deux propriétés sont des conséquences du **même** choix, donc
elles s'excluent. Tout cas gratuit est suspect de non-réalisme, et tout cas
réaliste coûte du jugement.

**Portée.** Le constat déborde le projet. Toute collection de test construite en
dérivant les requêtes des documents mesure la *retrouvabilité*, pas l'*utilité* —
c'est la raison pour laquelle la méthodologie TREC pose les *topics* d'abord et
constitue les jugements ensuite par pooling. Le coût du jugement est le prix du
réalisme ; il n'est pas évitable, seulement déplaçable.

**Exception, et elle est réelle.** Il existe une famille où la tâche
*elle-même* est descendante : celui qui détient une référence et veut le
document. `resolution_reference` (« article 1240 du Code civil » → l'article) et
`known_item_identifiant` (ECLI, n° de pourvoi → la décision) reproduisent
fidèlement ce geste. Là, le sens de dérivation n'est pas un artefact et le label
est gratuit **et** réaliste.

Le test qui reconnaît l'exception :

> **L'utilisateur réel arrive-t-il en tenant déjà l'identité de la cible ?**
> Si oui, « document d'abord » est fidèle. Si non, c'est un artefact.

Corollaire indépendant : `correspondance_litterale` échoue ce test — personne ne
cite un chunk verbatim pour le retrouver. Ce qui confirme, par une seconde voie,
sa requalification en test de fumée.

## Décision

### 1. Trois paradigmes, spécifiés comme instruments distincts

> ⚠️ **La colonne « Fonctionnel (ADR-033) » renvoie à un ADR obsolète** — lire **ADR-036**,
> et « aucun cadre d'échantillonnage » y est désormais **assumé et écrit**, non plus
> constaté en creux ([#4](https://github.com/left-eyebr0w/murphy/issues/4) : *le jeu
> n'échantillonne pas le droit, il énumère des fonctions*). **La séparation des trois
> instruments tient** ; c'est le seul point du §1 qui ne dépende pas de la grille disparue,
> et [#9](https://github.com/left-eyebr0w/murphy/issues/9) l'a même **durci** en énonçant le
> critère qui manquait : *un instrument est séparé quand il a ses propres cas, pas quand il
> a sa propre lecture*.

| | Organise par | Cadre d'échantillonnage | Répond à | Aveugle à |
|---|---|---|---|---|
| **Fonctionnel** (ADR-033) | la fonction de récupération exercée | aucun | « la récupération marche-t-elle ? » | l'importance des questions posées |
| **Contenu** (`docs/droit/taxomonie/`) | la région du droit | lui-même | « la couverture est-elle régulière ? » | la mécanique de récupération |
| **Usage** (panel, ADR-025) | ce qui est effectivement demandé | la distribution de la demande | « le service répond-il aux besoins réels ? » | tout ce que personne n'a encore demandé |

**Ils ne se fusionnent pas**, et c'est une décision, pas une commodité : ce sont
des réponses à **trois questions différentes**. Les fondre en une grille unique
serait une erreur de catégorie, et réintroduirait le contenu comme axe — ce que
tout le renversement d'ADR-033 visait à éviter.

En particulier : **la taxonomie n'a jamais été un paradigme concurrent de la
note.** Elle est une tentative de fournir le cadre d'échantillonnage que le
paradigme fonctionnel ne fournit pas. Les deux chantiers opèrent à des niveaux
différents, pas sur le même terrain.

### 2. Le paradigme usage n'est pas un complément, il est structurel

Par le constat ci-dessus : la v0 achète l'objectivité en payant le réalisme. Les
testeurs sont la **seule** source qui rachète le réalisme. Le recours au panel
cesse donc d'être une couverture optionnelle sur une faiblesse — c'est la seule
entrée de réalisme du dispositif.

Ce qui déplace entièrement la question de rigueur : elle ne porte plus sur
l'opportunité du pari, mais sur son **instrumentation**.

### 3. Le capteur — ce qui rend le pari réfutable

> ⚠️ **Le 2×2 ci-dessous survit comme *intention*, pas comme structure de sortie** — 5 août
> 2026 ([#5](https://github.com/left-eyebr0w/murphy/issues/5)). Trois choses ont changé
> et un lecteur qui construirait le capteur sur cette section seule se tromperait :
> (1) **le capteur émet une énumération d'items, jamais un taux** — le résidu comme
> proportion est illisible à l'effectif d'alpha ph.1 ; (2) **il n'y a pas de routeur** :
> c'est le **testeur** qui déclare, par verdict binaire puis liste fermée d'hypothèses en
> langue de mode d'échec, une table déclarée *a priori* traduisant vers les mécanismes —
> ce qui rend la contamination **structurellement impossible** et remplace la règle d'ordre
> ci-dessous par une garantie plus forte ; (3) la ligne « **le testeur réussit** » n'est
> **plus classée** — la case *faux positif* est vide et inactionnable, aucun cas ne pouvant
> être retiré de la v0. **La règle d'ordre reste juste** dans son motif, elle n'est
> simplement plus le dispositif qui l'assure. La **construction** du capteur est hors carte.

Un golden-set biaisé n'échoue pas bruyamment : **il échoue en rassurant.** Il
continue de produire de bons chiffres pendant que la zone qu'il ne couvre pas se
dégrade. Le tâtonnement exige que l'erreur soit détectable ; celle-ci ne l'est
pas sans instrument dédié.

L'observation « le système a un trou » et l'observation « la suite a un trou »
ne sont **pas équivalentes** — leur croisement est ce qui informe :

| | La suite prédisait l'échec | La suite ne le prédisait pas |
|---|:---|:---|
| **Le testeur échoue** | Trou système connu → travail de développement | **Trou de la suite** → travail d'échantillonnage |
| **Le testeur réussit** | **Faux positif de la suite** → cas dur artificiellement, candidat au retrait | rien (ou zone non explorée) |

Le signal de calibration est le **résidu** : la part des échecs testeurs que la
suite n'avait pas anticipés, suivie dans le temps.

**Règle d'ordre, non négociable** : la suite tourne et ses prédictions sont
**figées avant** consultation des retours testeurs. Relire les prédictions à la
lumière du résultat annule le capteur.

### 4. Pas de seuil numérique

> ⚠️ **Portée restreinte — 2 août 2026** (session d'audit de la carte
> [#1](https://github.com/left-eyebr0w/murphy/issues/1)). Ce §4 vaut pour une
> **sentinelle** : une grandeur qu'on observe et dont la direction s'interprète seule (taux
> de réussite ventilé d'E-P2-07, taux de rejet à l'authoring, stabilité du classement). Il
> **ne vaut pas** pour la **résolution de l'instrument** qui observe — là, « on publiera
> sans seuil » ne dit rien d'autre que *« on ne sait pas si c'est lisible »*. Motif :
> **quatre** questions quantitatives de la carte avaient reçu la même réponse en invoquant
> ce §4, faute d'une seconde issue de secours. **Première application de la restriction** :
> le contrôle d'auto-cohérence des assesseurs reçoit **un seuil obligatoire** (≥ +0,49,
> [#18](https://github.com/left-eyebr0w/murphy/issues/18) §2), précisément parce qu'il *est*
> la résolution de l'instrument.
>
> **L'issue de secours a un nom** ([#5](https://github.com/left-eyebr0w/murphy/issues/5)) :
> ***cesser d'agréger plutôt que baisser le seuil***. **Sept** fois la carte a rencontré un
> agrégat illisible, sept fois la sortie a été de **garder la structure sous-jacente au lieu
> de la réduire à un nombre**. À essayer **avant** d'invoquer ce §4.
> *(Compte corrigé le 8 août 2026 : il était resté à cinq. Sixième instance —
> [#23](https://github.com/left-eyebr0w/murphy/issues/23), la largeur appariée par document
> contre `r_A+r_B` ; septième — [#19](https://github.com/left-eyebr0w/murphy/issues/19), le
> versant *inter* de l'accord entre assesseurs, qui refuse le kappa au profit d'une
> ventilation par porte.)*
>
> ⚠️ **Un candidat examiné et écarté le 8 août 2026, pour que le compte ne dérive pas dans
> l'autre sens** : la **famille sentinelle de `p`** d'ADR-007 §4 réécrit
> ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) **n'est pas** une huitième
> instance. La faute réparée n'était pas une **somme prise trop tôt** — signature de
> l'idiome — mais une **dérivation depuis la mauvaise source** (`p` tiré de l'effort
> d'annotation au lieu du lecteur), et une **grandeur de décision unique est conservée**.
> C'est le motif d'une **sentinelle** (§4 ci-dessous : seuil facultatif), non celui d'un
> refus d'agréger. **Le compte reste à sept.**
>
> ⚠️ **Précision du 8 août 2026** ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) —
> **un seuil n'est pas nécessairement un nombre.** La restriction ci-dessus exige qu'une
> résolution d'instrument porte un seuil ; elle **n'exige pas** qu'il soit numérique. Sa
> **seconde application** en est la preuve : la porte q1 de l'accord inter-assesseurs reçoit
> un seuil **structurel** — *zéro désaccord inattribuable à un défaut de cas réparable* —
> qui peut échouer, donc qui satisfait ce §4 sans chiffre. Sans cette précision, un lecteur
> jugerait ce seuil non conforme et chercherait à lui inventer une valeur.

On pré-enregistre **la grandeur, sa direction et l'engagement à la publier** ;
pas de valeur de déclenchement. Un seuil dont on ignore ce qu'il vaut ne rend pas
le test réfutable, il le rend *arbitrairement* réfutable — et le jour où il est
franchi, la discussion porte sur le chiffre au lieu de porter sur l'observation.

Formulation retenue : *« on suit la part des échecs testeurs que la suite n'avait
pas prédits ; elle est publiée à chaque run ; on n'a pas de seuil parce qu'on ne
sait pas ce qu'il vaut — les premiers runs servent à établir sa distribution. »*

Le seuil devient alors **dérivé de sa propre distribution** au lieu d'être
inventé. C'est ADR-012 appliqué au dispositif de mesure lui-même : mesurer plutôt
qu'affirmer.

### 5. Triangulation, jamais fusion

Les instruments s'auditent mutuellement **a posteriori**, sans jamais se
contraindre :

- le paradigme contenu passe **par-dessus** la suite et rapporte où tombent les
  cas — diagnostic, jamais obligation de couverture. ~~ADR-033 le fait déjà à
  moitié (« la matière est équilibrée au mieux ; ses trous sont permis et
  **chiffrés** »)~~ ; ce qui est neuf est de le nommer comme un **second
  instrument**, non comme un tag ;

  > ⛔ **L'appui barré est mort deux fois** : `matiere` a disparu comme facette
  > ([#10](https://github.com/left-eyebr0w/murphy/issues/10), puis
  > [#12](https://github.com/left-eyebr0w/murphy/issues/12) qui l'identifie au tag `domaine
  > juridique` et clôt le reliquat), et **les trous ne sont plus chiffrés** — `GOLDEN-SET.md`
  > §6.2 est mort en entier ([#4](https://github.com/left-eyebr0w/murphy/issues/4), YAGNI du
  > porteur : un chiffre nu, non pondéré, aucune estimation de production). **Le second
  > instrument survit, son point d'accroche est explicitement ajourné** : tant que la
  > taxonomie n'existe pas, on ne conçoit pas son accroche — décision, non flou.
- le paradigme usage audite le paradigme fonctionnel par le capteur du §3.

**Ce que la triangulation achète, et c'est sa seule justification sérieuse :** on
ne peut pas mesurer un biais, mais on peut mesurer la **divergence entre deux
instruments** — et une divergence qui croît est un signal de dérive, même quand
on ne peut pas attribuer la dérive à l'un des deux. C'est le seul moyen
disponible d'apercevoir les dérives non mesurables directement.

Précédent interne : ADR-033 fonde explicitement son propre poids sur le fait que
la note de session était une « dérivation indépendante ». La pratique existait
déjà ; elle est ici érigée en dispositif.

## Alternatives rejetées

- **Construire la taxonomie comme cadre d'échantillonnage de la v0.** Rejetée
  comme prématurée, non comme fausse. Dans un domaine *wicked*, le cadre ne se
  dérive pas a priori ; et le faire porter par la v0 réintroduirait le contenu
  comme axe engageant. Le chantier reste ouvert **comme second instrument**.
- **Fusionner les paradigmes en une grille unique.** Erreur de catégorie (§1) et
  retour de la grille infinie.
- **Tirage aléatoire des germes** comme réponse au biais de sélection. Envisagée
  puis écartée, et la raison mérite d'être tracée : la randomisation corrige la
  représentativité du **germe** et ne touche pas au **sens de dérivation**, qui
  est le vrai défaut. Un chunk tiré au hasard puis muni d'une question fabriquée
  produit un ensemble-réponse de cardinalité 1 par construction — on mesure
  l'auto-similarité d'un embedding, pas la reconstitution d'un ensemble
  pertinent. Elle survit sur un objet étroit : choisir **quelles** références
  tester dans la famille d'exception (§*Constat*), pour ne pas retomber
  systématiquement sur les articles célèbres.
- **Accepter le biais et le documenter sans capteur.** Documenter un biais de
  sélection suppose de nommer ce qu'on a sur- et sous-échantillonné *par rapport
  à quoi* — donc un dénominateur, donc le cadre qu'on n'a pas. Sans capteur, la
  documentation honnête se réduit à « ces cas ont été choisis par une personne
  selon son intuition », ce qui est vrai et inexploitable.

## Conséquences

- **La v0 démarre petit, et c'est une conséquence, pas une économie.** Si le
  réalisme n'arrive qu'avec les testeurs, sur-investir l'authoring pré-panel
  achète du volume artefactuel. Direction retenue : privilégier une suite
  restreinte sur les mécanismes dont le sens de dérivation est **fidèle**, plutôt
  qu'une suite large majoritairement artefactuelle. Les nombres de
  `GOLDEN-SET.md` §7 sont à re-dériver sous cette direction — ils relevaient
  déjà du régime **humain** (ADR-028) et n'étaient pas actés.
  ✅ *Fait le 1er août par [#11](https://github.com/left-eyebr0w/murphy/issues/11)* : la
  dérivation est devenue **ascendante** (unité = le mécanisme, `N_cas` est une somme de
  planchers, jamais un total réparti), plancher **30 cas/mécanisme** par la règle de trois,
  **v1 = 150 cas**, `N_q ≥ 180`. Le mot `N_j` est sorti du vocabulaire au passage.
- **Les mécanismes gagnent une propriété distincte du régime.** La colonne
  `Régime` d'ADR-033 dit d'où vient le **label** ; il manque **le sens de
  dérivation** (fidèle / artefactuel), qui dit ce que le cas vaut en réalisme.
  Deux propriétés aujourd'hui confondues, à séparer dans `GOLDEN-SET.md` §4–§5.
  ✅ *Séparées le 1er août par [#2](https://github.com/left-eyebr0w/murphy/issues/2)*, mais
  **pas sous ces noms** : ce sont la **source de gratuité du label** et le **réalisme de la
  requête**, et elles sont **indépendantes** — c'est tout l'objet de l'amendement du
  §Constat. ⚠️ Et la propriété est celle du **mécanisme**, jamais une déclaration par cas
  ([#10](https://github.com/left-eyebr0w/murphy/issues/10)) : le test s'exerce **une fois, à
  l'admission d'un mécanisme**.
- **Le capteur du §3 est un prérequis du pari, pas un agrément.** À implémenter
  au harnais avant que le panel produise des retours exploitables (rattachement
  ADR-025 / ADR-027).
- **Le chantier taxonomie n'est ni abandonné ni bloquant.** Il devient le second
  instrument, sur son propre calendrier, et cesse d'être sur le chemin critique
  de B-08.
- ⛔ ~~**Hors périmètre de cet ADR**, et toujours en attente : la rétrogradation de la
  cardinalité en attribut, la renumérotation des mécanismes, le statut du tag
  `domaine juridique`, le resserrement de la cardinalité 0. Ces points amendent
  ADR-033 et seront traités ensemble.~~

  > **Ce reliquat est éteint — 7 août 2026.** Les quatre points sont clos, et pas dans le
  > sens annoncé : la cardinalité **ne se rétrograde pas, elle se dissout** — `0/1/n` est un
  > **compte** (`R = len(qrels)`, gratuit, jamais asserté), et le mot sort du vocabulaire
  > ([#3](https://github.com/left-eyebr0w/murphy/issues/3)), ce qui emporte au passage le
  > **resserrement de la cardinalité 0** ; le **tag `domaine juridique`** est `matiere` sous
  > son nom d'ADR-033, **morte avec les strates**
  > ([#12](https://github.com/left-eyebr0w/murphy/issues/12)) ; la **renumérotation** est
  > arrêtée — liste **7**, composition v1 **5**, noms fixés
  > ([#16](https://github.com/left-eyebr0w/murphy/issues/16), #12) — et il ne reste que
  > l'**acte d'écriture**, en ADR-036.

## Références

ADR-007 (métriques) · ADR-012 (constat sur preuves — fondement du §4) ·
ADR-016 (découplage récupération/génération) · ADR-017 (strates) · ADR-025
(environnement panel consenti — porteur du paradigme usage) · ADR-027
(plateforme d'évaluation end-to-end — hôte du capteur) · ADR-028 (frontière
vérification/validation) · ~~**ADR-033 (prolongé : il fixe l'axe, celui-ci fixe le
cadre)**~~ ⛔ **obsolète — lire ADR-036** · ADR-035 (paradigme TREC, ADR de méthode : il
arbitre cet ADR et non l'inverse) · ADR-037 (provenance d'authoring) · `GOLDEN-SET.md` §4,
§5, §7 — **tous trois estampillés périmés** dans le fichier · `docs/droit/taxomonie/`
(second instrument) · R-05 (`RISQUES.md`) ·
[carte #1](https://github.com/left-eyebr0w/murphy/issues/1)
