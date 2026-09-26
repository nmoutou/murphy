# ADR-031 — Graphe témoin, versionnement du graphe enrichi, protocole de comparaison

**Statut** : Acté (22 juillet 2026, préparation de B-08) — **étend ADR-027**
(couple `(W, R)` → triplet `(W, G, R)`), **prolonge ADR-029** (garde-fou de
circularité), **support d'ADR-030**

## Contexte

ADR-027 fait de P2 une plateforme d'expérimentation end-to-end : une expérience
est décrite par le couple **`(W, R)`** — `W` = normalisation + chunking +
embedding, `R` = runtime de récupération. Le graphe de citations, lui, n'est
pas un terme d'expérience : il est ce que l'ingestion produit.

Deux évolutions le rendent insuffisant.

**Le graphe devient un levier.** Un graphe *enrichi* — dont la responsabilité
est de rendre les documents plus faciles à trouver — est un objet qu'on fait
varier et dont on mesure la contribution. Un harnais qui ne peut pas le faire
varier ne peut pas mesurer son apport, ce qui est précisément le grief
qu'ADR-027 adressait au harnais passif.

**`W` ne peut pas le porter.** Le fingerprint blake2b de `W` nomme la
collection Qdrant. Or enrichir le graphe **ne change aucun vecteur** : deux
graphes différents produiraient la **même empreinte, donc la même collection**,
et deux expériences seraient indistinguables dans la traçabilité. Un trou
silencieux, du type le plus dangereux — il ne lève aucune erreur.

**Enfin, ADR-030 crée une seconde dépendance au graphe** : quatre de ses huit
opérations sont *dérivées du graphe*. Si le graphe qui sert à la dérivation est
celui de la config sous test, la stratification varie avec l'objet mesuré —
la circularité qu'ADR-029 écarte, revenue par une porte latérale.

## Décision

### 1. Deux rôles du graphe, jamais confondus

La distinction structurante n'est pas entre deux versions mais entre **deux
rôles** :

| Rôle | Graphe | Fonction | Varie ? |
|---|---|---|---|
| **Dérivation** | `G₀` — **graphe témoin** | Calcule les opérations dérivées d'ADR-030 (`graph_hop`, `contexte_structurel`, `succession_temporelle`, `fondement_textuel`) | **Jamais** dans une campagne |
| **Récupération** | `G₀`, `G₁`, `G₂`… | Alimente le moteur sous test | Oui — c'est le levier |

**Invariant** : le rôle de dérivation appartient **en permanence** au graphe
témoin ; un graphe enrichi n'a **jamais** que le rôle de récupération. La
stratification devient ainsi un invariant de campagne, et les comparaisons
portent bien sur la récupération.

`G₀` est le graphe produit par le pipeline d'ingestion de référence : les
arêtes minées (`cites`, `succeeded_by`, `references`, `modifies`, `contains`),
sans enrichissement.

### 2. Les relations dérivées ne sont pas ingérées

Les opérations dérivées d'ADR-030 sont **abstraites et calculées**, jamais
écrites en base. Ce n'est pas qu'une hygiène de stockage : une relation qui
n'est jamais écrite ne peut jamais être lue par le retriever, donc **jamais
être à la fois l'entrée du moteur et l'étalon qui le juge**. Le garde-fou
d'ADR-029 est obtenu **par construction** plutôt que par discipline — il ne
repose sur la vigilance de personne.

### 3. Le triplet `(W, G, R)`

`G` devient le troisième terme de description d'une expérience, avec son
**identifiant propre**, distinct du fingerprint de `W` :

```
ingest(corpus, W)                    → collection    [lent]
enrich(collection, G)                → graphe        [levier]
retrieve(collection, graphe, R, topics) → run        [rapide]
```

Tout artefact de run trace les **trois** termes, plus le graphe ayant servi à
la dérivation des opérations (`G₀` par invariant, mais consigné explicitement —
un invariant non tracé n'est pas vérifiable).

### 4. Protocole de comparaison : le passage témoin obligatoire

Un graphe enrichi `Gᵢ` n'entre pas dans le balayage avant d'avoir passé un
**test de non-régression sur config témoin** :

1. **Gel** : qrels gelées (hash consigné), config de récupération de référence
   `R₀`, graphe témoin `G₀`.
2. **Passage témoin** : `(W₀, Gᵢ, R₀)` contre `(W₀, G₀, R₀)` — **un seul
   facteur varie**.
3. **Verdict** : par **test statistique apparié** (ADR-007, E-P2-09), jamais
   par comparaison de moyennes.
4. **Portail** : `Gᵢ` n'entre dans le balayage `W × G × R` que s'il ne dégrade
   pas.

**Raison** : si le graphe et la config bougent ensemble, un écart de métrique
n'est attribuable à rien. Le témoin isole le facteur.

**Limite à assumer, écrite ici pour ne pas être découverte plus tard** : un
test apparié sur un jeu de requêtes modeste détecte mal les petits effets.
« Pas de dégradation significative » **n'est pas** « pas de dégradation ». Le
passage témoin est un garde-fou contre les régressions franches, **pas une
preuve d'innocuité**.

Règle héritée d'ADR-027, applicable telle quelle : deux versions de graphe se
comparent **sur leurs runs archivés**, jamais sur des bases coexistantes.

### 5. Circularité méthodologique vs circularité de mesure

La démarche du programme est **itérative et circulaire dans le temps** :
construire, mesurer, apprendre que la mesure était mal posée, la refaire. C'est
légitime, et c'est ce que la séparation observation / dérivation (ADR-030) rend
praticable.

Ce qui est proscrit est la **circularité de mesure** : l'étalon dérive de
l'objet qu'il juge **au même instant** — la « règle anti-tautologie »
d'ADR-028.

Discriminant opérationnel : *ma mesure d'aujourd'hui dépend-elle de l'artefact
qu'elle juge aujourd'hui ?* Trois protections, toutes structurelles :

- les qrels sont **gelées avant** l'exécution de la config qu'elles jugent ;
- la dérivation se fait sur `G₀`, jamais sur le graphe sous test (§1) ;
- les arêtes dérivées ne sont jamais ingérées (§2), et `origin` (ADR-008)
  reste tenu avec discipline pour pouvoir exclure les arêtes jugées quand
  c'est le graphe lui-même qu'on évalue.

## Alternatives rejetées

- **Étendre `W` pour y loger le graphe** : changerait le fingerprint donc le
  nom de la collection Qdrant, alors qu'aucun vecteur ne bouge — force une
  ré-ingestion complète (~99,9 % du temps de run est l'embedding) pour une
  variation qui n'y touche pas.
- **Ne pas versionner le graphe** : deux expériences indistinguables, sans
  erreur levée.
- **Dériver les opérations depuis le graphe sous test** : la stratification
  suivrait l'objet mesuré.
- **Ingérer les relations dérivées** : commodité de lecture payée par la perte
  de la garantie structurelle de non-circularité.
- **Balayage direct sans passage témoin** : deux facteurs simultanés, aucun
  écart attribuable.

## Conséquences

- **B-13 (orchestrateur + sweep)** balaie `W × G × R`, et non `W × R`. À poser
  **avant** que l'orchestrateur ne soit figé.
- **B-10 (test apparié) devient prérequis du travail sur le graphe enrichi** :
  le passage témoin en dépend. Nouvelle dépendance `B-10 → travaux graphe`.
- **E-P2-10 s'étend à `G`** : la reproductibilité couvre le triplet. Un
  identifiant de graphe est consigné dans l'artefact de run et vérifié, comme
  le fingerprint de `W` l'est contre `MURPHY_META.meta_published_collection`.
- Le travail d'enrichissement et sa validation document par document vivent
  dans **l'environnement d'évaluation** (ADR-027 : « la config d'évaluation
  *est* la config du pipeline »), hors du chemin de service — cohérent avec
  l'état actuel, Neo4j étant peuplé mais non branché au backend.
- Le graphe témoin `G₀` doit être **rejouable** (E-T-02) : sa définition est
  celle du pipeline d'ingestion de référence, pas un état de base accidentel.

## Références

ADR-007 (test apparié) · ADR-008 (`origin`, artefacts immuables) · ADR-027
(étendu ici : `(W, R)` → `(W, G, R)`) · ADR-028 (règle anti-tautologie) ·
ADR-029 (circularité, strate 2) · ADR-030 (opérations dérivées) ·
`EXIGENCES_v0.md` E-P2-09/10 · `BACKLOG.md` B-10, B-13
