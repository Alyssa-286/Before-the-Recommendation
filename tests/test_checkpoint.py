"""Tests for resumable, config-pinned trial checkpoint state."""

from pathlib import Path
import tempfile
import unittest

from before_recommendation.checkpoint import (
    CheckpointConfigurationMismatch,
    CheckpointConflict,
    CheckpointStore,
    TrialStatus,
)
from before_recommendation.failures import FailureCategory
from before_recommendation.tracing import TrialIdentity


CONFIG_HASH = "a" * 64


def identity(scenario: str, **changes: object) -> TrialIdentity:
    data = {
        "scenario_id": scenario,
        "profile_id": f"objective-{scenario}",
        "goal_condition": "ambiguous",
        "marketing_condition": "neutral",
        "model_family": "deterministic_mock",
        "model_version": "mock-1",
        "repetition": 1,
        "prompt_template_id": "ambiguous-v1",
        "experiment_version": "phase1-deterministic-0.1.0",
        "config_sha256": CONFIG_HASH,
        "random_seed": 20260930,
    }
    data.update(changes)
    return TrialIdentity(**data)


class CheckpointTests(unittest.TestCase):
    def test_register_claim_complete_and_restart_skips_completed_trial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "phase1.sqlite3"
            store = CheckpointStore(path, CONFIG_HASH)
            first, second = identity("scenario-1"), identity("scenario-2")
            self.assertEqual(store.register_trials((first, second)), (first.trial_id, second.trial_id))
            self.assertEqual(store.register_trials((first, second)), ())
            self.assertEqual(set(store.pending_trial_ids()), {first.trial_id, second.trial_id})

            claimed = store.claim(first.trial_id)
            self.assertIs(claimed.status, TrialStatus.RUNNING)
            self.assertEqual(claimed.attempt_count, 1)
            completed = store.complete(first.trial_id, "traces.jsonl#0", "b" * 64)
            self.assertIs(completed.status, TrialStatus.COMPLETED)

            resumed = CheckpointStore(path, CONFIG_HASH)
            self.assertEqual(resumed.requeue_interrupted(), ())
            self.assertEqual(resumed.pending_trial_ids(), (second.trial_id,))
            self.assertIs(resumed.get(first.trial_id).status, TrialStatus.COMPLETED)

    def test_running_trial_requires_explicit_interruption_recovery_then_replays(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "phase1.sqlite3"
            first_store = CheckpointStore(path, CONFIG_HASH)
            trial = identity("scenario-interrupted")
            first_store.register_trials((trial,))
            first_store.claim(trial.trial_id)

            resumed = CheckpointStore(path, CONFIG_HASH)
            self.assertEqual(resumed.pending_trial_ids(), ())
            self.assertEqual(resumed.requeue_interrupted(), (trial.trial_id,))
            self.assertEqual(resumed.pending_trial_ids(), (trial.trial_id,))
            retried = resumed.claim(trial.trial_id)
            self.assertEqual(retried.attempt_count, 2)
            self.assertEqual(retried.interruption_count, 1)
            self.assertEqual([event["event_type"] for event in resumed.events(trial.trial_id)], [
                "registered", "claimed", "interrupted_requeued", "claimed",
            ])

    def test_failed_trial_needs_a_documented_explicit_requeue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = CheckpointStore(Path(temporary) / "phase1.sqlite3", CONFIG_HASH)
            trial = identity("scenario-failure")
            store.register_trials((trial,))
            with self.assertRaises(CheckpointConflict):
                store.requeue_failed(trial.trial_id, "temporary network outage")
            store.claim(trial.trial_id)
            failed = store.fail(trial.trial_id, FailureCategory.TIMEOUT)
            self.assertIs(failed.status, TrialStatus.FAILED)
            self.assertEqual(failed.last_failure_category, "timeout")
            with self.assertRaisesRegex(ValueError, "documented reason"):
                store.requeue_failed(trial.trial_id, "  ")
            pending = store.requeue_failed(trial.trial_id, "documented deterministic mock timeout recovery")
            self.assertIs(pending.status, TrialStatus.PENDING)
            self.assertEqual(pending.explicit_requeue_count, 1)
            self.assertEqual(pending.last_failure_category, "timeout")
            self.assertEqual(store.claim(trial.trial_id).attempt_count, 2)

    def test_config_mismatch_is_rejected_instead_of_mixing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "phase1.sqlite3"
            CheckpointStore(path, CONFIG_HASH)
            with self.assertRaises(CheckpointConfigurationMismatch):
                CheckpointStore(path, "c" * 64)

            new_config_store = CheckpointStore(Path(temporary) / "new-config.sqlite3", "c" * 64)
            with self.assertRaises(CheckpointConfigurationMismatch):
                new_config_store.register_trials((identity("scenario-new-config"),))

    def test_code_revision_mismatch_is_rejected_instead_of_mixing_builds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "phase1.sqlite3"
            first_store = CheckpointStore(path, CONFIG_HASH)
            first_store.register_trials((identity("scenario-build-a", code_revision="abcdef0"),))
            resumed = CheckpointStore(path, CONFIG_HASH)
            with self.assertRaisesRegex(CheckpointConfigurationMismatch, "code revision"):
                resumed.register_trials((identity("scenario-build-b", code_revision="1234567"),))

    def test_state_transitions_and_duplicate_completion_are_guarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = CheckpointStore(Path(temporary) / "phase1.sqlite3", CONFIG_HASH)
            trial = identity("scenario-state")
            store.register_trials((trial,))
            with self.assertRaises(CheckpointConflict):
                store.complete(trial.trial_id, "trace#1")
            store.claim(trial.trial_id)
            store.complete(trial.trial_id, "trace#1")
            with self.assertRaises(CheckpointConflict):
                store.claim(trial.trial_id)
            with self.assertRaises(CheckpointConflict):
                store.complete(trial.trial_id, "trace#1")
            with self.assertRaises(CheckpointConflict):
                store.fail(trial.trial_id, FailureCategory.TIMEOUT)

    def test_bulk_registration_is_transactional_on_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = CheckpointStore(Path(temporary) / "phase1.sqlite3", CONFIG_HASH)
            valid = identity("scenario-valid")
            mismatched = identity("scenario-mismatch", config_sha256="c" * 64)
            with self.assertRaises(CheckpointConfigurationMismatch):
                store.register_trials((valid, mismatched))
            self.assertEqual(store.list_records(), ())
            self.assertEqual(store.events(), ())


if __name__ == "__main__":
    unittest.main()
