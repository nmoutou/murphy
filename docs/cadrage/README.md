# CADRAGE — Murphy

> Reprise du cadrage stratégique à partir du plan en six phases de `note.md`.
>
> **Régime : reprise à zéro.** Ce dossier ne s'appuie sur aucun document du
> programme existant, n'en reprend ni la structure ni les décisions. Ce qu'il
> conclut, il le **dérive**. La confrontation avec `docs/product/` et
> `docs/pilotage/` est une opération **distincte et différée**.

---

## Les six phases

| Phase | Objet | Livrables | État |
|---|---|---|---|
| **0** | Cadrage stratégique — le « pourquoi ». *Objectif : pouvoir dire non à des choses.* | note de cadrage (3–5 p.) · cartographie des parties prenantes (RACI) · registre de risques | 🔶 **en cours** |
| **1** | Discovery métier | taxonomie des requêtes · personas · parcours · **cahier des charges fonctionnel** · critères d'acceptabilité métier | ⬜ |
| **2** | Cadrage du corpus | inventaire des données · schéma de métadonnées · politique de fraîcheur/versionnage · note licences + RGPD · stratégie de parsing/chunking | ⬜ |
| **3** | Conception de l'évaluation | plan d'évaluation · golden set v1 · grille + guide annotateur · harness · dashboard · seuils go/no-go | ⬜ |
| **4** | Architecture | dossier d'architecture · ADR · matrice build/buy · modèle de coûts · note sécurité/hébergement | ⬜ |
| **5** | Baseline → itérations → pilote | rapport de baseline · journal d'expérimentations · rapport de pilote · plan de run · conduite du changement | ⬜ |

**Transverse à toutes les phases** : responsabilité juridique, disclaimers,
human-in-the-loop, classification AI Act, traçabilité des réponses.

### Deux règles de conduite

**Une seule phase est ouverte à la fois.** Rien des phases suivantes n'y est
décidé par avance — mais ce qu'on voit venir sans savoir encore qu'en faire est
**anticipé sans être tranché**, et c'est la fonction du registre des risques.

**Le registre des risques est repris à chaque seuil de jalon.** Aucun seuil de
sortie (T0 → T1 → T2) n'est prononcé avant que le registre ait été révisé avec
ce que la phase écoulée a appris. Le premier jet vise l'exhaustivité sans
l'atteindre : chaque revue comble ce qu'il a manqué.

### Note — le cahier des charges fonctionnel (phase 1)

La note de cadrage (§3) établit que Murphy relève de la **recherche
documentaire**, non de la question-réponse : la sortie est un ensemble de
documents-sources et rien d'autre, et l'usager en est l'**opérateur** (D-07) —
il constitue un ensemble, puis l'élargit, le concentre, ou le déplace.

Le cadrage s'arrête au **cadre** : le rôle d'opérateur, les modes d'échec
(bruit / silence), l'ensemble atteignable comme unité de valeur. Le **contenu**
— quels gestes de pilotage, sur quoi ils portent, ce qu'ils garantissent, ce que
le système restitue à chaque tour — est le premier objet du cahier des charges
fonctionnel. Sa **mesure** relève de la phase 3 (hypothèse H-12).

## Ce que le cadrage ne contient pas

Le cadrage produit les livrables des six phases, et rien d'autre. N'en font pas
partie et ne se décident pas ici : le **backlog**, l'**emploi du temps**, tout
dispositif de suivi (Kanban, Gantt), les **KPI**, et la définition des
**portefeuilles de projet**. Ces objets relèvent du pilotage, dont l'appareil se
constitue à part.

Un seul cas est mitoyen : **lister les ressources nécessaires** est bien un
travail de cadrage, mais anticipé d'un régime — on liste en T0 ce dont T1 aura
besoin, en T1 ce dont T2 aura besoin. Plus tôt, la liste n'a pas d'objet.

## La structuration du pilotage

**À faire en fin de cadrage, et pas avant** : le cadrage doit d'abord dire ce
qu'il y a à piloter. Cette étape ne porte pas sur le projet mais sur la façon de
conduire les six phases, et son produit sert ensuite tout le reste. Elle a trois
objets.

**Le choix d'une méthodologie.** L'objectif est une conduite fortement
structurée, de façon à pouvoir *optimiser* les processus plutôt que les subir —
au premier chef les **processus légaux**, dont le registre des risques montre
qu'ils pèsent la moitié de la charge (§5.6, §5.7). Le choix n'est pas fait, et
il ne se réduit pas à un cadre unique : **gouverner** des processus, **gérer** le
risque et **produire** des livrables de projet sont trois questions distinctes,
qu'aucun cadre ne traite toutes les trois. Un cadre de gouvernance, en
particulier, ne fournit pas de gabarit de livrable.

**Le format des livrables de seuil.** Aucun seuil (T0 → T1 → T2) ne devrait se
prononcer sans qu'il soit écrit *ce qui doit être produit, sous quelle forme, et
qui constate*. Le registre des risques est repris à chaque seuil (voir les règles
de conduite), mais ni la forme de cette reprise, ni celle des autres pièces
attendues, ne sont aujourd'hui définies.

**L'archivage des revues.** Les revues de risques successives doivent se ranger
quelque part et rester relisables : une révision qu'on ne peut pas rouvrir ne
prouve rien, et le régime haut-risque en demande précisément la preuve
(registre des risques, **R-16** — système de gestion des risques continu, à
réexamen périodique). Un dépôt dédié est la piste envisagée.

Deux manques connus du registre des risques attendent cette étape et n'ont pas à
être comblés avant elle : la **vraisemblance** de chaque risque, et l'**échéance
de décision** qui en porte l'urgence. Ce sont des attributs de pilotage, pas de
cadrage.

## État

**Phase 0 en cours.** Ordre de travail retenu, par dépendance :

1. problème → 2. utilisateurs cibles → 3. valeur mesurable → 4. périmètre in/out
→ 5. hypothèses, contraintes et risques → 6. gouvernance → 7. jalons macro.

Les hypothèses et les contraintes n'ont pas de livrable propre : elles ouvrent
le registre des risques, dont elles sont le matériau.
