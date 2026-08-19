"""M1-01 scoring 模块单元测试：步进校验 / 维度分 / 总体分 / 一站式统计。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import scoring  # noqa: E402

SCALE = {"min": 1, "max": 5, "step": 0.5}

# 维度锚点：V 维 V1/V2，I 维 I1/I2
ANCHORS = {
    "V": {"V1": {1: "x", 2: "x", 3: "x", 4: "x", 5: "x"}, "V2": {1: "x", 2: "x", 3: "x", 4: "x", 5: "x"}},
    "I": {"I1": {1: "x", 2: "x", 3: "x", 4: "x", 5: "x"}, "I2": {1: "x", 2: "x", 3: "x", 4: "x", 5: "x"}},
}


class TestValidateScore(unittest.TestCase):
    """步进校验：范围 + 0.5 步进。"""

    def test_valid_scores(self):
        for v in (1.0, 2.5, 3.5, 5.0, 1, 3):
            self.assertEqual(scoring.validate_score(v, SCALE), [])

    def test_out_of_range(self):
        errs = scoring.validate_score(0.5, SCALE)
        self.assertTrue(any("超出范围" in e for e in errs))
        errs = scoring.validate_score(5.5, SCALE)
        self.assertTrue(any("超出范围" in e for e in errs))

    def test_bad_step(self):
        errs = scoring.validate_score(2.2, SCALE)
        self.assertTrue(any("步进" in e for e in errs))

    def test_non_numeric(self):
        errs = scoring.validate_score("3", SCALE)
        self.assertTrue(errs)

    def test_invalid_scale(self):
        errs = scoring.validate_score(3, {})
        self.assertTrue(errs)


class TestDimensionsFromAnchors(unittest.TestCase):
    """从 anchors 推导维度分组。"""

    def test_derive(self):
        dims = scoring.dimensions_from_anchors(ANCHORS)
        self.assertEqual(dims["V"], ["V1", "V2"])
        self.assertEqual(dims["I"], ["I1", "I2"])

    def test_empty(self):
        self.assertEqual(scoring.dimensions_from_anchors({}), {})
        self.assertEqual(scoring.dimensions_from_anchors(None), {})


class TestComputeScores(unittest.TestCase):
    """维度分 / 总体分统计。"""

    def test_dimension_average_1dp(self):
        # V: (3.5+4.0)/2 = 3.75 → 3.8；I: (2.0+2.5)/2 = 2.25 → 2.2
        scores = {"V1": {"score": 3.5}, "V2": {"score": 4.0}, "I1": {"score": 2.0}, "I2": {"score": 2.5}}
        dims = scoring.compute_dimension_scores(scores, {"V": ["V1", "V2"], "I": ["I1", "I2"]})
        self.assertEqual(dims["V"], 3.8)
        self.assertEqual(dims["I"], 2.2)

    def test_unscored_angle_excluded(self):
        # I2 未打分 → I 维只计 I1（2.0）；V 全打分
        scores = {"V1": {"score": 3.5}, "V2": {"score": 4.0}, "I1": {"score": 2.0}}
        dims = scoring.compute_dimension_scores(scores, {"V": ["V1", "V2"], "I": ["I1", "I2"]})
        self.assertEqual(dims["I"], 2.0)
        self.assertNotIn("I", {})  # I 存在
        self.assertEqual(dims["I"], 2.0)

    def test_dimension_all_unscored_excluded(self):
        scores = {"V1": {"score": 3.5}}
        dims = scoring.compute_dimension_scores(scores, {"V": ["V1", "V2"], "I": ["I1", "I2"]})
        self.assertEqual(dims["V"], 3.5)
        self.assertNotIn("I", dims)

    def test_overall_average_1dp(self):
        # (3.8 + 2.2) / 2 = 3.0
        self.assertEqual(scoring.compute_overall_score({"V": 3.8, "I": 2.2}), 3.0)
        # (3.4 + 2.1 + 2.7 + 2.9 + 3.4) / 5 = 2.9（对齐 Demo 快消分销样例）
        self.assertEqual(
            scoring.compute_overall_score({"V": 3.4, "I": 2.1, "T": 2.7, "A": 2.9, "L": 3.4}),
            2.9,
        )

    def test_overall_none_when_empty(self):
        self.assertIsNone(scoring.compute_overall_score({}))


class TestComputeAll(unittest.TestCase):
    """一站式统计：步进校验 + 维度分 + 总体分。"""

    def test_full_pipeline(self):
        scores = {"V1": {"score": 3.5}, "V2": {"score": 4.0}, "I1": {"score": 1.5}, "I2": {"score": 2.5}}
        result = scoring.compute_all(scores, {"scale": SCALE, "blockThreshold": 2.0, "anchors": ANCHORS})
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["dimension_scores"]["V"], 3.8)
        self.assertEqual(result["dimension_scores"]["I"], 2.0)
        self.assertEqual(result["overall_score"], 2.9)

    def test_bad_step_excluded_with_error(self):
        scores = {"V1": {"score": 3.3}, "V2": {"score": 4.0}}
        result = scoring.compute_all(scores, {"scale": SCALE, "anchors": ANCHORS})
        self.assertTrue(any("V1" in e for e in result["errors"]))
        # 违规角度剔除出统计：V 维只计 V2（4.0）
        self.assertEqual(result["dimension_scores"]["V"], 4.0)

    def test_missing_scale_blocked(self):
        result = scoring.compute_all({"V1": {"score": 3.0}}, {})
        self.assertTrue(any("scale" in e for e in result["errors"]))
        self.assertIsNone(result["overall_score"])

    def test_empty_scores(self):
        result = scoring.compute_all({}, {"scale": SCALE, "anchors": ANCHORS})
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["dimension_scores"], {})
        self.assertIsNone(result["overall_score"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
