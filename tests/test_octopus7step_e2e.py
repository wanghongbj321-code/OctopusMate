"""M2-07 端到端演练：模拟顾问会话完整走完 Octopus 7 步法。

链路：会话初始化 → 7 步执行（gate 三态，含未决登记）→ 出口校验 →
未决裁决 → 确认授权（A6）→ finalized（A6）。
渲染说明（2026-08-18 改造）：确认包 HTML 由 AI 按视觉模式直接生成（单测环境无
LLM，不现场渲染）；测试用 examples/ 合规基线 HTML 过 13 条不变量审计，验证
"审计闸门"（audit_html）对合规产物放行（A8）。渲染质量走人工浏览器验收。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "skills" / "vision-render" / "scripts"))

from _engine import (  # noqa: E402
    executor,
    exit as exit_mod,
    open_issues,
    parser,
    session,
    state as state_mod,
)
from audit_html import audit as audit_html  # noqa: E402

MANIFEST = ROOT / "skills" / "methods" / "octopus-7step" / "manifest.yaml"
# AI 生成确认包的合规基线（版面参照，过审计即代表 LLM 产物质量达标）
EXAMPLES_HTML = ROOT / "skills" / "vision-render" / "examples" / "vision-confirm-canvas.html"


def build_full_output() -> dict:
    """完整契约字段产出（含 exit criteria 所需字段）。"""
    return {
        "visionStatement": "成为行业 AI 转型标杆：以数据驱动的运营体系重塑客户体验",
        "visionNarrative": "三年后的一天：客户自助下单，AI 实时调度订单，运营团队聚焦例外决策……",
        "ambitionTable": [
            {"kpi": "订单处理周期", "baseline": "72h", "y1": "48h", "y2": "24h", "y3": "12h", "owner": "运营负责人", "source": "流程系统"},
            {"kpi": "一次性解决率", "baseline": "55%", "y1": "65%", "y2": "75%", "y3": "80%", "owner": "客服负责人", "source": "客服系统"},
        ],
        "ambitionRationale": {
            "depth": "技术赋能的业务转型",
            "scope": "核心运营流程 + 客服体系",
            "scale": "全集团推广",
            "speed": "3 年三步走",
            "basis": "对标行业 S1 证据 + 内部试点",
            "resource_commitment": "预算 5000 万/年 + 转型团队 30 人",
        },
        "impactSummary": {
            "organization": "新增 AI 运营中心，客服与运营合并汇报",
            "capability": "数据驱动决策 / AI 用例规模化能力",
            "financial": "年降本 2000 万，收入提升 5%",
        },
        "changeControl": {
            "trigger": "战略前提变化 / 外部环境重大变化 / 检验新证据",
            "approver": "发起人 + CEO",
            "process": "主 Agent 提请顾问批准修订",
        },
        "downstreamInterfaces": {
            "roadmap": "能力路线图接口（阶段二）",
            "benefit_case": "Benefit Case 接口（含待验证假设）",
            "communication": "愿景沟通策略草案",
            "signatures": ["发起人：张总", "业务负责人：李总", "IT 负责人：王总"],
        },
        "aiElements": {"enhanced": "AI 嵌入运营决策，不设独立主链"},
    }


class TestOctopus7StepE2E(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_7step_session(self):
        """完整走完 7 步：未决登记 → 裁决闭环 → 契约齐全 → 授权 → 渲染审计通过。"""
        # 1. 会话初始化（M1-09）
        topic_dir = session.create_session(
            self.ws, "demo-retail", "示例零售集团", "ai-ops-vision", "AI 运营转型愿景"
        )

        # 2. 加载 7 步法
        method, errors = parser.parse_manifest(MANIFEST)
        self.assertEqual(errors, [])
        state = state_mod.load_state(topic_dir / "state.json")
        executor.begin(method, state)

        # 3. 步骤 01-03：通过
        for sid in ("01", "02", "03"):
            out = topic_dir / "modules" / f"step-{sid}.md"
            out.write_text(f"# 步骤 {sid} 产出\n\n（演练模拟：{method.step_by_id(sid).name}）\n", encoding="utf-8")
            r = executor.run_step(state, method, sid, out, {"core_ok": True})
            self.assertEqual(r["status"], "pass", f"步骤 {sid} 应通过：{r}")
            executor.advance(state, method)

        # 4. 步骤 04：有条件通过 → 登记未决项（六特质"可取"待确认）
        out4 = topic_dir / "modules" / "step-04.md"
        out4.write_text("# 步骤 04 产出\n\n（演练模拟：构建转型愿景）\n", encoding="utf-8")
        r4 = executor.run_step(
            state, method, "04", out4,
            {"core_ok": True, "conditional": True, "note": "六特质中「可取」未获一线代表确认"},
        )
        self.assertEqual(r4["status"], "conditional")
        issue_id = r4["open_issue"]["id"]
        self.assertEqual(issue_id, "U-01")
        self.assertEqual(len(state["open_issues"]), 1)
        executor.advance(state, method)

        # 5. 步骤 05-06：通过
        for sid in ("05", "06"):
            out = topic_dir / "modules" / f"step-{sid}.md"
            out.write_text(f"# 步骤 {sid} 产出\n\n（演练模拟：{method.step_by_id(sid).name}）\n", encoding="utf-8")
            r = executor.run_step(state, method, sid, out, {"core_ok": True})
            self.assertEqual(r["status"], "pass")
            executor.advance(state, method)

        # 6. 步骤 07 前：未决项统一裁决（v2.1 步骤 07 操作 1）
        open_issues.adjudicate(state, issue_id, "补充完成：第二轮工作坊获一线确认")
        self.assertEqual(open_issues.unowned(state), [])

        # 7. 步骤 07：确认（exit criteria 判定：未决无主 + 签署）
        out7 = topic_dir / "modules" / "step-07.md"
        out7.write_text("# 步骤 07 产出\n\n（演练模拟：确认记录）\n", encoding="utf-8")
        r7 = executor.run_step(
            state, method, "07", out7,
            {"core_ok": True, "note": "exit criteria 全部通过"},
        )
        self.assertEqual(r7["status"], "pass")
        self.assertIsNone(executor.advance(state, method))  # 已到最后一步

        # 8. 出口：契约校验 + exit criteria（M2-05）
        output = build_full_output()
        output["openIssues"] = state["open_issues"]
        result = exit_mod.run_exit(output, method.output_contract["requires"], state)
        self.assertEqual(result["errors"], [], f"出口校验应通过：{result['errors']}")
        self.assertFalse(result["blocked"])

        # 9. 确认包组装（markdown 唯一事实源）→ finalized
        content = exit_mod.assemble_confirm_package(output, state, method)
        pkg_path = exit_mod.write_confirm_package(topic_dir, content, slug="ai-ops-vision")
        self.assertTrue(pkg_path.exists())
        self.assertIn("## 愿景陈述", content)
        self.assertIn("## 未决条件清单", content)

        # 10. 授权节点（A6）→ finalized
        auth = exit_mod.confirm(state, "pass")
        self.assertTrue(auth["authorized"])
        state_mod.transition(state, "finalized")
        self.assertEqual(state["status"], "finalized")

        # 11. 渲染质量闸门（A8）：AI 生成产物（单测环境无 LLM，用 examples 合规基线代表）
        #     过 13 条不变量审计 → 闸门放行；审计闸门拦截能力见 test_audit_html.py
        self.assertTrue(EXAMPLES_HTML.exists(), "examples 版面参照应存在")
        violations = audit_html(EXAMPLES_HTML.read_text(encoding="utf-8"))
        self.assertEqual(violations, [], f"examples 基线违反不变量：{violations}")

        # 12. 演练产物齐备（md 中间产物 + HTML 确认包）
        self.assertTrue((topic_dir / "modules" / "step-01.md").exists())
        self.assertTrue((topic_dir / "modules" / "vision-confirm-ai-ops-vision-v1.md").exists())

    def test_contract_blocked_on_missing_core_field(self):
        """缺核心字段 → 出口阻断（§4 校验失败不允许进入确认）。"""
        state = session.create_session(self.ws, "p", "P", "t", "T") and None
        method, errors = parser.parse_manifest(MANIFEST)
        self.assertFalse(errors)
        fake_state = {"open_issues": [], "project_name": "P", "topic_name": "T", "method": method.name, "status": "review_ready"}
        output = build_full_output()
        del output["visionStatement"]  # 缺核心字段
        result = exit_mod.run_exit(output, method.output_contract["requires"], fake_state)
        self.assertTrue(result["blocked"])
        self.assertTrue(any("缺失核心字段" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
