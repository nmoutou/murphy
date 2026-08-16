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

Le cas grave n'est pas le Cerfa mais la **convention collective**. La question *"Que dit ma convention collective sur le préavis ?"* est une requête de groupe B banale, et lui rendre le code du travail seul, c'est rendre le principe sans sa dérogation : le pire échec du projet selon (§1.2 et Q-05). **Ce manque-là n'est pas dans le graphe mais dans l'état du corpus : on le connaît, donc on *doit* l'annoncer**.

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
| **1 - La référence** | un identifiant de forme reconnaissable - article et code, numéro de pourvoi, numéro de décret | "article L1234-5 du code du travail" · "Cass. soc. 25 nov. 2015, n° 14-24.444" | résoudre, non chercher : aucun écart à franchir | **le bruit** - la pièce voisine rendue pour la bonne, et jamais revérifiée |
| **2 - Les mots du corpus** | un terme que les textes visés portent | "préavis de démission" · "vice caché" · "rupture conventionnelle" | aller de la notion à ses supports | **le bruit** - on trouve, et autre chose, en trop, avec |
| **3 - Le nom d'emprunt** | un nom absent du texte qu'il désigne - éponyme, surnom, étiquette | "la prime Macron" · "la loi Badinter" | une correspondance vers le nom légal : elle existe et se tabule | **la correspondance fausse** - une réponse bien formée et fausse |
| **4 - Les mots de l'usager** | aucun terme repris du corpus ni du dispositif | "mon patron me fait travailler plus que prévu et ne me paie pas plus" · "mon père est décédé et il y a une maison" | une qualification qu'aucune correspondance ne fournit ; l'objet juridique lui-même n'est parfois pas délimité | **le silence**, indistinguable de l'absence de règle |

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
| **B - L'ensemble** | ni pièce singulière, ni dimension nommée | "le préavis de démission" · "l'article L1234-5 et ce qui le borne" | rendre la norme et ce qui la borne (le principe et sa dérogation/l'article et ses exceptions), **inconnu de l'usager** | il manque l'exception, et rien ne signale qu'elle manque |
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
| **A - Constituer** | aucune inflexion, ou une relaxation explicite : "y compris", "et aussi", "tous les cas de" | "le préavis de démission" · "le préavis de démission, y compris en période d'essai" | privilégier le **rappel**, au prix de la précision | aucun spécifique : il hérite de celui de la classe visée |
| **B - Resserrer** | une restriction explicite : "uniquement", "seulement lorsque", une condition ajoutée | "le préavis de démission uniquement en CDD" | filtrer, sur un ensemble | ne pas retirer un sous-ensemble que l'usager avait explicitement demandé d'écarter |

---

## 2. Les classes

