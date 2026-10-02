"""Les six rôles d'une balise : chacun correspond à un traitement qu'on ne sait pas
faire génériquement.

- ``BODY`` : le texte du document, pour Mongo et l'embedding ;
- ``LINK`` : une arête, traitée par ``core/links`` ;
- ``VERSION`` : l'axe temporel (``date_debut``/``date_fin``/``etat``), absent de la
  jurisprudence mais nommé, pour qu'un filtre « en vigueur au… » ait de quoi lire ;
- ``TITLE`` : le titre, qui a son champ dédié et n'entre pas en métadonnée (ADR-026) ;
- ``META`` : tout champ plat qui n'est rien de cela. Il doit être déclaré ; sans
  renommage dans ``meta_renames``, il reste non configuré (ADR-023) ;
- ``IGNORED`` : une balise connue qu'on n'ingère pas, ni en métadonnée ni en signal
  (ADR-027).

Une balise sans rôle ne disparaît pas : elle ressort en inconnu, et le golden test la
fait échouer.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Role"]


class Role(StrEnum):
    """Un seul par balise. Un enum fermé, contrairement aux verbes : un rôle est une
    décision d'architecture, il n'arrive pas du corpus.
    """

    BODY = "body"
    LINK = "link"
    VERSION = "version"
    TITLE = "title"
    META = "meta"
    IGNORED = "ignored"
