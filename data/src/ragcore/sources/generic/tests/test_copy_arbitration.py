"""Les copies d'une même racine : identiques, une seule reste ; différentes, la plus
récente ; à date égale, toutes, pour que le parser refuse le document."""

from typing import Any

from ragcore.core.models.enums import SourceName
from ragcore.core.services.collision_reasons import (
    COLLISION_DUPLICATE_COPY,
    COLLISION_SUPERSEDED_COPY,
)
from ragcore.sources.generic.copy_arbitration import Facet, arbitrate

_ID = "LEGIARTI000006201477"
_VIGUEUR = f"/legi/TNC_en_vigueur/{_ID}.xml"
_NON_VIGUEUR = f"/legi/TNC_non_vigueur/{_ID}.xml"
_OLDER, _NEWER = 1_000, 2_000


def _tree(tag: str, etat: str) -> dict[str, Any]:
    return {"tag": tag, "attrib": {}, "text": etat, "tail": "", "children": []}


def _arbitrate(*facets: Facet):  # noqa: ANN202
    return arbitrate(SourceName.LEGI, _ID, facets)


def test_une_facette_seule_passe_sans_collision() -> None:
    alone = Facet(_VIGUEUR, _tree("ARTICLE", "VIGUEUR"), _OLDER)

    result = _arbitrate(alone)

    assert (result.kept, result.collisions) == ((alone,), ())


def test_des_racines_differentes_ne_sont_pas_des_copies() -> None:
    """``TEXTE_VERSION`` et ``TEXTELR`` : deux facettes d'un même texte."""
    version = Facet("/version.xml", _tree("TEXTE_VERSION", ""), _OLDER)
    struct = Facet("/struct.xml", _tree("TEXTELR", ""), _NEWER)

    result = _arbitrate(version, struct)

    assert result.kept == (struct, version)
    assert result.collisions == ()


def test_la_copie_la_plus_recente_fait_foi() -> None:
    """``ABROGE_DIFF`` le 20 août, ``ABROGE`` le 31 : l'état le plus avancé reste."""
    stale = Facet(_VIGUEUR, _tree("ARTICLE", "ABROGE_DIFF"), _OLDER)
    fresh = Facet(_NON_VIGUEUR, _tree("ARTICLE", "ABROGE"), _NEWER)

    result = _arbitrate(stale, fresh)

    assert result.kept == (fresh,)
    (collision,) = result.collisions
    assert collision.reason == COLLISION_SUPERSEDED_COPY
    assert (collision.identifier, collision.key) == (_ID, "ARTICLE")
    assert collision.files == (_NON_VIGUEUR, _VIGUEUR)


def test_la_plus_recente_peut_etre_dans_en_vigueur() -> None:
    """Le dossier ne départage rien : ``VIGUEUR_DIFF → VIGUEUR`` y retourne."""
    stale = Facet(_NON_VIGUEUR, _tree("ARTICLE", "VIGUEUR_DIFF"), _OLDER)
    fresh = Facet(_VIGUEUR, _tree("ARTICLE", "VIGUEUR"), _NEWER)

    assert _arbitrate(stale, fresh).kept == (fresh,)


def test_des_copies_identiques_n_en_font_qu_une() -> None:
    """La plus récente reste ; à date égale, le premier chemin."""
    older = Facet(_VIGUEUR, _tree("ARTICLE", "MODIFIE"), _OLDER)
    newer = Facet(_NON_VIGUEUR, _tree("ARTICLE", "MODIFIE"), _NEWER)
    twin = Facet(_VIGUEUR, _tree("ARTICLE", "MODIFIE"), _NEWER)

    result = _arbitrate(older, newer)

    assert result.kept == (newer,)
    (collision,) = result.collisions
    assert collision.reason == COLLISION_DUPLICATE_COPY
    assert collision.files == (_NON_VIGUEUR, _VIGUEUR)
    assert _arbitrate(newer, twin).kept == (twin,)


def test_a_date_egale_des_copies_differentes_restent_toutes() -> None:
    """Le parser refusera le document (``facet_root_duplicated``) : aucun choix au
    hasard."""
    one = Facet(_VIGUEUR, _tree("ARTICLE", "VIGUEUR"), _OLDER)
    other = Facet(_NON_VIGUEUR, _tree("ARTICLE", "ABROGE"), _OLDER)

    result = _arbitrate(one, other)

    assert result.kept == (one, other)
    assert result.collisions == ()


def test_chaque_racine_est_departagee_seule() -> None:
    """Un texte dont ``TEXTE_VERSION`` et ``TEXTELR`` ont chacun une copie périmée."""
    facets = (
        Facet("/vigueur/version.xml", _tree("TEXTE_VERSION", "ABROGE_DIFF"), _OLDER),
        Facet("/non_vigueur/version.xml", _tree("TEXTE_VERSION", "ABROGE"), _NEWER),
        Facet("/vigueur/struct.xml", _tree("TEXTELR", "a"), _OLDER),
        Facet("/non_vigueur/struct.xml", _tree("TEXTELR", "b"), _NEWER),
    )

    result = _arbitrate(*facets)

    assert [facet.path for facet in result.kept] == [
        "/non_vigueur/struct.xml",
        "/non_vigueur/version.xml",
    ]
    assert [collision.key for collision in result.collisions] == [
        "TEXTE_VERSION",
        "TEXTELR",
    ]
