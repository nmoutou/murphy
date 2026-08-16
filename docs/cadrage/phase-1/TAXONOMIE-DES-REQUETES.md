# Taxonomie des requêtes - Murphy

## 0. Objet

### 0.1. Spécifications générales

**La taxonomie classe des requêtes, pas des utilisateurs.** La règle de non-personalisation (**D-06**) l'impose : le système ne voit d'un usager que ce que sa requête inclut. Toute propriété qui ne se lit pas dans la requête est illégitime ici. Ce qui s'apparenterait à un niveau d'expertise n'est permis qu'à la condition d'être inclus dans la formulation elle-même, en temps que propriété de la requête.

**Critère d'admission d'une classe :** Deux requêtes appartiennent à des classes différentes si, et seulement si, **le système doit se comporter différemment, ou échouer différemment**. 

**L'instrument** responsable de mesurer la qualité de la récupération est proscrit d'utiliser un **discriminant circulaire** : exiger de connaître la réponse pour **classer** la question. La règle générale de choix du discriminant est donc la suivante : un discriminant doit être décidable **avant** que la requête soit servie, non qu'il doive tenir dans la requête. **Cette règle porte sur l'instrument, jamais sur le périmètre**, et la confusion est assez facile pour valoir d'être fermée ici. Elle dit comment on **range** une requête, pas à laquelle on **répond**. Qu'un usager tienne déjà l'identifiant de ce qu'il veut lire n'est pas un cas gênant : une grande part du groupe A, et les citoyens les plus cultivés du groupe B, sont tous justiciables.

---

### 0.2. Anonymisation

**L'anonymisation est en amont de la taxonomie.** Ainsi, le refus d'anonymisation (**D-09**) n'est pas une classe de requête : il s'applique à toutes les classes sans en distinguer aucune, donc n'apparaît sur aucun axe.

---

### 0.3. Absences

**L'usager peut nommer un objet qui n'est pas dans le corpus ; L'absence doit être déclarée, explicitement et au premier plan.** Quand la requête nomme un objet que le corpus ne porte pas, le système le dit. Il peut ensuite rendre l'entourage juridique de l'objet, il doit alors le donner pour ce qu'il est, l'entourage et non l'objet. Cela dit, **la substitution est facultative**. Elle l'est même lorsqu'il n'y a rien à mettre à la place : c'est là qu'elle vaut le plus. En effet, un résultat vide non déclaré pourrait se lire *"cette règle n'existe pas"* (le problème en §1). 

> Dire *je n'ai pas trouvé* et dire *je ne peux pas trouver* n'engagent pas la même chose : le premier porte sur le résultat de la requête, le second porte sur l'état du corpus. Dans l'optique de déclarer ce que le corpus ne contient pas, ce document doit aussi expliciter les cas des classes qui existent et ne sont pas (et/ou ne doivent pas être) servies

**L'absence ne se déduit pas d'un résultat vide :** Elle doit s'établir par la résolution d'un identifiant et par rien d'autre. Déclarer absent ce qui est présent mais mal cherché produit une **fausse déclaration d'absence** : une réponse bien formée et fausse. C'est pire que le silence qu'elle remplace, puisqu'elle fait dire au système que "la règle n'existe pas" (voir **R-57**).

**Ce que l'inventaire sait, et ce qu'il ne sait pas.** L'absence d'une **base entière** se connaît. En revanche, l'absence d'une **pièce dans une base présente** ne se connaît que relativement à ce qui a été téléchargé et traité, jamais à ce qui a été publié : le producteur des données reste maître de ce qu'il diffuse (**C-06**). À cette granularité, la déclaration doit donc dire **"sans résultats"**, jamais **"inexistant"**. 

> **Cette nuance n'est pas une prudence de rédaction, c'est la limite de ce que le système sait.**

Le cas grave n'est pas le Cerfa mais la **convention collective**. La question *"Que dit ma convention collective sur le préavis ?"* est une requête de groupe B banale, et lui rendre le code du travail seul, c'est rendre le principe sans sa dérogation : le pire échec du projet selon (§1.2). **Ce manque-là n'est pas dans le graphe mais dans l'état du corpus : on le connaît, donc on *doit* l'annoncer**.

---

### 0.4. Limite de validité

Les spécimens sont produits par une seule tête. Le risque est que la taxonomie pourrait classer des usagers **imaginés**, plutôt que des usagers réels (**R-05**).

---

## 1. Axes

### 1.1 L'axe primaire

Ce dont l'utilisateur dispose d'emblée, à priori. La méthodologie l'évalue par rapport à la phrase qui "porte" le problème : *le moteur "exige" le vocabulaire de la réponse comme "clé d'accès" à la réponse.* L'axe prpopsé mesure la distance entre **ce que l'usager a déjà** et **les mots que le corpus contient**. 

L'axe peut se lire comme un gradient *ordonné et nommé* : l'identifiant du producteur, puis les mots des textes eux-mêmes, puis le nom qu'un tiers leur a donné, puis ceux de l'usager.

=> À chaque cran, on s'éloigne de la réponse canonique, pour se rapprocher des mots de l'utilisateur.

| Cran | Discriminant | Exemples | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **1 - La référence** | un identifiant de forme reconnaissable - article et code, numéro de pourvoi, numéro de décret | "article L1234-5 du code du travail", "Cass. soc. 25 nov. 2015, n° 14-24.444" | résoudre, non chercher : aucun écart à franchir | **le bruit** - la pièce voisine rendue pour la bonne, et jamais revérifiée |
| **2 - Les mots du corpus** | un terme que les textes visés portent | "préavis de démission", "vice caché", "rupture conventionnelle" | aller de la notion à ses supports | **le bruit** - on trouve, et autre chose, en trop, avec |
| **3 - Le nom d'emprunt** | un nom absent du texte qu'il désigne - éponyme, surnom, étiquette | "la prime Macron", "la loi Badinter" | une correspondance vers le nom légal : elle existe et se tabule | **la correspondance fausse** - une réponse bien formée et fausse |
| **4 - Les mots de l'usager** | aucun terme repris du corpus ni du dispositif | "mon patron me fait travailler plus que prévu et ne me paie pas plus", "mon père est décédé et il y a une maison" | une qualification qu'aucune correspondance ne fournit ; l'objet juridique lui-même n'est parfois pas délimité | **le silence**, indistinguable de l'absence de règle |

**Le mode d'échec bascule le long du gradient :** 
- En haut (1–2), l'échec est du **bruit** : on trouve, et autre chose, en trop,  avec.
- En bas (3–4), l'échec est du silence : **un système qui échoue silencieusement en bas du gradient n'améliore pas le moteur public, il en déguise la médiocrité**.

**C'est l'axe qui mesure ce que Murphy ajoute, par rapport aux solutions déjà existantes :** La résolution d'identifiant est résolue depuis longtemps, le cran 4 ne l'est par personne. 

#### Règle de frontière : le nom figure-t-il dans le texte ?

Aux crans 3 et 4, le nom utilisé dans la requête est absent du texte qu'il désigne, ce qui impose au système de test **une étape de correspondance**. C'est cette étape qui donne à l'instrument d'évaluation son mode d'échec propre aux deux derniers crans :  une réponse bien formée et fausse.

#### Récupération large : trop de résultats, jamais trop peu

Quand le système doit se tromper, **il doit se tromper par/en excès.** Un ensemble trop large se réduit, un ensemble trop étroit ne se remarque même pas nécessairement ; Rien ne dit ce qui a été laissé en dehors des résultats. C'est l'asymétrie du gradient : le bruit se juge comme tel, mais le silence peut se déguiser en absence de norme. La récupération large est donc une **décision** : on doit prioriser le **Recall**, au prix de la **Precision**. 

**L'ensemble restitué doit être lisible comme ensemble.**  Il doit donner à voir sa propre dispersion : l'usager ne répond à aucune question, il doit pouvoir constater de l'étendue de ce qu'il tient et poser une équation plus étroite. Sans cela, impossible de passer du cran 4 au cran 3.

**L'utilisateur est l'opérateur de sa recherche.** En effet, la qualification juridique lui revient (**D-03**) : c'est à lui de décider de quoi sa situation relève et d'orienter ce qu'il cherche. Le système ne délimite pas l'objet à sa place. **D-07** lui confie du même geste le jugement sur ce qui est rendu, donc le resserrement.

**L'utilisateur peut affiner sa recherche avec plusieurs requêtes.** Le geste correctif peut est une nouvelle requête. Des **filtres** seront également à sa disposition, pour garantir un autre moyen de modifier l'ensemble du résultat de la recherche.

**La question de clarification n'est pas tranchée ici.** Qu'un système puisse demander "voulez-vous dire X ou Y ?" pour orienter le tour suivant est une possibilité qui engage un tour de dialogue que ce document ne décide pas.

**Aucun refus explicite.** Il est réservé au hors-périmètre : une demande d'interprétation (**D-03**). Une requête jugée trop vague est une requête légitime dont l'ensemble en réponse est, lui-aussi, jugé trop large.

---

### 1.2 L'axe secondaire

Cet axe décrit la **sortie** : la forme de l'ensemble visé et quel ensemble le satisferait. Son unité de valeur n'est pas seulement l'ensemble restitué mais l'ensemble atteignable.

| Valeur | Discriminant | Exemples | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **A - La pièce** | une visée singulière : un arrêt, une loi, une décision | "l'arrêt qui a posé que le silence ne vaut pas acceptation" | rendre une pièce identifiée, **connue de l'usager** | on ne l'a pas, constatable immédiatement |
| **B - L'ensemble** | ni pièce singulière, ni dimension nommée | "le préavis de démission", "l'article L1234-5 et ce qui le borne" | rendre la norme et ce qui la borne (le principe et sa dérogation/l'article et ses exceptions), **inconnu de l'usager** | il manque l'exception, et rien ne signale qu'elle manque |
| **C - La série** | une dimension du corpus explicitement nommée | "toutes les versions de l'article L1234-5 depuis 2008" | énumérer exhaustivement sur la dimension, **calculable** | un trou dans l'exhaustivité, localisable **sur la dimension** |

**Cet axe rend "bruit / silence" opérable.** 
- Sur **la pièce**, le bruit est presque gratuit : la bonne pièce est là, le reste s'ignore. 
- Sur **l'ensemble**, le silence est le pire échec du projet : l'usager repart avec une règle vraie et incomplète, plus confiant qu'avant, et c'est la seule configuration où Murphy peut nuire à quelqu'un qui n'aurait rien trouvé sans lui. 
- Sur **la série**, un résultat complet à 95 % est un résultat incomplet : c'est un échec.

#### Règle de frontière : sans dimension nommée, pas de série

Une série n'existe que si l'usager **nomme la dimension** sur laquelle elle s'étend : une période, une juridiction, une nature de texte, "toutes les versions". 

<u>**Cas limite :**</u> "Toutes les règles sur le préavis" porte le mot *toutes* mais ne nomme aucune dimension : c'est un ensemble. Le discriminant reste observable seulement dans requête, puisque la dimension doit y être énoncée pour que la requête soit une série.

---

### 1.3 L'axe tertiaire 

Cet axe mesure ce que l'utilisateur demande au système de **faire** : **l'opération demandée**. Il porte sur l'**inflexion que la requête porte en elle-même**.

| Valeur | Discriminant | Exemples | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **α - Constituer** | aucune inflexion, ou une relaxation explicite : "y compris", "et aussi", "tous les cas de" | "le préavis de démission", "le préavis de démission, y compris en période d'essai" | privilégier le **rappel**, au prix de la précision | aucun spécifique : il hérite de celui de la classe visée |
| **β - Resserrer** | une restriction explicite : "uniquement", "seulement lorsque", une condition ajoutée | "le préavis de démission uniquement en CDD" | filtrer, sur un ensemble | ne pas retirer un sous-ensemble que l'usager avait explicitement demandé d'écarter |

---

## 2. Classes

### 2.1. Composition et notation

**Une classe est un triplet complet :** un cran de l'axe primaire, une valeur de l'axe secondaire, une valeur de l'axe tertiaire. L'espace nominal compte donc 4 × 3 × 2 = **24 cellules**.

---

### 2.2. Les retraits

#### 2.2.1 Les six cellules qui ne sont pas classes

**Une cellule n'est pas automatiquement une classe.** Le critère d'admission (**§0.1**) est un test de fusion : une cellule qui hérite intégralement du comportement cible **et** du mode d'échec de sa voisine n'est pas une classe distincte, c'est la même. Six cellules tombent par ce test, et il reste **18 classes**.

**Règle générale : le *resserrement* fait une classe, partout où il existe un ensemble candidat à réduire.** En effet, il y ajoute un comportement cible qui lui est propre : **imputer au filtre le vide qu'il produit**. Un resserrement qui vide l'ensemble et laisse lire le vide comme une absence de règle produit exactement la fausse déclaration d'absence que **R-57** proscrit. 

| Fusion | Cellule(s) | Absorbée(s) par |
|---|---|---|
| **F1** - la cible est déjà résolue | **1-A-β** | **1-A-α** |
| **F2** - le resserrement d'une série redéfinit sa dimension | **1-C-β · 2-C-β · 3-C-β · 4-C-β** | **-C-α** |
| **F3** - héritage d'une classe non servie | **4-A-β** | **4-A-α** |

#### Justifications

##### F1 - la cible est déjà résolue

Au cran 1 sur la pièce, il n'y a aucun ensemble candidat : l'identifiant désigne. Le resserrement y porte sur l'*intérieur* d'une pièce déjà tenue ("l'article L1234-5, uniquement l'alinéa 2"), c'est-à-dire sur la résolution d'un identifiant/contexte plus fin. 

##### F2 - le resserrement d'une série redéfinit sa dimension

Une série est déjà bornée par la dimension que l'usager a nommée (**§1.2**). Y ajouter une restriction ("toutes les versions depuis 2008, seulement celles issues d'une loi") ne fait que resserrer l'assiette : l'énumération exhaustive reste une énumération exhaustive, et son mode d'échec reste le trou localisable sur la dimension.

##### F3 - héritage d'une classe non servie

4-A-α n'est pas servie (**§2.2.2**) ; le resserrement n'y ajoute rien qui soit servi.

#### 2.2.2 Classes non servies

| Classe(s) | Motif de non-service | Énoncé dû à l'usager | Mode d'échec propre |
|---|---|---|---|
| **4-A-α**<br>*Pièce extra-textuelle*<br>(et **4-A-β**, absorbée par **F3**) | La requête vise une pièce singulière sans porter aucun terme qui la désigne : ni identifiant à résoudre, ni formule du corpus, ni nom d'emprunt à faire correspondre. Il n'y a rien sur quoi opérer, et la visée singulière interdit de rendre l'ensemble à la place. Le motif est **dans la requête** : aucune ressource ajoutée au système ne le lèverait | déclarer l'impossibilité de résoudre, et l'**imputer à la requête**, non au corpus : la pièce visée existe peut-être, elle n'est simplement pas atteignable par ce qui est fourni (**§0.3** — *sans résultats*, jamais *inexistant*) | rendre une pièce **plausible** à la place de la pièce visée : l'usager ne tient aucun identifiant qui lui permette de la démentir, donc l'erreur est indétectable de son côté |

---

### 2.3. Cran 1 - La référence

| Classe | Discriminant conjoint | Spécimens | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **1-A-α**<br>*Résolution* | identifiant **×** visée singulière **×** aucune inflexion | "article L1234-5 du code du travail", "Cass. soc. 25 nov. 2015, n° 14-24.444" | résoudre et non chercher : rendre la pièce désignée, aucun écart à franchir | **le bruit :** la pièce voisine (L1234-6) rendue pour la bonne, et jamais revérifiée |
| **1-B-α**<br>*Référence étendue* | identifiant **×** demande de ce qui borde le texte | "l'article L1234-5 et ce qui le borne" **×** "que dit la jurisprudence sur l'article 1240 du code civil" | résoudre, **puis** rendre l'entourage normatif : la dérogation, l'exception, l'application | **le silence :** il manque l'exception, et rien ne signale qu'elle manque |
| **1-B-β**<br>*Référence étendue resserrée* | identifiant **×** entourage **×** restriction explicite | "l'article L1234-5, uniquement pour les CDD", "ce qui borne L1234-5, seulement en cassation" | filtrer l'entourage sur la restriction, et **imputer au filtre** le vide qu'il produit | **double :** le silence hérité de 1-B-α, et le filtre non appliqué ou sur-appliqué sans déclaration |
| **1-C-α**<br>*Série référencée* | identifiant **×** dimension nommée | "toutes les versions de l'article L1234-5 depuis 2008" | énumérer exhaustivement sur la dimension, l'exhaustivité y est **calculable** | **le trou :** localisable sur la dimension : 95 % est un échec |

---

### 2.4. Cran 2 - Les mots du corpus

| Classe | Discriminant conjoint | Spécimens | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **2-A-α**<br>*Pièce décrite* | terme du corpus **×** visée singulière **×** aucune inflexion | "l'arrêt qui a posé que le silence ne vaut pas acceptation" | aller de la formule à son support unique, et rendre large autour | **on ne l'a pas**, constatable immédiatement : le bruit y est presque gratuit |
| **2-A-β**<br>*Pièce décrite resserrée* | idem **×** restriction portant sur l'espace candidat | "l'arrêt qui pose que le silence ne vaut pas acceptation, uniquement en chambre sociale" | filtrer l'espace candidat **avant** de désigner ; un résultat vide s'impute à la restriction, jamais au corpus | la bonne pièce écartée par le filtre, et le vide lu comme une absence |
| **2-B-α**<br>*Ensemble notionnel*<br>**(pivot)** | terme du corpus **×** ni pièce ni dimension **×** aucune inflexion | "le préavis de démission", "le vice caché", "la rupture conventionnelle" | rendre la norme **et** ce qui la borne ; privilégier le rappel ; donner l'ensemble à voir comme ensemble | **le pire échec du projet :** une règle vraie et incomplète, un usager plus confiant qu'avant |
| **2-B-β**<br>*Ensemble notionnel resserré* | idem **×** restriction explicite | "le préavis de démission uniquement en CDD" | constituer l'ensemble, **puis** filtrer ; imputer au filtre le vide qu'il produit | le sous-ensemble pas écarté / le **sur-filtrage silencieux** |
| **2-C-α**<br>*Série notionnelle* | terme du corpus **×** dimension nommée | "toutes les décisions de la Cour de cassation depuis 2020 sur le vice caché" | énumérer exhaustivement sur la dimension, **et déclarer la notion retenue** : l'exhaustivité est calculable sur la dimension, pas sur la notion | **le trou :** et l'ambiguïté sur son origine : la dimension ou l'assiette notionnelle |

---

### 2.5. Cran 3 - Le nom d'emprunt

Les cinq classes de ce cran passent toutes par **l'étape de correspondance** (**§1.1**), qui leur donne leur mode d'échec commun : une réponse bien formée et fausse. **La correspondance doit être rendue visible comme correspondance** - l'usager doit voir sous quel nom légal on a traduit le sien, sans quoi il n'a aucun moyen de constater l'erreur.

| Classe | Discriminant conjoint | Spécimens | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **3-A-α**<br>*Pièce sous nom d'emprunt* | nom absent du texte **×** visée singulière **×** aucune inflexion | "la loi Badinter", "l'arrêt Perruche" | établir la correspondance, l'exposer, puis résoudre | **la correspondance fausse :** bien formée, plausible, et fausse |
| **3-A-β**<br>*Correspondance désambiguïsée* | idem **×** restriction portant sur les candidats du nom | "la prime Macron, uniquement celle de 2022" | traiter la restriction **d'abord** comme un départage entre candidats du nom, **ensuite** seulement comme un filtre | la **restriction appliquée à la mauvaise correspondance** : le filtre **confirme** l'erreur au lieu de la révéler |
| **3-B-α**<br>*Dispositif sous nom d'emprunt* | nom absent du texte **×** ni pièce ni dimension | "la prime Macron", "la loi anti-cadeaux" | correspondre, puis rendre le dispositif et ses conditions | **cumul :** correspondance fausse, et silence sur les conditions |
| **3-B-β**<br>*Dispositif sous nom d'emprunt resserré* | idem **×** restriction explicite | "la prime Macron, seulement pour les entreprises de moins de 50 salariés" | correspondre, constituer, puis filtrer ; imputer au filtre son propre vide | **cumul, pire :** correspondance fausse, silence sur les conditions, et le sous-ensemble écarté non retiré |
| **3-C-α**<br>*Série sous nom d'emprunt* | nom absent du texte **×** dimension nommée | "toutes les versions de la prime Macron depuis 2019" | énumérer exhaustivement sur la dimension, l'assiette étant fixée par une correspondance exposée | **le plus composite du tableau :** un trou dont on ne sait pas s'il vient de la dimension ou de la correspondance |

---

### 2.6. Cran 4 - Les mots de l'usager

| Classe | Discriminant conjoint | Spécimens | Comportement cible | Mode d'échec |
|---|---|---|---|---|
| **4-A-α**<br>*Pièce extra-textuelle*<br>**(non servie, §2.2.2)** | aucun terme du corpus **×** visée singulière | "la décision que ma voisine a obtenue contre son propriétaire" | déclarer l'impossibilité de résoudre | rendre une pièce **plausible** à la place de celle qui est visée |
| **4-B-α**<br>*Situation racontée*<br>**(pivot)** | aucun terme du corpus ni du dispositif **×** ni pièce ni dimension **×** aucune inflexion | "mon patron me fait travailler plus que prévu et ne me paie pas plus", "mon père est décédé et il y a une maison" | rendre large, donner l'ensemble à voir dans sa dispersion, ne pas délimiter l'objet à la place de l'usager (**D-03**), rendre possible le passage au cran 3 | **le silence :** indistinguable de l'absence de règle |
| **4-B-β**<br>*Situation racontée resserrée*<br>**(la plus dure)** | idem **×** restriction elle aussi en mots d'usager | "mon patron ne me paie pas mes heures en plus, uniquement ce qui vaut pendant la période d'essai" | constituer l'ensemble **avant** d'appliquer la restriction : le filtre porte sur un ensemble qui n'existe pas encore au moment où il est énoncé | **le silence fabriqué par le filtre :** une restriction non qualifiée appliquée littéralement coupe l'ensemble avant qu'il soit constitué |
| **4-C-α**<br>*Série sur situation racontée*<br>**(statut à trancher, §2.8)** | aucun terme du corpus **×** dimension nommée | "toutes les décisions depuis 2020 où un patron n'a pas payé les heures en plus" | l'exhaustivité porte sur une qualification que le système doit lui-même produire : elle n'est pas décidable | **l'exhaustivité affirmée sur une assiette non qualifiée :** une complétude annoncée qui ne peut pas être vraie |

## 3. Legs

