"""M1-04 三态 gate 判定器：通过 / 有条件通过 / 回指。

判定分工（对齐 §6.5）：
- 语义型判定（愿景可想象/可沟通、六特质自检、五项检验一致性）由 AI 引导层执行，
  引擎只接收其建议（ai 参数），不自己做语义判断；
- 规则型判定（字段缺失、未决项无主等）由引擎模块（contract.py / open_issues.py）承担。
- 判定建议写入 state.json（本模块不直接改状态，由调用方写回）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

GATE_PASS = "pass"
GATE_CONDITIONAL = "conditional"
GATE_REGRESS = "regress"


@dataclass
class GateResult:
    status: str  # pass / conditional / regress
    reason: str = ""
    open_issue: dict | None = field(default=None)  # conditional 时待登记的未决项


def judge_gate(gate_conf: dict | None, ai: dict | None = None) -> GateResult:
    """三态判定。

    参数：
    - gate_conf: manifest steps[].gate（可为 None = 该步无 gate，直接通过）
    - ai: AI 引导层的语义判定建议，形如
          {"core_ok": bool,        # 核心判定项是否满足（如可想象/可沟通）
           "conditional": bool,    # 是否非核心项未满足（登记未决项后带项继续）
           "note": str}            # 判定说明
      规则（对齐 v2.1 §2.3）：
      - 核心判定项失败（core_ok=False）→ 回指（regress），即使有 conditional 也不得绕过
      - core_ok=True 且 conditional=True → 有条件通过（登记未决项）
      - core_ok=True 且 conditional=False → 通过
    """
    if gate_conf is None:
        return GateResult(status=GATE_PASS, reason="该步骤无 gate 判定")

    ai = ai or {}
    core_ok = ai.get("core_ok", True)
    conditional = ai.get("conditional", False)
    note = ai.get("note", "")

    if not core_ok:
        return GateResult(
            status=GATE_REGRESS,
            reason=f"核心判定项失败（{gate_conf.get('coreCheck', '')}）：{note}",
        )
    if conditional:
        return GateResult(
            status=GATE_CONDITIONAL,
            reason=f"非核心项未满足，登记未决项后带项继续：{note}",
            open_issue={
                "content": note or "未决项（AI 引导层补充登记内容）",
                "reason": "answer_unavailable",
                "resolveMode": "supplement",
            },
        )
    return GateResult(status=GATE_PASS, reason=f"通过（{gate_conf.get('pass', '')}）")
