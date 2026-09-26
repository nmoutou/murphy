# Corrections — nettoyage des trois codebases

> Document de travail : il vit le temps du chantier de nettoyage et
> disparaît à sa clôture. Ce qui doit survivre part ailleurs — une
> décision en ADR, une dette différée en `BACKLOG.md` §4, un statut en
> `STATUS.md` (`PILOTAGE.md` §2).
>
> Audit du 25 septembre 2026 sur `main` (backend `c3d7ec8` + modifications
> locales non commitées, frontend `1000018`, data `7e420af`). Objectif :
> retirer les coquilles, le code mort et la sur-complexité, et ramener
> chaque codebase aux règles de `CLAUDE.md`.

## 1. Fichiers

| Fichier | Périmètre | Préfixe |
|---|---|---|
| [`transverse.md`](transverse.md) | Défauts à cheval sur plusieurs dépôts (contrat serving ↔ ingestion, déploiement, environnement) | `TR-` |
| [`backend.md`](backend.md) | `backend/` — Express + TypeScript | `BE-` |
| [`frontend.md`](frontend.md) | `frontend/` — Next.js + React | `FE-` |
| [`data.md`](data.md) | `data/` — Kedro + `ragcore` | `DA-` |
| [`coquilles.md`](coquilles.md) | Fautes de frappe dans la documentation — **lot exécuté** | `CQ-` |

Sévérité (même échelle que `WIP/B-07-revue-code.md`) :
**Bloquant** (une fonctionnalité est cassée ou un contrôle qualité est
rouge) · **Dette** (viole une règle de `CLAUDE.md` ou complique la
maintenance) · **Confort**.

Statut : ⬜ à faire · 🔶 entamé · ✅ fait · ⏸ attend une décision.

## 2. État des lieux mesuré

Mesuré dans un miroir hors dépôt (voir TR-06 : les `node_modules` locaux
sont inaccessibles). Les lignes marquées « après » donnent l'état à la
fin du lot correspondant.

| Projet | Types | Lint | Tests | Format |
|---|---|---|---|---|
| backend | `tsc` ✅ | **29 erreurs** eslint | **2 suites / 3 ne compilent plus** — 4 tests passent, les seuils de couverture ne sont pas mesurables | — |
| backend, après le 1er lot | `tsc` ✅ | ✅ 0 | ✅ 5 suites, 31 tests — **couverture 40 % des lignes**, sous le seuil de 65 % | — |
| backend, après le 2e lot | `tsc` ✅ | ✅ 0 | ✅ 9 suites, 54 tests — couverture 66 % des lignes ; seules les instructions (64,5 %) restent sous le seuil de 65 % | — |
| backend, après le 3e lot | `tsc` ✅ | ✅ 0 | ✅ 15 suites, 82 tests — couverture 90 % des lignes, **les quatre seuils sont tenus** | — |
| backend, après BE-07/BE-10 | `tsc` ✅ | ✅ 0 | ✅ 17 suites, 115 tests — couverture 95,5 % des lignes, 95,4 % des instructions, 90,9 % des fonctions, 91,6 % des branches | — |
| frontend | **1 erreur** `tsc` | **eslint ne démarre pas** | aucun test | — |
| frontend, après le lot FE-02/04/05/07 | `tsc` ✅ | ✅ 0, avertissements compris | aucun test | — |
| frontend, après le lot FE-06/08/10 | `tsc` ✅ | ✅ 0 | aucun test | ✅ Prettier (`format:check` en CI) |
| data | `mypy --strict` ✅ | **95 erreurs** ruff (toutes dans le code mort, DA-01) | 296 ✅ (86 % de couverture) | 12 fichiers à reformater |
| data, après le lot | `mypy --strict` ✅ | ✅ 0 | 294 ✅ (86 %) | ✅ |

## 3. Décisions prises

Prises en session le 25 septembre 2026. `PILOTAGE.md` §2 (b) les fait
passer par un **mini-ADR** avant exécution, puisqu'elles changent un
comportement visible. Exceptions, traitées comme de l'hygiène (§2 c),
sans ADR, sur décision du porteur (25 septembre 2026) :
- la suppression de la route `/documents/:eli`, qu'aucun client
  n'appelle ;
- BE-03 : sans proxy devant le backend, qui n'est pas encore déployé,
  `trust proxy` vaut `false`. La valeur sera à revoir avec TR-03.

| Décision | Items |
|---|---|
| Afficher dans l'interface les erreurs du pipeline (aujourd'hui avalées en silence) — ✅ faite, dans une modale ([ADR-041](../../product/ADR/ADR-041-erreurs-du-chat-en-modale.md)) | FE-03 |
| Ne plus faire confiance à `X-Forwarded-For` tel quel pour le rate-limit — ✅ fait, sans ADR | BE-03 |
| Supprimer la route `GET /api/v1/documents/:eli` — ✅ faite, sans ADR | BE-04 |
| **Conserver** le bouton « dossier » du `ChatBox` (placeholder « Work in progress ») | — |
| **Supprimer** la copie des réponses de l'IA (26 septembre 2026) — ✅ faite, sans ADR | FE-05 |

**TR-01 exige un ADR à part entière** : il fixe où vit le texte d'un chunk
entre l'ingestion et le serving.

## 4. Ordre d'exécution recommandé

1. **TR-01**, l'ADR du contrat serving ↔ ingestion. Il conditionne le
   modèle `DocumentChunk` du backend et du frontend : autant ne refaire
   ces fichiers qu'une fois.
2. **Remettre les contrôles au vert**, sans changer de comportement :
   - DA-01 → DA-04 : rapide et indépendant ;
   - BE-01, BE-02 : tests et lint ;
   - FE-01, FE-02 : `tsc` et eslint.
3. **Supprimer le code mort**, à comportement constant : BE-05, FE-04,
   FE-05.
4. **Appliquer les décisions** du §3 : FE-03, BE-03, BE-04.
5. **Refactorisations en cascade**, plus de 3 fichiers chacune, avec un
   plan annoncé avant de commencer : BE-06, BE-08, BE-09, FE-08.
6. **Mettre à jour `CLAUDE.md`** et les `docs/` de chaque projet (TR-05).

DA-05 (fichiers de plus de 300 lignes dans `ragcore`) est un chantier à
part, hors de cet ordre.

## 5. Critère de sortie

- backend : `npm run type-check`, `npm run lint` et `npm test` verts,
  seuils de couverture de `jest.config.js` compris ;
- frontend : `tsc --noEmit`, `npm run lint` et `npm run build` verts ;
- data : `ruff check`, `ruff format --check`, `mypy` et `pytest` verts ;
- **test de bout en bout** : une question posée dans l'interface affiche
  au moins une source et une réponse fondée sur son contenu (TR-01,
  TR-02). Une erreur provoquée, par exemple TEI arrêté, s'affiche à
  l'écran (FE-03).
