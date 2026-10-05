<p align="center">
  <img src="frontend/public/img/logo.png" alt="Murphy" width="350">
</p>

Retrouver la décision ou l'article de loi qui répond à une question suppose, sur
Légifrance, de connaître déjà les bons mots-clés. Murphy prend la question en langage
naturel, retrouve les passages pertinents dans les codes, les lois et la jurisprudence
publiés par la DILA, et rédige une réponse qui cite ses sources.

<p align="center">
  <img src="docs/screenshots/accueil.png" alt="Écran d'accueil de Murphy" width="800">
</p>

<p align="center">
  <img src="docs/screenshots/reponse-sources.png" alt="Une réponse de Murphy et les documents sources qu'elle cite" width="800">
</p>

## Architecture

### Vue d'ensemble

```mermaid
flowchart TD
    LEGI[("<b>LEGIFRANCE</b><br>Fichiers XML")]
    PIPE["<b>Pipeline d'ingestion</b><br>Python (Kedro)"]
    MONGO[("<b>BDD (orientée objet)</b><br>MongoDB")]
    NEO[("<b>BDD (orientée graphe)</b><br>Neo4j")]
    EMB["<b>Embedding</b><br>Python (TEI)"]
    QDRANT[("<b>BDD (vectorielle)</b><br>Qdrant")]
    BACK["<b>Backend</b><br>Node.js, Express"]
    LLM["<b>LLM</b><br>API compatible OpenAI"]
    FRONT["<b>Frontend</b><br>React, Next.js"]

    LEGI -->|"Ouverture, extraction,<br>nettoyage et formatage<br>des données"| PIPE
    PIPE -->|"Ingestion des<br>documents"| MONGO
    PIPE -->|"Ingestion des<br>relations"| NEO
    PIPE <-->|"Vectorisation<br>des passages"| EMB
    PIPE -->|"Ingestion des<br>vecteurs"| QDRANT
    NEO -.->|"Vectorisation<br>(à suivre)"| EMB
    BACK <-->|"Vectorisation<br>de la question"| EMB
    QDRANT -->|"Passages les<br>plus proches"| BACK
    MONGO -->|"Texte des<br>passages"| BACK
    BACK <-->|"Rédaction de<br>la réponse"| LLM
    BACK <-->|"↑ Contrôle<br>↓ Affichage"| FRONT
```

<p align="center"><i>Figure 1 - Le trajet des données</i></p>

L'ingestion découpe les documents en passages, les vectorise et les écrit dans les
bases. Le backend peut ensuite les lire. Les deux ne partagent aucun code, seulement les
bases de données. Neo4j garde le graphe des relations entre documents (citations, textes et leurs articles), que le backend exploitera dans une version future.

### Pipeline d'ingestion

```mermaid
flowchart TD
    LEGI[(LEGIFRANCE)]
    A["1. Extraction"]
    B["2. Validation"]
    C["3. Normalisation"]
    D["4. Nettoyage"]
    E["5. Tokenization / Chunking"]
    F["6. Embedding (TEI)"]
    G["7a. Upload Qdrant"]
    H["7b. Upsert MongoDB"]
    I["7c. Upsert Neo4j"]
    QDRANT[(Qdrant)]
    MONGO[(MongoDB)]
    NEO[(Neo4j)]

    LEGI --> A --> B --> C --> D
    D --> E
    D --> H
    D --> I
    E --> F --> G --> QDRANT
    H --> MONGO
    I --> NEO
```

<p align="center"><i>Figure 2 - Les étapes d'un run d'ingestion</i></p>

La documentation technique est dans [docs/technical/](docs/technical/ARCHITECTURE.md),
les décisions d'architecture dans [docs/pilotage/ADR/](docs/pilotage/ADR/INDEX.md).

## Stack technique

| Partie | Technologies |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, AI SDK |
| Backend | Node.js 22, Express, TypeScript, WebSocket (`ws`), Pino |
| Contrat partagé | zod, paquet npm interne `@murphy/contract` |
| Ingestion | Python 3.13, Kedro, Pydantic, uv |
| Données | MongoDB 8, Qdrant 1.16, Neo4j 2025 |
| Embeddings | Text Embeddings Inference (Hugging Face), `all-mpnet-base-v2` |
| Outillage | Docker Compose, GitHub Actions, ESLint, Vitest, Jest, Ruff, mypy, pytest |

## Lancer le projet

### Prérequis

- Docker et Docker Compose
- un GPU NVIDIA et le NVIDIA Container Toolkit, pour le service d'embedding
- Node.js et uv
- Une clé d'API pour un LLM exposant une API compatible OpenAI

### 1. Installer et configurer

```bash
npm install                  
cp .env.example .env.dev
```

Dans `.env.dev`, renseigner au minimum `LLM_API_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`,
et `XML_SOURCE_PATH`, le chemin **absolu** du corpus.

### 2. Télécharger le corpus

Les archives XML sont sur <https://echanges.dila.gouv.fr/OPENDATA/>, un dossier par
base. Extraire chaque archive de stock dans un sous-répertoire de `XML_SOURCE_PATH`
portant le nom de la base :

```
$XML_SOURCE_PATH/
├── LEGI/
├── CASS/
├── INCA/
├── CAPP/
├── JADE/
└── CONSTIT/
```

### 3. Démarrer les services

```bash
npm run up
```


### 4. Ingérer le corpus

```bash
cd data
kedro run                          # toutes les six bases
kedro run --params source=legi     # une seule base
```

### 5. Ouvrir l'application

Le frontend est sur <http://localhost:3000>, l'API sur <http://localhost:5000/api/v1>. </br>
`npm run status` liste l'état des conteneurs. </br> `npm run down` arrête la stack.

## Licence

Code : tous droits réservés. </br> Les données juridiques proviennent de la DILA et sont sous Licence Ouverte 2.0.
