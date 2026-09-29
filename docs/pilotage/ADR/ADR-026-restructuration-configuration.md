# ADR-026 — Restructuration de la configuration en partition workflow / ingestion

**Statut** : ✅ Accepté — 19 juillet 2026
**Version cible** : v0

## Contexte

`data/conf/base/parameters.yml` mêle dans un seul fichier deux natures
de paramètres, distinguées aujourd'hui **par commentaires** seulement :

1. **Hashé** (structurel) — `normalization.version`, `chunking.*`,
   `embedding_model`, `dimension` : entre dans le `WorkflowConfig`, donc
   dans l'empreinte de collection Qdrant. Le changer crée une nouvelle
   collection.
2. **Infra** — provider d'embedding (`.env`), `batch_size`, `timeout`,
   `embedding.enabled` (ADR-023) : n'affecte pas les vecteurs, hors du
   hash.

Le bloc hashé (`W`) détermine le nom de la collection Qdrant. Ce lien
n'est fiable que si la partition est
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
```

Règle invariante : **le bloc `workflow/` ne contient que ce qui est
hashé** ; toute URI, secret, chemin ou paramètre d'infra en est proscrit
(déjà la doctrine de `WorkflowConfig` : « il ne connaît aucune URI, et
il ne peut pas en connaître »). La frontière hashé / non-hashé devient
une frontière de **répertoires**, exécutable et lisible.

**Écart assumé à la lettre du schéma ci-dessus** : les deux dossiers
vivent sous `conf/base/`, pas en frères de `base/`. Kedro
(`OmegaConfigLoader`, `base_env="base"`) ne lit que l'environnement
`base/` par défaut ; des dossiers frères ne seraient simplement jamais
chargés, sauf à ajouter des `config_patterns` dans `settings.py` — une
plomberie de loader évitable sur un refacto dont l'invariant central est
que rien ne doit changer côté chargement. Le glob `parameters*` de Kedro
descend déjà récursivement dans `base/` et fusionne les deux fichiers
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

## Alternatives rejetées

- **Statu quo (partition par commentaires)** : le nom de collection
  repose alors sur une convention non vérifiable ; un paramètre mal placé
  casse l'A/B de chunking en silence.
- **Un seul fichier plat mieux commenté** : ne rend pas la frontière
  exécutable.

## Conséquences

- L'ordre de lecture des params par les hooks Kedro
  (`_build_workflow_config`, `_resolve_embedding_enabled`) a été adapté à
  la nouvelle arborescence, sans changer le `WorkflowConfig` produit —
  **le fingerprint est resté identique** avant/après restructuration
  (`9424808d1c636d533648bbf4e77f2496`), prouvé par
  `golden/test_fingerprint.py` chargeant désormais la config via le
  vrai `OmegaConfigLoader` (fusion multi-fichiers réelle, et non plus un
  `yaml.safe_load` sur un chemin unique).

## Références

ADR-022 (régimes dev/prod) · ADR-023 (interrupteur d'embedding) ·
ADR-039 (contrat ingestion ↔ serving) · `WorkflowConfig`
(`data/src/ragcore/core/config/workflow.py`) · cliquet
`golden/test_fingerprint.py`
