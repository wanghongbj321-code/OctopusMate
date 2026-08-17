# schemas/

结构化数据 Schema 目录（JSON Schema，draft-07）：

| 文件 | 用途 | 对应里程碑 |
|---|---|---|
| `state.json.schema.json` | 会话状态 state.json（项目/Topic 元数据 + 状态机 review_ready → authorized → finalized + 未决清单 + 产物索引） | M0-04 |
| `manifest.schema.json` | 方法插件 manifest.yaml（name/version/type/steps/gate/aiConstraints/outputContract） | M0-05 |

使用：`tests/contract_consistency.py` 读取本目录 schema 做契约一致性校验。
