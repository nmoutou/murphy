"""Les fixtures de LEGI, réexportées : il faut du vrai XML pour éprouver le parser
générique, et un second jeu de fixtures dériverait.
"""

from ragcore.sources.legislatif.tests.conftest import fixtures_dir

__all__ = ["fixtures_dir"]
