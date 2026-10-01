"""Le vocabulaire de liens de la jurisprudence.

Ses ``<LIEN>`` n'ont pas de cible identifiée : leurs attributs sont vides, et leur texte
décrit l'article visé en langue naturelle (« Articles 1103 et 1229 du code civil. »). Ils
deviennent des relations non formatées.

TODO : les résoudre en arêtes demande un extracteur de références juridiques (plusieurs
cibles par phrase, versions, renumérotations, cibles hors LEGI), sans ré-ingestion : la
phrase est déjà conservée.
"""

from ragcore.core.links import CITES, LinkTable, RelationVerb

__all__ = ["JURI_LINK_TABLE", "TYPELIEN_TO_VERB"]


TYPELIEN_TO_VERB: dict[str, RelationVerb] = {
    # Le seul typelien du corpus juri : un arrêt cite, il ne modifie ni n'abroge
    "CITATION": CITES,
}
"""Mesuré sur un corpus maigre (1 fichier CAPP, 1 INCA, 2 CONSTIT) : un export complet
en révélera d'autres, qui entreront sous leur nom brut."""


JURI_LINK_TABLE = LinkTable(
    translation=TYPELIEN_TO_VERB,
    # Aucun lien structurel : la jurisprudence est plate
    structural_kinds=frozenset(),
    ancestor_kinds=frozenset(),
)
"""Un verbe, un sens, aucune structure, aucune cible identifiée."""
