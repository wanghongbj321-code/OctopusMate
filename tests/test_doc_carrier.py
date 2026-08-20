"""M5-05 文档载体合规检查（A8 载体部分）：中间产物全 markdown，交付物统一 HTML。

检查范围：artifacts/demo/*/ 演练产物 + 测试产生的 workshop 临时产物不查（不持久化）。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "artifacts" / "demo"


class TestDocCarrier(unittest.TestCase):
    """A8 载体合规：交付物统一 HTML + 每个 HTML 有对应 MD 唯一事实源 + 中间产物 MD。"""

    @staticmethod
    def _package_dirs(d: Path) -> list[Path]:
        """capability-roadmap 资产包目录（多文件包：index + 01~06 共 7 文件）。"""
        return [p for p in d.rglob("capability-roadmap-package-*") if p.is_dir()]

    def test_each_html_has_md_source(self):
        """每个 HTML 确认包有对应的 markdown 唯一事实源
        （vision-confirm / diagnosis-confirm 单文件；capability-roadmap-package 多文件包）。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            htmls = sorted(d.glob("vision-confirm-*.html")) + sorted(d.glob("diagnosis-confirm-*.html"))
            pkgs = self._package_dirs(d)
            self.assertGreater(len(htmls) + len(pkgs), 0, f"{d.name} 应至少含一个 HTML 交付物")
            for html in htmls:
                md_name = html.stem + ".md"
                self.assertTrue((d / md_name).exists(), f"{d.name}/{md_name} 应存在（HTML 唯一事实源）")
            # capability-package：7 文件包 + 六阶段 confirmed md 唯一事实源（M3-05）
            for pkg in pkgs:
                for rel in ("index.html", "01-capability-model/index.html", "02-baseline-maturity/index.html",
                            "03-priority-capabilities/index.html", "04-future-state/index.html",
                            "05-gap-initiatives/index.html", "06-capability-roadmap/index.html"):
                    self.assertTrue((pkg / rel).exists(), f"{pkg.relative_to(ROOT)} 缺 {rel}")
                session_dir = pkg.parent.parent if pkg.parent.name == "output" else None
                modules = sorted((session_dir / "modules").glob("*.md")) if session_dir else []
                self.assertGreaterEqual(len(modules), 6,
                                        f"{pkg.relative_to(ROOT)} 应存在六阶段 confirmed md 唯一事实源（modules/）")

    def test_intermediate_products_are_markdown(self):
        """artifacts 内不放置中间产物（演练产物只有 HTML 确认包 + 唯一 MD 事实源），不污染规范。
        验证：demo 目录下不应有 step-*.md / ns-*.md / gc-*.md 这类中间步骤产物。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            step_files = list(d.glob("step-*.md")) + list(d.glob("ns-*.md")) + list(d.glob("gc-*.md"))
            self.assertEqual(step_files, [], f"{d.name} 不应含中间步骤产物（步骤产物落 workshop/，demo 仅展示交付物）")

    def test_html_uses_inline_styles_no_external_resources(self):
        """交付物 HTML 内联 CSS，无外部样式表/脚本（离线可打印）。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            htmls = list(d.glob("vision-confirm-*.html")) + list(d.glob("diagnosis-confirm-*.html"))
            for pkg in self._package_dirs(d):
                htmls += [pkg / rel for rel in
                          ("index.html", "01-capability-model/index.html", "02-baseline-maturity/index.html",
                           "03-priority-capabilities/index.html", "04-future-state/index.html",
                           "05-gap-initiatives/index.html", "06-capability-roadmap/index.html")]
            for html in htmls:
                content = html.read_text(encoding="utf-8")
                self.assertIn("<style>", content, f"{html.name} 应含内联 <style>")
                self.assertNotIn('<link rel="stylesheet"', content, "交付物不得依赖外部样式表")
                self.assertNotIn("<script", content, "交付物不得依赖 JS 渲染")

    def test_diagnosis_canvas_audit_and_no_demo_leak(self):
        """M4-01：诊断报告画布通过 audit（token 无裸值 + 不变量）且 Demo 样例数值零泄漏。"""
        import sys

        canvas = ROOT / "skills" / "deliverable-render" / "examples" / "diagnosis-report-canvas.html"
        self.assertTrue(canvas.exists(), "diagnosis-report-canvas.html 应存在（M4-01 产出）")
        sys.path.insert(0, str(ROOT / "skills" / "deliverable-render" / "scripts"))
        from audit_html import audit

        content = canvas.read_text(encoding="utf-8")
        self.assertEqual(audit(content), [], f"画布应通过审计：{canvas.name}")
        # Demo 样例数值零泄漏（分数语义模式：2.9 分 / 3.4 分 等独立词）
        import re

        demo_pattern = re.compile(r"(2\.9|3\.4|2\.1|2\.7)\s*(分|%)")
        self.assertIsNone(demo_pattern.search(content), "画布不得含 Demo 样例数值（2.9 分 / 3.4 分 等）")
        self.assertNotIn("T+15", content)
        self.assertNotIn("快消品", content)
        self.assertNotIn("经销商", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)