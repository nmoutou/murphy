"""Le nom des artéfacts d'un run — UN format, un seul endroit.

Le journal JSONL et le fichier de stats d'un même run doivent partager un stem
horodaté (``<iso>_<run_id>``) : c'est ce qui les fait se ranger et se retrouver côte à
côte. Ce stem était composé à l'identique dans deux modules (jsonl et hooks) — trois
lignes de ``strftime`` recopiées, qu'une seule dérive de format aurait désynchronisées.
Il vit ici, et les deux artéfacts ne diffèrent plus que par leur suffixe.
"""

from datetime import datetime

__all__ = ["run_scoped_filename"]


def run_scoped_filename(run_id: str, started_at: datetime, suffix: str) -> str:
    """``<AAAA-MM-JJTHH.MM.SS.mmmZ>_<run_id><suffix>``.

    Millisecondes (pas microsecondes) et ``.`` à la place de ``:`` : lisible ET valide
    comme nom de fichier sur tous les systèmes. Le ``run_id`` en fin de nom fait qu'un
    ``ls`` trie par date puis regroupe par run.
    """
    iso = (
        started_at.strftime("%Y-%m-%dT%H.%M.%S.")
        + f"{started_at.microsecond // 1000:03d}Z"
    )
    return f"{iso}_{run_id}{suffix}"
