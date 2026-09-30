# ADR-042 — Une collection Qdrant au nom fixe : fin de l'empreinte, du pointeur et du tracking

**Statut** : ✅ Accepté (30 septembre 2026) — remplace ADR-026, amende ADR-039 §3 · **§3 amendé par [ADR-043](ADR-043-configuration-ingestion-environment.md)** (fichier unique, modèle lu d'`EMBEDDING_MODEL`)

## Contexte

L'ingestion nommait sa collection Qdrant par une **empreinte** de sa configuration
(`WorkflowConfig` : normalisation, chunking, modèle d'embedding). Changer un réglage
créait une collection neuve, et les deux coexistaient : le but était de comparer des
stratégies (A/B).

Ce mécanisme en portait trois autres :

- une **partition de la configuration** en deux fichiers (ADR-026), pour que seul le
  « hashé » entre dans l'empreinte ;
- un **pointeur** Mongo (`MURPHY_META.meta_published_collection`), publié par les seuls
  runs `ok` et lu par le backend au boot, puisque le serving ne pouvait pas deviner un
  nom de collection (ADR-039 §3) ;
- un **tracker d'expériences** (MLflow), dont le run-id était l'empreinte, pour relire
  les paramètres qu'un hash ne dit pas.

Aucune comparaison A/B n'est prévue avant longtemps. Le projet paie donc ce système
(quatre modules, un test golden, une dépendance optionnelle, une lecture Mongo au boot du
backend) sans s'en servir.

## Décision

**1. Un nom fixe.** La collection Qdrant s'appelle `QDRANT_COLLECTION`, une variable
obligatoire de `.env.dev`. L'ingestion (`InfraSettings.qdrant_collection`) et le backend
(`config.qdrant.collection`) lisent la même variable du même fichier.

**2. Plus de pointeur.** `PublishedCollection`, `CollectionPublisher`, leur port, leur
dépôt Mongo et `backend/src/infra/collectionPointer.ts` sont supprimés. Au boot, le
backend vérifie seulement que la collection existe (`assertCollectionExists`) et refuse
de démarrer sinon.

**3. Plus d'empreinte ni de `WorkflowConfig`.** Le paquet `core/config/` et
`conf/base/workflow/parameters.yml` sont supprimés. La découpe et le modèle d'embedding
deviennent deux blocs de `conf/base/ingestion/parameters.yml` (`chunking`, `embedding`),
lus en deux objets typés (`core/models/processing.py`), obligatoires et sans défaut dans
le code. `normalization.version` et `chunking.strategy`, qui ne servaient qu'au hash,
disparaissent.

**4. Plus de tracking.** Le port `ExperimentTracker`, les adaptateurs MLflow et `noop`,
l'extra `tracking` et les variables `TRACKING_PROVIDER` / `MLFLOW_TRACKING_URI` sont
supprimés.

## Alternatives rejetées

- **Garder le pointeur comme témoin d'un run `ok`.** Avec une seule collection réécrite
  en place, un run `degraded` a déjà écrit dans la collection servie : le pointeur ne
  protégerait plus rien.
- **Une constante dans le code.** Deux littéraux, en Python et en TypeScript, à garder
  synchrones à la main. Le fichier `.env.dev` est déjà la source commune des deux côtés.
- **Garder le tracking, identifié par le `run_id`.** Sans collections à comparer, il
  répète le bilan de run déjà persisté (`meta_run_summaries`).

## Conséquences

- **Changer le chunking ou le modèle d'embedding impose de réingérer tout le corpus**
  (`nuke_all` en dev). Rien ne sépare plus les anciens vecteurs des nouveaux : un run
  partiel après un tel changement mélange deux jeux de vecteurs incomparables.
- **Un run incomplet est servi.** Un run `degraded` ou `failed` laisse son corpus dans la
  collection que le backend interroge ; le bilan de run le dit, rien ne l'empêche.
- La précondition TEI (`GET /info`) reste : le modèle de `parameters.yml` doit être celui
  que sert le conteneur.
- Le document `meta_published_collection` et les collections Qdrant nommées par une
  empreinte, écrits par les runs précédents, ne sont plus lus. `nuke_all` supprime
  toutes les collections Qdrant ; le document Mongo est à supprimer à la main.
- Le backend ne lit plus la base `MURPHY_META`.

## Références

ADR-026 (partition de la configuration, remplacé) · ADR-039 (contrat ingestion ↔ serving,
§3 amendé) · ADR-043 (amende §3)
