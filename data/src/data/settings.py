"""Project settings. There is no need to edit this file unless you want to change values
from the Kedro defaults. For further information, including these default values, see
https://docs.kedro.org/en/stable/kedro_project_setup/settings.html."""

import structlog

# Pas de `load_dotenv` ici. L'appel qui s'y trouvait pointait sur `data/src/.env` — un
# fichier qui n'a jamais existé : un no-op silencieux. Il servait le résolveur `oc.env`
# d'OmegaConf, qu'aucun YAML de `conf/` n'utilise.
#
# La configuration est lue par `ragcore.adapters.config.settings`, qui va chercher le
# fichier UNIQUE de la racine par chemin absolu. Deux endroits qui prétendent savoir « où
# est le .env » sont précisément ce qui a produit le bug : il n'en reste qu'un.

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Instantiated project hooks.
# Hooks are executed in a Last-In-First-Out (LIFO) order.
from omegaconf.resolvers import oc  # noqa: E402

from ragcore.orchestration.kedro.hooks import TelemetryHooks  # noqa: E402

HOOKS = (TelemetryHooks(),)

# Installed plugins for which to disable hook auto-registration.
DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Class that manages storing KedroSession data.
# from kedro.framework.session.store import BaseSessionStore
# SESSION_STORE_CLASS = BaseSessionStore
# Keyword arguments to pass to the `SESSION_STORE_CLASS` constructor.
# SESSION_STORE_ARGS = {
#     "path": "./sessions"
# }

# Directory that holds configuration.
# CONF_SOURCE = "conf"

# Class that manages how configuration is loaded.
from kedro.config import OmegaConfigLoader  # noqa: E402

CONFIG_LOADER_CLASS = OmegaConfigLoader
# Keyword arguments to pass to the `CONFIG_LOADER_CLASS` constructor.
CONFIG_LOADER_ARGS = {
    "base_env": "base",
    "custom_resolvers": {
        "oc.env": oc.env,
    }
}

# Class that manages Kedro's library components.
# from kedro.framework.context import KedroContext
# CONTEXT_CLASS = KedroContext

# Class that manages the Data Catalog.
# from kedro.io import DataCatalog
# DATA_CATALOG_CLASS = DataCatalog
