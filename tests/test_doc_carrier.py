"""M5-05 文档载体合规检查（A8 载体部分）：中间产物全 markdown，交付物统一 HTML。

检查范围：artifacts/demo/*/ 演练产物 + 测试产生的 workshop 临时产物不查（不持久化）。
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "artifacts" / "demo"


class TestDocCarrier(unittest.TestCase):
    """A8 载体合规：交付物统一 HTML + 每个 HTML 有对应 MD 唯一事实源 + 中间产物 MD。"""

    def test_each_html_has_md_source(self):
        """每个 HTML 确认包有对应的 markdown 唯一事实源。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            htmls = sorted(d.glob("vision-confirm-*.html"))
            self.assertGreater(len(htmls), 0, f"{d.name} 应至少含一个 HTML 确认包")
            for html in htmls:
                md_name = html.stem + ".md"
                self.assertTrue((d / md_name).exists(), f"{d.name}/{md_name} 应存在（HTML 唯一事实源）")

    def test_intermediate_products_are_markdown(self):
        """artifacts 内不放置中间产物（演练产物只有 HTML 确认包 + 唯一 MD 事实源），不污染规范。
        验证：demo 目录下不应有 step-*.md / ns-*.md / gc-*.md 这类中间步骤产物。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            step_files = list(d.glob("step-*.md")) + list(d.glob("ns-*.md")) + list(d.glob("gc-*.md"))
            self.assertEqual(step_files, [], f"{d.name} 不应含中间步骤产物（步骤产物落 workshop/，demo 仅展示交付物）")

    def test_html_uses_inline_styles_no_external_resources(self):
        """交付物 HTML 内联 CSS，无外部样式表/脚本（离线可打印）。"""
        for d in (d for d in DEMO_DIR.iterdir() if d.is_dir()):
            for html in d.glob("vision-confirm-*.html"):
                content = html.read_text(encoding="utf-8")
                self.assertIn("<style>", content, f"{html.name} 应含内联 <style>")
                self.assertNotIn('<link rel="stylesheet"', content, "交付物不得依赖外部样式表")
                self.assertNotIn("<script", content, "交付物不得依赖 JS 渲染")


if __name__ == "__main__":
    unittest.main(verbosity=2)