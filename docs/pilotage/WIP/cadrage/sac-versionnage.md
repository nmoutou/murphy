# Sac des livrables — document de travail

> **Ce que c'est.** Un inventaire **non trié** des artefacts à produire. Aucun
> jalon, aucun canal, aucun ordre : le jalonnement et le découpage en canaux sont
> à refondre entièrement, et ce sac est ce qu'on triera *ensuite*.
>
> **Périmètre : les livrables seulement.** Ce qui doit être *produit*. Les
> prétentions (`PT-nn`), la sémantique des protocoles et la structure des jalons
> ne sont pas ici — elles s'arrangeront en fonction de ce sac.
>
> **Statut : durable jusqu'au tri.** Contrairement à
> `description-target-golden-set.md`, ce document n'est pas jetable — il est
> destiné à être consommé par l'exercice de rejalonnement, puis à disparaître
> dans lui.

## Règles de tenue de ce sac

- **Une ligne = une responsabilité.** La colonne *Ce que c'est* énonce **un seul**
  travail à faire, en verbe + objet. Un « et » qui joint deux travaux est une
  ligne à couper. C'est un test d'**ordonnançabilité** : un livrable qui porte
  deux responsabilités a deux jeux de prérequis, donc ne peut pas être placé dans
  un jalon sans être coupé en catastrophe.
- **Aucun ADR n'est un livrable.** Un ADR est la *trace* d'une décision, adressée
  au porteur plus tard ; un livrable est un *instrument*, adressé à quelqu'un
  maintenant. Les ADR restent, produits en marge, jamais bloquants. Là où le sac
  disait « ADR-0nn », il nomme désormais le document réel qui se cachait derrière.
- **Deux axes de rangement.** La **nature** (§1–§4, les sections) et le
  **domaine** (les sous-sections). Le **numéro** est l'identifiant stable à
  travers les deux : il ne se renumérote pas quand une ligne change de section.
  Les numéros ne se suivent donc pas à l'intérieur d'une section — c'est normal.
- **Le regroupement ne porte aucun ordre** et n'anticipe aucun jalon.

---

## 1. Documents dus

### 1.1 Domaine — jugement

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **1** | **Guide d'annotation** | dire à l'assesseur comment attribuer un grade (cascade q1→q3) | **n'existe pas** — `ADR-008.guide_version` pointe vers un document inexistant ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) |
| **2** | **Contraintes de rédaction de la `narrative`** | dire comment se rédige la `narrative` (huit contraintes) | à écrire ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) |
| **3** | **Protocole d'assessment *inter*** | définir la machinerie du désaccord entre assesseurs (troisième compartiment, séparateur en aveugle, table de réparation q2/q3) | à écrire ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) — sans domicile depuis qu'ADR-038 cesse d'être un livrable |
| **5** | **Conduite d'une campagne d'assessment** | définir comment une campagne s'ordonne et s'arrête (file unique, règle de famine, tourniquet par cas, deux critères d'arrêt) | ⚠️ **absent du sac jusqu'ici** — écrit seulement dans `description-target-golden-set.md` |
| **6** | **Pilote de calibration** | définir l'essai qui produit le seuil d'auto-cohérence (~5 cas, re-jugement à l'aveugle) | décidé en [#18](https://github.com/left-eyebr0w/murphy/issues/18) — était rangé à tort sous *pooling* |
| **7** | **Protocole de pooling** | définir qui contribue au pool et comment le budget s'y alloue (allocation gloutonne par contribution RBP) | décidé en [#18](https://github.com/left-eyebr0w/murphy/issues/18), **sans domicile déclaré** |

### 1.2 Domaine — contenu

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **8** | **Spécification des mécanismes** | définir l'axe de récupération : liste fermée, fixée *a priori*, un cas porte un mécanisme et un seul | à écrire — c'était le cœur d'ADR-036 |
| **13** | **Schéma de l'enregistrement d'authoring** | fixer les champs d'un cas (`case_id` · `mecanisme` · `texte` · `narrative` · `germe` · `leurre` · `date_pivot` · `variante_de` · `origin` · `origine_notion`) | forme fixée ([#12](https://github.com/left-eyebr0w/murphy/issues/12)), non implémentée |

### 1.3 Domaine — mesure

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **16** | **Spécification de l'instrument de mesure** | définir ce qui est mesuré et comment (`RBP(p) + résidu`, famille sentinelle, grades 0–3, écart apparié, les deux refus de publication) | ⚠️ **absent du sac jusqu'ici** — écrit seulement dans `description-target-golden-set.md` |
| **17** | **Format du rapport** | définir ce qu'une publication contient et dans quel ordre (`correspondance_litterale` en tête, ventilations sans seuil, grandeur de transfert par paire) | épars, non rassemblé |
| **18** | **Contrat de recevabilité** | définir ce qu'un tiers doit fournir pour qu'un run étranger soit projetable, notable et poolable | ⚠️ **domicilié en ADR-008** — jamais rédigé pour son lecteur |

### 1.4 Domaine — identité & versionnage

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **19** | **Spécification des trois hashes** | définir ce qui identifie une collection : sur quoi portent `corpus`, `cas` et `qrels` | forme fixée, non implémentée |

### 1.5 Domaine — contestations

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **27** | **Protocole d'intake des contestations** | définir la porte d'entrée (unité = une contestation, motifs en liste fermée + « autre », cinq issues, pas de SLA) | à écrire ([#21](https://github.com/left-eyebr0w/murphy/issues/21)) — c'était le cœur d'ADR-032 réécrit |

---

## 2. Artefacts de la collection

*Domaine — contenu, en totalité.*

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **14** | **Les cas** | écrire 5 mécanismes peuplés × plancher de 30 = **150** cas | aucun écrit |
| **15** | **Les qrels** | produire ≈ 600 jugements en **profondeur de départ** sur les 30 cas jugés | — |

> `traversee_chainee` ([#16](https://github.com/left-eyebr0w/murphy/issues/16)) et
> `desambiguisation` ([#9](https://github.com/left-eyebr0w/murphy/issues/9),
> [#20](https://github.com/left-eyebr0w/murphy/issues/20)) ne sont **pas des
> livrables distincts** : ce sont des instances **différées** de 14.

---

## 3. Organes techniques

### 3.1 Domaine — identité & versionnage

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **20** | **Porteur de hashes au run** | calculer les trois hashes et les attacher à chaque run | non implémenté |
| **21** | **Lignée corpus CalVer** | nommer des points `AAAA.MM`, chacun adossé à un hash `corpus` | à créer |
| **22** | **L'épingle** | désigner le point de lignée que stable sert **et** évalue | ⚠️ **existe peut-être déjà** — le backend résout sa collection au boot depuis `MURPHY_META.meta_published_collection` ([collectionPointer.ts](backend/src/infra/collectionPointer.ts)). À vérifier : bon organe, ou simple voisin ? |
| **23** | **Émission machine de l'identité** | publier `produit X.Y.Z` + `corpus AAAA.MM` + les trois hashes, jamais recopiés à la main | à créer (voisin de `/api/v1/health`) |
| **24** | **Affichage de la date du corpus** | porter la date du droit servi jusqu'à l'utilisateur | à créer (frontend) |
| **25** | **Outillage de publication** | rendre une publication assez bon marché pour que personne ne patche les données en place | à créer |

### 3.2 Domaine — contestations

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **29** | **Journal des déplacements** | enregistrer chaque déplacement de hash sous une cause typée (correction · extension · dérivation · corpus), en ajout seul, déclarant **par rôle** | décidé en [#21](https://github.com/left-eyebr0w/murphy/issues/21) ; **à raccrocher à la lignée corpus** |

---

## 4. Règles

Courtes, mais chacune doit atterrir quelque part. **Leur regroupement en un ou
plusieurs livrables n'est pas tranché** (voir *Décisions ouvertes*) — elles sont
donc listées une par ligne, comme responsabilités et non comme documents.

### 4.1 Domaine — contenu

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **9** | **Règle de confiance** | un mécanisme est admis à la gratuité du label ou ne l'est pas, sans état intermédiaire, et le test s'exerce à l'admission jamais par cas | décidée ([#2](https://github.com/left-eyebr0w/murphy/issues/2), [#15](https://github.com/left-eyebr0w/murphy/issues/15)), sans domicile |

### 4.2 Domaine — identité & versionnage

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **26** | **Plancher de composition** | fixer la condition d'accès au **nom promis** (contenu + monotonie), lue une fois avant déclaration | décidé en [#24](https://github.com/left-eyebr0w/murphy/issues/24), **sans domicile déclaré** |
| **30** | **Immuabilité d'un point nommé** | interdire la réécriture d'un point de lignée déjà nommé, quel que soit le nombre de points créés | à écrire |
| **31** | **Traduction `0.y.z`** | énoncer une fois qu'en majeur 0, ce qui « force un majeur » force un **mineur** | à écrire |
| **32** | **Contenu obligatoire de la note de version** | exiger que la note dise en toutes lettres qu'un déplacement d'épingle **annule les chiffres publiés** | à écrire |
| **33** | **Non-prétention beta** | déclarer qu'aucun chiffre produit en beta n'est comparable à quoi que ce soit | à écrire |
| **34** | **Cadence du train** | chiffrer l'obsolescence maximale du droit servi et la tenir comme un engagement | à écrire — ⚠️ le chiffre lui-même n'est pas décidé |
| **35** | **Compteur public = majeur** | interdire le découplage du compteur public et du majeur | à écrire |

### 4.3 Domaine — contestations

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **28** | **Routage champ → hash** | dire quel champ modifié déplace quel hash — lu, jamais arbitré | à écrire ; **était compté deux fois** dans l'ancien sac (sous *ADR-032 réécrit* et comme ligne propre) |

---

## 5. Autre — ce qui ne se classe pas

| N° | Livrable | Ce que c'est | État |
|---|---|---|---|
| **4** | **Ancre de l'*inter*** | fixer le seuil chiffré propre à l'*inter*, avant la campagne et non pendant | à décider ([#19](https://github.com/left-eyebr0w/murphy/issues/19)) — le +0,49 du Legal Track 2006 est nativement *inter*, employé jusqu'ici comme borne conservatrice pour de l'*intra* |
| **10** | **Marqueur des opérations sans producteur** | déclarer que `jurisprudence_applicable` ([#10](https://github.com/left-eyebr0w/murphy/issues/10)) et `fondement_textuel` ([#16](https://github.com/left-eyebr0w/murphy/issues/16) §5) n'ont pas de producteur | à poser |
| **11** | **Cimetière des métriques** | consigner les métriques écartées et le motif de chaque abandon | à écrire |
| **12** | **Pièges de construction P-01–P-04** | consigner les pièges identifiés à la construction du jeu | à écrire |
| **36** | **Calcul de la mesure** | router la métrique par branche et produire les chiffres que 17 publie | ⚠️ **jamais listé** — le domaine *mesure* n'a aucun organe dans ce sac |

**Pourquoi ces cinq-là ne se classent pas :**

- **4** — un **nombre calibré**, pas une règle de conduite ni un document. Sa
  frontière avec **6** n'est pas tranchée : le pilote produit un seuil
  d'auto-cohérence, celui-ci n'a pas de pilote qui le produise.
- **10** — une **annotation sur un existant**, pas la production d'un neuf. Rien
  n'est livré ; quelque chose est marqué.
- **11** et **12** — de nature **trace**, pas instrument : personne ne les ouvre
  pour travailler. C'est exactement ce qu'un ADR fait, et les ADR sont hors sac.
  Les garder ici serait réintroduire par la fenêtre ce qu'on sort par la porte.
- **36** — indécidable tant que le périmètre du sac vis-à-vis de `eval/` n'est pas
  tranché : livrable manquant, ou hors périmètre parce que le harnais le porte
  déjà ?

---

## Décisions ouvertes

Ce ne sont pas des livrables, mais elles conditionnent le tri.

1. **Regroupement des règles.** 9, 26, 28 et 30–35 : un livrable unique qui les
   porte toutes, une dispersion dans les documents du §1, ou un livrable par
   domaine ? Dispersées, elles redeviennent introuvables — ce qui est le problème
   qu'elles ont déjà.
2. **Périmètre du sac vis-à-vis d'`eval/`** — décide du sort de **36**.
3. **1 et 2 : un document ou deux ?** Deux responsabilités distinctes (grader /
   rédiger), un seul lecteur, un seul moment d'usage.
4. **Périmètre exact du lockstep** — quels dépôts bougent ensemble ? (`backend`,
   `frontend`, `data`, `eval`) Le verrou n'a de sens que sur ce qui se livre
   **et** se consomme ensemble.
5. **Deux lignées ou trois ?** La collection (`cas` + `qrels`) monte-t-elle dans
   le lockstep produit, ou porte-t-elle sa propre lignée comme le corpus ?
6. **La cadence** — le chiffre de la règle **34**.
