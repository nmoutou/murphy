"""Un hook qui n'a jamais atteint `before_pipeline_run` doit pouvoir finir un run.

Kedro appelle `after_pipeline_run` / `on_pipeline_error` même quand l'assemblage a
échoué en route : sans session, donc sans agrégateur, la fin de run n'a rien à
faire — mais elle ne doit pas masquer l'erreur d'origine en explosant à son tour.
"""

from ragcore.orchestration.kedro.hooks import TelemetryHooks


def test_ending_a_run_on_a_hook_that_was_never_wired_does_not_explode() -> None:
    TelemetryHooks().after_pipeline_run()


def test_failing_a_run_on_a_hook_that_was_never_wired_does_not_explode() -> None:
    TelemetryHooks().on_pipeline_error(RuntimeError("assemblage raté"))
