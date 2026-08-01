# Relations — registre et structure

> Une **relation** lie deux objets. Elle se distingue de la **facette**, qui
> est une dimension sur laquelle un objet prend une valeur.
>
> Cette distinction n'est pas de commodité : c'est elle qui tranche la question
> de la forme générale du modèle — voir §1.

## 1. Ce que la distinction règle : arbre ou rhizome

| | Facette | Relation |
|---|---|---|
| Nature | Une dimension ; un objet y prend une valeur | Un lien entre deux objets |
| Structure interne | **Peut être un arbre**, et l'est souvent | Un **graphe**, typé |
| Exclusivité des valeurs | Visée | Sans objet |
| Exemples | matière, rôle, territoire, temps, fonction | rang, abrogation, spécialité, qualification, renvoi |

D'où la forme retenue : **arborescent localement, acentré globalement.**

Chaque facette est un arbre — bien fondé, testable, avec une racine locale et
des valeurs qui s'excluent. L'ensemble n'a **aucune racine** : il n'existe pas
de nœud « le Droit » dont tout descendrait. On entre par n'importe quelle
facette, on circule par les relations typées.

**Ce à quoi on renonce, explicitement.** Un graphe où tout point se connecte à
tout point par des arêtes non typées rend **aucun classement jamais faux**,
donc rien de réfutable, donc rien de validable. On ne peut pas viser un modèle
*juste* et un modèle où rien ne peut être *faux*. La « rupture asignifiante »
est écartée sans regret ; l'acentrement et les entrées multiples sont conservés
intégralement.

**Traduction technique.** C'est exactement ce que SKOS offre sans effort : un
`ConceptScheme` par facette, `broader`/`narrower` à l'intérieur, propriétés
typées entre schemes. La **polyhiérarchie** est native — un concept peut avoir
plusieurs `broader` — ce qui donne l'essentiel de la souplesse recherchée tout
en interdisant les cycles, donc en gardant des tests possibles.

## 2. Relations de C3 — entre normes

| Relation | Énoncé | Structure |
|---|---|---|
| **rang** | N₁ prime N₂ par sa place dans la hiérarchie des normes | Ordre partiel |
| **spécialité** | N₁ écarte N₂ sur son domaine propre (*lex specialis*) | Ordre partiel, conditionné au recouvrement des domaines de validité |
| **succession** | N₁ remplace N₂ dans le temps (*lex posterior*) | Ordre total sur un même objet |
| **abrogation** | N₁ met fin à la vigueur de N₂ | Événement daté, orienté |
| **modification** | N₁ altère le texte de N₂ | Événement daté, orienté |

## 3. Relations de C4 — entre fait et norme

| Relation | Énoncé | Notes |
|---|---|---|
| **qualification** | Un fait est caractérisé comme relevant d'une catégorie juridique | La relation centrale. Son statut est le point ouvert R-01 |

**Ce qui varie par domaine, et c'est la vraie réponse à « différents domaines,
différentes représentations ».** Les domaines ne diffèrent pas par leur
contenu mais par **quatre propriétés de la relation de qualification** :

| Domaine | Clôture | Auteur | Cardinalité | Temporalité |
|---|---|---|---|---|
| **Pénal** | **Fermée** — légalité des délits et des peines, aucune qualification hors liste | Le législateur | 1 (concours mis à part) | Date de commission |
| **Contrat** | Ouverte | Les parties, puis le juge qui **re-qualifie** | **2 concurrentes** sur le même fait | Date de formation |
| **Fiscal** | Fermée | Le contribuable **déclare**, l'administration contrôle | 1, avec statut (déclarée / redressée / jugée) | Fait générateur |
| **Famille** | Fermée | L'officier d'état civil, le juge | 1 | **Un état, non un événement** — durée, pas date |
| **Administratif** | Ouverte | Le requérant, par l'acte qu'il attaque | 1 | Date de l'acte |

Quatre propriétés, modélisables comme telles. C'est plus précis et plus
opérationnel que « chaque domaine a un centre de gravité » — formulation
antérieure, abandonnée pour cause de flou.

## 4. Relations candidates et objets non classés

| # | Objet | Problème |
|---|---|---|
| **R-a** | **Ordre conditionnel** — la convention collective déroge à la loi *si elle est plus favorable* | Un rapport de rang qui dépend d'une **comparaison de contenu**. Non exprimable comme ordre partiel statique. Le droit du travail entier repose dessus |
| **R-b** | **Condition** — qualité pour agir, intérêt à agir, recevabilité | Transforme un rôle de fait en rôle de droit. Ni facette ni relation : un **prédicat sur les faits** qui conditionne l'applicabilité. Hypothèse de réduction en §5 |
| **R-c** | **Application** — la loi renvoie à un décret qui la met en œuvre | Probablement un cas de renvoi. À confirmer |
| **R-d** | **Interprétation** — une décision fixe le sens d'un article | Oriente document → norme, donc traverse C6. À traiter avec soin |

## 5. Hypothèse de travail sur R-b

**Hypothèse** : une condition est réductible à une **norme de fonction
secondaire** au sens de C5 — une règle de recevabilité est une règle sur les
règles, pas une conduite prescrite. Si l'hypothèse tient, R-b disparaît comme
catégorie autonome et se range en `F5 = compétence` ou `F5 = procédure`.

**Test qui la falsifierait** : trouver une condition qui ne soit portée par
aucune norme identifiable — c'est-à-dire une condition purement
jurisprudentielle et jamais écrite. L'intérêt à agir en excès de pouvoir est
le premier candidat à examiner.

## 6. Points ouverts

| # | Question |
|---|---|
| **R-01** | **La qualification est-elle une entité ou une relation ?** Si entité : elle a ses propres facettes, se catalogue, s'aligne sur NATINF — le modèle a un centre. Si relation : elle n'existe qu'entre un fait et une norme donnés, ne se catalogue pas — le modèle est vraiment acentré. Le pénal pousse vers *entité* (liste fermée et publiée), le civil vers *relation* (construite au cas par cas). **C'est la décision qui commande le plus de choses en aval** |
| **R-02** | **R-a, l'ordre conditionnel** — représentation à trouver, ou domaine à traiter à part |
| **R-03** | **R-b** — hypothèse de réduction à tester |
