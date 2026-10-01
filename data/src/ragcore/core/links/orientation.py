"""L'orientation d'un lien déclaré : le ``sens`` dit quel rôle le document courant joue.

Sortie d'``extraction.py`` : elle se lit seule, et c'est la seule règle qui transforme un
mot de la source (``source``/``cible``) en direction d'arête.
"""

from __future__ import annotations

from ..models.identifiers import Identifier

__all__ = ["SENS_CIBLE", "SENS_SOURCE", "orient"]

SENS_SOURCE = "source"
SENS_CIBLE = "cible"
"""Les deux rôles qu'un document peut jouer dans une arête qu'il déclare.

``sens="source"`` → *moi → lié*. ``sens="cible"`` → *lié → moi*.

Preuve empirique de cette lecture : l'article ``LEGIARTI000031367659`` (2015) porte des
liens ``sens="cible" typelien="CITATION"`` vers un arrêté de **2024**. Un article de 2015
ne cite pas le futur — c'est donc l'arrêté qui le cite.
"""


def orient(
    current: Identifier, linked: Identifier, sens: str
) -> tuple[Identifier, Identifier] | None:
    """Oriente l'arête selon le RÔLE que le document courant y joue.

    Rend ``None`` si le ``sens`` est inconnu — l'appelant compte le lien perdu. C'est ce
    qui remplace l'ancien ``_invert``, lequel ajoutait l'arête inverse **en plus** de
    l'originale : il DOUBLAIT chaque relation et rendait le graphe symétrique. Ici, un
    lien donne exactement une arête, orientée à la construction et jamais retournée.
    """
    if sens == SENS_SOURCE:
        return current, linked
    if sens == SENS_CIBLE:
        return linked, current
    return None
