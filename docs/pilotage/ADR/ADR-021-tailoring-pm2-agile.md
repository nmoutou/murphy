# ADR-021 — Tailoring PM² + exécution agile (extension du chantier 6)

**Statut** : accepté (18 juillet 2026)

## Contexte

Le cadrage (chantiers 1–7) a produit un corpus de pilotage sans le
rattacher explicitement à un référentiel. Or l'horizon subventionné du
programme (`INSTITUTIONNEL.md`, canaux DINUM/ADEME/ANCT) rend
souhaitable un alignement sur **PM²**, référentiel de la Commission
européenne déjà noté comme standard cible. Par ailleurs, quatre
artefacts de pilotage manquaient : méthode de travail explicite,
spécification d'exigences (« cahier des charges »), backlog
matérialisé, registre des risques.

## Décision

1. **PM² adopté comme cadre de gouvernance documentaire**, avec
   tailoring solo explicite : la correspondance artefact PM² →
   document du programme est consignée dans `HANDBOOK.md` §2, qui fait
   foi. Les artefacts écartés (Issue Log séparé, Change Log,
   Stakeholder Matrix avant chantier 8) le sont avec motif.
2. **Exécution agile en flux tiré (kanban)**, pas de sprints : WIP ≤ 2,
   tirage par ordre du backlog, DoD à quatre conditions
   (`HANDBOOK.md` §3–4). Les user stories sont différées à l'alpha
   ph.1 (premiers utilisateurs réels) ; en v0 le besoin est exprimé en
   **exigences testables**.
3. **Quatre documents créés** : `HANDBOOK.md` (méthode),
   `EXIGENCES_v0.md` (exigences dérivées de `VERSIONS.md`, une
   spécification par version), `BACKLOG.md` (work plan + graphe de
   dépendances), `RISQUES.md` (registre, relu en revue bimensuelle —
   ajout à la checklist `PILOTAGE.md` §1).
4. **Pas de Gantt interne** : l'ordonnancement temporel est le graphe
   de dépendances du backlog, conformément à ADR-012 (capacités, pas
   de dates). Un Gantt daté ne peut être produit que ponctuellement,
   comme artefact externe du chantier 8.

## Alternatives rejetées

- **Scrum (sprints datés)** : engagements d'itération artificiels en
  solo à cadence variable ; la revue bimensuelle joue déjà le rôle des
  cérémonies.
- **Cahier des charges unique programme entier** : spéculatif au-delà
  de la version courante (beta 🔶 par conception) ; une spécification
  par version, dérivée de `VERSIONS.md`.
- **Outil de backlog dédié** (Notion, tracker) : casse l'unité
  documentaire du repo pour un volume d'items qui ne le justifie pas ;
  réexaminé à l'alpha.
- **Gantt interne** : contradiction frontale avec ADR-012.

## Conséquences

- `PILOTAGE.md` §1 : la checklist de revue gagne deux points — relire
  `RISQUES.md`, relever les deux mesures de pilotage
  (`HANDBOOK.md` §5).
- `EXIGENCES_v0.md` devient la source de traçabilité du backlog ; la
  clôture de v0 se constate sur ses exigences (inchangé sur le fond :
  elles dérivent des critères de sortie de `VERSIONS.md`).
- À chaque changement de version : nouvelle spécification
  `EXIGENCES_<version>.md`, backlog réamorcé, handbook révisé si
  nécessaire (introduction des user stories à l'alpha ph.1).
- `CADRAGE_demarche.md` : le chantier 6 reste clos ; la présente
  extension y est référencée sans le rouvrir.

## Références

`HANDBOOK.md` · `EXIGENCES_v0.md` · `BACKLOG.md` · `RISQUES.md` ·
`PILOTAGE.md` · ADR-012 · `VERSIONS.md`
