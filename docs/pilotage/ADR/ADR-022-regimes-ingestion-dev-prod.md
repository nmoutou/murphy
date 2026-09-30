# ADR-022 — Régimes d'ingestion dev/prod : exhaustif vs sélectif

**Statut** : acté (18 juillet 2026) — **§5 amendé par ADR-023** (les
interrupteurs `exportation.<store>.enabled` sont remplacés par un unique
interrupteur d'embedding en dev) · **§7 amendé par ADR-024** (le
paramètre d'échantillonnage du connecteur est retiré : sans objet sur le
corpus réel ; le corpus témoin relève de `--params source=`) · **§5-§6
amendés par ADR-043** (routage d'audit laissé au code, conf morte refusée
par le modèle strict)

## Contexte

La préparation de la vérification d'identité croisée a révélé que
l'état des BDD n'est pas vérifiable en l'état : nœuds Neo4j maigres
(3 propriétés : `title`, `source`, `schema_version`), balises XML non
mappées reléguées dans un champ `unknowns` visible seulement dans
MongoDB, collisions de clés de métadonnées silencieuses (premier
arrivé gagne), conf morte (`field_mappings` sans consommateur),
champs superflus persistés (`parsed_at`, `structure["references"]`).

Or l'itération sur le modèle de données exige de **voir toutes les
données** — Neo4j étant l'outil
d'inspection privilégié. Le comportement sélectif actuel, défendable
en prod, est un obstacle en dev, particulièrement en v0.

## Décision

Le pipeline a **deux régimes**, différenciés par `ENVIRONMENT`
(précédent : garde-fou `nuke_all`). Le régime exhaustif est un
**échafaudage activable/désactivable**, pérenne (v1 incluse), pas un
mode jetable.

1. **Fin du concept « unknowns »**. Une balise non mappée est une
   balise **non-configurée**, à laquelle s'applique un traitement par
   défaut paramétrable : en dev, **ingestion** comme métadonnée ; en
   prod, exclusion + compteur de télémétrie `tag.unconfigured` au
   bilan de run (la vigie de dérive DILA survit sans le champ dans
   les données). Le champ `unknowns` de `ParsedDocument` disparaît.
2. **Nœuds Neo4j hydratés en dev** : `metadata` + `structure` +
   `content` + balises non-configurées. En prod : régime sélectif
   actuel.
3. **Aplatissement par préfixe de chemin complet** (ex.
   `article_meta_meta_spec_meta_article_num`) : zéro collision par
   construction. Remplace la clé « nom de balise nu » et sa collision
   silencieuse.
4. **Épuration Mongo** : `structure["references"]` n'est plus
   persisté (coût assumé : re-parsing du XML si la table de
   traduction des verbes change) ; `parsed_at` supprimé (doublon du
   manifest) ; bump de `SCHEMA_VERSION` groupé en une seule
   ré-ingestion.
5. **Interrupteurs de génération** : `exportation.<store>.enabled`
   pour MongoDB, Qdrant, Neo4j (cas d'usage immédiat :
   `qdrant.enabled: false` en dev — l'embedding est ~99,9 % du temps
   d'un run) ; routage d'audit (`EventBehavior`) exposé en
   `parameters.yml`. Non-candidats : `manifest` (idempotence) et
   `meta_pending_relations` (rejeu) — invariants, pas du volume. Le
   bilan de run déclare les stores actifs.
6. **Nettoyage** : `field_mappings` (conf morte) supprimé de
   `parameters.yml`.
7. **Échantillonnage de corpus** : paramètre de restriction du
   connecteur (en plus du `--params source=` existant), partagé entre
   l'itération dev et un corpus témoin de ré-ingestion.

## Alternatives rejetées

- **Garder `unknowns` à côté du traitement des non-configurées** :
  deux concepts pour le même fait, divergence garantie.
- **Préfixe minimal désambiguïsant** (chemin seulement en cas de
  conflit) : clés instables — une balise apparaissant à un nouvel
  endroit du XML renomme rétroactivement les clés existantes.
- **Whitelist unique pour tous les environnements** : c'est le statu
  quo ; il empêche l'itération sur le modèle de données qui est
  l'objet même de la v0.

## Conséquences

- Le `SCHEMA_VERSION` bump impose une ré-ingestion complète — groupée,
  une seule fois.
- La doctrine « rien n'entre en silence » de `ragcore` est amendée :
  l'exhaustivité (dev) ou le compteur (prod) remplacent la capture
  dans la donnée.

## Références

ADR-004 · ADR-018 · ADR-020 · ADR-023 · ADR-024 · ADR-043
