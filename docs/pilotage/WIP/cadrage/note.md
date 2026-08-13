Un conseil structurant d'abord : **ce ne sont pas deux projets parallèles**. L'évaluation n'est pas un livrable qui accompagne le moteur, c'est la *spécification exécutable* du moteur. En RAG juridique, on cadre l'évaluation **avant** de construire, sinon on itère à l'aveugle. Un seul projet, deux chantiers, un artefact pivot partagé : la taxonomie des requêtes.

## Phase 0 — Cadrage stratégique (le « pourquoi »)

Objectif : pouvoir dire non à des choses.

- Problème résolu, utilisateurs cibles, valeur mesurable (temps de recherche gagné ? taux de réponses fiables ?)
- Périmètre **in / out** explicite (ex. : « répond sur le droit du travail français, ne rédige pas de conclusions »)
- Hypothèses, contraintes, risques majeurs, gouvernance, jalons macro

**Livrables** : note de cadrage (3-5 pages), one-pager, cartographie des parties prenantes (RACI), registre de risques.

## Phase 1 — Discovery métier

C'est ici que se joue 50 % de la qualité finale.

- Entretiens juristes → **taxonomie des requêtes** : recherche de jurisprudence, question de droit ouverte, vérification de référence, comparaison de textes, veille, question hors périmètre…
- Pour chaque type : ce qu'est une « bonne réponse » selon un juriste

**Livrables** : taxonomie des requêtes (pondérée par fréquence/criticité), personas, parcours utilisateur, critères d'acceptabilité métier (ex. : *zéro citation inventée*, *toujours indiquer la version applicable*).

## Phase 2 — Cadrage du corpus

Le plus sous-estimé, et en droit c'est souvent le vrai projet.

- Inventaire des sources et **droits d'usage** (Légifrance, Judilibre, doctrine sous licence…)
- Structure documentaire : article / alinéa, arrêt / considérant, hiérarchie des normes
- **Dimension temporelle** : version en vigueur à une date donnée, textes abrogés, jurisprudence renversée — c'est le piège n°1 du RAG juridique
- Métadonnées obligatoires : juridiction, date, statut, portée

**Livrables** : inventaire des données, schéma de métadonnées, politique de fraîcheur/versionnage, note licences + RGPD, stratégie de parsing/chunking documentée et justifiée.

## Phase 3 — Conception de l'évaluation (avant le build)

Évaluez à **quatre niveaux séparés**, sinon vous ne saurez jamais *où* ça casse :

| Niveau | Exemples de métriques |
|---|---|
| Retrieval | recall@k, MRR, nDCG, context precision/recall |
| Génération (contexte donné) | groundedness/fidélité, exactitude des citations, complétude |
| Bout-en-bout | taux de réponses acceptables juriste, taux d'abstention appropriée |
| Opérationnel | latence p95, coût/requête, taux d'erreur |

- **Golden set** annoté par des juristes : 150-500 questions couvrant la taxonomie, incluant des cas adversariaux (question hors périmètre, texte abrogé, question ambiguë, piège de dénomination)
- Gel d'un jeu de test / jeu de dev distinct
- **LLM-as-judge calibré** : mesurez l'accord avec les annotations humaines (Cohen's kappa) avant de lui faire confiance
- Rythme : non-régression automatique en CI, revue humaine par échantillonnage, feedback produit en prod

**Livrables** : plan d'évaluation, golden set v1, grille d'annotation + guide annotateur, harness automatisé, dashboard, **seuils go/no-go** décidés à l'avance.

## Phase 4 — Architecture

**Livrables** : dossier d'architecture (ingestion → parsing → chunking → index hybride BM25+vectoriel → reranker → génération → citations → garde-fous), **ADR** (une décision = une fiche : contexte, options, choix, conséquences), matrice build/buy, modèle de coûts, note sécurité/hébergement.

## Phase 5 — Baseline → itérations → pilote

- **Baseline volontairement bête** (BM25 seul) mesurée sur le golden set : votre point de comparaison
- Chaque itération = une hypothèse, une mesure, une décision consignée
- Pilote utilisateurs réels avec critères de sortie définis

**Livrables** : rapport de baseline, journal d'expérimentations, rapport de pilote, plan de run/MLOps, plan de conduite du changement.

## Transverse

Responsabilité juridique (vous n'êtes pas un conseil), disclaimers, human-in-the-loop, classification AI Act, traçabilité des réponses.

---

**Les trois anti-patterns à éviter** : construire avant d'avoir défini le succès ; laisser les développeurs constituer seuls le golden set ; ne mesurer que le bout-en-bout (impossible de diagnostiquer).
