"""M1-09 新会话初始化测试（对齐 pratyaya Phase 0，无 group 层）。"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "vision-distill" / "scripts"))

from engine import session  # noqa: E402


class TestSession(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_slugify(self):
        self.assertEqual(session.slugify("AI Ops Vision"), "ai-ops-vision")
        self.assertEqual(session.slugify("ZhongRuan Power"), "zhongruan-power")
        self.assertEqual(session.slugify("客户_A!项目"), "a")  # 非 ASCII 被剔除
        self.assertEqual(session.slugify("中软电力转型"), "")  # 中文不猜测，需用户提供

    def test_plan_session_no_side_effect(self):
        """规划不落盘（确认前不创建目录、不写 state.json）。"""
        plan = session.plan_session(self.ws, "ZhongRuan Power", "AI Ops Vision")
        self.assertEqual(plan["project_slug"], "zhongruan-power")
        self.assertEqual(plan["topic_slug"], "ai-ops-vision")
        self.assertEqual(plan["conflicts"], [])
        self.assertFalse((self.ws / "zhongruan-power").exists())

    def test_create_session(self):
        """确认 slug 后建目录 + 写 state.json（无 group 层）。"""
        topic_dir = session.create_session(
            self.ws, "zhongruan-power", "中软电力转型", "ai-ops-vision", "AI 运维愿景"
        )
        self.assertTrue((topic_dir / "state.json").exists())
        self.assertTrue((topic_dir / "modules").is_dir())
        self.assertTrue((topic_dir / "output").is_dir())
        state = topic_dir / "state.json"
        import json
        data = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(data["project_slug"], "zhongruan-power")
        self.assertEqual(data["project_name"], "中软电力转型")
        self.assertEqual(data["topic_slug"], "ai-ops-vision")
        self.assertEqual(data["topic_name"], "AI 运维愿景")
        self.assertEqual(data["status"], "review_ready")
        self.assertNotIn("group", data)  # 无 group 层级

    def test_create_session_idempotent_and_locate(self):
        """重复创建幂等返回既有目录；locate_session 可定位。"""
        d1 = session.create_session(self.ws, "p", "P", "t", "T")
        d2 = session.create_session(self.ws, "p", "P", "t", "T")
        self.assertEqual(d1, d2)
        self.assertEqual(session.locate_session(self.ws, "p", "t"), d1)
        self.assertIsNone(session.locate_session(self.ws, "p", "missing"))

    def test_invalid_slug_rejected(self):
        with self.assertRaises(ValueError):
            session.create_session(self.ws, "中文项目", "P", "t", "T")


if __name__ == "__main__":
    unittest.main(verbosity=2)
