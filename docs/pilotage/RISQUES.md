# RISQUES — Registre des risques du programme

> Risk Log au sens PM², **léger par conception** : un tableau, relu à
> chaque revue bimensuelle (ajout à la checklist `PILOTAGE.md` §1).
> Un risque qui se matérialise devient un item de `BACKLOG.md` (le
> registre ne suit pas les problèmes, seulement les menaces).
> Échelles : probabilité et impact **F**aible / **M**oyen / **É**levé.
> Réponses PM² : éviter / réduire / accepter / transférer.
>
> État au 18 juillet 2026.

| ID | Risque | P | I | Réponse | Mitigation / déclencheur de revue |
|---|---|---|---|---|---|
| R-01 | **Bus factor solo** : indisponibilité prolongée du porteur = arrêt du programme | M | É | Accepter (réduire à la marge) | La documentation exhaustive (ADRs, cadrage) *est* la mitigation : reprise possible par un tiers. Création de l'association (ADR-015) = réponse structurelle, jalon beta→publication |
| R-02 | **Dépendance GPU** pour l'embedding TEI (ADR-020) : indisponibilité matérielle bloque ingestion et baseline | M | M | Réduire | Chiffrer un plan B (CPU dégradé ou location ponctuelle) avant B-11 ; figer les versions de modèles pour éviter une ré-ingestion subie |
| R-03 | **Qualité / dérive des données DILA** : identifiants manquants ou incohérents (ECLI absents, doublons) compromettent l'identité canonique | M | É | Réduire | B-01 (vérification croisée) est conçu pour l'exposer tôt ; les fallbacks d'identité (ADR-018) absorbent les cas dégradés ; taux d'anomalie consigné au rapport |
| R-04 | **Dérive de périmètre vers P3** : tentation de retravailler l'applicatif (en pause) au détriment des exigences v0 | É | M | Éviter | Règle de tirage du `HANDBOOK.md` §3 : P3 n'a aucun item v0 ; toute envie P3 va en idées non engageantes (`BACKLOG.md` §4) |
| R-05 | **Golden-set v1 biaisé** : un set synthétique construit par le porteur seul reflète ses propres intuitions de pertinence | É | M | Accepter (borné) | Biais assumé par conception (ADR-017, strate 4) : le set v1 sert la baseline, pas la vérité ; remplacé par les qrels expertes en alpha ph.2 ; guide d'annotation explicite pour limiter l'arbitraire |
| R-06 | **Non-reproductibilité de la baseline** : dépendances non figées (modèles, index, seeds) rendent E-P2-10 invérifiable | M | É | Réduire | Figer versions et paramètres dans les artefacts de run dès B-05 ; double run exigé avant clôture (E-P2-10) |
| R-07 | **Évolution du cadre DILA** (formats, licence, accès) pendant la v0 | F | É | Accepter | Veille passive ; la Licence Ouverte Etalab est stable ; réévaluer si signal |
| R-08 | **Sur-outillage du pilotage** : le cadre documentaire (8 chantiers, ADRs, 5 livrables) consomme le temps d'exécution | M | M | Réduire | Le cadrage est clos ; mesure de débit (`HANDBOOK.md` §5) au vert = des items ✅ à chaque revue ; deux revues consécutives sans item ✅ = signal |

## Revue

À chaque revue bimensuelle : probabilités/impacts réévalués, risques
éteints archivés en bas de tableau avec date, nouveaux risques
ajoutés. Un risque É/É impose une décision (ADR) — il ne reste pas au
registre sans réponse.
