"""`parameters.yml` illisible arrête le run — mais seule une panne du CATALOGUE.

Le hook rattrapait tout ``Exception`` autour de ``catalog.load("parameters")`` et le
traduisait en « Impossible de charger `parameters.yml` ». Un bug sans rapport s'y
déguisait en config illisible. Seule la ``DatasetError`` de Kedro est traduite.
"""

from typing import Any

import pytest
from kedro.io import DataCatalog, MemoryDataset

from ragcore.orchestration.kedro.hooks import _load_parameters


class _BuggyCatalog:
    """Catalogue dont le chargement lève une exception qui n'est pas de Kedro."""

    def load(self, name: str) -> Any:
        raise TypeError(f"bug en chargeant {name}")


def test_les_parametres_du_catalogue_sont_rendus_tels_quels() -> None:
    catalog = DataCatalog(datasets={"parameters": MemoryDataset({"chunk_size": 384})})

    assert _load_parameters(catalog) == {"chunk_size": 384}


def test_des_parametres_absents_arretent_le_run_avec_un_message_clair() -> None:
    with pytest.raises(RuntimeError, match="Impossible de charger `parameters.yml`"):
        _load_parameters(DataCatalog())


def test_un_bug_hors_Kedro_n_est_pas_deguise_en_config_illisible() -> None:
    with pytest.raises(TypeError, match="bug en chargeant parameters"):
        _load_parameters(_BuggyCatalog())  # type: ignore[arg-type]
