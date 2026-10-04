# Analyseurs OpenSearch

Les deux analyseurs de l'index OpenSearch (ADR-028 §5) : `fr_juridique` pour la langue
naturelle, `references` pour les références juridiques. L'ingestion les créera avec
l'index ; la question de l'utilisateur passe par les mêmes, au moment de la recherche.

Le mapping qui les emploie, et la requête qui les interroge, sont dans
[index-opensearch.md](index-opensearch.md).

Un analyseur enchaîne des filtres de caractères (`char_filter`), un tokenizer et des
filtres de jetons (`filter`). Un même texte est lu par les deux : « le code du travail et
l'article L. 1234-5 » donne `code` et `travail` à `fr_juridique`, `l1234-5` à
`references`. Deux textes se rejoignent quand ils produisent le même jeton : tout l'enjeu
de `references` est qu'une référence écrite de dix façons donne un seul jeton.

Les définitions et les mesures ci-dessous ont été vérifiées le 3 octobre 2026, sur le
corpus de dev (1 121 documents, dont 811 avec du texte), par l'API `_analyze`
d'OpenSearch 3.9.0.

## Les références du corpus

Relevé par expressions régulières sur le `content` des documents Mongo.

### Couvertes par `references`

| Famille | Formes relevées | Occurrences | Jeton |
|---|---|---|---|
| Article de code | `L. 861-1` (3 871), `R. 1143-1` (545), `L. 52-11-1`, `L.761-1`, `L6152-1`, `D. 3126-4`, `A. 243-1`, `D 24-21` | ≈ 4 900 | `l861-1` |
| … sans tiret | `L. 32`, `D. 591`, `A4` (article d'un règlement de PLU) | ≈ 350 | `l32` |
| … de loi organique | `L.O. 1112-1` ; titre `LO1112-1` | 9 | `lo1112-1` |
| … réglementaire en Conseil d'État | `R. * 222-19`, `R.* 771-16`, `R*196-1` | 9 | `r222-19` |
| Pourvoi en cassation | `n° 18-21.717`, `n° H 24-15.857` (lettre de la chambre), `08-12.742`, `n 08-12.742` ; métadonnée `numero_affaire` : `22-13330` | 295 | `18-21717` |
| Texte numéroté | `loi n° 86-1067`, `décret n°85-603`, `ordonnance n° 58-1136`, `loi organique n° 2001-692`, `arrêté n° 2024-01455`, `décret n° 2017 - 105` | 901 | `n°86-1067` |
| ECLI | `ECLI:FR:CCASS:2023:C300395`, `ECLI:FR:CECHR:2026:502302.20260612`, `ECLI:FR:CC:2026:2026.1206.QPC` | 7 dans le texte ; métadonnée `ecli` des décisions | `ecli:fr:ccass:2023:c300395` |

- **Le titre d'un article de code est déjà compact** : `L52-8`, `R1143-1`, `LO1112-1`. Les
  384 articles se répartissent en `L9-9` (196), `9` (100), `9-9` (31), `R9-9` (22), etc.
- **Le numéro d'un pourvoi perd son point dans les métadonnées** : `22-13.330` dans le
  titre, `22-13330` dans `numero_affaire`. Le jeton est la forme sans point.
- **Lois, ordonnances et décrets partagent une même numérotation annuelle** : le numéro
  seul désigne le texte, d'où un jeton sans la nature (`n°2004-374`). Un utilisateur qui
  écrit « loi 2004-374 » pour un décret le trouve quand même.

### Hors périmètre, pour l'instant

Relevées, mais sans motif dans `references`. `fr_juridique` les rattrape en partie.

| Famille | Exemple | Occurrences | Ce qui la trouve aujourd'hui |
|---|---|---|---|
| Article sans lettre (code civil, lois) | `article 34`, `Article 1er`, `article 21-1` | ≈ 4 400 | `fr_juridique` : `34`, ou `21` et `1`. Un nombre seul ne peut pas être une référence sans son contexte |
| Requête au Conseil d'État | `n° 502302`, `N° 501165` | ≈ 100 ; métadonnée `numero` (jade) | `fr_juridique` : `502302` |
| Requête de cour administrative d'appel | titre `25MA00274` | métadonnée `numero` (jade) | `fr_juridique` : `25ma00274`, un seul jeton |
| Décision du Conseil constitutionnel | `91-293 DC`, `2021-961 QPC` | 38 ; métadonnée `numero` (`2026-1206`) | `fr_juridique`, en deux jetons |
| Rôle de cour d'appel | `18/05246` | 7 ; métadonnée `numero_affaire` (capp) | `fr_juridique`, en deux jetons |
| Droit de l'Union | `directive 95/47/CE`, `règlement (UE) n° 1306/2013` | 151 | `fr_juridique`, en plusieurs jetons |
| NOR | `ECOI0120306A` | 0 dans le texte ; métadonnée `nor` | `fr_juridique` : un seul jeton |

## `references`

### Les jetons

| Famille | Jeton | Motif du jeton |
|---|---|---|
| Article de code | `l1234-5`, `lo1112-1`, `l32` | une lettre (`l`, `r`, `d`, `a`) ou `lo`, collée au numéro |
| Pourvoi | `21-12345` | 2 chiffres, tiret, 5 chiffres |
| Texte numéroté | `n°86-1067`, `n°2004-374` | `n°`, l'année sur 2 ou 4 chiffres, tiret, le numéro |
| ECLI | `ecli:fr:ccass:2023:c300395` | l'ECLI entier, en minuscules |

Un champ `.ref` ne contient que ces jetons : une phrase sans référence n'y produit rien.

### La chaîne

1. **`ordinal_degre`** remplace l'indicateur ordinal `º`, que certains claviers donnent
   pour `n°`, par le signe degré du corpus. `fr_juridique` le partage.
2. **`ref_pourvoi`** réduit un pourvoi à sa forme compacte, en retirant `n°` et la
   lettre de chambre : `n° H 24-15.857` devient `24-15857`. Il passe **avant les autres
   motifs** : sinon `ref_article` lirait `D 24-21` dans `n° D 24-21.811` comme un article.
3. **`ref_texte`** écrit `n°` devant le numéro d'un texte, qu'il suive une nature (`loi`,
   `décret`, `ordonnance`, `arrêté`, avec ou sans `organique`, avec ou sans `n°`) ou un
   `n°` seul : `loi 86-1067` comme `décret n° 2017 - 105` deviennent `n°86-1067`,
   `n°2017-105`. Le `n°` est le contexte qui distingue un numéro de texte d'un numéro
   d'article (`article 21-1`) ; les pourvois sont déjà réduits, sans `n°`.
4. **`ref_article_lo`** réduit `L.O.` à `LO`.
5. **`ref_article`** colle la lettre au numéro, en retirant le point, l'astérisque et les
   espaces : `R. * 222-19` devient `R222-19`.
6. **Le tokenizer `pattern`** (`group: 0`) n'émet que les formes compactes ; le reste du
   texte est ignoré.
7. **`lowercase`**.

**Le `n°` d'un utilisateur.** `ref_pourvoi` et `ref_texte` acceptent `n°`, `no`, `nos`
et un `n` seul, collé ou non au numéro : `loi n86-1067` et `n 86-1067` donnent
`n°86-1067`, `pourvoi n21-12.345` donne `21-12345`. Le `\b` qui précède le `n` l'empêche
de mordre sur la fin d'un mot : « un 12-3 » et « an 2004-374 » ne donnent aucun jeton.

Les filtres de caractères réécrivent librement le texte autour des références : seul ce
qu'émet le tokenizer compte.

**La casse.** Les motifs ignorent la casse : un utilisateur tape `l1234-5`. Le flag
`(?i)` de Java ne couvre que l'ASCII ; `ref_texte` porte `(?iu)` pour que `DÉCRET`
corresponde à `décret`, et `d[ée]cret`, `arr[êe]t[ée]` acceptent la saisie sans accents.
Seule exception : **un article sans tiret exige une lettre majuscule** dans le
tokenizer. Sinon « il y a 12 mois » donnerait le jeton `a12`.

### La définition

```json
{
  "analysis": {
    "char_filter": {
      "ordinal_degre": {
        "type": "mapping",
        "mappings": ["º => °"]
      },
      "ref_pourvoi": {
        "type": "pattern_replace",
        "pattern": "(?i)(?:\\bn[°o]?s?\\.?\\s*(?:[A-Z]\\s+)?|\\b[A-Z]\\s+|\\b)(\\d{2})-(\\d{2})\\.?(\\d{3})\\b",
        "replacement": "$1-$2$3"
      },
      "ref_texte": {
        "type": "pattern_replace",
        "pattern": "(?iu)(?:\\b(?:loi|d[ée]cret|ordonnance|arr[êe]t[ée])(?:\\s+organique)?\\s*(?:n[°o]?s?\\.?\\s*)?|\\bn[°o]?s?\\.?\\s*)(\\d{2,4})\\s*-\\s*(\\d{1,5})\\b",
        "replacement": "n°$1-$2"
      },
      "ref_article_lo": {
        "type": "pattern_replace",
        "pattern": "(?i)\\bL\\.?\\s*O\\.?\\s*(?=\\*?\\s*\\d)",
        "replacement": "LO"
      },
      "ref_article": {
        "type": "pattern_replace",
        "pattern": "(?i)\\b(LO|[LRDA])\\s*\\.?\\s*\\*?\\s*(\\d+(?:-\\d+)*)\\b",
        "replacement": "$1$2"
      }
    },
    "tokenizer": {
      "references": {
        "type": "pattern",
        "group": 0,
        "pattern": "(?i)\\bECLI:[A-Z]{2}:[A-Z]+:\\d{4}:[A-Z0-9]+(?:\\.[A-Z0-9]+)*|n°\\d{2,4}-\\d{1,5}\\b|\\b\\d{2}-\\d{5}\\b|\\b(?:LO|[LRDA])\\d+(?:-\\d+)+\\b|\\b(?-i:LO|[LRDA])\\d+\\b"
      }
    },
    "analyzer": {
      "references": {
        "type": "custom",
        "tokenizer": "references",
        "char_filter": ["ordinal_degre", "ref_pourvoi", "ref_texte", "ref_article_lo", "ref_article"],
        "filter": ["lowercase"]
      }
    }
  }
}
```

### Sur le corpus

Les 811 documents avec du texte donnent 6 509 jetons :

| Forme | Jetons | Exemple |
|---|---|---|
| `l9-9`, `l9-9-9`, `l9-9-9-9` | 4 164 | `l861-1`, `l4111-1-2` |
| `n°9-9` | 1 013 | `n°86-1067` |
| `r9-9`, `r9-9-9` | 622 | `r1143-1`, `r222-36-2` |
| `9-9` (pourvoi) | 294 | `22-13330` |
| `l9`, `d9`, `a9`, `r9`, `lo9` (sans tiret) | 358 | `l32`, `d591`, `a4` |
| `a9-9`, `d9-9`, `d9-9-9`, `lo9-9` | 50 | `a243-1`, `lo1112-1` |
| `ecli:…` | 7 | `ecli:fr:ccass:2014:co00501` |

### Limites connues

- **Du bruit sur les formes sans tiret** : la cote d'une pièce de procédure (« cote D
  1430 ») donne `d1430`, une mention « A1 » donne `a1`, un numéro d'arrêté préfectoral
  `R02-2024-11-18-00001` donne un jeton. Les retirer ferait perdre « article L. 32 » et
  « article D. 591 », bien plus nombreux.
- **Un numéro de décision du Conseil constitutionnel précédé de `n°`** (« décision n°
  2019-789 DC ») donne `n°2019-789`, comme un texte de même numéro.
- **Une plage n'est pas dépliée** : « L. 112-1 à L. 112-3 » donne `l112-1` et `l112-3`,
  pas `l112-2`. Une liste abrégée (« L. 861-1 et 2 ») perd ses éléments suivants.
- **Un titre d'article sans lettre** (`3`, `21-1`) ne donne aucun jeton : l'article n'est
  trouvé que par `fr_juridique` et par le titre de son texte (`parent_text_title`).
- **La métadonnée `num` d'un texte** (`86-1067`, sans `n°`) ne donne aucun jeton ; son
  titre (`Loi n° 86-1067 du …`) le porte.

## `fr_juridique`

Le filtre de caractères `ordinal_degre` (voir `references`), le tokenizer `standard`,
puis :

1. **`fr_elision`** retire `l'`, `d'`, `qu'`, `jusqu'`… avec l'apostrophe droite comme
   avec l'apostrophe typographique `’` du corpus.
2. **`lowercase`**.
3. **`fr_numero`** retire le `n` collé devant un nombre : `n1234` devient `1234`.
4. **`fr_stop`** retire les mots vides (`_french_`).
5. **`asciifolding`** retire les accents.
6. **`fr_stemmer`** (`light_french`) racinise.

**`n1234` et `n° 1234` donnent le même jeton.** Le tokenizer `standard` coupe au signe
`°` : `n° 1234` donne `n`, que la liste `_french_` retire, puis `1234`. Sans le `°`,
`n1234` reste un seul mot ; `fr_numero` le ramène à `1234`. La forme `n` + chiffres
n'apparaît nulle part dans le corpus : le filtre ne touche que la saisie des
utilisateurs. `ordinal_degre` fait de même pour `Nº 1234`, qui sinon garderait un jeton
`nº`.

**Les mots vides passent avant `asciifolding`**, alors que l'ADR-028 §5 cite
`asciifolding` d'abord. La liste `_french_` est accentuée : une fois les accents retirés,
« à » devient `a` et « où » devient `ou`, que la liste ne connaît plus. Sur « À défaut,
l’employeur a été condamné à payer à la salariée une indemnité ; où était-il ? », l'ordre
de l'ADR laisse trois jetons `a` de plus et `ou`.

```json
{
  "analysis": {
    "char_filter": {
      "ordinal_degre": { "type": "mapping", "mappings": ["º => °"] }
    },
    "filter": {
      "fr_elision": {
        "type": "elision",
        "articles_case": true,
        "articles": ["l", "m", "t", "qu", "n", "s", "j", "d", "c", "jusqu", "quoiqu", "lorsqu", "puisqu"]
      },
      "fr_numero": { "type": "pattern_replace", "pattern": "^n(\\d+)$", "replacement": "$1" },
      "fr_stop": { "type": "stop", "stopwords": "_french_" },
      "fr_stemmer": { "type": "stemmer", "language": "light_french" }
    },
    "analyzer": {
      "fr_juridique": {
        "type": "custom",
        "tokenizer": "standard",
        "char_filter": ["ordinal_degre"],
        "filter": ["fr_elision", "lowercase", "fr_numero", "fr_stop", "asciifolding", "fr_stemmer"]
      }
    }
  }
}
```

| Texte | Jetons |
|---|---|
| `l’employeur a licencié les salariés` | `employeu`, `a`, `licenc`, `sala` |
| `Les obligations contractuelles de l'État` | `oblig`, `contractuel`, `etat` |
| `l'article L. 1234-5 du code du travail` | `articl`, `1234`, `5`, `code`, `travail` |
| `pourvoi n° 21-12.345` | `pourvoi`, `21`, `12.345` |
| `25MA00274` | `25ma00274` |
| `n1234` · `N1234` · `n°1234` · `nº1234` · `Nº 1234` · `n 1234` | `1234` |
| `décision n516908` | `decision`, `516908` |
| `loi n86-1067` · `loi n° 86-1067` | `loi`, `86`, `1067` |
| `1º de l'article` | `1`, `articl` |
| `rn1234` · `n1234a` | `rn1234` · `n1234a` |

Le tokenizer `standard` coupe une référence au tiret (`l1234`, `5`) : c'est la raison
d'être de `references`.

## Vérifier un analyseur

Dans les Dashboards (`http://localhost:5601`), Dev Tools. L'index de l'ingestion
(`OPENSEARCH_INDEX`, `documents` en dev) porte les deux analyseurs :

```
POST documents/_analyze
{ "analyzer": "references", "text": "pourvoi n° H 24-15.857 et article L. 1234-5" }
```

Les cas vérifiés, tous conformes ; ceux de `fr_juridique` sont dans sa section :

| Entrée | Jetons `references` |
|---|---|
| `aux articles L. 861-1 et R. 1143-1 du code` | `l861-1`, `r1143-1` |
| `L.O. 1112-1` · `lo 1112-1` · `LO1112-1` | `lo1112-1` |
| `R. * 222-19` · `R*196-1` | `r222-19` · `r196-1` |
| `art. L1234-5` · `art L 1234-5` · `l. 1234-5` · `L.1234-5` · `l1234-5` | `l1234-5` |
| `pourvoi n° 18-21.717` · `n° H 24-15.857` · `08-12.742` | `18-21717` · `24-15857` · `08-12742` |
| `pourvoi 21-12345` · `Y 21-12.345` · `nº 21-12.345` · `pourvoi n21-12.345` | `21-12345` |
| `pourvoi n 08-12.742` · `Pourvoi n° N 25-11.726` · `nº H 24-15.857` | `08-12742` · `25-11726` · `24-15857` |
| `Cour de cassation, 8 juin 2023, 22-13.330, Publié` · `22-13330` | `22-13330` |
| `loi n° 86-1067` · `loi 86-1067` · `loi no 86-1067` · `loi n86-1067` · `loi n 86-1067` · `n86-1067` · `Nº 86-1067` | `n°86-1067` |
| `Décret n°2004-374 du 29 avril 2004` · `décret 2004-374` · `Decret 2004-374` · `DÉCRET 2004-374` | `n°2004-374` |
| `Loi organique n° 2010-837` · `décret n° 2017 - 105` · `arrete n° 2024-01455` | `n°2010-837` · `n°2017-105` · `n°2024-01455` |
| `ECLI:FR:CECHR:2026:502302.20260612.` (point final) | `ecli:fr:cechr:2026:502302.20260612` |
| `ecli:fr:ccass:2023:c300395` | `ecli:fr:ccass:2023:c300395` |
| `le code du travail et l'article L1234-5` | `l1234-5` |
| `quelles sont les conditions du licenciement pour faute grave ?` | — |
| `article 1240 du code civil` · `l'article 21-1 de la loi` | — |
| `il y a 12 mois, le 12-3` · `du 29 avril 2004` · `un 12-3` · `an 2004-374` · `n1234` | — |
| `catégorie A1` · `cote D 1430` (bruit accepté) | `a1` · `d1430` |
