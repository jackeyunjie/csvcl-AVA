#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XAUUSD 多时间框架技术面观测雷达图与因子图生成器
基于 RSIOMA + 枢轴点 + H1/H4 SR 指标分析
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# ============================================================
# 数据定义
# ============================================================

# 雷达图维度
dimensions = [
    "趋势强度",
    "RSIOMA动量",
    "SR结构",
    "多周期共振",
    "波动率收缩",
    "反转确认",
    "风险可控性",
]

# 三组观测值（满分 10）
current = [6, 7, 8, 7, 8, 7, 6]
ideal = [8, 9, 9, 9, 8, 9, 8]
weak = [4, 4, 5, 4, 5, 3, 4]

# 因子数据（影响方向、强度、置信度）
factors = [
    {"name": "H4 SR 下沿支撑有效", "score": 8, "confidence": 8, "category": "支撑"},
    {"name": "H1 SR 带收缩", "score": 7, "confidence": 7, "category": "结构"},
    {"name": "1日/3日枢轴收敛", "score": 6, "confidence": 6, "category": "结构"},
    {"name": "RSIOMA 低位金叉", "score": 8, "confidence": 8, "category": "动量"},
    {"name": "ADX 趋势强度配合", "score": 5, "confidence": 6, "category": "动量"},
    {"name": "假跌破后快速收回", "score": 7, "confidence": 7, "category": "价格行为"},
    {"name": "上方 H4 阻力仍存", "score": -4, "confidence": 6, "category": "阻力"},
    {"name": "宏观事件不确定性", "score": -3, "confidence": 5, "category": "风险"},
]

# 多时间框架评分矩阵
timeframe_data = {
    "时间框架": ["M15", "M30", "H1", "H4"],
    "趋势方向": ["震荡偏多", "偏多", "偏多", "震荡"],
    "SR 收缩度": [8, 7, 6, 5],
    "反转信号强度": [7, 8, 6, 5],
    "可信度": [6, 7, 7, 6],
}

# ============================================================
# 图表 1：雷达图
# ============================================================
radar_fig = go.Figure()

radar_fig.add_trace(go.Scatterpolar(
    r=current + [current[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='当前 XAUUSD 观测',
    line_color='#00BCD4',
    fillcolor='rgba(0, 188, 212, 0.25)',
))

radar_fig.add_trace(go.Scatterpolar(
    r=ideal + [ideal[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='理想反转突破场景',
    line_color='#4CAF50',
    fillcolor='rgba(76, 175, 80, 0.15)',
))

radar_fig.add_trace(go.Scatterpolar(
    r=weak + [weak[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='弱势/假突破警戒',
    line_color='#F44336',
    fillcolor='rgba(244, 67, 54, 0.15)',
))

radar_fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 10],
            tickvals=[2, 4, 6, 8, 10],
            ticktext=["2", "4", "6", "8", "10"],
        ),
        angularaxis=dict(direction="clockwise"),
    ),
    showlegend=True,
    title=dict(
        text="XAUUSD 多时间框架技术面观测雷达图",
        x=0.5,
        font=dict(size=20),
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.15,
        xanchor="center",
        x=0.5,
    ),
    height=600,
    template="plotly_white",
)

# ============================================================
# 图表 2：因子贡献条形图
# ============================================================
factor_names = [f["name"] for f in factors]
factor_scores = [f["score"] for f in factors]
factor_colors = ['#4CAF50' if s > 0 else '#F44336' for s in factor_scores]

factor_fig = go.Figure()

factor_fig.add_trace(go.Bar(
    y=factor_names,
    x=factor_scores,
    orientation='h',
    marker_color=factor_colors,
    text=[f"{s:+.0f}" for s in factor_scores],
    textposition='outside',
    hovertemplate='<b>%{y}</b><br>因子得分: %{x}<extra></extra>',
))

factor_fig.update_layout(
    title=dict(
        text="反转突破因子贡献图（得分 + 方向）",
        x=0.5,
        font=dict(size=20),
    ),
    xaxis=dict(
        title="因子得分（+ 利多反转 / - 利空反转）",
        range=[-10, 10],
        zeroline=True,
        zerolinecolor="#666",
        zerolinewidth=2,
    ),
    yaxis=dict(title=""),
    height=500,
    template="plotly_white",
    margin=dict(l=180),
)

# ============================================================
# 图表 3：多时间框架热力图
# ============================================================
heatmap_data = [
    timeframe_data["SR 收缩度"],
    timeframe_data["反转信号强度"],
    timeframe_data["可信度"],
]
heatmap_labels = ["SR 收缩度", "反转信号强度", "可信度"]

heatmap_fig = go.Figure(data=go.Heatmap(
    z=heatmap_data,
    x=timeframe_data["时间框架"],
    y=heatmap_labels,
    colorscale="RdYlGn",
    zmin=0,
    zmax=10,
    text=heatmap_data,
    texttemplate="%{text}",
    textfont={"size": 14},
    hovertemplate="%{x} %{y}: %{z}<extra></extra>",
))

heatmap_fig.update_layout(
    title=dict(
        text="多时间框架评分热力图",
        x=0.5,
        font=dict(size=20),
    ),
    xaxis=dict(title="时间框架"),
    yaxis=dict(title=""),
    height=350,
    template="plotly_white",
)

# ============================================================
# 组合成完整 HTML 报告
# ============================================================
html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAUUSD 技术面观测雷达与因子分析报告</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
            background: #f8f9fa;
            color: #333;
            line-height: 1.7;
        }}
        h1 {{
            text-align: center;
            color: #1565C0;
            margin-bottom: 8px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 32px;
        }}
        .section {{
            background: #fff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .section h2 {{
            color: #0D47A1;
            border-left: 4px solid #1565C0;
            padding-left: 12px;
            margin-top: 0;
        }}
        .score-card {{
            display: inline-block;
            background: #E3F2FD;
            border-radius: 8px;
            padding: 12px 18px;
            margin: 6px;
            min-width: 120px;
            text-align: center;
        }}
        .score-card .label {{
            font-size: 12px;
            color: #555;
        }}
        .score-card .value {{
            font-size: 22px;
            font-weight: bold;
            color: #1565C0;
        }}
        .conclusion {{
            background: #FFF3E0;
            border-left: 4px solid #FF9800;
            padding: 16px;
            border-radius: 0 8px 8px 0;
        }}
        .risk {{
            background: #FFEBEE;
            border-left: 4px solid #F44336;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin-top: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }}
        th {{
            background: #1565C0;
            color: #fff;
        }}
        tr:nth-child(even) {{
            background: #f2f2f2;
        }}
    </style>
</head>
<body>
    <h1>XAUUSD 技术面观测雷达与因子分析报告</h1>
    <div class="subtitle">基于 RSIOMA + 枢轴点 + H1/H4 SR 指标的多时间框架分析</div>

    <div class="section">
        <h2>一、综合评分卡</h2>
        <div class="score-card">
            <div class="label">当前综合得分</div>
            <div class="value">{composite_score:.1f}/10</div>
        </div>
        <div class="score-card">
            <div class="label">反转信号强度</div>
            <div class="value">{reversal_strength:.0f}/10</div>
        </div>
        <div class="score-card">
            <div class="label">多周期共振度</div>
            <div class="value">{confluence:.0f}/10</div>
        </div>
        <div class="score-card">
            <div class="label">风险等级</div>
            <div class="value">{risk_level}</div>
        </div>
        <p style="margin-top:16px;">
            雷达图显示当前观测在 <b>SR结构</b>、<b>波动率收缩</b> 上得分较高，
            在 <b>风险可控性</b> 上仍有提升空间。与理想反转场景相比，
            当前主要差距在于趋势强度和反转确认的绝对强度。
        </p>
    </div>

    <div class="section">
        <h2>二、观测雷达图</h2>
        {radar_div}
    </div>

    <div class="section">
        <h2>三、反转突破因子贡献图</h2>
        {factor_div}
        <p>
            绿色因子推动反转向上，红色因子构成压制。当前正向因子总和为 <b>{positive_sum}</b>，
            负向因子总和为 <b>{negative_sum}</b>，净效应为 <b>{net_effect}</b>。
        </p>
    </div>

    <div class="section">
        <h2>四、多时间框架评分热力图</h2>
        {heatmap_div}
        <table>
            <tr>
                <th>时间框架</th>
                <th>趋势方向</th>
                <th>SR 收缩度</th>
                <th>反转信号强度</th>
                <th>可信度</th>
            </tr>
            {timeframe_rows}
        </table>
    </div>

    <div class="section">
        <h2>五、关键结论</h2>
        <div class="conclusion">
            <b>核心结构：</b>大周期 H4 SR 提供关键支撑 → 中小周期 H1 SR / 1日/3日枢轴收缩蓄能 →
            价格假跌破/测试 H4 SR 后快速收回 → RSIOMA 低位金叉确认动量转向 →
            多周期共振下形成向上反转突破。
        </div>
        <div class="risk">
            <b>风险提示：</b>本报告仅基于两张静态截图的技术结构研究，不构成交易建议。
            实际决策需结合实时行情、仓位管理和个人风险承受能力。
        </div>
    </div>
</body>
</html>
"""

# 计算汇总指标
composite_score = sum(current) / len(current)
reversal_strength = current[5]
confluence = current[3]
risk_score = current[6]
if risk_score >= 7:
    risk_level = "低"
elif risk_score >= 5:
    risk_level = "中"
else:
    risk_level = "高"

positive_sum = sum(f["score"] for f in factors if f["score"] > 0)
negative_sum = sum(f["score"] for f in factors if f["score"] < 0)
net_effect = positive_sum + negative_sum

# 生成 HTML div
def fig_to_div(fig, div_id):
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
    )

radar_div = fig_to_div(radar_fig, "radar-chart")
factor_div = fig_to_div(factor_fig, "factor-chart")
heatmap_div = fig_to_div(heatmap_fig, "heatmap-chart")

# 生成表格行
timeframe_rows = ""
for i, tf in enumerate(timeframe_data["时间框架"]):
    timeframe_rows += f"""
    <tr>
        <td>{tf}</td>
        <td>{timeframe_data["趋势方向"][i]}</td>
        <td>{timeframe_data["SR 收缩度"][i]}</td>
        <td>{timeframe_data["反转信号强度"][i]}</td>
        <td>{timeframe_data["可信度"][i]}</td>
    </tr>
    """

# 填充模板
html_content = html_template.format(
    composite_score=composite_score,
    reversal_strength=reversal_strength,
    confluence=confluence,
    risk_level=risk_level,
    radar_div=radar_div,
    factor_div=factor_div,
    heatmap_div=heatmap_div,
    positive_sum=positive_sum,
    negative_sum=negative_sum,
    net_effect=net_effect,
    timeframe_rows=timeframe_rows,
)

output_path = r"D:\qoder\csvcl - AVA\reports\XAUUSD_Technical_Radar_Report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"报告已生成: {output_path}")
