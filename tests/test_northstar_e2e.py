"""M3-05 端到端演练：模拟半天工作坊走通北极星指标法 4 步路径。

验证：4 步执行 + 平台出口（复用 engine/exit.py）+ 契约满足规则（P1-6：
简化填充、字段集合与 7 步法一致）+ 渲染审计（A1/A3/A8 北极星部分）。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "vision-distill" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "vision-render" / "scripts"))

from engine import (  # noqa: E402
    executor,
    exit as exit_mod,
    open_issues,
    parser,
    session,
    state as state_mod,
)
from audit_html import audit as audit_html  # noqa: E402
from render_confirm import render as render_html  # noqa: E402

NORTH_STAR = ROOT / "skills" / "methods" / "north-star" / "manifest.yaml"
OCTOPUS7 = ROOT / "skills" / "methods" / "octopus-7step" / "manifest.yaml"


def build_simplified_output(open_issues: list[dict] | None = None) -> dict:
    """简化版契约产出（P1-6：填充深度允许简化）。"""
    output = {
        "visionStatement": "成为客户最信赖的智能供应链伙伴",
        "visionNarrative": "未来新闻稿：订单一次通过率 90%，客户自助下单……（半天工作坊产出）",
        "ambitionTable": [
            {"kpi": "订单一次通过率", "baseline": "62%", "y1": "72%", "y2": "82%", "y3": "90%", "owner": "运营负责人", "source": "订单系统"}
        ],
        "ambitionRationale": {"depth": "业务转型", "scope": "订单履约", "scale": "核心大客户", "speed": "3 年", "basis": "北极星指标轨迹", "resource_commitment": "预算 3000 万/年 + 转型团队 15 人"},
        "impactSummary": {"organization": "运营中心重构", "capability": "数据驱动运营", "financial": "年降本 1500 万"},
        "downstreamInterfaces": {"roadmap": "能力路线图接口", "signatures": ["发起人：张总"]},
    }
    if open_issues is not None:
        output["openIssues"] = open_issues
    return output


class TestNorthStarE2E(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_contract_structure_identical_to_7step(self):
        """P1-6：字段集合与 7 步法一致（结构完全一致 = 字段集合相同）。"""
        ns, e1 = parser.parse_manifest(NORTH_STAR)
        oc, e2 = parser.parse_manifest(OCTOPUS7)
        self.assertEqual(e1, [])
        self.assertEqual(e2, [])
        self.assertEqual(
            set(ns.output_contract["requires"]),
            set(oc.output_contract["requires"]),
            "requires 字段集合必须与 7 步法一致",
        )
        self.assertEqual(
            set(ns.output_contract["optional"]),
            set(oc.output_contract["optional"]),
        )

    def test_full_4step_workshop(self):
        """完整走通 4 步 + 出口 + 渲染审计（A1/A3/A8 北极星部分）。"""
        topic_dir = session.create_session(
            self.ws, "demo-supply", "示例供应链集团", "north-star-vision", "供应链转型愿景"
        )
        method, errors = parser.parse_manifest(NORTH_STAR)
        self.assertEqual(errors, [])
        state = state_mod.load_state(topic_dir / "state.json")
        executor.begin(method, state)

        # 步骤 01：通过
        out1 = topic_dir / "modules" / "ns-01.md"
        out1.write_text("# 步骤 01 产出（痛点）\n", encoding="utf-8")
        r1 = executor.run_step(state, method, "01", out1, {"core_ok": True})
        self.assertEqual(r1["status"], "pass")
        executor.advance(state, method)

        # 步骤 02：有条件通过 → 登记未决项（北极星指标责任方未定）
        out2 = topic_dir / "modules" / "ns-02.md"
        out2.write_text("# 步骤 02 产出（北极星指标）\n", encoding="utf-8")
        r2 = executor.run_step(
            state, method, "02", out2,
            {"core_ok": True, "conditional": True, "note": "北极星指标责任方暂未指定"},
        )
        self.assertEqual(r2["status"], "conditional")
        self.assertEqual(r2["open_issue"]["id"], "U-01")
        executor.advance(state, method)

        # 步骤 03：通过
        out3 = topic_dir / "modules" / "ns-03.md"
        out3.write_text("# 步骤 03 产出（未来新闻稿）\n", encoding="utf-8")
        r3 = executor.run_step(state, method, "03", out3, {"core_ok": True})
        self.assertEqual(r3["status"], "pass")
        executor.advance(state, method)

        # 步骤 04 前：未决项裁决（半天工作坊内完成）
        open_issues.adjudicate(state, "U-01", "降级为假设：责任方在路线图阶段指定")
        # 降级 → 出口契约 validationPlan 条件必填
        output = build_simplified_output(open_issues=state["open_issues"])
        output["validationPlan"] = [
            {"assumption": "责任方指定", "method": "路线图阶段", "owner": "发起人", "timepoint": "阶段二", "passCriteria": "责任方任命"}
        ]

        # 步骤 04：六特质自检（核心项通过）
        out4 = topic_dir / "modules" / "ns-04.md"
        out4.write_text("# 步骤 04 产出（六特质自检）\n", encoding="utf-8")
        r4 = executor.run_step(state, method, "04", out4, {"core_ok": True})
        self.assertEqual(r4["status"], "pass")
        self.assertIsNone(executor.advance(state, method))  # 4 步完成

        # 出口：契约校验（简化满足规则）+ exit criteria
        result = exit_mod.run_exit(output, method.output_contract["requires"], state)
        self.assertEqual(result["errors"], [], f"出口校验应通过：{result['errors']}")

        # 确认包 + 渲染 + 审计（复用 M2-06 链路）
        content = exit_mod.assemble_confirm_package(output, state, method)
        pkg = exit_mod.write_confirm_package(topic_dir, content, slug="north-star-vision")
        html_path = topic_dir / "output" / "vision-confirm-north-star-vision-v1.html"
        render_html(pkg, html_path)
        violations = audit_html(html_path.read_text(encoding="utf-8"))
        self.assertEqual(violations, [], f"HTML 违反不变量：{violations}")

        # 授权 → finalized
        self.assertTrue(exit_mod.confirm(state, "pass")["authorized"])
        state_mod.transition(state, "finalized")
        self.assertEqual(state["status"], "finalized")

    def test_simplified_ambition_table_single_row(self):
        """P1-6：ambitionTable 仅 1 项（单一北极星指标）即可通过校验。"""
        output = build_simplified_output(open_issues=[])
        self.assertEqual(len(output["ambitionTable"]), 1)
        from engine.contract import validate_output

        self.assertEqual(validate_output(output, ["visionStatement", "ambitionTable", "ambitionRationale", "impactSummary"], []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
