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
fonctionnel. Sa **mesure** relève de la phase 3 (hypothèse H-07).

## État

**Phase 0 en cours.** Ordre de travail retenu, par dépendance :

1. problème → 2. utilisateurs cibles → 3. valeur mesurable → 4. périmètre in/out
→ 5. hypothèses, contraintes et risques → 6. gouvernance → 7. jalons macro.

Les hypothèses et les contraintes n'ont pas de livrable propre : elles ouvrent
le registre des risques, dont elles sont le matériau.
