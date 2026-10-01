"""Les fixtures du parser générique — empruntées à LEGI, et c'est délibéré.

**Emprunter n'est pas dépendre.** Le parser et le chunker sont génériques, mais il faut du
*vrai* XML pour les éprouver : un arbre inventé ne porterait ni les ``<p>`` imbriqués, ni
les facettes fusionnées, ni les 23 ``<LIEN>`` frères d'un article réel. Dupliquer les
fixtures de LEGI ici en créerait un second jeu, qui dériverait — et c'est alors le test
qui mentirait, silencieusement.

La `conftest.py` est le mécanisme que pytest prévoit exactement pour ça : elle réexporte
la fixture sans qu'aucun module de test n'ait à l'importer (ce que ``ruff`` prend, à juste
titre, pour une redéfinition).
"""

from ragcore.sources.legislatif.tests.conftest import fixtures_dir

__all__ = ["fixtures_dir"]
