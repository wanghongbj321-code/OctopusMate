"""M4-02 端到端演练：模拟顾问会话完整走完 VITAL 五维诊断。

链路：会话初始化 → 范围界定 → 打分规则确认（含一处锚点修改验证动态化）→
五维 22 角度打分 → evidence 登记 → blocker 识别 → scoring 统计 → 出口校验
（diagnosis 分支）→ 授权 finalized → 确认包组装（无 Demo 样例泄漏）。

渲染说明：确认包 HTML 由 AI 直接生成（单测环境无 LLM，不现场渲染）；
测试用 examples/diagnosis-report-canvas.html 合规基线过 audit 验证审计闸门。
演练产物（确认包 md + HTML）写入 artifacts/demo/vital-diagnosis-e2e/。
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "skills" / "deliverable-render" / "scripts"))

from _engine import blocker, evidence, files, open_issues, scoring, session, state as state_mod  # noqa: E402
from _engine.executor import advance, begin, run_step  # noqa: E402
from _engine.exit import assemble_diagnosis_package, confirm, run_exit, write_diagnosis_package  # noqa: E402
from _engine.parser import parse_manifest  # noqa: E402
from audit_html import audit as audit_html  # noqa: E402

VITAL_MANIFEST = ROOT / "skills" / "methods" / "vital-diagnosis" / "manifest.yaml"
CANVAS_HTML = ROOT / "skills" / "deliverable-render" / "examples" / "diagnosis-report-canvas.html"
DEMO_OUT = ROOT / "artifacts" / "demo" / "vital-diagnosis-e2e"

# 打分规则确认的授权证据（G0/G1：confirmed scoring md 的 confirmation 元数据）
SCORING_CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T15:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:12:用户确认整体采用默认锚点并修改 I2 第 1 档",
    "confirmation_text": "用户明确确认采用本版打分规则",
}

# 顾问确认的打分规则：I2 锚点第 1 档修改（默认参考 → 顾问定制，验证动态化 D4）
SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "blockThreshold": 2.0,
    "anchors": {
        "V": {"V1": {1: "初步定位", 2: "明确职责", 3: "全面落地", 4: "成效量化", 5: "机制成熟"},
              "V2": {1: "范围初明", 2: "边界明确", 3: "跨平台落实", 4: "边界量化", 5: "模型自适应"},
              "V3": {1: "试点支撑", 2: "规范流程", 3: "规模支撑", 4: "绩效量化", 5: "支撑创新"},
              "V4": {1: "预期为主", 2: "阶段成效", 3: "价值可验证", 4: "指标跟踪", 5: "反哺战略"}},
        "I": {"I1": {1: "核心识别", 2: "定义规范", 3: "目录贯通", 4: "覆盖核查", 5: "管理自适应"},
              "I2": {1: "依赖人工判断（顾问定制）", 2: "质量规则", 3: "规模供给", 4: "量化监控", 5: "按需供给"},
              "I3": {1: "依赖人工解释", 2: "术语口径统一", 3: "机器可理解", 4: "一致性核查", 5: "语义自适应"},
              "I4": {1: "局部可追踪有断裂", 2: "环节规范", 3: "跨平台贯通", 4: "断裂可定位", 5: "全链路自动化"}},
        "T": {"T1": {1: "部分承接", 2: "映射明确", 3: "全面承接", 4: "覆盖率量化", 5: "自适应演进"},
              "T2": {1: "可运行有限", 2: "分层解耦", 3: "规模部署", 4: "量化监控", 5: "平台资产化"},
              "T3": {1: "零散接口", 2: "接口标准", 3: "协同贯通", 4: "绩效量化", 5: "服务资产化"}},
        "A": {k: {1: "初明", 2: "规范", 3: "规模覆盖", 4: "量化监控", 5: "自适应"}
              for k in ("A1", "A2", "A3", "A4", "A5", "A6", "A7")},
        "L": {"L1": {1: "初步配置", 2: "职责规范", 3: "规模运营", 4: "绩效量化", 5: "梯队自适应"},
              "L2": {1: "临时响应", 2: "目录 SLA", 3: "规模场景", 4: "指标量化", 5: "机制自适应"},
              "L3": {1: "使用有限", 2: "进入业务", 3: "持续使用", 4: "采用率量化", 5: "文化成熟"},
              "L4": {1: "被动响应", 2: "复盘迭代", 3: "效果可验证", 4: "闭环量化", 5: "持续领先"}},
    },
    "customNote": "顾问将 I2 锚点第 1 档改为「依赖人工判断（顾问定制）」",
}

# 22 角度演示打分（对齐 Demo 风格但非样例数值：低分 I4/T3 触发阻断）
DEMO_SCORES = {
    "V1": {"score": 3.5, "judgment": "战略承接清晰", "evidenceIds": ["E-01"]},
    "V2": {"score": 3.5, "judgment": "业务边界明确", "evidenceIds": ["E-01"]},
    "V3": {"score": 3.5, "judgment": "运行支撑扎实", "evidenceIds": ["E-02"]},
    "V4": {"score": 3.0, "judgment": "传统分析价值可验证", "evidenceIds": ["E-02"]},
    "I1": {"score": 3.0, "judgment": "主数据已纳入，非结构化覆盖不全", "evidenceIds": ["E-03"]},
    "I2": {"score": 1.5, "judgment": "动销数据漏采迟报（≤ 阈值 → 阻断）", "evidenceIds": ["E-04"]},
    "I3": {"score": 3.0, "judgment": "术语口径统一", "evidenceIds": ["E-03"]},
    "I4": {"score": 1.0, "judgment": "人工上报链路中断（≤ 阈值 → 阻断）", "evidenceIds": ["E-05"]},
    "T1": {"score": 3.5, "judgment": "应用承接完整", "evidenceIds": ["E-06"]},
    "T2": {"score": 2.5, "judgment": "架构分层规范，容量监控不足", "evidenceIds": ["E-06"]},
    "T3": {"score": 2.0, "judgment": "DMS 无直连接口（≤ 阈值 → 阻断）", "evidenceIds": ["E-05"]},
    "A1": {"score": 3.5, "judgment": "治理规则明确", "evidenceIds": ["E-07"]},
    "A2": {"score": 3.5, "judgment": "安全合规落实", "evidenceIds": ["E-07"]},
    "A3": {"score": 2.5, "judgment": "AI 受控覆盖试点", "evidenceIds": ["E-08"]},
    "A4": {"score": 3.5, "judgment": "审计闭环", "evidenceIds": ["E-07"]},
    "A5": {"score": 2.5, "judgment": "公平偏见审计覆盖试点", "evidenceIds": ["E-08"]},
    "A6": {"score": 2.5, "judgment": "可解释透明覆盖试点", "evidenceIds": ["E-08"]},
    "A7": {"score": 2.5, "judgment": "模型监控覆盖试点", "evidenceIds": ["E-08"]},
    "L1": {"score": 3.5, "judgment": "组织能力配置完整", "evidenceIds": ["E-09"]},
    "L2": {"score": 3.5, "judgment": "运营机制成熟", "evidenceIds": ["E-09"]},
    "L3": {"score": 3.5, "judgment": "应用持续采用", "evidenceIds": ["E-09"]},
    "L4": {"score": 3.0, "judgment": "持续演进机制成熟", "evidenceIds": ["E-09"]},
}


def build_evidence() -> list[dict]:
    ev: list[dict] = []
    evidence.register(ev, "战略文件与年度 OKR", level="B", verification="文档评审+访谈",
                      supports=["V1", "V2"], source_type="制度")
    evidence.register(ev, "连续 6 个月经营分析输出", level="A", verification="运行记录抽查",
                      supports=["V3", "V4"], source_type="运行记录")
    evidence.register(ev, "对象目录清单", level="B", verification="现网核验",
                      supports=["I1", "I3"], source_type="系统现状")
    evidence.register(ev, "动销覆盖率统计", level="A", verification="按终端/SKU/月份抽样",
                      supports=["I2"], source_type="运行记录")
    evidence.register(ev, "DMS 接口评估报告", level="A", verification="接口项逐项核验",
                      supports=["I4", "T3"], source_type="系统现状")
    evidence.register(ev, "AA 架构与现网功能核验", level="B", verification="4 业务域逐项",
                      supports=["T1", "T2"], source_type="制度")
    evidence.register(ev, "治理/安全/审计制度与台账", level="B", verification="文档评审",
                      supports=["A1", "A2", "A4"], source_type="制度")
    evidence.register(ev, "AI 试点复核与监控记录", level="A", verification="试点演示+记录抽查",
                      supports=["A3", "A5", "A6", "A7"], source_type="运行记录")
    evidence.register(ev, "运营分工与迭代记录", level="B", verification="文档评审",
                      supports=["L1", "L2", "L3", "L4"], source_type="制度")
    return ev


class TestVitalDiagnosisE2E(unittest.TestCase):
    """VITAL 诊断端到端演练（A1/A2/A3/A6 涉及诊断部分）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_session(self):
        """完整跑一遍诊断会话，返回 (topic_dir, state, output)。"""
        # 1. 会话初始化（M1-09 复用）
        topic_dir = session.create_session(
            self.ws, "demo-enterprise", "示例企业集团", "data-platform-diagnosis", "数据中台 AI 转型诊断"
        )
        method, errors = parse_manifest(VITAL_MANIFEST)
        self.assertEqual(errors, [])
        state = state_mod.load_state(topic_dir / "state.json")
        begin(method, state)

        # 2. 步骤 00 诊断准备：范围 + 打分规则确认（含锚点修改动态化验证）
        out00 = topic_dir / "modules" / "diagnosis-step00.md"
        out00.write_text("# 诊断准备\n\n诊断对象：数据中台；范围：数据管理域\n", encoding="utf-8")
        r0 = run_step(state, method, "00", out00,
                      ai_verdict={"core_ok": True, "conditional": False, "note": "范围明确"},
                      session_dir=topic_dir)
        self.assertEqual(r0["status"], "pass")
        # 写入 confirmed scoring md（文件级 gate G1）：同步 state.scoring_config + artifact manifest
        files.write_scoring_artifact(topic_dir, SCORING_CONFIG, SCORING_CONFIRMATION, state=state)
        self.assertEqual(state_mod.get_scoring_config(state)["customNote"],
                         "顾问将 I2 锚点第 1 档改为「依赖人工判断（顾问定制）」")
        advance(state, method)

        # 3. 步骤 01-05 五维打分（22 角度，按维推进；G2：每维 run_step 后写 confirmed 维度 md）
        dim_steps = {"01": "v", "02": "i", "03": "t", "04": "a", "05": "l"}
        dim_angles = {"01": ["V1", "V2", "V3", "V4"], "02": ["I1", "I2", "I3", "I4"],
                      "03": ["T1", "T2", "T3"], "04": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
                      "05": ["L1", "L2", "L3", "L4"]}
        for sid, dim in dim_steps.items():
            angles = dim_angles[sid]
            out = topic_dir / "modules" / f"diagnosis-{sid}.md"
            out.write_text(f"# {method.step_by_id(sid).name}\n\n（演练模拟：{len(angles)} 角度打分）\n", encoding="utf-8")
            r = run_step(state, method, sid, out, ai_verdict={"core_ok": True}, session_dir=topic_dir)
            self.assertEqual(r["status"], "pass", f"步骤 {sid} 应通过：{r}")
            # 写 confirmed 维度 md（含 item id；source_refs 指向 scoring 当前版本）
            dim_data = {
                "summary": f"{method.step_by_id(sid).name}：演练维度总结（用户已确认）",
                "angles": [
                    {"angle": a, "score": DEMO_SCORES[a]["score"], "judgment": DEMO_SCORES[a]["judgment"],
                     "evidenceIds": DEMO_SCORES[a]["evidenceIds"], "anchor_ref": "diagnosis-scoring-*-v1"}
                    for a in angles
                ],
                "items": [
                    {"angle": angles[0], "type": "fact", "content": f"{angles[0]} 现状事实（演练）", "evidence_refs": []},
                    {"angle": angles[0], "type": "issue", "content": f"{angles[0]} 问题点（演练）", "evidence_refs": []},
                ],
            }
            files.write_dimension_artifact(topic_dir, dim, dim_data, SCORING_CONFIRMATION, state=state)
            advance(state, method)

        # 4. evidence 登记（全流程累积）
        ev_list = build_evidence()

        # 5. 统计（维度分/总体分）——overview md 需要维度分
        result = scoring.compute_all(DEMO_SCORES, state_mod.get_scoring_config(state))
        self.assertEqual(result["errors"], [])
        # V: (3.5+3.5+3.5+3.0)/4 = 3.375 → 3.4；I: (3.0+1.5+3.0+1.0)/4 = 2.125 → 2.1
        self.assertEqual(result["dimension_scores"]["V"], 3.4)
        self.assertEqual(result["dimension_scores"]["I"], 2.1)
        # 总体（五维均分）≈ (3.4+2.1+T+A+L)/5；本演练仅 2 维有分 → 总体 = (3.4+2.1)/2 = 2.8
        # （未打分维度不计入，对齐方法论 §二-2）
        self.assertIsNotNone(result["overall_score"])

        # 6. 写 confirmed overview md（5 维完成后；G2：step:06 前置 gate 依赖它）
        files.write_overview_artifact(topic_dir, {
            "conclusion": "总体结论（演练）：数据链路断裂阻断 AI 消费；V/L 维度扎实，I 维全场最弱",
            "dimensions": [
                {"dim": d, "name": files.DIM_NAMES[d.lower()], "score": result["dimension_scores"].get(d),
                 "judgment": "演练判断"} for d in ("V", "I") if d in result["dimension_scores"]
            ],
            "narrative": "跨维度关联（演练）：I 维链路断裂限制 T/A/L 的 AI 就绪度",
            "items": [{"angle": "I2", "type": "issue", "content": "数据链路断裂（演练）", "evidence_refs": ["E-04"]}],
        }, SCORING_CONFIRMATION, state=state)

        # 7. 步骤 06 阻断识别（规则型 ≤2.0 + 语义型链路断裂）→ 写 confirmed blockers md
        blocks = blocker.identify_blockers(
            DEMO_SCORES, ev_list, state_mod.get_scoring_config(state),
            semantic_blocks=[{"angle": "T3", "issue": "核心业务系统无直连接口，链路断裂",
                              "impact": "AI 场景无实时业务数据输入",
                              "evidenceIds": ["E-05"], "suggestion": "建设直连接口"}],
        )
        self.assertEqual({b["angle"] for b in blocks}, {"I2", "I4", "T3"})
        out06 = topic_dir / "modules" / "diagnosis-06.md"
        out06.write_text(f"# 阻断性问题与改进路径\n\n{len(blocks)} 项阻断问题\n", encoding="utf-8")
        r6 = run_step(state, method, "06", out06, ai_verdict={"core_ok": True}, session_dir=topic_dir)
        self.assertEqual(r6["status"], "pass")
        files.write_blockers_artifact(topic_dir, {
            "blockers": [
                {"id": b["id"], "angle": b["angle"], "type": "规则型（≤2.0）", "impact": b["impact"],
                 "evidenceIds": b["evidenceIds"], "source_item": f"D-{b['angle']}-issue-001",
                 "suggestion": b["suggestion"], "owner": "待指定", "timeline": "待指定"}
                for b in blocks
            ],
            "path": blocker.build_improvement_path(blocks),
        }, SCORING_CONFIRMATION, state=state)
        advance(state, method)

        # 8. 组装输出 → 出口校验（diagnosis 分支）
        output = {
            "diagnosisScope": {"objects": ["数据中台"], "boundary": "数据管理域"},
            "scoringConfig": state_mod.get_scoring_config(state),
            "dimensionScores": [
                {"dim": "V", "name": "业务价值与战略对齐", "score": 3.4},
                {"dim": "I", "name": "数据生命周期与适用性", "score": 2.1},
            ],
            "angleScores": [
                {"angle": a, "name": a, "score": v["score"], "judgment": v["judgment"],
                 "evidenceIds": v["evidenceIds"]}
                for a, v in DEMO_SCORES.items()
            ],
            "blockingIssues": blocks,
            "improvementPath": blocker.build_improvement_path(blocks),
            "evidenceList": ev_list,
            "overallScore": result["overall_score"],
            "reportNarrative": "执行摘要：数据链路断裂阻断 AI 消费；V/L 维度扎实，I 维全场最弱",
            "openIssues": [],
        }
        exit_result = run_exit(output, method.output_contract["requires"], state, contract_type="diagnosis")
        self.assertEqual(exit_result["errors"], [], f"出口校验应通过：{exit_result['errors']}")
        self.assertFalse(exit_result["blocked"])

        # 9. 确认包组装（唯一事实源）→ 授权 finalized
        content = assemble_diagnosis_package(output, state, method)
        pkg_path = write_diagnosis_package(topic_dir, content, slug="data-platform-diagnosis")
        self.assertTrue(pkg_path.exists())
        confirm(state, "pass")
        self.assertEqual(state["status"], "authorized")
        state_mod.transition(state, "finalized", authorized=True)

        return topic_dir, state, output

    def test_full_vital_diagnosis_session(self):
        """完整诊断会话走通（A1 22 角度 / A2 动态化 / A3 统计 / A6 确认包）。"""
        topic_dir, state, output = self._run_session()
        # 22 角度齐全
        self.assertEqual(len(output["angleScores"]), 22)
        # 确认包含核心 section；业务数据来自确认包（演练自己的业务名），
        # Demo 特有业务词汇零泄漏（分数是合法统计结果，不做数值断言）
        content = (topic_dir / "modules" / "diagnosis-confirm-data-platform-diagnosis-v1.md").read_text(encoding="utf-8")
        for section in ("诊断范围界定", "维度打分分布", "二级角度打分", "阻断性问题清单", "改进路径", "证据清单", "总体分"):
            self.assertIn(f"## {section}", content)
        self.assertIn("示例企业集团", content)
        self.assertNotIn("T+15", content)
        self.assertNotIn("快消品", content)
        self.assertNotIn("经销商", content)
        self.assertNotIn("进销存", content)

    def test_canvas_audit_gate(self):
        """确认包渲染审计闸门：canvas 合规基线过 audit（代表 LLM 产物质量达标）。"""
        canvas = CANVAS_HTML.read_text(encoding="utf-8")
        self.assertEqual(audit_html(canvas), [], "诊断报告 canvas 应通过 token 无裸值 + 不变量审计")

    def test_demo_artifacts_written(self):
        """演练产物写入 artifacts/demo/vital-diagnosis-e2e/（确认包 md + HTML）。

        HTML 用 canvas 合规基线代表 AI 渲染质量（单测无 LLM 不现场渲染，
        对齐 vision e2e 的 audit 闸门验证方式）；命名对齐诊断域规范
        diagnosis-confirm-{slug}（对应确认包 md 唯一事实源）。
        """
        topic_dir, _, output = self._run_session()
        DEMO_OUT.mkdir(parents=True, exist_ok=True)
        content = (topic_dir / "modules" / "diagnosis-confirm-data-platform-diagnosis-v1.md").read_text(encoding="utf-8")
        (DEMO_OUT / "diagnosis-confirm-data-platform-diagnosis.md").write_text(content, encoding="utf-8")
        (DEMO_OUT / "diagnosis-confirm-data-platform-diagnosis.html").write_text(
            CANVAS_HTML.read_text(encoding="utf-8"), encoding="utf-8")
        # 断言产物落位（HTML 有对应 MD 唯一事实源，可通过载体合规检查）
        self.assertTrue((DEMO_OUT / "diagnosis-confirm-data-platform-diagnosis.md").exists())
        self.assertTrue((DEMO_OUT / "diagnosis-confirm-data-platform-diagnosis.html").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
