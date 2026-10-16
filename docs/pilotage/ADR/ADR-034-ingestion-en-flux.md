# ADR-034 — L'ingestion en flux : une mémoire bornée, des relations en transit

**Statut** : ✅ Accepté (14 octobre 2026) — amende ADR-013 (un échantillonnage revient,
en ratio) et ADR-019 §3 (une clé de plus dans `parameters.yml`) · **§8 amendé le
15 octobre 2026** (le détail des collisions a sa collection) · **§1 amendé le
15 octobre 2026** (les copies d'une même racine sont départagées par leur date) · **§8
amendé par ADR-036** (le détail des problèmes passe dans `MURPHY_PROBLEMS`, une ligne par
problème) · **§8 amendé le 16 octobre 2026** (une `Distribution` perd son histogramme)

## Contexte

`xml_source_path` pointe désormais vers le stock LEGI complet, le cas qu'ADR-013 laissait
à une ADR future. Le pipeline, écrit pour l'extrait de ~1100 documents, n'y tient plus :
`connect` ne termine pas, et rien ne dit où passe le temps.

Mesures du 13 et du 14 octobre 2026, sur une machine de 14 Go de RAM :

| Mesure | Valeur |
|---|---|
| Fichiers XML LEGI | 2 559 609, 25 Go |
| dont `versions.xml` | 282 633 : 277 725 de racine `VERSIONS`, 4 813 de racine `ID`, 95 illisibles |
| Identifiants LEGI | 2 116 313 : 1 956 845 à un fichier, 158 869 à deux, 599 à trois ou plus |
| Identifiants aux facettes dans deux arborescences (`en_vigueur` / `non_vigueur`) | 16 008 |
| Taille d'un document LEGI (facettes sommées) | moyenne 4,4 Ko, médiane 3,0 Ko, 99e centile 26 Ko, max 2,9 Mo |
| Mémoire retenue par document lu (`to_tree`) | ~18 Ko, ×6 la taille du XML |
| Relations par document | 8,8, ~1,9 Ko chacune |
| Lecture + parse d'un document | ~2,6 ms (`ET.parse` 0,41, `to_tree` 0,13, parse 2,11) |
| Nom de fichier ≠ `<ID>` | 0 sur 3 000 documents LEGI tirés au hasard, 0 sur les 352 fichiers de jurisprudence |
| Jurisprudence | 352 fichiers, moins de 10 Mo |

Le pipeline matérialise tout, d'un nœud au suivant :

- **`connect` charge le corpus entier.** Le connecteur LEGI lit tous les fichiers avant
  d'émettre, pour fusionner les facettes d'un texte, et le nœud vide le flux dans une
  liste. Extrapolé : au moins 48 Go. La machine swappe, et le run ne finit pas.
- **Les relations attendent la phase 2 en mémoire** (`IngestionOutcome.relations`) :
  ~18,6 M relations, ~35 Go. `reduce_transitively` en construit de plus un graphe
  networkx unique.
- **Neo4j reçoit une requête par relation** : 18,6 M allers-retours.
- **`promotable_for` passe tous les identifiants écrits dans un `$in`** : ~2,1 M
  identifiants, au-delà des 16 Mo d'une requête Mongo.

Le run n'expose ni sa progression ni ses durées, et le bilan (`run_summaries`) ne
compte que des événements.

## Décision

**1. Le connecteur LEGI lit en deux passes.** La passe 1 parcourt l'arborescence sans
rien parser et construit l'index `clé → [chemins]`, où la clé est le nom du fichier sans
son extension. La passe 2 lit les facettes d'une clé au moment de l'émettre. La fusion
reste globale : 16 008 identifiants ont leurs facettes dans deux arborescences, un
regroupement dossier par dossier les couperait.

- Les `versions.xml` partagent tous la clé `versions` : la passe 1 les met à part, la
  passe 2 les lit un par un et garde la règle actuelle (nom **et** racine). Dans ce
  dump, tous sont des artefacts ; la règle reste pour les dumps futurs.
- Un fichier dont l'`<ID>` diffère de sa clé est rejeté et compté, sous une nouvelle
  raison d'exclusion.
- Le connecteur de jurisprudence prend la même clé et le même contrôle.

> **Amendement (15 octobre 2026) : les copies d'une même racine.** Les « 16 008
> identifiants » ci-dessus ne sont pas des facettes légitimes réparties sur deux
> arborescences, mais des copies : l'export garde l'ancienne version d'un texte quand il
> écrit la nouvelle, souvent dans l'autre arborescence. Le parser les refusait toutes
> (`facet_root_duplicated`), version à jour comprise. Le connecteur générique les
> départage désormais, par racine : des copies identiques n'en font qu'une ; entre
> copies différentes, la plus récente (mtime) reste, le stock montrant qu'elle porte
> toujours l'état le plus avancé ; à date égale, toutes restent et le parser refuse le
> document. Chaque arbitrage est une collision (§8). La règle exige des mtimes
> préservés à l'extraction.

**2. Un nœud `ingest` enchaîne lecture, parse et ingestion.** `connect` et
`parseDocuments` cessent d'être des nœuds Kedro. `ragcore` expose les étapes comme des
fonctions sur des itérateurs, testées seules, et le nœud les compose. Le DAG devient
`nukeAll → ingest → resolveRelations → report`.

**3. Une file bornée, partagée par les workers.** La lecture et le parse restent dans le
thread principal ; ils alimentent une file que le premier worker libre consomme.

- **Capacité : le nombre de workers.** C'est un double tampon : chaque worker trouve un
  document prêt en finissant le sien. Au pire, 2n + 1 documents sont en mémoire (n
  traités, n en file, un en parse), soit ~55 Mo pour un worker au maximum mesuré.
- **Le partitionnement par hash du runner disparaît.** Il garantissait qu'un identifiant
  n'est traité que par un worker. La garantie vient désormais du flux : la clé est unique
  par source (§1), et les préfixes d'identifiants ne se croisent pas entre sources.
- **Arrêt** : en fin de flux, la lecture dépose un marqueur de fin par worker, y compris
  quand elle échoue. Un worker qui tombe sur une erreur hors d'un document (les échecs
  par document restent comptés comme avant) le signale à la lecture, qui cesse
  d'attendre une place dans la file.

**4. Les relations transitent par `MURPHY_DATA.transit_relations`.** La phase 1 n'en
garde plus aucune en mémoire.

- **Écriture** : une étape de la saga du document, après `mongo_unformatted_upsert`. Une
  ligne par relation : la `Relation` sérialisée, plus le `run_id`. Sa compensation
  supprime les lignes du document pour ce run (`source_id`, `run_id`).
- **Index** : (`run_id`, `relation_type`, `source_id`), non unique. Une arête déclarée
  par deux documents donne deux lignes ; la réduction dédoublonne.
- **Cycle de vie** : la collection est temporaire. Elle est vidée au démarrage du run,
  avant la phase 1, puis au fil de la phase 2 (§5). Chaque run relit et réextrait tout le
  corpus : les restes d'un run en échec ne contiennent rien que le suivant ne reproduise.
- **La barrière ne change pas** : l'arête `ingestion_outcome → resolveRelations` du DAG
  garantit que la phase 2 attend que tous les documents soient écrits.
  `IngestionOutcome` perd son champ `relations`.

**5. La phase 2 réduit composante connexe par composante connexe.** La réduction
supprime `a → c` quand un chemin `a → b → c` existe ; deux composantes connexes du graphe
`contient` n'ont aucune arête commune, donc aucun chemin ne passe de l'une à l'autre.
Réduire composante par composante donne exactement la réduction du graphe entier.

- Une première passe lit en flux les couples (`source`, `cible`) des relations
  `contient` de `transit_relations`. Un union-find en tire les composantes ; il ne garde
  qu'une entrée par nœud, et la taille de chaque composante (nœuds et relations).
- Chaque composante est lue, puis réduite seule par le code actuel
  (`reduce_transitively`, cycles compris). **Aucun plafond** : couper une composante
  rendrait la réduction approximative. La plus grande composante borne la mémoire de
  la phase 2, et `statistics` la mesure (§8).
- Les arêtes conservées vont dans un tampon, écrit dans Neo4j par lots `UNWIND` de
  taille fixe. Le lot peut mêler plusieurs composantes : la réduction est déjà faite.
- Les relations des autres verbes ne demandent aucune partition : elles passent par le
  même tampon, lues par lots de taille fixe.
- Une composante est supprimée de `transit_relations` une fois **toutes** ses relations
  traitées : écrites, enregistrées comme pendantes ou éliminées par la réduction. Les
  autres verbes, lot par lot, après écriture.

**6. `transit_relations` non vide en fin de phase 2 fait échouer le run.** C'est un bug,
pas un état dégradé : la phase 2 lève une exception, et le run est enregistré `failed`
avec un message explicite.

**7. La promotion des pendantes interroge Mongo par lots.** `written_node_ids` reste en
mémoire (~2,1 M identifiants, ~200 Mo) : le coût de la promotion suit la taille du run,
pas celle du stock de pendantes. Seul le `$in` est découpé.

**8. `MURPHY_META.statistics` mesure les tailles et les durées.** Un document par run,
index unique sur `run_id`, écrit à la clôture de la session, **même en cas d'échec**.

La frontière avec `run_summaries` :

| | `run_summaries` | `statistics` |
|---|---|---|
| Question | Le run a-t-il tout fait, et sinon, quoi ? | Combien ça pèse, combien de temps ça prend ? |
| Contenu | Une comptabilité : ce qui est arrivé aux objets | Des mesures : tailles et durées, en distributions |
| Usage | Le statut du run s'en dérive | Le diagnostic et le réglage ; jamais lue pour décider |

Ce qui compte des objets ou fait varier le statut va dans `run_summaries` ; une taille,
une durée ou une distribution va dans `statistics`.

Toute mesure est une `Distribution` :

```
Distribution = { count, sum, min, max, mean, max_ref, histogram }
```

- `max_ref` nomme ce qui a donné le maximum (un identifiant de document, de composante).
- `histogram` compte les valeurs par classe en puissance de 2 (`{"2^k": n}`) : aucune
  borne à choisir, et un compte exact par classe. Une moyenne seule ne dirait rien de
  distributions aussi asymétriques que celles du contexte. *Amendé le 16 octobre 2026 :
  l'histogramme est retiré, `min`, `max` et `max_ref` suffisent au diagnostic.*
- Comme `RunStats`, une `Distribution` se fusionne dans n'importe quel ordre : chaque
  worker tient la sienne, réunies en fin de run sans verrou.

Le schéma :

```
{
  run_id, started_at,
  stages_s: { discovery, phase1, components, phase2_write },
  documents: {                              // par source
    "<source>": {
      xml_bytes, facets, content_chars, chunks, relations,
      step_ms: { read, parse, embed, mongo, opensearch, neo4j }
    }
  },
  queues: { producer_blocked_s, worker_idle_s },
  components: { nodes, relations }
}
```

`components.nodes.count` est le nombre de composantes, et `max_ref` nomme la plus grande.
`queues` dit quel côté de la file freine : une lecture souvent bloquée désigne les
workers, des workers souvent inactifs désignent la lecture.

> **Amendement (15 octobre 2026) : `MURPHY_META.collisions`.** `run_summaries` ne garde
> des collisions qu'un compte par raison ; leur détail va dans `collisions`, écrit à la
> clôture de la session comme `statistics`, même en cas d'échec. Un document par source
> en collision et par run : `{run_id, source, started_at, part, parts, collisions:
> {raison: {count, details: [{identifier, key, files}]}}}`, chemins absolus, sans les
> valeurs en conflit. Trois raisons : `metadata` (ADR-025), `facet_root_duplicated` (le
> document est aussi rejeté, compté dans `invalidations` : l'équation de complétude ne
> change pas), et les copies arbitrées par le connecteur. Au-delà de 15 Mio de détails,
> le document est découpé en parties numérotées (`part` sur `parts`, index unique
> `(run_id, source, part)`), chacune portant les comptes de la source entière : la
> limite de 16 Mo d'un document Mongo ne fait ni échouer l'écriture ni tronquer le
> détail. Rejouer un run remplace ses documents.

> **Amendement (15 octobre 2026, ADR-036) : `MURPHY_PROBLEMS`.** `MURPHY_META.collisions`
> et son découpage en parties disparaissent. Le détail des problèmes va dans la base
> `MURPHY_PROBLEMS`, une ligne Mongo par problème avec son `run_id`, toujours écrit à la
> clôture de la session, même en cas d'échec : `collisions` (`metadata`,
> `duplicate_copy`, `facet_root_duplicated`) et `superseded` (une ligne par copie
> écartée par l'arbitrage, qui n'est plus une collision et se compte
> `document.superseded`). `nuke_all` vide cette base.

**9. `ingestion_ratio`, un réglage de dev par source.** Une nouvelle clé de
`parameters.yml` : une table `source → ratio`, chaque ratio dans [0, 1]. Une source
absente de la table vaut `1` ; une source inconnue, ou sans connecteur, arrête le run.
Hors `dev`, la table est vide (`SAFE_DEV_SETTINGS`) : tout le corpus est ingéré.

- **À `0`** : la source est retirée du run par son plan, avant la passe 1 : ni
  connecteur, ni parcours de l'arborescence. Si toutes les sources du run sont à `0`, le
  run s'arrête : il finirait « ok » sans rien avoir lu, après `nuke_all`.

- **Sélection** : par source, les ⌈ratio × n⌉ clés de plus petit hash (blake2b de la
  clé). Elle est exacte (10 % de LEGI, c'est ⌈0,1 × n⌉ documents ; une source d'un
  fichier garde le sien), reproductible d'un run à l'autre, et emboîtée : ce qui est
  retenu à 10 % l'est à 20 %.
- **Lieu** : dans les connecteurs, sur la clé, avant toute lecture : un document écarté
  ne coûte rien. La passe 1 (§1) connaît déjà toutes les clés. Le plan du run porte un
  ratio par source, l'assemblage donne le sien à chaque connecteur.
- **Annonce** : au démarrage, un avertissement donne les sources partielles et leur
  ratio, un autre les sources écartées à `0` ; après la passe 1, un troisième donne par
  source le nombre retenu sur le total.
- **Bilan** : `run_summaries.sampling` porte, par source, son ratio et le nombre retenu
  sur le total. C'est de la comptabilité : un run `ok` à 10 % ne doit pas passer pour un run
  complet.
- **Limite assumée** : l'échantillon est tiré par document, pas par texte. Un article
  est souvent retenu sans sa section ni son texte, et la plupart de ses arêtes deviennent
  pendantes. Le graphe d'un run partiel n'est pas représentatif.

**10. Limite connue, non traitée : le parse tient dans un thread.** La lecture et le
parse se font dans le thread principal, et Python n'exécute qu'un thread à la fois : le
flux plafonne autour de 380 documents/s, ~1 h 30 pour LEGI, quel que soit le nombre de
workers. On ne sait pas encore si c'est le goulot du run (l'embedding peut l'être) :
`statistics` le dira. Parser dans plusieurs processus demanderait de copier chaque
document d'un processus à l'autre ; ce choix attend les mesures et sa propre ADR.

## Alternatives rejetées

- **Garder trois nœuds Kedro, reliés par des générateurs.** Kedro verrait `connect` et
  `parseDocuments` finir en 0 s, et attribuerait leur temps et leurs erreurs à `ingest`.
  Les compteurs de fin de flux (`document.fetched`, `to_skip`) ne seraient connus que
  pendant `ingest`, par un état mutable partagé entre nœuds. Et une fonction de nœud qui
  contient `yield` est un nœud générateur pour Kedro, qui sauve chaque élément dans la
  sortie : un `MemoryDataset` n'en garderait que le dernier.
- **Clé = `<ID>` lu dans le XML.** Il faudrait lire chaque fichier en passe 1, pour une
  clé que le nom de fichier donne déjà ; la passe 2 contrôle l'égalité.
- **Une file par worker, avec le dispatch par hash.** Un worker bloqué sur un gros
  document remplit sa file et bloque la lecture pendant que les autres attendent. La
  garantie que le hash apportait vient désormais du flux (§3).
- **Partitionner par dossier du texte.** Un indice tiré de l'arborescence, pas des
  données : la composante connexe est la partition exacte.
- **Partitionner par nombre de fichiers.** Les arêtes d'un même chemin viennent de
  fichiers différents : le `<CONTEXTE>` d'un article A donne `T → A` et `S → A`, le
  fichier de sa section S donne `T → S` et `S → A`. Si A et S tombent dans deux lots,
  aucun ne voit `T → S → A`, et `T → A` survit. La réduction rendrait la fermeture.
- **Plafonner la taille d'une composante.** Couper une composante rend sa réduction
  approximative. Le maximum est mesuré à la place.
- **Réduire dans Neo4j, après écriture de toutes les arêtes.** Aucune partition à
  calculer, mais une règle du domaine part en Cypher dans un adaptateur, la gestion des
  cycles est à réécrire, la performance est incertaine sur ~11 M d'arêtes, et les arêtes
  pendantes, absentes de Neo4j, échappent à la réduction puis sont promues non réduites.
- **Les relations en transit dans un fichier JSONL.** Il resterait hors de la saga et de
  sa compensation.
- **Un champ `relations` dans `run_summaries` pour les composantes.** Des tailles dans la
  comptabilité : la frontière du §8 l'interdit.
- **Des moyennes seules.** Muettes sur des distributions à longue traîne.
- **Un ratio approché** (un seuil sur le hash) : ≈ 10 % seulement, et une source d'un
  fichier tombe à 0 ou 1 au hasard. **Les premiers fichiers** : un coin de l'arborescence.
  **Un tirage aléatoire** : un échantillon différent à chaque run, deux runs
  incomparables.
- **Résoudre le débit du parse maintenant** : sans mesure, rien ne dit que c'est le
  goulot (§10).

## Conséquences

- La mémoire d'un run est bornée par quelques documents en phase 1, et par la plus
  grande composante en phase 2.
- Le DAG perd deux nœuds ; kedro-viz montre moins de détail, les logs de progression et
  `statistics` le remplacent.
- `transit_relations` occupe de l'ordre de 5 à 6 Go sur disque pendant un run complet,
  et doit être vide à sa fin.
- Trois collections nouvelles (`MURPHY_DATA.transit_relations`,
  `MURPHY_META.statistics`, `MURPHY_META.collisions`), et `run_summaries` gagne `sampling` : par source, le ratio
  et les nombres retenus sur le total.
- Un run partiel produit beaucoup de relations pendantes : c'est attendu (§9).
- ADR-013 est **amendé** : l'échantillonnage revient, sous la forme d'un ratio et non
  d'une limite N, que la sélection du §9 rend sensée même sur une source d'un fichier.
- ADR-019 §3 est **amendé** : `ingestion_ratio` rejoint les clés de `parameters.yml`, et
  `SAFE_DEV_SETTINGS` met toutes les sources à `1`.
- `CLAUDE.md` et `docs/technical/data/` (`ARCHITECTURE.md`, `reference/pipeline.md`,
  `reference/modele-de-donnees.md`, `reference/telemetrie.md`,
  `reference/configuration.md`) suivent chaque commit qui les touche.

## Mise en œuvre

Chaque commit laisse le pipeline fonctionnel et la CI `python` au vert. Avant le commit 4,
le corpus complet ne passe toujours pas : on y teste à ratio réduit.

| # | Commit | Contenu |
|---|---|---|
| 1 | Statistiques | `Distribution`, `MURPHY_META.statistics`, écriture à la clôture, premières mesures, logs de progression (§8) |
| 2 | Connecteurs | Deux passes LEGI, clé = nom de fichier, `versions.xml` à part, contrôle de l'`<ID>` (§1) |
| 3 | `ingestion_ratio` | Réglage, sélection, avertissements, champs de `run_summaries` (§9) |
| 4 | Phase 1 en flux | Nœud `ingest`, file partagée, arrêt, stats des files (§2, §3) |
| 5 | `transit_relations` | Collection, vidage au démarrage, étape de saga, contrôle de fin (§4, §6) |
| 6 | Écriture Neo4j | `upsert_relations` par lots `UNWIND` (§5) |
| 7 | Phase 2 par composantes | Union-find, réduction par composante, suppression au fil de l'eau (§5) |
| 8 | Promotion | `promotable_for` par lots (§7) |

## Références

ADR-013 (amendé) · ADR-019 §3 (amendé) · ADR-021 (la saga et `unformatted_relations`) ·
`data/src/ragcore/sources/legislatif/file_connector.py` ·
`data/src/ragcore/orchestration/kedro/nodes/connect.py` ·
`data/src/ragcore/application/ingestion_runner.py` ·
`data/src/ragcore/application/resolve_relations.py` ·
`data/src/ragcore/core/services/relation_reduction.py` ·
`data/src/ragcore/adapters/storage/neo4j/graph_repository.py` ·
`data/src/ragcore/adapters/storage/mongo/pending_repository.py` ·
[pipeline.md](../../technical/data/reference/pipeline.md)
