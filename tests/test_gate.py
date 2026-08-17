"""M1-04 三态 gate 判定器单元测试（三态 + 回指语义基础）。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "vision-distill" / "scripts"))

from engine.gate import GATE_CONDITIONAL, GATE_PASS, GATE_REGRESS, judge_gate  # noqa: E402

GATE_CONF = {
    "coreCheck": "愿景可想象且可沟通",
    "pass": "愿景清晰",
    "conditional": "细节待补充，登记未决项",
}


class TestGateJudge(unittest.TestCase):
    def test_no_gate_passes(self):
        """无 gate 定义 → 直接通过。"""
        result = judge_gate(None)
        self.assertEqual(result.status, GATE_PASS)

    def test_pass(self):
        result = judge_gate(GATE_CONF, {"core_ok": True, "conditional": False})
        self.assertEqual(result.status, GATE_PASS)

    def test_conditional_registers_open_issue(self):
        """非核心项未满足 → 有条件通过，返回待登记未决项。"""
        result = judge_gate(
            GATE_CONF,
            {"core_ok": True, "conditional": True, "note": "六特质中的可取性待确认"},
        )
        self.assertEqual(result.status, GATE_CONDITIONAL)
        self.assertIsNotNone(result.open_issue)
        self.assertEqual(result.open_issue["content"], "六特质中的可取性待确认")

    def test_core_failure_regresses_even_with_conditional(self):
        """核心判定项失败 → 回指；即使同时 conditional 也不得绕过（v2.1 §2.3 规则 1）。"""
        result = judge_gate(
            GATE_CONF,
            {"core_ok": False, "conditional": True, "note": "愿景不可想象"},
        )
        self.assertEqual(result.status, GATE_REGRESS)
        self.assertIsNone(result.open_issue)


if __name__ == "__main__":
    unittest.main(verbosity=2)
