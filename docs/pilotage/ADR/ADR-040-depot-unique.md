# ADR-040 — Un seul dépôt : fin des sous-modules, contrat du flux dans un paquet partagé

**Statut** : ✅ Accepté (25 septembre 2026)

## Contexte

Le 27 juin 2026, le monodépôt d'origine a été découpé : un dépôt parent (infra, docs)
et trois sous-modules git, `murphy-backend`, `murphy-frontend` et `murphy-data`.

Trois mois plus tard, ce découpage coûte plus qu'il ne rapporte :

- **Les changements traversent les dépôts.** L'ADR-039 a touché `data/`, `backend/`,
  la doc du parent, et devait encore toucher `frontend/`. Chaque dépôt demande
  son commit, puis le parent un commit de pointeur. Rien ne garantit qu'ils partent
  ensemble.
- **Le contrat du flux existe en deux copies.** `backend/src/types/messages.ts` et
  `frontend/src/types/messages.ts` se déclaraient « à garder synchronisés ». Ils avaient
  divergé : le frontend ignorait `identifier`, les offsets et `ParentDocument`, et aucun
  outil ne l'a signalé.
- **Les sous-modules restent en HEAD détachée** et demandent une discipline (commit
  dedans, pousser, puis pointer) qu'aucun outil ne vérifie.
- **Le découpage ne sert rien.** Backend et frontend sont livrés ensemble, dans la même
  stack Compose, par la même personne. Aucune équipe, aucun cycle de version et aucun
  droit d'accès ne les sépare.

D'autres éléments partagés viendront : codes d'erreur, types d'API, constantes. Il faut
un mécanisme qui tienne à mesure qu'ils s'ajoutent.

## Décision

**Un seul dépôt.** `backend/`, `frontend/` et `data/` sont réintégrés avec leur
historique, réécrit sous leur préfixe par `git filter-repo`, si bien que
`git log -- backend/…` remonte aux commits d'origine. Ils **gardent leur emplacement** :
Compose, les chemins absolus vers `.env.dev` et les liens de doc restent valides.

**npm workspaces** pour le TypeScript : `backend`, `frontend` et `packages/*`, avec un
seul `package-lock.json` à la racine. `data/` est un projet Python posé à côté, hors
workspaces.

**`packages/` accueille uniquement ce qui franchit une frontière d'exécution entre deux
workspaces.** Premier paquet : `@murphy/contract`, le contrat du flux.

- Il contient des **schémas zod**, et les types en sont déduits (`z.infer`). Le backend
  compile contre les types. Le frontend valide les parts à leur arrivée avec les mêmes
  schémas (`useChat({ dataPartSchemas, messageMetadataSchema })`). Une modification casse
  la compilation des deux côtés à la fois.
- Il est **compilé** (`tsc` → `dist/`, CommonJS + `.d.ts`), parce que le backend est
  CommonJS et tourne avec `tsc`, `ts-node`, jest et `node dist/` en production. Le
  `postinstall` racine le construit ; les Dockerfiles et la CI le construisent
  explicitement.
- Un module par contrat, exporté par **sous-chemin** (`@murphy/contract/messages`),
  **sans barrel**. `typesVersions` reprend ces sous-chemins pour les résolveurs qui
  ignorent `exports` (ts-jest).

**Docker et CI suivent.** Le contexte de build devient la racine, et un `.dockerignore`
racine en exclut `.env*`, les `node_modules`, `data/` et `docs/`. En dev, seules
les sources sont montées. Une seule CI tourne à la racine (`npm run check`, puis le build
des deux images).

## Alternatives rejetées

- **Garder les sous-modules, deux copies et un script de comparaison** : protège un seul
  fichier, et chaque nouvel élément partagé ajoute une copie. Rien ne garantit que les
  deux côtés soient livrés au même commit.
- **Un paquet `murphy-contract` versionné dans son propre dépôt** : il faut un registre
  privé, un jeton dans la CI et dans Docker, et trois dépôts pour chaque changement
  (publier, puis monter la version des deux côtés). Surtout, backend et frontend peuvent
  tourner sur deux versions du contrat alors qu'ils se parlent directement. Ce choix
  convient à des équipes aux cycles distincts, ce que Murphy n'a pas.
- **Un paquet livré en source TypeScript, sans compilation** : le frontend s'en
  accommoderait (`transpilePackages`), mais pas le backend (`rootDir`, et `node dist/` en
  production).

## Conséquences

- La migration a produit quatre commits : le retrait des sous-modules, puis une fusion
  par dossier. Les dépôts `left-eyebr0w/murphy-{backend,frontend,data}` sont à archiver,
  avec un renvoi vers le dépôt unique.
- Le **contrat Python ↔ TypeScript** (payload Qdrant, `documents`, pointeur ; ADR-039)
  ne peut pas passer par un paquet npm. Il reste répliqué des deux côtés.
  S'il grossit, la piste est de l'écrire sous forme de schéma (un JSON Schema tiré des
  modèles pydantic, dont les types TypeScript sont générés).
- **Changer le contrat, une dépendance ou une config d'app demande de reconstruire les
  images de dev** (`npm run serve:build`), puisque seules les sources sont montées. En
  contrepartie, plus aucun `node_modules` appartenant à root n'apparaît sur l'hôte.
- Le lockfile unique a été reconstruit en gardant, pour chaque dépendance directe, la
  version exacte que verrouillaient les anciens lockfiles.

## Références

ADR-039 (contrat ingestion ↔ serving) · `packages/contract/src/messages.ts`
