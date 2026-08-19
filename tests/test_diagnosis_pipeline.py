"""M1-05 诊断引擎全链路验证（mock 诊断方法 2 维 4 角度）：

链路：诊断准备（scoring_config 确认）→ 逐角度打分 → evidence 登记 →
blocker 识别 → scoring 统计 → 出口契约校验（diagnosis 分支）。
同时覆盖 M1-04 scoring_config 版本化与打分规则动态化。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import blocker, contract, evidence, scoring, session, state as state_mod  # noqa: E402
from _engine.executor import advance, begin, current_step_id, regress_to, run_step  # noqa: E402
from _engine.parser import parse_manifest  # noqa: E402

MOCK_MANIFEST = ROOT / "tests" / "fixtures" / "mock-diagnosis-method" / "manifest.yaml"

# 顾问确认的打分规则（锚点从方法论默认参考修改——验证动态化）
SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "blockThreshold": 2.0,
    "anchors": {
        "V": {"V1": {1: "初步定位", 2: "明确职责", 3: "全面落地", 4: "成效量化", 5: "机制成熟"},
              "V2": {1: "范围初明", 2: "边界明确", 3: "跨平台落实", 4: "边界量化", 5: "模型自适应"}},
        "I": {"I1": {1: "核心识别", 2: "定义规范", 3: "目录贯通", 4: "覆盖核查", 5: "管理自适应"},
              "I2": {1: "依赖人工", 2: "质量规则", 3: "规模供给", 4: "量化监控", 5: "按需供给"}},
    },
    "customNote": "顾问将 I2 锚点第 1 档改为「依赖人工判断」",
}


def make_state(tmp: Path) -> dict:
    st = state_mod.new_state("test-project", "测试项目", "diagnosis-demo", "诊断演示")
    state_mod.set_scoring_config(st, SCORING_CONFIG)
    return st


class TestScoringConfigVersioning(unittest.TestCase):
    """M1-04 打分规则运行时注入：版本化覆盖不丢失历史。"""

    def test_set_and_get(self):
        st = state_mod.new_state("p", "项目", "t", "主题")
        self.assertIsNone(state_mod.get_scoring_config(st))
        state_mod.set_scoring_config(st, SCORING_CONFIG)
        self.assertEqual(state_mod.get_scoring_config(st), SCORING_CONFIG)

    def test_versioning_history(self):
        st = state_mod.new_state("p", "项目", "t", "主题")
        v1 = {"scale": {"min": 1, "max": 5, "step": 0.5}, "blockThreshold": 2.0, "anchors": {}}
        v2 = dict(v1, blockThreshold=1.5)
        state_mod.set_scoring_config(st, v1)
        state_mod.set_scoring_config(st, v2)
        self.assertEqual(state_mod.get_scoring_config(st), v2)
        self.assertEqual(len(st["scoring_config_history"]), 1)
        self.assertEqual(st["scoring_config_history"][0]["blockThreshold"], 2.0)
        self.assertIn("replaced_at", st["scoring_config_history"][0])

    def test_config_required_before_scoring(self):
        """scoring_config 未确认（None）时统计被阻断（对齐 §6.3 规则确认前不进入打分）。"""
        result = scoring.compute_all({"V1": {"score": 3.0}}, None)
        self.assertTrue(any("scale" in e for e in result["errors"]))


class TestDiagnosisPipeline(unittest.TestCase):
    """mock 诊断方法全链路。"""

    def test_full_pipeline(self):
        method, errs = parse_manifest(MOCK_MANIFEST)
        self.assertEqual(errs, [])

        with tempfile.TemporaryDirectory() as td:
            st = make_state(Path(td))

            # --- 步骤 00 诊断准备：范围界定（打分规则已确认）---
            state_mod.set_step(st, "00", status="completed")

            # --- 步骤 01 V 维打分（V1/V2）+ 证据登记 ---
            scores = {
                "V1": {"score": 3.5, "judgment": "战略承接清晰，价值已验证", "evidenceIds": ["E-01"]},
                "V2": {"score": 4.0, "judgment": "业务边界明确", "evidenceIds": ["E-01"]},
            }
            state_mod.set_step(st, "01", status="completed")

            # --- 步骤 02 I 维打分（I1/I2）：I2 低分触发阻断 ---
            scores["I1"] = {"score": 3.0, "judgment": "数据对象目录基本贯通", "evidenceIds": ["E-02"]}
            scores["I2"] = {"score": 1.5, "judgment": "动销数据漏采迟报", "evidenceIds": ["E-03"]}
            state_mod.set_step(st, "02", status="completed")

            # --- evidence 登记 ---
            ev_list: list[dict] = []
            evidence.register(ev_list, "战略文件与年度 OKR", level="B",
                              verification="文档评审 + 访谈", supports=["V1", "V2"], source_type="制度")
            evidence.register(ev_list, "对象目录清单", level="B",
                              verification="现网核验", supports=["I1"], source_type="系统现状")
            evidence.register(ev_list, "覆盖率统计 <40%", level="A",
                              verification="按终端/SKU/月份抽样", supports=["I2"], source_type="运行记录")

            # --- 步骤 03 阻断识别 + 语义型链路断裂 ---
            blocks = blocker.identify_blockers(
                scores, ev_list, state_mod.get_scoring_config(st),
                semantic_blocks=[{"angle": "T3", "issue": "DMS 无直连接口，链路断裂",
                                  "impact": "AI 场景无数据输入", "evidenceIds": ["E-04"],
                                  "suggestion": "建设 DMS 直连接口"}],
            )
            self.assertEqual({b["angle"] for b in blocks}, {"I2", "T3"})

            # --- scoring 统计 ---
            result = scoring.compute_all(scores, state_mod.get_scoring_config(st))
            self.assertEqual(result["errors"], [])
            # V: (3.5+4.0)/2 = 3.75 → 3.8；I: (3.0+1.5)/2 = 2.25 → 2.2
            self.assertEqual(result["dimension_scores"]["V"], 3.8)
            self.assertEqual(result["dimension_scores"]["I"], 2.2)
            self.assertEqual(result["overall_score"], 3.0)  # (3.8+2.2)/2

            # --- 出口契约校验（diagnosis 分支）---
            output = {
                "diagnosisScope": {"objects": ["数据中台"], "boundary": "数据管理域"},
                "scoringConfig": state_mod.get_scoring_config(st),
                "dimensionScores": [
                    {"dim": "V", "name": "业务价值与战略对齐", "score": 3.8},
                    {"dim": "I", "name": "数据生命周期与适用性", "score": 2.2},
                ],
                "angleScores": [
                    {"angle": a, "name": a, "score": v["score"],
                     "judgment": v["judgment"], "evidenceIds": v["evidenceIds"]}
                    for a, v in scores.items()
                ],
                "blockingIssues": blocks,
                "improvementPath": blocker.build_improvement_path(blocks),
                "evidenceList": ev_list,
                "overallScore": result["overall_score"],
                "reportNarrative": "执行摘要：数据链路断裂阻断 AI 消费",
            }
            errs = contract.validate_output(output, requires=[], contract_type="diagnosis")
            self.assertEqual(errs, [])

    def test_contract_blocked_missing_core(self):
        """diagnosis 契约缺核心字段（overallScore）→ 阻断。"""
        errs = contract.validate_output(
            {"diagnosisScope": {"objects": ["x"]}, "scoringConfig": SCORING_CONFIG},
            requires=[], contract_type="diagnosis",
        )
        self.assertTrue(any("缺失核心字段：overallScore" in e for e in errs))

    def test_contract_blocked_blockers_without_path(self):
        """存在阻断性问题但缺 improvementPath → 条件必填阻断。"""
        errs = contract.validate_output(
            {
                "diagnosisScope": {"objects": ["x"]},
                "scoringConfig": SCORING_CONFIG,
                "dimensionScores": [{"dim": "V", "name": "V", "score": 2.0}],
                "angleScores": [{"angle": "V1", "name": "V1", "score": 1.5, "judgment": "x", "evidenceIds": []}],
                "evidenceList": [{"id": "E-01", "evidence": "x", "level": "B", "verification": "x", "supports": ["V1"]}],
                "overallScore": 2.0,
                "reportNarrative": "x",
                "blockingIssues": [{"id": "B-01", "angle": "V1", "issue": "x", "impact": "", "evidenceIds": [], "suggestion": ""}],
                # 缺 improvementPath
            },
            requires=[], contract_type="diagnosis",
        )
        self.assertTrue(any("improvementPath" in e for e in errs))

    def test_gate_three_state_reuse(self):
        """diagnosis 方法步骤 gate 三态复用（P2-5）：executor 走 begin/run_step/advance/regress_to。

        验证诊断方法步骤（步骤 01 V 维）三态判定：
        - core_ok=False → regress（回指到步骤 00 之前的处理：回指已执行步骤）
        - core_ok=True + conditional=True → conditional（登记未决项）
        - core_ok=True + conditional=False → pass
        """
        method, errs = parse_manifest(MOCK_MANIFEST)
        self.assertEqual(errs, [])

        with tempfile.TemporaryDirectory() as td:
            st = make_state(Path(td))
            begin(method, st)

            # 步骤 00 诊断准备：pass
            r0 = run_step(st, method, "00", Path(td) / "step00.md",
                          ai_verdict={"core_ok": True, "conditional": False, "note": "范围明确"})
            self.assertEqual(r0["status"], "pass")
            advance(st, method)  # 00 → 01
            self.assertEqual(current_step_id(st, method), "01")

            # 步骤 01 V 维：conditional（非核心项未满足，登记未决项）
            r1 = run_step(st, method, "01", Path(td) / "step01.md",
                          ai_verdict={"core_ok": True, "conditional": True, "note": "V4 证据待补强"})
            self.assertEqual(r1["status"], "conditional")
            self.assertEqual(len(st["open_issues"]), 1)
            self.assertEqual(st["open_issues"][0]["sourceStep"], "01")

            # 步骤 02 I 维：core 失败 → regress（回指到已执行步骤 01）
            r2 = run_step(st, method, "02", Path(td) / "step02.md",
                          ai_verdict={"core_ok": False, "conditional": False, "note": "I1 无证据"})
            self.assertEqual(r2["status"], "regress")
            regress_to(st, method, "01", reason="I1 无证据（core 失败）")
            self.assertEqual(current_step_id(st, method), "01")
            self.assertEqual(state_mod.step_status(st, "01"), "draft")
            self.assertEqual(st["steps"]["01"]["regress_count"], 1)

    def test_threshold_adjust_changes_blockers(self):
        """阻断阈值调整场景（P2-7）：调低阈值后识别结果变化。"""
        scores = {
            "V1": {"score": 3.5, "judgment": "良好", "evidenceIds": ["E-01"]},
            "I1": {"score": 2.0, "judgment": "覆盖不全", "evidenceIds": ["E-02"]},
            "I2": {"score": 1.5, "judgment": "漏采", "evidenceIds": ["E-03"]},
        }
        # 默认阈值 2.0：I1(2.0) 与 I2(1.5) 均触发
        blocks_default = blocker.identify_blockers(scores, [], {"blockThreshold": 2.0})
        self.assertEqual({b["angle"] for b in blocks_default}, {"I1", "I2"})

        # 顾问下调阈值至 1.8：I1(2.0) 不再触发，仅 I2(1.5) 触发（动态化生效）
        blocks_lowered = blocker.identify_blockers(scores, [], {"blockThreshold": 1.8})
        self.assertEqual({b["angle"] for b in blocks_lowered}, {"I2"})

    def test_evidence_single_source_not_blocking(self):
        """缺双来源"待补强"而非阻断（P2-5 / 方法论"材料缺失≠能力缺失"）。

        重要事实仅单一来源时，cross_validation_ok 返回 False（提示待补强），
        但阻断性问题识别与出口校验均不因此阻断——证据不足只提示，不低分代替。
        """
        ev_list: list[dict] = []
        evidence.register(ev_list, "仅制度文件", level="B", source_type="制度",
                          verification="文档评审", supports=["V1"])
        ok, sources = evidence.cross_validation_ok(ev_list, "V1")
        self.assertFalse(ok)  # 单来源 → 待补强提示
        self.assertEqual(len(sources), 1)

        # 阻断识别不受单来源影响（按打分判定，不因证据少而误报）
        scores = {"V1": {"score": 4.0, "judgment": "良好", "evidenceIds": ["E-01"]}}
        blocks = blocker.identify_blockers(scores, ev_list, {"blockThreshold": 2.0})
        self.assertEqual(blocks, [])

    def test_bad_score_step_excluded(self):
        """非法步进分值：报错 + 剔除出统计（对齐 M1-01 完成标准）。"""
        method, _ = parse_manifest(MOCK_MANIFEST)
        scores = {"V1": {"score": 3.3}, "V2": {"score": 4.0}}
        result = scoring.compute_all(scores, SCORING_CONFIG)
        self.assertTrue(any("V1" in e for e in result["errors"]))
        self.assertEqual(result["dimension_scores"]["V"], 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
