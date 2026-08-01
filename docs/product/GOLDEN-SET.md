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
> et atterrira en **ADR-035**, qui remplacera ADR-033 et amendera ADR-034.
>
> | Section | État | Pourquoi |
> |---|---|---|
> | **§4** — les deux axes | ⛔ **faux** | La cardinalité n'est plus un axe. Le tableau des huit mécanismes est périmé sur deux points : la liste tombe à **sept** (`robustesse_paraphrase` devient une variante) et la colonne `Régime` classe `concept_vers_instance` en *détenu*, ce qui est faux — son label asserté est une opinion. |
> | **§4.1** — les quatorze cellules | ⛔ **supprimé** | La grille n'existe plus. Aucune cellule n'est à peupler. |
> | **§6** — les matières, §6.1 douze strates, §6.2 pondération | ⛔ **supprimé** | Les strates ne survivent pas comme cadre d'échantillonnage ; le vecteur D₁ tombe avec elles. `WIP/B-08-prior-ponderation.md` est sans objet. |
> | **§7** — dimensionnement | ⚠️ **à re-dériver** | `N_q ≈ 155` reposait sur `14 cellules × 10` : les facteurs n'existent plus. Et `N_j ≈ 60–70` (§7.4) est **optimiste d'un facteur ≈ 2,5** — la pratique publiée demande **150–165 requêtes jugées** pour départager deux configurations proches (Webber/Moffat/Zobel, CIKM 2008 §5.1). La distinction `N_q` / `N_j` elle-même, et l'argument de coût du §7.2, survivent. |
> | **§8.1** — paires isosémantiques | ⚠️ **requalifié** | Elles ne sont plus un sous-ensemble d'un mécanisme : la paraphrase devient une **variante** applicable à n'importe quel cas, donc mesurable partout sans coût de label. |
> | **§8.3** — strate-frontière | ⚠️ **suspendu** | Défini par rapport aux strates, qui tombent. |
> | **§4.4** — les types de difficulté | ✅ **tient** | Son raisonnement est indépendant de la grille. |
> | **§1, §2, §3, §5, §9, §10, §11** | ⚠️ **à instruire** | Non démolis, mais leurs dépendances bougent. §2 (la doctrine) et §10 (ce qu'on exige de l'ingestion, dérivé des strates S6/S11/S12) sont des tickets ouverts de la carte. |
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

## 2. La doctrine : on spécifie l'usage, pas le stock

Trois distributions coexistent et divergent fortement.

| | Nature | Biais propre |
|---|---|---|
| **D₁ — contentieux réel** | Volume d'affaires portées devant un juge | Dominé par les atteintes aux biens (35,1 % du socle), dont la majorité sans auteur identifié, donc quasiment sans jurisprudence publiée |
| **D₂ — empreinte documentaire** | Volume de documents effectivement ingérés | Reflète les choix d'ingestion et les biais éditoriaux des bases, pas le besoin |
| **D₃ — questions réellement posées** | Besoin de décision des utilisateurs | Non observable avant l'alpha ph.1 ; gouverné par l'enjeu, non par la fréquence |

**Le jeu se construit sur D₃, approché par D₁ corrigé. D₂ est écarté comme
entrée de conception.**

C'est la décision structurante de ce document, et elle a une raison de fond :
dimensionner depuis le corpus laisserait **l'ingestion définir ce qu'on
mesure**. L'instrument suivrait l'objet — la circularité qu'ADR-029 écarte
pour la strate 2, et qu'ADR-031 écarte pour le graphe, revenue par la porte
du corpus.

**Conséquence assumée, et c'est un bénéfice :** le golden-set est écrit
**avant** l'ingestion étendue. Une question dont la cible exige une base non
encore ingérée n'est pas un défaut du jeu — c'est une **exigence adressée à
l'ingestion** (voir §10). Le jeu cesse d'être un miroir du corpus pour devenir
une spécification de ce que Murphy doit savoir répondre.

**Bénéfice secondaire, structurel** : écrire les questions sans avoir les
documents sous les yeux rend le piège de la **requête-décalque** (P-01,
`WIP/B-08-cadrage.md`) matériellement impossible. On ne décalque pas un
document qu'on n'a pas. Le risque résiduel est inverse et bénin — une question
sans cible, qui reste `pending` jusqu'à ce que l'ingestion la serve.

> ⚠️ Le corpus revient en fin de chaîne, et à un seul titre : **ordonnancer
> l'effort d'annotation** (quelles questions sont jugeables aujourd'hui). Le
> même déplacement de rôle que le pooling a subi avec ADR-032 — de levier de
> complétude à ordonnanceur.

---

## 3. Trois couches, trois régimes de gel

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

---

## 4. Les deux axes

ADR-033 fixe la structure, et elle n'est pas celle qu'on attend d'un jeu de
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

**Quatre cardinalités, chacune déclarant sa métrique :**

| Cardinalité | Nature du besoin | Métrique de la cellule |
|---|---|---|
| **0 — vide attendu** | Hors corpus, hors périmètre | **Précision seule**, statut ADR-029 : jamais de rappel, jamais de grade |
| **1 — cible unique** | Known-item, référence résolue | **Doc-MRR**, lecture *success@1* |
| **n — ensemble borné** | Conjonctif (principe + exception) | **Recall@R**, tout-ou-rien |
| **ouvert — topique** | Pertinence graduée | **nDCG@R** |

Faire de la cardinalité un axe *explicite* **interdit mécaniquement** l'erreur
« nDCG@R partout ». Et aucune métrique n'est à implémenter : *success@1* se lit
sur Doc-MRR, `R` est écrit par authoring dans la cellule « ensemble borné »
donc la coupe y reste adaptative (ADR-007 — **le refus des coupes constantes
tient**, il n'y a pas de `Recall@k` dans ce jeu).

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

## 6. Les matières

> **Statut sous ADR-033 : facette, non axe.** La matière reste le **cadre
> d'échantillonnage stratifié** et conserve son vecteur de repondération D₁,
> mais elle n'entre pas dans les cellules à couvrir (§4.1). Elle est équilibrée
> au mieux sur la grille, et **ses trous sont permis et chiffrés** — c'est
> précisément l'information que la couverture forcée détruisait.
>
> C'est ce qui rend le renversement tenable : la wickedness du contenu n'est
> pas épuisée, elle est confinée à une dimension où l'exhaustivité n'est plus
> exigée.

### 6.1 Douze strates

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

### 6.2 Le tirage est uniforme, la pondération vient au rapport

**On échantillonne pour le pouvoir diagnostique, on pondère au moment du
rapport.** Un plancher par case garantit que chaque strate dit quelque chose ;
les poids D₁ ne sont jamais une clé d'allocation.

Deux chiffres sortent d'un jeu unique :

- un **score de diagnostic**, non pondéré, lisible strate par strate ;
- un **score d'estimation production**, repondéré par les poids ci-dessus.

Ce n'est pas une commodité mais une propriété de coût : un poids gravé dans
l'échantillonnage est irréversible sans réécrire le jeu, alors que changer
d'avis sur la représentativité au rapport est un changement de **classe 1**
(ADR-032) — re-notation seule, zéro re-récupération.

> ⚠️ Une ventilation (par strate, par base, par opération) est une **mesure
> distincte à dénominateur propre**. Restreindre les qrels à un sous-ensemble
> change `R`, donc la coupe adaptative de nDCG@R (ADR-007, ADR-030). Deux
> ventilations ne se comparent ni entre elles ni à l'agrégat. À énoncer dans
> chaque rapport.

### 6.3 Registre

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

## 7. Dimensionnement

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
DILA) a `R = 0`. Or nDCG@R coupe le classement à `R` (ADR-007) : **la coupe est
indéfinie, la métrique aussi.** Ces questions restent donc mesurées autrement —
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

**Complétude — le point de vigilance.** ADR-007 fondait la robustesse de nDCG@R
sur le pooling **et** les citations minées ; ADR-029 ayant retiré les secondes,
elle repose désormais **entièrement sur le pooling et sur ce jeu**. Comme `R`
dépend du nombre de documents jugés pertinents, des qrels incomplètes ne font
pas qu'ajouter du bruit : **elles déplacent la coupe**.

> ⚠️ **Garde-fou, non négociable.** Une modification de qrels ne se justifie
> **jamais** par un résultat de run. « J'ai relu, ce grade 1 est un 2 » est
> recevable ; « cette config remonte ce document, il doit être pertinent » ne
> l'est pas — c'est ajuster l'étalon à l'issue souhaitée (ADR-031 §5, ADR-032
> §5). Toute modification est datée et motivée sans référence à une mesure.

---

## 10. Ce que le jeu exige de l'ingestion

Effet de bord recherché de la doctrine du §2 : construit sur l'usage, le
golden-set **désigne les manques du corpus** au lieu de les épouser.

| Strate | Ce qu'elle réclame | État |
|---|---|---|
| S6 — Travail | KALI, ACCO (conventions et accords collectifs) | Non ingérés |
| S11 — Libertés publiques | CONSTIT en volume, CNIL | CONSTIT ingéré à l'état de trace |
| S12 — Procédure | CPC, CJA, CPP dans LEGI ; CASS et JADE en volume | Partiel |
| Toutes | Volumétrie des 5 bases de jurisprudence | CAPP et INCA à l'état de trace |

Ces lignes alimentent directement le point ouvert d'ADR-003 (contenu de la
vague 2 d'ingestion, candidates KALI et CIRCULAIRES), qui attendait un critère
pour être tranché. **Le golden-set est ce critère** : ce qu'il faut ingérer est
ce sans quoi des questions légitimes restent sans réponse possible.

Une question sans cible disponible reste **`pending`** : écrite, gelée,
interrogée à chaque run, non jugée. Elle devient jugeable sans aucun coût de
re-récupération le jour où sa base arrive (§7.2).

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
(cascade q1–q3, échelle 0–3) · ADR-006 (agrégation chunk→document) · ADR-007
(nDCG@R, coupe adaptative, complétude) · ADR-008 (format JSONL, provenance) ·
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
