# Dossiers de recherche

> Revues de littérature menées pour instruire une décision de conception. Chacune
> répond à une question posée par un ticket de la carte
> [Golden-set v1 — spécification prête à l'authoring](https://github.com/left-eyebr0w/murphy/issues/1),
> et sa synthèse vit dans le commentaire de résolution de ce ticket.
>
> **Ces documents ne décident rien.** Ils rassemblent ce que la discipline a publié
> et vérifié ; les arbitrages qui s'en déduisent vivent en ADR. Ils sont **datés et
> non maintenus** — un dossier ne se met pas à jour, il se remplace.

| Dossier | Question | Ticket | Ce qu'il a changé |
|---|---|---|---|
| [Collections de test à requêtes générées](requetes-generees.md) | Quels modes d'échec sont documentés pour les collections dont les requêtes descendent des documents ? | [#6](https://github.com/left-eyebr0w/murphy/issues/6) | Le constat d'ADR-034 est **plus fort que ce que la littérature soutient** : le classement des systèmes survit à la dérivation descendante (τ ≈ 0,82–0,86). La justification par la méthodologie TREC est **inexacte** — les topics TREC sont filtrés sur le nombre estimé de documents pertinents |
| [Incomplétude des qrels et biais de pool](incompletude-qrels.md) | Comment mesure-t-on l'incomplétude d'un jeu de jugements, et le biais de son pool ? | [#7](https://github.com/left-eyebr0w/murphy/issues/7) | Le **biais de pool est non mesurable** en solo mono-système, par construction. L'incomplétude est **bornable** par le **résidu RBP**, local à un run et sans `R`. Et les mêmes auteurs **disqualifient nommément nDCG** faute de `R` connu → a ouvert [#14](https://github.com/left-eyebr0w/murphy/issues/14) |
| [Le réalisme des collections et son prix](realisme-collections.md) | Comment les collections de RI achètent-elles leur réalisme, et à quel coût ? | [#8](https://github.com/left-eyebr0w/murphy/issues/8) | `N_j ≈ 60–70` (`GOLDEN-SET.md` §7.4) est **optimiste d'un facteur ≈ 2,5** : la pratique publiée demande **150–165 requêtes jugées**. À budget constant, **peu profond et large bat profond et étroit**. Et **ordonner n'exige pas la puissance qu'exige trancher** |

**Régime de vérification.** Les affirmations portantes de chaque dossier ont été
recoupées à la source primaire (PDF de l'article, section citée), pas relayées depuis
un résumé. Les réserves — ce qui n'a pas pu être vérifié — sont écrites dans chaque
dossier plutôt que dans cet index.
