"""G1 测试：打分规则 md 与步骤 01 前置 Gate（文件级 gate 优化）。

覆盖：
- G1-01 files.py 基础能力：frontmatter 解析、canonical hash 复算、版本不覆盖
- G1-02 write_scoring_artifact：生成 confirmed scoring md + 同步 state.json
- G1-03 step:01 required gate：无 confirmed scoring md / 缺 confirmation / bad hash /
  manifest 缺索引 / confirmed_by!=user / stale 时 run_step("01") 阻断（FileGateError）
- G1-04 回归：非 fileGate 方法（vision）行为不变
- G1-05 打分规则来源合并：user-upload / system-default / mixed（partial upload 不静默补齐）

对齐：internal/docs/dev-plan/VITAL 诊断功能开发计划-文件级gate优化方案-G0授权证据与产物索引设计.md
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import files, parser, session, state as state_mod  # noqa: E402
from _engine.executor import FileGateError, begin, run_step  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
ARTIFACTS = FIXTURES / "artifacts"
STATES = FIXTURES / "artifact-states"
GATE_MANIFEST = FIXTURES / "gate-diagnosis-method" / "manifest.yaml"
VISION_MANIFEST = FIXTURES / "mock-method" / "manifest.yaml"

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:12:用户确认整体采用默认锚点",
    "confirmation_text": "用户明确确认采用本版打分规则",
}

SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "blockThreshold": 2.0,
    "anchors": {
        "V": {"V1": {1: "初步定位", 3: "全面落地", 5: "机制成熟"}},
    },
    "customNote": "顾问确认采用默认锚点",
}


def make_gate_session(tmp: Path) -> tuple[dict, object]:
    """创建 fileGate 诊断会话（gate-diagnosis-method）。"""
    topic_dir = session.create_session(
        tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
    )
    method, errors = parser.parse_manifest(GATE_MANIFEST)
    assert not errors, errors
    state = state_mod.load_state(topic_dir / "state.json")
    begin(method, state)
    return state, method


class TestCanonicalHash(unittest.TestCase):
    """G0-02：hash 规范化（换行/尾随空格/末尾空行差异稳定；frontmatter 不参与）。"""

    def test_hash_stable_across_line_endings(self):
        a = "## 规则总览\n| 分值范围 | 1-5 |\n"
        b = "## 规则总览\r\n| 分值范围 | 1-5 |  \r\n\n\n"
        self.assertEqual(files.content_hash(a), files.content_hash(b))

    def test_hash_sensitive_to_content(self):
        self.assertNotEqual(files.content_hash("1-5"), files.content_hash("1-6"))

    def test_frontmatter_not_in_body_hash(self):
        """同一正文、不同 frontmatter（仅 status 差异）→ 正文 hash 相同。"""
        body = "# 打分规则\n\n| 分值范围 | 1-5 |\n"
        fm1 = f"---\nartifact_type: diagnosis-scoring\nstatus: draft\n---\n\n{body}"
        fm2 = f"---\nartifact_type: diagnosis-scoring\nstatus: confirmed\n---\n\n{body}"
        self.assertEqual(files.content_hash(fm1), files.content_hash(fm2))

    def test_hash_format(self):
        h = files.content_hash("hello")
        self.assertTrue(h.startswith("sha256:"))
        self.assertEqual(len(h), len("sha256:") + 64)


class TestFrontmatterParsing(unittest.TestCase):
    """G1-01：frontmatter 解析（valid / invalid / 无）。"""

    def test_parse_valid(self):
        text = "---\nartifact_type: diagnosis-scoring\nversion: 1\n---\n\nbody"
        meta, body = files.split_frontmatter(text)
        self.assertEqual(meta["artifact_type"], "diagnosis-scoring")
        self.assertEqual(meta["version"], 1)
        self.assertEqual(body, "\nbody")  # 结束定界符后的正文原样保留（canonicalize 处理空行）

    def test_parse_no_frontmatter(self):
        meta, body = files.split_frontmatter("# 无 frontmatter\n")
        self.assertIsNone(meta)
        self.assertEqual(body, "# 无 frontmatter\n")

    def test_parse_invalid_yaml(self):
        text = "---\nartifact_type: [unclosed\n---\n\nbody"
        meta, body = files.split_frontmatter(text)
        self.assertIsNone(meta)

    def test_parse_bom(self):
        text = "\ufeff---\nartifact_type: diagnosis-scoring\n---\n\nbody"
        meta, _ = files.split_frontmatter(text)
        self.assertEqual(meta["artifact_type"], "diagnosis-scoring")


class TestArtifactValidation(unittest.TestCase):
    """G1-01：artifact 结构校验（六类白名单 / 必填字段）。"""

    def test_unknown_artifact_type(self):
        errors = files.validate_artifact_meta({"artifact_type": "nope"})
        self.assertTrue(any("白名单" in e for e in errors))

    def test_missing_required_fields(self):
        errors = files.validate_artifact_meta({})
        self.assertTrue(any("必填" in e for e in errors))

    def test_confirmation_requires_user(self):
        meta = {
            "artifact_type": "diagnosis-scoring",
            "artifact_id": "diagnosis.scoring.current",
            "version": 1,
            "status": "confirmed",
            "source_refs": [],
            "content_hash": "sha256:" + "0" * 64,
            "confirmation": {
                "status": "confirmed",
                "confirmed_by": "ai",
                "confirmed_at": "2026-08-20T14:00:00+08:00",
                "interaction_ref": "x",
                "confirmed_content_hash": "sha256:" + "0" * 64,
            },
        }
        errors = files.validate_artifact_meta(meta)
        # confirmed_by=ai 结构上合法（枚举内），gate 层才拒绝——这里应无结构错误
        self.assertEqual(errors, [])


class TestVersion(unittest.TestCase):
    """G1-01：版本号递增与不覆盖。"""

    def test_next_version(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertEqual(files.next_version(d, "diagnosis-scoring-x"), 1)
            (d / "diagnosis-scoring-x-v1.md").write_text("a", encoding="utf-8")
            (d / "diagnosis-scoring-x-v3.md").write_text("c", encoding="utf-8")
            self.assertEqual(files.next_version(d, "diagnosis-scoring-x"), 4)


class TestWriteScoringArtifact(unittest.TestCase):
    """G1-02：write_scoring_artifact 生成 confirmed scoring md + 同步 state。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_artifact_and_sync_state(self):
        path = files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "diagnosis-scoring-gate-topic-v1.md")

        # 文件校验：frontmatter + hash 复算 + confirmation 强一致
        art = files.read_artifact(path)
        self.assertTrue(art.valid, art.errors)
        meta = art.meta
        self.assertEqual(meta["artifact_type"], "diagnosis-scoring")
        self.assertEqual(meta["artifact_id"], "diagnosis.scoring.current")
        self.assertEqual(meta["status"], "confirmed")
        self.assertEqual(meta["confirmation"]["confirmed_by"], "user")
        self.assertEqual(meta["confirmation"]["confirmed_content_hash"], meta["content_hash"])

        # state 同步：scoring_config + manifest
        reloaded = state_mod.load_state(self.topic_dir / "state.json")
        self.assertEqual(reloaded["scoring_config"]["blockThreshold"], 2.0)
        entry = reloaded["artifacts"]["diagnosis.scoring.current"]
        self.assertEqual(entry["version"], 1)
        self.assertEqual(entry["status"], "confirmed")
        self.assertEqual(entry["content_hash"], meta["content_hash"])
        self.assertEqual(entry["depends_on"], [])
        self.assertEqual(entry["confirmed_by"], "user")

    def test_version_not_overwritten(self):
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        path2 = files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        self.assertEqual(path2.name, "diagnosis-scoring-gate-topic-v2.md")
        self.assertTrue((self.topic_dir / "modules" / "diagnosis-scoring-gate-topic-v1.md").exists())


class TestCheckRequiredStep01(unittest.TestCase):
    """G1-03：step:01 前置 gate 校验（负例全覆盖）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "gate-proj", "Gate 项目", "gate-topic", "Gate 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")

    def tearDown(self):
        self._tmp.cleanup()

    def _place(self, src: str, dest_name: str) -> Path:
        """把夹具 md 复制进 topic 目录（路径与 manifest 一致）。"""
        dest = self.topic_dir / "modules" / dest_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ARTIFACTS / src, dest)
        return dest

    def _ok(self, result: dict):
        self.assertTrue(result["ok"], result)

    def test_missing_manifest_index(self):
        """文件存在但未登记 manifest → missing（§12.7 负例 7）。"""
        self._place("scoring-valid-confirmed.md", "diagnosis-scoring-gate-topic-v1.md")
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["missing"])
        self.assertFalse(result["ok"])

    def test_missing_file(self):
        """manifest 有索引但文件不存在 → missing（§12.7 负例 6）。"""
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": "sha256:" + "0" * 64,
            "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["missing"])

    def test_missing_confirmation(self):
        """自然语言确认留痕但无 confirmation 元数据 → invalid（§12.7 负例 3）。"""
        self._place("scoring-missing-confirmation.md", "diagnosis-scoring-gate-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": "x", "depends_on": [],
            "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["invalid"])
        self.assertFalse(result["ok"])

    def test_bad_hash(self):
        """content_hash 与正文不符 → invalid（§12.7 负例 5）。"""
        path = self._place("scoring-bad-hash.md", "diagnosis-scoring-gate-topic-v1.md")
        art = files.read_artifact(path)
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": art.meta["content_hash"],
            "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["invalid"])
        self.assertFalse(result["ok"])

    def test_confirmed_by_not_user(self):
        """confirmation.confirmed_by != user → invalid（§12.7 负例 4）。"""
        path = self._place("scoring-agent-confirmed.md", "diagnosis-scoring-gate-topic-v1.md")
        art = files.read_artifact(path)
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": art.meta["content_hash"],
            "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["invalid"])

    def test_manifest_stale(self):
        """manifest 标记 stale → stale（§12.7 负例 8 前置）。"""
        path = self._place("scoring-valid-confirmed.md", "diagnosis-scoring-gate-topic-v1.md")
        art = files.read_artifact(path)
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "stale", "content_hash": art.meta["content_hash"],
            "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["stale"])
        self.assertFalse(result["ok"])

    def test_source_refs_stale_detection(self):
        """source_refs 指向旧版本 → stale（§12.7 负例 8 的判定逻辑；G2-03 接入 step:02 后整体覆盖）。"""
        manifest = {
            "diagnosis.scoring.current": {"version": 2, "status": "confirmed"},
        }
        self.assertTrue(files._refs_stale(["diagnosis.scoring.current@v1"], manifest))
        self.assertFalse(files._refs_stale(["diagnosis.scoring.current@v2"], manifest))
        self.assertFalse(files._refs_stale([], manifest))

    def test_mark_stale_dependents(self):
        """G0-05：scoring v2 生成后，depends_on 引用 scoring@v1 的下游标记 stale。"""
        manifest = {
            "diagnosis.scoring.current": {"version": 2, "status": "confirmed", "depends_on": []},
            "diagnosis.dimension.v.current": {"version": 1, "status": "confirmed",
                                              "depends_on": ["diagnosis.scoring.current@v1"]},
            "diagnosis.dimension.i.current": {"version": 1, "status": "confirmed",
                                              "depends_on": ["diagnosis.scoring.current@v2"]},
        }
        state = {"artifacts": manifest}
        marked = files.mark_stale_dependents("diagnosis.scoring.current", 2, state)
        self.assertIn("diagnosis.dimension.v.current", marked)
        self.assertNotIn("diagnosis.dimension.i.current", marked)
        self.assertEqual(manifest["diagnosis.dimension.v.current"]["status"], "stale")
        self.assertEqual(manifest["diagnosis.dimension.i.current"]["status"], "confirmed")

    def test_manifest_hash_mismatch(self):
        """manifest 与文件 hash 不一致 → mismatched（§10 一致性）。"""
        path = self._place("scoring-valid-confirmed.md", "diagnosis-scoring-gate-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-gate-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": "sha256:" + "c" * 64,
            "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})
        result = files.check_required("step:01", self.state, self.topic_dir)
        self.assertIn("diagnosis.scoring.current", result["mismatched"])
        self.assertFalse(result["ok"])

    def test_happy_path(self):
        """confirmed scoring md 完整 → step:01 通过。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        result = files.check_required("step:01", self.state, self.topic_dir)
        self._ok(result)


class TestRunStepGate(unittest.TestCase):
    """G1-03：run_step 接入 file gate（G0-04 全路径强制）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_run_step_01_blocked_without_scoring_md(self):
        """直接 run_step("01") 但无 confirmed scoring md → FileGateError（§12.7 负例 1）。"""
        state, method = make_gate_session(self.tmp)
        with self.assertRaises(FileGateError) as ctx:
            run_step(state, method, "01", self.tmp / "gate-proj" / "gate-topic" / "modules" / "step01.md",
                     {"core_ok": True}, session_dir=self.tmp / "gate-proj" / "gate-topic")
        self.assertIn("缺失", str(ctx.exception))

    def test_run_step_requires_session_dir(self):
        """file gate 方法不传 session_dir → 拒绝执行（防绕过）。"""
        state, method = make_gate_session(self.tmp)
        with self.assertRaises(Exception) as ctx:
            run_step(state, method, "01", "step01.md", {"core_ok": True})
        self.assertIn("session_dir", str(ctx.exception))

    def test_run_step_01_passes_with_scoring_md(self):
        """写入 confirmed scoring md 后 run_step("01") → pass。"""
        state, method = make_gate_session(self.tmp)
        topic_dir = self.tmp / "gate-proj" / "gate-topic"
        files.write_scoring_artifact(topic_dir, SCORING_CONFIG, CONFIRMATION, state=state)
        out = topic_dir / "modules" / "step01.md"
        r = run_step(state, method, "01", out, {"core_ok": True}, session_dir=topic_dir)
        self.assertEqual(r["status"], "pass")

    def test_vision_method_unaffected(self):
        """非 fileGate 方法（vision mock）不传 session_dir 正常执行（G1 出口：vision 不受影响）。"""
        method, errors = parser.parse_manifest(VISION_MANIFEST)
        self.assertEqual(errors, [])
        state = state_mod.new_state("mock-proj", "Mock 项目", "mock-topic", "Mock Topic")
        begin(method, state)
        r = run_step(state, method, "01", self.tmp / "step01.md", {"core_ok": True})
        self.assertEqual(r["status"], "pass")


class TestMergeScoringRules(unittest.TestCase):
    """G1-05：打分规则来源合并（user-upload / system-default / mixed，不静默补齐）。"""

    DEFAULT = {
        "scale": {"min": 1, "max": 5, "step": 0.5},
        "blockThreshold": 2.0,
        "anchors": {"V": {"V1": "默认V1", "V2": "默认V2"}, "I": {"I1": "默认I1"}},
    }

    def test_system_default(self):
        r = files.merge_scoring_rules(None, self.DEFAULT)
        self.assertEqual(r["source"], "system-default")
        self.assertEqual(r["missing_angles"], ["V1", "V2", "I1"])
        self.assertEqual(r["conflicts"], [])

    def test_user_upload_full(self):
        user = {
            "scale": {"min": 1, "max": 5, "step": 0.5},
            "blockThreshold": 2.0,
            "anchors": {"V": {"V1": "用户V1", "V2": "用户V2"}, "I": {"I1": "用户I1"}},
        }
        r = files.merge_scoring_rules(user, self.DEFAULT)
        self.assertEqual(r["source"], "user-upload")
        self.assertEqual(r["missing_angles"], [])
        self.assertEqual(r["merged"]["anchors"]["V"]["V1"], "用户V1")

    def test_partial_upload_mixed_no_silent_fill(self):
        """部分提供 → source=mixed，缺失角度列出且不静默补齐（P2-3 / §4.2 验收）。"""
        user = {"anchors": {"V": {"V1": "用户V1"}}}  # 只给 V1
        r = files.merge_scoring_rules(user, self.DEFAULT)
        self.assertEqual(r["source"], "mixed")
        self.assertIn("V2", r["missing_angles"])
        self.assertIn("I1", r["missing_angles"])
        # 未覆盖角度锚点仍用默认值（merged 可追踪），但必须回读确认后才可落盘
        self.assertEqual(r["merged"]["anchors"]["V"]["V2"], "默认V2")
        self.assertEqual(r["merged"]["anchors"]["V"]["V1"], "用户V1")

    def test_conflict_detected(self):
        """用户阈值与默认不一致 → conflicts 列出（回读确认）。"""
        user = {"blockThreshold": 1.5, "anchors": {"V": {"V1": "用户V1", "V2": "用户V2"},
                                                   "I": {"I1": "用户I1"}}}
        r = files.merge_scoring_rules(user, self.DEFAULT)
        self.assertEqual(r["source"], "user-upload")
        self.assertTrue(any("阻断阈值" in c for c in r["conflicts"]))

    def test_mixed_conflict_and_missing(self):
        user = {"blockThreshold": 1.5, "anchors": {"V": {"V1": "用户V1"}}}
        r = files.merge_scoring_rules(user, self.DEFAULT)
        self.assertEqual(r["source"], "mixed")
        self.assertTrue(r["conflicts"])
        self.assertIn("V2", r["missing_angles"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
