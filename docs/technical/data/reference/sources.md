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
open data (ADR-001 : ingérée dès la v0). Les autres jeux DILA (JORF, KALI, DOLE,
CIRCULAIRES…) ne sont pas ingérés — `JORF` et `UPLOAD` existent dans le vocabulaire
(`SourceName`) mais n'ont ni connecteur ni table : ils sont volontairement absents du
registre, et les demander lève une erreur nette au démarrage.

Le corpus vit sous `XML_SOURCE_PATH` (chemin absolu, hors dépôt), un sous-répertoire par
base (`LEGI/`, `CASS/`, …). Le sous-répertoire est un fait sur la source
(`sources/registry.py`), pas de la configuration.

Le code, lui, est rangé par **format XML**, pas par base : `sources/legislatif/` porte le
format de LEGI, `sources/jurisprudence/` celui des cinq bases de jurisprudence (un
connecteur, trois tables de rôles selon la racine). Six bases, deux dossiers : c'est le
registre qui associe chaque base à son format.

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

**La clé d'un document est le nom de son fichier sans extension**, qui doit être son
`<ID>` (ADR-034 §1). Elle se lit sans ouvrir le fichier, d'où deux passes
(`sources/generic/file_connector.py:KeyedFileConnector`) :

1. **`discover()`** parcourt l'arborescence sans rien parser et construit l'index
   `clé → [chemins]` (des chaînes : l'index tient tout le stock). Il rend l'inventaire
   de la source (`SourceInventory` : le nombre de clés, celui que retient le ratio de la
   source dans `ingestion_ratio`, et ce ratio, ADR-034 §9 — les clés écartées ne seront
   jamais lues) ;
2. **`fetch_all()`**, un générateur synchrone, lit les facettes d'une clé au moment de
   l'émettre, clés triées pour un run reproductible. Chaque fichier est contrôlé : un
   fichier illisible est écarté (`unreadable`), un fichier dont l'`<ID>` n'est pas le
   nom aussi (`id_mismatch`, journalisé avec son chemin) ; les autres facettes de la clé
   sont émises quand même. Puis les copies d'une même racine sont départagées (voir
   plus bas).

Tout écart est **compté** (`connector.skipped`, par raison) et émis en un compteur par
raison, hors équation de complétude. La fusion reste globale : la garantie qu'un
identifiant n'est émis qu'une fois vient de là, la clé est unique par source.

**Les copies d'une même racine** (`sources/generic/copy_arbitration.py`). L'export DILA
garde l'ancienne version d'un texte quand il écrit la nouvelle, parfois dans l'autre
arborescence (`en_vigueur` / `non_vigueur`), sans supprimer l'ancienne. Dans le stock du
13 juillet 2025, 16 602 clés LEGI ont plusieurs fichiers de même racine XML ; dans les
groupes à contenus différents, la copie la plus récente porte toujours l'état le plus
avancé (`ABROGE_DIFF → ABROGE`, `VIGUEUR_DIFF → VIGUEUR`…), et le dossier ne départage
rien (environ 800 fois, la bonne copie est dans `en_vigueur`). Rien dans un article ne
date sa version : seule la date de modification du fichier (mtime) les départage. Pour
chaque racine portée par plusieurs fichiers d'une clé :

1. des copies identiques n'en font qu'une, la plus récente (`duplicate_copy`) ;
2. entre copies différentes, la plus récente reste (`superseded_copy`) ;
3. à date égale, toutes restent, et le parser refuse le document
   (`facet_root_duplicated`) plutôt que de choisir au hasard.

Chaque arbitrage est une collision (`connector.collisions`), détaillée dans
`MURPHY_PROBLEMS.collisions` ([telemetrie.md](telemetrie.md#les-problèmes-dun-run)). La
règle suppose **des mtimes préservés à l'extraction** : c'est le défaut de `tar`, pas
de `cp` sans `-p`, de `rsync` sans `-t`, ni de `tar --touch`. Une seule extraction par
racine de source : un dump incrémental posé à côté de l'export global le duplique.

**`LegiFileConnector`** compose le connecteur générique, et ajoute deux choses, sans
regarder le contenu :

- **il écarte les artefacts d'export** : les `versions.xml` partagent tous la clé
  `versions`, que la passe 1 met à part ; ils sont lus un par un après les documents.
  Une racine `<VERSIONS>` ou un `<ID>` nu est un artefact, compté et émis en
  `document.version_skipped`. Tout autre `versions.xml` est rejeté en `id_mismatch` : sa
  clé n'est jamais son `<ID>`. Dans le dump du 13 octobre 2026, les 282 633
  `versions.xml` sont des artefacts (95 illisibles) ;
- **il fusionne les deux facettes d'un même texte** : `TEXTE_VERSION` (titre +
  métadonnées) et `TEXTELR` (structure, aucun titre) sont le même document dans deux
  fichiers de même nom (`texte/version/` et `texte/struct/`). Émises séparément, les
  textes finiraient sans titre. `ParsedDocument.source_files` garde la provenance.

**La jurisprudence** prend le connecteur générique tel quel, une instance par base (la
base est un paramètre, pas un type) : un fichier par décision, aucun artefact d'export.

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
inconnue ressort en `unknowns["roots"]`), `content_blocks` (les balises qui portent le
texte, **dans l'ordre** — LEGI range le texte d'un article sous `BLOC_TEXTUEL`, mais un
`TEXTE_VERSION` n'en a pas : le sien vit sous `VISAS`, `SIGNATAIRES`, `TP`), et la
`LinkTable` de traduction des liens.

**Le cliquet** : une balise sans rôle ne disparaît pas — sa valeur ressort dans
`unknowns["tags"]` ou `unknowns["links"]`, sous sa clé chemin-complet, et les golden
tests (qui parcourent l'arbre XML) la font échouer. Une métadonnée qui a un rôle mais
pas de renommage ressort aussi dans `tags` (ADR-023), sans faire échouer le cliquet. Sur un corpus saturé la table ne
déclare rien ; sur le prochain export DILA, une balise neuve sort dans le bilan du run au
lieu de s'évaporer.

### La cascade des balises non-configurées

Une balise absente de la table est **routée**, pas jetée :

- sa valeur a la forme d'un identifiant DILA (`^[A-Z]{8}[0-9]{12}$`, duck-typing sur la
  **valeur**, jamais sur le nom d'attribut) → traitée comme un **lien** ;
- sinon → **métadonnée**, sous sa clé chemin-complet.

Le signal est déclaré au site de parse (`DocumentParsing`, dans `ingest`), sous la clé chemin-complet
de la valeur : `links` pour un lien, `tags` pour une métadonnée (ADR-024). Une balise
sans texte ni attribut ne laisse aucune trace. Le curseur `skip_unconfigured` (booléen,
validé en tête de run, forcé à `true` hors `ENVIRONMENT=dev`) décide ensuite du sort de
la donnée : la métadonnée est retirée au site de parse, l'arête heuristique à
l'extraction — le signal survit toujours au filtre.

### Les invariants du parse

- **Identité** : un seul `identifier` (type `Identifier`) nomme le document partout en
  aval, sous sa valeur brute (`LEGIARTI000006419264`, `JURITEXT000019333891`). Il est
  validé à la construction (8 majuscules + 12 chiffres), pour toutes les sources ; ses
  8 lettres distinguent un article d'une décision. Identifiant absent ou mal formé =
  `ValidationError` = rejet métier (`document.invalidated`, `reason=identifier_missing`
  ou `identifier_malformed`), distinct d'une panne de lecture (`ParseError`).
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
`CHUNKING_MAX_CHARS` dans un bloc (fenêtre glissante avec `CHUNKING_OVERLAP_CHARS`).

- Sans section déclarée, le document entier est un bloc : la découpe à taille fixe est le
  cas particulier où la structure est muette.
- Un document sans contenu ne rend **aucun** chunk (les 287 `SECTION_TA` du corpus sont
  des nœuds de structure, 0/287 avec du texte) : on n'embarque pas du néant.
- Les offsets (`char_start`/`char_end`) sont calculés avec un curseur qui ne recule
  jamais : deux blocs au texte identique reçoivent des offsets différents. Si l'invariant
  du parser est rompu (section non littérale), le bloc est ignoré plutôt que doté d'un
  offset faux.
- Le calibrage vit dans `.env.dev`, à côté d'`EMBEDDING_MODEL` — voir
  [configuration.md](configuration.md#chunkingsettings-préfixe-chunking_) :
  `CHUNKING_MAX_CHARS=384` est une valeur héritée de l'ancien modèle.

## Relations et relations non formatées (`core/links/`, `sources/generic/relations.py`)

L'extraction tourne **dans le worker**, avant le chunking, et distingue deux natures de
cible sur un seul critère — l'identification, jamais la source :

- **`@id` renseigné** → une **`Relation`** (une arête vers un nœud). Le verbe
  (`typelien`) est traduit par la table de vocabulaire quand elle le connaît ; un mot non
  traduit entre dans le graphe **sous son nom brut** et remonte dans `unknowns` — le
  graphe porte une arête vraie et un aveu, jamais un vide (c'est pourquoi il n'y a plus
  d'enum `RelationType` : un enum de six verbes déclarait perdue toute relation au verbe
  inattendu). Les relations ne sont pas écrites par le worker : elles remontent vers la
  phase 2 (voir [pipeline.md](pipeline.md#6-resolverelations--la-phase-2)).
- **`@id` vide** → une **`UnformattedRelation`** (ADR-021), jamais un nœud ni un champ
  du document : la saga du document l'écrit dans `MURPHY_DATA.unformatted_relations`, où
  elle s'accumule de run en run comme une pendante. Mesuré sur le corpus : 89/89 `<LIEN>` LEGI à `@id` vide portent du
  texte (« code de l'environnement »…), 68/68 côté CASS — ce sont des désignations en
  toutes lettres, pas des scories. Les matérialiser en nœuds `:Unknown` peuplait le
  graphe d'entités jamais résolues, une par formulation. Le texte (`target_text`) est
  conservé **brut et intégral** (une balise CASS énumère souvent plusieurs articles d'un coup — le découpage
  demanderait de la sémantique juridique et appartient à une passe de résolution future) ;
  `sens` est conservé pour pouvoir orienter l'arête ce jour-là.

Un `typelien` non traduit est un type de lien non configuré : l'arête entre sous son
nom brut, et le mot ressort dans `unknowns["links"]`. Un lien heuristique n'a pas de
`typelien` : son arête entre sous le nom brut de sa balise. Un lien qu'on ne sait pas
écrire (`sens` inconnu, `@id` illisible, `typelien` ou balise heuristique qui ne peut
pas être un verbe) est compté (`relation.unknown`). Les deux voyagent dans la valeur de retour de l'extracteur et sont
déclarés par le workload à la télémétrie du worker. Avec `skip_unconfigured: true`,
l'extracteur retire les arêtes d'un type non configuré — `typelien` inconnu ou
heuristique (ADR-024).

La hiérarchie déclarée en double (fermeture d'ancêtres côté article, arbre côté sections)
est dédoublonnée en phase 2 par **réduction transitive** — contenance (`contient`)
seulement, jamais les arêtes `cite`.
