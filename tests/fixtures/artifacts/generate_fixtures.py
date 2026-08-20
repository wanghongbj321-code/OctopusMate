#!/usr/bin/env python3
"""G0-06 测试夹具生成脚本（tests/fixtures/artifacts/ 与 artifact-states/）。

用法：cd OctopusMate && python3 tests/fixtures/artifacts/generate_fixtures.py
说明：content_hash 用 _engine/files.py 的真实复算值生成（G0-06 §6.4：不用手写占位）；
夹具是静态文件，生成后可重复运行（覆盖相同内容，幂等）。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # OctopusMate/
sys.path.insert(0, str(ROOT / "skills"))

from _engine import files  # noqa: E402

FIXTURES = Path(__file__).resolve().parent          # tests/fixtures/artifacts/
STATES = FIXTURES.parent / "artifact-states"

VALID_BODY = (
    "# 打分规则：示例项目 · 示例主题\n"
    "\n"
    "## 规则总览\n"
    "| 项 | 值 |\n"
    "|---|---|\n"
    "| 分值范围 | 1-5 |\n"
    "| 步进 | 0.5 |\n"
    "| 阻断阈值 | 2.0 |\n"
    "| 覆盖角度 | 22 |\n"
    "| 来源 | system-default |\n"
    "\n"
    "## 逐角度锚点\n"
    "| 角度 | 锚点文本（1-5 分参照） |\n"
    "|---|---|\n"
    "| V1 战略承接 | 1分:初步定位；3分:全面落地；5分:机制成熟 |\n"
)

BASE_META = {
    "artifact_type": "diagnosis-scoring",
    "artifact_id": "diagnosis.scoring.current",
    "version": 1,
    "status": "confirmed",
    "source_refs": [],
}


def _conf(confirmed_by="user", interaction_ref="transcript:12:用户确认整体采用默认锚点"):
    return {
        "status": "confirmed",
        "confirmed_at": "2026-08-20T14:00:00+08:00",
        "confirmed_by": confirmed_by,
        "interaction_ref": interaction_ref,
        "confirmation_text": "用户明确确认采用本版打分规则",
    }


def _render(meta: dict, body: str) -> str:
    """构造完整 md 文本（content_hash 按最终文本复算，与 files._write_artifact 一致）。"""
    meta = dict(meta)
    meta["content_hash"] = "sha256:" + "0" * 64
    meta["confirmation"] = dict(meta.get("confirmation", {}))
    text = f"---\n{files._dump_yaml(meta)}---\n\n{body}"
    real = files.content_hash(text)
    meta["content_hash"] = real
    meta["confirmation"]["confirmed_content_hash"] = real
    return f"---\n{files._dump_yaml(meta)}---\n\n{body}"


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    STATES.mkdir(parents=True, exist_ok=True)

    # ① valid confirmed（四类必测①）
    (FIXTURES / "scoring-valid-confirmed.md").write_text(
        _render({**BASE_META, "confirmation": _conf()}, VALID_BODY), encoding="utf-8")

    # ② missing confirmation（四类必测②）：正文有自然语言"确认留痕"，无 confirmation 元数据
    missing_body = VALID_BODY + "\n## 人类可读确认摘要\n- 确认方式：整体采用默认锚点\n- 确认内容摘要：用户确认采用默认规则\n"
    meta_no_conf = {**BASE_META}
    # 无 confirmation → 无 hash 可复算依据；直接写（content_hash 也缺）
    (FIXTURES / "scoring-missing-confirmation.md").write_text(
        f"---\n{files._dump_yaml(meta_no_conf)}---\n\n{missing_body}", encoding="utf-8")

    # ③ bad hash（四类必测③）：confirmation 完整但 content_hash 为错误值
    meta_bad = {**BASE_META, "confirmation": _conf()}
    meta_bad["content_hash"] = "sha256:" + "a" * 64
    meta_bad["confirmation"]["confirmed_content_hash"] = "sha256:" + "a" * 64
    (FIXTURES / "scoring-bad-hash.md").write_text(
        f"---\n{files._dump_yaml(meta_bad)}---\n\n{VALID_BODY}", encoding="utf-8")

    # ④ stale ref（四类必测④）：source_refs 指向 scoring@v1（配合 stale-state.json 当前 v2）
    meta_stale = {**BASE_META,
                  "artifact_id": "diagnosis.dimension.v.current",
                  "artifact_type": "diagnosis-dimension",
                  "source_refs": ["diagnosis.scoring.current@v1"],
                  "confirmation": _conf(interaction_ref="transcript:18:用户确认 V 维总结与分值")}
    stale_body = "# V 维诊断：示例项目 · 示例主题\n\n## 角度打分表\n| 角度 | 分值 |\n|---|---|\n| V1 | 3.0 |\n"
    (FIXTURES / "scoring-stale-ref.md").write_text(
        _render(meta_stale, stale_body), encoding="utf-8")

    # ⑤ confirmed_by=agent（绕过：非 user）
    meta_agent = {**BASE_META, "confirmation": _conf(confirmed_by="agent")}
    (FIXTURES / "scoring-agent-confirmed.md").write_text(
        _render(meta_agent, VALID_BODY), encoding="utf-8")

    # ⑥ 文件合法但未登记 manifest（绕过：无 manifest 索引）→ 复用 valid md，测试中不登记
    # state 夹具
    import json

    valid_hash = files.content_hash((FIXTURES / "scoring-valid-confirmed.md").read_text(encoding="utf-8"))
    stale_entry_hash = files.content_hash((FIXTURES / "scoring-stale-ref.md").read_text(encoding="utf-8"))

    valid_state = {
        "project_slug": "test-project",
        "project_name": "测试项目",
        "topic_slug": "test-topic",
        "topic_name": "测试主题",
        "updated_at": "2026-08-20T14:30:00+08:00",
        "status": "review_ready",
        "artifacts": {
            "diagnosis.scoring.current": {
                "path": "modules/diagnosis-scoring-test-topic-v1.md",
                "version": 1,
                "status": "confirmed",
                "content_hash": valid_hash,
                "depends_on": [],
                "created_at": "2026-08-20T14:00:00+08:00",
                "confirmed_at": "2026-08-20T14:00:00+08:00",
                "confirmed_by": "user",
                "interaction_ref": "transcript:12:用户确认整体采用默认锚点",
            }
        },
        "scoring_config": {"scale": {"min": 1, "max": 5, "step": 0.5}, "blockThreshold": 2.0},
    }
    (STATES / "valid-state.json").write_text(
        json.dumps(valid_state, ensure_ascii=False, indent=2), encoding="utf-8")

    # stale-state：scoring 当前 v2（confirmed），维度 v1 引用 scoring@v1 → 维度 stale
    stale_state = {
        "project_slug": "test-project",
        "project_name": "测试项目",
        "topic_slug": "test-topic",
        "topic_name": "测试主题",
        "updated_at": "2026-08-20T15:00:00+08:00",
        "status": "review_ready",
        "artifacts": {
            "diagnosis.scoring.current": {
                "path": "modules/diagnosis-scoring-test-topic-v2.md",
                "version": 2,
                "status": "confirmed",
                "content_hash": "sha256:" + "b" * 64,
                "depends_on": [],
                "created_at": "2026-08-20T14:50:00+08:00",
            },
            "diagnosis.dimension.v.current": {
                "path": "modules/diagnosis-v-test-topic-v1.md",
                "version": 1,
                "status": "stale",
                "content_hash": stale_entry_hash,
                "depends_on": ["diagnosis.scoring.current@v1"],
                "created_at": "2026-08-20T14:30:00+08:00",
            },
        },
    }
    (STATES / "stale-state.json").write_text(
        json.dumps(stale_state, ensure_ascii=False, indent=2), encoding="utf-8")

    print("fixtures generated:")
    for p in sorted(list(FIXTURES.iterdir())) + sorted(list(STATES.iterdir())):
        print("  -", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
