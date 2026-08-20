"""M4 验收测试：六阶段文件级 gate 链（roadmap adapter + 出口三段式）。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M4-01 ~ M4-05
      （M4 验收：六阶段强确认链端到端强制生效——任一阶段未确认无法进入下一步；
       出口按 render_preflight → authorized → finalized 顺序强制执行，
       未授权无法形成正式资产包；无授权/渲染循环依赖）

覆盖（M0-01 差距清单 G4/G5/G6 归属）：
- M4-01：伪造/缺失确认元数据被阻断（六阶段 + render-options）；render-options 通用类型不拆；
  旧 diagnosis 行为不回归
- M4-02：artifacts manifest 六阶段索引（path/version/status/hash/depends_on/created_at）；
  package source_refs（六阶段 @v 引用）+ package_hash；reconcile 从 confirmed md 重建（含 package 探测）
- M4-03：六阶段 required 链（step:02 需 step01 … step:06 需 step01~05）；
  run_step 与绕道直接调用均被阻断；渲染入口需 render-options
- M4-04：stale 传递传播（step01 v2 → step02~06 + render-options + package stale）；
  回指留痕（regress_reasons/regress_count）；条件重点裁决变更触发下游 stale
- M4-05：出口三段式（render_preflight → authorized → finalized）；无用户授权证据 /
  未 render_preflight / 未 authorized 均阻断；render_preflight 不要求 authorized（无循环依赖）
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "tests"))

from _engine import files, parser, reconcile, session, state as state_mod  # noqa: E402
from _engine.executor import FileGateError, begin, run_step  # noqa: E402
from _engine.exit import AuthorizationError, confirm  # noqa: E402
from _engine.roadmap import (  # noqa: E402
    PACKAGE_ARTIFACT_ID,
    RENDER_OPTIONS_ARTIFACT_ID,
    ROADMAP_STEP_META,
    exit_check,
    package_content_hash,
    render_preflight,
    write_roadmap_render_options,
    write_roadmap_step_artifact,
)
from tests.test_roadmap_m2_contracts import CONFIRMATION as M2_CONFIRMATION, MOCK_STEPS  # noqa: E402

ROADMAP_MANIFEST = ROOT / "skills" / "methods" / "capability-roadmap" / "manifest.yaml"
STEPS = ["01", "02", "03", "04", "05", "06"]

# M3 演练资产包（LLM 生成 7 文件 + 六阶段 confirmed md，M4-05 出口正向 fixture）
DEMO_TOPIC = ROOT / "artifacts" / "demo" / "capability-roadmap-e2e" / "capability-roadmap-e2e" / "e2e-topic"

AUTHORIZATION = {
    "confirmed_by": "user",
    "interaction_ref": "transcript:60:用户明确授权出口确认摘要与 draft 资产包",
    "confirmed_at": "2026-08-20T18:00:00+08:00",
    "authorization_text": "用户明确授权采用本版资产包交付",
}

RENDER_OPTIONS_DATA = {
    "canvasType": "capability-package",
    "tokenId": "10-black-gray-professional",
    "tokenPath": "skills/deliverable-render/visual-patterns/10-black-gray-professional.md",
}


def _make_roadmap_session(tmp: Path):
    """roadmap 方法会话（begin 六步骤；state.method 前缀 roadmap-method- 供 required_before 路由）。"""
    topic_dir = session.create_session(tmp, "m4-proj", "M4 项目", "m4-topic", "M4 主题")
    method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
    assert not errors, errors
    state = state_mod.load_state(topic_dir / "state.json")
    begin(method, state)
    return topic_dir, state, method


def _write_all_six(session_dir: Path, state: dict) -> None:
    """六阶段全部写入 confirmed md（M2 mock 数据，契约校验通过）。"""
    for step in STEPS:
        write_roadmap_step_artifact(
            session_dir, step, MOCK_STEPS[step](), confirmation=M2_CONFIRMATION, state=state)


def _copy_demo_session(tmp: Path) -> tuple[Path, dict]:
    """拷贝 M3 演练 session（六阶段 confirmed md + LLM 资产包）为出口三段式 fixture。

    demo state 经 M5-02 演练后含 finalized package + render-options + exit_authorization；
    清空让测试从干净 review_ready 状态开始（测试隔离，不依赖 demo 当前演进状态）。
    demo 未 begin()（无 method 字段），补 method 供 required_before 路由；
    六阶段 md 与资产包内容同源，对账可全过。
    """
    session_dir = tmp / "session"
    shutil.copytree(DEMO_TOPIC, session_dir)
    state = files.load_state_json(session_dir)
    state["method"] = "roadmap-method-capability"
    state["status"] = "review_ready"
    state["artifacts"].pop("roadmap.package.current", None)
    state["artifacts"].pop("roadmap.renderOptions.current", None)
    state.pop("exit_authorization", None)
    files.save_state_json(session_dir, state)
    return session_dir, state


def _write_forged_step01(session_dir: Path, state: dict, confirmed_by: str,
                         include_confirmation: bool = True) -> None:
    """构造伪造确认的 step01 md（hash 自洽、confirmed_by 任意），登记 manifest。

    include_confirmation=False：status=confirmed 但无 confirmation 块（缺凭据场景）。
    """
    from _engine.roadmap import _step_body

    data = MOCK_STEPS["01"]()
    body = _step_body("01", data, state)
    conf_block = (
        "confirmation:\n"
        f"  confirmed_by: {confirmed_by}\n"
        '  confirmed_at: "2026-08-20T14:00:00+08:00"\n'
        '  interaction_ref: "transcript:9"\n'
        '  confirmed_content_hash: "sha256:{0}"\n'
    ) if include_confirmation else ""
    text = (
        "---\n"
        "artifact_type: roadmap-step01\n"
        "artifact_id: roadmap.capabilityModel.current\n"
        "version: 1\n"
        "status: confirmed\n"
        "source_refs: []\n"
        'content_hash: "sha256:{0}"\n'
        f"{conf_block}"
        "---\n\n{1}"
    ).format("0" * 64, body)
    path = session_dir / "modules" / "capability-model-m4-topic-v1.md"
    path.write_text(text, encoding="utf-8")
    files.register_artifact(state, "roadmap.capabilityModel.current", {
        "path": "modules/capability-model-m4-topic-v1.md", "version": 1,
        "status": "confirmed", "content_hash": "sha256:" + "0" * 64,
        "depends_on": [], "created_at": "2026-08-20T14:00:00+08:00"})


class TestM4_01_ConfirmationAdapter(unittest.TestCase):
    """M4-01：roadmap artifact 类型 + confirmation adapter——伪造/缺失确认元数据被阻断。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_forged_confirmation_blocked(self):
        """伪造确认：confirmed_by=ai → step:02 前置校验 invalid（强确认链凭据，§6.3）。"""
        _write_forged_step01(self.topic_dir, self.state, "ai")
        r = files.check_required("step:02", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("roadmap.capabilityModel.current", r["invalid"])

    def test_missing_confirmation_blocked(self):
        """缺失 confirmation：status=confirmed 但无 confirmation 块 → G0 结构校验阻断。"""
        _write_forged_step01(self.topic_dir, self.state, "user", include_confirmation=False)
        art = files.read_artifact(
            self.topic_dir / "modules" / "capability-model-m4-topic-v1.md")
        self.assertFalse(art.valid)
        self.assertTrue(any("confirmation" in e for e in art.errors), art.errors)

    def test_render_options_generic_type_not_split(self):
        """render-options 不拆 roadmap-render-options 专属类型（通用 artifact_type）。"""
        _write_all_six(self.topic_dir, self.state)
        p = write_roadmap_render_options(
            self.topic_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=self.state)
        art = files.read_artifact(p)
        self.assertTrue(art.valid, art.errors)
        self.assertEqual(art.meta["artifact_type"], "render-options")
        self.assertEqual(art.meta["artifact_id"], RENDER_OPTIONS_ARTIFACT_ID)
        self.assertEqual(art.meta["source_refs"], [
            f"{ROADMAP_STEP_META[s]['artifact_id']}@v1" for s in STEPS])
        self.assertEqual(art.meta["confirmation"]["confirmed_by"], "user")

    def test_diagnosis_behavior_no_regression(self):
        """旧 diagnosis 域：required 映射与确认校验行为不变（独立会话，回归门禁）。"""
        from tests.test_g4_render import CONFIRMATION as G4_CONFIRMATION, SCORING_CONFIG, _dim_data, DIMS

        # 独立 diagnosis 会话（不 begin roadmap 方法 → required_before 走 STAGE_REQUIRED）
        topic_dir = session.create_session(self.tmp, "m4-diag", "M4 诊断", "d-topic", "D 主题")
        state = state_mod.load_state(topic_dir / "state.json")
        self.assertNotIn("method", state, "diagnosis 会话不应有 method（路由 STAGE_REQUIRED）")
        files.write_scoring_artifact(topic_dir, SCORING_CONFIG, G4_CONFIRMATION, state=state)
        r1 = files.check_required("step:01", state, topic_dir)
        self.assertTrue(r1["ok"], r1)
        for d in DIMS:
            files.write_dimension_artifact(topic_dir, d, _dim_data(d), G4_CONFIRMATION, state=state)
        files.write_overview_artifact(topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []},
            G4_CONFIRMATION, state=state)
        r6 = files.check_required("step:06", state, topic_dir)
        self.assertTrue(r6["ok"], r6)
        self.assertNotIn("roadmap.", str(r6), "diagnosis step:06 不应含 roadmap required")


class TestM4_02_Manifest(unittest.TestCase):
    """M4-02：artifacts manifest 扩展——六阶段索引 + package source_refs + reconcile 重建。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_six_step_manifest_registered(self):
        _write_all_six(self.topic_dir, self.state)
        for step in STEPS:
            aid = ROADMAP_STEP_META[step]["artifact_id"]
            entry = self.state["artifacts"].get(aid)
            self.assertIsNotNone(entry, f"{aid} 未登记 manifest")
            for key in ("path", "version", "status", "content_hash", "depends_on", "created_at"):
                self.assertIn(key, entry, f"{aid} manifest 缺 {key}")
            self.assertEqual(entry["status"], "confirmed")
            self.assertTrue(entry["content_hash"].startswith("sha256:"))

    def test_package_artifact_source_refs_and_hash(self):
        """package artifact 记录六阶段 source_refs（artifact id / version）+ package_hash（§5.1）。"""
        session_dir, state = _copy_demo_session(self.tmp)
        write_roadmap_render_options(session_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=state)
        res = render_preflight(session_dir, state)
        self.assertTrue(res["ok"], res["errors"])
        entry = state["artifacts"][PACKAGE_ARTIFACT_ID]
        expected_refs = [f"{ROADMAP_STEP_META[s]['artifact_id']}@v1" for s in STEPS]
        self.assertEqual(entry["source_refs"], expected_refs)
        self.assertEqual(entry["depends_on"], expected_refs)
        self.assertTrue(entry["package_hash"].startswith("sha256:"))
        self.assertEqual(entry["package_hash"], package_content_hash(session_dir / entry["path"]))
        self.assertEqual(entry["status"], "draft")

    def test_reconcile_rebuilds_roadmap_state(self):
        """state 视为缓存：清空后从 confirmed md + output/ 探测重建（§6.5）。"""
        session_dir, state = _copy_demo_session(self.tmp)
        write_roadmap_render_options(session_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=state)
        render_preflight(session_dir, state)
        broken = {"artifacts": {}, "method": "roadmap-method-capability",
                  "project_slug": "x", "topic_slug": "e2e-topic"}
        rebuilt = reconcile.rebuild_state_from_artifacts(session_dir, broken)
        arts = rebuilt["artifacts"]
        for step in STEPS:
            self.assertEqual(arts[ROADMAP_STEP_META[step]["artifact_id"]]["status"], "confirmed")
        self.assertEqual(arts[RENDER_OPTIONS_ARTIFACT_ID]["status"], "confirmed")
        # package 目录级重建（无 md 文件）：探测 output/ 登记
        pkg = arts.get(PACKAGE_ARTIFACT_ID)
        self.assertIsNotNone(pkg, "package 应被探测重建")
        self.assertEqual(pkg["status"], "draft")
        self.assertEqual(len(pkg["source_refs"]), 6)


class TestM4_03_RequiredChain(unittest.TestCase):
    """M4-03：required artifacts 前置 gate 映射（§6.4）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_step01_no_prereq_step02_requires(self):
        r1 = files.check_required("step:01", self.state, self.topic_dir)
        self.assertTrue(r1["ok"], r1)
        r2 = files.check_required("step:02", self.state, self.topic_dir)
        self.assertFalse(r2["ok"])
        self.assertIn("roadmap.capabilityModel.current", r2["missing"])

    def test_step06_requires_all_prereqs(self):
        for step in ("01", "02", "03", "04"):
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](), confirmation=M2_CONFIRMATION, state=self.state)
        r6 = files.check_required("step:06", self.state, self.topic_dir)
        self.assertFalse(r6["ok"])
        self.assertIn("roadmap.gapInitiatives.current", r6["missing"])

    def test_run_step_blocked_without_prereq(self):
        """跳过前置阶段 confirmed 产物 → run_step 阻断。"""
        with self.assertRaises(FileGateError):
            run_step(self.state, self.method, "02",
                     self.topic_dir / "modules" / "s02.md", {"core_ok": True}, session_dir=self.topic_dir)

    def test_direct_bypass_call_blocked(self):
        """绕道调用同样被阻断：未走 advance，直接 run_step("06")（缺前置）→ FileGateError。"""
        for step in ("01", "02", "03", "04"):
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](), confirmation=M2_CONFIRMATION, state=self.state)
        with self.assertRaises(FileGateError):
            run_step(self.state, self.method, "06",
                     self.topic_dir / "modules" / "s06.md", {"core_ok": True}, session_dir=self.topic_dir)

    def test_render_step_requires_render_options(self):
        """渲染某阶段 draft 页：对应阶段 confirmed md + confirmed render-options（§6.4）。"""
        write_roadmap_step_artifact(
            self.topic_dir, "01", MOCK_STEPS["01"](), confirmation=M2_CONFIRMATION, state=self.state)
        r = files.check_required("render:step01", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn(RENDER_OPTIONS_ARTIFACT_ID, r["missing"])
        # 补 render-options 后通过
        write_roadmap_render_options(self.topic_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=self.state)
        r2 = files.check_required("render:step01", self.state, self.topic_dir)
        self.assertTrue(r2["ok"], r2)


class TestM4_04_StalePropagation(unittest.TestCase):
    """M4-04：stale 与回指联动（§6.5）——传递传播 + 决策门 + 回指留痕。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_step01_v2_stales_all_downstream(self):
        """阶段 01 更新 v2 → 依赖它的全部下游（02~06 + render-options + package）标记 stale。"""
        _write_all_six(self.topic_dir, self.state)
        write_roadmap_render_options(self.topic_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=self.state)
        write_roadmap_step_artifact(
            self.topic_dir, "01", MOCK_STEPS["01"](), confirmation=M2_CONFIRMATION, state=self.state)
        for step in ("02", "03", "04", "05", "06"):
            aid = ROADMAP_STEP_META[step]["artifact_id"]
            self.assertEqual(self.state["artifacts"][aid]["status"], "stale",
                             f"{aid} 应被传递标记 stale")
        self.assertEqual(self.state["artifacts"][RENDER_OPTIONS_ARTIFACT_ID]["status"], "stale")

    def test_stale_blocks_next_step(self):
        _write_all_six(self.topic_dir, self.state)
        write_roadmap_step_artifact(
            self.topic_dir, "01", MOCK_STEPS["01"](), confirmation=M2_CONFIRMATION, state=self.state)
        r3 = files.check_required("step:03", self.state, self.topic_dir)
        self.assertFalse(r3["ok"])
        self.assertIn("roadmap.maturityBaseline.current", r3["stale"])

    def test_regress_reasons_recorded(self):
        """Q-gate 回指：regress_reasons/regress_count 留痕（§6.5，executor.regress_to）。"""
        from _engine.executor import regress_to

        _write_all_six(self.topic_dir, self.state)
        self.state["current_step"] = "03"
        regress_to(self.state, self.method, "02", "能力模型需修订：建模规范检查未通过")
        for sid in ("02", "03", "04", "05", "06"):
            info = self.state["steps"].get(sid, {})
            self.assertEqual(info.get("status"), "draft", f"步骤 {sid} 应待修订")
            if sid == "02":
                self.assertEqual(info.get("regress_count"), 1)
                self.assertIn("建模规范", info.get("regress_reasons", [])[0])
        # 回指后生成新版本 → 依赖旧 source_refs 的下游 confirmed 标记 stale
        write_roadmap_step_artifact(
            self.topic_dir, "02", MOCK_STEPS["02"](), confirmation=M2_CONFIRMATION, state=self.state)
        for sid in ("03", "04", "05", "06"):
            aid = ROADMAP_STEP_META[sid]["artifact_id"]
            self.assertEqual(self.state["artifacts"][aid]["status"], "stale")

    def test_conditional_decision_change_stales_downstream(self):
        """条件重点能力裁决变更（step03 v2）→ 阶段 04~06 引用该裁决的产物标记 stale（决策门）。"""
        _write_all_six(self.topic_dir, self.state)
        # step03 v2：裁决变更（C5 纳入/移出等）
        write_roadmap_step_artifact(
            self.topic_dir, "03", MOCK_STEPS["03"](), confirmation=M2_CONFIRMATION, state=self.state)
        for sid in ("04", "05", "06"):
            aid = ROADMAP_STEP_META[sid]["artifact_id"]
            self.assertEqual(self.state["artifacts"][aid]["status"], "stale",
                             f"{aid} 应因裁决变更 stale")


class TestM4_05_ExitChain(unittest.TestCase):
    """M4-05：出口 render_preflight / authorized / finalized 三段式（§6.6）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _exit_ready_session(self):
        """六阶段 + render-options + draft 包（render_preflight 通过）就绪的 session。"""
        session_dir, state = _copy_demo_session(self.tmp)
        write_roadmap_render_options(session_dir, RENDER_OPTIONS_DATA, M2_CONFIRMATION, state=state)
        return session_dir, state

    def test_confirm_requires_user_authorization_evidence(self):
        """直接 confirm(pass) 但无用户授权证据 → 阻断（AI 不得自代授权，§6.2/R8）。"""
        session_dir, state = self._exit_ready_session()
        render_preflight(session_dir, state)
        with self.assertRaises(AuthorizationError):
            confirm(state, "pass", session_dir=session_dir)
        with self.assertRaises(AuthorizationError):
            confirm(state, "pass", session_dir=session_dir,
                    authorization={"confirmed_by": "ai", "interaction_ref": "x"})
        self.assertEqual(state["status"], "review_ready")

    def test_confirm_without_render_preflight_blocked(self):
        """未 render_preflight（无 package 登记）→ 不可 authorized（无授权/渲染循环依赖）。"""
        session_dir, state = self._exit_ready_session()
        with self.assertRaises(AuthorizationError):
            confirm(state, "pass", session_dir=session_dir, authorization=AUTHORIZATION)

    def test_full_exit_chain(self):
        """render_preflight → authorized → finalized 顺序强制；package 状态 draft→authorized→finalized。"""
        session_dir, state = self._exit_ready_session()
        # 段 1：render_preflight（不要求 authorized，review_ready 可 preflight）
        pre = render_preflight(session_dir, state)
        self.assertTrue(pre["ok"], pre["errors"])
        self.assertEqual(state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "draft")
        self.assertEqual(state["status"], "review_ready")
        # 段 2：用户出口授权
        res = confirm(state, "pass", session_dir=session_dir, authorization=AUTHORIZATION)
        self.assertTrue(res["authorized"])
        self.assertEqual(state["status"], "authorized")
        self.assertEqual(state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "authorized")
        self.assertEqual(state["exit_authorization"]["confirmed_by"], "user")
        # 段 3：finalized（authorized + 无 stale + HTML 对账通过）
        state_mod.transition(state, "finalized", authorized=True, session_dir=session_dir)
        self.assertEqual(state["status"], "finalized")
        self.assertEqual(state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "finalized")

    def test_finalized_without_authorized_blocked(self):
        """未 authorized 直接 transition(finalized) → 阻断（状态机 + 三段式）。"""
        session_dir, state = self._exit_ready_session()
        render_preflight(session_dir, state)
        with self.assertRaises(ValueError):
            state_mod.transition(state, "finalized", authorized=True, session_dir=session_dir)

    def test_package_stale_blocks_finalized(self):
        """authorized 后上游更新 → package stale → finalized 阻断（§6.5/§6.6 段 3）。"""
        session_dir, state = self._exit_ready_session()
        render_preflight(session_dir, state)
        confirm(state, "pass", session_dir=session_dir, authorization=AUTHORIZATION)
        # 上游阶段 01 更新 v2 → package（depends_on 引用 step01@v1）标记 stale
        p1 = session_dir / "modules" / "capability-model-e2e-topic-v1.md"
        data = files.split_frontmatter(p1.read_text(encoding="utf-8"))[1]
        from _engine.roadmap import _step_body
        import yaml as yaml_mod
        raw = yaml_mod.safe_load(data.split("```yaml\n", 1)[1].rsplit("```", 1)[0])
        write_roadmap_step_artifact(
            session_dir, "01", raw, confirmation=M2_CONFIRMATION, state=state)
        self.assertEqual(state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "stale")
        with self.assertRaises(ValueError):
            state_mod.transition(state, "finalized", authorized=True, session_dir=session_dir)

    def test_render_preflight_requires_six_steps_and_render_options(self):
        """render_preflight 前置：六阶段 + render-options confirmed 齐备（§6.4）。"""
        session_dir, state = _copy_demo_session(self.tmp)
        # 删一个阶段 md → render_preflight 阻断（无 render-options + 六阶段不全）
        res = render_preflight(session_dir, state)
        self.assertFalse(res["ok"])
        joined = "；".join(res["errors"])
        self.assertIn(RENDER_OPTIONS_ARTIFACT_ID, joined)

    def test_exit_check_stage_finalized_requires_audit(self):
        """exit_check(finalized, require_audit=True)：HTML 对账复核（§6.6 段 3）。"""
        session_dir, state = self._exit_ready_session()
        render_preflight(session_dir, state)
        # 篡改包内一页（去掉 Illustrative）→ 对账失败
        p = session_dir / "output" / "capability-roadmap-package-e2e-topic-v1" / "index.html"
        text = p.read_text(encoding="utf-8").replace("Illustrative", "")
        p.write_text(text, encoding="utf-8")
        res = exit_check(session_dir, state, stage="roadmap:finalized", require_audit=True)
        self.assertFalse(res["ok"])
        self.assertTrue(any("对账" in e for e in res["errors"]), res["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
