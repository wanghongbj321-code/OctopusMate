"""渲染质量闸门测试（2026-08-18 渲染改造：AI 生成 HTML 后唯一确定性校验点）。

- 正向样本：合规黑灰 HTML（含表格 pale 表头 + 2px 主色底线、内联 CSS）→ 审计通过（放行）
- 反向样本：各类违规（box-shadow/渐变/圆润胶囊/彩色/emoji/SVG/外链/脚本/外部字体/背景图）
  → 审计拦截——锁定「闸门能拦坏东西」，防止 audit_html.py 被改坏后放行违规产物
"""
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deliverable-render" / "scripts"))

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
        example = ROOT / "skills" / "deliverable-render" / "examples" / "vision-confirm-canvas.html"
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


class TestAuditHtmlToken(unittest.TestCase):
    """M2-03 token 无裸值 + 语义演进（accent 允许自定义色）。"""

    def test_token_bare_color_blocked(self):
        """token 集外裸值（#FF0000 不在黑灰 token 集）→ 拦截。"""
        self.assertTrue(audit(_inject(VALID_HTML, "div { color: #FF0000; }")))

    def test_token_inline_value_allowed(self):
        """内联 token 值（#1A1A1A = ink）允许（token 集内）。"""
        bad = VALID_HTML.replace("th { background: var(--block-bg);", "th { background: #F7F7F7;")
        self.assertEqual(audit(bad), [], "内联 token 值应通过")

    def test_accent_custom_color_allowed(self):
        """语义演进：accent token 允许模式自定义色（如深蓝金 #C9A227）。"""
        html = VALID_HTML.replace("</style>", "h1 { color: var(--accent); }\n</style>")
        # 使用带 accent 自定义色的 token 集（深蓝金 accent）
        colors = {
            "pageBg": "#FFFFFF", "blockBg": "#F7F7F7", "ink": "#1A1A1A",
            "inkStrong": "#2D2D2D", "inkSoft": "#6B6B6B", "inkMuted": "#808080",
            "line": "#D4D4D4", "accentLine": "#0E2A47", "accent": "#C9A227",
            "tableHeadBg": "#F1F1F1", "calloutBg": "#FAFAFA",
        }
        html2 = html.replace("</style>", "h1 { color: #C9A227; }\n</style>")
        self.assertEqual(audit(html2, token_colors=colors), [], "accent 自定义色应通过语义演进审计")

    def test_pattern_file_token_loaded(self):
        """--token 模式文件：解析 Design Token 块校验（黑灰模式）。"""
        pattern = ROOT / "skills" / "deliverable-render" / "visual-patterns" / "10-black-gray-professional.md"
        self.assertTrue(pattern.exists())
        self.assertEqual(audit(VALID_HTML, pattern_path=pattern), [])

    def test_bare_hex_short_form(self):
        """#abc 短 hex 归一化后仍应被 token 无裸值捕获。"""
        self.assertTrue(audit(_inject(VALID_HTML, "div { color: #f00; }")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
