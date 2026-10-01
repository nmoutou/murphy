"""Applique ``KEDRO_LOG_LEVEL`` aux loggers du run.

Kedro configure le logging au démarrage avec son défaut (handler ``rich``,
``kedro: INFO``) : le projet n'a pas de ``conf/logging.yml``. Seuls les niveaux sont
réglés ici, pour ``kedro``, ``data`` et ``ragcore`` ; les bibliothèques tierces
(pymongo, httpx, neo4j) restent au ``WARNING`` de la racine.

On passe par ``configure_logging`` et non par ``logging.config.dictConfig`` : Kedro garde
la config appliquée dans ``LOGGING.data`` et la réutilise (``set_project_logging``,
bootstrap des sous-processus). Un ``dictConfig`` direct le laisserait en réappliquer une
ancienne.
"""

from kedro.framework.project import LOGGING, configure_logging

from ragcore.adapters.config.settings import LogLevel

PROJECT_LOGGERS = ("kedro", "data", "ragcore")


def apply_log_level(level: LogLevel) -> None:
    """Règle ``level`` sur les loggers du projet, en gardant le reste de la config Kedro."""
    loggers = dict(LOGGING.data.get("loggers", {}))
    for name in PROJECT_LOGGERS:
        loggers[name] = {"level": level.upper()}
    configure_logging({**LOGGING.data, "loggers": loggers})
