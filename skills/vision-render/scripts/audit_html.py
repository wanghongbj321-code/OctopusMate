#!/usr/bin/env python3
"""M2-06 确认包 HTML 静态审计（13 条 Pan-Mode Invariants 底线，黑灰专业模式）。

检查项（对齐开发计划 §5.2）：
1. 无 box-shadow / 复杂渐变（linear/radial-gradient）
2. 无圆润胶囊按钮（border-radius > 2px）
3. 背景仅灰度（#FFFFFF / #F7F7F7 等），无彩色信号
4. 表格：pale 色表头 + 主色文字 + 2px 主色底线
5. 质量判定仅字重 + 下划线 + 灰度（无彩色 PASS/FAIL）
6. 无 SVG / emoji 作信号

用法：python3 audit_html.py <output.html>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TOKENS = {
    "page_bg": "#FFFFFF",
    "block_bg": "#F7F7F7",
    "ink": "#1A1A1A",
    "ink_deep": "#2D2D2D",
    "ink_soft": "#6B6B6B",
    "ink_muted": "#808080",
    "border": "#D4D4D4",
}

# 允许的灰度色值（黑灰专业 token 全集）
ALLOWED_COLORS = {v.lower() for v in TOKENS.values()}


def _color_from(style_attr: str) -> list[str]:
    return re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)", style_attr)


def audit(html: str) -> list[str]:
    violations: list[str] = []

    if re.search(r"box-shadow\s*:", html):
        violations.append("发现 box-shadow（不变量 4：禁用）")
    if re.search(r"linear-gradient|radial-gradient", html, re.I):
        violations.append("发现渐变（不变量 4：禁用复杂渐变）")

    for m in re.finditer(r"border-radius\s*:\s*([0-9.]+)px", html):
        if float(m.group(1)) > 2:
            violations.append(f"发现圆润胶囊样式 border-radius={m.group(1)}px > 2px")

    # 彩色检测：CSS 与内联中的非灰度色值
    for m in re.finditer(r"(?:color|background|background-color|border[^:]*)\s*:\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]*\))", html):
        raw = m.group(1).lower()
        if raw not in ALLOWED_COLORS:
            # rgba(255,255,255) 等灰度表示
            rgb = re.findall(r"\d{1,3}", raw)
            if len(rgb) >= 3 and rgb[0] == rgb[1] == rgb[2]:
                continue
            violations.append(f"发现非灰度色值：{raw}")

    # 表格：th 背景必须 pale（--block-bg）+ 2px 主色底线
    if "th {" in html:
        th_block = html.split("th {")[1].split("}")[0]
        if "background: var(--block-bg)" not in th_block and "#F7F7F7" not in th_block:
            violations.append("表格表头背景非 pale 色（--block-bg）")
        if "2px solid var(--ink)" not in th_block and "2px solid #1A1A1A" not in th_block:
            violations.append("表格表头缺 2px 主色底线")

    # 无彩色 PASS/FAIL 信号（绿/红）
    if re.search(r"#[0-9a-fA-F]{6}", html):
        for c in re.findall(r"#[0-9a-fA-F]{6}", html):
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
            if (g > r + 60 and g > b + 60) or (r > g + 60 and r > b + 60):
                violations.append(f"发现彩色信号色值：{c}")

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


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：audit_html.py <output.html>")
        return 2
    html = Path(sys.argv[1]).read_text(encoding="utf-8")
    violations = audit(html)
    if violations:
        print(f"[FAIL] {sys.argv[1]} 违反 {len(violations)} 条不变量：")
        for v in violations:
            print(f"  - {v}")
        return 1
    print(f"[PASS] {sys.argv[1]}：13 条 Pan-Mode Invariants 静态审计通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
