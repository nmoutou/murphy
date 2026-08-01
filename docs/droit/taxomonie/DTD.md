# Taxonomie du droit français — inventaire des DTD DILA

> **Compagnon de [SOURCES.md](SOURCES.md).** Là où le registre des sources
> recense *où trouver* la matière, ce document descend d'un cran : il lit les
> **DTD réelles** publiées par la DILA pour établir, base par base, **quels
> champs de classification le XML porte nativement** — donc ce que le corpus
> pourra dire de lui-même une fois ingéré (dimension D₂, l'empreinte
> documentaire).
>
> Le fil conducteur de SOURCES.md §1 s'y vérifie au niveau du schéma : **les
> nomenclatures qualifient des documents, pas des normes.** On le voit ici
> physiquement — la classification n'est jamais au même endroit selon la
> famille de base, et la DTD n'énumère presque jamais les *valeurs* de matière.

## 1. Méthode et périmètre

**Source de vérité.** L'archive `DTD_LEGIFRANCE_20181017.7z`
(<https://echanges.dila.gouv.fr/OPENDATA/DTD_LEGIFRANCE/>, 339 Ko, datée du
2018-10-17 — **dernière version de DTD publiée**), extraite et lue fichier par
fichier. Elle contient les DTD, un `LEGIFRANCE_20181017_dtd_map.xlsx` (matrice
officielle base × type de document × DTD) et deux notices. Une
`Dila_Note_migration_technique_opendata_04102023.pdf` signale des évolutions
**mineures** depuis (ex. ajout d'`ECLI`, annoté « Fev 230 » dans le schéma
constit) : la structure décrite ci-dessous est stable, mais à revalider sur
données courantes avant tout usage critique.

**Recoupement.** Chaque constat a été confronté à nos propres parsers
(`data/src/ragcore/sources/`), qui ingèrent 6 de ces bases — la DTD dit ce que
la source *peut* porter, le parser dit ce qu'on en *retient*.

**Périmètre.** Les 35 dossiers de <https://echanges.dila.gouv.fr/OPENDATA/> ne
sont pas tous du droit : seules **11 bases** ont une DTD normative dans
l'archive. Les autres sont des annonces ou publications non normatives (BODACC,
BOAMP, BALO, DEBATS, RAPPORTS_PUBLICS, DISCOURS_PUBLICS, ASSOCIATIONS…) ou
relèvent d'un schéma distinct (`SERVICE-PUBLIC_DTD/`, traité au titre du
registre `citoyen` dans SOURCES.md §4). Les 11 retenues :

`legi` · `jorf` · `jorf_simple` · `juri` (CASS/INCA/CAPP) · `jade` · `constit`
· `kali` · `acco` · `cnil` · `sarde` · `dole` (seul schéma en **XSD**).

Vérifications datées du **2026-07-31**.

## 2. Trois familles structurelles

La DTD range les 11 bases en trois formes, et **c'est la forme qui décide où
vit la classification** :

| Famille | Bases | Forme du document | Où vit la classification |
|---|---|---|---|
| **Consolidée** (métadonnée `meta_texte_chronicle`) | LEGI, JORF, KALI | décomposée : conteneur → texte-version → texte-struct → section (`SECTION_TA`) → article | **positionnelle** — `CONTEXTE`/têtiers, c.-à-d. la place dans l'arbre du code |
| **Jurisprudence** (métadonnée `meta_juri`) | JURI, JADE, CONSTIT | plate : `META` + `TEXTE` + `LIENS` | **documentaire** — `SOMMAIRE/SCT` (titrage) + `ANA` (analyse) |
| **Plate simple** | CNIL, ACCO, SARDE, JORF_SIMPLE | `META_COMMUN` + un unique bloc `META_SPEC` | un champ dédié, ou aucune |

Le socle est commun à toutes : `META_COMMUN` = (`ID`, `ANCIEN_ID`, `ORIGINE`,
`URL`, `NATURE`). Tout le reste est spécifique et vit dans `META_SPEC`.

**La famille jurisprudence partage un `meta_juri.dtd` volontairement pauvre**
(`TITRE`, `DATE_DEC`, `JURIDICTION`, `NUMERO`, `SOLUTION`) : la richesse — le
titrage, la formation, le niveau de publication — est déclarée dans la racine
propre à chaque base (`juri_texte.dtd`, `jade_texte.dtd`, `constit_texte.dtd`),
pas dans le socle. C'est pourquoi lire le seul `meta_juri.dtd` fait croire, à
tort, que le titrage n'existe pas.

## 3. Carte des porteurs de classification (par base)

| Base | Préfixe XML / racine | Porteurs de *matière* | Axes énumérés *dans* la DTD |
|---|---|---|---|
| **LEGI** | LEGITEXT/SCTA/ARTI · `TEXTELR`, `ARTICLE`… | `CONTEXTE` (texte parent + têtiers `TM`), `NATURE` | `ETAT` (VIGUEUR, ABROGE, ABROGE_DIFF, ANNULE, DISJOINT, MODIFIE, MODIFIE_MORT_NE, PERIME, TRANSFERE, VIGUEUR_DIFF) |
| **JORF** | JORFCONT/TEXT/SCTA/ARTI · `JO`, `TEXTE_VERSION`… | `MC` (mots-clés), `NATURE`, `AUTORITE`/`MINISTERE`, `DOMAINE` (rubrique entreprise) | — |
| **JORF_SIMPLE** | JORFCONT/JORFTEXT · `JO`, `TEXTE` | (aucun — conteneur + corps) | — |
| **JURI** (CASS/INCA/CAPP) | JURITEXT · `TEXTE_JURI_JUDI` | **`SCT` titrage + `ANA`**, `FORMATION`, `SOLUTION`, `JURIDICTION` | `SCT@TYPE` (PRINCIPAL / REFERENCE), `PUBLI_BULL@publie` (oui / non) |
| **JADE** | CETATEXT · `TEXTE_JURI_ADMIN` | **`SCT`/`ANA`**, `TYPE_REC`, `FORMATION` | **`PUBLI_RECUEIL`** (A / B / C = publié / mentionné / inédit au recueil Lebon) |
| **CONSTIT** | CONSTEXT · `TEXTE_JURI_CONSTIT` | `NATURE_QUALIFIEE` (code DC, QPC…), `LOI_DEF` (loi déférée) | — |
| **KALI** (conv. collectives) | KALICONT/TEXT/SCTA/ARTI · **conteneur = `IDCC`** | **`IDCC`** (branche professionnelle), `CODES_NOMENCLATURES` (INSEE, NAF), `MC` | `APPLI_GEO` (A/B/C national/régional/départemental), `ETAT` (VIGUEUR, VIGUEUR_ETEN, SOUMIS_A_EXT…) |
| **ACCO** (accords d'entreprise) | ACCOTEXT · `TEXTE_ACCO` | **`THEMES/THEME` = (`CODE`, `LIBELLE`, `GROUPE`)**, `SECTEUR`, `IDCC`, `CODE_APE` | — |
| **CNIL** | CNILTEXT · `TEXTE_CNIL` | `NATURE_DELIB` (multivalué) | — (aucun axe de thème) |
| **SARDE** | `SARDE` | *base-référentiel* : `LIBELLE` / `CATEGORIE` / `IDENTIFIANT` | — |
| **DOLE** (dossiers législatifs, **XSD**) | JORFDOLE · `DOSSIER_LEGISLATIF` | `LEGISLATURE`, `OBJET`, `BASE_LEGALE`, `ECHEANCIER`, `ARBORESCENCE` | procédural (parcours d'une loi, non thématique) |

## 4. Ce que la DTD énumère, ce qu'elle laisse ouvert

La distinction décisive pour la taxonomie :

**Fermé dans la DTD (valeurs listées, donc lisibles sans les données) — mais ce
ne sont que des axes de *statut*, jamais de matière :**

- `ETAT` juridique (LEGI, KALI, CNIL) — vigueur / abrogation / …
- `PUBLI_RECUEIL` (JADE) — A/B/C, le niveau Lebon
- `PUBLI_BULL@publie` (JURI) — oui/non
- `SCT@TYPE` (JURI, JADE) — PRINCIPAL / REFERENCE
- `APPLI_GEO` (KALI) — forme A/B/C nationale/régionale/départementale

**Ouvert (`#PCDATA` libre, souvent annoté « *liste de valeurs à préciser* ») —
et c'est là que se trouve toute la *matière* :**

- `SCT` (le titrage lui-même — le point de droit), `NATURE`, `NATURE_QUALIFIEE`,
  `NATURE_DELIB`, `autorite`, `ministere`, `FORMATION`, `SECTEUR`, `MC`, les
  libellés de `THEME`.

**Conséquence :** aucune des nomenclatures de matière n'est récupérable depuis
la DTD ; toutes doivent être **minées sur le corpus**. La DTD garantit le
*champ*, jamais le *vocabulaire*. C'est le constat de SOURCES.md §1, vérifié au
niveau du schéma.

## 5. Trois conclusions pour la taxonomie

1. **La DTD donne le squelette, la donnée donne le vocabulaire** (§4). Le travail
   d'ossature ne peut pas se faire en lisant les schémas : il faut lire les
   valeurs, dans le corpus ingéré.

2. **Deux natures de classification cohabitent, exactement comme « normes vs
   documents » de SOURCES.md §1.** Le consolidé classe par **position** (où
   l'article est rangé dans son code — `CONTEXTE` et têtiers `TM`) ; la
   jurisprudence classe par **titrage** (`SCT`, une nomenclature de points de
   droit apposée après coup). L'opposition théorique du registre est physique
   dans le XML.

3. **Le titrage `SCT` est la nomenclature-matière la plus riche, déjà présente
   dans notre Mongo — mais ingérée comme prose.** Notre `RoleTable` juri
   (`data/src/ragcore/sources/juri/table.py`) range `SOMMAIRE`/`SCT`/`ANA` en
   `Role.BODY` : le texte part à l'embedding, mais l'attribut
   `TYPE=PRINCIPAL/REFERENCE` et l'appariement `SCT`↔`ANA` par `ID` sont
   aplatis. C'est le **pendant XML de l'endpoint JUDILIBRE `/taxonomy`**
   (SOURCES.md §3) : la même matière, disponible localement, mais non exposée
   comme **facette requêtable**. Piste D₂ la plus rentable — la donnée est déjà
   là, il ne manque que l'extraction structurée.

*Bonus.* **ACCO** est la seule base DILA dotée d'un **arbre de thèmes natif
explicite** (`THEME` = code + libellé + groupe) ; mais c'est du droit
conventionnel d'entreprise, hors périmètre actuel. **KALI** indexe par `IDCC`
(branche professionnelle) — une autre entrée sectorielle prête à l'emploi.

## 6. Réserves et prochains pas

- **Millésime 2018 + migration 2023.** Revalider la présence/forme des champs
  sur un échantillon de données courantes (ou via la note de migration) avant
  d'en dépendre.
- **Extraire `SCT` en facette** sur les décisions déjà ingérées (JURI + JADE) :
  test à faible coût de la conclusion 3, et première brique de D₂ mesurée.
- **Confronter les axes DTD aux nomenclatures externes** de SOURCES.md :
  `SCT` (JURI) ↔ titrages Cassation / JUDILIBRE `/taxonomy` ; `PUBLI_RECUEIL`
  (JADE) ↔ PCJA / plan Lebon ; `NATURE_QUALIFIEE` (CONSTIT) ↔ tables
  analytiques du Conseil constitutionnel.
- **Bases hors ingestion** (JORF, KALI, ACCO, CNIL) : décider explicitement si
  leur empreinte documentaire entre un jour dans le périmètre, ou l'écarter.
