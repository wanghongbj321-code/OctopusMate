"""M1-08 引擎全链路验证（mock 2 步法）：

执行 → gate（三态）→ 未决登记 → 出口校验 → 裁决闭环。
同时覆盖回指语义（M1-03）与状态机流转（authorized 授权约束）。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "vision-distill" / "scripts"))

from engine import contract, executor, open_issues, parser, state as state_mod  # noqa: E402

MOCK_MANIFEST = ROOT / "tests" / "fixtures" / "mock-method" / "manifest.yaml"


def make_state(tmp: Path) -> tuple[dict, object]:
    method, errors = parser.parse_manifest(MOCK_MANIFEST)
    assert not errors, errors
    state = state_mod.new_state("mock-proj", "Mock 项目", "mock-topic", "Mock Topic")
    executor.begin(method, state)
    return state, method


class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _full_output(self) -> dict:
        return {
            "visionStatement": "成为行业 AI 转型标杆",
            "visionNarrative": "一页叙事稿……",
            "ambitionTable": [
                {"kpi": "订单处理周期", "baseline": "72h", "y1": "48h", "y2": "24h", "y3": "12h", "owner": "运营负责人", "source": "流程系统"}
            ],
            "ambitionRationale": {"depth": "业务转型", "scope": "核心流程", "scale": "全集团", "speed": "3 年", "basis": "对标数据"},
            "impactSummary": {"organization": "新增 AI 运营中心", "capability": "数据驱动决策", "financial": "年降本 2000 万"},
        }

    def test_full_pass_pipeline(self):
        """场景 A：两步全通过，出口校验通过，无未决项，状态机可流转到 finalized。"""
        state, method = make_state(self.tmp)

        # 步骤 01：通过
        r1 = executor.run_step(state, method, "01", self.tmp / "step01.md", {"core_ok": True})
        self.assertEqual(r1["status"], "pass")
        nxt = executor.advance(state, method)
        self.assertEqual(nxt, "02")

        # 步骤 02：通过
        r2 = executor.run_step(state, method, "02", self.tmp / "step02.md", {"core_ok": True})
        self.assertEqual(r2["status"], "pass")
        self.assertIsNone(executor.advance(state, method))  # 已到最后一步

        # 出口校验：核心字段齐全 + 无降级项 → 通过
        output = self._full_output()
        errors = contract.validate_output(output, method.output_contract["requires"], state["open_issues"])
        self.assertEqual(errors, [])

        # 状态机：review_ready → authorized（须授权）→ finalized
        with self.assertRaises(ValueError):
            state_mod.transition(state, "authorized")  # 未授权写入被拒
        state_mod.transition(state, "authorized", authorized=True)
        state_mod.transition(state, "finalized")
        self.assertEqual(state["status"], "finalized")

    def test_conditional_then_adjudicate(self):
        """场景 B：步骤 01 有条件通过登记未决项 → 出口校验时无主项被阻断 → 裁决后通过。"""
        state, method = make_state(self.tmp)

        r1 = executor.run_step(
            state, method, "01", self.tmp / "step01.md",
            {"core_ok": True, "conditional": True, "note": "量化基线数据缺失"},
        )
        self.assertEqual(r1["status"], "conditional")
        self.assertEqual(len(state["open_issues"]), 1)
        issue_id = r1["open_issue"]["id"]
        self.assertEqual(issue_id, "U-01")

        executor.run_step(state, method, "02", self.tmp / "step02.md", {"core_ok": True})

        # 未裁决 → 无主项，出口校验阻断
        self.assertEqual(len(open_issues.unowned(state)), 1)
        output = self._full_output()
        output["openIssues"] = state["open_issues"]
        errors = contract.validate_output(output, method.output_contract["requires"], state["open_issues"])
        self.assertTrue(any("未裁决" in e for e in errors))

        # 裁决（补充回答）→ 闭环
        open_issues.adjudicate(state, issue_id, "补充完成：已获取对标数据")
        self.assertEqual(open_issues.unowned(state), [])
        errors = contract.validate_output(output, method.output_contract["requires"], state["open_issues"])
        self.assertEqual(errors, [])

    def test_downgrade_requires_validation_plan(self):
        """场景 B2：降级为假设 → validationPlan 条件必填（M1-06）。"""
        state, method = make_state(self.tmp)
        issue = open_issues.register(
            state, "01", "第三年 KPI 暂无法量化", "evidence_missing", "downgrade"
        )
        open_issues.adjudicate(state, issue["id"], "降级为假设：影响价值轨迹精度")

        output = self._full_output()
        output["openIssues"] = state["open_issues"]
        # 无 validationPlan → 阻断
        errors = contract.validate_output(output, method.output_contract["requires"], state["open_issues"])
        self.assertTrue(any("validationPlan" in e for e in errors))
        # 补 validationPlan → 通过
        output["validationPlan"] = [
            {"assumption": "第三年 KPI", "method": "试点", "owner": "运营", "timepoint": "确认后 90 天", "passCriteria": "可量化"}
        ]
        errors = contract.validate_output(output, method.output_contract["requires"], state["open_issues"])
        self.assertEqual(errors, [])

    def test_regress_semantics(self):
        """场景 C：步骤 02 核心判定项失败 → 回指 01 重走（草稿保留 + 留痕），重走完成后推进。"""
        state, method = make_state(self.tmp)

        executor.run_step(state, method, "01", self.tmp / "step01.md", {"core_ok": True})
        executor.advance(state, method)
        r2 = executor.run_step(
            state, method, "02", self.tmp / "step02-v1.md",
            {"core_ok": False, "note": "愿景不可想象，需要回到问题界定重审"},
        )
        self.assertEqual(r2["status"], "regress")

        # 回指到步骤 01：草稿保留 + 留痕
        executor.regress_to(state, method, "01", r2["reason"])
        self.assertEqual(state["current_step"], "01")
        step01 = state["steps"]["01"]
        self.assertEqual(step01["status"], "draft")  # 草稿保留（output_path 不清空）
        self.assertEqual(step01["output_path"], str(self.tmp / "step01.md"))
        self.assertEqual(step01["regress_count"], 1)
        self.assertIn("不可想象", step01["regress_reasons"][0])
        step02 = state["steps"]["02"]
        self.assertEqual(step02["status"], "draft")

        # 重走 01 → 02 通过
        executor.run_step(state, method, "01", self.tmp / "step01-v2.md", {"core_ok": True})
        executor.advance(state, method)
        r2b = executor.run_step(state, method, "02", self.tmp / "step02-v2.md", {"core_ok": True})
        self.assertEqual(r2b["status"], "pass")
        self.assertIsNone(executor.advance(state, method))

    def test_invalid_regress_rejected(self):
        """回指到未执行的后续步骤被拒绝（线性回溯约束）。"""
        state, method = make_state(self.tmp)
        with self.assertRaises(executor.ExecutionError):
            executor.regress_to(state, method, "02", "非法回指")

    def test_illegal_state_transition_rejected(self):
        """状态机非法迁移被拒（review_ready 直接跳 finalized）。"""
        state, _ = make_state(self.tmp)
        with self.assertRaises(ValueError):
            state_mod.transition(state, "finalized", authorized=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
