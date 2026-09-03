from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tests.scripts._bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.yan2023.feature_optimization import (
    YanFeatureFamilySpec,
    YanFeatureMathChoice,
    YanModelCandidate,
    YanOptimizationConfig,
    YanOptimizationSample,
    build_feature_subset_candidates,
    default_feature_pool,
    generate_candidate_blueprints,
    load_optimization_samples_from_csv,
)
from tests.harness.yan2023.slot_inventory import WORKING_FEATURE_SLOTS


class Yan2023FeatureOptimizationTests(unittest.TestCase):
    def test_default_feature_pool_excludes_blocked_features(self) -> None:
        pool = default_feature_pool()
        blocked_features = {
            slot.base_feature for slot in WORKING_FEATURE_SLOTS if slot.status == "blocked"
        }
        self.assertTrue(pool)
        self.assertFalse(set(pool) & blocked_features)
        self.assertIn("pitch_mean", pool)

    def test_candidate_blueprints_expand_feature_and_math_choices(self) -> None:
        samples = (
            YanOptimizationSample(
                sample_id="piece-1",
                score_path=Path("ignored.xml"),
                label="easy",
            ),
        )
        config = YanOptimizationConfig(
            samples=samples,
            feature_pool=("pitch_mean", "pitch_range"),
            required_features=("pitch_mean",),
            feature_subset_candidates=(
                ("pitch_mean",),
                ("pitch_mean", "pitch_range"),
            ),
            feature_family_specs=(
                YanFeatureFamilySpec(
                    base_feature="black_key_rate",
                    choices=(
                        YanFeatureMathChoice("written_note_ratio", {"black_key_rate_formula": "written_note_ratio"}),
                        YanFeatureMathChoice("logical_note_ratio", {"black_key_rate_formula": "logical_note_ratio"}),
                    ),
                ),
                YanFeatureFamilySpec(
                    base_feature="polyphony_rate",
                    choices=(
                        YanFeatureMathChoice("polyphonic_onset_ratio", {"polyphony_rate_formula": "polyphonic_onset_ratio"}),
                        YanFeatureMathChoice("polyphonic_note_ratio", {"polyphony_rate_formula": "polyphonic_note_ratio"}),
                    ),
                ),
            ),
            model_candidates=(YanModelCandidate("ridge_classifier", {"alpha": 1.0}, label="ridge"),),
        )

        candidates = generate_candidate_blueprints(config)
        self.assertEqual(len(candidates), 8)
        self.assertEqual(candidates[0].selected_features, ("pitch_mean",))
        self.assertEqual(candidates[-1].selected_features, ("pitch_mean", "pitch_range"))
        self.assertEqual(candidates[0].model_candidate.model_family, "ridge_classifier")

    def test_manifest_loader_resolves_relative_score_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manifest_path = tmp_path / "manifest.csv"
            score_path = tmp_path / "scores" / "piece-a.xml"
            score_path.parent.mkdir(parents=True, exist_ok=True)
            score_path.write_text("<score />")

            with manifest_path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["score_path", "label", "piece_id"])
                writer.writeheader()
                writer.writerow(
                    {
                        "score_path": "scores/piece-a.xml",
                        "label": "hard",
                        "piece_id": "piece-a",
                    }
                )

            samples = load_optimization_samples_from_csv(
                manifest_path,
                score_path_column="score_path",
                label_column="label",
                sample_id_column="piece_id",
            )

            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0].sample_id, "piece-a")
            self.assertEqual(samples[0].score_path, score_path.resolve())
            self.assertEqual(samples[0].label, "hard")

    def test_build_feature_subset_candidates_respects_required_features(self) -> None:
        candidates = build_feature_subset_candidates(
            ("a", "b", "c"),
            required_features=("required",),
            max_feature_count=2,
        )
        self.assertEqual(candidates, (("required",), ("required", "a"), ("required", "b"), ("required", "c")))


if __name__ == "__main__":
    unittest.main()
