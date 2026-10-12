# ADR-007 — Découplage récupération / génération

**Statut** : rétro-documenté (décision implicite antérieure au 17 juillet 2026) ·
**amendé par [ADR-028](ADR-028-opensearch-remplace-qdrant.md)** (la génération est retirée)
· **amendé par [ADR-033](ADR-033-onglet-explications.md)** (un LLM revient, borné aux documents choisis)

> **Amendement par ADR-028 (2 octobre 2026).** L'échafaudage est retiré : Murphy
> devient un moteur de recherche, sans LLM. Le contrat de la récupération devient
> `requête → liste ordonnée de documents (+ scores RRF) et leurs passages`. Le retrait
> se fait à l'étape 2 de la migration vers OpenSearch.
>
> **Amendement par ADR-033 (12 octobre 2026).** Un LLM revient, dans l'onglet
> Explications : il résume et explique les documents que l'utilisateur a choisis, sans
> chercher lui-même ni qualifier une situation. La récupération reste un composant
> autonome dans le code, mais le backend ne démarre plus sans la configuration du LLM.

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
