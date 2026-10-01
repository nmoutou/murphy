"""Réglages du projet Kedro :
https://docs.kedro.org/en/stable/kedro_project_setup/settings.html."""

from ragcore.orchestration.kedro.hooks import TelemetryHooks

# Pas de `load_dotenv` : seul `ragcore.adapters.config.settings` lit l'environnement.
HOOKS = (TelemetryHooks(),)

DISABLE_HOOKS_FOR_PLUGINS = ("kedro-viz",)

# Remplace les défauts de Kedro au lieu de les compléter : pas de `conf/local/` superposé
CONFIG_LOADER_ARGS = {"base_env": "base"}
