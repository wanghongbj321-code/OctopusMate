"""F9 包结构契约测试（防 P2/P3/P4/P5 类上架问题回归）。

验证 plugin.json 声明的结构与实际文件系统一致：
- skills 路径 → 目录存在且含 SKILL.md（防 P3：方法插件缺 SKILL.md）
- agents 路径 → 文件存在（防 P4：agents 目录误放非 Agent 文件）
- avatar 路径 → 文件存在且 ≤500KB（防 P5：头像超规范）
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_AVATAR_BYTES = 500 * 1024


def _load_plugin_json() -> dict:
    for meta_dir in (".codebuddy-plugin", ".workbuddy-plugin"):
        p = ROOT / meta_dir / "plugin.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("plugin.json not found (checked .codebuddy-plugin/ and .workbuddy-plugin/)")


class TestPackageStructure(unittest.TestCase):
    """包结构契约：plugin.json 声明与磁盘文件一致。"""

    @classmethod
    def setUpClass(cls):
        cls.plugin = _load_plugin_json()

    def test_skills_paths_have_skill_md(self):
        """每个声明的 skills 路径必须存在且含 SKILL.md（防 P3 回归）。"""
        skills = self.plugin.get("skills", [])
        self.assertGreater(len(skills), 0, "plugin.json 应至少声明一个 skill")
        for rel in skills:
            d = (ROOT / rel.lstrip("./")).resolve()
            self.assertTrue(d.is_dir(), f"skill 路径不存在：{rel}")
            self.assertTrue(
                (d / "SKILL.md").is_file(),
                f"skill 路径缺 SKILL.md：{rel}（校验脚本要求每个声明的 skill 有入口文件）",
            )

    def test_agents_paths_exist(self):
        """每个声明的 agents 路径必须存在（防 P4 同类回归）。"""
        agents = self.plugin.get("agents", [])
        self.assertGreater(len(agents), 0, "plugin.json 应至少声明一个 agent")
        for rel in agents:
            f = (ROOT / rel.lstrip("./")).resolve()
            self.assertTrue(f.is_file(), f"agent 路径不存在：{rel}")

    def test_agents_dir_only_has_agent_mds(self):
        """agents/ 目录只允许 Agent MD（有 frontmatter），不放 README 等说明文件（防 P4 回归）。"""
        agents_dir = ROOT / "agents"
        for f in agents_dir.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            self.assertTrue(
                text.startswith("---"),
                f"agents/{f.name} 无 YAML frontmatter，会被校验脚本误判为 Agent MD（应移出 agents/）",
            )

    def test_avatar_within_size_limit(self):
        """avatar 文件必须存在且 ≤500KB（防 P5 回归）。"""
        rel = self.plugin.get("avatar", "")
        self.assertTrue(rel, "plugin.json 应声明 avatar")
        f = (ROOT / rel.lstrip("./")).resolve()
        self.assertTrue(f.is_file(), f"avatar 文件不存在：{rel}")
        size = f.stat().st_size
        self.assertLessEqual(size, MAX_AVATAR_BYTES, f"avatar {rel} 大小 {size} 字节 > 500KB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
