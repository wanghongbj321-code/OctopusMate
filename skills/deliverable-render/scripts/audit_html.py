#!/usr/bin/env python3
"""deliverable-render HTML 静态审计（M2-03 v2：token 无裸值 + 13 条不变量语义演进；M3-04：capability-package 资产包对账扩展）。

检查项（对齐开发计划 §5.2 与 M3-04）：
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

capability-package 画布（M3-04）额外执行**资产包对账**：
- 包结构：index + 01~06 共 7 文件齐全、相对路径、无外链
- 每页信息对账：与 confirmed md 结构化数据块机器比对
  （质量门状态 / 实体 id / 派生计数 / 档位·级别关键词）
- Illustrative 标注校验

用法：python3 audit_html.py <output.html 或 package-dir> [--token <pattern.md>] [--canvas-type <vision-confirm|diagnosis-report|capability-package>] [--source-md <confirm.md 或 modules-dir>] [--report]
  --token: 选定视觉模式文件路径（解析 Design Token 块）；缺省用黑灰 token 集
  --canvas-type: 画布类型。vision-confirm（默认）：SVG 全拦（装饰信号）；
    diagnosis-report / capability-package：放行图表 SVG 但强校验（必含 title+role，见 chart-specs.md）
  --source-md: 确认包路径（diagnosis-report：诊断确认包 md；capability-package：六阶段任一 confirmed md
    或 modules 目录）。提供时执行 HTML/确认包信息对账；未提供时只算视觉/token 审计，**不算交付 gate 通过**
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 复用引擎对账解析（skills/_engine/reconcile.py；脚本位于 skills/deliverable-render/scripts/）
_ENGINE_DIR = Path(__file__).resolve().parents[2]
if str(_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGINE_DIR))

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


def audit(
    html: str,
    pattern_path: Path | None = None,
    token_colors: dict | None = None,
    allow_chart_svg: bool = False,
) -> list[str]:
    """静态审计，返回违规清单（空 = 通过）。

    - html: 成品 HTML
    - pattern_path: 选定视觉模式文件路径（解析 token 集）
    - token_colors: 直接传 token 色板（优先于 pattern_path）
    - allow_chart_svg: 是否放行图表 SVG（canvasType=diagnosis-report 时 True）。
      语义演进（方案 A，2026-08-19）：数据图表（雷达/问题树/链路图，见
      references/chart-specs.md）属"图表"非"装饰信号"，放行但强校验——
      每个 SVG 必须含 <title> + role="img"（无障碍，G2）；裸值/渐变/阴影
      仍由 token 无裸值与其他不变量拦截。容器外装饰性 SVG 仍拦。
    """
    violations: list[str] = []
    colors = token_colors or _load_token_colors(pattern_path)
    allowed = {v.lower() for v in colors.values()}

    # --- token 无裸值校验（语义演进核心）---
    for norm, raw in _color_literals(html):
        if norm not in allowed:
            violations.append(f"发现 token 集外裸值色值：{raw}（须引用选定 token 集内的颜色）")

    # --- 13 条 Pan-Mode Invariants 底线 ---
    # box-shadow: none 是显式禁用声明（合规），仅拦截实际阴影值
    for m in re.finditer(r"box-shadow\s*:\s*([^;]+);", html):
        if m.group(1).strip().lower() != "none":
            violations.append(f"发现 box-shadow（不变量 4：禁用）：{m.group(1).strip()}")
            break
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

    # 无 SVG / emoji 作信号（语义演进：图表 SVG 放行但强校验，见 chart-specs.md G1/G2）
    svg_blocks = re.findall(r"<svg[^>]*>.*?</svg>", html, re.S | re.I)
    if svg_blocks and not allow_chart_svg:
        violations.append("发现 SVG（不变量：SVG 不作信号；诊断图表画布须 --canvas-type=diagnosis-report）")
    if allow_chart_svg:
        for i, blk in enumerate(svg_blocks):
            if not re.search(r"<title[ >]", blk, re.I):
                violations.append(f"图表 SVG[{i}] 缺少 <title>（无障碍要求，chart-specs.md G2）")
            if not re.search(r'<svg[^>]*role=["\']img["\']', blk, re.I):
                violations.append(f"图表 SVG[{i}] 缺 role=\"img\"（无障碍要求，chart-specs.md G2）")
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


def check_diagnosis_consistency(html: str, confirm_md_path: Path) -> list[str]:
    """G4-04：HTML 与确认包信息对账（§8.3）。

    检查项：
    1. 六节编号 section（01 执行摘要 / 02 诊断方法与打分框架 / 03 总体诊断结论 /
       04 分维诊断详情 / 05 阻断性问题专题 / 06 附录证据清单）无缺节
    2. 分数一致：确认包各角度分/维度分/总体分数值出现在 HTML（图表与表格数据来源）
    3. 证据编号一致：确认包证据编号 ⊆ HTML 出现编号（附录清单）
    4. 阻断编号一致：确认包阻断编号 ⊆ HTML 出现编号（阻断专题）
    5. 三张图表 SVG 数据来自确认包（SVG ≥3 且数据由 2/4 覆盖检查）

    返回违规清单（空 = 通过）。
    """
    from _engine import files as files_mod
    from _engine import reconcile as reconcile_mod

    violations: list[str] = []
    art = files_mod.read_artifact(confirm_md_path)
    if not art.valid or art.meta is None:
        return [f"确认包无效：{art.errors}（不能作为 HTML 对账事实源）"]
    if art.meta.get("status") != "confirmed":
        return ["确认包非 confirmed 状态，不能作为 HTML 对账事实源"]
    body = art.body

    # 1. 六节编号 section
    sec_titles = {"01": "执行摘要", "02": "诊断方法与打分框架", "03": "总体诊断结论",
                  "04": "分维诊断详情", "05": "阻断性问题专题", "06": "附录"}
    missing_sections = []
    for num, title in sec_titles.items():
        if not re.search(rf'sec-num">{num}</span>\s*<h2>{re.escape(title)}</h2>', html):
            missing_sections.append(f"{num} {title}")
    if missing_sections:
        violations.append(f"HTML 缺诊断报告 section：{missing_sections}")

    # 2. 分数一致（角度分 + 总体分数值出现在 HTML）
    scores = reconcile_mod._parse_pkg_angle_scores(body)
    missing_scores = [f"{a}={s}" for a, s in scores.items() if not _html_has_number(html, s)]
    if missing_scores:
        violations.append(f"HTML 缺失确认包角度分值：{missing_scores}")

    # 3. 证据编号
    ev_ids = reconcile_mod._parse_pkg_evidence_ids(body)
    missing_ev = [e for e in sorted(ev_ids) if e not in html]
    if missing_ev:
        violations.append(f"HTML 缺失确认包证据编号：{missing_ev}")

    # 4. 阻断编号
    blk_ids = reconcile_mod._parse_pkg_blocker_ids(body)
    missing_blk = [b for b in sorted(blk_ids) if b not in html]
    if missing_blk:
        violations.append(f"HTML 缺失确认包阻断编号：{missing_blk}")

    # 5. 三张图表 SVG
    svg_count = len(re.findall(r"<svg", html, re.I))
    if svg_count < 3:
        violations.append(f"诊断报告图表 SVG 不足 3 张（实际 {svg_count}；雷达图/问题树/链路图）")

    return violations


def _html_has_number(html: str, value: float) -> bool:
    """HTML 中是否出现独立数值（如 3.0 / 3.5），避免子串误匹配（13.05 含 3.0）。"""
    text = f"{value:.1f}"  # 统一一位小数（3.0 → "3.0"，3.5 → "3.5"）
    return re.search(rf"(?<![\d.]){re.escape(text)}(?![\d.])", html) is not None


# --- M3-04：capability-package 资产包对账 ---

# 资产包 7 文件相对路径（对齐开发计划 §4.1）
PACKAGE_REL_FILES = (
    "index.html",
    "01-capability-model/index.html",
    "02-baseline-maturity/index.html",
    "03-priority-capabilities/index.html",
    "04-future-state/index.html",
    "05-gap-initiatives/index.html",
    "06-capability-roadmap/index.html",
)
# 阶段 md 文件名前缀 → 阶段页子目录
_MD_PREFIX_TO_STEP = {
    "capability-model": "01",
    "baseline-maturity": "02",
    "priority-capabilities": "03",
    "future-state": "04",
    "gap-initiatives": "05",
    "capability-roadmap": "06",
}
_STEP_DIR = {
    "01": "01-capability-model", "02": "02-baseline-maturity",
    "03": "03-priority-capabilities", "04": "04-future-state",
    "05": "05-gap-initiatives", "06": "06-capability-roadmap",
}


def _find_step_sources(source_md: Path) -> list[tuple[str, Path]]:
    """解析 --source-md：文件（单阶段）或目录（modules，自动匹配六阶段 confirmed md）。

    返回 [(step, md_path)]；按文件名前缀映射阶段页子目录。
    """
    results: list[tuple[str, Path]] = []
    if source_md.is_dir():
        for p in sorted(source_md.glob("*.md")):
            name = p.name
            prefix = name.split("-", 1)[0] if "-" in name else ""
            # 匹配 capability-model-{slug}-v{N}.md 等（前缀即阶段 md 前缀）
            for pre, step in _MD_PREFIX_TO_STEP.items():
                if name.startswith(pre + "-"):
                    results.append((step, p))
                    break
        return results
    # 单文件：按文件名前缀识别阶段
    for pre, step in _MD_PREFIX_TO_STEP.items():
        if source_md.name.startswith(pre + "-"):
            results.append((step, source_md))
            break
    return results


def _package_expected_tokens(data: dict, step: str) -> list[str]:
    """从结构化数据块提取「必须出现在对应页 html」的 token 列表。

    - 质量门状态（qualityGate）
    - 实体 id（能力域 / 能力 / 举措 / 里程碑 / 能力引用）
    - 派生计数（能力域数、能力数、重点数、举措数、里程碑数等）
    - 档位 / 级别 / 类型关键词（成熟度档位、差距级别、M/G/D、O7 六项）
    """
    tokens: list[str] = []
    block = data.get(step and {
        "01": "capabilityModel", "02": "maturityBaseline", "03": "priorityCapabilities",
        "04": "futureStateGaps", "05": "gapInitiatives", "06": "enterpriseRoadmap",
    }.get(step, ""), {}) or {}

    qg = block.get("qualityGate")
    if qg:
        tokens.append(str(qg))

    if step == "01":
        clusters = block.get("clusters") or []
        tokens.append(str(len(clusters)))                      # 能力域数
        caps_total = sum(len(c.get("capabilities") or []) for c in clusters)
        tokens.append(str(caps_total))                         # L2 能力数
        for c in clusters:
            tokens.append(str(c.get("id", "")))                # 能力域编号
            tokens.append(str(c.get("classification", "")))    # 分类词
    elif step == "02":
        caps = block.get("capabilities") or []
        tokens.append(str(len(caps)))                          # 能力域数
        for c in caps:
            tokens.append(str(c.get("id", "")))
            tokens.append(str(c.get("maturity", "")))          # 档位词
            tokens.append(str(c.get("evidenceStrength", "")))  # 证据强度
    elif step == "03":
        plist = block.get("priorityList") or []
        tokens.append(str(len(plist)))                         # 重点能力数
        for p in plist:
            tokens.append(str(p.get("capabilityId", "")))
        cond = sum(1 for p in plist if p.get("conditional") is True)
        if cond:
            tokens.append(str(cond))                           # 条件重点数
        excluded = block.get("excluded") or []
        tokens.append(str(len(excluded)))                      # 非重点数
        for e in excluded:
            tokens.append(str(e.get("capabilityId", "")))
    elif step == "04":
        gaps = block.get("gaps") or []
        tokens.append(str(len(gaps)))                          # 差距数
        for g in gaps:
            tokens.append(str(g.get("capabilityId", "")))
            tokens.append(str(g.get("level", "")))             # 大/中/小
        for prof in block.get("gapProfiles") or []:
            tokens.append(str(prof.get("profile", ""))[:12])   # 差距画像摘要（前 12 字匹配）
    elif step == "05":
        inits = block.get("initiatives") or []
        tokens.append(str(len(inits)))                         # 举措数
        for it in inits:
            tokens.append(str(it.get("id", "")))
        tokens.append(str(len(block.get("techPreChecks") or [])))  # 前置检查数
    elif step == "06":
        milestones = block.get("milestones") or []
        tokens.append(str(len(milestones)))                    # 里程碑数
        mtypes = {m.get("type", "") for m in milestones}
        for t in ("M", "G", "D"):
            if t in mtypes:
                tokens.append(t)                               # 节点类型标注
        for m in milestones:
            tokens.append(str(m.get("id", "")))
        tokens.append(str(len(block.get("sortClusters") or [])))  # 排序簇数
        for ph in block.get("phases") or []:
            tokens.append(str(ph.get("phase", "")))            # 阶段词
        o7 = data.get("downstreamInterfaces") or {}
        for key, label in (("endToEndSolution", "端到端方案"), ("targetOperatingModel", "目标运营模式"),
                           ("detailedImplementationPlan", "详细实施计划"), ("benefitCase", "Benefit Case"),
                           ("enterpriseArchitecture", "企业架构"), ("portfolioGovernance", "组合治理")):
            if key in o7 and not _blank(o7.get(key)):
                tokens.append(label)
    return [t for t in tokens if t]


def _blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def check_capability_package(package_dir: Path, source_md: Path, token_colors: dict) -> list[str]:
    """M3-04：资产包对账（包结构 + 每页信息机器比对 + Illustrative + token 无裸值 + 13 条不变量）。

    - package_dir：`capability-roadmap-package-{slug}-v{N}/` 目录
    - source_md：六阶段任一 confirmed md，或 modules 目录（自动匹配六阶段）
    - 返回违规清单（空 = 通过）
    """
    from _engine import roadmap as roadmap_mod

    package_dir = Path(package_dir)
    violations: list[str] = []

    # 1. 包结构：7 文件齐全
    missing = [rel for rel in PACKAGE_REL_FILES if not (package_dir / rel).exists()]
    if missing:
        violations.append(f"资产包缺文件：{missing}")
        return violations  # 结构不全，后续对账无意义

    # 2. 每页视觉审计 + 相对路径/无外链 + Illustrative 标注
    for rel in PACKAGE_REL_FILES:
        html = (package_dir / rel).read_text(encoding="utf-8")
        violations.extend(f"{rel}: {v}" for v in audit(html, token_colors=token_colors, allow_chart_svg=True))
        # 相对路径 / 无外链（http/https/绝对路径 / 绝对根路径）
        for m in re.finditer(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', html):
            u = m.group(1)
            if re.match(r"^(https?:)?//|^/[a-zA-Z]", u):
                violations.append(f"{rel}: 发现外链/绝对路径资源引用：{u}")
        if "Illustrative" not in html:
            violations.append(f"{rel}: 缺 Illustrative 标注（量化指标须标注 Illustrative · 需实际调研校准）")

    # 3. 信息对账：解析 source md 结构化数据块 → 与对应页 html 机器比对
    sources = _find_step_sources(Path(source_md))
    if not sources:
        violations.append(f"--source-md 无法识别六阶段产物：{source_md}")
    for step, md_path in sources:
        ra = roadmap_mod.read_roadmap_artifact(md_path)
        if not ra.valid:
            violations.append(f"{md_path.name}: 非有效 confirmed md（{ra.errors[:3]}）")
            continue
        data = roadmap_mod.extract_data_block(ra.artifact.body)
        if not data:
            violations.append(f"{md_path.name}: 缺结构化数据块，无法对账")
            continue
        rel = f"{_STEP_DIR[step]}/index.html"
        html = (package_dir / rel).read_text(encoding="utf-8")
        for token in _package_expected_tokens(data, step):
            if token and token not in html:
                violations.append(f"{rel}: 信息对账不一致，缺 {token!r}（结构化数据块 {md_path.name}）")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="deliverable-render HTML 静态审计")
    parser.add_argument("html_file", help="成品 HTML 路径（capability-package 画布传资产包目录）")
    parser.add_argument("--token", help="选定视觉模式文件路径（Design Token 块）")
    parser.add_argument("--canvas-type", choices=["vision-confirm", "diagnosis-report", "capability-package"],
                        default="vision-confirm", help="画布类型（diagnosis-report/capability-package 放行图表 SVG）")
    parser.add_argument("--source-md", help="确认包路径（diagnosis-report：确认包 md；capability-package：六阶段任一 confirmed md 或 modules 目录；缺省只做视觉审计）")
    parser.add_argument("--report", action="store_true", help="输出 token 合规报告")
    args = parser.parse_args()

    token_colors = _load_token_colors(Path(args.token) if args.token else None)
    allow_chart_svg = args.canvas_type != "vision-confirm"

    # capability-package：包目录对账（含每页 audit）
    if args.canvas_type == "capability-package":
        pkg = Path(args.html_file)
        if not pkg.is_dir():
            print(f"[FAIL] capability-package 画布须传资产包目录（index + 01~06）：{pkg}")
            return 1
        violations = check_capability_package(pkg, Path(args.source_md) if args.source_md else pkg.parent, token_colors)
        if args.report:
            for rel in PACKAGE_REL_FILES:
                html = (pkg / rel).read_text(encoding="utf-8")
                print(token_report(html, token_colors))
        if args.source_md:
            if not violations:
                print(f"[INFO] --source-md 对账通过：资产包 {pkg.name} 与六阶段 confirmed md 内容一致（7 文件 / 相对路径 / 信息比对 / Illustrative）")
        else:
            print("[INFO] 未提供 --source-md：只算视觉/token 审计，**不计为交付 gate 通过**（M3-04）")
        if violations:
            print(f"[FAIL] {pkg} 资产包对账失败（{len(violations)} 条）：")
            for v in violations:
                print(f"  - {v}")
            return 1
        print(f"[PASS] {pkg}：资产包对账通过（7 文件 + 相对路径 + 信息比对 + Illustrative + token 无裸值 + 13 条不变量"
              + (" + 确认包信息对账" if args.source_md else "") + ")")
        return 0

    # 单文件画布（vision-confirm / diagnosis-report）
    html = Path(args.html_file).read_text(encoding="utf-8")
    violations = audit(html, token_colors=token_colors, allow_chart_svg=allow_chart_svg)

    if args.report:
        print(token_report(html, token_colors))

    # G4-03：HTML/确认包信息对账（仅 --source-md 提供时执行）
    consistency_violations: list[str] | None = None
    if args.source_md:
        consistency_violations = check_diagnosis_consistency(html, Path(args.source_md))
        if not consistency_violations:
            print(f"[INFO] --source-md 对账通过：HTML 与 {Path(args.source_md).name} 内容一致（六节 section / 分数 / 证据编号 / 阻断编号 / 图表数据）")
    else:
        print("[INFO] 未提供 --source-md：只算视觉/token 审计，**不计为交付 gate 通过**（G4）")

    if violations or consistency_violations:
        if violations:
            print(f"[FAIL] {args.html_file} 违反 {len(violations)} 条规则：")
            for v in violations:
                print(f"  - {v}")
        if consistency_violations:
            print(f"[FAIL] {args.html_file} 与确认包信息对账失败：")
            for v in consistency_violations:
                print(f"  - {v}")
        return 1
    print(f"[PASS] {args.html_file}：token 无裸值 + 13 条 Pan-Mode Invariants 静态审计"
          + (" + 确认包信息对账" if args.source_md else "") + "通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
