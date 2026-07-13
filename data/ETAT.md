# État des lieux — 13 juillet 2026

> **Document temporaire.** Point d'étape après le franchissement du critère de fin de la
> migration. À supprimer une fois son contenu absorbé (dans les artéfacts, ou dans un
> commit qui rend ce texte inutile).

---

## 🔴 URGENT — rien n'est commité, et ce n'est pas une négligence bénigne

**106 fichiers `.py` de ragcore sur 159 ne sont pas suivis par git.**
Dernier commit : `39be0ac "Save"` — celui d'**avant** la migration.

Cinq lots de travail, plus celui d'aujourd'hui, n'existent **que sur ce disque**.

Ce n'est pas une hypothèse de risque, c'est une **répétition**. Le mémo
`etat-reel-depot-ragcore` dit :

> « N'avoir jamais été suivi par git est **la cause première** de la perte du 5 juillet. »
> (22 modules perdus définitivement, 3 voies de récupération épuisées.)

La consigne qui en avait été tirée — *« committer ragcore sur `main` AVANT d'y toucher,
même (surtout) cassé »* — **n'a jamais été appliquée**. Depuis, le pipeline s'est mis à
**fonctionner**. Ce qu'on perdrait aujourd'hui est incomparablement plus grand qu'en juillet.

**À faire avant toute autre chose.** Deux dépôts : `data/` → `murphy-data`, puis le
pointeur de sous-module dans `murphy`.

---

## ✅ Ce qui est acquis aujourd'hui

### Le lancement des services

Depuis `data/`, sans changer de répertoire :

```bash
npm run up      # mongo + qdrant + neo4j + TEI (GPU). Ni backend, ni frontend.
kedro run
npm run down
```

- **Profils Compose** à la racine : `ingest` (bases + TEI) / `serve` (+ backend/frontend).
  Les 3 bases ne portent **aucun** profil : socle commun, déclaré **une seule fois**.
- `data/package.json` = un simple renvoi (`npm --prefix ..`). Aucun code Node ici.
- ⚠️ `docker compose down` **sans** `--profile` ne stoppe **pas** les services profilés : il
  rapporte un succès en les laissant tourner. Les scripts nomment les deux profils.

### Un seul `.env`, et la règle qui l'explique

**`.env.dev` à la RACINE. Plus de `.env` dans `data/`** (en créer un n'a aucun effet :
`adapters/config/settings.py` lit la racine par chemin absolu).

> **Une variable dont la valeur diffère entre l'hôte et le conteneur ne doit pas avoir un
> seul nom.**

Le pipeline tourne sur l'**hôte**, les bases en **conteneur** (`localhost:27017` vs
`mongo:27017`). Le fichier porte donc les URLs **côté hôte** — l'hôte est celui qu'on ne
*peut pas* surcharger — et **compose surcharge les conteneurs en littéral dans le YAML**.

`MONGODB_DATABASE` et `EMBEDDING_MODEL_NAME` sont **dérivés** par compose, jamais saisis :
*une valeur jamais tapée deux fois ne peut pas être tapée différemment deux fois.*

### Le garde-fou TEI (§6 rendue vérifiable)

TEI ne sert **que** le modèle de son `--model-id` et **ignore le champ `model` de la
requête**. Une divergence avec `parameters.yml` écrirait les vecteurs du **mauvais** modèle
dans la collection nommée d'après le **bon** — sans lever, sans logguer, visible seulement
à la recherche.

`assert_service_serves_model()` interroge **`GET /info`** et refuse de démarrer sur un écart.
**Vérifié en le faisant échouer pour de vrai** contre le vrai service.

- ⚠️ `/info` est à l'**origine**, PAS sous `/v1` : s'y tromper donne un 404, donc un garde-fou
  qui ne se déclenche **jamais** — pire que pas de garde-fou.
- ⚠️ **Il vit dans le HOOK, pas dans l'embedder**, et c'est structurel : `SagaExecutor` attrape
  `Exception` pour compenser. Levée dans un worker, l'erreur deviendrait un échec *par
  document*, compensé N fois, et le run conclurait **« ok »**.
  *Un garde-fou qui dégrade en skip-par-document n'est pas un garde-fou.*

### Le `kedro run` RÉEL passe — le critère de fin est atteint

**7/7 nœuds, 92 secondes, contre les vraies bases** (LEGI) :

| | |
|---|---|
| documents | **766** (Mongo = manifest = nœuds Neo4j) |
| chunks vectorisés | **10 919** |
| arêtes Neo4j | **1 167** (`references`, `cites`, `modifies`, `contains` — types **dynamiques**) |
| échecs / inconnus | **0 / 0** |
| collection Qdrant | **`3119c73ab26b71121e40e079abe5a06c`** — l'empreinte figée par le golden |
| **vecteurs** | **766/768 dimensions non nulles** → **VRAIS** vecteurs (TEI sur RTX 3050) |

Le contrôle des vecteurs non nuls est **le seul test qui distingue « ça a tourné » de « ça a
tourné juste »** — la verrue `noop` écrit des vecteurs **nuls** dans la collection du vrai
modèle, où plus rien ne les distingue ensuite. À refaire systématiquement.

### Le bug qui bloquait tout — et que personne ne pouvait voir

`kedro run` **ne démarrait pas** : `TypeError: cannot pickle '_contextvars.Context'`.

**Cause :** `TelemetryHooks.__init__` allouait une boucle asyncio. Or `src/data/settings.py`
instancie le hook **à l'import**, et Kedro fait un `deepcopy` de ses settings dans
`KedroSession._init_store`. Une boucle asyncio n'est pas copiable.

Bug **pré-existant du lot 5**. Le smoke SequentialRunner ne pouvait pas l'attraper : il
construisait le pipeline **sans passer par `KedroSession`**. Il vivait exactement dans
l'angle mort entre « le DAG s'exécute » et « Kedro sait l'ouvrir ».

**Correctif :** `_runtime` devient une `@property` paresseuse.
**Règle :** *un `__init__` pose des attributs ; il n'alloue pas de ressource système.*

### Trois bugs latents tués au passage

1. `src/data/settings.py` chargeait `data/src/.env` — **un fichier qui n'a jamais existé**.
   No-op silencieux depuis toujours. Supprimé : deux endroits qui prétendent savoir « où est
   le .env » sont la cause même du bug.
2. `EMBEDDING_API_KEY=` / `QDRANT_API_KEY=` parsaient en `''` / `SecretStr('')`, **pas `None`**
   → validators « vide → None ».
3. `OpenAIEmbedder` sans `base_url` retombait sur `https://api.openai.com/v1` : un
   `EMBEDDING_SERVICE_URL` oublié aurait envoyé **tout le corpus chez OpenAI**, facturé, avec
   un autre modèle. `base_url` est désormais **obligatoire**.

### ⚠️ Le piège des deux parsers (il a mordu pour de vrai)

**Jamais de commentaire en fin de ligne dans un `.env`.** `docker-compose` les strippe,
**pydantic-settings NON** : il prend tout le reste de la ligne comme valeur.
`EMBEDDING_API_KEY=   # TEI needs none` a donné la chaîne littérale `'# TEI needs none'`,
qui serait partie en `Authorization: Bearer # TEI needs none`.
**Les commentaires vont au-dessus.** (Documenté en tête de `.env.example`.)

**194 tests unitaires verts, lint propre** (sans base ni `.env.dev` : la boucle hors-ligne tient).

---

## Ce qui reste

### 1. Committer — **aujourd'hui** (cf. l'alarme en tête)

### 2. Clore formellement le critère de fin : les 5 sources juri contre les vraies bases

Le run d'aujourd'hui était **LEGI**. Le critère (`migration-ragcore-artefact`) dit « les
**cinq** sources juri ». Les connectors juri existent et ont été mesurés (352 docs, 0 inconnu),
mais **jamais contre de vraies bases**.

C'est un `kedro run --params source=cass` (puis `capp`, `inca`, `jade`, `constit`).
**Une exécution, pas un chantier.**

### 3. Le lot B — la dette de doctrine

*Audité contre le code le 13 juillet, par ordre de gravité :*

| | État | Enjeu |
|---|---|---|
| **§1 registre d'alias** | `AliasRegistry` / `CanonicalKey` **absents** | Ce n'est plus une dette orthogonale : c'est le **chemin critique de la résolution juri** — et il ne suffit pas (il faut *aussi* un extracteur de références juridiques) |
| **§9 MLflow / `ExperimentTracker`** | **absents** | « MLflow dès v0 » ; sans lui le hash de collection reste **opaque** |
| **§12 backends typés** | les clés-strings `"log"`/`"jsonl"`/`"mongo"`/`"aggregate"` sont **toujours là** (`adapters/telemetry/factory.py:86-89`) | la doctrine les **condamne nommément** |
| **§8 manifest dans la saga** | **hors** de la saga | + compensation Neo4j exacte absente (pas de tag `run_id`, pas de DETACH conditionnel) |
| **§5 `structural_path` → `source_path`** | jamais renommé | cosmétique |
| `tests/contract/` | **absent** | la substituabilité des ports n'est prouvée par aucun test exécutable |
| `nodes/discover.py` | **absent** | le node de diagnostic du delta (§1, emplacement « C ») |
| deadcode `src/data/pipelines/embedding/` | **toujours là** | à supprimer |

### 4. Ce que le run d'aujourd'hui a fait *apparaître*

**🔴 Le serving est cassé d'avance.** Le backend lit `QDRANT_COLLECTION=chunks` ; le pipeline
écrit dans la collection **dérivée du fingerprint** (`3119c73a…`). Le premier
`npm run serve:up` interrogera une collection **vide**, et renverra zéro résultat **sans
erreur**. C'est le prochain vrai bug fonctionnel.
*Correctif architectural* (pas une valeur à changer à la main) : soit le backend **dérive** le
même hash, soit le pipeline **écrit la collection courante** dans un document de méta Mongo que
le backend lit au boot. La seconde est bien moins chère.
Un commentaire hurlant est posé dans `.env.example`.

**19 011 relations pendantes pour 1 167 arêtes.** §13 fonctionne (rien n'est perdu, tout est
différé) — mais ça **chiffre** l'ampleur du travail de résolution. Et c'est, gratuitement,
**la liste priorisée du prochain corpus à ingérer**.

**`chunk_size: 128` est en CARACTÈRES** → ~20 mots par chunk. Trop court pour porter du sens.
Le fingerprint existe précisément pour rendre cet **A/B** possible. À **mesurer**, pas à
décider à vide.

---

## Recommandation d'ordre

1. **Committer** (aujourd'hui, sans discussion).
2. **Les 5 sources juri** contre les vraies bases — clôt formellement le critère de fin.
3. Puis **choisir** :
   - **le serving** → rendre le produit *utilisable* (la collection Qdrant est le seul verrou) ;
   - **le lot B** → payer la dette de doctrine.

Ces deux-là ne sont pas dans le même registre : le premier livre de la valeur, le second
protège l'avenir. Le §1 (registre d'alias) est le point où ils se rejoignent — il est à la
fois dette de doctrine **et** chemin critique de la résolution juri.
