# ADR-020 — Architecture tri-base + P3 stateless/fail-fast

**Statut** : rétro-documenté (décision implicite antérieure au chantier 4)

## Contexte

Le socle data doit servir la recherche hybride, le graphe de citations
et le texte intégral ; l'applicatif doit respecter l'invariant de
confidentialité structurelle.

## Décision

**Tri-base** :

- **MongoDB** : texte intégral brut.
- **Neo4j** : nœuds/arêtes typés — **références, pas de texte**.
- **Qdrant** : embeddings + métadonnées, recherche hybride.

**P3** : **stateless** (aucun historique serveur, seule la dernière
question compte), **fail-fast** (pas de retry/fallback LLM, erreur
claire), **aucune analyse du contenu** des requêtes.

## Alternatives rejetées

- **Base unique polyvalente** : aucun des trois moteurs ne couvre
  correctement les trois usages.
- **Texte dans Neo4j** : duplication, dérive de synchronisation.
- **Retry/fallback silencieux** : réponse dégradée non signalée,
  contraire au respect de l'usager.

## Conséquences

- L'identité canonique inter-BDD (ADR-018) devient l'invariant bloquant
  du socle.
- La confidentialité est structurelle, pas une option de configuration.

## Références

`VISION.md` §2 · ADR-018 · `STATUS.md`
