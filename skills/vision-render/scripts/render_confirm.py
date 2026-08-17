#!/usr/bin/env python3
"""M2-06 确认包 HTML 渲染（vision-render）。

读取确认包 markdown 唯一事实源 → 按视觉模式渲染 HTML。
默认模式：10-black-gray-professional（黑灰专业）。业务内容全部来自确认包，
不凭空生成；视觉输出遵循 13 条 Pan-Mode Invariants（静态审计见 audit_html.py）。

用法：
    python3 render_confirm.py <confirm.md> <output.html> [pattern-id]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # skills/vision-render/scripts → 3 级到 ROOT
PATTERNS_DIR = ROOT / "skills" / "vision-render" / "visual-patterns"

DEFAULT_PATTERN = "10-black-gray-professional"

# 黑灰专业 token（与 10-black-gray-professional.md 一致）
TOKENS = {
    "page_bg": "#FFFFFF",
    "canvas_bg": "#FFFFFF",
    "block_bg": "#F7F7F7",
    "ink": "#1A1A1A",
    "ink_deep": "#2D2D2D",
    "ink_soft": "#6B6B6B",
    "ink_muted": "#808080",
    "border": "#D4D4D4",
    "accent_border": "#1A1A1A",
}

CSS = """
:root {
  --page-bg: {page_bg};
  --block-bg: {block_bg};
  --ink: {ink};
  --ink-deep: {ink_deep};
  --ink-soft: {ink_soft};
  --ink-muted: {ink_muted};
  --border: {border};
  --accent-border: {accent_border};
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html {{ background: var(--page-bg); }}
body {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
  color: var(--ink);
  background: var(--page-bg);
  line-height: 1.65;
  padding: 48px 24px;
}
.page {
  max-width: 860px;
  margin: 0 auto;
  background: var(--page-bg);
  border-top: 4px solid var(--ink);
  padding: 32px 8px 24px;
}
h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
  border-bottom: 2px solid var(--ink);
  padding-bottom: 10px;
  margin-bottom: 16px;
}
.meta {
  color: var(--ink-muted);
  font-size: 13px;
  margin-bottom: 28px;
}
h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink-deep);
  margin: 28px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
h3 { font-size: 15px; font-weight: 600; color: var(--ink); margin: 18px 0 8px; }
p { margin: 8px 0; color: var(--ink); }
strong { font-weight: 700; }
blockquote {
  margin: 10px 0;
  padding: 8px 14px;
  background: var(--block-bg);
  border-left: 3px solid var(--ink);
  color: var(--ink-deep);
}
ul, ol { margin: 8px 0 8px 22px; }
li { margin: 3px 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 13.5px;
}
th {
  background: var(--block-bg);
  color: var(--ink);
  font-weight: 600;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 2px solid var(--ink);
}
td {
  padding: 7px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--ink);
  vertical-align: top;
}
code {
  background: var(--block-bg);
  padding: 1px 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12.5px;
}
/* 13 条不变量底线：无 box-shadow / 无渐变 / 无圆润胶囊 / 无彩色信号 */
a { color: var(--ink); text-decoration: underline; }
"""


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def md_to_html(md_text: str) -> str:
    """轻量 markdown → HTML（覆盖确认包结构：标题/表格/列表/引用/段落）。"""
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    in_table = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 表格
        if stripped.startswith("|"):
            if not in_table:
                out.append("<table>")
                in_table = True
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells) and in_table:
                i += 1
                continue  # 分隔行，跳过
            tag = "th" if not in_table else "td"
            out.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
            i += 1
            continue
        if in_table:
            out.append("</table>")
            in_table = False

        if stripped == "":
            i += 1
            continue
        if stripped.startswith("### "):
            out.append(f"<h3>{_inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{_inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h1>{_inline(stripped[2:])}</h1>")
        elif stripped.startswith("> "):
            out.append(f"<blockquote>{_inline(stripped[2:])}</blockquote>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            out.append(f"<li>{_inline(stripped[2:])}</li>")
        elif re.match(r"^\d+\. ", stripped):
            out.append(f"<li>{_inline(re.sub(r'^\\d+\\. ', '', stripped))}</li>")
        else:
            out.append(f"<p>{_inline(stripped)}</p>")
        i += 1
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def render(md_path: Path, out_path: Path, pattern_id: str = DEFAULT_PATTERN) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    body = md_to_html(md_text)
    # 占位符替换（CSS 含花括号，不用 str.format）
    css = CSS
    for key, value in TOKENS.items():
        css = css.replace("{" + key + "}", value)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>愿景确认包</title>
<style>{css}</style>
</head>
<body>
<div class="page">
{body}
</div>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("用法：render_confirm.py <confirm.md> <output.html> [pattern-id]")
        return 2
    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    pattern = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_PATTERN
    render(md_path, out_path, pattern)
    print(f"[OK] 渲染完成：{md_path} → {out_path}（模式 {pattern}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
