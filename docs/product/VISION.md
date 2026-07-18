# VISION — Murphy

> Socle du programme. Fixe la **mission** et les **invariants non négociables** :
> ce qui ne se rediscute pas d'une version à l'autre et contraint tous les
> arbitrages en aval. Court par nature. Les décisions datées et révisables
> vivent dans `PROGRAM.md` et `decisions/`.

## 1. Mission

Rendre **la totalité du corpus juridique français** interrogeable — par un humain
comme par un agent — sous la forme d'un moteur qui **donne les sources, sans
raisonner à la place de l'usager**.

Aujourd'hui, Murphy est un **programme** composé de trois projets interdépendants
(Data, Évaluation, Applicatif), convergeant vers une **alpha avec des experts
du droit dans la boucle**. Son horizon est un
**commun numérique** d'intérêt général : service subventionné, porté par une
structure associative, publié à l'échelle nationale.

## 2. Invariants non négociables

**Sourcer, ne pas raisonner.** Murphy restitue des documents et des sources, pas
des réponses. La génération LLM est un échafaudage transitoire, destiné à être
**retiré** : la valeur du produit est la qualité de la récupération, jamais la
prose d'un modèle. On ne substitue pas le jugement de la machine à celui du
juriste.

**Exhaustivité visée.** L'objectif est de couvrir *tout* le droit français, pas
un échantillon commode. On n'écarte pas une source au motif qu'elle est
difficile. Le flou et l'imprécision du droit doivent être **encapsulés et
représentés**, jamais éliminés par simplification. L'exhaustivité est une
exigence à atteindre progressivement (critère de publication), pas un préalable.

**Identité canonique.** Tout document et tout fragment porte un **identifiant
stable et unique**, partagé à l'identique par les trois bases (MongoDB, Neo4j,
Qdrant). ECLI est l'identifiant primaire en jurisprudence ; les IDs internes
DILA et les numéros métier ne sont que des clés techniques ou des replis. Sans
cette couche d'identité, ni l'évaluation agnostique ni la boucle experts ne sont
possibles : c'est l'invariant qui rend tout le reste mesurable.

**Découplage récupération / génération.** La récupération est un composant
autonome, évaluable seul, indépendant de toute couche générative. Elle est
mesurée pour elle-même (harnais IR, golden-sets) et doit pouvoir tourner — et
progresser — sans qu'aucun LLM ne soit branché.

**Respect de l'usager.** Le service est **stateless** (aucun historique
conversationnel conservé), **fail-fast** (erreur claire plutôt que réponse
dégradée silencieuse), et ne procède à **aucune analyse du contenu** des
requêtes. La confidentialité de la recherche juridique est structurelle, pas une
option.

## 3. Ce que Murphy n'est pas

Un chatbot juridique qui « répond » ; un assistant qui conseille ou tranche ; un
agrégateur partiel des sources « importantes » ; un produit propriétaire à but
lucratif. Toute fonctionnalité qui contredit un invariant ci-dessus est hors
programme, quel qu'en soit l'intérêt à court terme.
