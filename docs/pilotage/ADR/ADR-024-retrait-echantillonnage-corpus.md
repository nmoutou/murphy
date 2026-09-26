# ADR-024 — Retrait de l'échantillonnage de corpus

**Statut** : acté (18 juillet 2026) — amende ADR-022 §7

## Contexte

ADR-022 §7 prévoyait un « paramètre de restriction du connecteur » (une
limite N documents, en plus du `--params source=` existant), avec deux
usages : (1) l'itération dev sur un petit corpus, (2) le corpus témoin
exigé par E-P1-03 (B-02, test de ré-ingestion du `doc_id` article
LEGI).

En préparant l'implémentation (B-00-c), la mesure du corpus réel a vidé
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
- **Usage 2 (corpus témoin B-02) — mal adressé par une limite N.**
  E-P1-03 exige un sous-ensemble **déterministe et désigné**, pas
  *petit* : ré-ingérer deux fois le *même* corpus et differ les
  `doc_id`. Le levier n'est pas « restreindre à N » mais « nommer le
  témoin ». Le `--params source=legi` **existant** désigne déjà le
  sous-ensemble LEGI ; le gel précis du témoin est un travail de B-02,
  pas un mécanisme du connecteur.

## Décision

Retirer le point 7 d'ADR-022 : **aucun paramètre de limite N n'est
ajouté au connecteur.** L'échantillonnage par source reste assuré par
le `--params source=` existant. La désignation et le gel du corpus
témoin de ré-ingestion relèvent de B-02 (E-P1-03), pas de B-00.

## Alternatives rejetées

- **Implémenter la limite N quand même** (ADR-022 §7 littéral) : aucun
  cas d'usage v0 sur les données réelles ; « pas de tâche au cas où »
  (`PILOTAGE.md` §2). Un échafaudage pour un stock DILA complet qui
  n'est pas le corpus de la v0 serait un besoin de scaling (v1), pas de
  mesurabilité (v0).
- **Garder §7 ouvert « au cas où »** : laisserait un point de B-00 sans
  critère de fin vérifiable, contre la DoD (`HANDBOOK.md` §4).

## Conséquences

- ADR-022 §7 est **amendé** (retiré) ; le sous-item B-00-c disparaît du
  backlog. Les autres points de B-00 (fin des unknowns, hydratation
  Neo4j, aplatissement, épuration Mongo, nettoyage `field_mappings`,
  interrupteur d'embedding) sont inchangés.
- Le corpus témoin de E-P1-03 est explicitement rattaché à **B-02** :
  sa désignation (quel sous-ensemble LEGI) et son gel y seront traités.
- Si un jour `xml_source_path` pointe vers le stock DILA complet, le
  besoin d'un échantillonnage renaîtrait — mais comme besoin de
  scaling (v1), révisable par ADR à ce moment, pas anticipé en v0.

## Références

ADR-022 (§7 amendé) · ADR-023 (même démarche, §5) · ADR-004 · E-P1-03
(`EXIGENCES_v0.md`) · `BACKLOG.md` B-00 / B-02 · corpus mesuré (40 Mo,
~1100 docs, CAPP/INCA à 1 fichier)
