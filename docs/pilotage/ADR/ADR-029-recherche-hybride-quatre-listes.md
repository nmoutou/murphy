# ADR-029 — Recherche hybride : une liste de références et un vecteur de titre

**Statut** : ✅ Accepté (4 octobre 2026) — amende ADR-028 §2 et §6

## Contexte

ADR-028 §6 fusionne par RRF deux sous-requêtes : une lexicale, une vectorielle. Le
mapping de l'ADR-028 a été essayé sur tout le corpus de dev (1 121 documents, 18 023
passages) avant la migration de l'ingestion et du backend.

Le mapping tient. Le classement, non : **un document trouvé par une seule des deux
listes ne remonte pas.** RRF additionne `1 / (60 + rang)` sur les listes où un document
apparaît : un document au rang 10 des deux listes (2/70 ≈ 0,029) passe devant un
document premier d'une seule (1/61 ≈ 0,016). Deux familles de documents en pâtissent :

- **Les références exactes.** L'embedding ne « voit » pas un numéro : la décision du
  pourvoi `22-13330`, première de la liste lexicale, n'est pas dans les 50 premiers
  documents de la liste vectorielle. Sur quatre questions de référence (« article L52-8
  du code électoral », « article 3 du décret 2005-850 », « 22-13330 », « pourvoi n°
  22-13.330 »), une seule trouve sa cible dans le top 10.
- **Les sections.** Sans texte, elles n'ont pas de passage, donc pas de vecteur (ADR-028
  §2). Trois sections cherchées par les mots de leur titre restent hors du top 10.

## Décision

### 1. Une sous-requête « références »

La requête `hybrid` gagne une sous-requête qui lit les mêmes champs que la lexicale, mais
seulement par l'analyseur `references` : `passages.text.ref` (un `nested`, en
`score_mode: max`), `title.ref`, `parent_text_title.ref` et `metadata.*.ref`.

Le document qui porte une référence de la question est alors en tête de deux listes, la
lexicale et celle-ci. Une question sans référence ne produit aucun jeton `references` :
la liste est vide et le classement ne change pas. Aucun poids n'est à régler.

Ses passages sont déjà trouvés par la sous-requête lexicale, qui lit aussi
`passages.text.ref` : elle n'a pas d'`inner_hits`, et ADR-028 §7 ne change pas.

### 2. Un vecteur de titre pour les documents sans passage

Le mapping gagne `title_embedding`, un `knn_vector` comme `passages.embedding`, rempli
**pour les seuls documents sans passage** (les sections, les textes au `content` vide).
L'ingestion le demande à TEI. La requête `hybrid` gagne une sous-requête kNN sur ce
champ.

Les autres documents n'ont pas de vecteur de titre : celui d'une décision (« CAA de
PARIS, 5ème chambre, 19/06/2026, 25PA05132 ») ou d'un article (« L52-8 ») n'a pas de
sens pour un embedding.

### 3. Quatre sous-requêtes

La requête `hybrid` compte donc quatre sous-requêtes, fusionnées par RRF : lexicale,
références, vectorielle sur les passages, vectorielle sur les titres. Le `k` de chaque
kNN vaut `PAGINATION_DEPTH`. La requête complète et son mapping sont décrits dans
`docs/technical/data/reference/index-opensearch.md`.

### Mesures

Rang des documents attendus dans le top 10, sur le corpus de dev :

| Question | RRF à 2 listes | 4 listes |
|---|---|---|
| `article L52-8 du code électoral` (5 versions) | absentes | 3, 7, 8, 10 |
| `article 3 du décret 2005-850` | absent | 6 |
| `22-13330` | absent | 1 |
| `pourvoi n° 22-13.330` | 1 | 1 |
| 3 sections, par les mots de leur titre | absentes | 1, 1, 1 |

Sur quatre questions en langue naturelle, le top 10 garde 10, 10, 9 et 9 documents de
celui à deux listes.

## Alternatives rejetées

- **Un RRF pondéré** (0,7 pour la liste lexicale, 0,3 pour la vectorielle). Résultat
  partiel (le pourvoi seul au rang 5, une section au rang 7, ni `L52-8` ni l'article 3),
  et un poids à régler sans méthode d'évaluation (ADR-028 §6).
- **Un vecteur de titre pour tous les documents.** Les sections remontent (rangs 1, 1 et
  9), mais le top 10 des questions en langue naturelle ne garde que 10, 6, 9 et 6
  documents de celui à deux listes : les titres de décisions et d'articles ajoutent une
  liste de bruit à chaque question.
- **Garder deux listes** et reporter le problème : la recherche de références exactes est
  la raison même de la recherche lexicale (ADR-028, contexte).

## Conséquences

- **Mapping** : `title_embedding` s'ajoute ; il change avec le modèle d'embedding, comme
  `passages.embedding`.
- **Ingestion** : un appel à TEI de plus par document sans passage (310 sur le corpus de
  dev).
- **Backend** : la requête compte quatre sous-requêtes (le plafond d'une requête
  `hybrid` est de cinq). Mesurée à 55 ms en médiane sur le corpus de dev.
- La limite reportée de l'ADR-028 sur les sections sans vecteur est levée.

## Références

ADR-028 (OpenSearch, recherche hybride) · ADR-015 (contrat ingestion ↔ serving) ·
`docs/technical/data/reference/index-opensearch.md` ·
`docs/technical/data/reference/analyseurs.md`
