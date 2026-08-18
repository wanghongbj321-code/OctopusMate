"""渲染质量闸门测试（2026-08-18 渲染改造：AI 生成 HTML 后唯一确定性校验点）。

- 正向样本：合规黑灰 HTML（含表格 pale 表头 + 2px 主色底线、内联 CSS）→ 审计通过（放行）
- 反向样本：各类违规（box-shadow/渐变/圆润胶囊/彩色/emoji/SVG/外链/脚本/外部字体/背景图）
  → 审计拦截——锁定「闸门能拦坏东西」，防止 audit_html.py 被改坏后放行违规产物
"""
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "vision-render" / "scripts"))

from audit_html import audit  # noqa: E402

# 合规正向样本（黑灰规范：内联 CSS、pale 表头 + 2px 主色底线、灰度、无信号元素）
VALID_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>愿景确认包</title>
<style>
:root { --page-bg: #FFFFFF; --block-bg: #F7F7F7; --ink: #1A1A1A; --ink-deep: #2D2D2D; --ink-soft: #6B6B6B; --ink-muted: #808080; --border: #D4D4D4; }
body { background: var(--page-bg); color: var(--ink); }
th { background: var(--block-bg); border-bottom: 2px solid var(--ink); }
table { border-collapse: collapse; }
td { border-bottom: 1px solid var(--border); }
</style>
</head>
<body>
<h1>愿景确认包</h1>
<p>三年后的一天：客户自助下单……</p>
<table><tr><th>KPI</th><th>基线</th></tr><tr><td>订单处理周期</td><td>72h</td></tr></table>
</body>
</html>
"""


def _inject(html: str, snippet: str) -> str:
    """在 <style> 内注入违规片段（保持其他部分合规）。"""
    return html.replace("</style>", f"{snippet}\n</style>")


class TestAuditHtmlPositive(unittest.TestCase):
    """正向：合规产物放行（不误伤）。"""

    def test_valid_html_passes(self):
        self.assertEqual(audit(VALID_HTML), [], "合规黑灰 HTML 应通过审计")

    def test_examples_baseline_passes(self):
        """examples/ 版面参照基线必须持续合规（AI 生成产物质量基准）。"""
        example = ROOT / "skills" / "vision-render" / "examples" / "vision-confirm-canvas.html"
        self.assertTrue(example.exists(), "examples 基线应存在")
        violations = audit(example.read_text(encoding="utf-8"))
        self.assertEqual(violations, [], f"examples 基线违反不变量：{violations}")


class TestAuditHtmlNegative(unittest.TestCase):
    """反向：闸门必须拦截各类违规（防 audit_html.py 回归放行坏产物）。"""

    def test_box_shadow_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "div { box-shadow: 0 2px 4px #000; }")))

    def test_gradient_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "div { background: linear-gradient(#FFF, #CCC); }")))

    def test_rounded_pill_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "button { border-radius: 12px; }")))

    def test_color_signal_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "div { color: #FF0000; }")))

    def test_table_header_without_pale_bg_blocked(self):
        bad = VALID_HTML.replace("th { background: var(--block-bg);", "th { background: #FFFFFF;")
        self.assertTrue(audit(bad), "表头非 pale 背景应被拦截")

    def test_table_header_without_2px_line_blocked(self):
        bad = VALID_HTML.replace("border-bottom: 2px solid var(--ink);", "border-bottom: 1px solid var(--border);")
        self.assertTrue(audit(bad), "表头缺 2px 主色底线应被拦截")

    def test_svg_blocked(self):
        bad = VALID_HTML.replace("</body>", '<svg width="10" height="10"><circle r="5"/></svg></body>')
        self.assertTrue(audit(bad))

    def test_emoji_blocked(self):
        self.assertTrue(audit(VALID_HTML.replace("</body>", "<p>✅ 通过</p></body>")))

    def test_external_stylesheet_blocked(self):
        bad = VALID_HTML.replace('<style>', '<link rel="stylesheet" href="theme.css"><style>')
        self.assertTrue(audit(bad))

    def test_script_blocked(self):
        self.assertTrue(audit(VALID_HTML.replace("</body>", "<script>alert(1)</script></body>")))

    def test_external_font_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "@font-face { font-family: X; src: url(x.woff); }")))

    def test_background_image_blocked(self):
        self.assertTrue(audit(_inject(VALID_HTML, "div { background-image: url(bg.png); }")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
