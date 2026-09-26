# ADR-026 — Restructuration de la configuration en partition workflow / ingestion / evaluation

**Statut** : ✅ Accepté — 19 juillet 2026 (implémenté par B-14)
**Version cible** : v0 (prérequis P1 de la plateforme P2)

## Contexte

`data/conf/base/parameters.yml` mêle dans un seul fichier trois natures
de paramètres, distinguées aujourd'hui **par commentaires** seulement :

1. **Hashé** (structurel) — `normalization.version`, `chunking.*`,
   `embedding_model`, `dimension` : entre dans le `WorkflowConfig`, donc
   dans l'empreinte de collection Qdrant. Le changer crée une nouvelle
   collection.
2. **Infra** — provider d'embedding (`.env`), `batch_size`, `timeout`,
   `embedding.enabled` (ADR-023) : n'affecte pas les vecteurs, hors du
   hash.
3. **Runtime de récupération** — top-K, seuil, fusion, rerank, graphe :
   n'existe pas encore côté ingestion, vit côté serving/évaluation.

La plateforme P2 (ADR-027) fait du bloc hashé (`W`) à la fois l'entrée
qu'elle passe à l'ingestion et la clé qu'elle hashe pour retrouver la
collection. Ce couplage n'est fiable que si la partition est
**structurelle** (des groupes de fichiers), pas implicite (des
commentaires) : sinon rien n'empêche un paramètre hashé de fuiter dans
l'infra, ou l'inverse — ce que le cliquet `golden/test_fingerprint.py`
signale déjà a posteriori, mais que la structure doit prévenir a priori.

## Décision

Restructurer `conf/` en **partition explicite par nature** :

```
conf/base/
├── workflow/parameters.yml     ← le WorkflowConfig hashé (bloc W) :
│                                  normalization.version, chunking.*,
│                                  embedding_model + dimension (jamais
│                                  le provider)
├── ingestion/parameters.yml    ← infra propre à l'ingestion (tokenizing,
│                                  relations, embedding_runtime : batch,
│                                  timeout, enabled ; exportation, maintenance)
└── evaluation/parameters.yml   ← runtime de récupération (bloc R) — consommé
                                   par P2, pas par l'ingestion (placeholder à B-14)
```

Règle invariante : **le bloc `workflow/` ne contient que ce qui est
hashé** ; toute URI, secret, chemin ou paramètre d'infra en est proscrit
(déjà la doctrine de `WorkflowConfig` : « il ne connaît aucune URI, et
il ne peut pas en connaître »). La frontière hashé / non-hashé devient
une frontière de **répertoires**, exécutable et lisible.

**Écart assumé à la lettre du schéma ci-dessus** : les trois dossiers
vivent sous `conf/base/`, pas en frères de `base/`. Kedro
(`OmegaConfigLoader`, `base_env="base"`) ne lit que l'environnement
`base/` par défaut ; des dossiers frères ne seraient simplement jamais
chargés, sauf à ajouter des `config_patterns` dans `settings.py` — une
plomberie de loader évitable sur un refacto dont l'invariant central est
que rien ne doit changer côté chargement. Le glob `parameters*` de Kedro
descend déjà récursivement dans `base/` et fusionne les trois fichiers
en un seul dict, sans aucune modification de `settings.py`. L'esprit de
la décision (frontière par nature rendue exécutable, au niveau
répertoire) est tenu ; seule la position exacte des dossiers diffère du
schéma initial.

Les blocs `formatting` et `embedding` du `parameters.yml` d'origine
étaient **mixtes** (hashé + infra dans la même clé top-level) ; Kedro
interdit qu'une clé top-level soit scindée entre deux fichiers d'un même
env (`_check_duplicates`). La partition a donc nécessité un
**re-nesting** : le hashé migre sous une clé `workflow:` dédiée,
l'infra d'embedding sous `embedding_runtime:` — plutôt qu'un simple
déplacement de fichiers à forme inchangée.

P2 **réplique** le schéma du bloc `workflow/` dans sa propre
`conf/workflow/` (ADR-027) et vérifie la correspondance par fingerprint
— aucun partage physique de fichiers entre submodules.

## Alternatives rejetées

- **Statu quo (partition par commentaires)** : le couplage config↔éval
  d'ADR-027 repose alors sur une convention non vérifiable ; un paramètre
  mal placé casse l'A/B en silence.
- **Un seul fichier plat mieux commenté** : ne rend pas la frontière
  exécutable ; ne se compose pas pour le sweep.
- **Socle `conf/workflow/` partagé physiquement entre `data/` et
  `evaluation/`** : franchit la frontière des submodules (rejeté aussi
  par ADR-027).

## Conséquences

- Chantier **P1** (touche l'ingestion), en amont de la plateforme P2 —
  item backlog **B-14** (✅). P2 (B-13) en dépend.
- L'ordre de lecture des params par les hooks Kedro
  (`_build_workflow_config`, `_resolve_embedding_enabled`) a été adapté à
  la nouvelle arborescence, sans changer le `WorkflowConfig` produit —
  **le fingerprint est resté identique** avant/après restructuration
  (`9424808d1c636d533648bbf4e77f2496`), prouvé par
  `golden/test_fingerprint.py` chargeant désormais la config via le
  vrai `OmegaConfigLoader` (fusion multi-fichiers réelle, et non plus un
  `yaml.safe_load` sur un chemin unique).
- Le désalignement connu « le backend lit `MONGODB_COLLECTION` défaut
  `chunks` » (ARCHITECTURE.md) est un candidat naturel à résorber dans le
  même geste, mais reste hors périmètre strict de cet ADR.

## Références

ADR-022 (régimes dev/prod) · ADR-023 (interrupteur d'embedding) ·
ADR-027 (plateforme end-to-end) · `WorkflowConfig`
(`data/src/ragcore/core/config/workflow.py`) · cliquet
`golden/test_fingerprint.py` · ARCHITECTURE.md (contrats ingestion↔serving)
