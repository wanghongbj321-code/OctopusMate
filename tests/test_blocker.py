"""M1-03 blocker 模块单元测试：阻断识别（规则型 ≤ 阈值 + 语义型链路断裂）/ 排序 / 改进路径。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import blocker  # noqa: E402


class TestIdentifyBlockers(unittest.TestCase):
    """阻断性问题识别。"""

    def _scores(self):
        return {
            "V1": {"score": 3.5, "judgment": "战略承接清晰", "evidenceIds": ["E-01"]},
            "I1": {"score": 2.0, "judgment": "数据对象覆盖不全", "evidenceIds": ["E-02"]},
            "I2": {"score": 1.5, "judgment": "动销数据漏采", "evidenceIds": ["E-03"]},
            "T1": {"score": 3.0, "judgment": "架构规范", "evidenceIds": []},
        }

    def test_below_threshold_identified(self):
        # 阈值 2.0：I1(2.0) 与 I2(1.5) 均 ≤ 2.0 → 阻断
        blocks = blocker.identify_blockers(self._scores(), [], {"blockThreshold": 2.0})
        angles = {b["angle"] for b in blocks}
        self.assertEqual(angles, {"I1", "I2"})

    def test_default_threshold_2(self):
        blocks = blocker.identify_blockers(self._scores(), [])
        self.assertEqual({b["angle"] for b in blocks}, {"I1", "I2"})

    def test_custom_threshold(self):
        blocks = blocker.identify_blockers(self._scores(), [], {"blockThreshold": 3.0})
        # V1 3.5 不触发；T1 3.0 恰好等于阈值 → 触发
        self.assertEqual({b["angle"] for b in blocks}, {"I1", "I2", "T1"})

    def test_sorted_by_score_asc(self):
        blocks = blocker.identify_blockers(self._scores(), [], {"blockThreshold": 2.0})
        self.assertLessEqual(len(blocks), 2)
        # I2(1.5) 应在 I1(2.0) 之前（升序，低分优先）
        self.assertEqual(blocks[0]["angle"], "I2")
        self.assertEqual(blocks[1]["angle"], "I1")

    def test_semantic_blocks_merged(self):
        semantic = [{"angle": "T3", "issue": "DMS 无直连接口，链路断裂", "impact": "AI 场景无数据输入",
                     "evidenceIds": ["E-04"], "suggestion": "建设 DMS 直连接口"}]
        blocks = blocker.identify_blockers(self._scores(), [], {"blockThreshold": 2.0}, semantic_blocks=semantic)
        angles = {b["angle"] for b in blocks}
        self.assertEqual(angles, {"I1", "I2", "T3"})
        # 语义型无分排最后
        self.assertEqual(blocks[-1]["angle"], "T3")

    def test_no_blockers(self):
        scores = {"V1": {"score": 4.0, "judgment": "良好"}, "V2": {"score": 3.5, "judgment": "良好"}}
        self.assertEqual(blocker.identify_blockers(scores, [], {"blockThreshold": 2.0}), [])

    def test_ids_reassigned_after_sort(self):
        semantic = [{"angle": "T3", "issue": "链路断裂"}]
        blocks = blocker.identify_blockers(self._scores(), [], {"blockThreshold": 2.0}, semantic_blocks=semantic)
        ids = [b["id"] for b in blocks]
        self.assertEqual(ids, ["B-01", "B-02", "B-03"])


class TestBuildImprovementPath(unittest.TestCase):
    """改进路径：阻断性问题优先输入。"""

    def test_path_priority(self):
        blocks = [
            {"angle": "I2", "issue": "漏采", "suggestion": "建设移动采集"},
            {"angle": "I1", "issue": "覆盖不全", "suggestion": "补齐对象目录"},
        ]
        path = blocker.build_improvement_path(blocks)
        self.assertEqual(len(path), 2)
        self.assertEqual(path[0]["priority"], 1)
        self.assertEqual(path[0]["action"], "建设移动采集")
        # owner/timeline 留待顾问确认（AI 不替顾问拍板）
        self.assertEqual(path[0]["owner"], "")
        self.assertEqual(path[0]["timeline"], "")

    def test_empty(self):
        self.assertEqual(blocker.build_improvement_path([]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
