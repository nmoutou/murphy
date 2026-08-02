# ADR-035 — Le paradigme d'évaluation s'aligne sur le TREC Legal Track

**Statut** : Acté (2 août 2026, session de la carte
[#1](https://github.com/left-eyebr0w/murphy/issues/1))

## Contexte

Le programme a construit son appareil d'évaluation **seul** : ADR-005 (échelle de
pertinence), ADR-007 (métriques), ADR-008 (formats qrels/runs), ADR-010 (deux modes
d'annotation), ADR-017 (strates), ADR-032 (versionnement), puis la refonte en cours du
golden-set. Aucune de ces décisions n'a été prise **contre** une méthodologie établie —
elles ont été prises **sans**.

Or il en existe une, éprouvée sur six campagnes (2006–2011) dans un régime dont la
priorité est renversée **exactement comme celle de Murphy** : le **TREC Legal Track**
évaluait la recherche documentaire pour l'*e-discovery*, où produire **tous** les
documents pertinents prime sur la précision — un pertinent manqué a un coût juridique,
un non-pertinent de trop non. C'est l'invariant d'exhaustivité de Murphy. La plupart des
autres tracks TREC optimisent la précision en tête de liste et **ne transfèrent pas**.

Le rapprochement révèle deux choses.

**Le programme faisait déjà du TREC sans le nommer.** ADR-008 projette déjà vers les
qrels/runs TREC plats pour `trec_eval` ; ADR-010 prévoit déjà la campagne poolée avec
calibration inter-experts ; `RISQUES.md` R-05 énonce déjà que « le set v1 sert la
baseline, **pas la vérité** ; remplacé par les qrels expertes en alpha ph.2 » ; et
`VERSIONS.md` place déjà la collection achetée par assesseur en **alpha phase 2**, sous
le nom de **golden-set v2**.

**Mais un manque est structurel.** ADR-029 ayant retiré les qrels citation-minées, Murphy
n'a **aucune** réponse à la diversité du pool : le biais de pool est **non mesurable en
solo mono-système, par construction** (dossier
[`recherche/incompletude-qrels.md`](../recherche/incompletude-qrels.md), ticket
[#7](https://github.com/left-eyebr0w/murphy/issues/7)). Cette réponse est la **pluralité
des participants** — et elle n'est pas un accessoire du projet, elle est sa vocation.

## Décision

### 1. Le modèle de référence est le **Legal Track**, pas TREC générique

Motif : le primat du rappel. Les traits transférables sont ceux calibrés sous ce primat.

### 2. Deux machines, disjointes et ordonnées

- **Machine A — production d'une collection de test réutilisable** : le triplet *corpus
  figé + topics + qrels*. Menable **en solo**. C'est, mot pour mot, la raison d'être de
  **P2**.
- **Machine B — campagne communautaire** : plusieurs équipes indépendantes soumettent des
  *runs* concurrents, poolés et jugés. **Structurellement plurielle.**

**B ⊃ A** : aucune campagne sans collection préalable. **A d'abord, B après.**

Rattachement : **A est dans P2** ; **B est post-publication**, sa couche institutionnelle
relevant du **chantier 8** (`INSTITUTIONNEL.md`).

> ⚠️ **Point ouvert, non tranché ici.** `VERSIONS.md` s'arrête à *publication* et **ne
> contient aucun jalon où la machine B puisse se poser**. Son ouverture exigera un
> amendement de `VERSIONS.md` — qui est figé et ne change que par ADR (ADR-012). À
> instruire le moment venu, pas maintenant.

### 3. Présomption **symétrique**

Quand une décision de conception de l'appareil d'évaluation hésite et qu'aucun argument
local ne tranche, **la forme du Legal Track détient le défaut**. On ne réinvente pas
contre eux par ignorance.

La présomption est **symétrique** — les deux mouvements sont chargés :

| Mouvement | Charge de l'argument |
|---|---|
| **S'écarter** de TREC | énoncer la raison dans la résolution |
| **Emprunter** à TREC | **nommer le régime dans lequel le trait a été calibré**, et dire pourquoi il transfère |

Motif de la symétrie : le régime du Legal Track diffère du nôtre sur **quatre**
dimensions et n'en partage qu'**une** — celle-là même qui a fait le choisir.

| | Legal Track | Murphy au 2 août 2026 |
|---|---|---|
| Corpus | ~7 M documents OCR (IIT CDIP) | corpus DILA |
| Participants | 6 à 30+ équipes | **un** |
| Assesseurs | réviseurs juridiques professionnellement formés | **zéro** |
| Budget d'assessment | NIST | néant |
| **Primat du rappel** | ✅ | ✅ |

Une présomption **asymétrique** — départ coûteux, emprunt gratuit — serait à l'envers :
le départ est visible, c'est l'**emprunt qui fait les dégâts en silence**. Elle
contredirait de surcroît la règle d'enregistrement de la carte #1, instituée le 2 août
après que six résolutions ont chacune transporté un chiffre juste **en laissant tomber sa
condition d'emploi**.

### 4. L'appareil de réception se construit **avant** ; la machinerie d'évaluation se promeut **après panne**

Le Legal Track **n'a pas démarré mûr** : 2006, *une* tâche, 6 équipes, pooling
partiellement évalué. La machinerie s'est ajoutée **par constat de ce qui cassait** —
échantillonnage profond après la panne du pooling à profondeur fixe, adjudication,
autorités de topic, évaluation non-résiduelle en 2009. Les organisateurs qualifiaient
eux-mêmes leur bilan de « travail en cours ».

Mais l'**infrastructure de réception** existait **dès l'année 1** : corpus figé, format de
topic, format de run, outil d'évaluation. Les équipes ne l'ont pas conçue — elles sont
arrivées dans un appareil déjà debout.

D'où deux régimes distincts, à ne jamais confondre :

| | Régime |
|---|---|
| **Appareil de réception** — formats, contrat de topic, format de run, qrels, guide d'annotation, protocole de pooling, outil d'évaluation | **Construit avant**, complet. On ne recrute personne dans le vide. |
| **Machinerie d'évaluation** — tâches multiples, échantillonnage profond, adjudication, autorités de topic, estimation | **Promue après panne observée**, jamais par anticipation. |

C'est ADR-012 (constat sur preuves, pas pré-décision) appliqué au **processus
d'évaluation lui-même**, et la réponse opérationnelle au risque **R-08** (sur-outillage
du pilotage).

### 5. La vérité s'achète par **assesseur** ; les labels gratuits sont un **incrément**, pas un paradigme concurrent

Le golden-set v1 tire ses labels de faits extérieurs à l'opinion — identité canonique,
graphe `G₀`, frontière du corpus. C'est un **avantage que TREC n'a pas**, et il est
conservé.

Mais il **ne remplace pas** l'assessment : il en est le **premier incrément**, dans un
régime où les assesseurs n'existent pas encore. La trajectoire est celle que R-05
énonçait déjà : **v1 sert la baseline, v2 sert la vérité** (alpha ph.2 — expert, poolé,
calibré).

### 6. Critère « **rien à jeter** »

Toute spécification produite sous ce paradigme doit survivre au passage au golden-set v2,
puis à l'ouverture aux runs externes, **sans redesign**. C'est un critère d'acceptation
opposable, pas une intention.

Conséquence immédiate : les décisions qui ont traité la **rareté du jugement comme une
condition permanente** — alors qu'elle n'est que la condition **actuelle** — sont
**rouvertes**.

## Alternatives rejetées

- **Fusionner v1 et v2** (le golden-set v1 devient lui-même la collection achetée par
  assesseur). Rend la sortie de v0 **otage du recrutement** d'un corps d'assesseurs
  inexistant, et arrête le chemin critique `B-05 ✅ → B-08 → B-11 → B-12`. Contredit
  frontalement le §4 : monter l'appareil d'assessment complet avant d'avoir un seul
  assesseur est exactement le pré-outillage que la rétrospective du Legal Track
  déconseille.
- **Refondre la carte #1** en carte « collection + campagne ». Rejoue neuf résolutions
  dont la plupart survivent, et planifie la machine B au **maximum de brouillard**, avant
  d'avoir livré A.
- **TREC générique** comme modèle. Optimise la précision en tête de liste ; ne transfère
  pas sous primat du rappel.
- **Règle contraignante** (« suivre TREC sauf à prouver qu'ils ont tort »). Lierait le
  programme à des positions que leurs propres auteurs qualifiaient de provisoires, pour un
  track qui **ne tourne plus depuis 2012**.
- **Emprunt gratuit** (présomption asymétrique). Voir §3.

## Conséquences

- La **destination de la carte #1 est redessinée** : le golden-set v1 devient le *premier
  incrément d'une collection de test au sens TREC*, et la frontière de la carte s'étend au
  **protocole de pooling et d'assessment** — la machine A complète.
- **Le contenu du golden-set n'atterrit plus en ADR-035 mais en ADR-036**, à la clôture de
  la carte #1. Toutes les mentions antérieures d'« ADR-035 » comme ADR *de contenu* se
  lisent désormais **ADR-036** (corrigées dans `EXIGENCES_v0.md`, `BACKLOG.md`,
  `GOLDEN-SET.md`, `ADR-033`, `INDEX.md`, `WIP/B-08-cadrage.md`). Motif de la
  renumérotation : ce sont **deux objets** — le présent ADR est un ADR *de méthode*,
  stable par construction, qui **arbitre** les tickets ; ADR-036 sera un ADR *de contenu*,
  qui bouge à chaque ticket résolu. La stratégie « un seul ADR à la fermeture de la
  carte » visait le second, pas le premier.
- Ouvre **R-09** : la trajectoire suppose désormais des assesseurs et des financements
  publics **qui n'existent pas**. R-01 (bus factor solo) ne couvre pas ce risque.
- **ADR-008 est conforté** : ses projections déterministes vers les qrels/runs TREC plats
  cessent d'être une commodité d'outillage et deviennent la **condition de recevabilité**
  des runs externes.
- **ADR-010 est conforté** : la campagne poolée avec calibration inter-experts *est* la
  machine A en mode expert.
- **ADR-029 n'est pas rouvert.** Les qrels citation-minées restent abandonnées. Il en
  résulte seulement que la **pluralité externe est la seule réponse restante** à la
  diversité du pool.
- **ADR-007 reste ouvert** par le ticket
  [#14](https://github.com/left-eyebr0w/murphy/issues/14), qui reçoit un **troisième
  terme** : `F1@K` avec **K déclaré par le système**, par topic (Legal Track, tâche batch
  2009) — ni coupe constante, ni coupe à `R`.

## Références

ADR-005 · ADR-007 · ADR-008 · ADR-010 · ADR-012 · ADR-017 · ADR-028 · ADR-029 · ADR-032 ·
ADR-034 · `VERSIONS.md` (alpha ph.2) · `RISQUES.md` R-05, R-08 · dossier
[`recherche/trec-legal-track.md`](../recherche/trec-legal-track.md) · carte
[Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1)
