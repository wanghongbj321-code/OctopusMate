"""G2 测试：维度 / 总体 / 阻断 md 链（文件级 gate 优化 §12.3）。

覆盖：
- G2-01 write_dimension_artifact / write_overview_artifact / write_blockers_artifact
  （文件名 / source_refs / confirmation / hash / manifest / 前置缺失时拒绝）
- G2-02 item id 生成（D-{angle}-{type}-{NNN} 唯一性 / 非法 type）
- G2-03 step:02-06 required gate（缺前置维度 md / 缺 overview → 阻断）
- G2-04 stale 传播（scoring v2 → 维度 stale；维度 v2 → overview/blockers stale）
- G2-05 reconcile.rebuild_state_from_artifacts（从 confirmed md 链重建 state）
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import files, parser, reconcile, session, state as state_mod  # noqa: E402
from _engine.executor import FileGateError, begin, run_step  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
GATE_MANIFEST = FIXTURES / "gate-diagnosis-method" / "manifest.yaml"

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:20:用户确认",
    "confirmation_text": "用户确认",
}

SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "anchors": {
        "V": {"V1": {1: "初步", 5: "成熟"}, "V2": {1: "初明", 5: "自适应"}},
        "I": {"I1": {1: "核心识别", 5: "自适应"}, "I2": {1: "依赖人工", 5: "按需"}},
    },
}

# 维度数据（V/I 维，2 角度/维，与 gate-mock manifest 对齐）
DIM_DATA = {
    "v": {
        "summary": "V 维总结：战略承接清晰",
        "angles": [
            {"angle": "V1", "score": 3.0, "judgment": "承接清晰", "evidenceIds": ["E-01"], "anchor_ref": "diagnosis-scoring-*-v1"},
            {"angle": "V2", "score": 3.5, "judgment": "边界明确", "evidenceIds": ["E-01"], "anchor_ref": "diagnosis-scoring-*-v1"},
        ],
        "items": [
            {"angle": "V1", "type": "fact", "content": "战略文件明确", "evidence_refs": ["E-01"]},
            {"angle": "V1", "type": "issue", "content": "成效未量化", "evidence_refs": ["E-01"]},
        ],
    },
    "i": {
        "summary": "I 维总结：数据链路部分断裂",
        "angles": [
            {"angle": "I1", "score": 3.0, "judgment": "对象已识别", "evidenceIds": ["E-02"], "anchor_ref": "diagnosis-scoring-*-v1"},
            {"angle": "I2", "score": 1.5, "judgment": "漏采迟报", "evidenceIds": ["E-03"], "anchor_ref": "diagnosis-scoring-*-v1"},
        ],
        "items": [
            {"angle": "I2", "type": "issue", "content": "动销数据漏采", "evidence_refs": ["E-03"]},
        ],
    },
}


class TestItemIds(unittest.TestCase):
    """G2-02：item id 生成规则。"""

    def test_generate_unique(self):
        items = files.make_item_ids([
            {"angle": "V1", "type": "fact", "content": "a"},
            {"angle": "V1", "type": "fact", "content": "b"},
            {"angle": "V1", "type": "issue", "content": "c"},
            {"angle": "V2", "type": "fact", "content": "d"},
        ])
        ids = [it["item_id"] for it in items]
        self.assertEqual(ids, ["D-V1-fact-001", "D-V1-fact-002", "D-V1-issue-001", "D-V2-fact-001"])
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(files.validate_item_ids(items), [])

    def test_invalid_type_rejected(self):
        with self.assertRaises(ValueError):
            files.make_item_ids([{"angle": "V1", "type": "foo", "content": "x"}])

    def test_duplicate_detected(self):
        errors = files.validate_item_ids([
            {"item_id": "D-V1-fact-001"},
            {"item_id": "D-V1-fact-001"},
        ])
        self.assertTrue(any("重复" in e for e in errors))


class TestDimensionArtifact(unittest.TestCase):
    """G2-01：维度 md 写入。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_dimension(self):
        path = files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        self.assertEqual(path.name, "diagnosis-v-gate-topic-v1.md")
        art = files.read_artifact(path)
        self.assertTrue(art.valid, art.errors)
        meta = art.meta
        self.assertEqual(meta["artifact_type"], "diagnosis-dimension")
        self.assertEqual(meta["artifact_id"], "diagnosis.dimension.v.current")
        self.assertEqual(meta["source_refs"], ["diagnosis.scoring.current@v1"])
        # item id 已生成并写入正文
        self.assertIn("D-V1-fact-001", art.body)
        self.assertIn("D-V1-issue-001", art.body)
        # manifest 登记
        entry = self.state["artifacts"]["diagnosis.dimension.v.current"]
        self.assertEqual(entry["version"], 1)
        self.assertEqual(entry["depends_on"], ["diagnosis.scoring.current@v1"])

    def test_write_without_scoring_rejected(self):
        """缺 confirmed scoring md → 拒绝写入维度 md（前置依赖）。"""
        state2 = state_mod.new_state("p", "项目", "t", "主题")
        with self.assertRaises(ValueError):
            files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=state2)

    def test_invalid_dim_rejected(self):
        with self.assertRaises(ValueError):
            files.write_dimension_artifact(self.topic_dir, "x", DIM_DATA["v"], CONFIRMATION, state=self.state)


class TestOverviewAndBlockersArtifact(unittest.TestCase):
    """G2-01：总体 / 阻断 md 写入与前置校验。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "i", DIM_DATA["i"], CONFIRMATION, state=self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def _overview_data(self):
        return {
            "conclusion": "总体：V 维扎实，I 维数据链路断裂为瓶颈",
            "dimensions": [
                {"dim": "V", "name": "业务价值与战略对齐", "score": 3.3, "judgment": "扎实"},
                {"dim": "I", "name": "数据生命周期与适用性", "score": 2.3, "judgment": "链路断裂"},
            ],
            "narrative": "跨维度：数据链路断裂影响 AI 消费",
            "items": [{"angle": "I2", "type": "issue", "content": "数据链路断裂", "evidence_refs": ["E-03"]}],
        }

    def test_write_overview(self):
        path = files.write_overview_artifact(self.topic_dir, self._overview_data(), CONFIRMATION, state=self.state)
        self.assertEqual(path.name, "diagnosis-overview-gate-topic-v1.md")
        art = files.read_artifact(path)
        self.assertTrue(art.valid, art.errors)
        self.assertEqual(art.meta["artifact_id"], "diagnosis.overview.current")
        self.assertEqual(sorted(art.meta["source_refs"]), [
            "diagnosis.dimension.i.current@v1", "diagnosis.dimension.v.current@v1"])

    def test_write_overview_missing_dimension(self):
        """缺维度 md → 拒绝写总体（前置依赖）。"""
        state2 = state_mod.new_state("p", "项目", "t", "主题")
        state2["artifacts"] = {"diagnosis.scoring.current": {"version": 1, "status": "confirmed"}}
        with self.assertRaises(ValueError):
            files.write_overview_artifact(self.topic_dir, self._overview_data(), CONFIRMATION, state=state2)

    def test_write_blockers(self):
        files.write_overview_artifact(self.topic_dir, self._overview_data(), CONFIRMATION, state=self.state)
        blockers_data = {
            "blockers": [{
                "id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "AI 无数据输入",
                "evidenceIds": ["E-03"], "source_item": "D-I2-issue-001",
                "suggestion": "建设自动采集", "owner": "待指定", "timeline": "待指定"}],
            "path": [{"priority": 1, "action": "建设自动采集", "source_blocker": "B-01",
                      "suggestion": "建设自动采集", "owner": "", "timeline": ""}],
        }
        path = files.write_blockers_artifact(self.topic_dir, blockers_data, CONFIRMATION, state=self.state)
        self.assertEqual(path.name, "diagnosis-blockers-gate-topic-v1.md")
        art = files.read_artifact(path)
        self.assertTrue(art.valid, art.errors)
        self.assertEqual(art.meta["artifact_id"], "diagnosis.blockers.current")
        self.assertIn("diagnosis.overview.current@v1", art.meta["source_refs"])

    def test_write_blockers_missing_overview(self):
        """缺 overview → 拒绝写阻断（前置依赖）。"""
        with self.assertRaises(ValueError):
            files.write_blockers_artifact(self.topic_dir, {"blockers": [], "path": []}, CONFIRMATION, state=self.state)


class TestStep02to06Gate(unittest.TestCase):
    """G2-03：step 02-06 required gate（完整 md 链）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        method, errors = parser.parse_manifest(GATE_MANIFEST)
        assert not errors, errors
        self.method = method
        begin(method, self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def _step(self, sid, ai=None):
        return run_step(self.state, self.method, sid, self.topic_dir / "modules" / f"step{sid}.md",
                        ai or {"core_ok": True}, session_dir=self.topic_dir)

    def test_step02_blocked_without_v_dim(self):
        """只有 scoring，缺 V 维 md → run_step("02") 阻断。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        with self.assertRaises(FileGateError):
            self._step("02")

    def test_step06_blocked_without_overview(self):
        """5 维齐但缺 overview → run_step("06") 阻断。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in ("v", "i"):
            files.write_dimension_artifact(self.topic_dir, d, DIM_DATA[d], CONFIRMATION, state=self.state)
        with self.assertRaises(FileGateError):
            self._step("06")

    @staticmethod
    def _dim_data(dim: str) -> dict:
        angles = {"v": ["V1", "V2"], "i": ["I1", "I2"], "t": ["T1", "T2"],
                  "a": ["A1", "A2"], "l": ["L1", "L2"]}[dim]
        return {
            "summary": f"{dim} 维总结",
            "angles": [{"angle": a, "score": 3.0, "judgment": "j", "evidenceIds": ["E-01"],
                        "anchor_ref": "diagnosis-scoring-*-v1"} for a in angles],
            "items": [{"angle": angles[0], "type": "fact", "content": "现状事实", "evidence_refs": []}],
        }

    def test_full_chain_passes(self):
        """scoring + 5 维 + overview → step 02/06 均通过。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in ("v", "i", "t", "a", "l"):
            files.write_dimension_artifact(self.topic_dir, d, self._dim_data(d), CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []}, CONFIRMATION, state=self.state)
        r = self._step("02")
        self.assertEqual(r["status"], "pass")
        r6 = self._step("06")
        self.assertEqual(r6["status"], "pass")


class TestStalePropagation(unittest.TestCase):
    """G2-04：上游版本更新触发下游 stale。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_scoring_v2_stales_dimensions(self):
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        # scoring v2
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        self.assertEqual(self.state["artifacts"]["diagnosis.dimension.v.current"]["status"], "stale")

    def test_dimension_v2_stales_overview(self):
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in ("v", "i"):
            files.write_dimension_artifact(self.topic_dir, d, DIM_DATA[d], CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []}, CONFIRMATION, state=self.state)
        # V 维 v2
        files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        self.assertEqual(self.state["artifacts"]["diagnosis.overview.current"]["status"], "stale")
        self.assertEqual(self.state["artifacts"]["diagnosis.dimension.v.current"]["version"], 2)

    def test_stale_blocks_step(self):
        """scoring v2 后，引用 v1 的维度 md stale → 后续 run_step 阻断（G2 出口）。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)  # v2
        method, errors = parser.parse_manifest(GATE_MANIFEST)
        assert not errors, errors
        state = self.state
        begin(method, state)
        # step:01 需 scoring（v2，confirmed OK）；step:02 需 V 维（stale → 阻断）
        run_step(state, method, "01", self.topic_dir / "m.md", {"core_ok": True}, session_dir=self.topic_dir)
        with self.assertRaises(FileGateError):
            run_step(state, method, "02", self.topic_dir / "m2.md", {"core_ok": True}, session_dir=self.topic_dir)


class TestRebuildState(unittest.TestCase):
    """G2-05：从 confirmed md 链重建 state。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", DIM_DATA["v"], CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "i", DIM_DATA["i"], CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [
                {"dim": "V", "name": "x", "score": 3.3, "judgment": "j"},
                {"dim": "I", "name": "y", "score": 2.3, "judgment": "k"}],
            "narrative": "n", "items": []}, CONFIRMATION, state=self.state)
        files.write_blockers_artifact(self.topic_dir, {
            "blockers": [{
                "id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "im",
                "evidenceIds": ["E-03"], "source_item": "D-I2-issue-001",
                "suggestion": "sug", "owner": "待指定", "timeline": "待指定"}],
            "path": []}, CONFIRMATION, state=self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def test_rebuild_restores_state(self):
        # 清空 state 业务字段（模拟丢失）
        self.state.pop("artifacts", None)
        self.state.pop("scoring_config", None)
        # 重建
        state2 = reconcile.rebuild_state_from_artifacts(self.topic_dir, self.state)
        # manifest 恢复
        self.assertEqual(set(state2["artifacts"]), {
            "diagnosis.scoring.current", "diagnosis.dimension.v.current",
            "diagnosis.dimension.i.current", "diagnosis.overview.current",
            "diagnosis.blockers.current"})
        # scoring_config 恢复（现有镜像已删 → md 解析兜底）
        self.assertIsNotNone(state2.get("scoring_config"))
        self.assertIn("anchors", state2["scoring_config"])
        # angleScores / dimensionScores 恢复（从角度表算术平均：V=(3.0+3.5)/2=3.25→3.2）
        self.assertEqual(len(state2.get("angleScores") or []), 4)
        dims = {d["dim"]: d["score"] for d in state2.get("dimensionScores") or []}
        self.assertAlmostEqual(dims["V"], 3.2)
        self.assertAlmostEqual(dims["I"], 2.2)
        # blockingIssues 恢复
        self.assertEqual(state2.get("blockingIssues", [])[0]["id"], "B-01")
        # evidenceList 恢复（编号骨架）
        ev = state2.get("evidenceList") or []
        self.assertIn("E-01", [e["id"] for e in ev])
        self.assertIn("E-03", [e["id"] for e in ev])

    def test_rebuild_preserves_existing_scoring_mirror(self):
        """现有 state.scoring_config 镜像可信时优先保留（重建不覆盖）。"""
        state2 = reconcile.rebuild_state_from_artifacts(self.topic_dir, self.state)
        self.assertIn("scale", state2["scoring_config"])
        self.assertNotIn("blockThreshold", state2["scoring_config"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
