# ADR-024 — Retrait de l'échantillonnage de corpus

**Statut** : acté (18 juillet 2026) — amende ADR-022 §7

## Contexte

ADR-022 §7 prévoyait un « paramètre de restriction du connecteur » (une
limite N documents, en plus du `--params source=` existant), avec deux
usages : (1) l'itération dev sur un petit corpus, (2) un corpus témoin
pour tester la ré-ingestion du `doc_id` article LEGI.

En préparant l'implémentation, la mesure du corpus réel a vidé
les deux usages :

- **Le corpus sur disque est déjà un extrait**, et réduit : 40 Mo au
  total, ~1100 documents. Volumétrie mesurée par source — LEGI 2564
  fichiers, JADE 256, CASS 92, CONSTIT 2, **CAPP 1, INCA 1**. Ce n'est
  pas le stock DILA (LEGI seul y pèse des dizaines de Go).
- **Usage 1 (itération rapide) — sans objet.** À cette échelle, et
  l'embedding désormais coupable en dev (ADR-023, l'embedding étant
  ~99,9 % du temps d'un run), limiter à N documents ne gagne rien de
  perceptible. Une limite numérique est de surcroît absurde sur des
  sources à 1 fichier.
- **Usage 2 (corpus témoin) — mal adressé par une limite N.** Le test
  de ré-ingestion exige un sous-ensemble **déterministe et désigné**, pas
  *petit* : ré-ingérer deux fois le *même* corpus et differ les
  `doc_id`. Le levier n'est pas « restreindre à N » mais « nommer le
  témoin ». Le `--params source=legi` **existant** désigne déjà le
  sous-ensemble LEGI ; le gel précis du témoin relève du test,
  pas d'un mécanisme du connecteur.

## Décision

Retirer le point 7 d'ADR-022 : **aucun paramètre de limite N n'est
ajouté au connecteur.** L'échantillonnage par source reste assuré par
le `--params source=` existant. La désignation et le gel du corpus
témoin de ré-ingestion relèvent du test, pas du connecteur.

## Alternatives rejetées

- **Implémenter la limite N quand même** (ADR-022 §7 littéral) : aucun
  cas d'usage v0 sur les données réelles ; « pas de tâche au cas où ».
  Un échafaudage pour un stock DILA complet qui
  n'est pas le corpus de la v0 serait un besoin de scaling (v1), pas de
  mesurabilité (v0).
- **Garder §7 ouvert « au cas où »** : laisserait un point d'ADR-022 sans
  critère de fin vérifiable.

## Conséquences

- ADR-022 §7 est **amendé** (retiré). Les autres points d'ADR-022 (fin des unknowns, hydratation
  Neo4j, aplatissement, épuration Mongo, nettoyage `field_mappings`,
  interrupteur d'embedding) sont inchangés.
- La désignation du corpus témoin (quel sous-ensemble LEGI) et son gel
  relèvent du test de ré-ingestion.
- Si un jour `xml_source_path` pointe vers le stock DILA complet, le
  besoin d'un échantillonnage renaîtrait — mais comme besoin de
  scaling (v1), révisable par ADR à ce moment, pas anticipé en v0.

## Références

ADR-022 (§7 amendé) · ADR-023 (même démarche, §5) · ADR-004 · corpus mesuré (40 Mo,
~1100 docs, CAPP/INCA à 1 fichier)
