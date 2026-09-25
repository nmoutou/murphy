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

# Importé APRÈS `structlog.configure` : les modules de `ragcore` doivent trouver structlog
# déjà configuré quand ils créent leurs loggers.
from ragcore.orchestration.kedro.hooks import TelemetryHooks  # noqa: E402

HOOKS = (TelemetryHooks(),)

# Installed plugins for which to disable hook auto-registration.
DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# REMPLACE les arguments par défaut de Kedro (`base_env: "base"`,
# `default_run_env: "local"`) au lieu de les compléter : aucun environnement d'exécution
# n'est donc superposé à `base` — il n'existe pas de `conf/local/`.
CONFIG_LOADER_ARGS = {"base_env": "base"}
