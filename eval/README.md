# murphy-eval — harnais d'évaluation IR (P2)

Scorer de récupération documentaire pour Murphy (RAG juridique). Évalue
uniquement la **récupération** (contrat `requête → IDs ordonnés`, ADR-016) :
aucune dépendance à un LLM générateur, aucune dépendance aux bases de données.

Périmètre actuel :

- **B-04** — le scorer pur : `(qrels, run) → métriques`.
- **B-05** — l'adapter baseline (config dense de référence) : `(topics, R) → run`.
  `BaselineRetriever` embarque chaque requête (TEI), interroge Qdrant en direct
  (chemin de lecture dédié, sans importer `ragcore` — ADR-027) et écrit un run
  JSONL canonique immuable (ADR-008). Le `doc_id` canonique (ADR-018) est lu du
  payload Qdrant (clé `identifier`), sans résolution externe. Le nom de
  collection provient du pointeur `MURPHY_META` publié par la dernière
  ingestion `ok`.
- **B-06** — les invariants structurels de strate 1 (ADR-017), part **pure**
  (aucune base de données). `core/services/invariants.py` collecte les
  `Violation` d'un run/qrels : rangs contigus et uniques par requête, pas de
  doublon `(query_id, chunk_id)`, `doc_id`/`chunk_id` non vides, et espaces de
  nommage `doc_id` compatibles entre run et qrels (garde-fou contre des
  métriques à 0 muettes). Branchés en option sur les loaders JSONL
  (`load_jsonl_run(..., validate=True)` → lève `InvariantError`). La complétude
  et l'intégrité des liens (strate 1 *live*, sur BDD peuplées) restent hors v0
  par décision de cadrage — déjà couvertes côté `data/`.
- **B-07** — le socle d'extraction des **paires de co-citation** de strate 2.
  Premier chemin de lecture **Neo4j** du harnais (`adapters/graph/`), lecture
  seule, **sans importer `ragcore`** (ADR-027). ADR-029 a rétrogradé la strate 2 :
  ce n'est **pas** un fichier de qrels scorables mais un **diagnostic de
  co-citation précision-seulement** — B-07 en produit les paires, B-09 les
  consomme. **Méthode** : une paire = une **arête directe orientée**
  `source -[verbe]-> target` entre deux nœuds documents ; **tous les verbes**
  (`type(r)` émis, aucun jugement de pertinence ici) ; **auto-paires et nœuds
  `:Pending` exclus** (les deux documents doivent exister réellement) ; `owner_id`
  en **filtre** de requête, absent des lignes de sortie (identité = `identifier`
  nu, ADR-018, même espace que `RunEntry.doc_id`). Sortie **JSONL dédiée
  immuable** (`adapters/cocitation_io.py`), triée `(source, verbe, target)` —
  reproductible bit-à-bit, **jamais** le format qrels ADR-008. **Volumétrie** :
  `core/services/cocitation_report.py:summarize_pairs` (total, ventilation par
  verbe, documents distincts). Filtres prouvés contre un vrai Neo4j
  (`tests/integration`, testcontainers). **Produit par la commande
  `murphy-eval-cocitation`** (cf. « Miner les paires » ci-dessous).

Voir `docs/product/ADR/ADR-027-plateforme-evaluation-end-to-end.md` (repo
parent) pour la place de ce projet dans la plateforme P2 complète.

## Installer

```bash
python -m pip install -e ".[dev]"
```

## Miner les paires (B-07)

Produit le jeu de paires de co-citation de strate 2 et sa volumétrie. C'est la
**procédure de rejeu** de cet artefact (E-T-02) ; le jeu produit est **commité**
(E-P2-05 : jeu versionné).

```bash
murphy-eval-cocitation                      # tenant OWNER_ID du .env.dev
murphy-eval-cocitation --owner-id tenant-x  # forcer un autre tenant
murphy-eval-cocitation --out-dir /tmp/essai # sortie hors du dossier versionné
```

Le tenant par défaut est **lu du `.env.dev`** (`OWNER_ID`, la variable même que
l'ingestion utilise), jamais codé en dur : un tenant qui ne correspond à rien
produirait un jeu vide sans erreur. Si le jeu ressort vide, la commande le
signale explicitement sur `stderr`.

Écrit deux fichiers dans `artifacts/cocitation/` :

| Fichier | Contenu |
|---|---|
| `pairs.jsonl` | le jeu miné, une `CocitationPair` par ligne, trié `(source, verbe, target)` |
| `summary.json` | la volumétrie : total, documents distincts, ventilation par verbe |

**Prérequis** : un Neo4j **peuplé** par une ingestion (`npm run ingest:up` à la
racine, puis `kedro run` depuis `data/`), et un `.env.dev` à la racine du dépôt
fournissant `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`. Le chemin de
sortie est résolu depuis la racine du projet, jamais depuis le répertoire
courant : la commande donne le même résultat d'où qu'on la lance.

**Volumétrie du premier jeu réel** (22 juillet 2026, corpus de dev, tenant
`default`) : **1456 paires, 726 documents distincts** — `contains` 726,
`cites` 373, `succeeded_by` 288, `references` 62, `modifies` 7.

> ⚠️ `contains` (la moitié du jeu) est de la **structure documentaire**
> (`Section→Article`, `Texte→Section`), pas une citation. ADR-029 fonde la
> strate 2 sur des documents *juridiquement liés* : son sort — filtrer au
> minage ou neutraliser au diagnostic — est **à trancher avant B-09**
> (`BACKLOG.md` §2). Le socle reste conforme ; c'est l'interprétation du jeu
> qui est en jeu.

Les deux fichiers sont **reproductibles bit-à-bit** : rejouer la commande sur le
même graphe ne produit aucun diff `git`. En cas de graphe injoignable ou
incohérent avec le contrat d'ingestion, la commande sort en code `1` avec un
message sur `stderr` (pas de traceback : ce sont des conditions d'exploitation).

## Tester

```bash
python -m pytest                 # suite primaire : goldens (oracle à la main) + unitaires
python -m pytest -m oracle       # cross-check trec_eval (nécessite pytrec_eval)
python -m pytest -m integration  # chemin réel Qdrant (testcontainers — nécessite Docker)
ruff check src
mypy src/murphy_eval
```
