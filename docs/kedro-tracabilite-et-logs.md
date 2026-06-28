# Traçabilité des données et structure des logs d'erreur dans le pipeline Kedro

## Vue d'ensemble

Dans ce projet, la traçabilité des données dans le pipeline Kedro repose sur quatre mécanismes complémentaires :

1. la persistance des données intermédiaires par couche dans le catalogue Kedro ;
2. l'enregistrement des événements d'exécution du pipeline ;
3. la conservation de métriques de pipeline dans la couche de reporting ;
4. la centralisation des erreurs dans un registre JSONL.

Cette combinaison permet de suivre à la fois :

- le cheminement d'un document entre les différentes étapes du traitement ;
- les jeux de données chargés et sauvegardés ;
- les nœuds exécutés et leur durée ;
- les erreurs rencontrées, avec leur contexte métier et technique.

## 1. Traçabilité des données dans le pipeline Kedro

### 1.1. Persistance par couches via le Data Catalog

Le catalogue Kedro définit explicitement les principaux artefacts du pipeline. Chaque étape produit un dataset persistant dans un répertoire dédié, ce qui permet de reconstituer le cycle de transformation des données.

Les couches principales observées sont les suivantes :

- `raw_documents` dans `data/raw`
- `validated_documents` dans `data/validated`
- `enriched_documents` dans `data/enriched`
- `cleaned_documents` dans `data/cleaned/cleaned_documents`
- `chunked_documents` dans `data/chunks/chunked_documents`
- `embedded_chunks` dans `data/embeddings/embedded_chunks`

Cette organisation permet de savoir à tout moment dans quelle couche se situe un document donné, et à quelle étape de traitement il correspond.

### 1.2. Journal des événements d'exécution Kedro

Le fichier `.viz/kedro_pipeline_events.json` conserve des événements techniques relatifs au déroulement du pipeline. On y trouve notamment :

- `before_pipeline_run`
- `after_dataset_loaded`
- `after_node_run`
- `after_dataset_saved`
- `after_pipeline_run`

Ces événements permettent de suivre chronologiquement :

- le démarrage et la fin d'un run ;
- les datasets chargés ;
- les nœuds exécutés ;
- les datasets produits.

Exemple d'événements enregistrés :

```json
[
  {
    "event": "before_pipeline_run",
    "timestamp": "2026-02-17T23:30:25.397817+00:00"
  },
  {
    "event": "after_dataset_loaded",
    "dataset": "xml_files",
    "node_id": "a706c3d4",
    "status": "Available",
    "size": 0
  },
  {
    "event": "after_node_run",
    "node": "extract_raw_data",
    "node_id": "ac7287e8",
    "duration": 1.1973231810043217,
    "status": "success"
  },
  {
    "event": "after_dataset_saved",
    "dataset": "raw_documents",
    "node_id": "7099fbc9",
    "status": "Available",
    "size": 0
  }
]
```

### 1.3. Reporting de métriques

Le catalogue déclare également un dataset `pipeline_metrics` écrit dans `data/meta_reporting/pipeline_metrics.json`.

Ce fichier constitue un point d'ancrage pour la traçabilité d'exécution au niveau global du pipeline, en complément des événements détaillés de Kedro.

### 1.4. Registre centralisé des erreurs

La configuration du projet active un registre d'erreurs centralisé :

- `registry_enabled: true`
- `registry_path: "data/meta_reporting/errors.jsonl"`
- `rotation_mode: "date"`
- `keep_document_snapshots: false`
- `keep_tracebacks: true`

Ce registre est alimenté par les nœuds du pipeline au moment où une erreur survient. Il associe chaque erreur à une étape, à une partition, et si possible à un identifiant ELI.

Le mécanisme de rotation par date produit des fichiers du type :

- `errors_2026-02-14.jsonl`

### 1.5. Conservation des éléments de reporting

Le pipeline de maintenance ne supprime pas la couche de reporting. Les métriques et les journaux d'erreur sont donc conservés d'un run à l'autre, ce qui renforce la continuité de la traçabilité.

## 2. Structure des messages de logs d'erreur

Le projet utilise deux formats complémentaires pour les erreurs :

1. un log texte structuré destiné à la lecture humaine et au débogage immédiat ;
2. un registre JSONL destiné à la persistance et à l'analyse structurée.

### 2.1. Format du log texte structuré

La fonction `log_error()` construit les messages sous la forme suivante :

```text
[timestamp_iso] [step] ELI=<eli> ERROR_TYPE=<error_type> MESSAGE=<message>
```

Ce message est ensuite injecté dans le format général du logger Python :

```text
asctime - logger_name - level - message
```

Un log complet ressemble donc à ceci :

```text
2026-02-13 11:01:57,451 - data.utils.logging - ERROR - [2026-02-13T11:01:57.451023] [clean_text] ELI=LEGIARTI000006219120 ERROR_TYPE=cleaning_error MESSAGE=Failed to clean document text: 'EnrichedDocument' object has no attribute 'content'
Traceback (most recent call last):
  File "/home/eyebrow/Documents/Murphy/data/src/data/pipelines/preprocessing/cleaning/nodes.py", line 57, in clean_text_content
    for field_name, text_value in doc.content.texts.items():
                                  ^^^^^^^^^^^
AttributeError: 'EnrichedDocument' object has no attribute 'content'
```

Ce format contient donc :

- l'horodatage du logger ;
- le nom du logger ;
- le niveau (`ERROR` ou `WARNING`) ;
- un timestamp ISO interne ;
- le nom de l'étape du pipeline ;
- l'identifiant ELI si disponible ;
- le type d'erreur ;
- un message lisible ;
- éventuellement la traceback complète.

À noter que certaines erreurs non critiques, comme `missing_eli` ou `empty_content`, sont journalisées en niveau `WARNING` plutôt qu'en `ERROR`.

### 2.2. Format du registre d'erreurs JSONL

Le registre centralisé écrit une entrée JSON par ligne. La structure de base est la suivante :

```json
{
  "timestamp": "<timestamp_iso>",
  "step": "<pipeline_step>",
  "partition_id": "<partition_id>",
  "eli": "<eli_or_null>",
  "error_type": "<error_type>",
  "message": "<human_readable_message>",
  "document_snapshot": null,
  "traceback": "<optional_traceback>"
}
```

Les champs principaux ont le rôle suivant :

- `timestamp` : date et heure ISO de l'erreur ;
- `step` : étape du pipeline où l'erreur s'est produite ;
- `partition_id` : identifiant de la partition ou du fichier traité ;
- `eli` : identifiant métier du document, s'il est connu ;
- `error_type` : catégorie de l'erreur ;
- `message` : message de diagnostic ;
- `document_snapshot` : instantané optionnel du document ;
- `traceback` : trace Python complète si une exception a été capturée.

## 3. Exemples concrets cités

### 3.1. Exemple de log texte d'erreur

```text
2026-02-13 11:01:57,451 - data.utils.logging - ERROR - [2026-02-13T11:01:57.451023] [clean_text] ELI=LEGIARTI000006219120 ERROR_TYPE=cleaning_error MESSAGE=Failed to clean document text: 'EnrichedDocument' object has no attribute 'content'
Traceback (most recent call last):
  File "/home/eyebrow/Documents/Murphy/data/src/data/pipelines/preprocessing/cleaning/nodes.py", line 57, in clean_text_content
    for field_name, text_value in doc.content.texts.items():
                                  ^^^^^^^^^^^
AttributeError: 'EnrichedDocument' object has no attribute 'content'
```

Analyse de l'exemple :

- étape concernée : `clean_text` ;
- document concerné : `LEGIARTI000006219120` ;
- type d'erreur : `cleaning_error` ;
- cause immédiate : tentative d'accès à l'attribut `content` sur un objet `EnrichedDocument` qui ne le possède pas.

### 3.2. Exemple d'entrée dans le registre JSONL

```json
{"timestamp": "2026-02-14T17:51:17.608746", "step": "extraction", "partition_id": "LEGI_20250712-211706/20250712-211706/legi/global/eli/decret/2015/4/3/DEFH1426725D/jo/article_43/versions", "eli": null, "error_type": "missing_eli", "message": "No ELI found for file /mnt/data/Murphy/src/LEGI/LEGI_20250712-211706/20250712-211706/legi/global/eli/decret/2015/4/3/DEFH1426725D/jo/article_43/versions.xml", "document_snapshot": null}
```

Analyse de l'exemple :

- étape concernée : `extraction` ;
- partition concernée : chemin logique complet du fichier XML ;
- ELI : absent (`null`) ;
- type d'erreur : `missing_eli` ;
- cause : impossibilité d'extraire un identifiant ELI depuis le fichier traité.

## 4. Conclusion

La traçabilité du pipeline Kedro est assurée par l'articulation de plusieurs briques complémentaires :

- le catalogue Kedro, qui matérialise les transformations par couche ;
- les événements d'exécution, qui décrivent le déroulement technique du run ;
- les métriques de pipeline, qui synthétisent les résultats globaux ;
- le registre centralisé des erreurs, qui conserve le détail des anomalies par étape et par partition.

La structure des logs d'erreur est cohérente avec cet objectif de traçabilité :

- le log texte facilite l'analyse humaine et le débogage ;
- le registre JSONL facilite l'exploitation systématique et la recherche ciblée.

En l'état du dépôt, c'est donc principalement cette combinaison catalogue + événements Kedro + reporting + registre d'erreurs qui assure la traçabilité opérationnelle des données.