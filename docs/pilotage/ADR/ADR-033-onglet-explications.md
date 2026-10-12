# ADR-033 — L'onglet Explications : un LLM borné aux documents choisis

**Statut** : ✅ Accepté (12 octobre 2026) — amende ADR-007, ADR-010, ADR-015 §2,
ADR-030 §1, §4, §5 et §6, ADR-032 §2, §4, §6, §11 et §12 · ferme, pour l'onglet Résumé,
le point ouvert « Contenu des onglets Graphe et Résumé » · ouvre le point « Garde-fous
de l'onglet Explications »

## Contexte

ADR-028 a retiré le LLM : Murphy devait **sourcer, pas raisonner** (ADR-007). ADR-032 §6
garde pourtant un onglet vide, Résumé, qui « réintégrera un LLM, plus contrôlé ». Cette
ADR décrit ce contrôle.

L'usage visé : l'utilisateur choisit des documents dans ses résultats, puis demande au
LLM de les résumer et de les lui expliquer. Le LLM ne cherche rien lui-même, et ne
travaille sur rien d'autre que ces documents.

Six contraintes pèsent sur les choix :

- **La consultation juridique est réservée** à certaines professions (loi n° 71-1130 du
  31 décembre 1971, art. 54 et suivants). L'onglet explique des textes ; il ne qualifie
  pas une situation et ne conseille pas.
- **L'identité des magistrats et des greffiers** ne peut être réutilisée pour évaluer,
  analyser, comparer ou prédire leurs pratiques (loi n° 2019-222, art. 33), sous peine de
  sanctions pénales. Une décision porte ces noms dans ses métadonnées.
- **Le serving est sans état** (ADR-010) : aucune conversation n'est gardée côté serveur.
- **Le LLM est externe pour l'instant** (Mammouth, compatible OpenAI), auto-hébergé plus
  tard : les questions et les documents quittent le système.
- **Un appel au LLM coûte de l'argent**, à l'inverse d'une recherche.
- **Les limites de l'ESLint** : 300 lignes par fichier (200 par `.tsx`), 30 par
  fonction, profondeur 3.

## Décision

### 1. Une sélection, construite depuis la recherche

- **Un bouton à bascule « + » (Ajouter) / « - » (Retirer)** remplace le menu « … » de chaque
  résultat (amende ADR-032 §4).
- **La sélection est une liste ordonnée**, dans l'ordre des ajouts. Elle survit à une
  nouvelle recherche, comme les onglets document, et disparaît au rechargement. Elle vit
  dans un store Zustand, `selectionStore`, sans `persist`.
- Chaque entrée garde ce que la sidebar et les messages affichent : `identifier`,
  `title`, `documentType`, `nature`, `isInForce` et `contentLength` (§9).

### 2. La sidebar

Une colonne à droite de l'espace de travail, **hors de Dockview** : on construit la
sélection dans Recherche, on l'utilise dans Explications, et elle doit rester visible
des deux côtés. Elle se replie, avec un compteur ; sur mobile, elle devient un tiroir.

De haut en bas :

- **Le bouton « Résumer »** (§4) ;
- **la jauge du budget** : la somme des `contentLength` de la sélection, rapportée au
  budget de contexte (§9) ;
- **la liste numérotée** : le numéro, la pastille de vigueur, le titre (qui ouvre
  l'onglet du document) et un bouton pour retirer ;
- **« Tout retirer »**.

**Un ajout qui dépasse le budget est accepté** : la jauge passe au rouge, puis
« Résumer » et le champ de question sont désactivés. L'utilisateur choisit ce qu'il
retire. **Une sélection vide** désactive aussi les deux, avec une invite qui renvoie à
la recherche : sans document, il n'y a rien à expliquer.

Retirer un document renumérote la liste.

### 3. L'onglet Explications

L'onglet Résumé devient **Explications**, et son type reste `explanation`. Il affiche une
conversation, sur le modèle du chat retiré par ADR-032 §11 (`AIMessage`, `ChatBubble`,
`SourcesList` sur `main`) : des messages, un champ de question, un bouton « Arrêter »
pendant la génération.

- **Sous chaque message de l'utilisateur**, une liste déroulante « Sources (n) » montre
  la sélection *au moment du message* : son numéro, sa pastille, son titre. Chaque
  message en garde une copie.
- **Un séparateur** s'insère avant un message dont la sélection diffère de celle du
  message précédent.
- **La conversation vit dans un store**, pas dans le panneau : fermer l'onglet ne la
  perd pas, et le bouton de la sidebar peut y écrire. Elle disparaît au rechargement.
- Les réponses sont rendues en Markdown.

### 4. Le bouton « Résumer »

Il ajoute à la conversation le message « Veuillez résumer les documents fournis. », avec
la sélection courante, puis active l'onglet Explications, ou le rouvre s'il est fermé.
Sur une conversation existante, il **ajoute** : le séparateur s'insère si la sélection a
changé. Le texte est une constante du frontend ; le backend le traite comme n'importe
quelle question.

### 5. Le séparateur borne le contexte

Le LLM ne reçoit que **le segment courant** : les messages depuis le dernier séparateur,
et la sélection courante. L'utilisateur voit toute la conversation ; le LLM n'en voit
qu'un segment. Une réponse ne peut donc pas s'appuyer sur un document retiré, qui
n'apparaîtrait plus que dans une ancienne réponse.

Le client envoie le segment à chaque question ; le serveur ne garde rien (amende
ADR-010).

### 6. Les citations

- Le backend envoie les documents au LLM **dans l'ordre de la sélection**, chacun
  précédé de son repère : `[1]`, `[2]`…
- Le prompt demande de citer ces repères **le plus souvent possible**. Une phrase sans
  repère n'est pas refusée.
- Dans une réponse, `[n]` désigne le n-ième document des sources du message qui l'a
  demandée. Le frontend en fait un lien qui ouvre l'onglet du document. Un repère sans
  document correspondant reste du texte brut.
- Le séparateur borne le contexte : à l'intérieur d'un segment, un repère ne change
  jamais de sens, même si la sidebar a été renumérotée depuis.

La citation au niveau du passage, avec surlignage, reste ouverte.

### 7. Ce que le LLM reçoit d'un document

Le backend relit chaque document de la sélection dans Mongo, par son `identifier` : il
ne fait jamais confiance à un texte envoyé par le client. Pour chacun : son repère, son
titre, son type, sa nature, `parent_text_title` s'il en a un, son texte entier, et les
métadonnées d'une **liste blanche**.

> **Précision (12 octobre 2026, mise en œuvre).** `parent_text_title` n'était écrit que
> dans OpenSearch. L'ingestion l'écrit aussi dans Mongo, dans le même `replace_one` que
> `content_length` : le backend lit tout dans Mongo.

| Source | Métadonnées transmises |
|---|---|
| Législatif | `statut`, `date_debut`, `date_fin`, `versions_a_venir`, `date_texte`, `date_publication`, `nor`, `titre_full` |
| Jurisprudence | `juridiction`, `formation`, `date_decision`, `numero`, `ecli`, `solution`, `type_recours`, `date_decision_attaquee` |

- **Chaque clé reçoit un libellé français** (« Date d'entrée en vigueur » pour
  `date_debut`) : le LLM lit un libellé mieux qu'une clé.
- **Le statut de vigueur est toujours transmis** quand il existe : résumer un texte
  abrogé sans le dire induirait en erreur.
- **Sont exclus** `president`, `rapporteur`, `rapporteur_public` et `avocats` (loi
  n° 2019-222), les identifiants techniques et les champs de publication (`ancien_id`,
  `chronicle_cid`, `num_sequence`, `page_debut_publication`, `page_fin_publication`,
  `origine`, `url_conseil_constitutionnel`), et toute métadonnée non configurée.
- Une clé absente de la liste n'est pas transmise : un oubli prive le LLM d'une
  information, mais ne fait rien fuir.

### 8. Le prompt système est un fichier versionné

Le prompt vit dans un fichier du backend, relu et testé comme du code. Ce n'est plus une
variable d'environnement, comme l'ancien `SYSTEM_PROMPT` : il porte le cadre de
l'onglet, expliquer sans qualifier, et ce cadre ne doit dépendre d'aucun déploiement.

### 9. Le budget de contexte

- **`contentLength`** est écrit à l'ingestion : `content_length` dans Mongo, la longueur
  de `content` en points de code, dans le même `replace_one` que le texte (amende
  ADR-015 §2). Le résultat de recherche et le document servi par `GET /documents` le
  transmettent.
- **`LLM_CONTEXT_MAX_CHARS`** (par défaut 100 000, environ 25 000 tokens) fixe le budget.
  La réponse de recherche le transmet, comme `pageSizes` (ADR-032 §8) : la sidebar ne se
  remplit qu'après une recherche.
- **La jauge est indicative** : elle ne compte que les textes. **Le serveur fait foi** :
  à chaque question, il compte les textes, les métadonnées, le prompt et le segment, en
  points de code, et refuse au-delà du budget (400 `CONTEXT_TOO_LARGE`). Le message dit
  comment s'en sortir : retirer un document ouvre un nouveau segment.
- **`LLM_MAX_OUTPUT_TOKENS`** (par défaut 2 000) borne la longueur d'une réponse.

### 10. La route et le flux : SSE, sans WebSocket

**`POST /api/v1/explanations`**, corps `{ selection, messages }` : les identifiants dans
l'ordre de la sélection, puis les messages du segment. La réponse est un flux SSE.

- **`POST`, jamais `GET`** : la question ne passe pas par une URL (ADR-010). Le client
  lit donc le flux avec `fetch`, pas avec `EventSource`, qui n'accepte que `GET`.
- **L'AI SDK revient** des deux côtés : `useChat` côté frontend, `streamText` et
  `@ai-sdk/openai-compatible` côté backend. Son transport par défaut est un SSE en
  `POST` ; le WebSocket de `main` exigeait un transport sur mesure. *Précision (12 octobre
  2026)* : la version majeure retenue est `ai` 6 (`@ai-sdk/react` 3,
  `@ai-sdk/openai-compatible` 2), comme sur `main`. `ai` 7 n'est publié qu'en ESM, que
  le backend, en CommonJS, et ses tests (ts-jest) ne chargent pas. Les deux côtés gardent
  la même version majeure, donc le même protocole de flux.
- **Des messages utilisateur consécutifs** (§11) sont fusionnés par le backend avant
  l'appel : certains modèles refusent deux messages du même rôle à la suite.

### 11. L'arrêt et les erreurs

- **L'arrêt se propage jusqu'au LLM** (amende ADR-030 §6 pour cette route). « Arrêter »
  coupe le `fetch` ; le backend voit la connexion se fermer (`res.on('close')` sans
  `res.writableEnded` : `req.on('close')` se déclenche dès que le corps est lu) et coupe
  l'appel au LLM par un `AbortSignal`. Un fournisseur peut facturer la génération
  au-delà de la coupure : cela ne dépend pas de nous.
- **Après un arrêt**, la réponse partielle reste, marquée « interrompue », et part avec
  le segment.
- **Une erreur avant le flux** a son statut HTTP et son code, comme ailleurs (ADR-030
  §4). *Précision (12 octobre 2026)* : le backend attend le premier fragment du LLM,
  pendant `LLM_TIMEOUT` au plus, avant d'ouvrir le flux. Un fournisseur injoignable, une
  clé refusée ou un délai dépassé donnent donc encore un vrai 502 `LLM_FAILED` ou 504
  `TIMEOUT`.
- **Une erreur pendant le flux** arrive comme un événement d'erreur, le statut 200 étant
  déjà parti. La réponse partielle est effacée, le message de l'utilisateur reste. La
  modale affiche le message du code (ADR-032 §10). Le message resté sans réponse part
  avec la question suivante, fusionné avec elle (§10).

| Statut | Code | Message |
|---|---|---|
| 400 | `CONTEXT_TOO_LARGE` | La sélection dépasse ce que le service peut lire : retirez un document. |
| 404 | `DOCUMENT_NOT_FOUND` | Un document de la sélection est introuvable. |
| 429 | `EXPLANATION_RATE_LIMIT_EXCEEDED` | Trop de questions : réessayez dans une minute. |
| 429 | `EXPLANATION_QUOTA_EXCEEDED` | Le service d'explications a atteint sa limite du jour. |
| 502 | `LLM_FAILED` | Le service d'explications est indisponible. |
| 504 | `TIMEOUT` | (inchangé) |

`VALIDATION_ERROR` et les erreurs du corps gardent leur message. Les codes rejoignent la
liste du contrat ; la table du frontend, exhaustive, ne compile pas sans leurs messages.

### 12. Deux plafonds d'appels

- **Par IP** : 10 questions par minute (`EXPLANATION_RATE_LIMIT_*`), en plus du limiteur
  général.
- **Global** : 200 appels par jour (`EXPLANATION_DAILY_LIMIT`), tous clients confondus :
  `express-rate-limit` avec une clé constante et une fenêtre de 24 h.

On compte des appels plutôt que des tokens. Le coût maximal d'un appel est connu
d'avance (le budget de contexte plus `LLM_MAX_OUTPUT_TOKENS`), donc le plafond borne la
dépense. Compter des tokens supposerait que l'API renvoie l'usage en streaming, ce que
tous les serveurs compatibles OpenAI ne font pas.

Le compteur vit en mémoire : un redémarrage le remet à zéro, et chaque instance a le
sien. C'est acceptable avec une instance. Le plafond de dépense de la clé chez le
fournisseur, s'il existe, s'ajoute à celui-ci.

### 13. Un LLM derrière une interface, et obligatoire

- **`LlmClient`** (`infra/`) expose une seule opération : produire une réponse en flux à
  partir d'un prompt système, de messages et d'un `AbortSignal`. Son implémentation
  s'appuie sur `@ai-sdk/openai-compatible`. Passer à un modèle auto-hébergé (vLLM, TGI,
  Ollama) change l'URL, pas le code. Aucun nom de fournisseur dans le code.
- **La configuration** : `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT` (le
  délai jusqu'au premier fragment), `LLM_CONTEXT_MAX_CHARS` et `LLM_MAX_OUTPUT_TOKENS`.
- **Le LLM est obligatoire** (fail-fast, ADR-010). Sans `LLM_BASE_URL`, `LLM_API_KEY`
  ou `LLM_MODEL`, le backend refuse de démarrer, comme pour toute variable critique :
  la recherche ne démarre pas non plus. *Précision (12 octobre 2026)* : une variable
  critique absente n'était jusqu'ici que journalisée. `checkEnvironment` arrête
  désormais le démarrage pour toutes, `EMBEDDING_QUERY_INSTRUCTION` comprise. La récupération reste un composant autonome
  dans le code (ADR-007), mais aucun déploiement ne la sert sans le LLM.
- **Le démarrage ne sonde pas le LLM**, à l'inverse d'OpenSearch : seule sa
  configuration est vérifiée. Un fournisseur injoignable ne se révèle qu'à l'appel, par
  un 502 `LLM_FAILED`.
- **La santé** sonde le LLM (`GET {LLM_BASE_URL}/models`, authentifié) avec TEI,
  OpenSearch et Mongo. Une panne du seul LLM rend l'état `degraded`.

### 14. Rien du contenu dans les journaux

La règle d'ADR-010 s'étend : ni les questions, ni les réponses, ni les textes envoyés ne
sont journalisés. Le log `Explanation completed` garde le nombre de documents, les
longueurs, la durée, la raison de fin (terminé, arrêté, erreur) et les tokens si l'API
les renvoie. Une erreur du fournisseur est journalisée par son statut et son code, pas
par son message, qui peut reprendre une part de la requête.

### 15. Les garde-fous : une ADR à part

L'interdiction de la qualification et du conseil juridiques repose sur trois couches :
un filtre des questions avant le LLM, le cadre du prompt, une vérification des réponses
après. **Leur conception relève d'une ADR dédiée**, qui fixera la frontière entre
expliquer un texte et l'appliquer à une situation. Elle amendera ADR-010, qui exclut
toute analyse du contenu des requêtes.

Cette ADR-ci décrit la mécanique de l'onglet. Le prompt du §8 en pose le cadre, mais
**l'onglet n'est pas mis en production avant l'ADR des garde-fous**.

## Alternatives rejetées

- **Un WebSocket**, pour propager l'arrêt : la fermeture de la connexion HTTP suffit, et
  le WebSocket ramènerait un transport sur mesure et un état par connexion (ADR-010).
- **Un SSE écrit à la main**, avec des événements validés par zod : l'AI SDK fournit le
  même protocole, `useChat`, l'arrêt et les erreurs du flux.
- **La sidebar dans l'onglet Explications**, ou en panneau Dockview : il faudrait
  changer d'onglet pour voir ce qu'on vient d'ajouter.
- **L'option « Ajouter » dans le menu « … »** : une action fréquente cachée dans un menu
  qui n'avait pas d'autre option.
- **Tout l'historique envoyé au LLM** : une ancienne réponse ferait entrer dans le
  contexte un document retiré de la sélection, sans son texte.
- **Des numéros fixes, avec des trous** (1, 3, 4) : le séparateur suffit à garder les
  repères stables à l'intérieur d'un segment.
- **Toutes les métadonnées** : du bruit qui consomme le budget, et l'identité des
  magistrats qui part chez un tiers.
- **Le prompt dans l'environnement** : le cadre de l'onglet varierait d'un déploiement à
  l'autre, sans relecture.
- **`contentLength` calculé au serving** : le serving lit déjà le texte, mais
  l'ingestion est la source du contrat (ADR-015).
- **Refuser un ajout qui dépasse le budget** : l'utilisateur devrait retirer un document
  avant de voir celui qu'il voulait ajouter.
- **Compter les tokens** pour le plafond global : l'usage n'est pas toujours renvoyé en
  streaming, et le plafond ne serait plus garanti.
- **Un LLM facultatif**, la route répondant 503 sans configuration : un traitement à
  part, contre le fail-fast que suit toute autre variable critique.
- **Sonder le LLM au démarrage**, comme OpenSearch : une panne du fournisseur
  empêcherait de redémarrer le backend, recherche comprise, alors qu'une erreur à
  l'appel suffit.
- **Effacer la réponse partielle après un arrêt** : l'utilisateur l'a arrêtée
  lui-même, et peut vouloir la lire.
- **Effacer le message de l'utilisateur après une erreur** : il perdrait sa question.

## Conséquences

La mise en œuvre se fait en cinq lots, commités chacun à part. `npm run check` et le job
`python` restent verts après chacun.

**Lot 1 — L'ingestion : `content_length`.**
- `ragcore` écrit `content_length` dans Mongo ; tests unitaires et
  `docs/technical/data/reference/modele-de-donnees.md`.
- **Réingestion complète** : le backend du lot 2 refuse un document sans
  `content_length` (`CONTRACT_VIOLATION`).

**Lot 2 — Le backend et le contrat.**
- `@murphy/contract/search` : `contentLength` dans le résultat et le document,
  `contextBudget` dans la réponse, les nouveaux codes d'erreur. Un sous-chemin
  `@murphy/contract/explanations` pour la requête et le type des messages.
- `infra/llm.ts` (`LlmClient`), la route, le service, la liste blanche et ses libellés,
  le fichier du prompt. Le build du backend copie le prompt dans `dist/`.
- `config.ts` et `configWarnings` : les variables `LLM_*` et `EXPLANATION_*` ;
  `docker-compose.base.yml` et `.env.dev`, où `LLM_*` devient indispensable pour
  démarrer le backend en dev.
- Les deux limiteurs, la sonde de santé, les tests avec un faux `LlmClient` : aucun
  appel réel en CI.
- Les dépendances `ai` et `@ai-sdk/openai-compatible` reviennent au backend.

**Lot 3 — Le frontend : la sélection.**
- `selectionStore`, le bouton à bascule, la sidebar et sa jauge, son repli et le tiroir
  mobile.

**Lot 4 — Le frontend : l'onglet Explications.**
- Le store de la conversation, les messages, les sources sous chaque message, le
  séparateur, les repères en liens, « Arrêter », les erreurs du flux.
- Un onglet document peut s'ouvrir sans passage à surligner : `passage` devient
  facultatif dans ses paramètres.
- Les dépendances `ai`, `@ai-sdk/react` et `react-markdown` reviennent (amende ADR-032
  §11). `features/selection/` et `features/explanation/` rejoignent l'arborescence
  (amende ADR-032 §12).

**Lot 5 — Documentation.**
- `CLAUDE.md`, `docs/technical/ARCHITECTURE.md`, `docs/technical/backend/` et
  `docs/technical/frontend/`.
- Les amendements d'ADR-007, ADR-010, ADR-015, ADR-030 et ADR-032 ; `INDEX.md`.
- Vérification dans le navigateur : un ajout, un retrait, un résumé, une question de
  suivi, un changement de sélection et son séparateur, un repère cliqué, un arrêt, une
  erreur (LLM injoignable), un dépassement de budget.

**Restent ouverts** :
- les garde-fous (§15), dans une ADR dédiée, avant toute mise en production ;
- le modèle retenu chez Mammouth, et la politique de rétention des données de ce modèle ;
- l'information de l'utilisateur : ses questions et les documents choisis partent chez
  un tiers ;
- la citation au niveau du passage (§6) ;
- l'ajout à la sélection depuis l'onglet document.

## Références

ADR-007 (sourcer, pas raisonner) · ADR-010 (stateless, confidentialité) · ADR-015
(contrat ingestion ↔ serving) · ADR-028 (le LLM retiré) · ADR-030 (API de recherche) ·
ADR-032 (interface Dockview)

- Loi n° 71-1130 du 31 décembre 1971, art. 54 et suivants (consultation juridique)
- Loi n° 2019-222 du 23 mars 2019, art. 33 (identité des magistrats et des greffiers)
- [AI SDK](https://ai-sdk.dev) — `useChat`, `streamText`, `@ai-sdk/openai-compatible`
