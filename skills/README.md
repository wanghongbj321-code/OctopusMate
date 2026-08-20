# skills/

Skill 目录，对齐 init.md「distill 生产 / gate 质检 / render 输出」工程化拆分。规划结构：

```
skills/
├── _engine/               # 平台方法引擎（manifest 解析 / 步骤执行 / 三态 gate / 文件级 gate / 契约校验 / 未决清单）
├── vision-distill/        # 愿景生产（调用方法引擎 + 方法包）
├── vision-gate/           # 愿景质检（出口校验 + 质量检验 + 视觉审计）
├── diagnosis-distill/     # 诊断生产（VITAL 五维，22 角度打分 + 证据记录 + 阻断识别）
├── diagnosis-gate/        # 诊断质检（contract diagnosis 分支 + 评分/证据/阻断一致性复核）
├── roadmap-distill/       # 能力路线图生产（capability-roadmap 六阶段 + 强确认链）—— M1-05 创建
├── roadmap-gate/          # 能力路线图质检（contract roadmap 分支 + 文件级 gate + 六阶段质量检验）—— M1-05 创建
├── deliverable-render/    # 交付物 HTML 输出（多画布：vision-confirm / diagnosis-report / capability-package）
├── octopus-faq/           # 官方自我介绍与常见问题（references/FAQ.md 为事实源）
└── methods/               # 方法插件（每个方法一个 Skill 包）
    ├── _shared/           # 平台共享模板（T5 六特质自检 / T10 未决清单 vision 版 / T10 路线图表 / T12 未决清单 roadmap 完整版 / T13 下一步行动）
    ├── octopus-7step/     # 内置方法 1：Octopus 7 步法
    ├── north-star/        # 内置方法 2：北极星指标法
    ├── golden-circle/     # 内置方法 3：黄金圈
    ├── vital-diagnosis/   # 内置方法 4：VITAL 五维诊断（diagnosis-method）
    ├── capability-roadmap/ # 内置方法 5：构建企业能力路线图（roadmap-method，六阶段）—— M1 创建
    └── templates/vision-method-template/   # 用户安装脚手架
```

> 说明：各 skill 目录按开发计划里程碑创建；roadmap 域（distill/gate + capability-roadmap 方法）已随 M1 落地，其余目录按各自里程碑推进。
