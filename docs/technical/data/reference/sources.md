# Les sources : connecteurs, parsing, chunking, relations

Référence de la chaîne de traitement d'un document, de la découverte du fichier XML aux
chunks et relations. Code : `src/ragcore/sources/` et `src/ragcore/core/links/`.

## Les corpus DILA

La DILA publie les données juridiques en open data
(<https://echanges.dila.gouv.fr/OPENDATA/>), au format XML, en stock initial + incréments.
Le pipeline ingère aujourd'hui **six** bases :

| Base | Contenu | Ordre |
|---|---|---|
| **LEGI** | Codes, lois et règlements consolidés | droit positif |
| **CASS** | Arrêts publiés de la Cour de cassation | judiciaire |
| **INCA** | Arrêts inédits de la Cour de cassation | judiciaire |
| **CAPP** | Décisions des cours d'appel et juridictions judiciaires de 1er degré | judiciaire |
| **JADE** | Décisions des juridictions administratives (CE, CAA, TA) | administratif |
| **CONSTIT** | Décisions du Conseil constitutionnel | constitutionnel |

CASS + INCA + CAPP + JADE + CONSTIT = l'intégralité de la jurisprudence DILA disponible en
open data (ADR-002 : ingérée dès la v0). Les autres jeux DILA (JORF, KALI, DOLE,
CIRCULAIRES…) ne sont pas ingérés — `JORF` et `UPLOAD` existent dans le vocabulaire
(`SourceName`) mais n'ont ni connecteur ni table : ils sont volontairement absents du
registre, et les demander lève une erreur nette au démarrage.

Le corpus vit sous `XML_SOURCE_PATH` (chemin absolu, hors dépôt), un sous-répertoire par
base (`LEGI/`, `CASS/`, …). Le sous-répertoire est un fait sur la source
(`sources/registry.py`), pas de la configuration.

## Le registre (`sources/registry.py`)

**Une source = trois données**, pas une classe :

```python
SourceDefinition(
    connector=…,      # fabrique : comment localiser et transcrire ses fichiers
    table=…,          # RoleTable : comment interpréter ce qu'on a transcrit
    subdirectory=…,   # où elle vit sous la racine du corpus
)
```

Quatre tables pour six sources : LEGI a la sienne ; CAPP, CASS et INCA partagent
`JURI_JUDI_ROLE_TABLE` (même racine `TEXTE_JURI_JUDI`, la base n'est qu'un champ) ; JADE a
`JURI_ADMIN_ROLE_TABLE` ; CONSTIT a `JURI_CONSTIT_ROLE_TABLE`. Au-dessus, trois routeurs
(`CompositeConnector`, `RoutingParser`, `RoutingRelationExtractor`) aiguillent sur
`document.source` : les nœuds du DAG ne voient qu'un connecteur et qu'un parser.

## Les connecteurs — « idiots » par principe

Un connecteur localise, lit et **transcrit l'arbre XML en dict, sans perte et sans
interprétation**. Il ne sait pas ce qu'est un `<LIEN>` ni un identifiant ; si la DILA ajoute une
balise demain, il la transporte — c'est le parser qui la déclarera inconnue. La
transcription est un arbre (pas un dict à plat : `<LIENS>` contient N `<LIEN>` frères
qu'un aplatissement écraserait mutuellement).

**`LegiFileConnector`** prend deux décisions, aucune ne regarde le contenu :

- **il écarte les artefacts d'export** : les `versions.xml` (racine `<VERSIONS>`) et les
  fichiers `<ID>` d'une ligne — mesuré, 1 637 + 60 des 2 564 fichiers du corpus. Ce ne
  sont pas des documents pauvres, ce ne sont pas des documents. L'écart est **compté**
  (`connector.skipped`, par raison) et émis en `document.skipped`, hors équation de
  complétude ;
- **il fusionne les deux facettes d'un même texte** : `TEXTE_VERSION` (titre +
  métadonnées) et `TEXTELR` (structure, aucun titre) sont le même document dans deux
  fichiers (98 IDs, intersection 98/98). Les émettre séparément produirait 98 collisions
  d'identifiant, et les 98 textes finiraient sans titre. `ParsedDocument.source_files`
  garde la provenance (jusqu'à 2 fichiers par document).

**`JuriFileConnector`** — une seule classe pour les cinq bases (la base est un paramètre,
pas un type). Plus simple que LEGI : un fichier = un document, aucun artefact d'export.

## Le parser générique (`sources/generic/parser.py`)

**Un seul parser pour six sources.** Sa mécanique (parcourir l'arbre, relever les blocs de
texte, aplatir les métadonnées) ne contient aucun mot de LEGI ni de jurisprudence : tout ce
qui est spécifique vit dans la `RoleTable` de la source.

Le parser délègue à trois modules voisins : `tree.py` (relire l'arbre transcrit par
`xml_tree.py`), `structure.py` (les liens bruts et les ancêtres déclarés) et
`unconfigured.py` (la cascade des trois portes pour les balises que la table ne connaît
pas).

### La table de rôles (`roles.py`, `role_table.py`)

Chaque balise déclarée porte **un** rôle, parmi quatre :

| Rôle | Traitement |
|---|---|
| `BODY` | Le texte : part dans Mongo et dans l'embedding. |
| `LINK` | Une arête : part dans `core/links`, jamais traitée par le parser. |
| `VERSION` | L'axe temporel (`date_debut`/`date_fin`/`etat`). Absent de la jurisprudence : le rôle existe, aucune balise n'y est mappée. |
| `META` | Tout champ plat qui n'est ni corps, ni lien, ni date — un défaut *déclaré*, jamais implicite. |

La table porte aussi : `roots` (les racines XML que la source connaît — une racine
inconnue ressort en `unknowns["racine"]`), `content_blocks` (les balises qui portent le
texte, **dans l'ordre** — LEGI range le texte d'un article sous `BLOC_TEXTUEL`, mais un
`TEXTE_VERSION` n'en a pas : le sien vit sous `VISAS`, `SIGNATAIRES`, `TP`), et la
`LinkTable` de traduction des liens.

**Le cliquet** : une balise sans rôle ne disparaît pas — elle ressort dans
`unknowns["balise"]` et les golden tests la font échouer. Sur un corpus saturé la table ne
déclare rien ; sur le prochain export DILA, une balise neuve sort dans le bilan du run au
lieu de s'évaporer.

### La cascade des balises non-configurées

Une balise absente de la table est **routée**, pas jetée :

- sa valeur a la forme d'un identifiant DILA (`^[A-Z]{8}[0-9]{12}$`, duck-typing sur la
  **valeur**, jamais sur le nom d'attribut) → traitée comme un **lien** ;
- sinon → **métadonnée**, sous sa clé chemin-complet.

Dans les deux cas, le signal `tag.unconfigured` est déclaré au site de parse
(`computeIdempotence`), et le curseur `exportation.skip_unconfigured` (booléen, validé en
tête de run) décide
ensuite du sort de la métadonnée — le signal survit toujours au filtre.

### Les invariants du parse

- **Identité** : un seul `identifier` (type `Identifier`) nomme le document partout en
  aval, sous sa valeur brute (`LEGIARTI000006419264`, `JURITEXT000019333891`). Il est
  validé à la construction (8 majuscules + 12 chiffres), pour toutes les sources ; ses
  8 lettres distinguent un article d'une décision. Identifiant absent ou mal formé =
  `ValidationError` = rejet métier (manifest `EXCLUDED`), distinct d'une panne de lecture
  (`ParseError`).
- **`content` et `structure["sections"]` sortent de la même lecture, dans le même
  ordre** : chaque section est un morceau **littéral** de `content`, et
  `content.find(section)` le retrouve toujours. C'est l'invariant dont dépendent les
  offsets des chunks — un offset faux ne lève rien, il désigne juste le mauvais passage.
- **Aucune lemmatisation.** L'ancien nettoyage spaCy transformait « Le directeur général
  est nommé par décret » en « directeur général nommer décret » — et ce sac de lemmes
  partait dans Mongo (donc à l'écran) et dans l'embedding, sans que le texte original
  soit stocké nulle part. Supprimé : ce qui sort du parser est du français lisible.

### La normalisation typographique (`normalize.py`, version `v1`)

Ce qu'elle corrige : Unicode NFC (`é` en un caractère, pas deux), espaces
insécables/fines, caractères de largeur nulle, césures conditionnelles, balises HTML
résiduelles. Invisible à l'œil, décisif pour le tokenizer et le modèle.

Ce qu'elle ne fait pas, délibérément : lemmatisation, mots vides, minuscules — on
normalise la *typographie*, jamais la *langue*.

⚠️ La modifier invalide les vecteurs déjà écrits : après un changement, réingérer tout
le corpus, sinon deux jeux de vecteurs incomparables cohabitent dans la collection.

## Le chunking (`sources/generic/chunking.py` — `StructuralChunker`)

**La structure dit où couper, la taille dit jusqu'où aller** — pas deux stratégies
concurrentes : on ne coupe jamais à travers un bloc structurel, et on ne dépasse jamais
`chunking.size` dans un bloc (fenêtre glissante avec `overlap`).

- Sans section déclarée, le document entier est un bloc : la découpe à taille fixe est le
  cas particulier où la structure est muette.
- Un document sans contenu ne rend **aucun** chunk (les 287 `SECTION_TA` du corpus sont
  des nœuds de structure, 0/287 avec du texte) : on n'embarque pas du néant.
- Les offsets (`char_start`/`char_end`) sont calculés avec un curseur qui ne recule
  jamais : deux blocs au texte identique reçoivent des offsets différents. Si l'invariant
  du parser est rompu (section non littérale), le bloc est ignoré plutôt que doté d'un
  offset faux.
- Le calibrage vit dans `conf/base/ingestion/parameters.yml` — voir
  [configuration.md](configuration.md#chunking-et-embedding--ce-qui-décide-des-vecteurs)
  pour le raisonnement mesuré derrière `chunking.size: 384`.

## Relations et citations (`core/links/`, `sources/generic/relations.py`)

L'extraction tourne **dans le worker**, avant le chunking, et distingue deux natures de
cible sur un seul critère — l'identification, jamais la source :

- **`@id` renseigné** → une **`Relation`** (une arête vers un nœud). Le verbe
  (`typelien`) est traduit par la table de vocabulaire quand elle le connaît ; un mot non
  traduit entre dans le graphe **sous son nom brut** et remonte dans `unknowns` — le
  graphe porte une arête vraie et un aveu, jamais un vide (c'est pourquoi il n'y a plus
  d'enum `RelationType` : un enum de six verbes déclarait perdue toute relation au verbe
  inattendu). Les relations ne sont pas écrites par le worker : elles remontent vers la
  phase 2 (voir [pipeline.md](pipeline.md#6-resolverelations--la-phase-2)).
- **`@id` vide** → une **`Citation`**, champ du document (`ParsedDocument.citations`),
  jamais un nœud. Mesuré sur le corpus : 89/89 `<LIEN>` LEGI à `@id` vide portent du
  texte (« code de l'environnement »…), 68/68 côté CASS — ce sont des désignations en
  toutes lettres, pas des scories. Les matérialiser en nœuds `:Unknown` peuplait le
  graphe d'entités jamais résolues, une par formulation. Le texte est conservé **brut et
  intégral** (une balise CASS énumère souvent plusieurs articles d'un coup — le découpage
  demanderait de la sémantique juridique et appartient à une passe de résolution future) ;
  `sens` est conservé pour pouvoir orienter l'arête ce jour-là.

Les inconnus d'extraction (`typelien`, `sens`, `identifiant`) voyagent dans la valeur de
retour de l'extracteur et sont déclarés par le workload à la télémétrie du worker.

La hiérarchie déclarée en double (fermeture d'ancêtres côté article, arbre côté sections)
est dédoublonnée en phase 2 par **réduction transitive** — contenance (`titre`) seulement,
jamais les citations.
