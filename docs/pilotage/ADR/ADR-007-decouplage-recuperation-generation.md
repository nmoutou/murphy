# ADR-007 — Découplage récupération / génération

**Statut** : rétro-documenté (décision implicite antérieure au 17 juillet 2026)

## Contexte

Murphy repose sur un invariant de vision : **sourcer, ne pas
raisonner**. La génération LLM est un échafaudage transitoire, destiné à
être retiré.

## Décision

- La **récupération est un composant autonome**, indépendant de toute
  couche générative.
- Contrat unique : `requête → liste ordonnée d'IDs (+ scores)`.

## Conséquences

- La récupération peut tourner et progresser sans qu'aucun LLM ne soit
  branché.

## Références

ADR-015
