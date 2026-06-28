# Beta-test — Synthèse & backlog (sans dates)

Ce document synthétise ce qui manque pour démarrer une phase de **beta-test** et propose un **backlog ordonné par dépendances**, sans dates.

## Objectif beta (définition minimale)

- Valider le **parcours de bout en bout** : question utilisateur → pipeline RAG → réponse + sources.
- Avoir un environnement **reproductible** (Docker) et **diagnosticable** (logs/health) pour itérer vite.

## Scope BETA (verrouillée — v1)

### Objectifs principaux
- **Valider la valeur** : les réponses sont jugées utiles par des bêta-testeurs (évaluation comparative).
- **Valider l’UX** : expérience conversationnelle utilisable sur le web, avec streaming et feedback.

### Public cible (personas)
- Avocats (cabinets)
- Étudiants
- Grand public (“Monsieur/Madame tout le monde”)

### Plateforme / accès
- Application **web** déployée, accessible aux **personnes autorisées**.
- Support de la **concurrence** : worst-case **50 utilisateurs simultanés** (objectif Beta).

### Parcours “must-have” (scénarios validés)
1. Poser une **question libre**.
2. Poser une question avec **contexte** (texte collé).
3. **Suivi conversationnel** (mémoire).
4. Citer des **articles précis** (ELI).
5. **Comparer** des textes / versions (selon disponibilité des versions dans les données + traçabilité).

### Réponses & évaluation comparative (A/B) — requis
- Pour une même requête, la Beta doit produire **deux réponses** basées sur **deux variantes** :
  - variante de **prompt**
  - et/ou variante de **retrieval** (ex: top-k, rerank, filtres, scoring)
- **Test aveugle** : l’utilisateur ne voit pas “A” vs “B” (ni le mécanisme), seulement deux réponses à comparer.
- Les retours doivent permettre d’identifier **quelle variante gagne**, sans enregistrer le contenu des messages.

### Sources (contraintes obligatoires)
Les sources doivent être :
- listées
- **cliquables** (vers le texte)
- avec **excerpt** (extrait) obligatoire
- avec **score** et/ou explication de sélection (au minimum score + métadonnées)

### Fonctionnalités UX requises
- **Streaming** requis (le MVP streame via WebSocket ; SSE également disponible)
- **Annulation** d’une requête (Abort)
- **Historique local** (au minimum)
- Feedback “**utile / pas utile**”
- **Copier / citer** la réponse
- Gestion d’erreurs **actionnable** (messages clairs)

### Langue
- **Français uniquement**

### Périmètre données
- Corpus : **toute la base LEGIFRANCE**
- **Refresh périodique** requis
- **Traçabilité forte** requise (versions, date d’effet, consolidation / provenance)

### Conformité / sécurité / privacy (contraintes fortes)
- Les utilisateurs peuvent saisir des **données sensibles** → obligation d’**anonymiser/pseudonomiser** (au minimum dans logs/événements/monitoring).
- **Interdiction d’analyse du contenu** : hors de question d’exploiter les questions/réponses pour de la data/BI.
- Les conversations doivent être **sauvegardées** et accessibles **uniquement par l’utilisateur** :
  - stockage **chiffré de bout en bout (E2EE)** recommandé (le serveur ne doit pas pouvoir lire prompts/réponses)
  - les événements/metrics ne doivent jamais contenir de texte utilisateur (ni extraits)
- Authentification : **OAuth 2.0**.

### Hors scope (explicite)
- **Jurisprudence**
- **Export PDF**

### In-scope (explicite)
- **Neo4j** (in-scope Beta)

### Déploiement / exécution
- Le pipeline de **peuplement (seeding)** peut tourner sur une machine **Linux**.
- Le pipeline de **mise à jour (MAJ)** doit pouvoir tourner **en production**.

### Critères de sortie Beta (gates)
- Stabilité, latence/erreurs “raisonnables”, UX utilisable, retours utilisateurs + métriques (quand consentement).
- (À préciser) objectifs chiffrés p95 latence / taux d’échec / coûts.

## Métriques (sans contenu) — proposition (avec consentement explicite)

### Principes
- Aucune collecte de **prompt**, **réponse**, **contexte collé**, ni de **texte** (même partiel).
- On collecte uniquement des **métadonnées** techniques et UX, et des **votes**.
- Un “mode sans métriques” doit exister (opt-out).

### Événements recommandés (niveau MVP)
- **rag_request_started** : timestamp, user_id (pseudonyme), session_id, client (browser/os), langue=fr, ab_bucket_id, rag_variant_id
- **rag_request_finished** : rag_variant_id, success=true/false, http_status/error_code, latency_ms_total, latency_ms_embedding/retrieval/llm, tokens_in/tokens_out (si dispo), cost_estimate (si dispo)
- **rag_sources_returned** : rag_variant_id, num_sources, top_score, min_score (pas d’ELI en métriques si ça peut révéler l’intention)
- **rag_answer_voted** : vote (A gagne / B gagne / égal / aucun), utile/pas utile, raisons (liste fermée), temps_avant_vote_ms
- **rag_source_clicked** : count_clicks, position_cliquée (1..n)
- **rag_request_cancelled** : step_at_cancel (embedding/retrieval/llm/stream), latency_ms_before_cancel
- **ui_error_shown** : error_category (network/timeout/server/auth), recoverable=true/false

### Raisons (liste fermée) pour feedback (exemples)
- “Pas pertinent”
- “Manque de sources”
- “Sources hors sujet”
- “Réponse trop vague”
- “Réponse trop longue”
- “Réponse difficile à comprendre”
- “Erreur factuelle apparente”
- “L’application est lente / instable”

## Backlog (sans dates) — ordre recommandé

### A. Cadrage (pré-requis)
- Définir le **scope Beta** + critères d’acceptation (happy path + cas d’erreur).
- Définir un **jeu de données Beta** (subset) + procédure de refresh (seed/clean).

### B. Débloquer le pipeline RAG (bloquants)
- Rendre le **service d’embedding** disponible (endpoint stable + healthcheck + configuration).
- Vérifier le flux **embedding → retrieval → LLM** (résultats + erreurs gérées proprement).

### C. Données testables (nécessaire pour des retours utilisateurs)
- Remplir **Qdrant** (sinon retrieval vide) + valider le schéma du payload.
- Remplir **MongoDB** (texte / excerpts / métadonnées) + vérifier cohérence IDs.
- Décider si **Neo4j** est *in-scope beta* (sinon expliciter “hors scope”). // NOTE: in-scope confirmé

### D. Robustesse du pipeline
- Normaliser **timeouts** par étape (embedding/retrieval/LLM) — déjà pilotés par env.
- Décider d’une éventuelle **politique de retry/fallback** (aujourd’hui : fail-fast, pas de
  retry — choix stateless assumé ; à réévaluer pour la beta).
- Ajouter un **mode dégradé** côté API (messages d’erreur utiles, pas d’échec opaque).

### E. Backend API stable pour intégration
- Le pipeline est exposé via `/api/v1/chat/ws` (WebSocket), `/api/v1/chat/streams` (SSE) et
  `/api/v1/chat/completions` (JSON). Stabiliser validation, timeouts et erreurs JSON.
- Aligner le **format des sources** (part `data-document` : `chunkId`, `title`, `type`,
  `score`) avec le contrat attendu frontend ; ajouter `excerpt`/`eli` si requis.
- Le **streaming** est en place (parts `text-delta`). Confirmer l’UX beta dessus.
- Ajouter le mode **A/B** (deux variantes prompt/retrieval + test aveugle) + contrat associé.
- Implémenter **OAuth 2.0** + contrôle d’accès.

### F. Frontend (intégration Beta)
- Implémenter la **couche API** (timeout + AbortController + SSE) et les **types** (request/response/sources/stream events).
- Mettre en place le **store** (messages/loading/error/step + A/B state + votes).
- Ajouter les hooks **useRagStream** (SSE) + annulation.
- Intégrer l’affichage : réponse + sources + gestion loading/erreur + feedback.
- Ajout consentement métriques (opt-in/opt-out) + émission événements “sans contenu”.

### G. Observabilité (indispensable en Beta)
- Logs corrélés (traceId) du frontend → API → étapes du pipeline RAG.
- Healthchecks : API + embedding (TEI) + Qdrant + MongoDB (déjà exposés via `/api/v1/health`).
- Guide “quoi regarder” (logs Pino structurés + `ragTiming` + erreurs fréquentes).
- (Privacy) S’assurer que les logs n’incluent pas prompts/réponses.

### H. Tests (gate Beta)
- Tests unitaires des activities (incl. erreurs réseau/timeout).
- Tests d’intégration de l’API RAG (mocks + au moins 1 run réel en Docker).
- Tests E2E “question → réponse + sources → feedback”.

### I. Packaging / Déploiement Beta
- Docker Compose “Beta” complet (DBs + embedding-service + backend + frontend) + `.env.example` à jour.
- Script bootstrap : seed data + init collections/index (l'ingestion vit hors dépôt).
- Documentation setup + troubleshooting (embedding down, Qdrant vide, Mongo vide).

## Critères simples “Prêt pour beta”
- Données présentes : **MongoDB + Qdrant** non vides, retrieval renvoie des sources.
- Le pipeline chat (`/api/v1/chat/ws` + `/streams`) répond de manière fiable (timeouts et erreurs propres).
- Frontend permet au minimum : poser une question, voir réponse + sources, gérer loading/error/cancel + streaming.
- Environnement Docker reproductible + doc d’exécution.

## Points à trancher (restants)
1. **E2EE conversations** : stratégie de gestion de clé (un seul appareil vs multi-appareils + récupération).
2. **Objectifs chiffrés Beta** : latence p95, taux d’échec toléré, budget coût par requête.
3. **Canal de support / collecte bugs** : formulaire, issues privées, email, Slack/Discord, autre.
