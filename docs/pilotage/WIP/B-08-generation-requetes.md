# B-08 — Génération des requêtes : protocole et prompts (résolution de D-01)

> ## ⚠️ EN SURSIS (1er août 2026) — ne pas relancer la récolte
>
> Le protocole en deux phases du §5 est structuré par `intention × registre` et
> présuppose le cadre d'échantillonnage tombé avec les strates ; les **72
> questions** déjà produites sont **rebutées**, pas re-taguées. Le sort de ce
> document est le ticket
> [Le sort du protocole de génération des requêtes](https://github.com/left-eyebr0w/murphy/issues/13)
> de la carte [#1](https://github.com/left-eyebr0w/murphy/issues/1).
>
> **Ce qui survit vraisemblablement** : la frontière E-T-01 (§2), l'hygiène de
> prompt (§3), le schéma de provenance (§7) et le critère de sélection (§6) —
> tous indépendants de la grille. **Ce qui ne survit pas** : la structuration
> par `intention × registre` et les quotas qui en descendent.

> Document de travail (`WIP/`), **éphémère par conception** — compagnon de
> [B-08-cadrage.md](B-08-cadrage.md), dont il tranche la décision ouverte
> **D-01**. Il vit le temps de la récolte et disparaît quand
> `questions_brutes.jsonl` est scellé.
>
> Écrit **pour le porteur**, à lire à côté de la session LLM. Ce qui doit
> survivre part ailleurs : la frontière E-T-01 (§2) en **ADR**, le schéma de
> provenance (§7) dans le modèle de requête d'`eval/`, le critère de
> sélection (§6) dans le guide d'annotation.

## 1. Ce qu'on cherche exactement

**Les ~155 textes de questions du §7.3 de [GOLDEN-SET.md](../../product/GOLDEN-SET.md),
et rien d'autre.** Pas de jugements, pas de cibles, pas de qrels — la couche
*questions* seule (ADR-030 : texte, `intention`, `matière`, `registre`, date
pivot).

Le LLM ne produit pas le jeu. Il produit des **candidats de texte**, dont le
porteur retient un sur N. C'est la frontière d'ADR-028 — *la machine produit un
candidat, l'humain tranche* — appliquée à la rédaction au lieu de la lecture,
exactement comme le §7 de [B-08-prior-ponderation.md](B-08-prior-ponderation.md)
l'applique à la lecture documentaire.

## 2. La frontière E-T-01, écrite

E-T-01 interdit toute dépendance du **harnais** à un LLM générateur. Le cadrage
notait que l'emploi hors ligne n'est pas exclu « mais que la frontière doit être
écrite ». La voici, en trois lignes qui suffisent à trancher n'importe quel cas :

| | |
|---|---|
| **Autorisé** | Un LLM, hors ligne, produit des textes candidats. Le porteur en retient un, qui entre dans la couche gelée et hashée. |
| **Interdit** | `eval/` appelle un LLM. À n'importe quel moment, pour n'importe quoi — génération, notation, reformulation, jugement. |
| **Interdit** | Un texte non relu par le porteur entre dans le jeu. Il n'y a pas de lot « accepté en masse ». |

**Le test qui tranche** : *est-ce qu'un run devient irreproductible si le
fournisseur change de modèle demain ?* Ici, non — le texte est gelé, hashé,
versionné (ADR-032) ; le modèle qui l'a proposé est une note de provenance, au
même titre que le nom de l'annotateur sur un jugement (ADR-008). Le jour où le
modèle disparaît, le jeu est intact.

> C'est la même asymétrie qu'ADR-029 sur les citations : ce qui est interdit,
> ce n'est pas de *se servir* d'une source automatique, c'est de la laisser
> **fermer la boucle** de mesure.

## 3. Hygiène : ce que les prompts ne contiennent jamais

Aucun document. Aucun extrait de corpus. Aucune liste des bases ingérées.
Aucune volumétrie. Aucun poids D₁.

Les trois premiers interdits écartent P-01 par construction (on ne décalque pas
ce qu'on n'a pas). Les deux derniers écartent une contamination plus discrète :
un LLM à qui l'on annonce que le pénal pèse 52 % **équilibrera de lui-même**, et
l'on récupérera au niveau du texte une pondération qu'on a délibérément refusé
de graver dans l'échantillonnage (GOLDEN-SET.md §6.2). Les statistiques disent
*combien* de questions par case ; elles n'entrent jamais dans un prompt.

**Le seul matériau autorisé en entrée** est celui du §8.4 — les nomenclatures
divergentes de [analyse.md](analyse.md). Il décrit des *libellés
administratifs*, jamais des documents du corpus : le passer au LLM ne crée
aucun risque de décalque.

## 4. Le protocole en deux temps

La demande initiale — *générer N versions d'une même question, n'en garder
qu'une* — est le **temps 2**. Seule, elle ne protège que contre une mauvaise
formulation : la question elle-même, celle qui décide si la case a du sens,
aurait été choisie par le modèle en un coup. D'où un temps 1 symétrique.

| | Ce que le LLM produit | Ce que le porteur fait | Ce que ça protège |
|---|---|---|---|
| **Temps 1 — situation** | N situations **différentes** dans la case `matière × intention` | En retient 1 (ou 2) | Le choix de *quelle* question. Évite qu'un modèle impose son idée du contentieux type. |
| **Temps 2 — formulation** | N formulations de **la** question retenue | En retient 1 | Le choix de *comment* elle est dite. Sert directement le registre (§6.3). |

**Règle de fer, héritée du cadrage : jeter, jamais reformuler.** On sélectionne,
on ne rédige pas par-dessus. Une variante retouchée à la main est une variante
dont plus personne ne sait d'où elle vient — et le temps 2 existe précisément
pour rendre la retouche inutile : si aucune des 5 ne va, on relance, on ne
corrige pas.

**Le temps 2 est obligatoire sur le registre `citoyen`, facultatif sur
`praticien`.** Sur une question de praticien, la formulation est à peu près
déterminée par le vocabulaire du métier et le choix entre 5 variantes est
marginal. Sur une question citoyenne, **la formulation *est* l'objet mesuré**
(§6.3 : l'écart lexical est le premier facteur d'échec) — la choisir au hasard
reviendrait à tirer au sort la variable qu'on prétend étudier.

**Bénéfice comptable, et il n'est pas mince** : les variantes écartées au temps
2 sont du matériau isosémantique déjà écrit. Le §8.2 note que sur ces paires le
poste cher (les jugements) est partagé et que seule la rédaction est dupliquée —
or ici la rédaction est déjà payée. On archive les écartées (§7) ; les ~20
paires isosémantiques s'y puisent au lieu d'être commandées à part.

## 5. Les prompts

Un prompt par **intention**, pas par case : c'est l'intention qui change la
nature de ce qu'on demande, la matière et le registre ne sont que des créneaux.
Cinq prompts de temps 1, un de temps 2, quatre pour les sous-ensembles.

**Conditions d'exécution, non négociables :**

- **Une conversation neuve par case.** Jamais d'enchaînement. Un modèle qui voit
  ses réponses précédentes évite spontanément de se répéter et biaise la
  couverture — il vous donnera de la diversité inter-cases là où vous demandez
  de la diversité intra-case.
- **Un seul modèle pour toute la v1**, noté en provenance. Changer de modèle en
  cours de récolte introduit une variable dont personne ne saura quoi faire.

### 5.1 Temps 1 — le socle (exemple complet : `trouver_la_regle`)

Le prompt intégral une fois ; les autres intentions ne remplacent que le
cartouche `INTENTION` et leurs dérogations (§5.2).

```
Tu écris des questions de test pour un moteur de recherche juridique français.
Ces questions serviront à mesurer un moteur, pas à être répondues.

MATIÈRE : [S5 — Biens, baux, copropriété, immobilier, urbanisme]
INTENTION : trouver_la_regle — la personne veut savoir quelle norme régit sa
situation. Elle décrit un fait ou une position, elle ne demande ni la définition
d'un mot, ni une décision de justice, ni un document dont elle aurait la
référence.
REGISTRE : [citoyen] — aucune formation juridique. Emploie les mots de la vie
courante, ignore le vocabulaire technique, décrit son problème comme elle le
raconterait à un proche.

Produis 6 questions candidates. Chacune doit porter sur une SITUATION
DIFFÉRENTE relevant de cette matière — six situations, pas six façons de dire la
même chose. Fais-les différer par les faits : qui est concerné, à quel moment du
problème la personne se trouve, ce qui est en jeu pour elle.

CONTRAINTES
- Une seule question de droit par item. Aucune question à tiroirs.
- Aucune référence à un article, un code, une loi, un décret, une décision, une
  juridiction ou une date de texte — ni dans la question, ni en commentaire.
- Aucun chiffre présenté comme du droit : pas de délai, pas de montant, pas de
  seuil. La personne les ignore, c'est pour cela qu'elle cherche.
- Deux phrases au maximum. La question doit pouvoir être tapée telle quelle dans
  une barre de recherche.
- Pas de situation spectaculaire ni de cas d'école. Du contentieux ordinaire.

SORTIE : un tableau JSON de 6 objets
{"id": 1..6, "situation": "<les faits, une ligne>", "question": "<le texte tapé>"}
Aucun texte hors du JSON.
```

### 5.2 Temps 1 — les quatre autres cartouches

| Intention | Cartouche `INTENTION` | Dérogations |
|---|---|---|
| `verifier_une_solution` | *« La personne connaît la règle et veut savoir comment un juge a tranché un cas semblable au sien. Elle cherche une décision, pas un texte. »* | Ajouter : *« La question doit décrire un cas concret assez précis pour qu'une décision puisse ou non lui correspondre — mais sans nommer aucune juridiction ni aucune date. »* |
| `definir_un_terme` | *« La personne a rencontré un mot ou une expression et veut savoir ce qu'il signifie en droit. Elle ne décrit aucune situation personnelle. »* | Lever la contrainte « deux phrases » : ces questions sont naturellement brèves. Ajouter : *« Le terme doit être un mot que quelqu'un peut réellement rencontrer — sur un courrier, un contrat, une convocation, dans la presse. »* |
| `retrouver_un_document` | *« La personne dispose d'une référence et veut le document lui-même. »* | **Seule intention où la référence est autorisée — elle est l'objet même.** Ajouter : *« La référence doit être réelle et exacte en droit français. N'invente aucun numéro. Si tu n'es pas certain d'une référence, propose-en une autre dont tu es sûr. »* |
| `connaitre_une_procedure` | *« La personne sait ce qu'elle veut obtenir et cherche comment s'y prendre : devant qui, dans quel délai, sous quelle forme, avec quels justificatifs. »* | Ajouter : *« La question porte sur la marche à suivre dans la matière indiquée, pas sur le fond du droit de cette matière. »* |

> ⚠️ **`retrouver_un_document` est la case sensible** — P-01 la vise
> nommément. La ligne à tenir est exacte et tient en une phrase : la référence
> se vérifie **contre le droit français**, jamais contre le corpus de Murphy.
> Une référence réelle mais non ingérée donne une question `pending` (§10), ce
> qui est le régime normal et sans coût. Une référence choisie *parce qu'on
> sait qu'elle est ingérée* est un décalque, et elle rend la case ininterprétable.

> **Cas de S12.** La matière *Procédure et contentieux* et l'intention
> `connaitre_une_procedure` se recouvrent : dans S12 la procédure est le sujet,
> ailleurs elle est le moyen. C'est attendu, pas un défaut de la grille — les
> deux axes ne partitionnent pas les mêmes objets (§4). Si une case rend 6
> candidats manifestement forcés, **on en retient un seul et on note la case
> comme mince** : le §7.3 prévoit une vérification ex post, jamais un remplissage
> mécanique.

### 5.3 Temps 2 — les N formulations (le cœur de la demande)

```
Voici une question de test pour un moteur de recherche juridique français :

« [texte retenu au temps 1] »

Produis 5 reformulations de CETTE question, au registre [citoyen].
Même question de droit, mêmes faits, même attente. Seule la formulation change.

Les 5 versions doivent différer par la manière de dire, jamais par ce qui est
demandé : niveau de langue, longueur, ordre entre le fait et la demande, question
directe ou énoncé de situation, présence ou absence de détails non déterminants.

INTERDIT
- Ajouter, retirer ou modifier un fait qui changerait la réponse juridique
  attendue.
- Introduire une référence à un article, un code ou une décision.
- Poser une question différente, même voisine, même meilleure.
- « Améliorer » la question en la rendant plus précise juridiquement.

SORTIE : un tableau JSON de 5 objets
{"id": 1..5, "variante": "...", "ecart": "aucun" | "<l'écart, une ligne>"}
Le champ "ecart" vaut "aucun" seulement si la réponse juridique attendue est
strictement identique à celle de la question d'origine. Au moindre doute,
décris l'écart.
Aucun texte hors du JSON.
```

Le champ `ecart` est un **filtre de tri, pas une garantie** : toute variante qui
ne porte pas `"aucun"` se jette sans lecture, ce qui fait gagner du temps ; mais
un `"aucun"` ne dispense pas de relire, un modèle sous-déclarant volontiers sa
propre dérive.

### 5.4 Les sous-ensembles hors quota

**Négatives (§8.1) — ~20.** Le modèle ignore le périmètre exact de DILA : il
faut le lui donner, sans quoi il produira des questions qu'il *croit* hors
périmètre.

```
Périmètre couvert par le moteur : [droit français national — codes et textes
consolidés (LEGI), jurisprudence judiciaire, administrative et
constitutionnelle françaises]. Hors périmètre : [droit étranger, droit de
l'Union non transposé, doctrine, contrats types, jurisprudence non publiée].

Produis 6 questions qu'un utilisateur français poserait naturellement à ce
moteur et dont la bonne réponse est « aucun document pertinent » — parce que ce
qu'elles demandent est hors du périmètre ci-dessus.

Elles doivent paraître parfaitement légitimes : le piège est qu'elles ressemblent
à des questions dans le périmètre. Pas d'absurdité, pas de hors-sujet manifeste.
Pour chacune, indique en une ligne pourquoi elle tombe hors du périmètre.

SORTIE : JSON, {"id", "question", "motif_hors_perimetre"}. Rien d'autre.
```

**Strate-frontière (§8.3) — ~15.** Une exécution par paire de strates
mitoyenne ; le §8.3 vise le résidu de 6,32 % (« autres » civils, référés,
« autres contentieux » administratifs).

```
Produis 5 questions qui relèvent à la fois de [S6 — Travail et protection
sociale] et de [S3 — Personnes, famille, état civil], sans qu'on puisse trancher
laquelle prédomine. Le chevauchement doit venir des FAITS, pas d'une formulation
volontairement vague : une personne réelle, dont le problème relève des deux à
la fois. Registre : [citoyen]. Mêmes contraintes que précédemment (aucune
référence, deux phrases, un seul objet).
```

**Polysémie (§8.4) — flag, pas quota.** Seul prompt qui reçoit un matériau
externe : les référents concurrents établis dans [analyse.md](analyse.md).

```
En droit français, l'expression « contentieux social » a trois référents
incompatibles selon la nomenclature employée :
- l'aide sociale et le RSA devant le tribunal administratif ;
- les relations du travail dans la nomenclature civile ;
- la sécurité sociale, sous le « pôle social » du tribunal judiciaire.

Produis 4 questions qui emploient cette expression NATURELLEMENT — comme le
ferait quelqu'un qui n'a pas conscience de l'ambiguïté — et dont chacune vise en
réalité un référent différent. Indique pour chacune le référent visé.
N'explique pas l'ambiguïté dans la question : elle doit être invisible pour
celui qui la pose.

SORTIE : JSON, {"id", "question", "referent_vise", "registre"}.
```

À rejouer sur les trois autres pièges du §8.4 (stupéfiants, atteinte à
l'autorité de l'État, nomenclature administrative 8 vs 12 postes).

**Isosémantiques (§8.2) — ~20, sur S1, S3, S5, S6.** Aucun prompt propre : on
reprend une question `praticien` déjà retenue, on lui applique le prompt du §5.3
avec `REGISTRE : citoyen`, et l'on garde **une** variante. Les qrels seront
partagées entre les deux membres.

## 6. Le critère de sélection, écrit avant de voir les variantes

C'est la pièce qui rend le protocole défendable, et elle doit être figée
maintenant : un critère écrit après coup est une rationalisation.

**On retient la variante qui :**

1. est **plausible comme réellement tapée** par quelqu'un de ce registre ;
2. est **juridiquement cohérente** — la situation existe en droit français, le
   régime invoqué n'est pas inventé ;
3. ne **fuit aucune référence** (hors `retrouver_un_document`) ;
4. porte **une seule** question de droit ;
5. sur registre `citoyen` : emploie **le moins de vocabulaire normatif** possible.

> ⚠️ **Et on ne sélectionne jamais sur :** « celle que le moteur trouvera » ·
> « celle qui contient les bons mots-clés » · « celle qui ressemble le plus à un
> texte de loi » · « celle qui a l'air la plus facile à juger ».
>
> Ces quatre-là sont **le décalque par la porte de la sélection**. GOLDEN-SET.md
> §2 établit que la requête-décalque est matériellement impossible faute de
> document sous les yeux : c'est vrai de la construction, **faux de la
> sélection**. Retenir, parmi 5 variantes, la plus normative produit exactement
> l'effet que P-01 décrit — une requête rédigée dans les mots de sa cible — sans
> qu'aucun document soit jamais intervenu. Sur le registre citoyen le critère
> est **inverse** de l'intuition (point 5) : la variante la plus profane est la
> bonne, parce que l'écart profane/normatif est précisément ce que le jeu mesure.

**Ce que la sélection n'automatise pas** : la cohérence juridique (point 2). Un
modèle produit sans effort une question sur « le délai de rétractation d'un
CDI ». C'est l'unique raison pour laquelle cette étape ne peut pas être déléguée,
et elle coûte quelques secondes par item — pas davantage.

## 7. Ce qu'on enregistre

**Presque rien.** La méthode de génération est un échafaudage : elle variera
d'une version à l'autre — génération, rédaction par des experts, mélange des
deux. Ce qui est gelé et hashé, c'est le **texte** (E-P2-06) ; consigner le
prompt, le modèle, N et l'index retenu reviendrait à figer un outil dont
personne n'aura besoin, et à laisser croire qu'un jeu produit autrement serait
d'un autre statut. Il ne l'est pas.

Un seul champ mérite d'être posé, et seulement parce qu'il sera **impossible à
reconstituer après coup** une fois les origines mélangées :

```json
{
  "question_id": "S05-trouver_la_regle-cit-01",
  "texte": "...",
  "matiere": "S5",
  "intention": "trouver_la_regle",
  "registre": "citoyen",
  "date_pivot": "2026-07-31",
  "flags": [],
  "origin": "llm | expert | porteur"
}
```

Il sert à une question qu'on se posera un jour — *les questions écrites par des
experts se comportent-elles autrement que les questions générées ?* — et c'est
le pendant exact d'`origin` sur les jugements (ADR-008). S'il gêne, il saute :
il n'a aucune conséquence sur la mesure.

Les variantes écartées vont dans `variantes_ecartees.jsonl`, archivé, ni gelé ni
hashé — c'est un brouillon, gardé pour le seul §8.2.

**Date pivot** — proposition à trancher : *une seule date pour toute la v1, celle
du gel*, sauf pour les questions portant délibérément sur une succession
temporelle, qui reçoivent la leur. Une date par question serait plus juste et
n'apporterait rien : LEGI se dégrade par millésime, pas par jour.

## 8. Ce que l'exercice coûte réellement

| Étape | Exécutions | Items à lire |
|---|---|---|
| Temps 1 — 12 matières × 5 intentions, N = 6, on garde 2 | 60 | 360 |
| Temps 2 — sur les ~60 questions `citoyen` seulement, N = 5 | 60 | 300 |
| Négatives, frontière, polysémie | ~16 | ~90 |
| Isosémantiques (temps 2 sur questions déjà retenues) | ~20 | 100 |
| **Total** | **~156** | **~850** |

Pour ~175 questions retenues (155 scorables + 20 négatives).

> **Le LLM rend la génération gratuite ; il ne rend pas la sélection gratuite.**
> C'est le seul chiffre qui compte pour planifier : ~850 items courts à trier,
> soit quelques heures de lecture rapide, à comparer aux ~175 questions qu'il
> aurait fallu rédiger à la main. Le gain est réel, il n'est pas d'un ordre de
> grandeur.

Corollaire, qui contredit une intuition naturelle : **augmenter N ne coûte
presque rien à la génération et coûte tout à la lecture.** N = 6 puis N = 5 est
un choix de budget de lecture, pas un choix de qualité — au-delà, on lit
davantage de quasi-doublons.

## 9. Les risques propres à cette étape

| Risque | Pourquoi il est spécifique au LLM | Parade |
|---|---|---|
| **Décalque par sélection** | Le modèle produit spontanément des formulations normatives ; les retenir *paraît* être un choix de qualité | §6, critère écrit d'avance, point 5 inversé sur `citoyen` |
| **Effondrement de diversité** | N variantes d'un même appel ne sont pas indépendantes : le modèle décline un patron | Diversité exigée **sur les faits** au temps 1 ; conversation neuve par case |
| **Régime juridique halluciné** | Aucune erreur visible en aval : la question paraît normale et n'a simplement jamais de bonne réponse | Point 2 du §6 — le seul contrôle non délégable |
| **Monoculture stylistique** | Toutes les questions finissent par « sonner » pareil, et le jeu mesure la robustesse à *un* style | Le seul risque que le **mélange des méthodes** (experts, versions ultérieures) traite mieux qu'aucune parade interne |
| **Référence inventée** (`retrouver_un_document`) | Le modèle produit des numéros d'article plausibles et faux | Vérification contre le droit français, **jamais** contre le corpus |

Le premier est de loin le plus sérieux : c'est le seul qui ne produit **aucun
symptôme** et qui gonfle les scores dans le sens attendu.

## 10. Ce que ce document ne décide pas

- **Le modèle employé** — sans importance, à condition d'être le même sur un lot
  donné (sans quoi les six candidats d'une case ne sont plus comparables entre
  eux). D'un lot à l'autre, il peut changer sans que rien n'en dépende.
- **La méthode des versions suivantes.** Ce protocole vaut pour le premier lot.
  Les suivants viendront d'experts, d'un autre modèle, d'un mélange — le jeu
  n'en garde aucune trace au-delà d'`origin` (§7), et c'est voulu.
- **Le guide d'annotation** (ADR-005, cas limites) — périmètre B-08, indépendant.
- **L'ordre de récolte** — les cases sont indépendantes ; commencer par les
stratégies mal servies par le corpus (S6, S11, S12 — §10 de GOLDEN-SET.md) donne
  le plus vite la liste d'exigences à l'ingestion.

## 11. Ce qui doit survivre à ce document

**Deux choses, et elles ne parlent pas de la méthode.** Tout le reste — le
protocole en deux temps, les valeurs de N, les prompts eux-mêmes — est un
échafaudage propre au premier lot et meurt avec ce fichier.

| Quoi | Où | Pourquoi ça survit |
|---|---|---|
| **Le critère de sélection (§6)** | Guide d'annotation B-08 | Indépendant de la méthode. Un expert qui rédige sur un domaine qu'il maîtrise emploie spontanément le vocabulaire normatif de la cible qu'il a en tête : le décalque par sélection le guette **davantage** qu'un modèle, pas moins. |
| **La correction du §2 de GOLDEN-SET.md** | GOLDEN-SET.md §2 | Porte sur la validité de l'artefact : le décalque n'est pas « matériellement impossible », il est déplacé vers la sélection. Vrai quelle que soit la plume. |

Deux points mineurs à trancher au passage, sans enjeu : la **date pivot unique
v1** (§7) dans GOLDEN-SET.md §6.4, et le champ `origin` (§7) dans le modèle
`Query` d'`eval/` — ou pas.

**Pas d'ADR.** D-01 demandait si l'emploi hors ligne d'un LLM contrevient à
E-T-01. La réponse tient en une ligne (§2) et clarifie une exigence existante ;
elle n'arbitre aucune architecture. À porter en note sous E-T-01 dans
`EXIGENCES_v0.md`, pas en décision.

## 12. Références

[B-08-cadrage.md](B-08-cadrage.md) (D-01, pièges P-01 à P-04) ·
[B-08-prior-ponderation.md](B-08-prior-ponderation.md) (frontière machine/humain
appliquée à la lecture) · [analyse.md](analyse.md) (nomenclatures divergentes,
matériau du §5.4) · [GOLDEN-SET.md](../../product/GOLDEN-SET.md) §5, §6.3, §7.3,
§8 · ADR-005 · ADR-008 (provenance) · ADR-028 (régimes de vérification) ·
ADR-030 (deux axes) · ADR-032 (gel par version) · `EXIGENCES_v0.md` E-P2-06,
E-P2-07, E-P2-10, **E-T-01**
