"""M1-02 evidence 模块单元测试：登记 / 编号 / 查重 / 交叉验证 / 无证据提示。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import evidence  # noqa: E402


class TestRegister(unittest.TestCase):
    """证据登记与编号。"""

    def test_register_auto_id(self):
        lst: list[dict] = []
        entry, errs = evidence.register(lst, "系统日志显示覆盖率 <40%", level="A",
                                        verification="按终端、SKU、月份抽样", supports=["I2"])
        self.assertEqual(errs, [])
        self.assertEqual(entry["id"], "E-01")
        self.assertEqual(entry["level"], "A")
        self.assertEqual(len(lst), 1)

    def test_register_increments_id(self):
        lst: list[dict] = []
        evidence.register(lst, "证据一", level="B")
        entry, _ = evidence.register(lst, "证据二", level="C")
        self.assertEqual(entry["id"], "E-02")

    def test_register_empty_rejected(self):
        lst: list[dict] = []
        entry, errs = evidence.register(lst, "   ", level="A")
        self.assertTrue(errs)
        self.assertEqual(entry, {})
        self.assertEqual(len(lst), 0)

    def test_register_bad_level_rejected(self):
        lst: list[dict] = []
        entry, errs = evidence.register(lst, "证据", level="D")
        self.assertTrue(any("等级" in e for e in errs))
        self.assertEqual(len(lst), 0)

    def test_register_explicit_id(self):
        lst: list[dict] = []
        entry, _ = evidence.register(lst, "证据", level="B", id_="E-99")
        self.assertEqual(entry["id"], "E-99")


class TestDuplicateCheck(unittest.TestCase):
    """证据查重。"""

    def test_duplicate_detected(self):
        lst: list[dict] = []
        evidence.register(lst, "DMS 接口清单无直连项", level="A")
        self.assertTrue(evidence.duplicate_check(lst, "DMS 接口清单无直连项"))
        self.assertTrue(evidence.duplicate_check(lst, "  dms 接口清单 无直连项 "))

    def test_not_duplicate(self):
        lst: list[dict] = []
        evidence.register(lst, "证据甲", level="B")
        self.assertFalse(evidence.duplicate_check(lst, "证据乙"))


class TestCrossValidation(unittest.TestCase):
    """重要事实双来源交叉验证。"""

    def test_two_sources_ok(self):
        lst: list[dict] = []
        evidence.register(lst, "制度文件", level="B", source_type="制度", supports=["V1"])
        evidence.register(lst, "访谈确认", level="C", source_type="访谈", supports=["V1"])
        ok, sources = evidence.cross_validation_ok(lst, "V1")
        self.assertTrue(ok)
        self.assertEqual(len(sources), 2)

    def test_single_source_not_ok(self):
        lst: list[dict] = []
        evidence.register(lst, "仅一个来源", level="B", source_type="制度", supports=["V1"])
        ok, _ = evidence.cross_validation_ok(lst, "V1")
        self.assertFalse(ok)

    def test_same_source_type_counted_once(self):
        lst: list[dict] = []
        evidence.register(lst, "材料一", level="B", source_type="制度", supports=["V1"])
        evidence.register(lst, "材料二", level="B", source_type="制度", supports=["V1"])
        ok, _ = evidence.cross_validation_ok(lst, "V1")
        self.assertFalse(ok)

    def test_no_support(self):
        ok, sources = evidence.cross_validation_ok([], "V1")
        self.assertFalse(ok)
        self.assertEqual(sources, [])


class TestUnverifiedAngles(unittest.TestCase):
    """无证据角度提示。"""

    def test_angles_without_evidence(self):
        lst: list[dict] = []
        evidence.register(lst, "支撑 V1", level="B", supports=["V1"])
        angles = evidence.unverified_angles({"V1": {}, "V2": {}, "I1": {}}, lst)
        self.assertEqual(sorted(angles), ["I1", "V2"])

    def test_all_verified(self):
        lst: list[dict] = []
        evidence.register(lst, "支撑", level="B", supports=["V1", "V2"])
        self.assertEqual(evidence.unverified_angles({"V1": {}, "V2": {}}, lst), [])

    def test_empty(self):
        self.assertEqual(evidence.unverified_angles({}, []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
