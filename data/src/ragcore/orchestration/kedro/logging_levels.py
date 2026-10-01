"""Applique ``KEDRO_LOG_LEVEL`` aux loggers du projet ; les bibliothèques tierces restent
au ``WARNING`` de la racine.

``configure_logging`` plutôt que ``dictConfig`` : Kedro réutilise la config gardée dans
``LOGGING.data``, et en réappliquerait sinon une ancienne.
"""

from kedro.framework.project import LOGGING, configure_logging

from ragcore.adapters.config.settings import LogLevel

PROJECT_LOGGERS = ("kedro", "data", "ragcore")


def apply_log_level(level: LogLevel) -> None:
    """Garde le reste de la config Kedro."""
    loggers = dict(LOGGING.data.get("loggers", {}))
    for name in PROJECT_LOGGERS:
        loggers[name] = {"level": level.upper()}
    configure_logging({**LOGGING.data, "loggers": loggers})
