"""M4 方法插件机制测试：安装 / 升级 / 卸载 / 切换 + 黄金圈演示方法出口校验（A4/A5）。

- A4：用 vision-method-template 可安装第三方方法并运行通过出口校验
- A5：方法切换不丢数据（产出物与未决项保留）
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import (  # noqa: E402
    executor,
    exit as exit_mod,
    install,
    open_issues,
    parser,
    registry,
    session,
    state as state_mod,
    switch,
)

GOLDEN_CIRCLE_MANIFEST = ROOT / "skills" / "methods" / "golden-circle" / "manifest.yaml"
OCTOPUS_MANIFEST = ROOT / "skills" / "methods" / "octopus-7step" / "manifest.yaml"
NORTH_STAR_MANIFEST = ROOT / "skills" / "methods" / "north-star" / "manifest.yaml"


class TestInstallLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.methods_dir = self.root / "skills" / "methods"

    def tearDown(self):
        self._tmp.cleanup()

    def test_install_from_template_and_validate(self):
        """A4：复制脚手架 → 填写 → 校验上架（安装流程可用）。"""
        result = install.install_from_template(
            methods_dir=self.methods_dir,
            template_dir=ROOT / "skills" / "methods" / "templates" / "vision-method-template",
            slug="my-method",
        )
        self.assertEqual(result["status"], "created")
        target = Path(result["target"])
        self.assertTrue((target / "manifest.yaml").exists())
        self.assertTrue((target / "SKILL.md").exists())
        self.assertTrue((target / "references" / "CHECKLIST.md").exists())

        # 填写：用黄金圈 manifest 内容替换（模拟用户填写）
        filled = GOLDEN_CIRCLE_MANIFEST.read_text(encoding="utf-8")
        (target / "manifest.yaml").write_text(filled, encoding="utf-8")

        v = install.validate_installed(methods_dir=self.methods_dir, slug="my-method")
        self.assertEqual(v["status"], "ok", v["errors"])
        self.assertEqual(v["method"]["displayName"], "黄金圈法")

    def test_upgrade_preserves_workshop_state(self):
        """升级：版本替换后仍可用；workshop state 数据保留（引擎层分离）。"""
        # 安装黄金圈到临时目录
        install.install_from_template(
            methods_dir=self.methods_dir, template_dir=ROOT / "skills" / "methods" / "templates" / "vision-method-template",
            slug="golden-circle",
        )
        (self.methods_dir / "golden-circle" / "manifest.yaml").write_text(
            GOLDEN_CIRCLE_MANIFEST.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # 建一个 workshop 会话（模拟已产生的数据）
        ws = self.root / "workshop"
        topic_dir = session.create_session(ws, "p", "P", "t", "T")

        # 升级到 v1.1.0
        import yaml

        new_manifest = yaml.safe_load(GOLDEN_CIRCLE_MANIFEST.read_text(encoding="utf-8"))
        new_manifest["version"] = "1.1.0"
        up = install.upgrade_method(methods_dir=self.methods_dir, slug="golden-circle", new_manifest=new_manifest)
        self.assertEqual(up["status"], "ok", up)
        self.assertEqual(up["version"], "1.1.0")
        # 升级后仍通过校验 + workshop 数据保留
        v = install.validate_installed(methods_dir=self.methods_dir, slug="golden-circle")
        self.assertEqual(v["status"], "ok")
        self.assertTrue((topic_dir / "state.json").exists(), "workshop state 必须保留")

    def test_uninstall_preserves_outputs(self):
        """卸载：目录移除；未决清单与产物保留在引擎层/workshop。"""
        install.install_from_template(
            methods_dir=self.methods_dir, template_dir=ROOT / "skills" / "methods" / "templates" / "vision-method-template",
            slug="golden-circle",
        )
        (self.methods_dir / "golden-circle" / "manifest.yaml").write_text(
            GOLDEN_CIRCLE_MANIFEST.read_text(encoding="utf-8"), encoding="utf-8"
        )
        ws = self.root / "workshop"
        topic_dir = session.create_session(ws, "p", "P", "t", "T")
        (topic_dir / "modules" / "step-01.md").write_text("# 历史产物\n", encoding="utf-8")

        un = install.uninstall_method(methods_dir=self.methods_dir, slug="golden-circle")
        self.assertEqual(un["status"], "ok")
        self.assertFalse((self.methods_dir / "golden-circle").exists(), "方法目录已移除")
        self.assertTrue((topic_dir / "modules" / "step-01.md").exists(), "产物必须保留")
        self.assertTrue((topic_dir / "state.json").exists(), "state 必须保留")


class TestSwitchMethod(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_switch_preserves_data(self):
        """A5：7 步法执行到中途（含未决项）→ 切换北极星法 → 数据保留、新方法可继续。"""
        topic_dir = session.create_session(self.ws, "p", "P", "t", "T")
        octopus, _ = parser.parse_manifest(OCTOPUS_MANIFEST)
        northstar, _ = parser.parse_manifest(NORTH_STAR_MANIFEST)
        state = state_mod.load_state(topic_dir / "state.json")
        executor.begin(octopus, state)

        # 7 步法执行步骤 01-03 + 步骤 04 有条件通过（登记未决项）
        for sid in ("01", "02", "03"):
            out = topic_dir / "modules" / f"step-{sid}.md"
            out.write_text(f"# 步骤 {sid} 产出\n", encoding="utf-8")
            executor.run_step(state, octopus, sid, out, {"core_ok": True})
            executor.advance(state, octopus)
        out4 = topic_dir / "modules" / "step-04.md"
        out4.write_text("# 步骤 04 产出\n", encoding="utf-8")
        r4 = executor.run_step(
            state, octopus, "04", out4,
            {"core_ok": True, "conditional": True, "note": "可取性待一线确认"},
        )
        self.assertEqual(len(state["open_issues"]), 1)
        artifacts_before = len(state["artifacts"])
        steps_before = len(state["steps"])

        # 切换 → 北极星法
        result = switch.switch_method(state, northstar, migrated_fields=["visionStatement"])
        self.assertEqual(result["kept"]["open_issues"], 1, "未决项必须保留")
        self.assertEqual(result["kept"]["artifacts"], artifacts_before, "产物索引必须保留")
        self.assertEqual(result["kept"]["old_steps"], steps_before, "旧方法步骤历史必须保留")
        self.assertEqual(state["method"], northstar.name)
        self.assertEqual(state["current_step"], "01")

        # 切换后可继续执行北极星法（不丢数据）
        r = executor.run_step(state, northstar, "01", topic_dir / "modules" / "ns-01.md", {"core_ok": True})
        self.assertEqual(r["status"], "pass")
        self.assertEqual(len(state["open_issues"]), 1, "切换前未决项仍保留")

    def test_switch_entry_step(self):
        """用户指定入口步骤（兜底②）。"""
        topic_dir = session.create_session(self.ws, "p", "P", "t", "T")
        octopus, _ = parser.parse_manifest(OCTOPUS_MANIFEST)
        northstar, _ = parser.parse_manifest(NORTH_STAR_MANIFEST)
        state = state_mod.load_state(topic_dir / "state.json")
        executor.begin(octopus, state)

        result = switch.switch_method(state, northstar, entry_step="03")
        self.assertEqual(state["current_step"], "03")
        self.assertEqual(result["current_step"], "03")

    def test_migrate_contract_fields(self):
        """阶段映射兜底①：契约字段完成度迁移（已有值不覆盖）。"""
        old_output = {"visionStatement": "旧方法愿景", "ambitionTable": [{"kpi": "A"}]}
        new_output = {"visionStatement": "新方法已填愿景"}  # 已有值
        migrated = switch.migrate_contract_fields(old_output, new_output)
        self.assertEqual(new_output["visionStatement"], "新方法已填愿景", "已有值不覆盖")
        self.assertEqual(new_output["ambitionTable"], [{"kpi": "A"}], "空字段被迁移")
        self.assertIn("ambitionTable", migrated)
        self.assertNotIn("visionStatement", migrated)


class TestGoldenCircleE2E(unittest.TestCase):
    """M4-05 演示方法验证：黄金圈 3 步跑通出口校验（A4）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_golden_circle_registered_and_passes_exit(self):
        """黄金圈在注册器列表中（M5-01 将校验）+ 3 步跑通出口校验。"""
        valid, errors = registry.scan_methods()
        self.assertEqual(errors, [])
        names = {m.name for m in valid}
        self.assertIn("vision-method-golden-circle", names, "黄金圈方法已注册（A4）")

        method, errs = parser.parse_manifest(GOLDEN_CIRCLE_MANIFEST)
        self.assertEqual(errs, [])
        self.assertEqual(len(method.steps), 3)

        topic_dir = session.create_session(self.ws, "demo", "Demo", "gc", "黄金圈愿景")
        state = state_mod.load_state(topic_dir / "state.json")
        executor.begin(method, state)
        for sid, core_ok in (("01", True), ("02", True), ("03", True)):
            out = topic_dir / "modules" / f"gc-{sid}.md"
            out.write_text(f"# 黄金圈步骤 {sid}\n", encoding="utf-8")
            r = executor.run_step(state, method, sid, out, {"core_ok": core_ok})
            self.assertEqual(r["status"], "pass")
            executor.advance(state, method)

        output = {
            "visionStatement": "成为客户首选的智能伙伴",
            "visionNarrative": "一页叙事稿……",
            "ambitionTable": [{"kpi": "NPS", "baseline": "40", "y1": "50", "y2": "60", "y3": "70", "owner": "CXO", "source": "调研"}],
            "ambitionRationale": {"depth": "业务转型", "scope": "核心体验", "scale": "全线", "speed": "3 年", "basis": "使命驱动", "resource_commitment": "预算 2000 万/年"},
            "impactSummary": {"organization": "体验中心", "capability": "使命驱动决策", "financial": "NPS 提升"},
            "downstreamInterfaces": {"roadmap": "能力路线图接口", "signatures": ["发起人：张总"]},
            "openIssues": [],
        }
        result = exit_mod.run_exit(output, method.output_contract["requires"], state)
        self.assertEqual(result["errors"], [], f"出口校验应通过（A4）：{result['errors']}")
        self.assertTrue(exit_mod.confirm(state, "pass")["authorized"])
        state_mod.transition(state, "finalized")
        self.assertEqual(state["status"], "finalized")


if __name__ == "__main__":
    unittest.main(verbosity=2)
