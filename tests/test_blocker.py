"""M1-03 blocker 模块单元测试：阻断识别（仅语义型链路断裂/能力缺口）/ 编号 / 改进路径。

注意：硬阈值规则（角度 ≤ blockThreshold 触发阻断）已于 v0.3.1 清除；
阻断识别完全来自语义型核验，不再基于任何角度打分阈值。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import blocker  # noqa: E402


class TestIdentifyBlockers(unittest.TestCase):
    """阻断性问题识别（仅语义型）。"""

    def _scores(self):
        # 低分角度（如 I1/I2）不再自动触发阻断——仅作上下文
        return {
            "V1": {"score": 3.5, "judgment": "战略承接清晰", "evidenceIds": ["E-01"]},
            "I1": {"score": 2.0, "judgment": "数据对象覆盖不全", "evidenceIds": ["E-02"]},
            "I2": {"score": 1.5, "judgment": "动销数据漏采", "evidenceIds": ["E-03"]},
            "T1": {"score": 3.0, "judgment": "架构规范", "evidenceIds": []},
        }

    def test_low_score_not_blocking(self):
        # 角度低分（I1=2.0 / I2=1.5）不再触发阻断（硬阈值规则已清除）
        blocks = blocker.identify_blockers(self._scores(), [])
        self.assertEqual(blocks, [])

    def test_semantic_blocks_merged(self):
        semantic = [{"angle": "T3", "issue": "DMS 无直连接口，链路断裂", "impact": "AI 场景无数据输入",
                     "evidenceIds": ["E-04"], "suggestion": "建设 DMS 直连接口"}]
        blocks = blocker.identify_blockers(self._scores(), [], semantic_blocks=semantic)
        self.assertEqual({b["angle"] for b in blocks}, {"T3"})
        self.assertEqual(blocks[0]["issue"], "DMS 无直连接口，链路断裂")

    def test_no_blockers(self):
        scores = {"V1": {"score": 4.0, "judgment": "良好"}, "V2": {"score": 3.5, "judgment": "良好"}}
        self.assertEqual(blocker.identify_blockers(scores, []), [])

    def test_ids_assigned_in_order(self):
        semantic = [
            {"angle": "T3", "issue": "链路断裂 A"},
            {"angle": "I4", "issue": "能力缺口 B"},
        ]
        blocks = blocker.identify_blockers(self._scores(), [], semantic_blocks=semantic)
        ids = [b["id"] for b in blocks]
        self.assertEqual(ids, ["B-01", "B-02"])
        self.assertEqual([b["angle"] for b in blocks], ["T3", "I4"])

    def test_empty_semantic_none(self):
        blocks = blocker.identify_blockers(self._scores(), [], semantic_blocks=None)
        self.assertEqual(blocks, [])


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
