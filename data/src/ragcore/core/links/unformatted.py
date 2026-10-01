"""Les cibles DÉCRITES : un lien sans ``@id`` devient une ``UnformattedRelation``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models.unformatted_relation import UnformattedRelation
from .subject import LinkSubject
from .table import LinkTable
from .vocabulary import translate

__all__ = ["unformatted_relation_from"]


def unformatted_relation_from(
    reference: Mapping[str, Any],
    table: LinkTable,
    subject: LinkSubject,
) -> UnformattedRelation | None:
    """La cible DÉCRITE : une relation non formatée, **jamais** un nœud du graphe.

    Appelée quand l'``@id`` est vide — et c'est le seul critère. Ni la source, ni un
    drapeau déclaratif : l'identification, ou son absence. Le ``describes_targets`` qui
    régnait ici distinguait « le vide est la norme » (juri) de « le vide est une scorie »
    (LEGI) ; la mesure du corpus a montré que cette seconde moitié était fausse — les 89
    ``<LIEN>`` LEGI à ``@id`` vide portent **tous** un texte de désignation et un
    ``typelien``, exactement comme les 68 de la jurisprudence. Le drapeau ne protégeait
    d'aucun bruit : il jetait 89 relations réelles en silence.

    Rend ``None`` s'il n'y a pas même un texte : une balise sans identifiant ET sans
    désignation ne dit rien du tout. Ce n'est pas un renoncement, c'est une absence.

    Le verbe suit la doctrine de ``Relation.relation_type`` : traduit si la table le
    sait, brut sinon. Un mot non traduit entre sous son nom plutôt que de disparaître.
    """
    target_text = str(reference.get("label", "")).strip()
    if not target_text:
        return None

    raw_typelien = str(reference.get("typelien", ""))
    verb, _ = translate(table.translation, raw_typelien)
    return UnformattedRelation(
        source_identifier=subject.current,
        target_text=target_text,
        relation_type=str(verb) if verb is not None else raw_typelien,
        sens=str(reference.get("sens", "")),
        source=subject.source,
    )
