# ADR-043 — Configuration de l'ingestion : un fichier, un bloc `dev`, `ENVIRONMENT` seul arbitre

**Statut** : ✅ Accepté (30 septembre 2026) — amende ADR-022 §5-§6, ADR-023 et ADR-042 §3 · **§4 amendé le 30 septembre 2026** (labels Neo4j déclarés par les sources)

## Contexte

Kedro sépare ses réglages par environnement : un dossier `conf/<env>/` superposé à
`conf/base/`, choisi par `kedro run --env`. L'ingestion ne s'en sert pas.
`CONFIG_LOADER_ARGS = {"base_env": "base"}` (`data/src/data/settings.py`) retire
l'environnement d'exécution par défaut (`local`), et la variable `ENVIRONMENT` (`.env.dev`)
en tient lieu, arbitrée dans le code (`run_parameters.resolve_dev_settings`). Ce choix a
été hérité, jamais tranché.

Ce qu'il décide, les ADR précédents le supposent sans l'écrire, et ils ont dérivé du code
(critique de `parameters.yml`, P19 à P22) :

- ADR-042 §3 range la découpe et le modèle d'embedding dans
  `conf/base/ingestion/parameters.yml`. Le sous-dossier a disparu, et le modèle n'est plus
  lu du YAML.
- ADR-022 §5 prévoyait d'exposer le routage d'audit dans `parameters.yml`. Il est resté
  dans le code.
- ADR-023 ne dit pas que l'interrupteur d'embedding ne vaut qu'en dev, et un second
  interrupteur a existé à côté de lui (`EMBEDDING_PROVIDER=noop`).

`ENVIRONMENT` ne concerne que `data/` : le backend tire `NODE_ENV` de sa cible de build.

## Décision

**1. Pas d'environnement Kedro.** Un seul fichier de réglages, `conf/base/parameters.yml`,
sans surcouche ni `--env`.

**2. `ENVIRONMENT` vaut `dev` ou `prod`.** Absente ou vide, elle vaut `prod`. Toute autre
valeur (`Dev`, `development`…) arrête le run au chargement de la configuration, avant
tout nœud (`InfraSettings.environment`). Tout ce qui n'est pas un poste de développement
est `prod`.

**3. Ce qui diffère entre dev et prod vit dans le bloc `dev`.** En `dev`, le bloc
s'applique tel quel ; en `prod`, il est remplacé par des valeurs sûres
(`SAFE_DEV_SETTINGS` : rien n'est effacé, l'embedding est calculé, les métadonnées des
balises non configurées sont retirées, les nœuds Neo4j restent maigres) et un
avertissement le signale au log. Ses clés sont obligatoires et validées dans les deux
environnements : une coquille arrête le run même en prod.

**4. Ce qui vaut partout est hors du bloc** : `chunking`.

> **Amendement (30 septembre 2026)** : `node_labels` en est sorti. Un label Neo4j est un
> fait de schéma, pas un réglage : le changer demande `nuke_all`, puisque l'écriture
> ajoute un label sans retirer l'ancien. Chaque source le déclare dans le registre
> (`SourceDefinition.node_labels`), et un préfixe qu'aucune source ne déclare reçoit
> `Document` (critique de `parameters.yml`, P15).

## Alternatives rejetées

- **Une surcouche `conf/prod/`.** Une surcouche change des valeurs ; elle ne sait pas
  ignorer un bloc. Et oublier `--env prod` retombe sur `base`, c'est-à-dire sur les
  valeurs de dev : le défaut ouvrirait la trappe.
- **Une surcouche `conf/dev/`, `base` sûr.** Le défaut serait sûr, mais deux notions
  d'environnement, `--env` et `ENVIRONMENT`, seraient à garder alignées.
- **Arrêter le run quand `nuke_all` est vrai hors dev** (l'ancien
  `NukeAllOutsideDevError`). Un même fichier ne pourrait pas servir aux deux
  environnements, alors que les valeurs sûres suffisent à protéger la prod.
- **`ENVIRONMENT` en chaîne libre** (l'état antérieur). Une coquille valait prod en
  silence : le bloc `dev` était ignoré sans que rien ne s'arrête.

## Amendements

**ADR-022.**

- §1 s'applique tel qu'écrit : hors dev, les métadonnées des balises non configurées sont
  toujours retirées ; le compteur `tag.unconfigured` est émis dans les deux régimes.
- §5 : le routage d'audit (`EventBehavior`) reste dans `EVENT_CATALOG`. C'est un fait sur
  chaque type d'événement, pas un réglage qu'un opérateur change d'un run à l'autre ; son
  exposition dans `parameters.yml` est retirée.
- §6 est étendu : toute la configuration morte a été supprimée, pas seulement
  `field_mappings`, et le modèle strict du fichier (`IngestionParameters`) refuse les clés
  inconnues, ce qui l'empêche de revenir.

**ADR-023.**

- L'interrupteur s'appelle `dev.embedding_enabled`. Il n'a d'effet qu'en `dev` : la prod
  calcule toujours l'embedding.
- Il est le seul : `EMBEDDING_PROVIDER` et son fournisseur `noop`, qui écrivait par défaut
  des vecteurs nuls, ont disparu. TEI est le seul embedder.

**ADR-042.**

- §3 : `chunking` vit dans `conf/base/parameters.yml`, à la racine. Il n'y a plus de bloc
  `embedding` : le modèle vient d'`EMBEDDING_MODEL`, la variable que lisent aussi TEI et
  le backend, et la dimension est mesurée auprès de TEI au démarrage. Il ne reste rien de
  la partition d'ADR-026.
- La précondition TEI (`GET /info`) compare le modèle servi à `EMBEDDING_MODEL`, non plus
  à `parameters.yml`.

## Conséquences

- Il n'y a pas de surcouche de valeurs pour la prod. Un réglage qui doit différer entre
  les deux environnements va dans le bloc `dev`, avec sa valeur sûre dans
  `SAFE_DEV_SETTINGS`, ou dans l'environnement (`.env.dev`).
- Un troisième environnement (staging, recette) demande d'amender cet ADR : aujourd'hui,
  il est `prod`.

## Références

ADR-022 (régimes dev/prod) · ADR-023 (interrupteur d'embedding) · ADR-026 (partition de
la configuration, remplacé) · ADR-042 (collection au nom fixe) ·
`run_parameters.resolve_dev_settings` · `InfraSettings.environment` ·
`docs/pilotage/WIP/critique-parameters.md` (P19 à P22)
