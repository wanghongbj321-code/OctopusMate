# skills/

Skill 目录，对齐 init.md「distill 生产 / gate 质检 / render 输出」工程化拆分。规划结构：

```
skills/
├── vision-distill/        # 愿景生产（调用方法引擎 + 方法包）—— M1-07 创建
├── vision-gate/           # 愿景质检（出口校验 + 质量检验 + 视觉审计）—— M1-07 创建
├── vision-render/         # 确认包 HTML 输出（内置 visual-patterns/）—— M2-06 创建
└── methods/               # 方法插件（每个方法一个 Skill 包）
    ├── _shared/           # 平台共享模板（T5 六特质自检 / T10 未决清单）
    ├── octopus-7step/     # 内置方法 1：Octopus 7 步法（M2）
    ├── north-star/        # 内置方法 2：北极星指标法（M3）
    └── templates/vision-method-template/   # 用户安装脚手架（M4）
```

> 占位说明：各 skill 目录按开发计划里程碑（M1/M2/M3/M4）创建，创建前不登记入能力地图（标注「开发中」）。
