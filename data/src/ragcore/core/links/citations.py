"""Les cibles DÉCRITES : un lien sans ``@id`` devient une ``Citation`` du document."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models.citation import Citation
from .table import LinkTable
from .vocabulary import translate

__all__ = ["citation_from"]


def citation_from(
    reference: Mapping[str, Any],
    table: LinkTable,
) -> Citation | None:
    """La cible DÉCRITE : un champ sur le document, **jamais** un nœud du graphe.

    Appelée quand l'``@id`` est vide — et c'est le seul critère. Ni la source, ni un
    drapeau déclaratif : l'identification, ou son absence. Le ``describes_targets`` qui
    régnait ici distinguait « le vide est la norme » (juri) de « le vide est une scorie »
    (LEGI) ; la mesure du corpus a montré que cette seconde moitié était fausse — les 89
    ``<LIEN>`` LEGI à ``@id`` vide portent **tous** un texte de désignation et un
    ``typelien``, exactement comme les 68 de la jurisprudence. Le drapeau ne protégeait
    d'aucun bruit : il jetait 89 citations réelles en silence.

    Rend ``None`` s'il n'y a pas même un texte : une balise sans identifiant ET sans
    désignation ne dit rien du tout. Ce n'est pas un renoncement, c'est une absence.

    Le verbe suit la doctrine de ``Relation.relation_type`` : traduit si la table le
    sait, brut sinon. Un mot non traduit entre sous son nom plutôt que de disparaître.
    """
    text = str(reference.get("label", "")).strip()
    if not text:
        return None

    raw_typelien = str(reference.get("typelien", ""))
    verb, _ = translate(table.translation, raw_typelien)
    return Citation(
        text=text,
        verb=str(verb) if verb is not None else raw_typelien,
        sens=str(reference.get("sens", "")),
    )
