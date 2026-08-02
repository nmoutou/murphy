# Dossiers de recherche

> Revues de littérature menées pour instruire une décision de conception. La plupart
> répondent à une question posée par un ticket de la carte
> [Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1),
> et leur synthèse vit dans le commentaire de résolution de ce ticket ; le dossier TREC
> fait exception — il n'est né d'aucun ticket et a produit un ADR directement.
>
> **Ces documents ne décident rien.** Ils rassemblent ce que la discipline a publié
> et vérifié ; les arbitrages qui s'en déduisent vivent en ADR. Ils sont **datés et
> non maintenus** — un dossier ne se met pas à jour, il se remplace.

| Dossier | Question | Ticket | Ce qu'il a changé |
|---|---|---|---|
| [Collections de test à requêtes générées](requetes-generees.md) | Quels modes d'échec sont documentés pour les collections dont les requêtes descendent des documents ? | [#6](https://github.com/left-eyebr0w/murphy/issues/6) | Le constat d'ADR-034 est **plus fort que ce que la littérature soutient** : le classement des systèmes survit à la dérivation descendante (τ ≈ 0,82–0,86). La justification par la méthodologie TREC est **inexacte** — les topics TREC sont filtrés sur le nombre estimé de documents pertinents |
| [Incomplétude des qrels et biais de pool](incompletude-qrels.md) | Comment mesure-t-on l'incomplétude d'un jeu de jugements, et le biais de son pool ? | [#7](https://github.com/left-eyebr0w/murphy/issues/7) | Le **biais de pool est non mesurable** en solo mono-système, par construction. L'incomplétude est **bornable** par le **résidu RBP**, local à un run et sans `R`. Et les mêmes auteurs **disqualifient nommément nDCG** faute de `R` connu → a ouvert [#14](https://github.com/left-eyebr0w/murphy/issues/14) |
| [Le réalisme des collections et son prix](realisme-collections.md) | Comment les collections de RI achètent-elles leur réalisme, et à quel coût ? | [#8](https://github.com/left-eyebr0w/murphy/issues/8) | `N_j ≈ 60–70` (`GOLDEN-SET.md` §7.4) est **optimiste d'un facteur ≈ 2,5** : la pratique publiée demande **150–165 requêtes jugées**. À budget constant, **peu profond et large bat profond et étroit**. Et **ordonner n'exige pas la puissance qu'exige trancher** |
| [Le remplacement du pooling à profondeur fixe au TREC Legal Track](deep-sampling-legal-track.md) | Comment le Legal Track a-t-il remplacé le pooling à profondeur fixe, et sous quelles conditions cette machinerie transfère-t-elle ? | [#17](https://github.com/left-eyebr0w/murphy/issues/17) | A **levé la réserve la plus sérieuse** de `trec-legal-track.md` : les deux sources non récupérées sont lues. Le pooling à profondeur fixe **n'a jamais tourné seul** — la panne est mesurée dès 2006 (accord poolé/stratifié jusqu'à `B` = 267, rupture à `B` ≥ 528) et remplacée en 2007 par l'échantillonnage `L07` à probabilité `p(d) = f(hiRank)` ; `R` devient un **estimateur de Horvitz–Thompson**, **sans intervalle publié en Ad Hoc/Batch** (seulement `C` « points d'échantillon »), avec IC 95 % en Interactive seulement. `F1@K` (2008–2009 seulement) a produit une **saturation de borne** (`K` = max pour tous les topics) et a été **scindé en 2011** en *Hypothetical F1* / *Actual F1*. **Corrige 9 points** du dossier antérieur, dont « assesseurs = réviseurs professionnels » (ce sont des étudiants en droit volontaires en Ad Hoc) |
| [TREC & le Legal Track comme référence méthodologique](trec-legal-track.md) | Existe-t-il une méthodologie établie pour ce que le programme construit seul, et laquelle transfère ? | *aucun — recherche menée en parallèle par le porteur* | A produit **[ADR-035](../ADR/ADR-035-paradigme-evaluation-trec-legal-track.md)** : le paradigme s'aligne sur le **Legal Track** (primat du rappel, seul track qui transfère). **Deux machines ordonnées** — A (collection, solo, P2) puis B (campagne plurielle, post-publication). **Présomption symétrique**. L'**appareil de réception** se bâtit avant, la **machinerie** après panne. La vérité s'achète **par assesseur** ; les labels gratuits en sont le premier incrément. Critère « **rien à jeter** ». ⚠️ Ce dossier a été **corrigé sur trois points** avant versement (voir son bandeau) |

**Régime de vérification.** Les affirmations portantes de chaque dossier ont été
recoupées à la source primaire (PDF de l'article, section citée), pas relayées depuis
un résumé. Les réserves — ce qui n'a pas pu être vérifié — sont écrites dans chaque
dossier plutôt que dans cet index.
