#!/usr/bin/env python3
"""render_package.py · 能力路线图交付资产包渲染脚本（骨架版，M0-03；M3 完善）。

M0-03 范围（对齐开发计划 M0-03）：
- 模板片段加载与页面组装骨架：从 templates/capability-package/ 读取片段，
  用阶段数据填充 {{占位符}} 组装出可审计通过的页面骨架
- 无裸值：CSS 全部来自模板片段（token 化，黑灰默认），本脚本不产生任何色值

M3 待完善（明确不在 M0 范围内）：
- 六阶段 confirmed md 解析（对齐 M2 阶段产物 md 契约）→ stage_data
- 可视化生成：逻辑链 / 分层图 / 覆盖矩阵 / 热力矩阵 / 重点矩阵 / 差距热力 /
  举措链 / 战略屋 / 里程碑甘特图（M/G/D）等 SVG，数据全部来自确认 md
- 包结构渲染：index.html + 01~06 六页，相对路径
- 资产包对账：audit_html.py --canvas-type=capability-package（M3-04）

用法（演示骨架，M3 前）：
    python3 render_package.py --demo
    # 输出演示页面骨架到 stdout（供 audit 与人工预览）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_RENDER_DIR = Path(__file__).resolve().parents[1]          # skills/deliverable-render
_TEMPLATES = _RENDER_DIR / "templates" / "capability-package"


class TemplateError(Exception):
    """模板片段缺失或渲染数据缺失。"""


# ---------- 模板片段加载 ----------

def load_template(name: str) -> str:
    """读取模板片段；缺失抛 TemplateError（M0-03 骨架内所有片段必须在 templates/capability-package/）。"""
    path = _TEMPLATES / name
    if not path.exists():
        raise TemplateError(f"模板片段缺失：{path}")
    return path.read_text(encoding="utf-8")


# ---------- 片段渲染函数（骨架）----------

def _fill(tpl: str, data: dict) -> str:
    """将 {{key}} 占位符替换为 data[key]；缺失 key 保留占位（M3 后由对账保证无残留）。"""
    out = tpl
    for k, v in data.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def render_hero(data: dict) -> str:
    """hero 区：Executive Message + 导航 + So what。data 键：标题/一句话说明/导航链接/管理含义。"""
    return _fill(load_template("_hero.html.tpl"), data)


def render_summary_strip(data: dict) -> str:
    """支撑论点条：data 键：论点一~三标题/说明、关键数字/关键数字说明。"""
    return _fill(load_template("_summary-strip.html.tpl"), data)


def render_section(data: dict, body: str) -> str:
    """通用 section：data 键：section_id/eyebrow/标题/说明/输出判断；body 为该节内容 HTML。"""
    return _fill(load_template("_section.html.tpl"), {**data, "section_body": body})


def render_quality_gate(data: dict) -> str:
    """质量门：data 键：质量门标题/说明/下一步重点/质量门卡片（已组装的卡片 HTML）。"""
    return _fill(load_template("_quality-gate.html.tpl"), data)


def render_open_issues(data: dict) -> str:
    """未决条件清单（T12）：data 键：未决项数量/阶段编号/未决项行（已组装的行 HTML）。"""
    return _fill(load_template("_open-issues.html.tpl"), data)


def render_action_table(data: dict) -> str:
    """下一步行动（T13）：data 键：行动行（已组装的行 HTML）。"""
    return _fill(load_template("_action-table.html.tpl"), data)


def render_footer(data: dict) -> str:
    """页脚：data 键：项目名称/日期/版本/阶段编号。"""
    return _fill(load_template("_footer.html.tpl"), data)


# ---------- 页面组装（骨架）----------

def assemble_page(stage: dict, sections: list[str]) -> str:
    """组装单阶段页面骨架。

    stage 键：页面标题/阶段编号/版本/项目名称/主题名称/阶段交付物名称/阶段对象/质量门状态
    sections：按顺序排列的 section HTML（hero/summary 之后的各内容节 + 质量门 +
              未决面板 + 行动表；footer 由本函数统一追加）。
    """
    head = _fill(load_template("_head.html.tpl"), stage)
    hero = render_hero(stage)
    summary = render_summary_strip(stage)
    body = "".join(sections)
    footer = render_footer(stage)
    return head + hero + summary + body + footer


# ---------- 演示入口（M0-03 骨架验证）----------

def _demo() -> str:
    """用 mock 阶段数据组装一页骨架，验证模板片段链可用（M3 后由 md 解析替代）。"""
    stage = {
        "页面标题": "01 构建战略对齐的企业能力模型（骨架演示）",
        "阶段编号": "01",
        "版本": "v0.1-draft",
        "项目名称": "{{项目名称}}",
        "主题名称": "{{主题名称}}",
        "阶段交付物名称": "企业能力模型交付物",
        "阶段对象": "能力模型",
        "质量门状态": "{{质量门状态}}",
        "hero_标题": "{{阶段主结论标题}}",
        "hero_一句话说明": "{{阶段一句话说明}}",
        "hero_导航链接": '<a href="#logic">战略连接</a><a href="#quality">质量门</a>',
        "hero_管理含义": "{{管理含义}}",
        "论点一标题": "{{支撑论点一标题}}", "论点一说明": "{{支撑论点一说明}}",
        "论点二标题": "{{支撑论点二标题}}", "论点二说明": "{{支撑论点二说明}}",
        "论点三标题": "{{支撑论点三标题}}", "论点三说明": "{{支撑论点三说明}}",
        "关键数字": "{{关键数字}}", "关键数字说明": "{{关键数字说明}}",
        "日期": "{{日期}}",
    }
    sections = [
        render_section(
            {"section_id": "logic", "section_eyebrow": "01 · Strategy To Capability",
             "section_标题": "{{战略连接标题}}", "section_说明": "{{战略连接说明}}",
             "section_输出判断": "{{输出判断}}"},
            '<p style="color:var(--ink-soft);font-size:13px;">{{section_body：逻辑链/能力架构/清单/价值流等，M3 按确认包 md 渲染}}</p>',
        ),
        render_quality_gate({
            "质量门标题": '{{质量门标题}}', "质量门说明": "{{质量门说明}}",
            "下一步重点": "{{下一步重点}}",
            "质量门卡片": '<article class="quality-card"><span class="status">{{状态}}</span><h3>{{检查项}}</h3><p>{{检查说明}}</p></article>',
        }),
        render_open_issues({
            "未决项数量": "{{未决项数量}}", "阶段编号": "01",
            "未决项行": "<tr><td>{{U-xx}}</td><td>{{来源/原编号}}</td><td>{{未决内容}}</td><td>{{影响面}}</td><td>{{证据强度}}</td><td>{{责任人}}</td><td>{{拟裁决方式}}</td></tr>",
        }),
        render_action_table({"行动行": "<tr><td>{{下一步行动}}</td><td>{{责任 owner}}</td><td>{{时限}}</td></tr>"}),
    ]
    return assemble_page(stage, sections)


def main() -> int:
    ap = argparse.ArgumentParser(description="能力路线图资产包渲染（骨架）")
    ap.add_argument("--demo", action="store_true", help="输出演示页面骨架（M0-03 验证）")
    args = ap.parse_args()
    if args.demo:
        print(_demo())
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
