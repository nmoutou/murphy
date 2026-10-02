# ADR-010 — Architecture tri-base + serving stateless/fail-fast

**Statut** : rétro-documenté (décision implicite antérieure au 17 juillet 2026) ·
**amendé par [ADR-028](ADR-028-opensearch-remplace-qdrant.md)** (OpenSearch remplace
Qdrant ; le LLM est retiré)

> **Amendement par ADR-028 (2 octobre 2026).** Qdrant ne faisait qu'une recherche
> vectorielle : OpenSearch le remplace et porte la recherche hybride (BM25 et
> vecteurs). Le LLM est retiré : le fail-fast vaut pour le pipeline de recherche, et
> « stateless » couvre aussi la pagination, chaque page recalculant tout. La décision
> ci-dessous décrit la répartition après cet amendement.

## Contexte

Le socle data doit servir la recherche hybride, le graphe de citations
et le texte intégral ; l'applicatif doit respecter l'invariant de
confidentialité structurelle.

## Décision

**Tri-base** :

- **MongoDB** : texte intégral brut.
- **Neo4j** : nœuds/arêtes typés — **références, pas de texte**.
- **OpenSearch** : embeddings + métadonnées, recherche hybride ; le texte y est
  indexé, pas stocké (ADR-028).

**Serving** : **stateless** (aucun historique serveur, seule la dernière
question compte, aucun état entre deux pages), **fail-fast** (pas de
retry ni de fallback, erreur claire), **aucune analyse du contenu** des requêtes.

## Alternatives rejetées

- **Base unique polyvalente** : aucun des trois moteurs ne couvre
  correctement les trois usages.
- **Texte dans Neo4j** : duplication, dérive de synchronisation.
- **Retry/fallback silencieux** : réponse dégradée non signalée,
  contraire au respect de l'usager.

## Conséquences

- L'identité canonique inter-BDD (ADR-008) devient l'invariant bloquant
  du socle.
- La confidentialité est structurelle, pas une option de configuration.

## Références

ADR-008 · ADR-028
