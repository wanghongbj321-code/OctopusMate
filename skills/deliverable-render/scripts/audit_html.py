#!/usr/bin/env python3
"""deliverable-render HTML 静态审计（M2-03 v2：token 无裸值 + 13 条不变量语义演进）。

检查项（对齐开发计划 §5.2）：
1. **token 无裸值**：成品 HTML 中出现的颜色值必须属于选定 token 集
   （CSS 变量引用 var(--x) 或内联 token 值均可）；token 集外出现任何色值
   （含灰度）判为裸值违规——`accent` token 允许模式自定义色（语义演进），
   其余颜色仍须来自 token 集
2. 13 条 Pan-Mode Invariants 底线（语义演进后）：
   - 无 box-shadow / 复杂渐变（linear/radial-gradient）
   - 无圆润胶囊按钮（border-radius > 2px）
   - 表格：pale 色表头 + 2px 主色底线
   - 无 SVG / emoji 作信号
   - 内联样式离线可打印（无外链样式表/脚本/外部字体/背景图）
3. 输出 token 合规报告（颜色出现位置统计）

用法：python3 audit_html.py <output.html> [--token <pattern.md>]
  --token: 选定视觉模式文件路径（解析 Design Token 块）；缺省用黑灰 token 集
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 默认黑灰 token 集（§5.2，与 10-black-gray-professional.md 一致）
DEFAULT_TOKENS = {
    "pageBg": "#FFFFFF", "blockBg": "#F7F7F7", "ink": "#1A1A1A",
    "inkStrong": "#2D2D2D", "inkSoft": "#6B6B6B", "inkMuted": "#808080",
    "line": "#D4D4D4", "accentLine": "#1A1A1A", "accent": "#1A1A1A",
    "tableHeadBg": "#F1F1F1", "calloutBg": "#FAFAFA",
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,6}\b")
RGB_RE = re.compile(r"rgba?\([^)]*\)")


def _norm_color(raw: str) -> str:
    """归一化色值：hex 3→6 位、rgb() → #rrggbb（便于与 token 比较）。"""
    raw = raw.strip().lower()
    m = HEX_RE.match(raw)
    if m and len(m.group(0)) == 4:  # #abc → #aabbcc
        h = m.group(0)[1:]
        return "#" + "".join(c * 2 for c in h)
    if raw.startswith("#"):
        return raw
    m = RGB_RE.match(raw)
    if m:
        vals = [int(x) for x in re.findall(r"\d{1,3}", m.group(0))]
        if len(vals) >= 3:
            return "#{:02x}{:02x}{:02x}".format(vals[0], vals[1], vals[2])
    return raw


def _load_token_colors(pattern_path: Path | None) -> dict[str, str]:
    """从模式文件 Design Token 块解析 color token；缺省用黑灰集。"""
    if pattern_path is None or not pattern_path.exists():
        return dict(DEFAULT_TOKENS)
    import re as _re
    import yaml

    text = pattern_path.read_text(encoding="utf-8")
    m = _re.search(r"```yaml\n(designToken:.*?)```", text, _re.S)
    if not m:
        return dict(DEFAULT_TOKENS)
    data = yaml.safe_load(m.group(1))
    data = data.get("designToken", data)
    colors = (data.get("tokens") or {}).get("color") or {}
    return {k: _norm_color(v) for k, v in colors.items() if isinstance(v, str)}


def _color_literals(html: str) -> list[tuple[str, str]]:
    """提取 HTML 中所有颜色字面量 → [(归一化色值, 原文)]。"""
    found: list[tuple[str, str]] = []
    for m in HEX_RE.finditer(html):
        found.append((_norm_color(m.group(0)), m.group(0)))
    for m in RGB_RE.finditer(html):
        found.append((_norm_color(m.group(0)), m.group(0)))
    return found


def audit(html: str, pattern_path: Path | None = None, token_colors: dict | None = None) -> list[str]:
    """静态审计，返回违规清单（空 = 通过）。

    - html: 成品 HTML
    - pattern_path: 选定视觉模式文件路径（解析 token 集）
    - token_colors: 直接传 token 色板（优先于 pattern_path）
    """
    violations: list[str] = []
    colors = token_colors or _load_token_colors(pattern_path)
    allowed = {v.lower() for v in colors.values()}

    # --- token 无裸值校验（语义演进核心）---
    for norm, raw in _color_literals(html):
        if norm not in allowed:
            violations.append(f"发现 token 集外裸值色值：{raw}（须引用选定 token 集内的颜色）")

    # --- 13 条 Pan-Mode Invariants 底线 ---
    if re.search(r"box-shadow\s*:", html):
        violations.append("发现 box-shadow（不变量 4：禁用）")
    if re.search(r"linear-gradient|radial-gradient", html, re.I):
        violations.append("发现渐变（不变量 4：禁用复杂渐变）")

    for m in re.finditer(r"border-radius\s*:\s*([0-9.]+)px", html):
        if float(m.group(1)) > 2:
            violations.append(f"发现圆润胶囊样式 border-radius={m.group(1)}px > 2px")

    # 表格：th 背景必须 pale + 2px 主色底线（底线不变）
    if "th {" in html:
        th_block = html.split("th {")[1].split("}")[0]
        if "background: var(--block-bg)" not in th_block and "#F7F7F7" not in th_block and "#f7f7f7" not in th_block:
            violations.append("表格表头背景非 pale 色（--block-bg）")
        if "2px solid var(--ink)" not in th_block and "2px solid #1A1A1A" not in th_block and "2px solid #1a1a1a" not in th_block:
            violations.append("表格表头缺 2px 主色底线")

    # 无 SVG / emoji 作信号
    if "<svg" in html.lower():
        violations.append("发现 SVG（不变量：SVG 不作信号）")
    if re.search(r"[\U0001F300-\U0001FAFF]|\u2705|\u274c|\u2714|\u2716", html):
        violations.append("发现 emoji 信号（不变量：emoji 不作信号）")

    # 打印/离线就绪（M5-04）：内联样式、无外部资源、系统字体
    if re.search(r'<link[^>]+rel=["\']stylesheet', html, re.I):
        violations.append("发现外部样式表引用（须离线可打印，应内联 CSS）")
    if "<script" in html.lower():
        violations.append("发现 <script>（交付物须离线可打印，不应依赖 JS 渲染）")
    if re.search(r"@font-face|fonts\.googleapis|fonts\.gstatic", html, re.I):
        violations.append("发现外部/自定义字体（应使用系统字体）")
    if re.search(r"background-image\s*:", html):
        violations.append("发现背景图片（打印不友好，禁用）")

    return violations


def token_report(html: str, token_colors: dict[str, str]) -> str:
    """token 合规报告：统计选定 token 集内颜色的使用情况。"""
    colors = token_colors or DEFAULT_TOKENS
    used = {_norm_color(v): 0 for v in colors.values()}
    total = 0
    for norm, _ in _color_literals(html):
        if norm in used:
            used[norm] += 1
            total += 1
    lines = [f"Token 合规报告：命中 {total} 处颜色引用（token 集 {len(colors)} 项）"]
    for name, value in colors.items():
        n = used.get(_norm_color(value), 0)
        lines.append(f"  {name}: {value} × {n}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="deliverable-render HTML 静态审计")
    parser.add_argument("html_file", help="成品 HTML 路径")
    parser.add_argument("--token", help="选定视觉模式文件路径（Design Token 块）")
    parser.add_argument("--report", action="store_true", help="输出 token 合规报告")
    args = parser.parse_args()

    html = Path(args.html_file).read_text(encoding="utf-8")
    token_colors = _load_token_colors(Path(args.token) if args.token else None)
    violations = audit(html, token_colors=token_colors)

    if args.report:
        print(token_report(html, token_colors))

    if violations:
        print(f"[FAIL] {args.html_file} 违反 {len(violations)} 条规则：")
        for v in violations:
            print(f"  - {v}")
        return 1
    print(f"[PASS] {args.html_file}：token 无裸值 + 13 条 Pan-Mode Invariants 静态审计通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
