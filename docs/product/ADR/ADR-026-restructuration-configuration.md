# ADR-026 — Restructuration de la configuration en partition workflow / ingestion / evaluation

**Statut** : 🔶 Proposé — 19 juillet 2026
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
conf/
├── workflow/          ← le WorkflowConfig hashé (bloc W)
│   ├── normalization/
│   ├── chunking/
│   └── embedding/     ← model + dimension (jamais le provider)
├── ingestion/         ← infra propre à l'ingestion (tokenizing,
│                         relations, provider, batch, timeout, enabled)
└── evaluation/        ← runtime de récupération (bloc R) — consommé
                          par P2, pas par l'ingestion
```

Règle invariante : **le bloc `workflow/` ne contient que ce qui est
hashé** ; toute URI, secret, chemin ou paramètre d'infra en est proscrit
(déjà la doctrine de `WorkflowConfig` : « il ne connaît aucune URI, et
il ne peut pas en connaître »). La frontière hashé / non-hashé devient
une frontière de **répertoires**, exécutable et lisible.

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
  nouvel item backlog **B-14**. P2 (B-13) en dépend.
- L'ordre de lecture des params par les hooks Kedro
  (`_build_workflow_config`) doit être adapté à la nouvelle arborescence,
  sans changer le `WorkflowConfig` produit — **le fingerprint d'une même
  config doit rester identique** avant/après restructuration (test de
  non-régression du fingerprint).
- Le désalignement connu « le backend lit `MONGODB_COLLECTION` défaut
  `chunks` » (ARCHITECTURE.md) est un candidat naturel à résorber dans le
  même geste, mais reste hors périmètre strict de cet ADR.

## Références

ADR-022 (régimes dev/prod) · ADR-023 (interrupteur d'embedding) ·
ADR-027 (plateforme end-to-end) · `WorkflowConfig`
(`data/src/ragcore/core/config/workflow.py`) · cliquet
`golden/test_fingerprint.py` · ARCHITECTURE.md (contrats ingestion↔serving)
