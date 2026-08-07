# Le golden-set Murphy — conception, dimensionnement, cycle de vie

> Document **permanent**. Décrit ce qu'est le golden-set, ce qu'il mesure,
> comment il est dimensionné et comment il vit. Les décisions qu'il applique
> vivent en ADR (004 à 008, 017, 028 à 033) ; les chiffres et leur dérivation
> vivent ici.
>
> **Statut** : v1 en construction (B-08). Les nombres du §7 sont une
> proposition dérivée, pas une décision actée — ils relèvent du régime
> **humain** (ADR-028) et attendent validation du porteur.

---

> ## ⚠️ Sections périmées — ne pas appliquer sans lire ceci
>
> **Au 1er août 2026, plusieurs sections de ce document décrivent une conception
> abandonnée.** Elles n'ont pas encore été réécrites : la refonte est en cours
> sur la carte
> [Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1)
> et atterrira en **ADR-036**, qui remplacera ADR-033 et amendera ADR-034.
>
> **⚠️ Tour du 2 août 2026 — le paradigme change (ADR-035).** L'évaluation
> s'aligne désormais sur le **TREC Legal Track** : la vérité s'achète *à terme*
> **par assesseur**, les labels gratuits n'en sont que le **premier incrément**,
> et toute spécification doit satisfaire le critère « **rien à jeter** » — survivre
> au passage au golden-set v2 (expert, poolé, calibré — alpha ph.2) puis à
> l'ouverture aux runs externes, sans redesign. Ce qui, dans les sections
> ci-dessous **et dans les résolutions déjà closes**, dérive d'une **rareté du
> jugement traitée comme permanente** est rouvert.
>
> | Section | État | Pourquoi |
> |---|---|---|
> | **§4** — les deux axes | ⛔ **faux** | La cardinalité n'est plus un axe. Le tableau des huit mécanismes est périmé sur deux points : la liste tombe à **six** — `robustesse_paraphrase` devient une variante ([#2](https://github.com/left-eyebr0w/murphy/issues/2)) et `correspondance_litterale` **quitte le golden-set** pour les instruments diagnostiques du §1 ([#10](https://github.com/left-eyebr0w/murphy/issues/10)) — et la colonne `Régime` classe `concept_vers_instance` en *détenu*, ce qui est faux — son label asserté est une opinion. **La v1 compte cinq mécanismes** — quatre gratuits + `concept_vers_instance` **jugé**, qui peuple la branche `ouvert` restée vide ; `desambiguisation` sort de la v1. Ne pas confondre **la liste** (six) et **la composition de la v1** (cinq) : la couverture exigée par E-P2-07 porte sur la seconde. [Tickets #9](https://github.com/left-eyebr0w/murphy/issues/9) et [#10](https://github.com/left-eyebr0w/murphy/issues/10). |
> | **§4.1** — les quatorze cellules | ⛔ **supprimé** | La grille n'existe plus. Aucune cellule n'est à peupler. |
> | **§6** — les matières, §6.1 douze strates | ⛔ **supprimé** | Les strates ne survivent pas comme cadre d'échantillonnage ; le vecteur de pondération tombe avec elles. `WIP/B-08-prior-ponderation.md` est sans objet. **Seul §6.4 (date pivot) survit** et est à replacer hors du §6 mourant — [ticket #12](https://github.com/left-eyebr0w/murphy/issues/12). **§6.3 (registre) ne survit plus** : il se dissout dans `variante_de` — voir sa ligne ci-dessous. |
> | **§6.2** — pondération au rapport | ✅ **traité** | **Supprimé, chiffre et principe** (YAGNI) : un seul chiffre publié, non pondéré, aucune estimation production. Seule survit la mise en garde sur les ventilations. [Ticket #4](https://github.com/left-eyebr0w/murphy/issues/4). |
> | **§7** — dimensionnement | ⛔ **remplacé** — contenu arrêté le 1er août 2026, rédaction en attente d'ADR-036 | **Le §7 est faux en entier, y compris ses parties que les révisions précédentes déclaraient survivantes.** `N_q ≈ 155` reposait sur `14 cellules × 10` (facteurs disparus) ; `N_j ≈ 60–70` (§7.4) est **optimiste d'un facteur ≈ 2,5** (Webber/Moffat/Zobel, CIKM 2008 §5.1 — dossier : [`recherche/realisme-collections.md`](recherche/realisme-collections.md)) ; la **carotte** de §7.4 n'a plus de sous-ensemble à tirer ; le tableau de croissance §7.5 décrit une croissance qui n'aura pas lieu. **`N_j` sort du vocabulaire** — quatre grandeurs le remplacent : `N_cas` (cas **indépendants**, unité du plancher et du taux ventilé), `N_q` (interrogé à chaque run — cas **+ variantes**), `N_pending`, et un **budget de jugement**. La dérivation devient **ascendante, unité = le mécanisme** : `N_cas` est une somme de planchers, jamais un total réparti. **Plancher = 30 cas par mécanisme**, par la règle de trois — zéro échec sur 30 borne l'échec à < 10 %, seuil de lisibilité de la sentinelle d'E-P2-07 ; uniforme, **noyau jugé compris**. **v1 = 150 cas, dont 30 jugés ; `N_q ≥ 180`.** Budget d'annotation en **jugements totaux alloués par pondération RBP** (CLEF eHealth 2016), **jamais en profondeur fixe**. **§7.2 garde sa prémisse et perd sa conclusion** : le rejeu qu'il fuyait est déjà au calendrier (vague 2, ADR-003, après alpha ph.1), donc c'est un argument de **calendrier des lots** → **v0 n'ajoute ni ne retire jamais un cas** (gel **bilatéral** : retirer casse la comparabilité sans qu'ADR-032 le signale). **Attention au motif** : ce n'est pas un problème de volume. Les labels gratuits rendent le volume gratuit ; ce qui manque est de la **variance discriminante**. [Tickets #9](https://github.com/left-eyebr0w/murphy/issues/9) et [#11](https://github.com/left-eyebr0w/murphy/issues/11). |
> | **§8.1** — paires isosémantiques | ⚠️ **requalifié + dimensionné** | Elles ne sont plus un sous-ensemble d'un mécanisme : la paraphrase devient une **variante** applicable à n'importe quel cas, donc mesurable partout sans coût de label. Masse fixée : **30 cas variés**, répartis sur les mécanismes, ≥ 1 variante chacun, **qrels partagées** (le label ne bouge pas sous paraphrase) — zéro divergence borne alors la divergence à < 10 %. **Les variantes comptent dans `N_q`, jamais dans le plancher** : trois paraphrases d'un même cas ne sont pas trois observations indépendantes, et les compter rendrait fausse la borne de la règle de trois. Précédent : CLEF eHealth 2016 compte 300 requêtes (50 scénarios × 6 variantes) mais alloue les jugements **par scénario**. [Ticket #11](https://github.com/left-eyebr0w/murphy/issues/11). |
> | **§8.3** — strate-frontière | ⚠️ **suspendu** | Défini par rapport aux strates, qui tombent. |
> | **§4.4** — les types de difficulté | ✅ **tient** | Son raisonnement est indépendant de la grille. |
> | **§2** — la doctrine | ✅ **réécrit** | Intégralement, le 1ᵉʳ août 2026 : **aucun cadre d'échantillonnage** (assumé), **le corpus est entrée matérielle** et l'interdit anti-circularité porte désormais sur la *liste des mécanismes*, **`pending` délibéré sur la source `identite`** seule. Le vocabulaire D₁/D₂/D₃ a disparu du document. [Ticket #4](https://github.com/left-eyebr0w/murphy/issues/4). |
> | **§10** — ce qu'on exige de l'ingestion | ✅ **re-dérivé** | Depuis la source de gratuité au lieu des strates. Devient un **constat émergent**, donc un critère **non exhaustif** pour ADR-003. [Ticket #4](https://github.com/left-eyebr0w/murphy/issues/4). |
> | **§5.1** — hiérarchie de provenance | ⚠️ **contesté** | Le rang 1 s'y déclare *permanent, survit à la ré-ingestion* — faux pour la source `frontiere_corpus`, dont le label **se retourne** quand le corpus s'étend. [Ticket #15](https://github.com/left-eyebr0w/murphy/issues/15). |
> | **§1** — instruments séparés | ⚠️ **précisé + contesté** | Précisé : **un instrument est séparé quand il a ses propres cas, pas quand il a sa propre lecture** — graph-hop et co-citation ont un corpus de cas propre ; une lecture nouvelle des mêmes runs reste dans le jeu. Contesté : « mesurer le **delta** de chaque brique » suggère *trancher*, alors que **B-10 ordonne** — amendement acquis, à porter à la réécriture. **Un troisième instrument rejoint la famille** : `correspondance_litterale`, sorti du golden-set comme **test de fumée** — requête artefactuelle, précondition d'interprétabilité du reste, **sans exigence propre** dans `EXIGENCES_v0.md` ([#10](https://github.com/left-eyebr0w/murphy/issues/10)). [Ticket #9](https://github.com/left-eyebr0w/murphy/issues/9). |
> | **§3** — les deux couches | ⚠️ **à instruire** | La séparation questions / jugements **tient** et absorbe le noyau jugé sans rouvrir E-P2-06. Mais la **couche jugements devient hétérogène en provenance** (qrels dérivées pour quatre mécanismes, jugées pour le cinquième) : chaque qrel doit porter la sienne — [ticket #12](https://github.com/left-eyebr0w/murphy/issues/12). Vérifier au passage qu'ADR-032, écrit avant cette hétérogénéité, couvre encore les classes de changement. |
> | **§4.3** — les opérations d'ADR-030 | ⚠️ **rétrogradation confirmée, obligation supprimée** | La machinerie tient (portage par l'arête, régime jugée/dérivée, dérivation depuis `G₀`), mais l'obligation de **non-vide sur les trois opérations jugées** disparaît d'E-P2-07 : c'était une **couverture** imposée à une facette, contre la doctrine du §5. Elle est de surcroît **insatisfiable en v1** — les quatre mécanismes gratuits ne produisent que des opérations *dérivées* (`known_item`, `graph_hop`/`fondement_textuel`), `absence_hors_corpus` ne produit **aucune arête**, et **`jurisprudence_applicable` n'a aucun producteur**. La surface d'annotation tombe de trois à **deux, portées par un seul mécanisme**. [Ticket #10](https://github.com/left-eyebr0w/murphy/issues/10). |
> | **§5.2** — les facettes | ⚠️ **triées + erreur de rangement** | Tri par le test d'ADR-030 (« dois-je rouvrir les documents ? ») : **date pivot** et **doc(s) germe** exigés à 100 % — le second devient le **support matériel du typage**, plus une commodité ; **`intention` n'est plus exigée du tout** (on n'exige pas la conformité à un vocabulaire non acté, §11.2) ; **`matière` et `polysemique` disparaissent**. Erreur relevée : les opérations y sont rangées en bloc parmi les facettes *« dérivées — lues, jamais saisies »*, alors qu'ADR-030 en déclare **trois jugées**. [Ticket #10](https://github.com/left-eyebr0w/murphy/issues/10). |
> | **§5.3** — la difficulté en sortie | ⚠️ **boucle à fermer** | *« Un cas que la baseline rate est de facto difficile »* est juste comme **mesure**, mais laisse la boucle ouverte : écrire les cas suivants en relisant le run rend le jeu circulaire. Second cran à écrire — **la difficulté d'un cas se dérive de propriétés de la tâche, jamais d'un run observé** (E-P2-07 + guide d'annotation). [Ticket #10](https://github.com/left-eyebr0w/murphy/issues/10). |
> | **§6.3** — registre | ⛔ **dissous** | **Le quota et le tag disparaissent tous deux.** Un décalage praticien ↔ citoyen est *même besoin, même label, formulation différente* — c'est la définition de la **variante** ([#2](https://github.com/left-eyebr0w/murphy/issues/2)), et c'en est le membre le plus fort : §6.3 y localise lui-même *« le premier facteur d'échec d'une recherche vectorielle en droit »*, et #10 §5 range la « paraphrase agressive » parmi les propriétés de la tâche dont on a le droit de dériver la difficulté. Le mot `registre` **sort du vocabulaire**. Ce qui survit est une **contrainte de rédaction** au guide d'annotation : *les cas variés sont des décalages de registre, pas des reformulations lexicales*. [Ticket #11](https://github.com/left-eyebr0w/murphy/issues/11). |
> | **§4.2** — écrire des cas qu'on s'attend à rater | ✅ **promu** | De conseil de rédaction à **critère de sortie** : le pouvoir discriminant devient l'une des deux bases d'E-P2-07, publié comme **grandeur sans seuil** (taux de réussite de la baseline ventilé par mécanisme, ADR-034 §4). [Ticket #10](https://github.com/left-eyebr0w/murphy/issues/10). |
> | **§5, §9, §11** | ⚠️ **à instruire** | Non démolis, mais leurs dépendances bougent. |
>
> **Ce qui est acquis et n'est écrit nulle part ici encore** : l'axe unique des
> mécanismes ; le remplacement du test de sens de dérivation d'ADR-034 par
> **deux propriétés indépendantes** — la *source de gratuité du label*
> (`identite` / `graphe_g0` / `frontiere_corpus` / `aucun`) et le *réalisme de la
> requête* ; et la v1 gratuite à quatre mécanismes (`resolution_reference`,
> `known_item_identifiant`, `multi_hop`, `absence_hors_corpus`), avec
> `concept_vers_instance` et `desambiguisation` requalifiés « à jugement ».
> Détail :
> [résolution du ticket racine](https://github.com/left-eyebr0w/murphy/issues/2#issuecomment-5152165131).
>
> **De même, acquis et écrit nulle part ici** ([ticket #9](https://github.com/left-eyebr0w/murphy/issues/9)) :
>
> - **B-10 *ordonne*, il ne tranche pas.** La v0 range des configurations ; elle
>   ne conclut pas qu'une brique est inutile. Ce pouvoir s'achète à l'alpha ph.2.
> - **Deux lectures des mêmes runs et des mêmes qrels** : binaire
>   (`success@1`, `Recall@R`, précision sur `R=0`) pour le rapport et la
>   non-régression ; **continue et sensible au rang** pour la comparaison de
>   configurations. `success@1` détruit de la variance ; la comparaison ne le lit
>   plus. *Quelle* métrique continue reste ouvert
>   ([ticket #14](https://github.com/left-eyebr0w/murphy/issues/14)).
> - **`concept_vers_instance` est financé et rédigé *besoin d'abord***, comme
>   **noyau de contrôle de transfert** — il audite l'ordre obtenu sur les
>   mécanismes gratuits au lieu de l'alimenter. R-05 revient sur ce mécanisme et
>   lui seul.
> - **L'accord entre les deux ordres est une grandeur permanente**, publiée à
>   chaque run, **sans seuil**, direction pré-enregistrée : un accord qui décroît
>   à mesure qu'entrent des configurations `W` signale que l'ordre gratuit ne
>   transfère pas. ADR-034 §4 appliqué à un second dispositif.
> - **La puissance du contrôle de transfert vient du nombre `k` de
>   configurations classées**, plafonné par le coût de ré-ingestion (`W`), pas
>   par le budget d'annotation.

---

## 1. Ce que c'est

Une **collection de test de Recherche d'Information** au sens classique : le
triplet `(corpus, questions, jugements de pertinence)`. En découplant
récupération et génération (ADR-016), Murphy n'évalue pas « du RAG » mais un
problème IR ordinaire — toute la méthodologie TREC s'applique, outillage
compris.

Le golden-set est **unique** (ADR-017). On ne multiplie pas les golden-sets par
brique technologique : on mesure le **delta** de chaque brique sur le *même*
jeu. Les sets diagnostiques (graph-hop, co-citation) sont des instruments
séparés, à côté, jamais des variantes du jeu principal.

---

## 2. La doctrine : le jeu n'échantillonne pas le droit, il énumère des fonctions

> Section **réécrite intégralement** le 1ᵉʳ août 2026
> ([ticket #4](https://github.com/left-eyebr0w/murphy/issues/4)). La version
> précédente construisait le jeu sur une distribution du contentieux réel ; ce
> cadre est tombé avec les douze strates. Le vocabulaire D₁ / D₂ / D₃ ne figure
> plus dans ce document.

### 2.1 Aucun cadre d'échantillonnage, et c'est par construction

ADR-034 §1 range le paradigme fonctionnel — celui de ce jeu — dans la colonne
*cadre d'échantillonnage* : **aucun**. Ce n'est pas un manque à combler, c'est
la définition du paradigme.

**Le jeu n'échantillonne pas le droit ; il énumère des fonctions de
récupération.** L'ensemble des mécanismes est petit, borné et testable au sens
logiciel ; l'ensemble des contenus juridiques ne l'est pas. Organiser par
mécanisme, c'est renoncer explicitement à représenter quoi que ce soit du
*contenu* du droit.

Deux cadres de remplacement ont été examinés et écartés :

| Écarté | Pourquoi |
|---|---|
| **Un cadre promis à la taxonomie** (`docs/droit/taxomonie/`, ADR-034 §5) | Elle est hors chemin critique et sur son propre calendrier. Écrire une dépendance qu'on ne peut pas honorer en v1 revient à dater un chèque. |
| **Le corpus lui-même comme cadre par défaut** | C'est exactement la circularité qu'ADR-029 écarte pour la strate 2 et qu'ADR-031 écarte pour le graphe. |

L'argument décisif n'est pas qu'un meilleur cadre resterait à trouver, mais que
**tout cadre de contenu est devenu sans objet** : un cas
`known_item_identifiant` n'a pas de matière au sens utile — la région du droit
de sa cible est un accident du document tiré, pas une propriété du test.

> ⚠️ **Conséquence assumée, et elle coûte.** Sans cadre d'échantillonnage, **un
> trou n'est plus chiffrable** : plus rien ne dit par rapport à quoi une absence
> est grave. La couverture régulière du contenu relève du **second instrument**
> (la taxonomie), la représentativité du besoin relève du **paradigme usage**
> (le panel, ADR-025) — ni l'une ni l'autre n'est mesurable ici. ADR-034 §5 :
> triangulation, jamais fusion.

### 2.2 Le corpus est une entrée matérielle assumée

> ⚠️ **Support corrigé le 5 août 2026**
> ([#15](https://github.com/left-eyebr0w/murphy/issues/15)). **La thèse tient, son
> exemple porteur tombe.** La table ci-dessous faisait reposer l'aveu sur
> `absence_hors_corpus` — or ce mécanisme ne tire plus son label de la frontière
> du **corpus** (un *état*, qui bouge à chaque vague) mais de celle du **périmètre
> DILA** (une *définition*, externe). **`frontiere_corpus` est sorti du
> vocabulaire — neuvième mot.** Ce qui reste vrai : le corpus est bien une entrée
> matérielle, mais **par `graphe_g0` seul**. Rédaction définitive en ADR-036.

La v1 gratuite tient en quatre mécanismes, et **tous ont besoin du corpus** —
l'un d'eux y prend directement son label :

| Mécanisme | Source de gratuité | Rapport au corpus |
|---|---|---|
| `resolution_reference` | `identite` | le label (ELI) se calcule **hors** corpus ; le corpus sert à *scorer* |
| `known_item_identifiant` | `identite` | idem (ECLI) |
| `multi_hop` | `graphe_g0` | `G₀` est **construit depuis les documents ingérés** — **seul appui survivant de cette section** |
| ~~`absence_hors_corpus`~~ | ~~`frontiere_corpus`~~ | ⛔ **faux depuis le 5 août** — le label se lit sur le **périmètre DILA**, pas sur le corpus ingéré ; la cible d'un tel cas est hors périmètre **définitivement**, et une cible seulement *pas encore ingérée* relève de `pending` sur `identite` (§2.3, §10) |

Un jeu dont un mécanisme sur quatre est étiqueté par l'empreinte documentaire
ne peut pas prétendre écarter le corpus de sa conception. On l'assume donc :
**le corpus fournit le matériau.**

> **Le compte est désormais d'un mécanisme sur quatre, non plus deux** — et
> l'aveu ne perd rien : `G₀` étant construit depuis les documents ingérés, il
> suffit à lui seul à interdire de prétendre écarter le corpus. La différence
> est que cet appui-là est **réparable** (les qrels de graphe se re-dérivent,
> §2.3), là où celui qu'on retire ne l'était pas.

Mais la raison de fond de l'ancien interdit — *dimensionner depuis le corpus
laisserait l'ingestion définir ce qu'on mesure* — reste valide. Elle change
simplement d'objet, du contenu vers la fonction :

> **La liste des mécanismes est fixée a priori, jamais par ce qui se trouve
> ingéré.**

L'ingestion fournit les cibles ; elle ne décide pas quelles **fonctions** sont
testées. C'est le seul niveau où la non-circularité ait encore un objet — sous
§2.1 il n'y a plus de contenu à biaiser. Le risque concret que cet interdit
couvre : déduire de « KALI n'est pas ingéré » qu'on renonce à `multi_hop` sur le
droit du travail. L'ingestion aurait repris la main sur la mesure.

### 2.3 Le jeu n'est pas écrit avant l'ingestion — sauf sur la source `identite`

L'ancienne rédaction tirait deux bénéfices de la doctrine : le jeu écrit avant
l'ingestion, et la **requête-décalque** (P-01) rendue « matériellement
impossible ». Les deux tombent.

- Le décalque n'est pas supprimé, il est **déplacé vers la sélection** du
  document germe (ADR-034 §*Constat*). Il n'existe pas d'authoring qui l'évite ;
  il se traite au guide d'annotation, pas par une propriété structurelle.
- Écrire avant l'ingestion est **structurellement impossible** pour
  `graphe_g0` et ~~`frontiere_corpus`~~, dont le label vit *dans* le corpus.

> ⚠️ **Le partage devient ternaire, le 5 août 2026**
> ([#15](https://github.com/left-eyebr0w/murphy/issues/15)). Il n'y a plus deux
> régimes mais **trois**, et le titre de cette section (« sauf sur la source
> `identite` ») est trop étroit — deux sources sur trois échappent désormais au
> corpus. Rédaction définitive en ADR-036.
>
> | Source | Où vit le label | Écrire avant l'ingestion ? | Ce qu'une extension lui fait |
> |---|---|---|---|
> | `identite` | **hors** corpus (ELI, ECLI) | oui, délibérément (`pending`) | **maturation** — le label ne change pas, il acquiert une cible |
> | `graphe_g0` | **dans** le corpus (`G₀` en est dérivé) | non | **dérive** — l'ensemble-réponse *croît* ; réparable, voir ci-dessous |
> | **frontière de périmètre** | **hors** corpus (le catalogue DILA, autorité externe) | oui | **rien** — le périmètre ne bouge pas quand nous ingérons |
>
> **`graphe_g0` ne se périme pas, il se re-dérive.** Ses qrels sont un ensemble
> **calculable** depuis `G₀` (les cibles à distance 1 du germe) : elles sont
> **re-dérivées à chaque version de collection déclarée, jamais recopiées**. `G₀`
> bouge donc → le hash `qrels` change → la comparabilité se restaure **par
> re-notation, gratuitement** (ADR-032 §2 ; ADR-031 §1 garde `G₀` au rôle de
> *dérivation*, donc le run archivé avait bien accès aux documents). Deux
> conditions : **le germe reste asserté, jamais dérivé** — sinon le hash `cas`
> bougerait quand seul `G₀` a bougé — et **la gratuité meurt le jour où le levier
> `G₁` d'ADR-031 alimente le retriever**.
>
> **Sans cette obligation, le trou est silencieux** : le lot d'extraction de
> références n'exige **aucune ré-ingestion**, donc il ajoute des arêtes sans
> ajouter de documents — ni le hash `corpus` ni le hash `cas` ne bougent, et `G₀`
> se déplace sous des qrels que rien ne signale.

Ce qui survit, et ce n'est pas rien : **le label de la source `identite` vit
hors du corpus.** L'ELI se calcule depuis « article 1240 du Code civil »,
l'ECLI depuis un numéro de pourvoi (ADR-018) — sans que le document soit
ingéré. Le corpus n'est nécessaire que pour *scorer*, pas pour *étiqueter*.

**Donc une question `identite` peut être écrite sur une cible absente, et le
jeu en écrit délibérément.** Elle reste `pending` : écrite, gelée, interrogée à
chaque run, non jugée — et jugeable sans aucune re-récupération le jour où sa
base arrive (§7.2, §10).

C'est **délibéré et non simplement toléré**, parce qu'un auteur qui travaille
depuis le corpus n'en produira jamais par accident : il ouvrira le document.
Tolérer sans rechercher équivaudrait à abandonner, et le jeu redeviendrait un
miroir du corpus — au niveau des cibles, ce que §2.2 vient d'interdire au
niveau des mécanismes.

L'argument de coût est solide **et il est local à cette source** : §7.2 pose
qu'écrire large coûte moins que d'écrire deux fois, tandis qu'ADR-034
§*Conséquences* avertit que sur-investir l'authoring pré-panel achète du volume
artefactuel. Sur `identite`, la tension n'existe pas — c'est l'exception nommée
par ADR-034 §*Constat*, où le sens de dérivation n'est pas un artefact et où le
label est gratuit **et** réaliste. Une question `pending` y est le cas le moins
cher du jeu : label gratuit, hors corpus, zéro jugement, zéro re-récupération.

Le **volume** de `pending` n'est pas fixé ici (voir §7 et
[ticket #11](https://github.com/left-eyebr0w/murphy/issues/11)).

> ⚠️ Le corpus intervient aussi en fin de chaîne, à un titre distinct :
> **ordonnancer l'effort d'annotation** (quelles questions sont jugeables
> aujourd'hui). Même déplacement de rôle que le pooling a subi avec ADR-032 —
> de levier de complétude à ordonnanceur.

---

## 3. ⛔ Trois couches, trois régimes de gel — **périmé sur le mot `gel`**

> **Périmé le 2 août 2026** ([#18](https://github.com/left-eyebr0w/murphy/issues/18) §0).
> **`gel` est sorti du vocabulaire** — sixième mot retiré par la carte
> [#1](https://github.com/left-eyebr0w/murphy/issues/1). Motif : *il ne garantissait la
> validité de rien* — un grade faux et gelé reste faux — et il exigeait de savoir d'avance
> ce qui mérite d'être scellé.
>
> **Remplacement : on ne gèle rien, on identifie tout.** La colonne « Gel » ci-dessous se
> lit désormais comme une colonne **d'identification**, et l'empilement en trois couches
> **survit** — c'est même lui qui donne les **trois hashes** portés par chaque run :
>
> | Couche | Hash | Ce que coûte son déplacement |
> |---|---|---|
> | **Corpus** *(couche neuve — elle manquait ici comme dans ADR-032 §4)* | sur les **identités canoniques de document** (ADR-004 / ADR-018), donc **stable sous `W`** | ré-ingestion **et** re-récupération |
> | **Questions** | hash `cas` | re-récupération sur les cas neufs |
> | **Jugements** | hash `qrels` | **re-notation seule, gratuite** (ADR-032 §2) |
>
> Deux runs sont comparables **ssi** leurs trois hashes sont égaux. Une **version de
> collection** est un triplet qu'on **nomme** et publie — un nom, jamais un hash, et pas de
> quatrième hash composé. Le contenu de la ligne « Questions » ci-dessous est par ailleurs
> **doublement périmé** : `cardinalité`, `intention`, `matière` et `registre` ont tous
> disparu (#3, #10, #11), et le champ **`narrative`** s'y ajoute (#18 §5).
>
> ⛔ **Second point périmé, constaté le 7 août 2026**
> ([#12](https://github.com/left-eyebr0w/murphy/issues/12)) : **la dernière phrase de la
> rédaction antérieure est fausse.** Une classe existe — `Topic(query_id, text)`, dans
> `eval/src/murphy_eval/core/models/runtime.py`, délibérément minimale. #12 en tire un
> cadrage : l'objet que ce document spécifie est l'enregistrement d'**authoring**, dont
> `Topic` est la **projection runtime, inchangée** — même patron qu'ADR-008, qui projette son
> JSONL canonique vers du TREC plat. La séparation **se paie zéro**, et le hash `cas` porte
> sur l'authoring, jamais sur la projection.
>
> ⚠️ **Et l'attribution des champs aux hashes ne suit plus les couches de la table
> ci-dessous** : #12 §4 amende #18 §0 en posant que **le hash suit le coût, pas le fichier**.
> `narrative` vit dans la couche questions mais appartient au hash **`qrels`**, aucun run ne
> la consommant.
>
> Réécriture d'ensemble : **ADR-036**, à la clôture de la carte.

### Rédaction antérieure

Le jeu n'est pas un fichier mais un empilement. La règle de partage est celle
d'ADR-030 : *enregistrer ce qui a coûté une lecture, dériver tout le reste*.
Test opérationnel — **« si je change d'avis là-dessus, dois-je rouvrir les
documents ? »**

| Couche | Contenu | Coût | Gel |
|---|---|---|---|
| **Questions** | Texte, `mécanisme`, `cardinalité`, `intention`, `matière`, `registre`, date pivot | Rédaction | Gelée, hashée |
| **Jugements** | `q1/q2/q3` par arête, `grade` dérivé, `source`, `origin`, `annotator` | **Lecture — poste dominant** | Gelée, hashée (ADR-008) |
| **Dérivations** | 5 opérations dérivées, taxonomie, définition des strates | Calcul | **Versionnée à part** |

*Figé* et *révisable* ne s'opposent pas : ils ne portent pas sur le même objet
(ADR-030, ADR-032). Les dérivations se recalculent à la demande depuis le
graphe témoin `G₀` (ADR-031) — jamais ingérées, jamais annotées.

La couche **questions** est propre à ce document : ADR-030 note qu'aucune
classe `Query` n'existe dans `eval/`. C'est ici qu'elle se peuple.
⛔ **Faux depuis le 7 août 2026** — voir l'encadré en tête de section :
`Topic` existe, et l'objet spécifié ici est l'enregistrement d'authoring
dont `Topic` est la projection.

---

## 4. ⛔ Les deux axes — **remplacé par ADR-035**

> **Statut.** ADR-033 est obsolète ; la section est **remplacée, pas amendée**
> ([ticket #3](https://github.com/left-eyebr0w/murphy/issues/3)) : elle est
> écrite autour de deux axes dont le second a été dissous. **§4.1 (les quatorze
> cellules) disparaît avec elle.** Ce qui subsiste, et qu'on lit ci-dessous : le
> renversement de l'axe primaire (mécanisme plutôt que contenu), qui tient.
>
> **Trois corrections à porter avant relecture :**
> 1. **L'axe « cardinalité » n'existe plus.** Ce qu'il empilait se rend à deux
>    concepts déjà présents ailleurs : un **compte**, `R = len(qrels)`, jamais
>    asserté ; et une **clôture**, qui *est* la source de gratuité du label
>    ([#2](https://github.com/left-eyebr0w/murphy/issues/2)).
> 2. **La liste des mécanismes n'est plus à huit** : sept après #2
>    (`robustesse_paraphrase` devient une *variante* applicable à tout cas),
>    puis six après [#10](https://github.com/left-eyebr0w/murphy/issues/10)
>    (`correspondance_litterale` passe aux instruments diagnostiques). La
>    **composition de la v1** en compte cinq. Renumérotation et cimetière de
>    vocabulaire à écrire en ADR-036.
> 3. **La table des métriques ci-dessous est périmée** — voir la table de
>    remplacement, plus bas dans cette même section.

ADR-033 fixait la structure, et elle n'est pas celle qu'on attend d'un jeu de
test classique : **on n'évalue pas un contenu, on évalue une fonction de
récupération.**

| Axe | Porté par | Cardinalité | Ce qu'il fait |
|---|---|---|---|
| **Mécanisme** | le cas de test | une seule valeur | Localise la panne — *quelle fonction décroche ?* |
| **Cardinalité** | le cas de test | une seule valeur | Détermine **quelle métrique est valide** dans la cellule |

Le renversement par rapport à ADR-030 tient en une phrase : organiser le jeu
par *ce que l'utilisateur veut* adosse l'axe au **contenu** du droit — espace
non borné, sans complétion naturelle. Organiser par *mécanisme exercé* donne un
ensemble **énumérable et petit** de fonctions testables au sens logiciel. Le
contenu descend au rang de facette qu'on tague et qu'on slice (§5), jamais
qu'on énumère.

**Huit mécanismes, aucun jugé :**

| # | Mécanisme | Nature du test | Régime |
|---|---|---|---|
| 1 | `correspondance_litterale` | Requête = texte source verbatim | détenu |
| 2 | `resolution_reference` | « article 1240 du Code civil » → l'article (ELI) | dérivé (requête) |
| 3 | `known_item_identifiant` | ECLI, n° de pourvoi → la décision | dérivé (requête) |
| 4 | `robustesse_paraphrase` | Reformulation → même cible | détenu (paire) |
| 5 | `concept_vers_instance` | Notion juridique → l'article qui la fonde | détenu |
| 6 | `multi_hop` | Cible atteignable seulement via une citation | dérivé (`G₀`) |
| 7 | `desambiguisation` | Terme à référents concurrents attestés | détenu + constatable |
| 8 | `absence_hors_corpus` | Besoin hors corpus → *fail-fast* | détenu |

**Les known-item auto-étiquetés sont la famille la moins chère du jeu.** La
requête est *construite à partir* du document cible : le label n'est pas une
intuition, c'est un **fait d'authoring**. Citer verbatim l'article 1240 ⇒ le
système *doit* le rendre au rang 1. Aucun jugement de pertinence n'intervient,
donc **R-05 est esquivé par construction**, pas atténué. C'est ce qui justifie
de commencer par là plutôt que par le topique gradué.

⛔ ~~**Quatre cardinalités, chacune déclarant sa métrique.**~~ *(Table retirée :
la cardinalité est dissoute, et `nDCG@R` avec elle.)*

**Le routage de métrique, sous sa forme dérivée** — trois branches, toutes
**lues**, aucune assertée ([#3](https://github.com/left-eyebr0w/murphy/issues/3),
[#14](https://github.com/left-eyebr0w/murphy/issues/14)) :

| Condition | Cas v1 | Rapport / couverture | **Comparaison de configurations** |
|---|---|---|---|
| `R = 0` | 30 (`absence_hors_corpus`) | **précision seule**, statut ADR-029 : jamais de rappel, jamais de grade | **taux de remontée au-delà du seuil** (§8.1) — `RBP` y est identiquement nul, donc aucune métrique de **classement** ; cette lecture ne se compare pas aux deux autres branches |
| `R ≥ 1` **et ensemble clos** | 90 | **`Recall@R`** tout-ou-rien (`R = 1` se *lit* success@1 — Doc-MRR n'est pas une branche) | **RBP(`p`) + résidu** |
| **ensemble ouvert** | 30 (noyau jugé) | — | **RBP(`p`) + résidu** |

La colonne de comparaison est **commune aux deux branches où une comparaison a
un sens**, soit **120 cas sur 150** : RBP ne demande pas `R`, il couvre donc
aussi les cas gratuits — où il n'y a d'ailleurs **aucun trou**,
l'ensemble-réponse étant exact, et où le résidu est donc **nul** (pas de trous,
et une queue de `0,75¹⁰⁰ ≈ 3·10⁻¹³` sous le `d_min` d'ADR-007). **Toute
l'incertitude du dispositif vient des 30 cas jugés.**

**Le refus des coupes constantes tient, et il est mieux servi** : RBP n'est pas
une coupe mais une pondération géométrique, il n'a pas à choisir où couper. `R`
n'est écrit nulle part en propre — il **est** la longueur de l'ensemble-réponse.
Voir [ADR-007](ADR/ADR-007-metrique-rbp-residu.md) pour la règle de `p`, la
projection linéaire des grades et la **porte du résidu**.

⛔ *La garantie revendiquée ici — « faire de la cardinalité un axe explicite
interdit mécaniquement l'erreur nDCG@R partout » — est sans objet : il n'y a
plus de `nDCG@R` à interdire nulle part.*

### 4.1 Les quatorze cellules valides

Les deux axes se **croisent et se couvrent** — c'est le coût engageant, et la
raison pour laquelle il n'y en a que deux. La grille brute fait 32 cellules,
dont 18 sont vides par construction : un known-item par identifiant n'est pas
de cardinalité ouverte.

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

**Le vide impossible est de l'information ; le vide non observé est un défaut.**
Cette table les sépare : une cellule non cochée n'est jamais à peupler, une
cellule cochée et vide est un manque de couverture, chiffré au rapport.

> **Réserve d'orthogonalité, assumée.** La cardinalité corrèle partiellement
> avec le mécanisme — un known-item *est* de cardinalité 1. La table rend cette
> corrélation explicite au lieu de la laisser produire des doublons à
> l'authoring.

### 4.2 Écrire des cas qu'on s'attend à rater

Exigence de conception, pas conseil de rédaction. **Une suite réussie à 100 %
par la baseline a un pouvoir discriminant nul** et ne mesure aucune marge de
progression — la baseline de B-11 ne prouverait alors rien.

On écrit donc délibérément des cas de stress — paraphrase agressive, graph-hop
profond, homonymes inter-domaines — *à côté* des cas triviaux, dans les mêmes
cellules.

### 4.3 Où sont passées les opérations d'ADR-030

Elles ne portent pas sur le même objet que les mécanismes : l'**opération**
type une arête `(requête, source, cible)` — *pourquoi ce document-ci est
pertinent* — quand le **mécanisme** qualifie un cas — *quelle fonction est
exercée*. ADR-033 leur retire le statut d'axe ; il ne les supprime pas.

Elles deviennent des **facettes dérivées** (§5), et tout ce qui en dépendait
reste en vigueur : le régime jugée / dérivée, le champ `source` de `Judgment`,
la dérivation depuis `G₀`, la réserve sur la ventilation.

**La surface d'annotation reste `3`** — `texte_applicable`,
`jurisprudence_applicable`, `definition` — et elle ne se multiplie plus par la
matière, qui n'est plus un axe.

### 4.4 Où sont passés les « types de difficulté »

Une conception antérieure (`docs/droit/stats/`, 23 juillet 2026) proposait six
« types de difficulté de retrieval » T1–T6 comme second axe. Ils ne sont pas
perdus, mais ils ne sont pas un axe : ils mêlent **quatre natures d'objet
différentes**, ce qui explique l'inconfort du croisement.

| Type d'origine | Ce qu'il est réellement | Où il atterrit |
|---|---|---|
| T1 — Identifiant | Un **mécanisme** | `known_item_identifiant` (§4, #3) |
| T2 — Langage courant | Un **registre** | Champ `registre` sur la question (§6.3) |
| T3 — Polysémie | Un **mécanisme** | `desambiguisation` (§4, #7), matériau en §8.2 |
| T4 — Temporel | Une opération **dérivée** + une date | `succession_temporelle` + date pivot (§6.4) |
| T5 — Multi-base | Une **cardinalité** | Niveau « n — ensemble borné » (§4) |
| T6 — Négatif | Un **mécanisme** + une cardinalité | `absence_hors_corpus` × cardinalité 0 (§4) |

Sous ADR-033, **trois des six atterrissent sur l'axe primaire**. L'intuition de
départ était donc bonne pour moitié : elle avait identifié de vrais mécanismes,
mais les mêlait à un registre, à une date et à une cardinalité — quatre natures
d'objet dans un seul axe, ce qui explique l'inconfort du croisement.

L'axe *difficulté* comme tel est supprimé. Étiqueter une requête « difficile »
enregistre une impression, et l'étiquette **absorbe la question qu'elle prétend
documenter** — quand le score s'effondre sur les requêtes difficiles,
« c'était difficile » n'explique rien.

> Ce point est le plus solide du dossier : ADR-030 et une synthèse de session
> menée sans accès au corpus ADR l'ont établi **indépendamment, sans se
> connaître, avec le même argument** (ADR-033). Il a cessé d'être une
> préférence de conception.

La difficulté n'est pas perdue pour autant — elle est **reframée en sortie**
(§5.3).

---

## 5. Les facettes

**Un axe se croise et se couvre ; une facette se tague et se slice.** Le
premier coûte de l'authoring combinatoire, la seconde est quasi gratuite. C'est
toute la différence, et c'est pourquoi il n'y a que deux axes (§4) et autant de
facettes qu'on veut.

Une facette est **promouvable en axe — mais sur preuve chiffrée
d'interaction**, jamais a priori. On tague tout dès le départ ; on ne promeut
que quand les nombres montrent que le mécanisme se comporte différemment selon
les valeurs. C'est ADR-012 appliqué à l'évaluation : un changement d'état est un
constat sur preuves, pas une pré-décision.

### 5.1 D'où vient la valeur d'un tag

La bonne question n'est pas « ce tag est-il pertinent ? » — tout l'est
vaguement — mais **d'où vient sa valeur ?** La source détermine le coût *et* le
risque R-05.

| Rang | Source | Coût | Statut |
|---|---|---|---|
| 1 | **Dérivé de l'identité canonique** — lu depuis l'ECLI, l'ELI, la structure, `G₀` | gratuit, objectif, **permanent** (survit à la ré-ingestion) | le tag idéal |
| 2 | **Détenu par construction** — connu parce qu'on a fabriqué le cas | gratuit, objectif | admis |
| 3 | **Jugé** — arbitrage de pertinence ou de difficulté | cher, R-05 | **banni en v0** |

**Règle d'admission.** Un tag mérite sa place **ssi** (1) il est dérivé ou
détenu, jamais jugé ; (2) on peut **nommer la question** qu'on répondrait en
*slice*-ant dessus — pas de question, pas de tag ; (3) son vocabulaire est clos
et le **null est permis**.

> ✅ **Contestation levée le 5 août 2026**
> ([#15](https://github.com/left-eyebr0w/murphy/issues/15)) — **la règle « rang 1
> = permanent » était juste ; c'est `frontiere_corpus` qui n'était pas rang 1.**
> Cette section n'avait donc rien à corriger, seulement à être déchargée.
>
> La contestation du 1ᵉʳ août observait que les trois sources de gratuité n'ont
> pas la même permanence, `frontiere_corpus` bougeant à chaque vague d'ingestion.
> Exact — mais le défaut était dans la source, pas dans le rang : **un label de
> rang 1 se dérive d'une *définition*, jamais d'un *état***. Une frontière de
> corpus ingéré est un état ; la **frontière de périmètre DILA** est une
> définition, externe et que nos vagues d'ingestion ne déplacent pas
> (`VISION.md` §2, ADR-014). Le mécanisme est re-fondé sur la seconde, et **le
> jeu cesse de travailler à invalider ses propres labels**.
>
> `graphe_g0` reste rang 1 lui aussi, à une condition **mécanique** posée par
> §2.3 : ses qrels sont **re-dérivées**, jamais recopiées. Un label dérivé est
> permanent au sens qui compte ici — non pas *immobile*, mais **recalculable sans
> jugement**.
>
> **`frontiere_corpus` est sorti du vocabulaire (neuvième mot).** Le nom du
> mécanisme doit dénoter le **périmètre** et jamais l'état d'ingestion
> (proposition : `absence_hors_perimetre`) ; l'acte de renommage est groupé avec
> la renumérotation des mécanismes, en ADR-036.

**Le soulagement est structurel.** Les trois angles *wicked* du départ —
thématiques, domaines, institutions — sont **déjà encodés dans la structure du
corpus DILA**. La juridiction est dans l'ECLI, la chambre dans les métadonnées,
le domaine se lit sur le code (LEGI) ou la chambre (CASS). On ne les énumère
pas : **on les lit sur l'identité canonique** (ADR-018). La wickedness de
contenu disparaît non parce qu'on l'épuise, mais parce que DILA l'a déjà
étiquetée.

### 5.2 Registre

**Dérivées — lues, jamais saisies :**

| Facette | Question répondue en *slice*-ant | Vocabulaire |
|---|---|---|
| **Opérations** (ADR-030) | pourquoi ce document est-il pertinent ? | 8 valeurs, dont 3 jugées (§4.3) |
| **Registre / provenance** | le mécanisme dégrade-t-il selon droit positif vs jurisprudence ? | positif / jurisprudence (JORF-KALI plus tard, ADR-003) |
| **Juridiction émettrice** | quelle institution le système sert-il mal ? | clos (ECLI) |
| **Chambre / formation** | quelle formation décroche ? proxy de domaine en jurisprudence | clos (métadonnées) |
| **Matière** | couverture par matière ? | 12 strates, **null admis** (§6) |
| **Statut temporel** | régression sur l'abrogé, le mort-né ? | en vigueur / abrogé / mort-né (`succeeded_by`) |
| **Profondeur de hop** | courbe de dégradation par hop | 0 / 1 / 2+ (depuis `G₀`) |

**Détenues par construction — posées à l'authoring :**

| Facette | Rôle | Vocabulaire |
|---|---|---|
| **Intention** | le mécanisme dégrade-t-il selon ce que l'utilisateur veut ? | 5 valeurs, ci-dessous |
| **Registre de langue** | coût du décalage de vocabulaire | praticien / citoyen (§6.3) |
| **`polysemique`** | matériau de désambiguïsation, avec ses référents concurrents | booléen + liste (§8.2) |
| **Doc(s) germe** | rend le label auto-étiqueté rejouable | référence(s) |

**Les cinq intentions.** Rétrogradées d'axe en facette par ADR-033 : taguées
sur 100 % des questions, **non couvertes**. Le critère d'une bonne intention
reste qu'elle décrive *ce que l'utilisateur veut*, jamais comment la réponse
est atteinte.

| Intention | Ce que l'utilisateur veut |
|---|---|
| `trouver_la_regle` | Quelle norme régit ma situation |
| `verifier_une_solution` | Comment le juge a tranché ce cas |
| `definir_un_terme` | Que signifie ce mot en droit |
| `retrouver_un_document` | J'ai la référence, donne-moi le texte |
| `connaitre_une_procedure` | Comment agir, dans quel délai, devant qui |

`connaitre_une_procedure` mérite d'exister séparément : la procédure n'est le
sujet d'aucune nomenclature statistique officielle, et elle est pourtant une
part majeure des pourvois et du contentieux administratif. Sans valeur dédiée,
elle reste un angle mort par construction.

### 5.3 Deux pièges, traités explicitement

**Le null est une valeur de première classe**, pas un trou. Le droit non
codifié → matière `null`, jamais devinée. Le rapport affichera « X % des cas
portent une matière » — **et ce pourcentage est lui-même une information**.
Forcer une valeur pour éviter un trou, c'est exactement le jugement arbitraire
que R-05 interdit.

**La difficulté ne se tague pas en entrée.** Elle se reframe en sortie : **un
cas que la baseline rate est *de facto* difficile.** La difficulté devient un
label **calculé par le harnais**, jamais asserté par l'annotateur — mesurer
plutôt qu'affirmer, ADR-012 poussé jusqu'au tag.

---

## 6. ⛔ Les matières — supprimé

> **§6 et §6.1 sont supprimés** depuis le 1ᵉʳ août 2026. Les douze strates ne
> survivent pas comme cadre d'échantillonnage, et le vecteur de pondération
> tombe avec elles (§2.1 : le jeu n'a **aucun** cadre d'échantillonnage, par
> construction). `WIP/B-08-prior-ponderation.md` est sans objet.
>
> **Le texte est conservé en l'état à titre d'archive, pas de spécification.**
> Rien de ce qui suit jusqu'à §6.2 n'est à appliquer. En particulier, « ses
> trous sont permis et chiffrés » ne tient plus : sans cadre, **un trou n'est
> plus chiffrable** — voir §2.1 et
> [ticket #10](https://github.com/left-eyebr0w/murphy/issues/10).
>
> **§6.3 (registre) et §6.4 (date pivot) survivent** et sont à replacer hors de
> cette section — [ticket #12](https://github.com/left-eyebr0w/murphy/issues/12).

<details>
<summary>Archive — statut sous ADR-033 (périmé)</summary>

> **Statut sous ADR-033 : facette, non axe.** La matière reste le **cadre
> d'échantillonnage stratifié** et conserve son vecteur de repondération, mais
> elle n'entre pas dans les cellules à couvrir (§4.1). Elle est équilibrée
> au mieux sur la grille, et **ses trous sont permis et chiffrés** — c'est
> précisément l'information que la couverture forcée détruisait.
>
> C'est ce qui rend le renversement tenable : la wickedness du contenu n'est
> pas épuisée, elle est confinée à une dimension où l'exhaustivité n'est plus
> exigée.

</details>

### 6.1 ⛔ Douze strates — supprimé (archive)

> Conservé à titre documentaire. Les poids ci-dessous n'ont plus d'emploi :
> ils ne sont ni une clé d'allocation, ni une clé de pondération au rapport
> (§6.2). Les références au « §2 » dans ce qui suit visent l'ancienne doctrine,
> réécrite depuis.

Reprises de l'analyse statistique (RSJ 2025, Chiffres clés 2025, Chiffres clés
JA 2025), refondues pour l'usage documentaire. La nomenclature d'origine était
exhaustive sur les **affaires** ; elle manquait deux pans entiers.

| # | Strate | Poids D₁ |
|---|---|---|
| S1 | Pénal — atteintes aux personnes et aux biens | 52,31 % |
| S2 | Pénal — routier, santé publique, environnement, ordre public | 16,47 % |
| S3 | Personnes, famille, état civil, protection des majeurs | 11,30 % |
| S4 | Contrats, obligations, responsabilité, consommation | 1,76 % |
| S5 | Biens, baux, copropriété, immobilier, urbanisme | 2,17 % |
| S6 | Travail et protection sociale | 4,13 % |
| S7 | Affaires, sociétés, entreprises en difficulté | 1,84 % |
| S8 | Fiscal et finances publiques | 0,22 % |
| S9 | Étrangers, asile, nationalité | 2,98 % |
| S10 | Fonction publique et droit administratif général | 0,51 % |
| S11 | Libertés publiques, données personnelles, constitutionnel | **0 %** |
| S12 | Procédure et contentieux (civile, pénale, administrative) | **0 %** |
| — | *Résidu non rattachable* | 6,32 % |

Les poids bouclent exactement sur un socle homogène de **6 162 985 affaires
nouvelles 2024** (même unité, même millésime, aucun recoupement entre piliers).
Table de correspondance détaillée : `WIP/analyse.md`.

**S11 et S12 pèsent 0 % et sont pourtant retenues.** C'est la démonstration la
plus nette de la doctrine du §2 : elles sont absentes de la statistique des
affaires parce que personne ne saisit un tribunal pour connaître le RGPD ou le
délai d'un référé — ce sont des besoins d'**information**, pas de litige. Les
omettre reviendrait à laisser la statistique judiciaire définir le produit.

### 6.2 ⛔ Supprimé — la pondération au rapport

> **Supprimé le 1ᵉʳ août 2026**
> ([ticket #4](https://github.com/left-eyebr0w/murphy/issues/4)), chiffre **et**
> principe.
>
> Le **score d'estimation production** était défini comme le score de diagnostic
> repondéré par les poids du contentieux réel : il meurt avec eux, sans
> arbitrage.
>
> Le **principe** qui l'accompagnait — *on échantillonne pour le pouvoir
> diagnostique, on pondère au rapport ; un poids gravé dans l'échantillonnage
> est irréversible, alors que changer d'avis au rapport est un changement de
> classe 1 (ADR-032)* — aurait pu survivre en changeant de rôle : garantir que
> l'absence de cadre d'échantillonnage (§2.1) soit rattrapable en classe 1 le
> jour où la taxonomie en fournit un. **Écarté par YAGNI** : tant que la
> taxonomie n'existe pas, on ne conserve pas un principe pour une reprise
> hypothétique, et l'on ne conçoit pas non plus son point d'accroche.
>
> **Ce que le rapport publie donc : un seul chiffre, non pondéré.** Le jeu
> n'estime pas la performance en production — c'est le paradigme usage (panel,
> ADR-025) qui répond à cette question, pas celui-ci.

**Ce qui survivait dans cette section sans dépendre de la pondération** — ⛔ et
qui est **dissous à son tour le 2 août 2026**
([#14](https://github.com/left-eyebr0w/murphy/issues/14)) :

> ⛔ ~~⚠️ Une ventilation (par base, par opération, par mécanisme) est une
> **mesure distincte à dénominateur propre**. Restreindre les qrels à un
> sous-ensemble change `R`, donc la coupe adaptative (ADR-007, ADR-030). Deux
> ventilations ne se comparent ni entre elles ni à l'agrégat. À énoncer dans
> chaque rapport.~~

**Ce qui la remplace.** La gêne était **entièrement** un effet de la
normalisation par `R`. `nDCG@R` est retiré ; RBP se moyenne par cas **sans
dénominateur global** ([ADR-007](ADR/ADR-007-metrique-rbp-residu.md)), donc une
ventilation redevient une **moyenne sur un sous-ensemble, directement comparable**
à l'agrégat et aux autres ventilations. Le rapport n'a plus d'avertissement à
porter — il a en revanche **un résidu à publier avec chaque moyenne, ventilée
comprise**, et la **porte du résidu** s'applique à une ventilation comme à
l'agrégat : elle y est simplement **plus large**, sur moins de cas, ce qui est le
bon comportement.

### 6.3 ⛔ Registre — dissous dans `variante_de`

> **Supprimé le 1ᵉʳ août 2026 par le [ticket #11](https://github.com/left-eyebr0w/murphy/issues/11)
> — le quota *et* le tag.** Un décalage praticien ↔ citoyen est *même besoin, même
> label, formulation différente* : c'est la définition de la **variante** (#2), et
> le paragraphe ci-dessous en est l'argument le plus fort — il localise lui-même
> dans l'écart lexical *le premier facteur d'échec*. Le mot `registre` sort du
> vocabulaire ; ce qui survit est une **contrainte de rédaction** au guide
> d'annotation : *les cas variés sont des décalages de registre, pas des
> reformulations lexicales*. Les *« parts approximativement égales »* étaient une
> **couverture** sur une facette, ce que §2.1 a évacué partout ailleurs.
>
> Contrairement au reste du §6, ce paragraphe **n'est pas mort avec les strates** :
> il est mort d'avoir été absorbé par un mécanisme plus général.

Chaque question porte un registre, `praticien` ou `citoyen`, à parts
approximativement égales. Le registre n'est pas décoratif : l'écart lexical
entre la formulation profane et la rédaction normative est le premier facteur
d'échec d'une recherche vectorielle en droit.

### 6.4 Date pivot

Chaque question porte une **date de référence**, figée. LEGI est versionné :
sans date pivot, les qrels se dégradent silencieusement à chaque modification
législative. C'est le premier poste de dette technique d'un golden-set
juridique, et il ne se rattrape pas — un jugement rendu sans date de référence
n'est pas ré-interprétable après coup.

---

## 7. ⛔ Dimensionnement — remplacé

> **Le §7 est faux en entier depuis le 1ᵉʳ août 2026**, y compris les parties que
> les révisions précédentes déclaraient survivantes (la distinction `N_q` / `N_j`,
> et la conclusion de §7.2). Contenu de remplacement arrêté par le
> [ticket #11](https://github.com/left-eyebr0w/murphy/issues/11) ; rédaction en
> attente d'**ADR-036**.
>
> **Le texte est conservé en l'état à titre d'archive, pas de spécification.**
> Ce qui le remplace, en résumé :
>
> - **`N_j` sort du vocabulaire** (comme `cardinalité` et `D₁/D₂/D₃`). Quatre
>   grandeurs : **`N_cas`** — cas *indépendants*, unité du plancher et du taux
>   ventilé ; **`N_q`** — ce qui est interrogé à chaque run, cas *et* variantes ;
>   **`N_pending`** ; et un **budget de jugement**. `N_cas` et `N_q` ne sont pas la
>   même chose, et la confusion est le piège principal de la réécriture.
> - **La dérivation est ascendante, unité = le mécanisme.** `N_cas` est une somme
>   de planchers, jamais un total réparti — §2.1 ayant supprimé le tout à répartir.
> - **Plancher = 30 cas par mécanisme**, par la règle de trois : zéro échec sur
>   30 cas borne le taux d'échec réel à < 10 % (IC 95 %). C'est l'effectif à partir
>   duquel un sans-faute devient informatif, donc la condition de lisibilité de la
>   sentinelle d'E-P2-07. Uniforme, **noyau jugé compris**, et y compris quand un
>   mécanisme couvre deux branches métriques.
> - **v1 = 150 cas, dont 30 jugés ; `N_q ≥ 180`** (150 + les 30 cas variés du §8.1).
>   Les `pending` sont **hors plancher et hors taux** : la baseline les rate par
>   construction, et leur fonction est de désigner les manques (§10), pas de
>   mesurer.
> - **Le budget d'annotation est un nombre total de jugements**, alloué par
>   pondération RBP, **jamais une profondeur fixe** (CLEF eHealth 2016 ; dossier
>   [`recherche/realisme-collections.md`](recherche/realisme-collections.md) §5).
>   Ordre de grandeur : 30 questions × pool ≈ 20 ≈ **600 jugements**.
> - **§7.2 garde sa prémisse et perd sa conclusion.** Le rejeu qu'il cherchait à
>   éviter est **déjà au calendrier** — ADR-003 diffère la vague 2 à « après retours
>   alpha », et `VERSIONS.md` place alpha ph.1 juste après v0. Un lot post-panel
>   monte donc dans un rejeu déjà payé, à coût marginal nul, et vaut plus cher à
>   l'unité. §7.2 est un argument de **calendrier des lots**, pas de volume.
> - **§7.5 se re-dérive en un seul énoncé : `v0` n'ajoute ni ne retire jamais un
>   cas.** Gel **bilatéral** — ajouter coûte un rejeu, retirer rend deux runs
>   incomparables sans qu'aucune classe de changement d'ADR-032 ne le signale. Un
>   cas recalé au typage se **neutralise**, il ne se supprime pas. Trois vecteurs
>   de croissance seulement : la **profondeur du noyau**, la **résorption des
>   `pending`**, et **`k`** (le nombre de configurations classées).
> - **La carotte de §7.4 se dissout** : il n'y a plus de sous-ensemble à tirer, le
>   jeu jugé *est* un mécanisme de l'axe. Et toute sélection maligne est fermée par
>   la littérature — les bons sous-ensembles de topics existent mais **ne sont pas
>   identifiables a priori** (Guiver/Mizzaro/Robertson TOIS 2009, puis Robertson
>   ECIR 2011, Berto/Mizzaro/Robertson ICTIR 2013, Roitero 2020).

### 7.1 Deux volumes, pas un

C'est le point central de ce document, et la correction principale apportée à
la conception antérieure.

| | Ce que c'est | Ce qui le contraint |
|---|---|---|
| **N_q** | Questions **écrites**, présentes dans l'artefact et interrogées à chaque run | Couverture de la matrice · coût de l'ajout ultérieur |
| **N_j** | Questions **jugées**, donc scorables, dans une version donnée | Budget d'annotation · puissance statistique (B-10) |

`N_j ≤ N_q`, et l'écart n'est pas une dette : c'est le régime normal. Une
question écrite mais non jugée est **utile dès sa rédaction** — elle est
interrogée, ses résultats sont archivés dans chaque run, et le jour où on la
juge, il n'y a rien à re-récupérer.

### 7.2 Pourquoi écrire large et juger étroit

ADR-032 classe les changements par coût. Une quatrième ligne s'en déduit, et
elle commande tout le dimensionnement :

| Changement | Re-récupération ? | Historique comparable ? |
|---|---|---|
| Corriger un grade, réviser le guide, re-dériver | Non | Oui |
| Juger des documents supplémentaires sur une question existante | Non | Oui |
| **Juger une question déjà présente dans les runs** | **Non** | **Oui** |
| **Ajouter une question au jeu** | **Oui** | Non, sauf rejeu des configs |

La troisième ligne ne figure pas telle quelle dans ADR-032 ; elle s'en déduit
de sa prémisse — *un run est `question → documents ordonnés`, il ne contient
aucun jugement*. Si la question était dans le run, ses résultats y sont déjà.

**Conséquence directe : écrire 170 questions maintenant et en juger 60 coûte
strictement moins, sur la durée, qu'en écrire 60 maintenant et 110 plus tard.**
Le premier scénario paie une fois le seul poste cher ; le second le paie deux
fois.

> Réserve honnête : si l'ingestion s'étend entre deux versions, `W` change
> (ADR-027, ADR-031) et un rejeu est de toute façon nécessaire. L'argument ne
> supprime pas ce rejeu — il garantit qu'il reste le **seul** coût, et qu'il
> n'est pas doublé par un lot de questions tardives.

### 7.3 Dériver N_q

Deux dérivations ont été écartées avant celle-ci, et pour des raisons
différentes.

`12 strates × 6 types × 4 requêtes = 288` (conception d'origine) : le second
facteur n'était pas une partition. `12 matières × 5 intentions × 2 = 120`
(sous ADR-030) : les deux facteurs étaient bien des propriétés de la requête,
mais **la matière n'est plus un axe** sous ADR-033 — la faire multiplier
réintroduirait le contenu comme dimension à couvrir.

L'allocation porte donc sur les **cellules valides** de §4.1, et la matière est
équilibrée à l'intérieur.

```
Allocation      14 cellules (mécanisme × cardinalité) × 10   = 140
                matière équilibrée ≈ 12 par matière, trous permis
Strate-frontière  questions à cheval sur deux matières       ≈  15
                                                             ─────
N_q                                                          ≈ 155
   dont cellule (8, cardinalité 0) → précision seule         ≈  10
   dont scorables Doc-MRR / Recall@R / nDCG@R                ≈ 145
```

**Les paires isosémantiques ne s'ajoutent plus, elles sont dans la grille.** Le
mécanisme 4 (`robustesse_paraphrase`) occupe trois cellules, soit ≈ 30
questions = **15 paires à qrels partagés**. Le poste cher — les jugements — est
divisé par deux sur ces cellules ; seule la rédaction est dupliquée.

**Vérification ex post, non allocation** (E-P2-07) : les 14 cellules non vides ;
mécanisme et cardinalité sur 100 % des cas ; intention et matière taguées à
100 % mais **non couvertes**. Si une matière ne produit aucun cas dans une
cellule, c'est un constat chiffré au rapport — pas une case à remplir
mécaniquement.

Le résultat tombe dans le même ordre de grandeur que les 288 d'origine et que
les 120 intermédiaires. **Le chiffre n'a jamais été absurde ; c'est sa
dérivation qui l'était, deux fois de suite.** La distinction N_q / N_j, elle,
reste ce qui change tout : les 288 étaient présentés comme un objectif
d'annotation.

### 7.4 Dériver N_j — la puissance statistique

C'est le seul plancher qui ne dépende ni du corpus ni du budget, donc le seul
qu'on puisse poser *a priori*. B-10 compare deux configurations par un test
apparié ; sur `n` requêtes, l'effet minimal détectable suit `n ≈ 7,85 / d²`
(α = 5 % bilatéral, puissance 80 %).

| Effet détectable | n requêtes jugées |
|---|---|
| d ≈ 0,5 — net | ~31 |
| d ≈ 0,35 — modéré | ~64 |
| d ≈ 0,25 — fin | ~126 |
| d ≈ 0,2 — très fin | ~196 |

**N_j(v1) ≈ 60–70.** C'est le premier palier qui détecte un effet modéré, soit
le besoin réel quand on départage deux configurations de récupération. En
dessous de 30, le test ne conclut que sur des écarts grossiers ; au-delà de
130, on achète une finesse que le budget d'annotation solo ne peut pas
alimenter et que le bruit d'annotation solo rendrait illusoire.

> Ces valeurs sont des ordres de grandeur. B-10 emploiera vraisemblablement un
> test de permutation, les deltas de nDCG n'étant pas normalement distribués ;
> le calibre reste le même.

**Sélection du sous-ensemble jugé** : une **carotte** à travers la matrice, pas
un bloc. Juger 60 questions concentrées sur trois matières donnerait 60
questions et un jeu qui ne dit rien des neuf autres. Le tirage prend au moins
une question par case `matière × intention`, puis complète.

### 7.5 Croissance

| Version | N_q | N_j | Ce qui change |
|---|---|---|---|
| v1 | ~155 | ~60–70 | Gel initial, jugements sur le corpus disponible |
| v2+ | ~155 | croissant | Jugements supplémentaires — **gratuits** (§7.2), corrections de grades au fil de l'eau |
| v_n | révisé | — | Ajout d'un lot de questions, **à un moment choisi**, suivi d'un rejeu des configurations de référence |

Les corrections de jugement se font au fil de l'eau et n'invalident rien. Les
ajouts de questions se font **par lots**, jamais à l'unité.

---

## 8. Sous-ensembles

### 8.1 Trois sous-ensembles sont entrés dans la grille

ADR-033 absorbe comme cellules trois dispositifs qui vivaient à côté du jeu.
Ils n'ont pas disparu : ils ont cessé d'être des exceptions.

| Ancien sous-ensemble | Devient | Ce que ça change |
|---|---|---|
| Questions négatives | Cellule `(8, cardinalité 0)` | Entrent dans la couverture, restent hors métrique primaire |
| Paires isosémantiques | Dispositif du mécanisme 4 | Comptées dans N_q (§7.3), plus en surplus |
| Matériau de polysémie | Matériau du mécanisme 7 | Devient une ligne d'axe, plus un flag isolé |

**Ce qui n'a pas changé, et ne pouvait pas changer.** Une question dont la
bonne réponse est *aucun résultat pertinent* (droit étranger, hors périmètre
DILA) a `R = 0`, donc **aucune métrique de rappel n'y est définie** — c'était
déjà vrai quand la métrique primaire coupait à `R`, et ça le reste. *(Mise à
jour du 2 août : la coupe à `R` a disparu avec `nDCG@R`
— [ADR-007](ADR/ADR-007-metrique-rbp-residu.md) — mais le fait est indépendant
de la métrique : sans pertinent, il n'y a pas de rappel à mesurer. **RBP n'y
supplée pas** : tous les gains valant 0, `RBP = 0` pour tout run, quel que soit
le volume de bruit remonté — la métrique est définie mais **identiquement nulle,
donc sans pouvoir discriminant**. La branche `R = 0` reste précision-seule. Elle
n'est pas inerte pour autant : le **taux de remontée au-delà du seuil**, décrit
ci-dessous, **se compare entre configurations** — une régression du *fail-fast*
s'y voit. Ce qui manque est une métrique de *classement*, pas une comparaison.)* Ces questions restent donc mesurées autrement —
taux de résultats au-delà d'un seuil de score, sur un jeu où toute remontée est
un faux positif — au **même statut que le diagnostic de co-citation**
(ADR-029) : précision seulement, jamais de rappel, jamais de grade.

Le niveau de cardinalité 0 est exactement ce qui permet de les **couvrir** sans
les **scorer** comme le reste. Sans elles, le jeu ne mesure que le rappel et
jamais la précision : c'est le sous-ensemble le plus souvent omis, et le moins
cher à produire.

**L'économie des paires isosémantiques est intacte** : une même question de
droit, **des qrels identiques**, deux formulations — praticien et citoyen. Le
delta de score entre les deux membres donne **le coût du décalage de
vocabulaire en un seul nombre**. Le poste cher (les jugements) est partagé,
seule la rédaction est dupliquée. Elles restent concentrées sur les matières où
l'écart de registre est le plus large, donc les plus exposées au public — S1
(pénal courant), S3 (famille), S5 (logement), S6 (travail) — la matière étant
désormais une facette (§6), c'est un choix d'équilibrage et non un quota.

### 8.2 Matériau adversarial de polysémie

Le corpus statistique fournit **cinq nomenclatures officielles divergentes
décrivant la même réalité**. C'est du matériau de désambiguïsation authentique,
produit par l'administration elle-même — et non fabriqué pour le test. Il
peuple directement les cellules du mécanisme 7.

| Piège | Divergence |
|---|---|
| *« contentieux social »* | Trois référents incompatibles : aide sociale et RSA (TA) ; relations du travail (nomenclature civile) ; sécurité sociale sous « pôle social » (TJ) |
| *Stupéfiants* | Sous-ligne de « santé publique » dans une table, poste autonome dans deux autres |
| *« Atteinte à l'autorité de l'État »* | Devient « atteinte à l'ordre administratif et judiciaire » ailleurs — périmètres non identiques |
| *Nomenclature administrative* | 8 postes en 2024 contre 12 en 2025, même juridiction |

Ces questions portent le flag `polysemique` avec la liste de leurs référents
concurrents. Le flag est **constatable** (le terme a N référents attestés), à la
différence d'une étiquette de difficulté — c'est la raison pour laquelle T3
avait survécu là où T1–T6 tombaient, et pourquoi il est aujourd'hui un
mécanisme à part entière (§4.4).

### 8.3 Strate-frontière — le seul vrai hors quota

Questions tombant **entre deux matières**. Elles réintroduisent délibérément ce
que la stratification rend invisible : le résidu de 6,32 % non rattachable de
l'analyse D₁ — « autres » civils, référés, « autres contentieux »
administratifs.

Elles portent `matière = null`, qui est une valeur de première classe et non un
trou (§5.3). Une classification qui n'a jamais de cas limite n'est pas une
bonne classification, c'est une classification qu'on n'a pas testée.

---

## 9. Comment on juge

**Échelle 0–3, dérivée d'une cascade de trois tests binaires** (ADR-005) — on
ne saisit jamais un grade directement.

| Test | Question | Si non |
|---|---|---|
| q1 | Même question de droit ? | grade 0 |
| q2 | Citable dans une consultation ? | grade 1 |
| q3 | Support principal de la solution ? | grade 2 (oui → 3) |

Deux conventions qui surprennent et qu'il faut tenir : la pertinence est
**topique, non directionnelle** — un arrêt *contraire* bien en point est un 3 ;
et les trois réponses sont **stockées avec le grade** (ADR-008), ce qui rend
les désaccords localisables à la question près et les grades re-dérivables sans
relecture.

**Granularité : au niveau document** (article LEGI, décision — ADR-004), qui
est l'unité stable. Annoter au chunk casse à chaque re-chunking. Un
sous-ensemble d'une cinquantaine d'items annotés au passage permet de
diagnostiquer le chunking séparément, sans contaminer la référence.

**Projection dans la métrique** : les grades entrent dans RBP par **projection
linéaire** `g/3` (0 · 0,33 · 0,67 · 1) — l'échelle est un *compte de portes
franchies*, non une intensité (ADR-005, [ADR-007](ADR/ADR-007-metrique-rbp-residu.md)).
Conséquence de rédaction pour le guide : **chaque porte doit se franchir ou non
sans demi-mesure**, c'est la propriété sur laquelle la métrique s'appuie. Les
cas gratuits, eux, ont un label **binaire** — un fait détermine
l'ensemble-réponse — et entrent avec des gains `{0, 1}`.

**Complétude — le point de vigilance a changé de nature le 2 août 2026.**

> ⛔ *Rédaction antérieure :* « ADR-007 fondait la robustesse de nDCG@R sur le
> pooling **et** les citations minées ; ADR-029 ayant retiré les secondes, elle
> repose entièrement sur le pooling et sur ce jeu. Comme `R` dépend du nombre de
> documents jugés pertinents, des qrels incomplètes ne font pas qu'ajouter du
> bruit : **elles déplacent la coupe**. »

Le déplacement de coupe **n'existe plus** : `nDCG@R` est retiré, et RBP ne
dépend pas de `R` ([#14](https://github.com/left-eyebr0w/murphy/issues/14)).
L'incomplétude n'a pas disparu pour autant — elle cesse d'être **subie** pour
devenir **mesurée** :

- **le résidu** l'exprime, trou par trou, run par run. Tout score publié est
  `score + résidu` ; l'écart entre deux configurations porte une **borne
  déterministe**, et un intervalle contenant zéro **n'admet aucun test** ;
- **juger davantage ne peut que réduire l'incertitude** — propriété que `nDCG@R`
  n'avait pas, où trois effets de signes différents se composaient (Lu, Moffat &
  Culpepper, IRJ 2016 §4) ;
- la complétude repose toujours **entièrement sur le pooling et sur ce jeu**
  (ADR-029 ayant retiré les citations minées), mais ce n'est plus une fragilité
  silencieuse : c'est une grandeur publiée. **Le biais de pool, lui, reste non
  mesurable en solo mono-système, par construction** — la position défendable
  est de l'assumer, non de prétendre le contraire
  ([#7](https://github.com/left-eyebr0w/murphy/issues/7)).

> ⚠️ **Garde-fou, non négociable.** Une modification de qrels ne se justifie
> **jamais** par un résultat de run. « J'ai relu, ce grade 1 est un 2 » est
> recevable ; « cette config remonte ce document, il doit être pertinent » ne
> l'est pas — c'est ajuster l'étalon à l'issue souhaitée (ADR-031 §5, ADR-032
> §5). Toute modification est datée et motivée sans référence à une mesure.

---

## 10. Ce que le jeu exige de l'ingestion

> Section **re-dérivée** le 1ᵉʳ août 2026
> ([ticket #4](https://github.com/left-eyebr0w/murphy/issues/4)). Elle tirait
> auparavant ses exigences des strates S6 / S11 / S12, qui sont tombées. Elle se
> tire désormais de la **source de gratuité du label** — un objet qui, lui,
> tient (§2.3).

> ⚠️ **Frontière explicitée le 5 août 2026**
> ([#15](https://github.com/left-eyebr0w/murphy/issues/15)). Deux objets étaient
> confondus parce qu'ils ont **la même observation aujourd'hui** — le système ne
> trouve rien — et des **verdicts opposés**. Rédaction définitive en ADR-036.
>
> | Cible | Source | Statut | Fonction |
> |---|---|---|---|
> | Hors du **périmètre DILA**, définitivement | frontière de périmètre | **scoré**, `R = 0` | teste le *fail-fast* (ADR-020) |
> | Dans DILA, **pas encore ingérée** | `identite` | **`pending`** — interrogé, non jugé | **désigne les manques** — c'est cette section |
>
> **Leur intersection — une cible non ingérée mais scorée `R = 0` — est
> exactement ce qui se périmait, et c'est la seule chose qui n'aurait jamais dû
> exister.** Le mécanisme hors périmètre cesse donc d'en absorber une part : le
> non-ingéré n'a plus qu'un domicile, `pending`, et `N_pending` devient le
> **seul** véhicule de la fonction décrite ci-dessous (dimensionnement →
> [#20](https://github.com/left-eyebr0w/murphy/issues/20)).
>
> **Contrôle mécanique associé** : à chaque version de collection déclarée, on
> re-vérifie qu'aucune cible déclarée hors périmètre n'a été ingérée. Ce contrôle
> **ne devrait jamais se déclencher** — c'est une **alarme**, pas une réparation,
> et son déclenchement signifie que *la définition du périmètre était fausse*
> (intake → [#21](https://github.com/left-eyebr0w/murphy/issues/21)). C'est parce
> que cette alarme existe que **rien n'est enregistré par cas**, bien que le
> périmètre DILA ne soit énuméré par aucun document de ce dépôt.

Le golden-set **désigne les manques du corpus** au lieu de les épouser. Le
mécanisme est celui de §2.3 : sur la source `identite`, le label vit hors du
corpus, donc une question peut être écrite sur une cible non ingérée.

Une telle question reste **`pending`** : écrite, gelée, interrogée à chaque run,
non jugée. Elle devient jugeable **sans aucun coût de re-récupération** le jour
où sa base arrive (§7.2). C'est le cas le moins cher du jeu, et il en est écrit
délibérément.

### 10.1 Un constat émergent, non une dérivation exhaustive

C'est le changement de nature qu'il faut tenir. L'ancienne table disait *voici
les strates, donc voici ce qu'il faut ingérer* — une dérivation qui se
prétendait complète parce qu'un cadre d'échantillonnage la fondait. **Ce cadre
n'existe plus** (§2.1), donc la liste ne peut plus être qu'un relevé :

> **Voici ce que le jeu a réclamé et que le corpus ne sert pas.**

Elle se lit sur les questions `pending` du jeu, à tout moment, sans travail
supplémentaire — chaque `pending` nomme la base qui lui manque.

**Conséquence à ne pas masquer** : le critère fourni à ADR-003 (contenu de la
vague 2 d'ingestion, candidates KALI et CIRCULAIRES) est désormais **non
exhaustif**. Il reste un critère — *ce qu'il faut ingérer est ce sans quoi des
questions légitimes restent sans réponse possible* — mais il ne peut plus
prétendre couvrir tout ce qui manque, seulement ce que le jeu a eu l'occasion
de demander.

Le **volume** de `pending` à écrire n'est pas fixé ici : voir §7 et
[ticket #11](https://github.com/left-eyebr0w/murphy/issues/11).

---

## 11. Ce qui reste ouvert

| # | Point | Qui tranche |
|---|---|---|
| 1 | **Méthode de génération des requêtes** (D-01). E-T-01 interdit toute dépendance du *harnais* à un LLM générateur ; employer un LLM **hors ligne** pour fabriquer des requêtes n'est pas exclu, mais la frontière doit être écrite. Règle déjà posée : **jeter, jamais reformuler**. | B-08 |
| 2 | **Vocabulaire des mécanismes** (§4) — liste de travail issue d'ADR-033, destinée à évoluer ; et **vocabulaire d'intentions** (§5.2), proposition non validée. | Porteur (ADR-028) |
| 3 | **Nombres du §7** — dérivés, non actés. | Porteur (ADR-028) |
| 4 | **Espace des cibles.** `Section` et `Texte` ne sont pas des unités de citation au sens d'ADR-004 mais pèsent un tiers du graphe. Décision prise : **ne pas restreindre, observer d'abord** — si elles ne remontent jamais, la question se clôt sans qu'on ait rien décidé. | Observation |
| 5 | **Point d'entrée outillage** — la re-notation de tout l'historique doit tenir en **une commande**, sans quoi le modèle de versionnement d'ADR-032 n'est pas praticable. | B-11 |

---

## 12. Références

**Décisions** — ADR-004 (unité document, ventilation par base) · ADR-005
(cascade q1–q3, échelle 0–3, projection linéaire) · ADR-006 (agrégation
chunk→document) · [ADR-007](ADR/ADR-007-metrique-rbp-residu.md) (**RBP + résidu**
— réécrit le 2 août 2026, `nDCG@R` retiré) · ADR-008 (format JSONL, provenance) ·
ADR-016 (découplage récupération/génération) · ADR-017 (strates de pérennité) ·
ADR-012 (constat sur preuves) · ADR-018 (identité canonique — support des tags
dérivés) · ADR-028 (régimes de vérification) · ADR-029 (garde-fou de
circularité ; statut de la cardinalité 0) · ADR-030 (opérations, régime
jugée/dérivée — **axes remplacés par ADR-033**) · **ADR-031** (graphe témoin
`G₀`) · **ADR-032** (gel par version, re-notation) · **ADR-033** (axes
mécanisme × cardinalité)

**Exigences** — `EXIGENCES_v0.md` E-P2-06 (gel + guide + grades), E-P2-07 (deux
axes), E-P2-09 (test apparié), E-P2-10 (reproductibilité), E-T-01, E-T-02

**Travaux** — `BACKLOG.md` B-08 (ce jeu), B-09 (set graph-hop), B-10 (test
apparié), B-11 (baseline chiffrée) · `WIP/B-08-cadrage.md` (méthode, pièges
P-01 à P-04) · `WIP/B-08-prior-ponderation.md` (protocole de pondération) ·
`WIP/analyse.md` (socle statistique, rattachements sourcés)
