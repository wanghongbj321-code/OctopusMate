"""M3 验收测试：资产包渲染（LLM 生成路线）——audit 对账闸门 + 演练资产包。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M3-01 ~ M3-05
      （LLM 生成方向，2026-08-20 用户拍板；Python 只做审计不参与生成）
      重构依据：internal/docs/debug/渲染重构计划-资产包LLM生成-20260820.md

覆盖（对齐 2026-08-18 测试原则：不假装覆盖 LLM 渲染质量，只锁闸门拦截能力）：
- 正向：演练资产包（LLM 生成的 7 文件，artifacts/demo/capability-roadmap-e2e/）
  通过 check_capability_package 包对账（7 文件 / 相对路径 / 信息比对 / Illustrative / token / 13 条不变量）
- 反向：缺文件 / 缺 Illustrative / 信息不一致 / 外链 → 拦截
- 无 --source-md：只算视觉审计不计交付 gate（main 逻辑）
- _package_expected_tokens：结构化数据块 → 对账 token 提取
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

from audit_html import (  # noqa: E402
    PACKAGE_REL_FILES,
    _package_expected_tokens,
    check_capability_package,
)

# 演练资产包（LLM 生成的 7 文件，作为正向 fixture；M3-05 演练产物）
DEMO_ROOT = ROOT / "artifacts" / "demo" / "capability-roadmap-e2e" / "capability-roadmap-e2e" / "e2e-topic"
DEMO_PACKAGE = DEMO_ROOT / "output" / "capability-roadmap-package-e2e-topic-v1"
DEMO_MODULES = DEMO_ROOT / "modules"

from _engine import roadmap  # noqa: E402  (用于提取结构化数据块)


class TestPackageExpectedTokens(unittest.TestCase):
    """_package_expected_tokens：结构化数据块 → 对账 token 提取（M3-04 机器比对依据）。"""

    def test_step01_tokens(self):
        ra = roadmap.read_roadmap_artifact(DEMO_MODULES / "capability-model-e2e-topic-v1.md")
        data = roadmap.extract_data_block(ra.artifact.body)
        tokens = _package_expected_tokens(data, "01")
        for t in ("pass", "1", "2", "C1", "Core"):
            self.assertIn(t, tokens, f"阶段 01 应含对账 token {t!r}")

    def test_step06_tokens_include_o7_and_milestones(self):
        ra = roadmap.read_roadmap_artifact(DEMO_MODULES / "capability-roadmap-e2e-topic-v1.md")
        data = roadmap.extract_data_block(ra.artifact.body)
        tokens = _package_expected_tokens(data, "06")
        for t in ("pass", "3", "M1", "G1", "D1", "M", "G", "D", "1", "夯实基本盘",
                  "增长与规模化", "再定位与重塑", "端到端方案", "目标运营模式",
                  "详细实施计划", "Benefit Case", "企业架构", "组合治理"):
            self.assertIn(t, tokens, f"阶段 06 应含对账 token {t!r}")


class TestPackageAuditPositive(unittest.TestCase):
    """正向：演练资产包（LLM 生成）通过包对账。"""

    def test_demo_package_passes_full_reconciliation(self):
        violations = check_capability_package(DEMO_PACKAGE, DEMO_MODULES, token_colors=None)
        self.assertEqual(violations, [], f"演练资产包应对账通过：{violations}")

    def test_demo_package_has_seven_files(self):
        for rel in PACKAGE_REL_FILES:
            self.assertTrue((DEMO_PACKAGE / rel).exists(), f"缺 {rel}")

    def test_single_source_md_reconciliation(self):
        """--source-md 传单文件（阶段 01）→ 仅比对该页信息（+ 包结构）。"""
        violations = check_capability_package(
            DEMO_PACKAGE, DEMO_MODULES / "capability-model-e2e-topic-v1.md", token_colors=None)
        self.assertEqual(violations, [], f"单 md 对账应通过：{violations}")


class TestPackageAuditNegative(unittest.TestCase):
    """反向：闸门必须拦截（缺文件 / 信息不一致 / 缺 Illustrative / 外链）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        shutil.copytree(DEMO_PACKAGE, self.tmp / "pkg")

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_blocked(self):
        (self.tmp / "pkg" / "06-capability-roadmap" / "index.html").unlink()
        violations = check_capability_package(self.tmp / "pkg", DEMO_MODULES, token_colors=None)
        self.assertTrue(any("缺文件" in v for v in violations), violations)

    def test_missing_illustrative_blocked(self):
        p = self.tmp / "pkg" / "01-capability-model" / "index.html"
        text = p.read_text(encoding="utf-8").replace("Illustrative", "")
        p.write_text(text, encoding="utf-8")
        violations = check_capability_package(self.tmp / "pkg", DEMO_MODULES, token_colors=None)
        self.assertTrue(any("Illustrative" in v for v in violations), violations)

    def test_data_mismatch_blocked(self):
        """改掉阶段 03 页质量门状态 conditional → 与结构化数据块不一致被拦截。"""
        p = self.tmp / "pkg" / "03-priority-capabilities" / "index.html"
        text = p.read_text(encoding="utf-8").replace("conditional", "regress")
        p.write_text(text, encoding="utf-8")
        violations = check_capability_package(self.tmp / "pkg", DEMO_MODULES, token_colors=None)
        self.assertTrue(any("信息对账不一致" in v for v in violations), violations)

    def test_external_link_blocked(self):
        p = self.tmp / "pkg" / "index.html"
        text = p.read_text(encoding="utf-8").replace(
            'href="./01-capability-model/index.html"', 'href="https://example.com/x"')
        p.write_text(text, encoding="utf-8")
        violations = check_capability_package(self.tmp / "pkg", DEMO_MODULES, token_colors=None)
        self.assertTrue(any("外链" in v for v in violations), violations)

    def test_bad_source_md_blocked(self):
        """--source-md 非有效 confirmed md → 阻断。"""
        bad = self.tmp / "bad.md"
        bad.write_text("# 非契约文件\n无结构化数据块", encoding="utf-8")
        violations = check_capability_package(DEMO_PACKAGE, bad, token_colors=None)
        self.assertTrue(violations, "非法 source-md 应被阻断")


if __name__ == "__main__":
    unittest.main(verbosity=2)
