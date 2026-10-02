# ADR-012 — Un interrupteur d'embedding, pas trois interrupteurs de store

**Statut** : acté (18 juillet 2026) — amende ADR-011 §5 · **amendé par
ADR-019** (interrupteur limité au bloc `dev`, plus de fournisseur `noop`)

## Contexte

ADR-011 §5 prévoyait des « interrupteurs de génération »
`exportation.<store>.enabled` pour MongoDB, Qdrant et Neo4j, avec pour
**unique cas d'usage nommé** `qdrant.enabled: false` en dev, motivé par
un seul fait : *l'embedding est ~99,9 % du temps d'un run* (mesuré). Le but réel n'a jamais
été de choisir dans quels stores écrire — c'était d'éviter de payer le
GPU en itérant sur le modèle de données.

En préparant l'implémentation d'ADR-011, deux constats :

1. **Aucun cas d'usage pour Mongo et Neo4j désactivés.** Neo4j *est*
   l'outil d'inspection privilégié de la v0 (ADR-011, contexte) ;
   Mongo porte le contenu de travail. Les désactiver irait à l'exact
   opposé du but d'ADR-011. La règle « pas de tâche au cas où »
   proscrit un échafaudage sans cas d'usage.
2. **Le « toggle Qdrant » était un toggle d'embedding déguisé.**
   L'embedding se déclenche dans le workload (`workload.py`), *en amont*
   de l'écriture Qdrant (un step de la saga). Un simple no-op sur le
   dépôt Qdrant couperait l'écriture mais **pas** le calcul des
   vecteurs : on paierait les ~173 s de GPU pour les jeter. Le levier
   de coût que §5 visait n'est donc pas atteignable par un interrupteur
   de *store*.

## Décision

Remplacer les trois interrupteurs `exportation.<store>.enabled` par
**un seul interrupteur d'embedding**, exposé en `parameters.yml`
(phase formatting/embedding). Quand il est actif (dev) :

- le workload **ne calcule pas** les vecteurs (l'appel à `embed()` est
  sauté) ;
- l'écriture Qdrant reçoit zéro chunk embarqué — il n'y a rien à
  écrire ;
- Mongo et Neo4j tournent **normalement** : c'est précisément l'état
  recherché pour itérer sur le modèle de données sans le mur GPU.

Le nom porte l'intention (« ne pas embarquer »), pas l'effet de bord
(« ne pas écrire Qdrant »). Interrupteur pérenne (v1 incluse), pas un
mode jetable — dans le même esprit d'échafaudage activable que
l'ADR-011.

## Alternatives rejetées

- **Garder les trois toggles par store** (l'ADR-011 §5 littéral) :
  deux d'entre eux (Mongo, Neo4j) n'ont aucun cas d'usage et
  contrediraient le rôle d'inspection de Neo4j ; « au cas où » proscrit.
- **No-op sur le seul dépôt Qdrant** : coupe l'écriture sans couper
  l'embedding — ne réalise pas l'économie qui justifiait §5, et calcule
  173 s de vecteurs pour les jeter.
- **Deux interrupteurs séparés** (« ne pas embarquer » / « ne pas
  écrire Qdrant ») : ouvre une combinaison (embarquer sans écrire) sans
  cas d'usage.

## Conséquences

- ADR-011 §5 est **amendé** : `exportation.<store>.enabled` n'est plus
  implémenté ; le point 5 devient « un interrupteur d'embedding ». Les
  autres points d'ADR-011 (fin des unknowns,
  hydratation Neo4j, aplatissement, épuration Mongo, nettoyage,
  échantillonnage) sont inchangés.
- Le régime dev/prod (ADR-011 §1-2, différencié par `ENVIRONMENT`)
  reste le mécanisme structurant ; cet interrupteur en est un levier
  parmi d'autres, pas un régime à part.
- Le workload devient le seul point où l'état « embedding coupé » est
  lu — justifié par la mesure (l'embedding n'existe qu'à cet endroit),
  pas par confort.

## Références

ADR-011 (§5 amendé) · ADR-010 · ADR-019 (amende cet ADR) · `workload.py`
