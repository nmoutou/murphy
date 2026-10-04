# Index OpenSearch

L'index OpenSearch qui porte la recherche (ADR-028, ADR-029) : ses réglages, son mapping,
et la requête hybride qu'il doit servir. Les analyseurs `fr_juridique` et `references`
sont décrits à part, dans [analyseurs.md](analyseurs.md). L'ingestion créera l'index ; le
backend l'interrogera.

Le mapping et la requête ont été vérifiés le 4 octobre 2026 sur tout le corpus de dev
(1 121 documents, 18 023 passages), avec OpenSearch 3.9.0 et `all-mpnet-base-v2`.

## Un document par document Mongo

Chaque document Mongo devient un document OpenSearch, d'`_id` son `identifier`. Ses
passages (les chunks) y sont imbriqués, dans un champ `nested` : un passage trouvé
désigne toujours son document, sans regroupement à faire.

**Le texte est indexé, pas stocké.** `_source` exclut le texte et les vecteurs des
passages : Mongo reste le seul stockage du texte (ADR-015). Un document renvoyé porte les
offsets de ses passages (`chunk_id`, `char_start`, `char_end`), pas leur texte. En
contrepartie, ni `_reindex` ni mise à jour partielle ne sont possibles : elles relisent
`_source` et perdraient le texte et les vecteurs. **Un changement du mapping, des
analyseurs, du chunking ou du modèle d'embedding passe par une réingestion complète.**

Sur le corpus de dev, 310 documents n'ont aucun passage : les 287 sections, nœuds de
structure sans texte, et 23 textes dont le `content` est vide.

## Les réglages

```json
{
  "settings": {
    "index": { "knn": true, "number_of_shards": 1, "number_of_replicas": 0 }
  }
}
```

`settings.analysis` reçoit les définitions d'[analyseurs.md](analyseurs.md), fusionnées.

- **`index.knn`** active les champs `knn_vector`.
- **Une shard, aucune réplique** : en nœud unique, une réplique ne trouve aucun nœud où
  s'allouer, et l'index reste jaune. Un cluster de prod réglera les répliques.
- **Pendant une ingestion**, `refresh_interval: -1` suspend la publication des segments ;
  un `_refresh` final, puis le retour à la valeur par défaut, rendent l'index cherchable.
  Le corpus de dev se charge ainsi en une trentaine de secondes.

## Le mapping

```json
{
  "mappings": {
    "dynamic": "strict",
    "date_detection": false,
    "_source": { "excludes": ["passages.text", "passages.embedding"] },
    "dynamic_templates": [
      { "metadata_dates": {
          "path_match": "metadata.date_*",
          "mapping": { "type": "date", "format": "strict_date" } } },
      { "metadata_derniere_modification": {
          "path_match": "metadata.derniere_modification",
          "mapping": { "type": "date", "format": "strict_date" } } },
      { "metadata_versions_a_venir": {
          "path_match": "metadata.versions_a_venir",
          "mapping": { "type": "date", "format": "strict_date" } } },
      { "metadata_chaines": {
          "path_match": "metadata.*",
          "match_mapping_type": "string",
          "mapping": {
            "type": "keyword", "ignore_above": 1024,
            "fields": {
              "texte": { "type": "text", "analyzer": "fr_juridique" },
              "ref": { "type": "text", "analyzer": "references" } } } } }
    ],
    "properties": {
      "identifier": { "type": "keyword" },
      "document_type": { "type": "keyword" },
      "nature": { "type": "keyword" },
      "title": {
        "type": "keyword", "ignore_above": 1024,
        "fields": {
          "texte": { "type": "text", "analyzer": "fr_juridique" },
          "ref": { "type": "text", "analyzer": "references" } } },
      "parent_text_title": {
        "type": "text", "analyzer": "fr_juridique",
        "fields": { "ref": { "type": "text", "analyzer": "references" } } },
      "title_embedding": {
        "type": "knn_vector", "dimension": 768,
        "method": { "name": "hnsw", "engine": "faiss", "space_type": "cosinesimil" } },
      "metadata": { "type": "object", "dynamic": true },
      "passages": {
        "type": "nested",
        "properties": {
          "chunk_id": { "type": "keyword" },
          "char_start": { "type": "integer" },
          "char_end": { "type": "integer" },
          "text": {
            "type": "text", "analyzer": "fr_juridique",
            "fields": { "ref": { "type": "text", "analyzer": "references" } } },
          "embedding": {
            "type": "knn_vector", "dimension": 768,
            "method": { "name": "hnsw", "engine": "faiss", "space_type": "cosinesimil" } } } }
    }
  }
}
```

| Champ | Type | Contenu |
|---|---|---|
| `identifier` | `keyword` | La clé du document dans Mongo, aussi son `_id` |
| `document_type`, `nature` | `keyword` | Le typage (ADR-022) |
| `title` | `keyword` + `.texte` + `.ref` | Le titre ; celui d'un article est son numéro (`L52-8`, `3`) |
| `parent_text_title` | `text` + `.ref` | Articles et sections : les titres du texte qui les contient |
| `title_embedding` | `knn_vector` | Le vecteur du titre, pour un document sans passage seulement (ADR-029) |
| `metadata.*` | dynamic templates | Les métadonnées, typées clé par clé |
| `passages.chunk_id` | `keyword` | L'identité du passage |
| `passages.char_start`, `passages.char_end` | `integer` | Ses bornes dans `content`, en points de code (ADR-015) |
| `passages.text` | `text` + `.ref` | Son texte : indexé, non stocké |
| `passages.embedding` | `knn_vector` | Son vecteur : indexé, non stocké |

- **`dynamic: strict`** : un champ inconnu fait échouer l'écriture du document. Seul
  `metadata` accepte des clés nouvelles.
- **Les vecteurs** : 768 dimensions, celles d'`all-mpnet-base-v2`. L'ingestion demandera
  la dimension à TEI, comme pour Qdrant aujourd'hui. Moteur `faiss` (le défaut d'OpenSearch
  3.x ; `nmslib` est déprécié), graphe HNSW, similarité cosinus.

### Les métadonnées

`metadata` reste un dictionnaire plat dans le modèle de l'ingestion ; les dynamic
templates typent chaque clé à sa première apparition, d'après son nom, jamais d'après sa
valeur (`date_detection: false`). Le premier template qui correspond l'emporte : les
trois templates de dates passent avant celui des chaînes.

- **Les dates** (`date_*`, `derniere_modification`, `versions_a_venir`) sont des `date`
  au format `strict_date` (`AAAA-MM-JJ`). Une date mal formée fait échouer l'écriture du
  document, donc sa saga. Les sentinelles de la DILA (`2999-01-01` en `date_fin`,
  `2222-02-22` en `versions_a_venir`) sont des dates valides.
- **Toute autre chaîne** est un `keyword` (égalité, filtres, agrégations), avec
  `.texte` et `.ref` pour la recherche.
- **`ignore_above: 1024`** : une valeur de plus de 1 024 caractères n'est pas indexée
  comme `keyword`, mais reste cherchable par `.texte` et `.ref`, et le document est
  écrit. Sans lui, une valeur de plus de 32 766 octets, possible depuis une balise non
  configurée (ADR-023), rejetterait le document entier. La plus longue valeur du corpus
  de dev fait 418 caractères (`titre_full`).
- **Une liste** (`numero_affaire`, `versions_a_venir`, ADR-025) s'indexe comme ses
  éléments : tout champ accepte un tableau.

Sur le corpus de dev, les 38 clés donnent 8 champs `date` et 30 `keyword`, soit 98 champs
avec leurs sous-champs ; avec le reste du mapping, 115. La limite par défaut
(`index.mapping.total_fields.limit`, 1 000) laisse de la marge : les clés viennent du
vocabulaire fini de la DILA, et leur nombre croît avec les sources, pas avec les données.

### `parent_text_title`

Le titre du texte qui contient un article ou une section : dans « l'article 3 du décret
2005-850 », il départage les « 3 » de tous les textes. Il ne vit que dans l'index : ni
Mongo ni le contrat du flux ne le portent.

Il se lit dans le XML du document, sous `<CONTEXTE>/<TEXTE>/<TITRE_TXT>`, que l'ingestion
parcourt déjà pour la relation `contient`. Le XML donne un titre par période, souvent
deux formes du même titre :

```
Décret n° 2005-850 du 27 juillet 2005  relatif aux délégations de signature des membres du Gouvernement
Décret n°2005-850 du 27 juillet 2005 relatif aux délégations de signature des membres du Gouvernement.
```

Le champ les reçoit tous, sans doublon et les espaces normalisés. Sur le corpus de dev,
les 384 articles et 287 sections en ont au moins un. Neo4j ne suffirait pas : il ne garde
pas le titre d'un texte absent du corpus.

### `title_embedding`

Le vecteur du titre, **pour les seuls documents sans passage** (ADR-029) : sans lui, une
section n'est trouvée que par la recherche lexicale, et la fusion RRF la relègue derrière
les documents trouvés par les deux recherches. Il n'est pas calculé pour les autres : le
titre d'une décision (« CAA de PARIS, 5ème chambre, 19/06/2026, 25PA05132 ») ou d'un
article (« L52-8 ») n'a pas de sens pour un embedding, et ces vecteurs perturbaient le
classement des questions en langue naturelle (voir [Vérification](#vérification)).

## La requête

La recherche est une requête `hybrid` à quatre sous-requêtes (ADR-028 §6, amendé par
ADR-029), fusionnées par RRF :

1. **lexicale** : un `nested` sur `passages.text` et `passages.text.ref` en
   `score_mode: max`, avec ses `inner_hits`, plus un `multi_match` sur `title.texte`,
   `title.ref`, `parent_text_title`, `parent_text_title.ref`, `metadata.*.texte` et
   `metadata.*.ref` ;
2. **références** : les mêmes champs, en ne gardant que ceux de l'analyseur `references`
   (`.ref`). Une question sans référence n'y produit aucun jeton, et cette liste est
   vide ;
3. **vectorielle sur les passages** : un `nested` kNN sur `passages.embedding`, avec
   `expand_nested_docs` et ses `inner_hits` (les 3 passages les plus proches) ;
4. **vectorielle sur les titres** : un kNN sur `title_embedding`.

Le pipeline de recherche, que le backend créera au boot :

```
PUT _search/pipeline/<nom>
{ "phase_results_processors": [
    { "score-ranker-processor": { "combination": { "technique": "rrf" } } } ] }
```

La requête, pour une question `Q` de vecteur `V` :

```json
{
  "from": 0, "size": 10,
  "query": { "hybrid": {
    "pagination_depth": 50,
    "queries": [
      { "bool": { "should": [
        { "nested": {
            "path": "passages", "score_mode": "max",
            "query": { "multi_match": { "query": "Q", "fields": ["passages.text", "passages.text.ref"] } },
            "inner_hits": { "name": "lexical", "size": 100,
                            "_source": ["passages.chunk_id", "passages.char_start", "passages.char_end"] } } },
        { "multi_match": { "query": "Q", "fields": [
            "title.texte", "title.ref", "parent_text_title", "parent_text_title.ref",
            "metadata.*.texte", "metadata.*.ref"] } } ] } },
      { "bool": { "should": [
        { "nested": {
            "path": "passages", "score_mode": "max",
            "query": { "match": { "passages.text.ref": "Q" } } } },
        { "multi_match": { "query": "Q", "fields": ["title.ref", "parent_text_title.ref", "metadata.*.ref"] } } ] } },
      { "nested": {
          "path": "passages", "score_mode": "max",
          "query": { "knn": { "passages.embedding": { "vector": "V", "k": 50, "expand_nested_docs": true } } },
          "inner_hits": { "name": "vectoriel",
                          "_source": ["passages.chunk_id", "passages.char_start", "passages.char_end"] } } },
      { "knn": { "title_embedding": { "vector": "V", "k": 50 } } }
    ] } }
}
```

- **`k` vaut `pagination_depth`** : chaque sous-requête rend au plus autant de documents.
  Dans un `nested` kNN, `k` compte des documents, pas des passages.
- **La liste « références » n'a pas d'`inner_hits`** : ses passages sont aussi trouvés
  par la sous-requête lexicale, qui lit déjà `passages.text.ref`. Les passages d'un
  document trouvé restent ceux de l'ADR-028 §7 : lexicaux et vectoriels.
- **`_source`** d'un résultat porte les offsets de tous ses passages : un document trouvé
  par son titre ou ses métadonnées est renvoyé avec tous ses passages (ADR-028 §7).

## Vérification

Le corpus de dev a été chargé par un script jetable : les documents depuis Mongo, les
passages et leurs vecteurs depuis Qdrant, `parent_text_title` depuis le XML, les vecteurs
de titre depuis TEI. Aucun document n'a été rejeté ; l'index compte 1 121 documents et
18 023 passages, autant que de points Qdrant.

Le rang des documents attendus dans le top 10 :

| Question | Attendu | RRF à 2 listes (ADR-028) | 3 listes (+ références) | 4 listes (+ titres) |
|---|---|---|---|---|
| `article L52-8 du code électoral` | les 5 versions de `L52-8` | absentes | 2, 6, 7, 9, 10 | 3, 7, 8, 10 |
| `article 3 du décret 2005-850` | `LEGIARTI000045938851` (titre « 3 ») | absent | 6 | 6 |
| `22-13330` | la décision du pourvoi | absente | 1 | 1 |
| `pourvoi n° 22-13.330` | la même | 1 | 1 | 1 |
| `affectations de recettes` | la section « Chapitre III : Des affectations de recettes. » | absente | absente | 1 |
| `le projet de loi de finances de l'année` | la section « Chapitre Ier : Du projet de loi de finances… » | absente | absente | 1 |
| `les ressources et les charges de l'État` | la section « TITRE II : DES RESSOURCES ET DES CHARGES DE L'ETAT. » | absente | absente | 1 |

**Pourquoi RRF à deux listes perdait les références.** La sous-requête lexicale classait
bien les cibles (`22-13330` au rang 1, les `L52-8` aux rangs 3 à 8), mais l'embedding ne
« voit » pas un numéro : aucune n'entrait dans les 50 premiers documents de la liste
vectorielle. RRF additionne `1 / (60 + rang)` sur les listes où un document apparaît :
un document présent dans les deux listes au rang 10 (2/70 ≈ 0,029) passe devant un
document premier d'une seule liste (1/61 ≈ 0,016). La liste « références » donne au
document qui porte la référence une deuxième première place ; le vecteur de titre fait de
même pour une section.

**Les questions en langue naturelle ne changent presque pas.** Sur « conditions du
licenciement pour faute grave du salarié », « délégation de signature des membres du
Gouvernement », « financement des campagnes électorales par une personne morale » et
« permis de construire refusé par le maire », le top 10 à quatre listes garde 10, 10, 9 et
9 documents de celui à deux listes. Avec un vecteur de titre pour **tous** les documents,
il n'en gardait que 10, 6, 9 et 6 : d'où la restriction aux documents sans passage.

Une requête prend 55 ms en médiane (62 au plus), sur 11 questions. La pagination est
cohérente : à profondeur égale, la page `from: 10` prolonge la page `from: 0` sans
recouvrement. Aucun index `top_queries-*` n'apparaît : Query Insights est désactivé.

### Limites connues

- **Le bruit lexical** : les mots fréquents d'une question (`article`, `3`) suffisent à
  faire correspondre presque tout le corpus (1 059 documents sur 1 121 pour « article
  L52-8 du code électoral »). Le classement n'en souffre pas sur les cas mesurés, mais la
  liste lexicale est longue.
- **Beaucoup de passages lexicaux par document** : une décision en renvoie jusqu'à 69 pour
  « article 3 du décret 2005-850 ». Tant que le LLM reste branché (étape 1 de l'ADR-028), ils
  partent tous dans son contexte.
- **Les versions d'un article remontent toutes** (les 5 `L52-8`) : un filtre sur
  `metadata.statut` reste à décider (ADR-028).

## Vérifier l'index

L'index d'essai `documents-essai` est consultable dans les Dashboards
(`http://localhost:5601`, Dev Tools) :

```
GET documents-essai/_mapping
GET documents-essai/_search
{ "query": { "term": { "title": "L52-8" } }, "_source": ["title", "parent_text_title", "passages"] }
```
