# PILOTAGE — Processus de pilotage du programme (chantier 6)

> Rituel de suivi d'un programme mené **en solo**. Léger par conception :
> le pilotage sert à garder la trace et la cohérence, pas à produire du
> reporting. Tout ce qui est décidé finit en ADR ; tout ce qui est
> constaté finit dans `STATUS.md`.

## 1. Revue bimensuelle

Une revue **toutes les deux semaines**, seul, à échéance fixe.
Durée cible : 30–45 minutes. Checklist :

1. **STATUS à jour** — refléter l'état réel de chaque projet (P1–P3),
   supprimer ce qui n'est plus vrai.
2. **Décisions → ADR** — toute décision prise depuis la dernière revue
   (y compris en session de travail avec un assistant) est consignée
   dans `decisions/` ; l'INDEX est mis à jour.
3. **Points ouverts** — relire la liste des points ouverts de
   `decisions/INDEX.md` : lesquels sont devenus tranchables ?
4. **Backlog repriorisé** — réordonner le backlog courant au regard des
   critères de sortie de la version en cours (`VERSIONS.md`), rien
   d'autre.
5. **Log de revue** — 10 lignes max, en tête de `PILOTAGE_log.md` :
   date, fait / décidé / bloqué / prochain pas.

## 2. Règles de gestion du backlog

- Le backlog est **ordonné par les critères de sortie de la version en
  cours** : une tâche qui ne sert aucun critère de sortie est soit
  différée, soit le signe qu'un critère manque (→ revoir `VERSIONS.md`
  par ADR).
- Pas de tâche « au cas où » : ce qui n'a pas de version cible sort du
  backlog et rejoint une liste d'idées non engageante.
- Les tâches du chantier 8 (institutionnel) sont backloguées comme les
  autres, avec leur version cible (beta ou publication).

## 3. Changement de version

Le passage à la version suivante est un **constat, pas une décision** :

- Déclencheur : **tous les critères de sortie** de la version courante
  (`VERSIONS.md`) sont vérifiés, preuves à l'appui (runs, tests,
  artefacts versionnés).
- Le constat est consigné par un **mini-ADR de clôture de version**
  (contexte : critères vérifiés ; conséquences : critères d'entrée de la
  version suivante activés).
- Si un critère s'avère invérifiable ou obsolète, on ne le contourne
  pas : on le **révise par ADR**, puis on constate.

## 4. Hygiène documentaire

- `VISION.md` ne change qu'exceptionnellement ; toute modification est
  un ADR.
- `PROGRAM.md` et `VERSIONS.md` ne changent que par ADR (les ✅/🔶/⬜
  doivent toujours refléter le registre).
- Les documents périmés sont déplacés dans `archive/` avec un bandeau,
  jamais supprimés.
- Les synthèses de session de travail sont des sources éphémères : leur
  contenu utile est reversé dans les documents pérennes, puis elles sont
  archivées.
