# Spécimens d'enregistrement de cas — prototype de la forme (issue #12)

> ⚠️ **Jetable, et non versable au jeu.** Ces enregistrements sont des **spécimens de
> forme**, écrits pour qu'on réagisse à l'objet plutôt qu'à sa description
> ([#12](https://github.com/left-eyebr0w/murphy/issues/12), méthode `/prototype`). Ils
> ne sont **pas** des cas du golden-set : la carte
> [#1](https://github.com/left-eyebr0w/murphy/issues/1) s'arrête avant la première
> question, et rien ici n'entre en v1. Les textes sont volontairement quelconques ; c'est
> la **structure** qu'on regarde.
>
> ⚠️ **Les identifiants sont des spécimens non vérifiés** contre le corpus ingéré. Leur
> *forme* est réelle (`eli:LEGIARTI…`, `decision:JURITEXT…` — ADR-018, payload Qdrant
> `identifier`) ; leurs chiffres ne le sont pas.

Quatre mécanismes couvrant les **trois sources de gratuité du label**
([#2](https://github.com/left-eyebr0w/murphy/issues/2),
[#15](https://github.com/left-eyebr0w/murphy/issues/15)) plus le **seul mécanisme jugé** de
la v1 ([#9](https://github.com/left-eyebr0w/murphy/issues/9)). Plus un cinquième
enregistrement qui n'est pas un cas : une **variante**.

---

## S1 — `known_item_identifiant` · source `identite`

```json
{
  "case_id": "gs1-0001",
  "texte": "Je voudrais le texte de l'article 1240 du code civil.",
  "mecanisme": "known_item_identifiant",
  "germe": ["eli:LEGIARTI000006438819"],
  "leurre": [],
  "date_pivot": "2026-07-31",
  "variante_de": null,
  "narrative": null,
  "origin": "porteur",
  "pending": false
}
```

Label dérivé de l'**identité**. Le germe est le point de départ de la dérivation — et ici il
*est* la cible : c'est l'exception connue, l'utilisateur tient déjà l'identité de ce qu'il
cherche. `R = 1`.

---

## S2 — `absence_attendue` · source périmètre DILA

```json
{
  "case_id": "gs1-0002",
  "texte": "Un employeur belge peut-il rompre un contrat pendant la période d'essai sans motif ?",
  "mecanisme": "absence_attendue",
  "germe": [],
  "leurre": ["eli:LEGIARTI000006901147"],
  "date_pivot": "2026-07-31",
  "variante_de": null,
  "narrative": null,
  "origin": "porteur",
  "pending": false
}
```

`R = 0`, dérivé de la **définition du périmètre DILA** — externe, et que nos vagues
d'ingestion ne déplacent pas (#15). **Aucun germe** : rien n'est amorcé, la vacuité se déduit
du périmètre. Le `leurre` est l'article français voisin, qui atteste la **sixième contrainte
de rédaction** (#15) et porte le pouvoir discriminant du cas : sans voisin lexical, n'importe
quel système réussit trivialement.

---

## S3 — `traversee_simple` · source `graphe_g0`

```json
{
  "case_id": "gs1-0003",
  "texte": "J'ai lu l'article L. 1234-9 du code du travail ; quels textes faut-il lire avec lui ?",
  "mecanisme": "traversee_simple",
  "germe": ["eli:LEGIARTI000006901122"],
  "leurre": [],
  "date_pivot": "2026-07-31",
  "variante_de": null,
  "narrative": null,
  "origin": "porteur",
  "pending": false
}
```

Qrels **re-dérivées, jamais recopiées** (§5.1) : tous les voisins du germe à distance 1 par
`cites` dans `G₀`. Précondition mécanique vérifiée à l'admission : *toutes* les cibles à
distance 1 (#16). `R` = compte dérivé, jamais asserté (#3).

---

## S4 — `concept_vers_instance` · **jugé**

```json
{
  "case_id": "gs1-0004",
  "texte": "Mon propriétaire ne m'a pas rendu ma caution deux mois après mon départ, que puis-je faire ?",
  "mecanisme": "concept_vers_instance",
  "germe": [],
  "leurre": [],
  "date_pivot": "2026-07-31",
  "variante_de": null,
  "narrative": "Est pertinent tout document énonçant le délai de restitution du dépôt de garantie, la sanction de son dépassement, ou la procédure de recouvrement ouverte au locataire. Un document traitant du dépôt de garantie sans aborder ni délai ni sanction est citable mais non décisif. Le contentieux de l'état des lieux est hors sujet sauf s'il conditionne la restitution.",
  "origin": "porteur",
  "pending": false
}
```

Label **jugé** — cascade q1→q3, grades 0–3 (ADR-005), projetés `g/3` dans RBP (#14).
**Germe vide, et c'est l'attestation du typage** (voir §1). Seul enregistrement des quatre où
un assesseur existe, donc le seul où `narrative` a un consommateur.

---

## S5 — une **variante**, qui n'est pas un cas

```json
{
  "case_id": "gs1-0004-v1",
  "texte": "Quel est le délai de restitution du dépôt de garantie et quelle sanction s'attache à son dépassement ?",
  "mecanisme": "concept_vers_instance",
  "germe": [],
  "leurre": [],
  "date_pivot": "2026-07-31",
  "variante_de": "gs1-0004",
  "narrative": null,
  "origin": "porteur",
  "pending": false
}
```

Décalage de registre **citoyen → praticien** (#11), pas une reformulation lexicale.
**Partage les qrels de S4**, compte dans `N_q`, **jamais dans le plancher de 30**.

---

# Ce que l'objet a tranché

## 1. `germe` n'est exigé que là où le label est gratuit

**La règle « germe à 100 % » (#10) était énoncée quand le jeu était censé être entièrement
gratuit.** `#9` a fait entrer un mécanisme jugé en v1 et personne n'est revenu dessus. Le
prototype le rend visible : en écrivant S4, **il n'y a aucun document sous les yeux** — c'est
la définition même de « besoin d'abord », et c'est ce qui achète le réalisme du mécanisme.

Le germe a deux consommateurs dans les documents, et un seul survit à l'examen :

- *rejouer le label* (GOLDEN-SET §5.2) — **sans objet sur un cas jugé** : un label jugé est
  **consigné**, pas dérivé, il n'a rien à ré-amorcer ;
- *prouver le typage* (#16) — assuré autrement, voir ci-dessous.

**Règle retenue** — le germe est exigé à 100 % des cas dont le **label est gratuit**, et n'a
pas d'objet sur les cas jugés. Son taux de remplissage est **dérivable de `mecanisme`** : ce
n'est pas un null d'authoring, c'est une propriété structurelle.

**Issue morte, et elle l'est indépendamment des préférences** : remplir le germe *après coup*,
au jugement. Il deviendrait du rang 3 (banni par §5.1) — mais surtout, s'il entre dans le hash
`cas`, **juger un cas déplacerait son hash**, et les runs déjà produits cesseraient d'être
comparables sans qu'aucune question ait bougé.

## 2. Sur un cas jugé, l'absence de germe *est* la preuve du typage

La propriété distinctive de `concept_vers_instance` est que la requête énonce une
**situation** : elle ne désigne ni une cible, ni un texte de départ. Ça se vérifie en lisant
la question, **a priori et sans run** — exactement la forme de vérifiabilité qu'exige
l'interdit de circularité de `#10`. Le champ vide n'est pas une négligence, c'est
l'attestation.

*Limite connue, à emporter* : la lecture tient tant que `concept_vers_instance` est le **seul**
mécanisme rédigé besoin d'abord. `desambiguisation` l'est aussi et il est hors v1 (#9).

✅ **Levée le 8 août 2026** ([#24](https://github.com/left-eyebr0w/murphy/issues/24)) — la limite
ne peut plus mordre. #24 a instruit puis **écarté** l'entrée de `desambiguisation` en
substitution : remplacer le composant jugé **change l'objet en gardant le nom**, donc franchit le
plancher de composition au lieu de l'éviter. Il n'existe **aucun repli**, et la v1 garde donc
`concept_vers_instance` comme **unique** mécanisme besoin-d'abord aussi longtemps qu'elle porte
son nom. *Corollaire utile pour ce document* : l'absence de germe reste une preuve de typage
valable sur toute la v1 — si un second mécanisme besoin-d'abord entrait un jour, ce serait par un
**changement de nom**, donc sur une collection dont ce spécimen ne parle plus.

## 3. `germe` et `leurre` sont deux champs, pas un

Sur les trois cas gratuits, le germe ne fait pas le même travail :

| Spécimen | Ce qui est détenu | Fonction |
|---|---|---|
| **S1** | l'article visé | **amorce** — la dérivation part de là |
| **S3** | l'article lu | **amorce** — la dérivation part de là |
| **S2** | l'article français voisin | **leurre** — il ne dérive rien ; il atteste la contrainte de #15 et porte le pouvoir discriminant |

Sur S2, la réponse est *« il n'y en a pas »* et elle se déduit du **périmètre**, jamais du
document noté. Les fondre en un seul champ ferait *slice*-er sur deux populations mélangées,
alors que `#5` §8 a durci la règle : **le rapport ventile sur tout champ admis**. Deux champs,
chacun avec son taux de remplissage dérivable de `mecanisme`.

## 4. La projection vers `Topic` se paie zéro

```
enregistrement d'authoring                    →   Topic (eval/, inchangé)
{case_id, texte, mecanisme, germe, leurre,        Topic(query_id=case_id,
 date_pivot, variante_de, narrative,                    text=texte)
 origin, pending}
```

Rien de ce que le runtime consomme n'est absent, rien de ce que l'authoring porte n'a à
descendre. La séparation en deux objets ne coûte qu'une fonction de projection — même patron
qu'ADR-008 vers le TREC plat.

## 5. Deux champs entérinés par le négatif

- **`sens_derivation`** — écarté en chemin par `#10` (propriété du *mécanisme*, donc
  dérivable ; une obligation déclarative par cas serait une dette de vocabulaire au sens de
  `#3`). Aucun des cinq spécimens n'en a eu besoin : **confirmé par l'usage**.
- **`domaine juridique`** — dernier point en attente d'ADR-034 §Conséquences. C'est
  **`matiere` sous son nom d'ADR-033** : ADR-033 écrit *« Le droit non codifié → domaine
  `null` »*, GOLDEN-SET §5.3 écrit la même phrase avec *matière*. `matiere` est tombée avec
  les strates, confirmée morte par `#10`. **Se ferme par identification, pas par arbitrage.**

---

## 6. ⚠️ `narrative` appartient au hash `qrels` — amendement à #18 §0

Le partage de `#18` §0 est fondé sur le **coût de déplacement** : `cas` coûte une
re-récupération, `qrels` une re-notation gratuite. Or **un run ne consomme jamais
`narrative`** — il ne consomme que `texte`, via la projection `Topic`. Réécrire une narrative
ne change aucun run : ça change ce que l'assesseur aurait dû juger, donc ça coûte exactement
une re-notation.

La mettre dans `cas` ferait **casser la comparabilité de runs que rien n'a touchés** —
précisément ce que la décomposition en trois hashes existe pour éviter. Le champ **vit** dans
l'enregistrement d'authoring mais **appartient** au hash `qrels` : *le hash suit le coût, pas
le fichier*.

## 7. Trois calls mineurs

- **`case_id`** — `gs1-NNNN`, opaque et séquentiel, variantes suffixées `-vN`. Écarté :
  encoder le mécanisme dans l'identité (`S1-KII-001`), commode à lire mais **deux renommages
  de mécanismes sont en cours** — tous les ids casseraient.
- **`origin` est conservé**, malgré une variance nulle en v1 (tout est `porteur`). Motif :
  il est **impossible à reconstituer une fois les origines mélangées**, et il sert une
  question qu'on se posera — *les questions écrites par des experts se comportent-elles
  autrement que les générées ?* Son vocabulaire reste à fixer par
  [#13](https://github.com/left-eyebr0w/murphy/issues/13). *⚠️ Fixé le 7 août par #13 §6, et
  **le champ se dédouble** : `origin` (auteur du **texte** — `porteur` | `expert` | `llm`,
  uniformément `porteur` en v1) et **`origine_notion`** (ce qui a **suggéré** le cas —
  `porteur` | `llm`, rempli sur `concept_vers_instance` seul). Le motif de la dérogation
  ci-dessus est **re-fondé** : la v1 étant uniforme, `origin` est reconstituable depuis la
  version, et son dernier appui est qu'une correction puisse réécrire le texte d'un cas —
  ~~question ouverte de [#21](https://github.com/left-eyebr0w/murphy/issues/21)~~ **tranchée
  le 8 août : l'appui tombe, mais pas par l'immuabilité du texte** (une réécriture sans
  changement de sujet garde son id et déplace le hash `cas`) — **l'intake ne transporte
  jamais de texte**, l'unité étant une contestation et les corrections étant dérivées en
  interne, donc `origin` reste à variance nulle **sous toutes les ères** et la dérogation est
  à reprendre à l'écriture d'ADR-036.*
- **Date pivot** — la proposition du §7 de `B-08-generation-requetes.md` *(fichier supprimé le
  7 août par [#13](https://github.com/left-eyebr0w/murphy/issues/13) ; sa résolution en tient
  lieu)* tient sur le fond
  (une date pour toute la v1, sauf les cas portant délibérément sur une succession
  temporelle), mais son ancrage — *« celle du gel »* — désigne un **mot mort** (#18). Elle est
  réénoncée sur une date **déclarée**.

## 8. Nommage des mécanismes

Les deux mécanismes de graphe sont **`traversee_simple`** et **`traversee_chainee`** —
la proposition de `#16`, entérinée. `chainee` dénote l'enchaînement, donc la profondeur, sans
nommer d'arête : la contrainte de `#16` §2 est tenue.

Le mécanisme d'absence devient **`absence_attendue`**, et **la proposition de `#15`
(`absence_hors_perimetre`) est écartée** — pour une raison que le prototype a fait apparaître
et que `#15` ne pouvait pas voir, faute d'avoir écrit les autres noms côte à côte.

**Aucun des six autres mécanismes n'encode sa source de gratuité.** `known_item_identifiant`
ne dit pas `identite`, `traversee_simple` ne dit pas `graphe_g0`. Et c'est régulier : `#2` a
fait de la source de gratuité une **propriété indépendante** du mécanisme, enregistrée à part
— pas un morceau du nom. `absence_hors_perimetre` serait donc le **seul** nom à porter sa
source, et il serait fragile pour la raison même qui a tué `frontiere_corpus` : *un nom qui
grave sa source doit être réécrit le jour où la source bouge.* Un nom qui n'en dit rien ne
peut pas dénoter la mauvaise. La contrainte de `#15` est ainsi tenue **par son motif plutôt
que par sa lettre** — elle exigeait que le nom ne dénote pas l'état d'ingestion ;
`absence_attendue` ne dénote aucune source du tout.

**Le qualificatif `attendue` n'est pas cosmétique.** Il porte la distinction que `#15` a
achetée et qui se perd sur un `absence` nu :

| Situation | Nom | Verdict |
|---|---|---|
| **dans** DILA, non ingéré | `pending` | **non scoré** — désigne un manque du corpus |
| **hors** périmètre DILA | `absence_attendue` | **scoré**, `R = 0` — teste le *fail-fast* |

*« Même observation aujourd'hui, verdicts opposés »* (#15). La confusion des deux s'est
produite **en séance, sur ce ticket même** — preuve empirique que le nom nu ne suffit pas.
`attendue` dit qu'il s'agit d'une absence **normale**, par opposition à une absence *à
combler* : exactement l'axe sur lequel `pending` s'oppose, et régulier avec les six autres
noms, qui décrivent tous ce qu'on attend du système.

⚠️ **Ce que l'identification `absence = pending` aurait coûté**, et pourquoi elle n'était pas
tranchable ici : le mécanisme serait sorti du périmètre scoré — composition v1 de **5 à 4**,
`N_cas` de **150 à 120**, disparition du **seul contrôle du fail-fast**. C'est mot pour mot le
second déclencheur de [#24](https://github.com/left-eyebr0w/murphy/issues/24). Une composition
ne se change pas depuis un ticket de **forme**.

✅ **Tranché le 8 août 2026 par #24 — l'identification est refusée**, et le renvoi est honoré.
Trois motifs, dont deux que ce document ne pouvait pas produire : **(1)** identifier maintenant,
c'est **décider la panne avant de l'observer**, alors qu'ADR-035 pose *machinerie après panne
observée, jamais par anticipation* — et #15 a montré que le cas hors périmètre lexicalement
voisin est le cas **dur** ; **(2)** la surveillance du *fail-fast* **ne survit pas au transfert**,
parce que `pending` s'indexe sur un **état** et que sa population **s'évapore** avec la résorption
du corpus (#11 §7) — pire, toute ingestion déplace le hash `corpus`, donc deux configurations
mesurées à deux moments ne seraient **pas comparables** : la sentinelle serait structurellement
incomparable, pas seulement transitoire ; **(3)** c'est la faute *état vs définition* que #15
vient de réparer en retirant `frontiere_corpus`, et que **le nom choisi ici encode déjà** —
`attendue` porte la charge de la séparation *`pending` non scoré ↔ hors périmètre scoré*.

*Coût du refus : nul.* Le second déclencheur reste vivant, #20 §5 l'a déjà rendu propre, et sous
la **condition de monotonie** de #24 il produit un **retrait** — donc un sous-ensemble, donc **le
nom se garde**. **#15, #4 et #14 n'ont pas à être rouverts ensemble.**
