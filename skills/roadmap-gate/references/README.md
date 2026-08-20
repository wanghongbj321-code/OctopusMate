# references

质检检查清单（六阶段 Q-gate 核心判定项 / 文件级 gate / 出口三段式）：
- 六阶段核心判定项（对齐 manifest gate 文本）：01 能力模型完整性·战略对齐 / 02 基线证据·基准独立性 / 03 战略关键性·业务所有权 / 04 未来状态可回溯·差距可解释 / 05 差距回溯·依赖可见 / 06 路线图完整性·依赖与资源可承受
- 文件级 gate（G0 复用）：confirmed md + confirmation 元数据（confirmed_by=user）+ content_hash + required artifacts + 非 stale
- 出口三段式（§6.6）：render_preflight → authorized → finalized；未 render_preflight 不可 authorized、未 authorized 不可 finalized
