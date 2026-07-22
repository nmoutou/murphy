"""``CocitationPair`` — une paire de documents juridiquement liés, minée du graphe.

Sortie du socle d'extraction de la **strate 2** (B-07). ADR-029 a rétrogradé la
strate 2 : elle ne produit **plus des qrels scorables** mais un **diagnostic de
co-citation précision-seulement**. Ce module modélise donc un *fait mécanique* du
graphe — « ``source`` est lié à ``target`` par le verbe ``verb`` » — jamais un
grade de pertinence.

**Une paire = une arête directe orientée.** Le choix (acté au recadrage B-07) est
l'arête `source -[verb]-> target` telle qu'elle existe dans Neo4j, pas la
co-citation bibliométrique via un tiers : cette dernière introduirait une notion
de *degré* (le nombre de citants communs) que le graphe ne porte pas et qu'ADR-029
bannit. Si deux documents sont reliés par plusieurs verbes, il y a plusieurs
paires — la granularité est l'arête, d'où ``verb`` sur chaque ligne.

**L'identité est le ``identifier`` nu** (``"kind:raw"``, ADR-018) — la même chaîne
que ``RunEntry.doc_id`` (payload Qdrant ``identifier``). C'est ce qui rend le
recoupement paires ↔ run gratuit côté B-09, sans espace d'identité concurrent.
Pas de ``owner_id`` ici : un jeu de paires est intégralement intra-tenant (le
tenant est un paramètre du minage, pas une donnée par ligne).
"""

from __future__ import annotations

from murphy_eval.core.models._base import Frozen


class CocitationPair(Frozen):
    """Un lien de citation orienté entre deux documents existants du graphe."""

    source: str
    """Le ``doc_id`` canonique (ADR-018) du document citant — nœud d'origine de l'arête."""
    verb: str
    """Le type de l'arête Neo4j (``type(r)``), c.-à-d. le verbe de citation."""
    target: str
    """Le ``doc_id`` canonique du document cité — nœud cible de l'arête."""
