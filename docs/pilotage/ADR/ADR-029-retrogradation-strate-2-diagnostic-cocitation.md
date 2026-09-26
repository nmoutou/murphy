# ADR-029 — Rétrogradation de la strate 2 : diagnostic de co-citation, non qrels

**Statut** : Acté (20 juillet 2026, recadrage de B-07) — **amende ADR-017**
(rétracte « qrels » de la strate 2), **prolonge ADR-028**

## Contexte

ADR-017 nomme la strate 2 « **Qrels citation-minées (garde-fou
circularité)** » ; ADR-028 la classe comme régime **assisté** — miner les
paires *(décision citante, décision citée)* du graphe est *auto*, mais
poser que **citation ≈ pertinence** est une *hypothèse* que le porteur
tranche. E-P2-05 en tirait une preuve de sortie : un **fichier qrels
versionné, scorable** (format ADR-008).

À la préparation de B-07, l'hypothèse *citation ≈ pertinence* ne tient
pas en droit. Quatre raisons, la troisième décisive :

1. **Le graphe ne porte pas le degré de pertinence.** Une arête « A cite
   B » est binaire ; la métrique de décision attend des grades 0–3. Une citation
   ne dit pas *à quel point* B est pertinent. *(Référence mise à jour le 2 août
   2026 : la métrique n'est plus `nDCG@R` mais `RBP(p) + résidu`
   — [ADR-007](ADR-007-metrique-rbp-residu.md) — qui consomme les mêmes grades par
   projection linéaire `g/3`. **L'argument est inchangé** : il porte sur la nature
   binaire de l'arête, pas sur la métrique qui la consommerait.)*
2. **La gestion des relations est lourde** — coût réel, mais ce n'est pas
   un argument de validité.
3. **Les textes ne citent pas explicitement les concepts qu'ils
   traitent.** L'absence de citation n'est pas l'absence de pertinence.
   Des qrels citation-minées sont donc **massivement incomplètes** — et en
   IR, des qrels incomplètes ne sont pas seulement partielles : elles
   **pénalisent** un moteur qui remonte un document pertinent *non cité*
   comme un faux positif. Le signal est **biaisé**, pas seulement bruité.
4. **On ne saurait pas ce que vaut le résultat.** Sans oracle
   indépendant, une métrique de classement calculée sur ces qrels n'a pas
   d'interprétation.

Le mot « qrels » d'ADR-017 et l'intention « garde-fou circularité » de la
même ligne sont en **tension** : un garde-fou n'est pas un étalon de
classement. Cet ADR tranche du côté du garde-fou.

## Décision

**La strate 2 cesse d'être une source de qrels scorables.** Elle devient
un **set diagnostique de co-citation, précision-seulement**.

- **Ce qu'on mesure** : parmi les documents *remontés* par un moteur,
  quelle part est juridiquement liée (citée / citante) dans le graphe
  Neo4j. Un signal de **précision** sur des liens connus.
- **Ce qu'on ne mesure jamais** : le **rappel** (l'absence de lien ne
  pénalise pas — neutralise la raison 3), ni un **grade** de pertinence
  (binaire assumé — neutralise la raison 1), ni un **classement** absolu
  entre moteurs.
- **Régime (ADR-028)** : on ne garde que la part **auto** — le fait
  mécanique « A est lié à B » dans le graphe. On cesse de traiter la
  pertinence comme un *candidat* à trancher : l'hypothèse n'est pas
  assez solide pour porter un jugement, on n'en fait donc plus un jugement.

**Le graphe reste uniquement fournisseur de ce signal.** Utiliser le
graphe pour **suggérer** le golden-set (B-08) est **explicitement
écarté** : les mêmes paires deviendraient à la fois la suggestion et la
vérité terrain, réinjectant le biais de circularité que cet ADR combat.
L'assistance à la construction du golden-set sera pensée **séparément,
hors graphe de citations** (idée non engageante, `BACKLOG.md` §4).

### Redistribution dans le backlog

- **B-07** subsiste comme **socle d'extraction** : adapter Neo4j dédié
  dans `eval/` (premier chemin de lecture graphe du harnais, **hors
  `ragcore`** — ADR-027), requête Cypher extrayant les paires liées,
  writer des paires. Il ne produit plus « un fichier qrels » mais un
  **jeu de paires de co-citation** documenté (volumétrie + méthode).
- **B-09** (set diagnostique graph-hop) **consomme** ce socle. Dépendance
  nouvelle **B-07 → B-09**.
- **B-08** (golden-set) redevient **indépendant du graphe**.
- Débouché aval inchangé : **B-11** (baseline) reçoit de la strate 2 un
  chiffre *auto et reproductible*, mais **diagnostique** (précision sur
  liens connus), jamais une métrique de classement.

## Alternatives rejetées

- **Abandon sec de la strate 2** : jette un actif déjà payé (le graphe de
  citations de B-03) alors que la critique n'établit pas que le graphe est
  *inutile*, seulement qu'il est un *mauvais étalon de classement*.
- **Graphe → suggestion du golden-set** : ferait du graphe l'aide à
  l'annotation de B-08 ; la circularité (suggestion = vérité terrain)
  recontamine le golden-set avec le biais même qu'on dénonce.
- **Report hors v0** : laisserait un trou dans la couverture « signal
  automatique » de la baseline, alors qu'un signal diagnostique borné est
  légitime et bon marché.
- **Conserver le libellé « qrels »** : entretiendrait la confusion
  qu'ADR-028 nommait déjà — une sortie machine prise pour une vérité
  terrain.

## Conséquences

- **E-P2-05 change de libellé** : de « fichier qrels versionné,
  scorable » à « jeu de paires de co-citation miné depuis le graphe,
  usage diagnostique précision-seulement, volumétrie et méthode
  documentées ». Reste **assisté** au sens d'ADR-028 (la machine mine ; le
  porteur juge l'usage diagnostique, pas la pertinence de chaque paire).
- **ADR-017** : dans la table des strates, « Qrels citation-minées » se
  lit désormais « **Diagnostic de co-citation** (précision-seulement) » ;
  la ligne « Conséquences » ne compte plus les citations minées comme
  source de qrels de la baseline.
- **BACKLOG.md** : B-07 requalifié (socle d'extraction), arête `B-07 →
  B-09` ajoutée, note d'ordonnancement consignée.
- L'assistance à l'annotation du golden-set entre en **§4** (idées non
  engageantes), à cadrer hors graphe de citations.

## Références

ADR-017 (strates ; amendé ici) · ADR-028 (régimes de vérification ;
prolongé ici) · ADR-005 (échelle 0–3) · [ADR-007](ADR-007-metrique-rbp-residu.md) (RBP + résidu) · ADR-008
(format) · ADR-027 (frontière `eval/` sans `ragcore`) · `EXIGENCES_v0.md`
E-P2-05 · `BACKLOG.md` B-07/B-08/B-09/B-11
