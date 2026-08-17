# tests/

测试与契约一致性检查目录（对齐 pratyaya 工程化范式）：

| 文件 | 用途 |
|---|---|
| `contract_consistency.py` | 契约一致性校验器：manifest.yaml ↔ manifest.schema.json（纯标准库，零依赖） |
| `test_contract_consistency.py` | 校验器单元测试（unittest）：合法/非法/空跑 |
| `fixtures/` | 测试样例（合法/非法 manifest、state 样例） |

运行：

```bash
# 空跑（当前无 manifest 时 0 失败）
python3 tests/contract_consistency.py

# 单元测试
python3 -m unittest discover -s tests -v
```

> M5 将扩展：gate 三态判定单测、状态机流转测试、视觉审计。
