# Cadrage — Évaluation de la récupération documentaire (RAG juridique, v0)

> ⚠️ **ARCHIVE — document historique, non normatif.** Conservé pour la
> traçabilité du raisonnement initial. En cas de contradiction avec un ADR
> ou avec `EXIGENCES_v0.md`, **ce document a tort**. Points périmés
> connus, à ne pas reprendre :
>
> - **§3.3 « Amorçage par le graphe de citations »** — **révoqué par
>   ADR-029**. Utiliser le graphe pour suggérer ou pré-remplir le
>   golden-set (B-08) est explicitement écarté : la suggestion
>   deviendrait la vérité terrain, réinjectant la circularité que la
>   strate 2 doit prévenir. L'assistance à l'annotation est renvoyée
>   hors graphe (`BACKLOG.md` §4).
> - **§3.3 « Qrels citation-minées »** — la strate 2 n'est plus une
>   source de qrels scorables mais un **diagnostic de co-citation
>   précision-seulement** (ADR-029) : jamais le rappel, jamais un grade.
> - **§3.3 échelle « directement applicable / support / périphérique /
>   hors-sujet »** — remplacée par la **cascade de trois tests binaires**
>   q1/q2/q3 d'**ADR-005** (l'échelle par démarcations d'intensité y est
>   explicitement rejetée : arbitraire, désaccords non localisables).
> - **§9 « décisions encore ouvertes »** — toutes tranchées depuis :
>   unité document (ADR-004), échelle + guide (ADR-005), agrégation
>   (ADR-006), coupe et métriques (ADR-007), format (ADR-008), types
>   d'action (ADR-009).
>
> Restent valides et utiles : le reframing IR (§0), le **pooling**
> (§3.3) et le **garde-fou représentativité** du synthétique (§8).

> Document de cadrage destiné à un agent LLM travaillant dans cette codebase.
> Objectif : construire un dispositif d'évaluation de la **récupération seule**
> (sans LLM générateur), **agnostique** au fonctionnement interne du pipeline,
> pour itérer sur les configs, modèles et méthodes et augmenter la pertinence
> des résultats documentaires.
 
---
 
## 0. Intention et périmètre
 
- On évalue **uniquement la récupération** de documents/passages. Aucun LLM
  générateur n'est branché en bout de chaîne (choix délibéré : isole et
  stabilise la mesure).
- Le « Golden-Set » visé est, en vocabulaire consacré, une **collection de test
  de Recherche d'Information (IR)** : le triplet
  `(corpus, requêtes/topics, jugements de pertinence = "qrels")`.
- **Reframing directeur** : en découplant récupération et génération, on n'est
  plus dans « l'évaluation de RAG » mais dans un problème IR classique. Toute la
  méthodologie type TREC s'applique, outillage compris (trec_eval, pytrec_eval,
  ir_measures, ranx) et métriques établies (nDCG, Recall, MRR). **Ne pas
  réinventer la forme du problème.**
---
 
## 1. Principes invariants (à ne jamais violer)
 
1. **Découplage** récupération / génération.
2. **Contrat d'interface unique** : toute config, quel que soit son chemin
   interne, expose `requête → liste ordonnée d'IDs canoniques (+ scores)`.
   L'évaluation ne compare **jamais** que des listes d'IDs ordonnées aux qrels.
3. **Identité canonique stable inter-BDD** : un même chunk/document porte le
   **même ID** qu'il sorte de Qdrant, Neo4j ou MongoDB. Sans cela, aucune
   évaluation agnostique n'est possible. *(Pilier — voir §2.)*
4. **Golden-set versionné et figé** ; les **runs** (listes produites) sont
   stockés séparément du scoring, pour re-scorer avec de nouvelles métriques
   sans tout relancer.
5. **Pertinence graduée**, pas binaire (la pertinence juridique ne l'est pas).
6. **Décision par test statistique apparié**, pas par moyenne nue (voir §5).
---
 
## 2. Couche d'identité canonique (prérequis technique bloquant)
 
Avant toute évaluation, garantir un schéma d'identité stable et partagé.
 
- Chaque unité indexée possède un `chunk_id` **canonique** et déterministe
  (p. ex. hash stable de `source_uri + offset` ou un identifiant métier).
- Chaque `chunk_id` porte son `doc_id` **parent** (l'identifiant du document
  juridique : arrêt, article, décision…). Idéalement l'identifiant Légifrance
  natif (LEGIARTI…, JURITEXT…, CETATEXT…, CONSTEXT…).
- Qdrant, Neo4j et MongoDB référencent tous ce même `chunk_id` / `doc_id`.
```json
{
  "chunk_id": "canon::JURITEXT000012345678::0007",
  "doc_id": "JURITEXT000012345678",
  "doc_type": "jurisprudence_judiciaire",
  "source_uri": "legifrance://JURITEXT000012345678",
  "char_span": [4210, 4890]
}
```
 
**À trancher (voir §9) :** ce qui compte comme « document » (arrêt entier ?
article ? section ?).
 
---
 
## 3. Structure de la collection de test
 
### 3.1 Granularité
 
- **Unité de jugement = le chunk/passage** (les qrels sont écrits à ce niveau).
- **Unité d'agrégation = le document** (dérivée, via `doc_id`). Un seul fichier
  de qrels au niveau chunk suffit à produire les métriques passage **et**
  document (voir §4).
### 3.2 Topics / requêtes
 
- **Stratifier** les requêtes par (a) **type d'action** du système (les
  « différentes actions » qu'il doit soutenir) et (b) **difficulté**.
- Statut des requêtes : **synthétiques** pour la v0 (pas de requêtes réelles
  disponibles), à valider et remplacer progressivement (voir §8).
- Conserver le format compatible avec le futur outil d'annotation par des
  experts (même schéma d'IDs, mêmes champs).
```json
{
  "query_id": "q0042",
  "text": "Conditions de recevabilité d'un pourvoi hors délai",
  "action_type": "recherche_article_applicable",
  "difficulty": "hard",
  "origin": "synthetic|mined|expert"
}
```
 
### 3.3 Qrels — le goulot d'étranglement
 
C'est la partie la plus difficile et la plus facile à rater. Solo pour la v0.
 
- **Pertinence graduée**, p. ex. `0–3` :
  `3` directement applicable / `2` pertinent-support / `1` périphérique /
  `0` hors-sujet. Alimente un nDCG bien plus informatif qu'un binaire.
  *(Échelle exacte + guide d'annotation à figer, voir §9.)*
- **Pooling** : ne juger que l'**union des top-k** des configs comparées.
  Réduit fortement la charge d'annotation.
- **Amorçage par le graphe de citations (Neo4j)** : un arrêt cite tel article
  → cet article est un candidat pertinent pour les requêtes visant cet arrêt.
  Signal semi-automatique pour pré-remplir les qrels.
- **Garde-fou circularité** : si le graphe sert **à la fois** à fabriquer les
  qrels **et** comme composant évalué, on le favorise mécaniquement. Isoler :
  les qrels d'amorçage par citation doivent être **relues/validées** avant de
  servir de vérité terrain, et idéalement marquées `source: citation_bootstrap`
  pour pouvoir les exclure des évaluations du composant graphe.
```
# format qrels (TREC-like) : query_id  0  chunk_id  grade
q0042  0  canon::LEGIARTI000012::0003  3
q0042  0  canon::LEGIARTI000099::0000  1
```
 
---
 
## 4. Évaluation à deux niveaux (passage + document)
 
Un seul jeu de qrels (niveau chunk) → deux familles de métriques.
 
- **Niveau passage** : nDCG@k, Recall@k sur les `chunk_id`.
- **Niveau document** : agréger via `doc_id`.
  - **Règle d'agrégation (à figer, §9)** — proposition par défaut : un document
    est « trouvé » dans le top-k si **au moins un** de ses chunks pertinents
    (grade ≥ seuil) y apparaît. Le grade document peut être `max` (ou `sum`
    plafonné) des grades de ses chunks.
  - Métriques : **Document-Recall@k** (« le bon document est-il présent ? ») et
    **Document-MRR** (« à quel rang le premier bon document apparaît-il ? »).
> Rationale : même si aucun LLM n'est branché aujourd'hui, un générateur futur
> aura besoin que le **bon document soit présent** dans le contexte → le
> Document-Recall@k est un objectif de premier ordre, pas un détail.
 
---
 
## 5. Métriques et discipline de décision
 
- **Primaire** : `nDCG@k` (gradué, sensible au rang).
- **Secondaire** : `Recall@k` (présence du bon document dans le contexte).
- **Ciblée** : `MRR` pour les tâches « trouver LE bon article ».
- Toujours reporter la **distribution par requête**, pas seulement la moyenne.
- Avant de conclure qu'une config en bat une autre : **test apparié** (t-test
  apparié ou test de randomisation/permutation sur le nDCG par requête). Sur un
  petit jeu, une différence de moyenne non testée = probablement du bruit.
- Outillage recommandé : `pytrec_eval`, `ir_measures`, ou `ranx` (ce dernier
  gère aussi la fusion et les tests de significativité).
---
 
## 6. Golden-set vs ablations vs sets diagnostiques
 
**Réponse à « faut-il un golden-set par brique techno ? » : non.**
 
- **UN** golden-set canonique. Ne pas multiplier les golden-sets (fragmente
  l'annotation, rend les signaux non comparables).
- **Harnais d'ablations** : chaque brique (augmentation Neo4j, mode « thinking »,
  choix d'embedding, fusion hybride…) est un **toggle**. On mesure le **delta**
  de métriques sur le **même** golden-set. C'est ainsi qu'on attribue une
  contribution marginale à chaque composant.
- **Sets diagnostiques ciblés** (petits, façon tests unitaires de la
  récupération) — pour isoler un mécanisme que l'agrégat **dilue** :
  - **graph-hop set** : requêtes dont le passage-or n'est atteignable **que**
    via une relation de citation (le graphe est alors indispensable). Mesure
    directement la valeur de l'augmentation Neo4j, invisible dans la moyenne
    globale si peu de requêtes nécessitent un saut relationnel.
  - **hard-query set** : requêtes à fort décalage de vocabulaire / concept
    implicite, où la récupération naïve échoue. Stresse spécifiquement le mode
    « thinking » (reformulation/expansion de requête sans entraînement).
> Principe : `1 golden-set (mesure le système)` +
> `N mini-sets diagnostiques (mesurent des capacités/mécanismes)` +
> `harnais d'ablation (mesure la contribution marginale de chaque brique)`.
 
---
 
## 7. Le harnais (architecture logique)
 
```
[ config/pipeline A ] ─┐
[ config/pipeline B ] ─┼─►  ADAPTER (contrat §1.2)  ─►  RUN (liste ordonnée d'IDs + scores)
[ config/pipeline C ] ─┘                                      │
                                                              ▼
                                                       RUN STORE (versionné, immuable)
                                                              │
                        QRELS (versionnés) ──────────────►  SCORER  ─►  RAPPORT
                                                                        - par requête
                                                                        - agrégats (§4,§5)
                                                                        - tests appariés
```
 
- **Adapter** : la seule chose spécifique à chaque config. Traduit sa sortie
  interne (vectoriel / graphe / hybride RRF…) vers le contrat unique.
- **Run store** : runs bruts conservés → re-scoring a posteriori sans relancer
  le pipeline.
- **Scorer** : `(qrels, runs) → métriques`. Ne connaît rien du pipeline.
---
 
## 8. Ressources réutilisables
 
### Méthodologie / benchmarks à imiter (pas des données FR réutilisables)
- **COLIEE** (Competition on Legal Information Extraction/Entailment) : tâche de
  recherche d'articles de loi (Task 3) et de jurisprudence (Task 1). Template
  méthodologique le plus proche (qrels, pooling). Corpus canadien/japonais →
  **modèle**, pas données à réemployer.
- **BEIR** : pour les conventions de format et l'outillage IR.
### Données juridiques françaises réelles (corpus + graphe de citations)
- **API Légifrance (DILA / portail PISTE)** — gratuite après inscription
  (OAuth2 client credentials). Codes, LODA, jurisprudence, Conseil constit.
- **Judilibre** (API Cour de cassation).
- **Open data justice administrative** (Conseil d'État, CAA, TA).
- **Open data Conseil constitutionnel** (identifiants uniques Légifrance).
- Librairie **`pylegifrance`** (accès Python, validation Pydantic).
- **Le graphe de citations de ces sources est réel** → source de qrels
  semi-automatiques pour amorcer Neo4j (avec le garde-fou circularité, §3.3).
### Requêtes (pas de réelles → synthétique en v0)
- Génération : **doc2query / docT5query**, **InPars / InPars-v2**,
  **Promptagator** (few-shot). Orientés entraînement mais réutilisables pour
  fabriquer des paires requête↔passage.
- Évaluation : **RAGAS** (diversité des types de requêtes) et **AIR-Bench**
  sont pensés pour produire des *testsets d'évaluation*.
- **Garde-fou représentativité** : la correspondance entre requêtes synthétiques
  et vraies requêtes utilisateur est peu garantie. Traiter le synthétique comme
  un **bootstrap à valider**, jamais comme vérité terrain figée. Prévoir le
  remplacement progressif par des requêtes minées (sommaires/headnotes,
  questions type service-public.fr) puis par des requêtes expertes.
---
 
## 9. Décisions encore ouvertes (à trancher avant implémentation)
 
- [ ] Définition exacte de l'unité **« document »** (arrêt entier ? article ?
      section ?).
- [ ] **Échelle de pertinence** définitive + **guide d'annotation** écrit
      (critères pour distinguer chaque grade).
- [ ] **Règle d'agrégation** chunk → document (§4).
- [ ] Valeur(s) de **k** (coupe) pour les métriques.
- [ ] **Format de stockage** qrels/runs, compatible avec le futur outil
      d'annotation par des experts.
- [ ] Périmètre initial des **types d'action** (stratification des requêtes).
---
 
## 10. Definition of Done — v0
 
- [ ] Couche d'identité canonique en place et vérifiée sur les 3 BDD.
- [ ] Contrat d'adapter implémenté pour ≥ 1 config de référence (**baseline**).
- [ ] Golden-set v1 figé et versionné : corpus + topics stratifiés + qrels
      gradués (pooling + amorçage citations relu).
- [ ] Scorer produisant nDCG@k / Recall@k (passage) + Doc-Recall@k / Doc-MRR
      (document), **par requête** et agrégés.
- [ ] Test statistique apparié branché dans le rapport.
- [ ] ≥ 1 set diagnostique (graph-hop) opérationnel.
- [ ] Une baseline mesurée, chiffrée, reproductible — point de départ des
      itérations.
---
 
## Note sur « code parfait »
 
Pour un harnais d'évaluation, « parfait » = **correct, reproductible, et
golden-set stable**. C'est de l'infrastructure de mesure : sa valeur est dans la
fiabilité et la comparabilité dans le temps, pas dans l'ingéniosité. Priorité au
déterminisme (IDs stables, runs immuables, seeds figées) sur l'élégance.