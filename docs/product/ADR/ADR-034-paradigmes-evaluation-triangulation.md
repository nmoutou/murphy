# ADR-034 — Paradigmes d'évaluation : fonctionnel, contenu, usage — séparation et triangulation

**Statut** : Acté (1er août 2026, session de cadrage) — **prolonge ADR-033**
(qui fixe l'axe, celui-ci fixe le cadre d'échantillonnage), **amende la
direction** de `GOLDEN-SET.md` §7, **ne touche à aucun axe**

## Contexte

ADR-033 a fixé ce qu'on teste — le mécanisme de récupération exercé. Il laisse
ouvert ce qu'il ne pouvait pas fixer : **le cadre d'échantillonnage**. Un axe
dit quoi écrire ; il ne dit pas si ce qu'on a écrit représente quoi que ce soit.

Le chantier `docs/droit/taxomonie/`, repris de zéro le 31 juillet 2026, visait
exactement ce cadre : une taxonomie du droit fournirait le dénominateur qui
manque. La question posée en session était donc : **peut-on s'en passer ?**

La réponse est oui pour la v0 — mais pas gratuitement, et le prix a un nom.

## Le constat qui commande le reste

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
  cas — diagnostic, jamais obligation de couverture. ADR-033 le fait déjà à
  moitié (« la matière est équilibrée au mieux ; ses trous sont permis et
  **chiffrés** ») ; ce qui est neuf est de le nommer comme un **second
  instrument**, non comme un tag ;
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
- **Les mécanismes gagnent une propriété distincte du régime.** La colonne
  `Régime` d'ADR-033 dit d'où vient le **label** ; il manque **le sens de
  dérivation** (fidèle / artefactuel), qui dit ce que le cas vaut en réalisme.
  Deux propriétés aujourd'hui confondues, à séparer dans `GOLDEN-SET.md` §4–§5.
- **Le capteur du §3 est un prérequis du pari, pas un agrément.** À implémenter
  au harnais avant que le panel produise des retours exploitables (rattachement
  ADR-025 / ADR-027).
- **Le chantier taxonomie n'est ni abandonné ni bloquant.** Il devient le second
  instrument, sur son propre calendrier, et cesse d'être sur le chemin critique
  de B-08.
- **Hors périmètre de cet ADR**, et toujours en attente : la rétrogradation de la
  cardinalité en attribut, la renumérotation des mécanismes, le statut du tag
  `domaine juridique`, le resserrement de la cardinalité 0. Ces points amendent
  ADR-033 et seront traités ensemble.

## Références

ADR-007 (métriques) · ADR-012 (constat sur preuves — fondement du §4) ·
ADR-016 (découplage récupération/génération) · ADR-017 (strates) · ADR-025
(environnement panel consenti — porteur du paradigme usage) · ADR-027
(plateforme d'évaluation end-to-end — hôte du capteur) · ADR-028 (frontière
vérification/validation) · **ADR-033 (prolongé : il fixe l'axe, celui-ci fixe le
cadre)** · `GOLDEN-SET.md` §4, §5, §7 · `docs/droit/taxomonie/` (second
instrument) · R-05 (`RISQUES.md`)
