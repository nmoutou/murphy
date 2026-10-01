"""L'orientation d'un lien déclaré : le ``sens`` dit quel rôle le document courant joue.

C'est la seule règle qui transforme ``source``/``cible`` en direction d'arête.
"""

from __future__ import annotations

from ..models.identifiers import Identifier

__all__ = ["SENS_CIBLE", "SENS_SOURCE", "orient"]

SENS_SOURCE = "source"
SENS_CIBLE = "cible"
"""``sens="source"`` → *moi → lié*. ``sens="cible"`` → *lié → moi*.

Preuve de cette lecture : ``LEGIARTI000031367659`` (2015) porte des liens
``sens="cible" typelien="CITATION"`` vers un arrêté de 2024. Un article de 2015 ne cite
pas le futur : c'est l'arrêté qui le cite.
"""


def orient(
    current: Identifier, linked: Identifier, sens: str
) -> tuple[Identifier, Identifier] | None:
    """Un lien donne exactement une arête. ``None`` si le ``sens`` est inconnu :
    l'appelant compte le lien perdu.
    """
    if sens == SENS_SOURCE:
        return current, linked
    if sens == SENS_CIBLE:
        return linked, current
    return None
