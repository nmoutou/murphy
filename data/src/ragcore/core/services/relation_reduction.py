"""La réduction transitive — une règle de DOMAINE, pas un détail de source.

Deux choses sont fausses dans la version qu'on remplace, et il faut les dire toutes
les deux.

**1. Elle réduisait TOUT.** Or la réduction transitive supprime une arête ``A→C``
dès qu'un chemin ``A→B→C`` existe. Appliquée à des citations, elle DÉTRUIT UN FAIT :
« A cite B, B cite C, A cite C » est *trois* citations réelles, pas deux. Le texte
A cite bel et bien C, et il l'a écrit. Effacer cette arête, c'est faire mentir le
graphe sur ce que les textes déclarent.

**Seule la CONTENANCE est transitive par nature.** Un article dans un chapitre dans
un livre *est* dans le livre : l'arête directe est redondante avec le chemin, elle
n'ajoute aucune information. C'est exactement — et uniquement — ce cas que la
réduction doit traiter.

**2. Elle opérait à la mauvaise ÉCHELLE.** ``BaseRelationExtractor.extract`` voit UN
document. Or la hiérarchie d'un article ne peut pas être reconstruite depuis le seul
article : LEGI la déclare de deux côtés à la fois — ``<CONTEXTE>`` donne la *fermeture
transitive* (la chaîne complète des ancêtres, jusqu'à neuf niveaux), ``<STRUCTURE_TA>``
donne l'*arbre* (les liens parent→enfant directs), et ce dernier vit dans les fichiers
des SECTIONS, pas dans celui de l'article.

Il faut les deux — mesuré : ``STRUCTURE_TA`` seul ne couvre que 370 des 384 articles.
Il faut donc prendre l'UNION, et l'union d'une fermeture et d'un arbre n'est ni l'un
ni l'autre : c'est la fermeture. La réduire redonne l'arbre.

Réduire par document était donc structurellement impossible, pas seulement imprécis.
Ce module vit dans ``core/services`` et s'applique à l'union — en tête de la phase 2,
le seul endroit qui la voit.
"""

from collections import defaultdict

import networkx as nx

from ..links.vocabulary import CONTAINS, RelationVerb
from ..models.relation import Relation

__all__ = ["REDUCIBLE_TYPES", "reduce_transitively"]

REDUCIBLE_TYPES: frozenset[RelationVerb] = frozenset({CONTAINS})
"""Les seuls verbes dont la transitivité est une VÉRITÉ, et non un hasard du graphe.

Y ajouter ``CITES`` reviendrait à décréter que « qui cite un texte cite tout ce que
ce texte cite » — ce qu'aucun juriste ne soutiendrait, et ce qu'aucun texte ne dit.

**Un ensemble en liste blanche, et c'est essentiel depuis que le vocabulaire est
ouvert.** Un verbe brut arrivé d'une source (``zorglub``) n'est pas dans cet ensemble :
il n'est donc **jamais réduit**. C'est la seule position tenable — on ne connaît pas
l'algèbre d'un verbe qu'on n'a pas encore compris, et supposer sa transitivité
détruirait des arêtes vraies. Ce qu'on ne comprend pas, on le laisse intact.
"""


def reduce_transitively(
    relations: list[Relation],
    reducible: frozenset[RelationVerb] = REDUCIBLE_TYPES,
) -> list[Relation]:
    """Réduit la fermeture transitive en arbre, pour les seuls verbes réductibles.

    Les relations d'un verbe non réductible traversent **intactes** : ce n'est pas un
    oubli, c'est le sujet. Et depuis que le vocabulaire est ouvert, cela couvre aussi
    tous les verbes bruts que le domaine n'a pas encore traduits.

    Groupé par ``relation_type`` — deux verbes n'ont pas la même algèbre. Un cycle rend la réduction
    indéfinie (elle n'existe que sur les DAG) : le sous-graphe est alors conservé tel
    quel. Une donnée qu'on ne sait pas simplifier reste une donnée vraie.
    """
    if not relations:
        return relations

    kept: list[Relation] = []
    to_reduce: dict[str, list[Relation]] = defaultdict(list)

    for relation in relations:
        if relation.relation_type in reducible:
            to_reduce[relation.relation_type].append(relation)
        else:
            kept.append(relation)

    for group in to_reduce.values():
        kept.extend(_reduce_group(group))

    return kept


def _reduce_group(group: list[Relation]) -> list[Relation]:
    """Réduit un groupe homogène (même type). Rend les arêtes CONSERVÉES."""
    graph: nx.DiGraph = nx.DiGraph()
    # L'arête porte l'identité complète de la relation : après réduction, networkx ne
    # rend que des couples de chaînes. Sans ce registre, on saurait quelles arêtes
    # garder mais on aurait perdu leurs métadonnées — donc le typelien d'origine.
    by_edge: dict[tuple[str, str], Relation] = {}

    for relation in group:
        edge = (
            relation.source_identifier.serialize(),
            relation.target_identifier.serialize(),
        )
        graph.add_edge(*edge)
        by_edge.setdefault(edge, relation)

    if graph.number_of_edges() == 0:
        return []

    if not nx.is_directed_acyclic_graph(graph):
        # Un cycle de contenance est une anomalie du corpus (A contient B qui contient
        # A). On ne la corrige pas ici — on ne la CACHE pas non plus : les arêtes
        # passent, et le graphe portera l'anomalie visible plutôt que réduite.
        return list(by_edge.values())

    surviving = set(nx.transitive_reduction(graph).edges())
    return [relation for edge, relation in by_edge.items() if edge in surviving]
