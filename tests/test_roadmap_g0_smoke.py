"""M0-01 smoke test：验证现有 G0 文件级 gate 能力（roadmap 域开发前的回归基线）。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M0-01
       internal/docs/dev-plan/VITAL 诊断功能开发计划-文件级gate优化方案.md（G0 已落地）

验证 G0 核心能力（每类 1-2 个关键断言，快速冒烟）：
1. canonical hash 规范化与内容敏感
2. frontmatter 解析（valid / invalid）
3. artifact 元数据校验（白名单 / 必填 / confirmed_by=user 结构合法）
4. write_scoring_artifact：confirmed md 生成 + state.json 同步 + 版本不覆盖
5. check_required("step:01")：正例通过；缺文件 / 缺 confirmation / bad hash /
   confirmed_by!=user / stale 均阻断
6. mark_stale_dependents：上游变更触发下游 stale
7. run_step 接入 file gate：无 confirmed 前置 → FileGateError；有前置 → pass
8. reconcile.rebuild_state_from_artifacts：从 confirmed md 重建 state
9. exit.confirm：无 formal 确认包直接授权 → AuthorizationError

结论：现有 G0 全部能力可用 → roadmap 域只需新增 adapter（差距清单见
     构建企业能力路线图-功能开发计划-M0-01-G0适配差距清单.md），不重写 G0。
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

from _engine import files, parser, reconcile, session, state as state_mod  # noqa: E402
from _engine.executor import FileGateError, begin, run_step  # noqa: E402
from _engine.exit import AuthorizationError, confirm  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
ARTIFACTS = FIXTURES / "artifacts"
GATE_MANIFEST = FIXTURES / "gate-diagnosis-method" / "manifest.yaml"

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:12:用户确认采用默认规则",
    "confirmation_text": "用户明确确认采用本版打分规则",
}

SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "anchors": {"V": {"V1": {1: "初步", 3: "全面", 5: "成熟"}}},
}


def make_session(tmp: Path):
    topic_dir = session.create_session(tmp, "m0-proj", "M0 项目", "m0-topic", "M0 主题")
    method, errors = parser.parse_manifest(GATE_MANIFEST)
    assert not errors, errors
    state = state_mod.load_state(topic_dir / "state.json")
    begin(method, state)
    return topic_dir, state, method


class SmokeHashAndParse(unittest.TestCase):
    """G0 基础：hash 规范化 + frontmatter 解析。"""

    def test_hash_stable_and_content_sensitive(self):
        self.assertEqual(files.content_hash("a\nb\n"), files.content_hash("a\r\nb  \r\n\n\n"))
        self.assertNotEqual(files.content_hash("1-5"), files.content_hash("1-6"))

    def test_frontmatter_parse(self):
        meta, body = files.split_frontmatter("---\nartifact_type: diagnosis-scoring\nversion: 1\n---\n\nbody")
        self.assertEqual(meta["artifact_type"], "diagnosis-scoring")
        meta2, _ = files.split_frontmatter("no-frontmatter")
        self.assertIsNone(meta2)


class SmokeArtifactMeta(unittest.TestCase):
    """G0 结构校验：白名单 / 必填 / confirmed_by 结构。"""

    def test_unknown_type_blocked(self):
        errors = files.validate_artifact_meta({"artifact_type": "nope"})
        self.assertTrue(any("白名单" in e for e in errors))

    def test_valid_confirmed_by_user(self):
        meta = {
            "artifact_type": "diagnosis-scoring", "artifact_id": "diagnosis.scoring.current",
            "version": 1, "status": "confirmed", "source_refs": [],
            "content_hash": "sha256:" + "0" * 64,
            "confirmation": {"status": "confirmed", "confirmed_by": "user",
                             "confirmed_at": "2026-08-20T14:00:00+08:00",
                             "interaction_ref": "x",
                             "confirmed_content_hash": "sha256:" + "0" * 64},
        }
        self.assertEqual(files.validate_artifact_meta(meta), [])


class SmokeWriteAndGate(unittest.TestCase):
    """G0 写入 + required artifacts 前置 gate（正例 + 负例）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = make_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _place(self, src: str, dest: str) -> None:
        shutil.copy2(ARTIFACTS / src, self.topic_dir / "modules" / dest)

    def test_write_artifact_sync_and_version(self):
        p1 = files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        self.assertTrue(p1.exists())
        art = files.read_artifact(p1)
        self.assertTrue(art.valid, art.errors)
        self.assertEqual(art.meta["confirmation"]["confirmed_by"], "user")
        self.assertEqual(art.meta["confirmation"]["confirmed_content_hash"], art.meta["content_hash"])
        p2 = files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        self.assertEqual(p2.name, "diagnosis-scoring-m0-topic-v2.md")
        self.assertTrue(p1.exists())  # 版本不覆盖

    def test_check_required_happy_path(self):
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertTrue(r["ok"], r)

    def test_check_required_blocks(self):
        # 缺文件 + 未登记 manifest → missing
        self._place("scoring-valid-confirmed.md", "diagnosis-scoring-m0-topic-v1.md")
        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("diagnosis.scoring.current", r["missing"])

    def test_agent_confirmed_blocked(self):
        # 伪造确认：confirmed_by != user → invalid
        self._place("scoring-agent-confirmed.md", "diagnosis-scoring-m0-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-m0-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": "x", "depends_on": [],
            "created_at": "2026-08-20T14:00:00+08:00"})
        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("diagnosis.scoring.current", r["invalid"])

    def test_bad_hash_blocked(self):
        self._place("scoring-bad-hash.md", "diagnosis-scoring-m0-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-m0-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": "sha256:" + "0" * 64, "depends_on": [],
            "created_at": "2026-08-20T14:00:00+08:00"})
        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("diagnosis.scoring.current", r["invalid"])

    def test_stale_blocked(self):
        self._place("scoring-valid-confirmed.md", "diagnosis-scoring-m0-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-m0-topic-v1.md", "version": 1,
            "status": "stale", "content_hash": "x", "depends_on": [],
            "created_at": "2026-08-20T14:00:00+08:00"})
        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("diagnosis.scoring.current", r["stale"])

    def test_mark_stale_dependents(self):
        manifest = {
            "diagnosis.scoring.current": {"version": 2, "status": "confirmed", "depends_on": []},
            "diagnosis.dimension.v.current": {"version": 1, "status": "confirmed",
                                              "depends_on": ["diagnosis.scoring.current@v1"]},
            "diagnosis.dimension.i.current": {"version": 1, "status": "confirmed",
                                              "depends_on": ["diagnosis.scoring.current@v2"]},
        }
        marked = files.mark_stale_dependents("diagnosis.scoring.current", 2, {"artifacts": manifest})
        self.assertIn("diagnosis.dimension.v.current", marked)
        self.assertNotIn("diagnosis.dimension.i.current", marked)
        self.assertEqual(manifest["diagnosis.dimension.v.current"]["status"], "stale")


class SmokeRunStepFileGate(unittest.TestCase):
    """G0-04：run_step 全路径强制（绕过 advance 同样被阻断）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_run_step_blocked_without_prereq(self):
        topic_dir, state, method = make_session(self.tmp)
        with self.assertRaises(FileGateError):
            run_step(state, method, "01", topic_dir / "modules" / "step01.md",
                     {"core_ok": True}, session_dir=topic_dir)

    def test_run_step_passes_with_prereq(self):
        topic_dir, state, method = make_session(self.tmp)
        files.write_scoring_artifact(topic_dir, SCORING_CONFIG, CONFIRMATION, state=state)
        r = run_step(state, method, "01", topic_dir / "modules" / "step01.md",
                     {"core_ok": True}, session_dir=topic_dir)
        self.assertEqual(r["status"], "pass")


class SmokeReconcileAndAuthorize(unittest.TestCase):
    """G0：reconcile 重建 + 出口授权阻断。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = make_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reconcile_rebuild_state(self):
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        broken = {"artifacts": {}}
        rebuilt = reconcile.rebuild_state_from_artifacts(self.topic_dir, broken)
        self.assertEqual(rebuilt["artifacts"]["diagnosis.scoring.current"]["status"], "confirmed")

    def test_confirm_requires_formal_package(self):
        # 已走 confirmed md 链（scoring confirmed）但无 formal 确认包 → 授权阻断
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        with self.assertRaises(AuthorizationError):
            confirm(self.state, "pass", session_dir=self.topic_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
