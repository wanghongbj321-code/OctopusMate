"""M2 验收测试：六阶段产物 md 管线——md 契约 + 契约校验器 + 六阶段写函数。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M2-01 ~ M2-07
      （六阶段 md 契约全部定义并接入校验；mock 六阶段 md 通过/被阻断行为正确）
      M0-01 差距清单 G1/G2/G3/G9（白名单 / id 命名空间 / 写函数 / 产物命名随 M2 落地）

覆盖：
- 六阶段契约定义齐全（artifact_type / artifact_id / 文件名前缀 / 结构化数据块）
- 每阶段写函数生成 confirmed md → read_roadmap_artifact 契约校验通过（正例）
- 被阻断行为：缺字段 / 未 confirmed（draft）/ 伪造 confirmed_by=ai / 枚举非法 /
  结构化数据块缺失 / confirmed_content_hash 不一致
- 阶段特殊规则：02 六维完整性（3/6/9 能力域样例，不硬编码数量）/
  03 条件重点裁决 + 排除理由 / 04 差距级别 + AI 风险控制 / 06 里程碑 M·G·D + O7 六项
- 写函数：版本不覆盖 / manifest 登记 / source_refs 前置链 / draft 不推进
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import files, roadmap  # noqa: E402
from _engine.roadmap import (  # noqa: E402
    O7_KEYS,
    ROADMAP_ARTIFACT_IDS,
    ROADMAP_ARTIFACT_TYPES,
    ROADMAP_CONTRACTS,
    ROADMAP_STEP_IDS,
    ROADMAP_STEP_META,
    extract_data_block,
    read_roadmap_artifact,
    validate_roadmap_contract,
    write_roadmap_step_artifact,
)

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:12:用户明确确认采用本版能力模型草稿",
    "confirmation_text": "用户明确确认采用本版草稿",
}


# --- mock 六阶段数据（业务数据占位，对齐方法论 T1-T13 字段） ---

def mock_step01():
    return {
        "capabilityModel": {
            "qualityGate": "pass",
            "valueConnections": [
                {"vision": "门店获得适合自己的商品策略", "businessResult": "铺货质量与终端动销",
                 "intermediateBenefit": "更准分群与更快试验", "enabler": "主数据与交易信号",
                 "capabilityId": "C1", "mission": "让门店获得适合自己的策略", "benefitCase": "BC-1"},
            ],
            "clusters": [
                {"id": "C1", "name": "渠道与门店策略管理", "commonDenominator": "端到端流程",
                 "classification": "Core", "rationale": "直接支撑战略交付与竞争优势",
                 "modelOwner": "销售 VP",
                 "capabilities": [
                     {"id": "C1-1", "name": "门店分群与画像", "level": "L2", "mission": "精准分群",
                      "purpose": "支撑差异化策略", "valueSource": "业务结果", "aiDependency": "高"},
                     {"id": "C1-2", "name": "门店级策略制定", "level": "L2", "mission": "制定门店策略",
                      "purpose": "支撑铺货质量", "valueSource": "价值流", "aiDependency": "中"},
                 ]},
            ],
            "modelingChecks": [
                {"checkItem": item, "conclusion": "通过", "issue": "", "handling": ""}
                for item in ("命名", "层级", "MECE", "粒度", "稳定性", "版本治理")
            ],
            "valueStreamChecks": [
                {"valueStream": "铺货价值流", "stage": "策略制定", "capabilities": "C1",
                 "conclusion": "覆盖完整", "priorityCandidate": "是"},
            ],
        }
    }


def mock_step02(n_caps: int = 3):
    """n_caps 个能力域（3/6/9 样例验证能力域数可变）。"""
    caps = []
    for i in range(1, n_caps + 1):
        caps.append({
            "id": f"C{i}", "name": f"能力域 {i}",
            "baseline": {dim: f"{dim} 当前状态 {i}" for dim in
                         ("mission", "insights", "process", "technology", "talent", "governance")},
            "maturity": "Performing", "rationale": "整体判断", "evidenceStrength": "B",
            "evidenceGap": "",
        })
    return {
        "maturityBaseline": {
            "qualityGate": "pass",
            "capabilities": caps,
            "compositeMaturityNote": "基于六维当前状态与独立基准的整体判断，不设加权评分公式",
            "benchmarks": [
                {"capabilityId": f"C{i}", "mandatory": "强制要求", "professional": "正常专业要求",
                 "peer": "同行基准", "commonPractice": "普遍实践", "leadingPractice": "领先实践",
                 "source": "行业标准", "applicability": "行业/规模/模式相似"} for i in range(1, n_caps + 1)
            ],
            "calibration": [
                {"capabilityId": f"C{i}", "item": "成熟度", "strength": "B", "conflictEvidence": "",
                 "provisionalJudgment": "", "calibrationConclusion": "口径一致", "verification": "回测"}
                for i in range(1, n_caps + 1)
            ],
        }
    }


def mock_step03():
    return {
        "priorityCapabilities": {
            "qualityGate": "conditional",
            "priorityList": [
                {"capabilityId": "C1", "enterpriseViewRationale": "对总体方向最关键",
                 "domainViewRationale": "域内关键差距", "valueTraceback": "可回溯愿景与价值实现",
                 "valueStreamCheck": "支撑关键价值流", "maturityInfo": "Performing",
                 "businessOwner": "销售 VP", "governanceRoles": ["Capability", "Data"],
                 "conditional": False, "conditionalNote": "", "decisionArrange": ""},
                {"capabilityId": "C5", "enterpriseViewRationale": "战略关键性证据待补",
                 "domainViewRationale": "域内关键差距", "valueTraceback": "待补证",
                 "valueStreamCheck": "影响多条价值流", "maturityInfo": "Lagging",
                 "businessOwner": "供应链 VP", "governanceRoles": ["Capability"],
                 "conditional": True, "conditionalNote": "关键数据缺失",
                 "decisionArrange": "挂 T12·U-03，责任人=供应链 VP，拟补强证据后裁决，时限=阶段 06 决策门 D1"},
            ],
            "excluded": [
                {"capabilityId": "C4", "reason": "非关键差距且非部门诉求，成熟度已达标"},
            ],
        }
    }


def mock_step04():
    return {
        "futureStateGaps": {
            "qualityGate": "pass",
            "gaps": [
                {"capabilityId": "C1", "dimension": "technology",
                 "currentState": "无策略引擎", "futureState": "门店级策略引擎",
                 "gap": "缺策略引擎与接口", "level": "大", "requirementSource": "战略", "impact": "策略闭环"},
                {"capabilityId": "C1", "dimension": "talent",
                 "currentState": "无专职角色", "futureState": "策略分析师角色",
                 "gap": "缺角色与技能", "level": "中", "requirementSource": "设计判断", "impact": "运营"},
            ],
            "gapProfiles": [
                {"capabilityId": "C1", "profile": "技术单维大差距，整体中幅"},
            ],
            "aiConditions": [
                {"aiObject": "门店策略推荐", "checkItem": "AI 治理", "currentGap": "无风险分级",
                 "futureRequirement": "AI 风险分级与可信治理", "mappedDimension": "Governance",
                 "entersInitiative": "是"},
            ],
            "aiRiskControls": [
                {"aiObject": "门店策略推荐", "riskLevel": "中", "trustFeatures": "可解释、透明",
                 "keyControls": "人工复核 + 例外处理", "mappedDimensions": "Governance",
                 "owner": "数据治理组", "lifecycleCheckpoints": "设计/验证/上线/监控"},
            ],
        }
    }


def mock_step05():
    return {
        "gapInitiatives": {
            "qualityGate": "pass",
            "initiatives": [
                {"id": "I-01", "capabilityId": "C1", "gap": "缺策略引擎",
                 "action": "建设门店级策略引擎", "valueRelation": "弥合关键技术差距",
                 "dependency": "依赖主数据治理", "costComplexity": "中",
                 "verification": "区域试点", "owner": "销售 VP", "tradeoffRationale": "依赖关键性",
                 "domainOrder": 1},
            ],
            "tradeoffs": [
                {"initiativeId": "I-01", "strategicNecessity": "高", "valueCertainty": "中",
                 "dependencyCriticality": "高", "riskExposure": "中", "orgCapacity": "可承受",
                 "learningValue": "中", "conclusion": "前置", "decisionRecord": "保留"},
            ],
            "techPreChecks": [
                {"initiativeId": "I-01", "insights": "数据先行", "process": "流程并行",
                 "talent": "需补角色", "governance": "治理并行", "conclusion": "数据先行"},
            ],
            "aiLayers": [
                {"layer": "用例专属", "initiatives": "I-01"},
                {"layer": "共同数据基础", "initiatives": "I-02"},
            ],
        }
    }


def mock_step06():
    return {
        "enterpriseRoadmap": {
            "qualityGate": "pass",
            "sortClusters": [
                {"id": "SC-1", "name": "底座关键路径", "representativeInitiatives": "I-01、I-02",
                 "valueContribution": "规模化前置", "dependencyMaturity": "就绪",
                 "constraints": "资源紧张", "conclusion": "先行投入"},
            ],
            "phases": [
                {"phase": "夯实基本盘", "goal": "弥补关键能力缺口", "keyInitiatives": "I-01",
                 "capabilities": "C1", "dependencies": "主数据", "resources": "中投入",
                 "valueValidation": "区域试点", "outcomeMetrics": "业务/能力/采用/风险"},
                {"phase": "增长与规模化", "goal": "强化运营系统", "keyInitiatives": "I-03",
                 "capabilities": "C2", "dependencies": "平台", "resources": "大投入",
                 "valueValidation": "规模化验证", "outcomeMetrics": "业务/能力/采用/风险"},
                {"phase": "再定位与重塑", "goal": "配置战略投入", "keyInitiatives": "I-05",
                 "capabilities": "C3", "dependencies": "组织", "resources": "专项投入",
                 "valueValidation": "价值释放评估", "outcomeMetrics": "业务/能力/采用/风险"},
            ],
            "milestones": [
                {"id": "M1", "type": "M", "name": "策略引擎可验证节点", "phase": "夯实基本盘",
                 "dependsOn": "", "month": "2026-11"},
                {"id": "G1", "type": "G", "name": "阶段一目标达成判定", "phase": "夯实基本盘",
                 "dependsOn": "M1", "month": "2027-02"},
                {"id": "D1", "type": "D", "name": "C5 条件能力裁决", "phase": "夯实基本盘",
                 "dependsOn": "", "month": "2026-11"},
            ],
            "metricsReview": [
                {"phase": "夯实基本盘", "metricType": "业务结果", "name": "终端动销率",
                 "baseline": "口径说明", "dataSource": "销售系统", "owner": "销售 VP",
                 "frequency": "月", "reviewRhythm": "月度跟踪/季度复审", "triggers": "价值假设失效"},
            ],
            "consistency": [
                {"layer": layer, "conclusion": "通过", "openIssues": ""}
                for layer in ("Strategy", "Business Model", "Operating Model",
                              "Enabling Technology & Infrastructure")
            ],
            "governance": [
                {"item": "跨能力资源冲突", "type": "跨能力", "involvedInitiatives": "I-01、I-03",
                 "decisionMaker": "组合治理", "risk": "资源争夺", "tradeoffQuestion": "",
                 "reviewRhythm": "季度复审", "status": "跟踪中"},
            ],
        },
        "downstreamInterfaces": {
            "endToEndSolution": "待补",
            "targetOperatingModel": "不适用",
            "detailedImplementationPlan": "待补",
            "benefitCase": "待补",
            "enterpriseArchitecture": "不适用",
            "portfolioGovernance": "待补",
        },
    }


MOCK_STEPS = {
    "01": mock_step01,
    "02": mock_step02,
    "03": mock_step03,
    "04": mock_step04,
    "05": mock_step05,
    "06": mock_step06,
}


def _make_state(tmp: Path) -> dict:
    from _engine import session, state as state_mod

    topic_dir = session.create_session(tmp, "m2-proj", "M2 项目", "m2-topic", "M2 主题")
    return topic_dir, state_mod.load_state(topic_dir / "state.json")


class TestStepContractsDefined(unittest.TestCase):
    """M2-01~06 契约定义齐全（artifact_type / id / 文件名前缀 / 结构化数据块键）。"""

    def test_six_step_contracts_all_defined(self):
        self.assertEqual(set(ROADMAP_CONTRACTS), set(ROADMAP_STEP_IDS))

    def test_artifact_types_and_ids_match_plan(self):
        expected_types = {f"roadmap-step{i}" for i in ROADMAP_STEP_IDS}
        self.assertEqual(ROADMAP_ARTIFACT_TYPES, expected_types)
        expected_ids = {
            "roadmap.capabilityModel.current",
            "roadmap.maturityBaseline.current",
            "roadmap.priorityCapabilities.current",
            "roadmap.futureStateGaps.current",
            "roadmap.gapInitiatives.current",
            "roadmap.enterpriseRoadmap.current",
        }
        self.assertEqual(ROADMAP_ARTIFACT_IDS, expected_ids)

    def test_filenames_match_plan_sec5_1(self):
        expected_prefixes = {
            "01": "capability-model", "02": "baseline-maturity", "03": "priority-capabilities",
            "04": "future-state", "05": "gap-initiatives", "06": "capability-roadmap",
        }
        for step, prefix in expected_prefixes.items():
            self.assertEqual(ROADMAP_STEP_META[step]["file_prefix"], prefix)
            self.assertEqual(files._ARTIFACT_FILENAME[ROADMAP_STEP_META[step]["artifact_type"]],
                             f"{prefix}-{{topic_slug}}-v{{N}}.md")

    def test_prereq_chain_matches_sec6_2(self):
        from _engine.roadmap import PREREQ_STEPS

        self.assertEqual(PREREQ_STEPS["02"], ("01",))
        self.assertEqual(PREREQ_STEPS["03"], ("01", "02"))
        self.assertEqual(PREREQ_STEPS["06"], ("01", "02", "03", "04", "05"))

    def test_contract_required_fields_non_empty(self):
        for step, contract in ROADMAP_CONTRACTS.items():
            self.assertTrue(contract.required_paths, f"阶段 {step} 契约无必填字段")


class TestWriteAndValidateHappyPath(unittest.TestCase):
    """正例：六阶段写函数生成 confirmed md → 契约校验通过。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state = _make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_confirmed(self, step: str, data: dict):
        return write_roadmap_step_artifact(
            self.topic_dir, step, data, confirmation=CONFIRMATION, state=self.state)

    def test_all_six_steps_pass_contract(self):
        for step in ROADMAP_STEP_IDS:
            data = MOCK_STEPS[step]()
            path = self._write_confirmed(step, data)
            self.assertTrue(path.exists(), f"阶段 {step} 产物未生成")
            ra = read_roadmap_artifact(path)
            self.assertTrue(ra.valid, f"阶段 {step} 契约校验失败：{ra.errors}")
            self.assertEqual(ra.artifact.meta["confirmation"]["confirmed_by"], "user")
            self.assertEqual(ra.artifact.meta["status"], "confirmed")

    def test_md_body_contains_human_sections_and_data_block(self):
        path = self._write_confirmed("01", mock_step01())
        text = path.read_text(encoding="utf-8")
        self.assertIn("## 价值-能力连接（T1）", text)
        self.assertIn("## 结构化数据块", text)
        self.assertIn("```yaml", text)
        data = extract_data_block(text.split("---", 2)[-1])
        self.assertEqual(data["capabilityModel"]["qualityGate"], "pass")

    def test_manifest_registered_with_hash(self):
        self._write_confirmed("01", mock_step01())
        entry = self.state["artifacts"]["roadmap.capabilityModel.current"]
        self.assertEqual(entry["status"], "confirmed")
        self.assertEqual(entry["version"], 1)
        self.assertTrue(entry["content_hash"].startswith("sha256:"))

    def test_version_not_overwritten(self):
        # draft v1 → confirmed v2（版本化不覆盖）
        write_roadmap_step_artifact(self.topic_dir, "01", mock_step01(), status="draft", state=self.state)
        p2 = self._write_confirmed("01", mock_step01())
        self.assertEqual(p2.name, "capability-model-m2-topic-v2.md")
        self.assertTrue((self.topic_dir / "modules" / "capability-model-m2-topic-v1.md").exists())

    def test_source_refs_prereq_chain(self):
        """阶段 02 source_refs 指向阶段 01 confirmed 当前版本（M4 stale 依赖图依据）。"""
        self._write_confirmed("01", mock_step01())
        p2 = self._write_confirmed("02", mock_step02())
        ra = read_roadmap_artifact(p2)
        self.assertTrue(ra.valid, ra.errors)
        refs = ra.artifact.meta["source_refs"]
        self.assertIn("roadmap.capabilityModel.current@v1", refs)


class TestBlockedBehavior(unittest.TestCase):
    """负例：缺字段 / 未 confirmed / 伪造确认 / 枚举非法 / 数据块缺失 均被阻断。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state = _make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, step: str, data: dict, confirmation=None, status="confirmed"):
        return write_roadmap_step_artifact(
            self.topic_dir, step, data, confirmation=confirmation or CONFIRMATION,
            state=self.state, status=status)

    def _read_errors(self, step: str, data: dict) -> list:
        path = self._write(step, data)
        return read_roadmap_artifact(path).errors

    def test_draft_not_advanceable(self):
        """draft 未 confirmed → 契约阻断（status != confirmed）。"""
        p = write_roadmap_step_artifact(self.topic_dir, "01", mock_step01(), status="draft", state=self.state)
        ra = read_roadmap_artifact(p)
        self.assertFalse(ra.valid)
        self.assertTrue(any("confirmed" in e for e in ra.contract_errors), ra.contract_errors)

    def test_missing_field_blocked_per_step(self):
        """每阶段删除一个核心必填字段 → 阻断（M2 完成标准：缺字段被规则型阻断）。"""
        cases = {
            "01": (mock_step01(), ("capabilityModel", "clusters")),
            "02": (mock_step02(), ("maturityBaseline", "compositeMaturityNote")),
            "03": (mock_step03(), ("priorityCapabilities", "excluded")),
            "04": (mock_step04(), ("futureStateGaps", "aiRiskControls")),
            "05": (mock_step05(), ("gapInitiatives", "techPreChecks")),
            "06": (mock_step06(), ("enterpriseRoadmap", "milestones")),
        }
        for step, (data, (top, key)) in cases.items():
            data = dict(data)
            data[top] = {k: v for k, v in data[top].items() if k != key}
            errors = self._read_errors(step, data)
            self.assertTrue(errors, f"阶段 {step} 删 {key} 应被阻断")

    def test_forged_ai_confirmation_blocked(self):
        """伪造确认：confirmed_by=ai → 契约阻断（强确认链凭据）。"""
        from _engine.roadmap import _step_body

        data = mock_step01()
        text = ("---\n"
                "artifact_type: roadmap-step01\n"
                "artifact_id: roadmap.capabilityModel.current\n"
                "version: 1\n"
                "status: confirmed\n"
                "source_refs: []\n"
                "content_hash: \"sha256:{0}\"\n"
                "confirmation:\n"
                "  status: confirmed\n"
                "  confirmed_by: ai\n"
                "  confirmed_at: \"2026-08-20T14:00:00+08:00\"\n"
                "  interaction_ref: \"transcript:9\"\n"
                "  confirmed_content_hash: \"sha256:{0}\"\n"
                "---\n\n{1}").format("0" * 64, _step_body("01", data, self.state))
        errors = validate_roadmap_contract("roadmap-step01", text)
        self.assertTrue(any("confirmed_by" in e or "确认凭据" in e for e in errors), errors)

    def test_bad_enum_blocked(self):
        """枚举非法：成熟度档位 / 差距级别 / 里程碑类型 / 战略分类。"""
        # 成熟度非法
        d02 = mock_step02()
        d02["maturityBaseline"]["capabilities"][0]["maturity"] = "Advanced"
        errors = self._read_errors("02", d02)
        self.assertTrue(any("成熟度档位非法" in e for e in errors), errors)
        # 差距级别非法
        d04 = mock_step04()
        d04["futureStateGaps"]["gaps"][0]["level"] = "特大"
        errors = self._read_errors("04", d04)
        self.assertTrue(any("差距级别非法" in e for e in errors), errors)
        # 里程碑类型非法
        d06 = mock_step06()
        d06["enterpriseRoadmap"]["milestones"][0]["type"] = "X"
        errors = self._read_errors("06", d06)
        self.assertTrue(any("里程碑节点类型非法" in e for e in errors), errors)
        # 战略分类非法
        d01 = mock_step01()
        d01["capabilityModel"]["clusters"][0]["classification"] = "Strategic-Core"
        errors = self._read_errors("01", d01)
        self.assertTrue(any("战略性质分类非法" in e for e in errors), errors)

    def test_missing_data_block_blocked(self):
        """无结构化数据块 → 阻断（R12：渲染/审计共用结构化数据层）。"""
        body = "# 阶段 01 · 能力模型\n\n## 人类可读确认摘要\n- 无数据块"
        text = ("---\n"
                "artifact_type: roadmap-step01\n"
                "artifact_id: roadmap.capabilityModel.current\n"
                "version: 1\n"
                "status: confirmed\n"
                "source_refs: []\n"
                "content_hash: \"sha256:{0}\"\n"
                "confirmation:\n"
                "  status: confirmed\n"
                "  confirmed_by: user\n"
                "  confirmed_at: \"2026-08-20T14:00:00+08:00\"\n"
                "  interaction_ref: \"x\"\n"
                "  confirmed_content_hash: \"sha256:{0}\"\n"
                "---\n\n{1}").format("0" * 64, body)
        errors = validate_roadmap_contract("roadmap-step01", text)
        self.assertTrue(any("结构化数据块" in e for e in errors), errors)


class TestStepSpecialRules(unittest.TestCase):
    """阶段特殊规则：02 六维完整性 / 03 条件重点 + 排除理由 / 04 AI 风险 / 06 O7。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state = _make_state(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _errors(self, step: str, data: dict) -> list:
        path = write_roadmap_step_artifact(
            self.topic_dir, step, data, confirmation=CONFIRMATION, state=self.state)
        return read_roadmap_artifact(path).errors

    def test_step02_dimension_completeness_3_6_9(self):
        """能力域数 × 6 维完整性：3/6/9 域样例均通过（不硬编码 6 个能力域，R11）。"""
        for n in (3, 6, 9):
            errors = self._errors("02", mock_step02(n))
            self.assertEqual(errors, [], f"{n} 能力域应通过：{errors}")

    def test_step02_missing_one_dimension_blocked(self):
        d = mock_step02(3)
        del d["maturityBaseline"]["capabilities"][1]["baseline"]["technology"]
        errors = self._errors("02", d)
        self.assertTrue(any("六维基线缺失 Technology" in e for e in errors), errors)

    def test_step03_conditional_priority_requires_decision(self):
        d = mock_step03()
        for p in d["priorityCapabilities"]["priorityList"]:
            if p["capabilityId"] == "C5":
                p["decisionArrange"] = ""
        errors = self._errors("03", d)
        self.assertTrue(any("条件重点能力 C5 缺少裁决安排" in e for e in errors), errors)

    def test_step03_exclusion_reason_required(self):
        d = mock_step03()
        d["priorityCapabilities"]["excluded"][0]["reason"] = ""
        errors = self._errors("03", d)
        self.assertTrue(any("非重点排除理由" in e for e in errors), errors)

    def test_step04_ai_risk_control_fields(self):
        d = mock_step04()
        d["futureStateGaps"]["aiRiskControls"][0]["lifecycleCheckpoints"] = ""
        errors = self._errors("04", d)
        self.assertTrue(any("生命周期检查点" in e for e in errors), errors)

    def test_step06_milestone_m_g_d_types(self):
        d = mock_step06()
        types = {m["type"] for m in d["enterpriseRoadmap"]["milestones"]}
        self.assertEqual(types, {"M", "G", "D"})

    def test_step06_o7_all_six_required(self):
        """O7 六项允许写不适用/待补但不可缺失。"""
        d = mock_step06()
        d["downstreamInterfaces"] = {"endToEndSolution": "待补"}
        errors = self._errors("06", d)
        self.assertEqual(len([e for e in errors if "下游接口摘要缺失" in e]), len(O7_KEYS) - 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
