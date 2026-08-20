<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{页面标题}}</title>
<!-- 由 render_package.py 渲染：业务内容只来自阶段确认包 markdown，token 来自选定视觉模式 -->
<style>
  :root{
    --page-bg:#FFFFFF; --block-bg:#F7F7F7; --ink:#1A1A1A; --ink-deep:#2D2D2D;
    --ink-soft:#6B6B6B; --ink-muted:#808080; --border:#D4D4D4; --accent:#1A1A1A;
    --table-head:#F1F1F1; --callout:#FAFAFA;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--page-bg);color:var(--ink);line-height:1.6;}
  .page{width:min(1280px,calc(100vw - 48px));margin:0 auto;padding:28px 0 64px;}
  .report-header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:start;padding-bottom:18px;border-bottom:1px solid var(--border);}
  .report-kicker,.eyebrow{margin:0;color:var(--ink-soft);font-size:11px;font-weight:700;letter-spacing:.2em;line-height:1.4;text-transform:uppercase;}
  .report-title{margin:6px 0 0;color:var(--ink);font-size:15px;font-weight:700;}
  .report-subtitle{margin:2px 0 0;color:var(--ink-soft);font-size:12px;}
  .report-meta{display:grid;gap:8px;color:var(--ink-soft);font-size:12px;text-align:right;}
  .hero{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(300px,.6fr);gap:28px;padding:34px 0 24px;border-bottom:1px solid var(--border);}
  h1{margin:10px 0 0;color:var(--ink);font-size:26px;font-weight:700;line-height:1.4;}
  h2{color:var(--ink);font-size:20px;font-weight:700;line-height:1.4;}
  h3{color:var(--ink);font-size:15px;font-weight:600;line-height:1.4;}
  .lead{margin:14px 0 0;max-width:900px;color:var(--ink-deep);font-size:14px;line-height:1.75;}
  .so-what{padding:16px;border:1px solid var(--border);border-left:3px solid var(--ink);background:var(--block-bg);font-size:13px;color:var(--ink-deep);}
  .so-what h2{font-size:15px;}
  .so-what p{margin:8px 0 0;}
  .nav-strip{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;}
  .nav-strip a{padding:5px 8px;border:1px solid var(--border);color:var(--ink-soft);font-size:12px;text-decoration:none;}
  .summary-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr)) auto;gap:10px;margin-top:22px;}
  .summary-card{padding:13px;border:1px solid var(--border);background:var(--block-bg);font-size:12px;color:var(--ink-soft);}
  .summary-card strong{display:block;color:var(--ink);font-size:13px;line-height:1.5;}
  .summary-card p{margin:6px 0 0;}
  .summary-tag{padding:13px;border:1px solid var(--ink);font-size:12px;color:var(--ink-soft);}
  .summary-tag strong{display:block;color:var(--ink);font-size:26px;line-height:1.2;}
  .section{padding-top:34px;}
  .section-head{display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,.34fr);gap:24px;align-items:end;margin-bottom:14px;}
  .section-head p{margin:6px 0 0;color:var(--ink-soft);font-size:13px;}
  .section-note{margin:0;padding:11px;border:1px solid var(--border);background:var(--block-bg);color:var(--ink-deep);font-size:12px;}
  .logic-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;}
  .logic-node{padding:13px;border:1px solid var(--border);background:var(--block-bg);}
  .logic-node strong{display:block;margin-top:8px;color:var(--ink);font-size:14px;line-height:1.45;}
  .logic-node p{margin:6px 0 0;color:var(--ink-soft);font-size:12px;}
  .node-label{display:inline-block;color:var(--ink-muted);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;}
  .arch-row{display:grid;grid-template-columns:170px minmax(0,1fr);gap:10px;margin-bottom:10px;}
  .arch-label{padding:13px;border:1px solid var(--ink);font-size:13px;font-weight:700;color:var(--ink);}
  .arch-cells{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}
  .domain{padding:13px;border:1px solid var(--border);background:var(--block-bg);}
  .domain-top{display:flex;justify-content:space-between;gap:10px;}
  .domain-code{padding:3px 6px;border:1px solid var(--ink);font-size:11px;font-weight:700;}
  .domain p{margin:8px 0 0;color:var(--ink-soft);font-size:12px;}
  .classification{display:block;margin-top:10px;color:var(--ink-muted);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;}
  .table-wrap{overflow-x:auto;border:1px solid var(--border);background:var(--page-bg);}
  table{width:100%;min-width:900px;border-collapse:collapse;}
  th,td{padding:10px 12px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top;font-size:13px;line-height:1.5;}
  th{color:var(--ink);background:var(--table-head);border-bottom:2px solid var(--ink);font-weight:700;}
  td{color:var(--ink-deep);}
  caption{padding:9px 12px 5px;text-align:left;color:var(--ink-soft);font-size:12px;font-weight:700;}
  .quality-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}
  .quality-card{min-height:120px;padding:13px;border:1px solid var(--border);background:var(--block-bg);}
  .quality-card h3{font-size:14px;}
  .quality-card p{margin:8px 0 0;color:var(--ink-soft);font-size:12px;}
  .status{display:inline-block;margin-bottom:8px;padding-bottom:2px;color:var(--ink);border-bottom:1px solid var(--ink);font-size:12px;font-weight:700;}
  details.panel{margin-top:12px;border:1px solid var(--border);background:var(--block-bg);}
  details.panel summary{padding:11px 13px;color:var(--ink);font-size:13px;font-weight:700;cursor:pointer;}
  details.panel .panel-body{padding:0 13px 13px;color:var(--ink-deep);font-size:13px;}
  .action-table{margin-top:12px;}
  .pill{display:inline-block;padding:3px 6px;border:1px solid var(--ink);color:var(--ink);background:var(--page-bg);font-size:12px;white-space:nowrap;}
  .report-footer{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;margin-top:40px;padding-top:13px;border-top:1px solid var(--border);color:var(--ink-muted);font-size:11px;}
  @media (max-width:980px){
    .hero,.report-header,.section-head,.arch-row{grid-template-columns:1fr;}
    .summary-strip,.logic-grid,.arch-cells,.quality-grid{grid-template-columns:1fr;}
    .report-meta{text-align:left;}
  }
  @media print{.page{width:auto;padding:0;}.nav-strip{display:none;}}
</style>
</head>
<body>
  <div class="page">
    <header class="report-header">
      <div>
        <p class="report-kicker">Capability Roadmap · {{阶段编号}} · {{版本}}</p>
        <p class="report-title">{{项目名称}} · {{主题名称}}</p>
        <p class="report-subtitle">{{阶段交付物名称}} · Illustrative exhibit</p>
      </div>
      <div class="report-meta" aria-label="交付物元信息">
        <span>阶段：{{阶段编号}}</span>
        <span>对象：{{阶段对象}}</span>
        <span>状态：{{质量门状态}}</span>
      </div>
    </header>

    <main>
