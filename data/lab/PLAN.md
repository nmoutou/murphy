# Plan de travail — Analyse exploratoire des bases de jurisprudence

> Espace de travail exploratoire (`lab/`). **Objectif : comprendre, pas ingérer.**
> Ce document fige les objectifs et la méthode. Il précède toute écriture de code.

## Finalité

Faire la **rétro-ingénierie du modèle de données implicite** des bases de
jurisprudence LEGIFRANCE, afin de comprendre *comment la réalité a été
représentée* — et, à terme, décider d'un **schéma de persistance ACID** propre.

Ce n'est pas de l'analyse de données au sens « stats descriptives » : c'est
reconstruire le modèle que LEGIFRANCE a utilisé pour encoder la jurisprudence.

Principe directeur : **la structure d'abord, les valeurs ensuite.**

## Périmètre

5 bases de jurisprudence (XML LEGIFRANCE). **LEGI (droit positif) est exclu.**

| Base    | Juridiction                         | Branche méta spécifique |
|---------|-------------------------------------|-------------------------|
| CASS    | Cour de cassation                   | `META_JURI_JUDI`        |
| INCA    | Cassation — inédits anciens         | `META_JURI_JUDI`        |
| CAPP    | Cours d'appel                       | `META_JURI_JUDI`        |
| JADE    | Juridictions administratives (CE)   | `META_JURI_ADMIN`       |
| CONSTIT | Conseil constitutionnel             | `META_JURI_CONSTIT`     |

Toutes partagent un **tronc commun** (`META_COMMUN`, `META_SPEC`,
`BLOC_TEXTUEL`, `TEXTE`, `TITRE`, `DATE_DEC`, `SOLUTION`…) et une **branche
spécialisée** par ordre de juridiction.

- **Données** : `/mnt/data/Murphy/src/{CAPP,CASS,CONSTIT,INCA,JADE}/`
- **Démarrage** : échantillon actuel (~350 fichiers). On scalera ensuite.
- **Stack** : Python — `pandas` + `lxml` + Jupyter.

## Deux échelles de comparaison

1. **Inter-bases** : CASS vs JADE vs CONSTIT… (tronc commun vs spécifique).
2. **Intra-base** : ex. chambre criminelle vs sociale au sein de CASS.

→ Conséquence : dès le parsing, **capturer la provenance** de chaque fichier
(base + partition, déductible du chemin `…/global/criminelle/…`). La provenance
est une dimension d'analyse à part entière.

## Structure de données centrale — l'arbre de stats

La Phase 1 produit, **par base**, un **arbre de stats récursif** qui épouse la
hiérarchie XML. Chaque nœud a la même forme :

```json
{
  "name": "AVOCAT",
  "nb_fichiers_present": 40,
  "occ_total": 153,
  "count_par_fichier": { "min": 1, "max": 6, "avg": 3.8, "std": 1.4 },
  "depth": 6,
  "children": [ /* nœuds de même forme */ ]
}
```

Règles :
- **Fusion par nom** : une balise répétée sous le même parent (ex. plusieurs
  `AVOCAT` sous `AVOCATS`) = **un seul nœud**, la répétition étant capturée par
  les compteurs — pas un nœud par occurrence.
- **`count_par_fichier`** = distribution du nombre d'occurrences par fichier *où
  la balise est présente* (`min`, `max`, `avg`, `std`).
- **À ce stade, on ignore les valeurs** : on ne collecte que noms, imbrication,
  profondeur, cardinalité.

Pourquoi cet arbre (et pas un dict plat indexé par chemin) :
- il **est** le schéma — fidèle à la réalité représentée, sans aplatissement
  prématuré (l'aplatissement est une décision de modélisation, repoussée en P2) ;
- sérialisable en JSON, visualisable comme un arbre ;
- la comparaison de bases = **diff de deux arbres** (nœuds communs vs branches
  propres) ;
- la cardinalité 0/1/N se lit **localement** sur chaque nœud.

### Lecture de la cardinalité (→ décisions de modélisation)

| Signature                          | Interprétation             | Implication ACID            |
|------------------------------------|----------------------------|-----------------------------|
| `min=1, max=1, std=0`              | obligatoire & unique       | attribut simple / clé       |
| `min=0, max=1`                     | optionnel unique           | colonne nullable            |
| `max>1, std>0`                     | **multivalué**             | **table fille candidate**   |

## Découpage en phases

### Phase 0 — Infra du lab
Parseur XML→arbre qui capture **provenance** (base + partition depuis le chemin)
et **structure** (chemins complets, sans valeurs). Squelette de notebooks.

### Phase 1 — STRUCTURE
1. **Arbre des balises par base** (paths, profondeur) — le squelette.
2. **Cardinalité 0/1/N par parent** → repère les **multivalués**.
3. **Matrices présence/absence** : balise × base **et** balise × partition.
4. **Schéma reconstruit** par base + tronc commun vs spécifique.

### Phase 2 — VALEURS *(après avoir figé une méthode d'aplatissement)*
5. Remplissage, cardinalité des valeurs, distributions catégorielles, formats.
6. Qualité & cohérence (clés candidates, doublons, dates).
7. Relations (`LIENS`, `CITATION_JP`, `LOI_DEF`) → aperçu graphe.

### Phase 3 — SYNTHÈSE MODÉLISATION
8. Document « du schéma source au modèle ACID » :
   - **entité atomique** (1 décision = 1 fichier = 1 ligne ? ou éclatement ?) ;
   - **multivalués** → tables filles ;
   - **commun vs spécialisé** → table creuse unique vs héritage ;
   - **clé primaire** candidate parmi `ID` / `ANCIEN_ID` / `ECLI` / `NUMERO`.

## Questions de modélisation que l'exploration doit trancher

- Quelle est l'**entité atomique** ?
- Qu'est-ce qui est **multivalué** (→ table fille) ?
- Qu'est-ce qui est **commun vs spécialisé** par ordre de juridiction ?
- Quel identifiant est une **clé primaire stable et fiable** ?
