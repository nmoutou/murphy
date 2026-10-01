"""Kedro appelle la fin de run même si l'assemblage a échoué : sans session, elle ne
doit pas masquer l'erreur d'origine.
"""

from ragcore.orchestration.kedro.hooks import TelemetryHooks


def test_ending_a_run_on_a_hook_that_was_never_wired_does_not_explode() -> None:
    TelemetryHooks().after_pipeline_run()


def test_failing_a_run_on_a_hook_that_was_never_wired_does_not_explode() -> None:
    TelemetryHooks().on_pipeline_error(RuntimeError("assemblage raté"))
