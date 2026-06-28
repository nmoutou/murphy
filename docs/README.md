# Murphy — Chatbot RAG pour LEGIFRANCE

## 🎯 Objectif

Murphy est un assistant de recherche juridique basé sur une architecture **RAG**
(Retrieval-Augmented Generation) pour interroger les données juridiques de LEGIFRANCE.
Un utilisateur pose une question ; le backend l'embed, fait une recherche sémantique sur
des chunks de documents juridiques, récupère le contenu correspondant, puis streame une
réponse générée par un LLM accompagnée des sources qui l'ont informée.

Le système est **stateless par conception** : chaque requête recompute tout le pipeline,
aucun historique conversationnel n'est stocké côté serveur, et il n'y a pas de retry
automatique (fail-fast avec erreur claire).

## 🏗️ Architecture générale

- **Frontend** : Next.js 16 (App Router) + React 19 + Tailwind v4 — interface de chat.
- **Backend** : Express 5 + TypeScript — l'orchestrateur RAG (le gros de la logique).
- **Embeddings** : service TEI (HuggingFace Text Embeddings Inference, GPU).
- **LLM** : API externe OpenAI-compatible (type Mammouth.AI), en streaming.
- **Bases de données** :
  - **MongoDB** : contenu des chunks (sert à construire le contexte LLM).
  - **Qdrant** : index vectoriel pour la recherche sémantique.
  - **Neo4j** : provisionné, réservé à un enrichissement graphe futur (non câblé).

> Les bases sont supposées **pré-peuplées**. Le pipeline d'ingestion LEGIFRANCE ne fait
> **pas** partie de ce dépôt.

## 🚀 Démarrage rapide

La stack complète tourne via Docker Compose. Les scripts racine (qui requièrent un fichier
`.env.dev`, gitignoré) l'enveloppent :

```bash
npm run up      # build + démarre la stack dev (détaché)
npm run watch   # idem, au premier plan (logs)
npm run logs    # suivre les logs
npm run status  # tableau de statut des conteneurs
npm run down    # tout arrêter
```

Ports dev : frontend `3000`, backend `5000`, Qdrant `6333`, MongoDB `27017`,
Neo4j `7474`/`7687`, service d'embedding `5001→80`.

> Le service d'embedding requiert un **GPU NVIDIA**. Sans GPU, lancez backend et frontend
> en local et pointez les variables d'environnement vers des services accessibles.
> Voir [SETUP.md](SETUP.md) pour le détail (dev sans Docker, variables d'environnement).

## 📊 Flux d'une requête

1. L'utilisateur pose une question via le frontend (transport **WebSocket**).
2. Le backend :
   - extrait la question du dernier message `user` ;
   - l'embed via TEI ;
   - fait une recherche top-K dans Qdrant ;
   - **streame d'abord les sources** (chaque hit), puis récupère leur contenu dans MongoDB ;
   - construit le contexte et appelle le LLM en streaming.
3. La réponse est streamée token par token, suivie des métriques de latence (`ragTiming`).
4. Le frontend affiche progressivement la réponse, sources en tête.

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — schémas et description du pipeline RAG.
- **[API.md](API.md)** — endpoints, transports (WS/SSE) et contrat de parts.
- **[SETUP.md](SETUP.md)** — configuration, exécution et variables d'environnement.
- **[DEPENDENCIES.md](DEPENDENCIES.md)** — paquets et images Docker.
- **[STATUS.md](STATUS.md)** — état d'implémentation.
- **[ROADMAP.md](ROADMAP.md)** / **[BETA.md](BETA.md)** — trajectoire produit.

## 🔑 Concepts clés

- **RAG** : recherche d'information + génération LLM pour des réponses contextualisées
  et sourcées.
- **Transports** : un seul pipeline (`createChatStream`) exposé en WebSocket (utilisé par
  le frontend), SSE et JSON non-streamé.
- **Parts UI Message** (Vercel AI SDK) : le flux est une séquence de parts typées
  (`data-document` pour les sources, `text-delta` pour les tokens, `finish` pour les
  métriques).
- **Embeddings** : représentations vectorielles permettant une recherche par similarité
  sémantique.
