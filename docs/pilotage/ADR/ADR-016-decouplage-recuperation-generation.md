# ADR-016 — Découplage récupération/génération + pertinence graduée

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

Murphy repose sur un invariant de vision : **sourcer, ne pas
raisonner**. La génération LLM est un échafaudage transitoire, destiné à
être retiré. Comment rendre cela mesurable ?

## Décision

- La **récupération est un composant autonome**, évaluable seul,
  indépendant de toute couche générative → problème IR classique
  (méthodologie TREC, outillage standard).
- Pertinence **graduée**, jamais binaire (précisée par ADR-005).
- Contrat d'adapter unique : `requête → liste ordonnée d'IDs (+ scores)`.

## Alternatives rejetées

- **Évaluation end-to-end de la réponse générée** : mesure la prose du
  LLM, pas la qualité de récupération ; disparaît avec le LLM.
- **Pertinence binaire** : perd la distinction citable / support
  principal, essentielle en droit.

## Conséquences

- La récupération peut tourner et progresser sans qu'aucun LLM ne soit
  branché.
- L'adapter est l'interface P2→P3.

## Références

`VISION.md` §2 · ADR-005 · `PROGRAM.md` §2.2
