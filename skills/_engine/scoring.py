"""M1-01 诊断打分统计（scoring）。

对齐 VITAL 方法论 §二 打分规则与开发计划 §4 统计规则：
- 单一打分：每个二级角度按锚点评定 1-5 分（0.5 步进），单一数值标记输出
- 维度分：取本维各二级角度打分的算术平均（保留一位小数）；未打分角度不计入
- 总体分：取五维维度分的算术平均（保留一位小数），统计结果不映射回档位
- 打分规则唯一事实源在 state.json.scoring_config（M1-04 运行时注入），
  本模块不读 manifest 硬编码锚点；scoring_config 缺失时阻断
"""
from __future__ import annotations


def validate_score(value, scale: dict) -> list[str]:
    """步进校验：分值必须在 [min, max] 且符合 step 步进（浮点容差 1e-9）。

    返回错误列表（空 = 通过）。
    """
    errors: list[str] = []
    if not isinstance(value, (int, float)):
        return [f"分值必须为数值，实际 {value!r}"]
    try:
        lo = float(scale["min"])
        hi = float(scale["max"])
        step = float(scale["step"])
    except (KeyError, TypeError, ValueError):
        return [f"scoring_config.scale 无效：{scale!r}"]

    if value < lo or value > hi:
        errors.append(f"分值 {value} 超出范围 [{lo}, {hi}]")
    # (value - min) / step 应为整数（浮点容差）
    if step > 0:
        ratio = (value - lo) / step
        if abs(ratio - round(ratio)) > 1e-9:
            errors.append(f"分值 {value} 不符合步进 {step}（起点 {lo}）")
    return errors


def dimensions_from_anchors(anchors: dict) -> dict[str, list[str]]:
    """从 scoring_config.anchors 推导维度分组：{维度: [角度...]}。

    anchors 按维度组织（anchors.V 含 V1/V2/V3/V4 等），每个维度的键即该维角度列表。
    空 anchors 返回空 dict。
    """
    return {
        dim: list(angles.keys())
        for dim, angles in (anchors or {}).items()
        if isinstance(angles, dict)
    }


def _avg_1dp(values: list[float]) -> float | None:
    """算术平均保留一位小数；空列表返回 None（未打分不计入）。"""
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def compute_dimension_scores(scores: dict, dimensions: dict[str, list[str]]) -> dict[str, float]:
    """维度分：每维各二级角度打分算术平均（保留一位小数）。

    - scores: {角度: {"score": float, ...}}
    - dimensions: {维度: [角度...]}
    - 未打分角度（不在 scores 或无 score）不计入；某维全部未打分则该维无分（不计入总体）
    """
    result: dict[str, float] = {}
    for dim, angles in dimensions.items():
        vals = [
            scores[a]["score"]
            for a in angles
            if a in scores and isinstance(scores[a], dict) and "score" in scores[a]
        ]
        avg = _avg_1dp(vals)
        if avg is not None:
            result[dim] = avg
    return result


def compute_overall_score(dimension_scores: dict[str, float]) -> float | None:
    """总体分：五维维度分算术平均（保留一位小数）。

    返回 None 表示无任何维度分（无可统计）。
    """
    return _avg_1dp(list(dimension_scores.values()))


def compute_all(scores: dict, scoring_config: dict) -> dict:
    """一站式统计：步进校验 → 维度分 → 总体分。

    返回 {
      "errors": [...],             # 步进/范围违规清单（空 = 通过）
      "dimension_scores": {...},   # 维度分（通过校验的角度参与）
      "overall_score": float|None,
    }
    """
    scale = (scoring_config or {}).get("scale")
    if not scale:
        return {"errors": ["scoring_config.scale 缺失，无法统计"], "dimension_scores": {}, "overall_score": None}

    # 步进校验：仅对已打分角度校验；违规角度剔除出统计（保留在 scores 供呈现）
    errors: list[str] = []
    clean: dict = {}
    for angle, entry in (scores or {}).items():
        if not isinstance(entry, dict) or "score" not in entry:
            continue
        errs = validate_score(entry["score"], scale)
        if errs:
            errors.append(f"角度 {angle}: {errs[0]}")
        else:
            clean[angle] = entry

    dimensions = dimensions_from_anchors((scoring_config or {}).get("anchors"))
    dim_scores = compute_dimension_scores(clean, dimensions)
    return {
        "errors": errors,
        "dimension_scores": dim_scores,
        "overall_score": compute_overall_score(dim_scores),
    }
