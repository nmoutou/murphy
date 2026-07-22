# B-07 — Revue de code du socle de co-citation

> Document de travail (`WIP/`), **éphémère par conception** : il vit le
> temps de B-07 et disparaît à sa clôture. Ce qui doit survivre part
> ailleurs — un constat de conception en ADR, une dette différée en
> `BACKLOG.md` §4, un statut en `STATUS.md`.
>
> Revue du 22 juillet 2026, sur le code non committé de B-07 (socle
> d'extraction des paires de co-citation, strate 2 — ADR-029).
> Périmètre relu : `eval/src/murphy_eval/{adapters/graph/neo4j_cocitation.py,
> adapters/cocitation_io.py, core/models/cocitation.py, core/ports/graph.py,
> core/services/cocitation_report.py}` + les trois suites de tests
> associées, croisés avec le contrat d'ingestion
> (`data/src/ragcore/adapters/storage/neo4j/graph_repository.py`).

## 1. Constat général

Le socle est conforme à ADR-029 sur le fond : pas de grade, pas de
rappel, pas de format qrels, `owner_id` en paramètre et non en donnée,
frontière ADR-027 tenue (aucun import `ragcore`). L'hexagone est
respecté (port `CocitationMiner`, adapter isolé, service pur) et le
déterminisme du writer est testé.

Les points ci-dessous ne portent donc pas sur le cadrage mais sur la
**fidélité au contrat du graphe** (C-01, C-02), la **livrabilité au sens
d'E-P2-05** (C-04) et la dette assumable (C-03, C-05, C-06).

## 2. Points à adresser

Sévérité : **Bloquant** (le jeu de paires est faux ou le bloc n'est pas
livrable) · **Dette** (à régler avant le bloc aval nommé) · **Confort**.

| ID | Point | Sévérité | Débouché |
|---|---|---|---|
| C-01 | `MATCH (a)-[r]->(b)` ne contraint **ni label ni type d'arête** : la requête n'exprime **aucune** hypothèse sur ce qu'est un nœud-document. Défaut **latent, non actif** (cf. §4) : rien ne cassera le jour où un `:Chunk`, un `:Run` ou un nœud de télémétrie entrera dans le graphe — il rejoindra le jeu de paires en silence, et B-09 croira diagnostiquer une précision documentaire. Le test d'intégration ne l'expose pas : son seed ne contient que des `:Article` et un `:Pending`. | Dette (latent) | B-07 |
| C-02 | Le fail-fast de `_record_to_pair` **ne peut pas se déclencher** : `RETURN a.identifier AS source` rend toujours les trois clés — une propriété absente vaut `None`, jamais `KeyError`. Un nœud hors contrat produirait donc `str(None) == "None"`, une paire **silencieusement fausse** : exactement ce que la docstring dit prévenir. Le test unitaire passe sur une doublure qui fabrique un dict tronqué — situation que le driver ne produit jamais. C'est du **code mort qui prétend protéger**, donc dispense de se poser la question. | Bloquant | B-07 |
| C-03 | `mine_pairs` matérialise **toutes** les arêtes du tenant en mémoire (`list`). Le corpus DILA complet se compte en millions d'arêtes ; le seul consommateur (`dump_jsonl_pairs`) n'a besoin que d'un flux. Le port renvoie `list[CocitationPair]` — le passer en `Iterator` rendrait le streaming bout-en-bout (le writer consomme déjà un `Iterable` ; `summarize_pairs` ne fait qu'un passage, `len()` mis à part). | Dette | avant B-13 |
| C-04 | **Aucun point d'entrée.** Ni script, ni `console_scripts`, ni composeur reliant `settings → miner → dump → summarize`. Les settings Neo4j sont ajoutés mais **personne ne les lit**. En l'état, produire le jeu demande d'écrire du Python à la main — or E-P2-05 exige un jeu versionné, volumétrie et méthode documentées, donc un artefact reproductible par une commande. Sans elle, la volumétrie ne sera jamais mesurée et B-09 n'aura rien à consommer. | Bloquant | B-07 |
| C-05 | `Neo4jCocitationMiner` (comme `QdrantSearchClient`) expose `close()` sans `__enter__`/`__exit__`. Le test d'intégration compense en `try/finally` : signe que l'API pousse à la fuite de connexion, ce qui coûtera dans l'orchestrateur B-13. | Dette | avant B-13 |
| C-06 | `write_text`/`read_text` **sans `encoding="utf-8"`** dans `cocitation_io.py` : la sortie dépend de la locale du poste, ce qui rend illusoire la promesse « reproductible bit-à-bit » affichée juste au-dessus (d'autant que `ensure_ascii=False` laisse passer du non-ASCII). | Bloquant (bon marché) | B-07 |
| C-07 | Le test unitaire du miner contourne le constructeur (`__new__` + injection de `_driver`). Symptôme d'un couplage : le driver devrait être injectable (`__init__(self, driver)` + fabrique `from_uri`), ce dont le composeur de C-04 profiterait. | Confort | opportuniste |
| C-08 | `eval/tests/data/sane.pairs.jsonl` n'est référencé par **aucun** test — fichier orphelin, à câbler ou supprimer. | Confort | B-07 |
| C-09 | **Découvert en corrigeant C-02, non vu à la revue.** Le prédicat d'auto-arête `a.identifier <> b.identifier` **écartait silencieusement les nœuds sans `identifier`** : en Cypher toute comparaison avec `NULL` vaut `NULL`, jamais `TRUE`. La ligne hors contrat était donc filtrée *par la requête*, n'atteignait jamais `_record_to_pair`, et vidait C-02 de son objet — corriger le fail-fast seul n'aurait rien changé. Mesuré contre un vrai Neo4j, puis corrigé en `NOT (a = b)` (comparaison de **nœuds**, indépendante des propriétés). | Bloquant | ✅ fait |

## 2 bis. Constats du premier run réel (22 juillet 2026)

Graphe peuplé, `murphy-eval-cocitation` exécuté : **1456 paires, 726 documents**,
artefacts reproductibles bit-à-bit (md5 identiques sur deux runs).

| ID | Point | Sévérité | Débouché |
|---|---|---|---|
| C-10 | **Le tenant était codé en dur à `"system"`** alors que l'ingestion écrit `OWNER_ID` (= `"default"`, défaut de `ragcore/adapters/config/settings.py:140`). La commande minait donc un tenant **inexistant** et produisait un artefact **vide, en code 0, sans rien signaler** — l'échec silencieux même que cette revue combat. Invisible aux tests (la doublure accepte n'importe quel `owner_id`) ; seul le run réel pouvait le montrer. Corrigé : `owner_id` lu des settings (`OWNER_ID`, même variable que l'ingestion), et **avertissement explicite sur `stderr` si le jeu est vide**. | Bloquant | ✅ fait |
| C-11 | **`contains` pèse 726 des 1456 paires — la moitié du jeu — et n'est pas une citation.** Ventilation mesurée : `Section→Article` (395), `Section→Section` (269), `Texte→Section` (48), `Texte→Article` (14) : c'est l'**arborescence documentaire** d'un code (un texte contient ses articles), pas un lien juridique entre deux documents distincts. ADR-029 fonde la strate 2 sur « documents juridiquement liés » ; un couple parent/enfant structurel n'est pas ce lien, et sa présence gonflerait mécaniquement la précision diagnostique de B-09 avec des paires triviales. **Décision de cadrage à prendre** (filtrer `contains` ? le verbe est-il jugé en B-09 comme le prévoit ADR-029 ?) — non tranchée ici. | Bloquant | avant B-09 |

Le jeu produit reste **techniquement conforme** (méthode et volumétrie documentées,
reproductible) ; C-11 porte sur son **interprétation**, pas sa fabrication.

## 3. Ordre d'attaque retenu

1. **C-01 + C-02 (+ C-09)** — ✅ **faits le 22 juillet 2026.** Correction :
   tant qu'ils tenaient, le jeu de paires produit était fragile, et tout ce
   qui est construit dessus (volumétrie, B-09) héritait du défaut. Traités
   ensemble : même fichier, même requête, mêmes tests d'intégration durcis.
   C-09 est apparu **en cours de correction** — il neutralisait C-02, et
   seule l'exécution contre un vrai Neo4j pouvait le révéler (cf. §4).
2. **C-06** — ✅ **fait le 22 juillet 2026**, et **étendu** : le même défaut
   existait dans `adapters/trec/projection.py` (writer de runs B-05 + loader
   commun), qui porte la même promesse de déterminisme. Corrigé aux deux
   endroits — le laisser dans le patron d'origine aurait garanti sa recopie.
3. **C-04** — ✅ **fait le 22 juillet 2026** : commande `murphy-eval-cocitation`
   (`cli/cocitation.py`), artefacts versionnés dans `eval/artifacts/cocitation/`
   (`pairs.jsonl` + `summary.json`), procédure de rejeu au README. Portée tenue à
   B-07 seul : **B-05 n'a pas de point d'entrée non plus** (cf. §4).
4. **C-08** — ✅ **fait** : `sane.pairs.jsonl` câblé en test de round-trip sur
   fichier réel. **C-07** — sans objet immédiat : la fabrique `build_miner()`
   isole la construction, la CLI se teste par doublure du port sans toucher au
   constructeur du miner. À rouvrir si le besoin revient.
5. **C-05** — ✅ **fait** : `Neo4jCocitationMiner` est un gestionnaire de
   contexte (`__enter__`/`__exit__`) ; le test d'intégration abandonne son
   `try/finally`. `close()` reste public pour le composeur CLI, qui doit fermer
   dans un `finally` couvrant aussi son propre code.
   **C-03** — **non fait, et requalifié.** La fiche le présentait comme une
   substitution `list` → `Iterator` ; le composeur consomme en réalité les paires
   **deux fois** (`dump_jsonl_pairs` puis `summarize_pairs`, qui exige une
   `Sequence`). Un itérateur nu serait épuisé au second passage : le rendre
   streamant demande de fusionner écriture et résumé en un seul parcours. Volume
   mesuré : **1456 paires sur le corpus de dev** — aucune pression mémoire
   aujourd'hui. À reprendre avec le corpus complet, avant B-13.
- **Réserve de forme — ✅ soldée** : `aggregated.py` et `test_invariants.py`
  (B-06) reformatés dans un changement isolé. `ruff format --check .` est vert
  sur les 60 fichiers.

## 5. Clôture

**B-07 est ✅ (22 juillet 2026).** Cette fiche a rempli son office et peut
disparaître au prochain nettoyage : ce qui devait survivre est parti ailleurs —
E-P2-05 ✅ (`EXIGENCES_v0.md`), volumétrie et défauts consignés en
`BACKLOG.md` §2, état du programme en `STATUS.md`, méthode et chiffres en
`eval/README.md`.

**Le seul point ouvert est C-11** (sort du verbe `contains`), porté au backlog
comme décision à prendre **avant B-09**.

### Ce que la fiche aura appris

Trois des quatre défauts réels de ce bloc étaient **invisibles à la revue
statique**, et chacun a été trouvé par une exécution :

| Défaut | Révélé par |
|---|---|
| C-09 (`NULL` en Cypher neutralisait le fail-fast) | test d'intégration contre un vrai Neo4j |
| C-10 (tenant codé en dur → jeu vide en code 0) | premier run contre le graphe peuplé |
| C-11 (`contains` = structure, pas citation) | lecture de la **volumétrie** du jeu produit |

La leçon de C-09 se généralise : **un filtre ou une valeur par défaut ne se
prouve qu'en s'exécutant contre le vrai système.** C-10 est le cas limite — la
doublure de test acceptait n'importe quel `owner_id`, donc aucun test unitaire
n'aurait pu le voir. D'où le garde-fou ajouté : un jeu vide avertit désormais
sur `stderr`, parce que le mode d'échec à craindre ici n'est pas l'erreur mais
le **silence**.

## 4. Notes de revue

- C-01 impose un arbitrage : contraindre les labels dans `eval/`
  **duplique** un contrat qui vit dans `ragcore`, ce qu'ADR-027 interdit
  d'importer. La duplication est assumée mais doit être explicitement
  documentée comme miroir d'ADR-018, et **gardée par un test
  d'intégration** qui échoue si un nœud inattendu apparaît (nœud parasite
  au seed) — sinon la dérive du contrat serait silencieuse.
- C-02 et C-01 partagent le même remède côté preuve : le seed du test
  d'intégration doit contenir les cas dégradés (nœud hors contrat, nœud
  sans `identifier`), pas seulement le cas nominal.
- **Leçon de C-09, à retenir pour la suite de B-07.** Le défaut a été
  trouvé parce que le test d'intégration a été écrit *pour échouer* sur
  un cas dégradé et l'a fait pour la mauvaise raison. Une revue statique
  ne pouvait pas le voir : la sémantique `NULL` de Cypher ne se lit pas
  dans le code Python. **Corollaire** : pour tout filtre vivant dans une
  requête, la preuve est un test contre un vrai serveur, pas une
  doublure — c'est déjà l'argument de C-02, C-09 en est la démonstration.
- Vérification du 22 juillet : 95 tests unitaires verts, 2 tests
  `integration` verts (Neo4j 5.26 via testcontainers), `mypy` strict et
  `ruff` propres. Reste à faire, une fois un graphe réellement peuplé :
  le contrôle de volumétrie avant/après filtre de labels (doit être
  **identique** — C-01 est latent, pas actif ; un écart signalerait un
  label documentaire non recensé dans `_DOCUMENT_LABELS`).
  **Sorti de cette fiche** : cette réserve doit survivre à B-07, elle est
  donc portée par `BACKLOG.md` §2 (note B-07) et par la docstring de
  `_DOCUMENT_LABELS`. Ce qui suit n'en est qu'un rappel de contexte.
- **Constat d'exploration (C-04), à ne pas perdre** : `BaselineRetriever` (B-05)
  **n'est câblé nulle part** non plus — avant ce jour, `eval/` n'avait aucun
  `[project.scripts]` ni composeur. C-04 n'était donc pas un oubli propre à B-07
  mais un manque structurel du harnais. La commande de B-07 pose le patron
  (`cli/` = seule couche qui compose, `T201` levé là et nulle part ailleurs) ;
  **le point d'entrée de B-05 reste à faire** — porté en `BACKLOG.md` §2.
- **Réserve de forme, non traitée** : `ruff format --check` signale
  `core/models/aggregated.py` et `tests/unit/test_invariants.py`,
  **pré-existants (B-06) et non touchés ici**. Laissés délibérément pour
  ne pas mêler du reformatage sans rapport au diff de C-01/C-02/C-09 —
  à solder dans un commit propre. Conséquence : `ruff format --check .`
  est rouge à l'échelle du projet, ce qui bloquerait un hook pre-commit.
